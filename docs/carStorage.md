# 차량정보·FAQ 저장소 설계 (`carStorage`)

> source: [AutoData Lab](http://192.168.0.51:4000/)  
> 차량정보: MySQL  
> FAQ: MongoDB

차량정보와 FAQ는 구조와 조회 방식이 다르므로 저장소를 분리한다.

차량정보는 현재 팀이 선택한 로컬 목록 source를 기준으로 하고, FAQ는 로컬 `/faqs` HTML을 기준으로 한다.

프로젝트 brief의 저장소 역할은 그대로 적용한다. 정형 차량정보는 MySQL, 문서형 FAQ는 MongoDB에 저장한다. Day1에는 두 저장소에 소량 sample만 연결한다.

## 1. 저장소 결정

| 데이터 | 저장소 | collection/table |
|---|---|---|
| 차량 목록 | MySQL | `car_listing` |
| 브랜드 FAQ | MongoDB | `brand_faq` |

## 2. MySQL 차량 table

### `car_listing` 한 행

차량 목록의 매물 한 건을 저장한다.

| source field | 의미 |
|---|---|
| `source_id` | source 식별자 |
| `car_id` | API `id` 또는 HTML `data-car-id` |
| `listing_number` | `UC-...` 형식 매물번호 |
| `title` | 목록 제목 |
| `brand` | 브랜드 |
| `model_year` | 연식 |
| `fuel_type` | 연료 |
| `location` | 차량 소재지 |
| `mileage_km` | 주행거리(km) |
| `price_krw` | 가격(원) |
| `currency` | 통화 |
| `status` | `AVAILABLE`, `RESERVED`, `SOLD` |
| `registered_at` | 등록일 |

내부 적재 추적용으로 `record_hash`, `run_id`, `quality_status`, `collected_at`, `ingested_at`을 함께 둔다. 화면의 `번호`는 page 순번이라 저장하지 않는다.

### DDL 초안

```sql
CREATE TABLE car_listing (
    source_id       VARCHAR(100) NOT NULL,
    car_id          VARCHAR(64)  NOT NULL,
    listing_number  VARCHAR(64)  NOT NULL,
    title           VARCHAR(200) NOT NULL,
    brand           VARCHAR(80)  NOT NULL,
    model_year      SMALLINT     NOT NULL,
    fuel_type       VARCHAR(40)  NULL,
    location        VARCHAR(160) NULL,
    mileage_km      INT          NOT NULL,
    price_krw       BIGINT       NOT NULL,
    currency        CHAR(3)      NULL,
    status          VARCHAR(20)  NOT NULL,
    registered_at   DATETIME     NOT NULL,
    record_hash     CHAR(64)     NOT NULL,
    run_id          CHAR(36)     NOT NULL,
    quality_status  VARCHAR(20)  NOT NULL,
    collected_at    DATETIME     NOT NULL,
    ingested_at     DATETIME     NOT NULL,
    PRIMARY KEY (source_id, car_id),
    UNIQUE KEY uq_car_listing_number (source_id, listing_number),
    KEY idx_car_filter (status, brand, location, model_year),
    KEY idx_car_price (status, price_krw),
    KEY idx_car_run (run_id)
);
```

## 3. MongoDB FAQ collection

### `brand_faq` 한 document

FAQ card 하나를 document 하나로 저장한다.

```json
{
  "_id": "<source_id>:<faq_id>",
  "source_id": "<source_id>",
  "faq_id": "hyundai-support-001",
  "brand": "현대",
  "category": "고객지원",
  "question": "FAQ 질문 heading",
  "answer": "FAQ 답변 paragraph",
  "source_url": "<official-source-url>",
  "source_checked_at": "2026-08-11",
  "content_hash": "<sha256>",
  "run_id": "<run-id>",
  "quality_status": "pass",
  "collected_at": "<ISO-8601>",
  "ingested_at": "<ISO-8601>"
}
```

### Index

```javascript
db.brand_faq.createIndex(
  { source_id: 1, faq_id: 1 },
  { unique: true }
);

db.brand_faq.createIndex(
  { source_id: 1, brand: 1, category: 1 }
);
```

조회 기준은 브랜드·category와 `faq_id`다. 질문·답변 full-text index는 실제 검색 요구가 생긴 뒤 추가한다.

## 4. 전처리 전·후 산출물과 품질 결과

```text
raw/<run_id>/vehicle.json
raw/<run_id>/faq.json
processed/<run_id>/vehicle.json 또는 vehicle.csv
processed/<run_id>/faq.json
quality/<run_id>/result.json
logs/<run_id>/pipeline.log
logs/<run_id>/error.log
```

품질 결과에는 track별 `input_count`, `accepted_count`, `rejected_count`, `skipped_count`, `loaded_count`를 기록한다. raw는 원본, processed는 변환 결과로 구분한다.

## 5. 적재 규칙

### 차량정보

- `source_id + car_id`가 같으면 같은 차량으로 보고 MySQL upsert한다.
- 같은 `record_hash`면 `skipped`로 처리한다.
- hash가 달라지면 목록 field를 갱신한다.
- 필수값 검사에 실패한 record는 `car_listing`에 넣지 않는다.
- `listing_number`가 중복이면 적재 전에 오류로 처리한다.

### FAQ

- `source_id + faq_id`를 unique key로 사용한다.
- 같은 `content_hash`면 `skipped`로 처리한다.
- hash가 달라지면 같은 FAQ document를 update한다.
- 질문·답변·공식 source URL·확인일이 없는 document는 적재하지 않는다.

## 6. 예시

### 차량 record

```json
{
  "source_id": "<source_id>",
  "car_id": "<data-car-id>",
  "listing_number": "UC-00094191",
  "title": "2008 기아 레이 트렌디",
  "brand": "기아",
  "model_year": 2008,
  "fuel_type": "가솔린",
  "location": "광주광역시 북구",
  "mileage_km": 202142,
  "price_krw": 1500000,
  "currency": "KRW",
  "status": "RESERVED",
  "registered_at": "2025-08-31"
}
```

### FAQ record

```json
{
  "faq_id": "hyundai-support-001",
  "brand": "현대",
  "category": "고객지원",
  "question": "FAQ 질문 heading",
  "answer": "FAQ 답변 paragraph",
  "source_url": "<official-source-url>",
  "source_checked_at": "2026-08-11"
}
```

## 7. AWS 저장소 소량 연결

- MySQL target은 프로젝트 환경에 따라 local MySQL, Amazon Linux MySQL 또는 승인된 RDS로 주입한다.
- FAQ target은 승인된 MongoDB 연결정보로 주입한다.
- 실제 credential은 `.env.example`에 넣지 않고 환경변수 또는 secret으로 주입한다.
- Day1 확인량은 차량 1건과 FAQ 1건이다.
- MySQL 1행, MongoDB 1 document, 전처리 전·후 파일, 품질 결과, 실행 log를 확인한다.

## 8. Day21 확인 범위

1. 차량 HTML/API 한 건을 받아 전처리 후 MySQL `car_listing`에 적재한다.
2. FAQ HTML 한 건을 받아 전처리 후 MongoDB `brand_faq`에 적재한다.
3. 차량·FAQ 각각의 필수값과 중복 key를 검사한다.
4. 같은 sample을 다시 실행해 차량과 FAQ가 중복되지 않는지 확인한다.
