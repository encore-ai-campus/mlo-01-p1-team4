"""가상 중고차 JSON 한 건을 MySQL에 저장하는 초급용 loader."""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

try:
    import mysql.connector
except ModuleNotFoundError:
    mysql = None
else:
    mysql = mysql.connector


# 수정이 필요할 때 먼저 보는 설정이다.
TABLE_NAME = "car_listing"
ALLOWED_STATUS = {"AVAILABLE", "RESERVED", "SOLD"}


def read_json(file_path: Path) -> dict:
    """JSON 파일 한 개를 읽는다."""
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("입력 JSON은 객체 한 개여야 합니다.")
    return data


def parse_registration_date(value: str) -> date:
    """YYYY-MM-DD 형식의 차량 등록일을 날짜 값으로 바꾼다."""
    return date.fromisoformat(value[:10])


def normalize_car(raw: dict) -> dict:
    """원본 JSON에서 DB에 필요한 값만 꺼내 이름을 바꾼다."""
    brand = raw.get("brand") or {}
    location = raw.get("location") or {}

    return {
        "car_id": int(raw["id"]),
        "region": str(location["province"]).strip(),
        "sub_region": str(location["city"]).strip(),
        "brand": str(brand["name"]).strip(),
        "model_year": int(raw["modelYear"]),
        "fuel_type": str(raw.get("fuelType", "")).strip() or None,
        "mileage_km": int(raw["mileageKm"]),
        "price_krw": int(raw["price"]),
        "status": str(raw["status"]).strip().upper(),
        "registration_date": parse_registration_date(str(raw["firstRegistration"])),
    }


def validate_car(car: dict) -> list[str]:
    """필수값과 상태값을 확인하고 오류 목록을 반환한다."""
    required_fields = [
        "car_id",
        "region",
        "sub_region",
        "brand",
        "model_year",
        "fuel_type",
        "mileage_km",
        "price_krw",
        "status",
        "registration_date",
    ]
    errors = [field + " 값이 없습니다." for field in required_fields if car.get(field) in (None, "")]

    if car.get("status") not in ALLOWED_STATUS:
        errors.append("status는 AVAILABLE, RESERVED, SOLD 중 하나여야 합니다.")

    return errors


def connect_mysql():
    """환경변수로 로컬 MySQL에 연결한다."""
    if mysql is None:
        raise RuntimeError("mysql-connector-python을 먼저 설치하세요.")

    return mysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "project1"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
    )


def insert_car(car: dict) -> None:
    """차량 한 건을 INSERT한다."""
    sql = f"""
        INSERT INTO {TABLE_NAME} (
            car_id, region, sub_region, brand, model_year,
            fuel_type, mileage_km, price_krw, status, registration_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        car["car_id"],
        car["region"],
        car["sub_region"],
        car["brand"],
        car["model_year"],
        car["fuel_type"],
        car["mileage_km"],
        car["price_krw"],
        car["status"],
        car["registration_date"],
    )

    connection = connect_mysql()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, values)
        connection.commit()
        cursor.close()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="차량 JSON 한 건을 MySQL에 INSERT합니다.")
    parser.add_argument("--input", required=True, type=Path, help="입력 JSON 파일")
    parser.add_argument("--dry-run", action="store_true", help="변환 결과만 출력하는 확인 모드")
    args = parser.parse_args()

    try:
        raw = read_json(args.input)
        car = normalize_car(raw)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(json.dumps({"input_count": 1, "valid_count": 0, "rejected_count": 1, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1

    errors = validate_car(car)
    if errors:
        print(json.dumps({"input_count": 1, "valid_count": 0, "rejected_count": 1, "errors": errors}, ensure_ascii=False, indent=2, default=str))
        return 1

    if args.dry_run:
        print(json.dumps({"input_count": 1, "valid_count": 1, "rejected_count": 0, "loaded_count": 0, "record": car}, ensure_ascii=False, indent=2, default=str))
        return 0

    try:
        insert_car(car)
    except Exception as error:
        print(json.dumps({"input_count": 1, "valid_count": 1, "rejected_count": 0, "loaded_count": 0, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"input_count": 1, "valid_count": 1, "rejected_count": 0, "loaded_count": 1}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
