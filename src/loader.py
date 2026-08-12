"""Load normalized used-car JSON records into the local MySQL table.

처리 흐름은 다음과 같다.
1. JSON 파일을 읽는다.
2. 원본의 중첩 필드를 MySQL 컬럼 형태로 변환한다.
3. 필수값과 상태값을 검증하고 record_hash를 만든다.
4. 같은 데이터면 건너뛰고, 새 데이터나 변경 데이터만 upsert한다.

Usage:
    python src/loader.py --input data/fixtures/vehicle_105764.json --dry-run
    python src/loader.py --input data/fixtures/vehicle_105764.json

The input can be one JSON object, a JSON array, or an API envelope whose
``data`` value is a list of objects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    import mysql.connector
except ModuleNotFoundError:  # pragma: no cover - depends on the local environment
    mysql = None  # type: ignore[assignment]
else:
    mysql = mysql.connector


# INSERT_FIELDS의 순서와 UPSERT_SQL의 VALUES 순서는 반드시 같아야 한다.
# 이 목록은 변환된 row에서 어떤 필드를 DB에 넣을지 결정한다.
INSERT_FIELDS = (
    "source_id",
    "car_id",
    "listing_number",
    "title",
    "brand",
    "model_year",
    "fuel_type",
    "region",
    "base_region",
    "mileage_km",
    "price_krw",
    "currency",
    "status",
    "registered_at",
    "record_hash",
    "run_id",
    "quality_status",
    "collected_at",
    "ingested_at",
)

# 차량이 처음 들어오면 INSERT하고, 같은 기본 키가 있으면 UPDATE한다.
# ON DUPLICATE KEY UPDATE가 upsert 동작을 담당한다.
UPSERT_SQL = """
INSERT INTO car_listing (
    source_id, car_id, listing_number, title, brand, model_year,
    fuel_type, region, base_region, mileage_km, price_krw, currency,
    status, registered_at, record_hash, run_id, quality_status,
    collected_at, ingested_at
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    listing_number = VALUES(listing_number),
    title = VALUES(title),
    brand = VALUES(brand),
    model_year = VALUES(model_year),
    fuel_type = VALUES(fuel_type),
    region = VALUES(region),
    base_region = VALUES(base_region),
    mileage_km = VALUES(mileage_km),
    price_krw = VALUES(price_krw),
    currency = VALUES(currency),
    status = VALUES(status),
    registered_at = VALUES(registered_at),
    record_hash = VALUES(record_hash),
    run_id = VALUES(run_id),
    quality_status = VALUES(quality_status),
    collected_at = VALUES(collected_at),
    ingested_at = VALUES(ingested_at)
"""

# record_hash를 만들 때 비교할 실제 차량 데이터 필드다.
# run_id나 collected_at은 실행할 때마다 바뀌는 운영 정보이므로 해시에 포함하지 않는다.
HASH_FIELDS = (
    "source_id",
    "car_id",
    "listing_number",
    "title",
    "brand",
    "model_year",
    "fuel_type",
    "region",
    "base_region",
    "mileage_km",
    "price_krw",
    "currency",
    "status",
    "registered_at",
)


def load_records(path: Path) -> list[dict[str, Any]]:
    """JSON 객체, JSON 배열, data 배열을 모두 차량 record 목록으로 통일한다."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        records = payload["data"]
    elif isinstance(payload, dict):
        records = [payload]
    else:
        raise ValueError("JSON must be an object, array, or data envelope")

    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Every JSON record must be an object")
    return records


def parse_datetime(value: str) -> datetime:
    """ISO 시간을 MySQL DATETIME에 넣을 수 있는 UTC 기준 시간으로 바꾼다."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def as_int(value: Any, field_name: str) -> int:
    """주행거리·가격·연식처럼 숫자여야 하는 값을 정수로 변환한다."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def normalize(raw: dict[str, Any], source_id: str, run_id: str, collected_at: datetime) -> dict[str, Any]:
    """원본 차량 JSON을 car_listing 테이블의 한 행(row)으로 변환하고 검증한다."""

    # 원본 JSON에서는 brand와 location이 객체로 중첩되어 있다.
    brand = raw.get("brand") or {}
    location = raw.get("location") or {}

    # 화면의 한글 상태값이 들어와도 DB에는 정해진 영문 enum 값으로 저장한다.
    status_map = {
        "판매중": "AVAILABLE",
        "예약중": "RESERVED",
        "판매완료": "SOLD",
    }
    status = status_map.get(str(raw.get("status", "")), str(raw.get("status", "")).upper())

    # 원본 필드명을 DB의 표준(canonical) 필드명으로 맞춘다.
    row: dict[str, Any] = {
        "source_id": source_id,
        "car_id": str(raw["id"]),
        "listing_number": str(raw["listingNumber"]),
        "title": str(raw["title"]).strip(),
        "brand": str(brand["name"]).strip(),
        "model_year": as_int(raw["modelYear"], "modelYear"),
        "fuel_type": str(raw.get("fuelType", "")).strip() or None,
        "region": str(location["province"]).strip(),
        "base_region": str(location["city"]).strip(),
        "mileage_km": as_int(raw["mileageKm"], "mileageKm"),
        "price_krw": as_int(raw["price"], "price"),
        "currency": str(raw.get("currency", "KRW")).strip(),
        "status": status,
        # 현재 테이블에서 registered_at은 매물 생성 시각(createdAt)을 의미한다.
        # firstRegistration은 차량 최초 등록일이라 의미가 다르고, 현재 테이블에는 저장하지 않는다.
        "registered_at": parse_datetime(str(raw["createdAt"])),
        "run_id": run_id,
        "quality_status": "pass",
        "collected_at": collected_at,
        "ingested_at": collected_at,
    }

    # DB에 넣기 전에 필수값이 빠졌는지 검사한다.
    required = (
        "car_id",
        "listing_number",
        "title",
        "brand",
        "region",
        "base_region",
        "model_year",
        "mileage_km",
        "price_krw",
        "status",
        "registered_at",
    )
    missing = [field for field in required if row.get(field) in (None, "")]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    # DB에서 허용하는 차량 상태만 통과시킨다.
    if status not in {"AVAILABLE", "RESERVED", "SOLD"}:
        raise ValueError(f"unsupported status: {status}")

    # 정규화된 값으로 해시를 만들기 때문에 표기 방식만 달라진 같은 데이터는 같은 해시를 갖는다.
    # 예: 91,516km와 91516을 모두 91516으로 만든 뒤 비교한다.
    hash_payload = {field: row[field] for field in HASH_FIELDS}
    hash_text = json.dumps(hash_payload, ensure_ascii=False, sort_keys=True, default=str)
    row["record_hash"] = hashlib.sha256(hash_text.encode("utf-8")).hexdigest()
    return row


def connect_mysql():
    """환경변수로 MySQL 접속 정보를 읽어 DB 연결을 만든다."""
    if mysql is None:
        raise RuntimeError(
            "mysql-connector-python is not installed. "
            "Run: python -m pip install mysql-connector-python"
        )

    return mysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "autodata"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
    )


def upsert_rows(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """변환된 차량 행을 저장하고, 변경 없는 행은 건너뛴다."""
    connection = connect_mysql()
    cursor = connection.cursor()
    skipped = 0
    loaded = 0

    try:
        for row in rows:
            # 같은 출처의 같은 차량이 이미 있는지 먼저 확인한다.
            cursor.execute(
                "SELECT record_hash FROM car_listing WHERE source_id = %s AND car_id = %s",
                (row["source_id"], row["car_id"]),
            )
            existing = cursor.fetchone()

            # record_hash가 같으면 내용이 완전히 같으므로 재적재하지 않는다.
            if existing and existing[0] == row["record_hash"]:
                skipped += 1
                continue

            # 신규 차량이면 INSERT, 기존 차량이지만 내용이 바뀌었으면 UPDATE한다.
            cursor.execute(UPSERT_SQL, tuple(row[field] for field in INSERT_FIELDS))
            loaded += 1

        connection.commit()
    except Exception:
        # 한 건이라도 오류가 나면 이번 실행의 전체 변경을 취소한다.
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

    return loaded, skipped


def main() -> int:
    # 명령줄에서 입력 파일과 실행 옵션을 받는다.
    parser = argparse.ArgumentParser(description="Load used-car JSON into MySQL car_listing")
    parser.add_argument("--input", required=True, type=Path, help="JSON file path")
    parser.add_argument(
        "--source-id",
        default=os.getenv("SOURCE_ID", "autodata-lab-local"),
    )
    parser.add_argument("--run-id", default=str(uuid.uuid4()))
    parser.add_argument("--dry-run", action="store_true", help="normalize only; do not connect to MySQL")
    args = parser.parse_args()

    # 1단계: 입력 JSON을 읽는다.
    raw_records = load_records(args.input)
    collected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_records):
        try:
            # 2~3단계: 원본을 표준 row로 변환하고 검증한다.
            rows.append(normalize(raw, args.source_id, args.run_id, collected_at))
        except (KeyError, TypeError, ValueError) as exc:
            # 한 record의 오류가 전체 처리를 중단시키지 않도록 오류 목록에 기록한다.
            errors.append({"index": index, "error": str(exc)})

    result: dict[str, Any] = {
        "run_id": args.run_id,
        "input_count": len(raw_records),
        "accepted_count": len(rows),
        "rejected_count": len(errors),
        "loaded_count": 0,
        "skipped_count": 0,
        "errors": errors,
    }

    if args.dry_run:
        # dry-run은 변환·검증 결과만 보여주고 MySQL에는 접속하지 않는다.
        result["records"] = rows
    elif rows:
        # 4단계: 정상 row만 MySQL에 적재한다.
        result["loaded_count"], result["skipped_count"] = upsert_rows(rows)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 1 if errors and not rows else 0


if __name__ == "__main__":
    sys.exit(main())
