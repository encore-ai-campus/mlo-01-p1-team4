# 중고차 데이터 저장소 설계

이 문서는 **로컬 서버의 차량과 FAQ를 어떤 구조로 저장하고 조회할지** 정한다.
차량 자체의 정보는 차량 테이블에 모으고, 파이프라인 실행 정보는 데이터 컬럼과 구분해 관리한다.

## 1. 차량 저장 위치

```text
MySQL database: project1
MySQL table: car_listing
차량 1건: table의 1행(row)
```

`row`(테이블의 한 줄)는 차량 매물 한 건을 뜻한다.

## 2. MySQL 테이블

처음에는 아래 SQL을 MySQL Workbench에서 실행한다.

```sql
CREATE DATABASE IF NOT EXISTS project1;
USE project1;

CREATE TABLE IF NOT EXISTS car_listing (
    car_id            INT         PRIMARY KEY,
    region            VARCHAR(50) NOT NULL,
    sub_region        VARCHAR(50) NOT NULL,
    brand             VARCHAR(50) NOT NULL,
    model_year        INT         NOT NULL,
    fuel_type         VARCHAR(30) NOT NULL,
    mileage_km        INT         NOT NULL,
    price_krw         INT         NOT NULL,
    status            VARCHAR(20) NOT NULL,
    registration_date DATE        NOT NULL
);

CREATE INDEX idx_car_search
    ON car_listing (region, sub_region, brand, model_year);
```

### 컬럼 의미

| 컬럼 | 의미 |
|---|---|
| `car_id` | 차량 고유 번호. `PRIMARY KEY`로 중복을 막는다. |
| `model_year` | 연식 |
| `region` | 광역 지역 |
| `sub_region` | 기초 지역 |
| `brand` | 브랜드 |
| `fuel_type` | 연료 |
| `mileage_km` | 주행거리(km) |
| `price_krw` | 가격(원) |
| `status` | 매물 상태 |
| `registration_date` | 차량 등록일 |

`PRIMARY KEY`(행을 구분하는 고유값)는 차량의 `car_id`다. `NOT NULL`(값을 비워둘 수 없음)은 반드시 필요한 컬럼에 적용한다.

## 3. 인덱스와 조회

`idx_car_search`는 지역, 기초지역, 브랜드, 연식 조건으로 자주 조회할 때 사용하는 인덱스다. 인덱스는 검색을 빠르게 할 수 있지만, 많다고 무조건 좋은 것은 아니다.

```sql
SELECT car_id, brand, price_krw
FROM car_listing
WHERE brand = '기아'
  AND region = '인천광역시'
  AND sub_region = '서구'
ORDER BY price_krw ASC;
```

```sql
SELECT car_id, brand, mileage_km, price_krw
FROM car_listing
WHERE price_krw BETWEEN 10000000 AND 20000000
ORDER BY price_krw ASC
LIMIT 10;
```

`WHERE`(조건에 맞는 행 선택), `ORDER BY`(정렬), `LIMIT`(최대 행 수 제한)은 Day16에서 배운 기본 조회 문법이다.

## 4. MongoDB FAQ 구조

FAQ는 MongoDB `brand_faq` collection에 document 하나씩 저장한다.

```javascript
use project1;

db.brand_faq.insertOne({
  _id: "local-faq-001",
  source_id: "local-faq",
  faq_id: "faq-001",
  brand_en: "hyundai",
  brand: "현대",
  category: "보증",
  question: "보증 기간은 어떻게 되나요?",
  answer: "차량별 보증 기준을 확인합니다.",
  source_url: "https://example.com/faq",
  collected_at: "2026-08-11"
});
```

`document`(MongoDB에 저장되는 JSON 모양의 한 건), `collection`(document를 모아두는 공간)이다.

기본 인덱스와 조회는 두 개만 둔다.

```javascript
db.brand_faq.createIndex(
  { source_id: 1, faq_id: 1 },
  { unique: true }
);

db.brand_faq.createIndex(
  { brand_en: 1, brand: 1, category: 1 }
);

db.brand_faq.find(
  { brand: "현대", category: "보증" },
  { _id: 0, question: 1, answer: 1 }
);
```

`unique`(같은 값의 중복을 허용하지 않는 설정)는 FAQ ID에만 적용한다.

## 5. 확인 내용

Day21에서는 다음 네 가지를 순서대로 확인한다.

1. MySQL 테이블이 생성되는가?
2. JSON 차량 1건이 `INSERT`되는가?
3. `SELECT`로 저장된 행을 볼 수 있는가?
4. FAQ document와 두 기본 인덱스를 MongoDB에서 확인할 수 있는가?

저장 구조와 샘플 조회 결과를 확인한 뒤 차량 수집 범위와 실행 주기를 확장할 수 있다.
