"""car_listing의 차량 데이터 품질을 검사한다."""

import json
from datetime import date, datetime
from pathlib import Path

from loader import TABLE_NAME, connect_mysql


# SELECT 결과의 컬럼 순서와 같다.
COLUMNS = [
    "car_id", "region", "sub_region", "brand", "model_year",
    "fuel_type", "mileage_km", "price_krw", "status",
    "registration_date",
]

# 현재 파일의 상위 프로젝트 폴더에 있는 output 폴더를 결과 저장 위치로 지정한다.
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "quality_check_output"


def check_car(row): 
    """차량 한 건의 빈 값과 기본 형식을 검사한다."""
    errors = []

    for index in range(len(COLUMNS)):
        if row[index] is None or row[index] == "":
            errors.append(COLUMNS[index] + " 값이 없습니다.")

    if not isinstance(row[0], int):
        errors.append("car_id 형식 오류")
    if not isinstance(row[4], int):
        errors.append("model_year 형식 오류")
    if not isinstance(row[5], str):
        errors.append("fuel_type 형식 오류")
    if not isinstance(row[6], int) or row[6] < 0: #주행거리는 음수가 될 수 없으므로 0보다 작은 경우 오류로 처리
        errors.append("mileage_km 값 오류")
    if not isinstance(row[7], int) or row[7] < 0: # 가격은 음수가 될 수 없으므로 0보다 작은 경우 오류로 처리
        errors.append("price_krw 값 오류")
    if row[8] not in ["AVAILABLE", "RESERVED", "SOLD"]:
        errors.append("status 값 오류")
    if not isinstance(row[9], date):
        errors.append("registration_date 형식 오류")
    # region, sub_region, brand는 loader.py에서 이미 문자열로 변환하고
    # MySQL에서도 문자열 컬럼으로 저장하므로 자료형 검사는 생략한다.
    # 값이 비어 있는지는 위의 필수값 검사에서 확인한다.
    return errors


def main():
    # 1. MySQL에서 차량 데이터를 가져온다.
    connection = connect_mysql()
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT car_id, region, sub_region, brand, model_year,
               fuel_type, mileage_km, price_krw, status,
               registration_date
        FROM {TABLE_NAME}
    """)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    processed_cars = []
    rejected_cars = []

    # 2. 모든 차량을 검사한다.
    for row in rows:
        car = dict(zip(COLUMNS, row))
        car["registration_date"] = str(car["registration_date"])
        processed_cars.append(car)

        errors = check_car(row)
        if errors:
            rejected_cars.append({"car_id": row[0], "errors": errors})

    # 3. 검사 결과를 만든다.
    report = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "table": TABLE_NAME,
        "input_count": len(rows),
        "processed_count": len(processed_cars),
        "loaded_count": len(rows),
        "accepted_count": len(rows) - len(rejected_cars),
        "rejected_count": len(rejected_cars),
        "skipped_count": 0,
        "quality_status": "PASS" if not rejected_cars else "FAIL",
        "errors": rejected_cars,
    }

    # 4. 전처리 결과와 품질 결과를 파일로 저장한다.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "processed-cars.json").write_text(
        json.dumps(processed_cars, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("검사 대상:", len(rows), "건")
    print("검사 통과:", report["accepted_count"], "건")
    print("검사 실패:", report["rejected_count"], "건")
    print("품질 상태:", report["quality_status"])


if __name__ == "__main__":
    main()
