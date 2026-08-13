"""중고차 JSON을 MySQL car_listing 테이블에 저장하는 loader."""

import json
from datetime import date
from pathlib import Path

from db_config import DB_CONFIG

try:
    import mysql.connector
except ModuleNotFoundError:
    mysql = None
else:
    mysql = mysql.connector


# 테이블명이나 허용 상태를 바꿀 때 먼저 보는 설정이다.
TABLE_NAME = "car_listing"
ALLOWED_STATUS = {"AVAILABLE", "RESERVED", "SOLD"}

INSERT_SQL = f"""
    INSERT INTO {TABLE_NAME} (
        car_id, region, sub_region, brand, model_year,
        fuel_type, mileage_km, price_krw, status, registration_date
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        region = VALUES(region),
        sub_region = VALUES(sub_region),
        brand = VALUES(brand),
        model_year = VALUES(model_year),
        fuel_type = VALUES(fuel_type),
        mileage_km = VALUES(mileage_km),
        price_krw = VALUES(price_krw),
        status = VALUES(status),
        registration_date = VALUES(registration_date)
"""


def read_json(file_path):
    """JSON 파일 한 개를 읽는다."""
    data = json.loads(file_path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("입력 JSON은 객체 한 개여야 합니다.")

    return data


def parse_registration_date(value):
    """YYYY-MM-DD 형식의 차량 등록일을 날짜 값으로 바꾼다."""
    return date.fromisoformat(value[:10])


def normalize_car(raw):
    """원본 JSON에서 DB에 필요한 값만 꺼내 이름과 타입을 바꾼다."""
    brand = raw.get("brand")
    if brand is None:
        brand = {}

    location = raw.get("location")
    if location is None:
        location = {}

    fuel_type = str(raw.get("fuelType", "")).strip()
    if fuel_type == "":
        fuel_type = None

    car = {
        "car_id": int(raw["id"]),
        "region": str(location["province"]).strip(),
        "sub_region": str(location["city"]).strip(),
        "brand": str(brand["name"]).strip(),
        "model_year": int(raw["modelYear"]),
        "fuel_type": fuel_type,
        "mileage_km": int(raw["mileageKm"]),
        "price_krw": int(raw["price"]),
        "status": str(raw["status"]).strip().upper(),
        "registration_date": parse_registration_date(
            str(raw["firstRegistration"])
        ),
    }

    return car


def validate_car(car):
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

    errors = []
    for field in required_fields:
        if car.get(field) in (None, ""):
            errors.append(field + " 값이 없습니다.")

    if car.get("status") not in ALLOWED_STATUS:
        errors.append("status는 AVAILABLE, RESERVED, SOLD 중 하나여야 합니다.")

    return errors


def connect_mysql():
    """환경변수로 로컬 MySQL에 연결한다."""
    if mysql is None:
        raise RuntimeError("mysql-connector-python을 먼저 설치하세요.")

    return mysql.connect(**DB_CONFIG)


def count_car_listings():
    """car_listing 테이블의 전체 행 개수를 반환한다."""
    connection = connect_mysql()
    cursor = connection.cursor()

    try:
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        result = cursor.fetchone()
        return int(result[0])

    finally:
        cursor.close()
        connection.close()


def car_values(car):
    """정제된 차량 dictionary를 SQL 값 순서의 tuple로 바꾼다."""
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

    return values


def save_cars(cars):
    """정제·검증된 차량 여러 건을 한 transaction으로 저장한다."""
    if not cars:
        return 0

    connection = connect_mysql()
    cursor = connection.cursor()

    try:
        for car in cars:
            cursor.execute(INSERT_SQL, car_values(car))

        connection.commit()
        return len(cars)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def insert_cars(raw_cars):
    """API에서 받은 차량 여러 건을 정제·검증한 뒤 모두 저장한다."""
    cars = []

    for number, raw in enumerate(raw_cars, start=1):
        car = normalize_car(raw)
        errors = validate_car(car)

        if errors:
            error_message = "; ".join(errors)
            raise ValueError(
                f"{number}번째 차량 검증 실패: {error_message}"
            )

        cars.append(car)

    return save_cars(cars)


def insert_car(car):
    """정제된 차량 한 건을 저장한다."""
    return save_cars([car])
