import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime


# MongoDB 연결
client = MongoClient(
    "mongodb://3.38.211.228:27017",
    serverSelectionTimeoutMS=5000
)
client.admin.command("ping")
print("MongoDB 연결 성공")

# DB / Collection 선택
db = client["project1"]
collection = db["brand_faq"]


# 크롤링 주소
base_url = "http://192.168.0.51:4000"
url = "http://192.168.0.51:4000/faqs"


# 성공 / 실패 개수
insert_count = 0
error_count = 0


# 첫 페이지 요청
response = requests.get(url)

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


# 브랜드 순회
for brand_link in soup.select(".faq-brand-link"):

    brand_filter = brand_link.get(
        "data-faq-brand-filter"
    )

    # 전체는 제외
    if brand_filter == "all":
        continue

    # 브랜드별 주소 만들기
    href = brand_link.get("href")
    brand_url = base_url + href

    # 브랜드별 페이지 요청
    response = requests.get(brand_url)

    brand_soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # 해당 브랜드 FAQ 순회
    for item in brand_soup.select(".faq-item"):

        brand = item.select_one(
            '[data-field="brand"]'
        ).get_text(strip=True)

        category = item.select_one(
            '[data-field="category"]'
        ).get_text(strip=True)

        question = item.select_one(
            '[data-field="question"]'
        ).get_text(strip=True)

        answer = item.select_one(
            '[data-field="answer"]'
        ).get_text(strip=True)

        source = item.select_one(
            '[data-field="source"]'
        ).get_text(strip=True)

        reviewed_at = item.select_one(
            '[data-field="reviewed-at"]'
        ).get_text(strip=True)

        # MongoDB에 저장할 데이터
        faq = {
            "company": brand,
            "category": category,
            "question": question,
            "answer": answer,
            "link": source,
            "collected_at": reviewed_at
        }

        try:
            # 에러 로그 테스트용 코드
            #raise Exception(
                #"테스트용 MongoDB INSERT 오류"
            #)

            # 중복 확인
            if not collection.find_one({
                "company": brand,
                "question": question
            }):

                # MongoDB INSERT
                collection.insert_one(faq)

                # 성공 개수 증가
                insert_count += 1

        except Exception as e:

            # 실패 개수 증가
            error_count += 1
            print("적재실패: ",e)
            # 에러 로그 파일 열기
            with open(
                "logs/faq_error.log",
                "a",
                encoding="utf-8"
            ) as log:

                # 에러 내용 기록
                log.write(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"MongoDB 처리 실패 | "
                    f"기업명: {brand} | "
                    f"질문: {question} | "
                    f"원인: {e}\n"
                )


# 실행 결과 출력
print(
    f"신규적재: {insert_count}건 | "
    f"실패: {error_count}건"
)


# MongoDB 연결 종료
client.close()


# 실패가 있으면 종료코드 1
if error_count > 0:
    raise SystemExit(1)
