import os
from datetime import date, datetime
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient


# app.py와 같은 폴더에 있는 .env 파일을 읽는다.
ENV_PATH = Path(__file__).resolve().parent / ".env"

if not ENV_PATH.exists():
    raise RuntimeError(f".env 파일이 없습니다: {ENV_PATH}")

load_dotenv(ENV_PATH, override=True)

app = Flask(__name__)


# 필요한 환경변수가 모두 있는지 확인한다.
REQUIRED_ENV = [
    "MYSQL_HOST",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
    "MONGO_URI",
    "MONGO_DATABASE",
]

missing_env = [
    key for key in REQUIRED_ENV
    if not os.getenv(key)
]

if missing_env:
    raise RuntimeError(
        "필수 환경변수가 없습니다: "
        + ", ".join(missing_env)
    )


# =========================
# MySQL 연결
# =========================
def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )


# =========================
# MySQL 차량 데이터 조회
# =========================
def get_cars():
    connection = None
    cursor = None

    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                car_id,
                region,
                sub_region,
                brand,
                model_year,
                fuel_type,
                mileage_km,
                price_krw,
                status,
                registration_date
            FROM car_listing
            ORDER BY car_id DESC
        """)

        cars = cursor.fetchall()

        # MySQL 날짜 객체를 HTML에서 사용할 문자열로 변환한다.
        for car in cars:
            registration_date = car.get("registration_date")

            if isinstance(registration_date, (date, datetime)):
                car["registration_date"] = registration_date.isoformat()

        return cars

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================
# MongoDB 연결
# =========================
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE")

mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
)

mongo_db = mongo_client[MONGO_DATABASE]


# =========================
# MongoDB FAQ 데이터 조회
# =========================
def get_faqs(query=None):
    if query is None:
        query = {}

    # MongoDB FAQ 문서의 실제 필드만 조회한다.
    documents = list(
        mongo_db["brand_faq"].find(
            query,
            {
                "_id": 0,
                "company": 1,
                "category": 1,
                "question": 1,
                "answer": 1,
                "link": 1,
                "collected_at": 1,
            },
        )
    )

    # 혹시 날짜 타입이 추가되어도 JSON 변환이 가능하도록 처리한다.
    for document in documents:
        for key, value in document.items():
            if isinstance(value, (date, datetime)):
                document[key] = value.isoformat()

    return documents


# =========================
# 메인 페이지
# =========================
@app.route("/")
def index():
    try:
        # 메인 페이지에는 차량 데이터만 전달한다.
        cars = get_cars()

        return render_template(
            "index.html",
            cars=cars,
        )

    except Exception:
        app.logger.exception("index 페이지 데이터 조회 실패")

        return (
            "데이터 조회 중 오류가 발생했습니다. "
            "서비스 로그를 확인하세요.",
            500,
        )


# =========================
# FAQ 전용 페이지
# =========================
@app.route("/faq")
def faq_page():
    try:
        # MongoDB FAQ 데이터를 FAQ 전용 화면에 전달한다.
        faqs = get_faqs()

        return render_template(
            "faq.html",
            faqs=faqs,
        )

    except Exception:
        app.logger.exception("FAQ 페이지 데이터 조회 실패")

        return (
            "FAQ 데이터 조회 중 오류가 발생했습니다. "
            "서비스 로그를 확인하세요.",
            500,
        )


# =========================
# MySQL 차량 API
# =========================
@app.route("/api/cars")
def cars_api():
    try:
        return jsonify(get_cars())

    except Exception:
        app.logger.exception("MySQL 차량 데이터 조회 실패")

        return jsonify({
            "error": "MySQL 차량 데이터 조회에 실패했습니다.",
        }), 500


# =========================
# MongoDB FAQ API
# =========================
@app.route("/api/faqs")
def faqs_api():
    try:
        query = {}

        # company와 category가 전달되면 MongoDB 검색 조건으로 사용한다.
        company = request.args.get("company")
        category = request.args.get("category")

        if company:
            query["company"] = company

        if category:
            query["category"] = category

        return jsonify(get_faqs(query))

    except Exception:
        app.logger.exception("MongoDB FAQ 데이터 조회 실패")

        return jsonify({
            "error": "MongoDB FAQ 데이터 조회에 실패했습니다.",
        }), 500


# 개발 서버 실행용 코드다.
# 운영 환경에서는 systemd가 Gunicorn으로 실행한다.
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True,
    )
