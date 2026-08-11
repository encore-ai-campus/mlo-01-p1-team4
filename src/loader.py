"""Load normalized used-car JSON records into the local MySQL table.

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
    """Parse an ISO timestamp and store it as a UTC-naive MySQL DATETIME."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def as_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def normalize(raw: dict[str, Any], source_id: str, run_id: str, collected_at: datetime) -> dict[str, Any]:
    brand = raw.get("brand") or {}
    location = raw.get("location") or {}

    status_map = {
        "판매중": "AVAILABLE",
        "예약중": "RESERVED",
        "판매완료": "SOLD",
    }
    status = status_map.get(str(raw.get("status", "")), str(raw.get("status", "")).upper())

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
        # The current table's registered_at means listing createdAt.
        # firstRegistration is a different vehicle attribute and is not stored yet.
        "registered_at": parse_datetime(str(raw["createdAt"])),
        "run_id": run_id,
        "quality_status": "pass",
        "collected_at": collected_at,
        "ingested_at": collected_at,
    }

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

    if status not in {"AVAILABLE", "RESERVED", "SOLD"}:
        raise ValueError(f"unsupported status: {status}")

    hash_payload = {field: row[field] for field in HASH_FIELDS}
    hash_text = json.dumps(hash_payload, ensure_ascii=False, sort_keys=True, default=str)
    row["record_hash"] = hashlib.sha256(hash_text.encode("utf-8")).hexdigest()
    return row


def connect_mysql():
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
    connection = connect_mysql()
    cursor = connection.cursor()
    skipped = 0
    loaded = 0

    try:
        for row in rows:
            cursor.execute(
                "SELECT record_hash FROM car_listing WHERE source_id = %s AND car_id = %s",
                (row["source_id"], row["car_id"]),
            )
            existing = cursor.fetchone()
            if existing and existing[0] == row["record_hash"]:
                skipped += 1
                continue

            cursor.execute(UPSERT_SQL, tuple(row[field] for field in INSERT_FIELDS))
            loaded += 1

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

    return loaded, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Load used-car JSON into MySQL car_listing")
    parser.add_argument("--input", required=True, type=Path, help="JSON file path")
    parser.add_argument(
        "--source-id",
        default=os.getenv("SOURCE_ID", "autodata-lab-local"),
    )
    parser.add_argument("--run-id", default=str(uuid.uuid4()))
    parser.add_argument("--dry-run", action="store_true", help="normalize only; do not connect to MySQL")
    args = parser.parse_args()

    raw_records = load_records(args.input)
    collected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_records):
        try:
            rows.append(normalize(raw, args.source_id, args.run_id, collected_at))
        except (KeyError, TypeError, ValueError) as exc:
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
        result["records"] = rows
    elif rows:
        result["loaded_count"], result["skipped_count"] = upsert_rows(rows)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 1 if errors and not rows else 0


if __name__ == "__main__":
    sys.exit(main())
