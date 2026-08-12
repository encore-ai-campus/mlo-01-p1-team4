# 차량정보·FAQ 저장소 설계 (`carStorage`)

<!--
이 문서는 carPipeline에서 처리한 데이터를 실제 DB에 어떤 구조로 저장할지 정의한다.
차량은 MySQL의 행(row), FAQ는 MongoDB의 document로 저장한다.
-->

> source: [AutoData Lab](http://192.168.0.51:4000/)  
> 차량정보: MySQL  
> FAQ: MongoDB

<!-- 차량은 정형 필드와 조건 검색이 중심이고, FAQ는 질문·답변 문서 조회가 중심이어서 저장소를 분리한다. -->

차량정보와 FAQ는 구조와 조회 방식이 다르므로 저장소를 분리한다.

차량정보는 현재 팀이 선택한 로컬 목록 source를 기준으로 하고, FAQ는 로컬 `/faqs` HTML을 기준으로 한다.

## 1. 저장소 결정

<!-- table은 MySQL 테이블, collection은 MongoDB 문서 모음이다. -->

| 데이터 | 저장소 | collection/table |
|---|---|---|
| 차량 목록 | MySQL | `car_listing` |
| 브랜드 FAQ | MongoDB | `brand_faq` |

## 2. MySQL 차량 table

<!-- 차량 매물 한 건을 car_listing의 한 행으로 저장한다. -->

### `car_listing` 한 행

<!-- source_id + car_id가 같은 차량을 식별하는 business key이고, listing_number는 별도로 중복을 검사한다. -->

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
| `region` | 광역 지역 |
| `base_region` | 기초 지역 |
| `mileage_km` | 주행거리(km) |
| `price_krw` | 가격(원) |
| `currency` | 통화 |
| `status` | `AVAILABLE`, `RESERVED`, `SOLD` |
| `registered_at` | 등록일 |

내부 적재 추적용으로 `record_hash`, `run_id`, `quality_status`, `collected_at`, `ingested_at`을 함께 둔다. 화면의 `번호`는 page 순번이라 저장하지 않는다.

### DDL 초안

<!-- DDL은 테이블을 생성하기 위한 SQL이다. PRIMARY KEY는 고유 식별자, UNIQUE KEY는 중복 방지, KEY는 조회 성능을 위한 인덱스다. -->

```sql
CREATE TABLE car_listing (
    source_id       VARCHAR(100) NOT NULL,
    car_id          VARCHAR(64)  NOT NULL,
    listing_number  VARCHAR(64)  NOT NULL,
    title           VARCHAR(200) NOT NULL,
    brand           VARCHAR(80)  NOT NULL,
    model_year      SMALLINT     NOT NULL,
    fuel_type       VARCHAR(40)  NULL,
    region          VARCHAR(50)  NOT NULL,
    base_region     VARCHAR(50)  NOT NULL,
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
    KEY idx_car_filter (status, brand, region, base_region, model_year),
    KEY idx_car_price (status, price_krw),
    KEY idx_car_run (run_id)
);
```

## 3. MongoDB FAQ collection

<!-- FAQ 하나를 brand_faq의 document 하나로 저장한다. document는 JSON과 비슷한 MongoDB의 문서 단위다. -->

### `brand_faq` 한 document

<!-- _id와 source_id·faq_id는 FAQ 식별에 사용하고, content_hash는 질문·답변 변경 여부 확인에 사용한다. -->

FAQ card 하나를 document 하나로 저장한다.

```json
{
  "_id": "<source_id>:<faq_id>",
  "source_id": "<source_id>",
  "faq_id": "hyundai-support-001",
  "brand_id": "hyundai",
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

<!-- 인덱스는 자주 사용하는 브랜드·카테고리·FAQ ID 조회를 빠르게 하며 unique 옵션은 중복을 막는다. -->

```javascript
db.brand_faq.createIndex(
  { source_id: 1, faq_id: 1 },
  { unique: true }
);

db.brand_faq.createIndex(
  { source_id: 1, brand_id: 1, category: 1 }
);

db.brand_faq.createIndex(
  { source_id: 1, brand: 1 }
);
```

조회 기준은 `brand_id`·brand·category와 `faq_id`다. `brand_id`는 source가 제공하는 영문 브랜드 코드이고, `brand`는 화면 표시 기업명이다. 기업명이 변경되면 source가 제공하는 최신 `brand_id`와 `brand`를 반영한다. 질문·답변 full-text index는 실제 검색 요구가 생긴 뒤 추가한다.

## 4. 적재 규칙

<!-- upsert는 데이터가 없으면 insert하고, 이미 있으면 update하는 처리다. 같은 hash면 skip한다. -->

### 차량정보

<!-- 차량은 source_id + car_id로 찾고, record_hash가 같으면 변경 없음으로 판단한다. -->

- `source_id + car_id`가 같으면 같은 차량으로 보고 MySQL upsert한다.
- 같은 `record_hash`면 `skipped`로 처리한다.
- hash가 달라지면 목록 field를 갱신한다.
- 필수값 검사에 실패한 record는 `car_listing`에 넣지 않는다.
- `listing_number`가 중복이면 적재 전에 오류로 처리한다.

### FAQ

<!-- FAQ는 source_id + faq_id로 찾고, content_hash가 같으면 변경 없음으로 판단한다. -->

- `source_id + faq_id`를 unique key로 사용한다.
- 같은 `content_hash`면 `skipped`로 처리한다.
- hash가 달라지면 같은 FAQ document를 update한다.
- 기업명이 변경되면 source가 제공하는 최신 `brand_id`와 `brand`를 반영한다.
- 질문·답변·공식 source URL·확인일이 없는 document는 적재하지 않는다.

## 5. 예시

<!-- 아래 예시는 설계한 표준 필드가 실제 한 건의 차량 record와 FAQ document로 표현되는 형태다. -->

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
  "region": "광주광역시",
  "base_region": "북구",
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
  "brand_id": "hyundai",
  "brand": "현대",
  "category": "고객지원",
  "question": "FAQ 질문 heading",
  "answer": "FAQ 답변 paragraph",
  "source_url": "<official-source-url>",
  "source_checked_at": "2026-08-11"
}
```

## 6. Day21 확인 범위

<!-- Day21 1일차에는 전체 수집이 아니라 차량 1건·FAQ 1건으로 전처리와 샘플 적재 경로만 확인한다. -->

1. 차량 HTML/API 한 건을 받아 전처리 후 MySQL `car_listing`에 적재한다.
2. FAQ HTML 한 건을 받아 전처리 후 MongoDB `brand_faq`에 적재한다.
3. 차량·FAQ 각각의 필수값과 중복 key를 검사한다.
4. 같은 sample을 다시 실행해 차량과 FAQ가 중복되지 않는지 확인한다.
