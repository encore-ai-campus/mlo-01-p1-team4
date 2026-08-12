# 차량정보·FAQ 수집·전처리 파이프라인 (`carPipeline`)

<!--
이 문서는 실행 코드가 아니라 수집부터 DB 적재까지의 처리 규칙을 정의하는 설계 문서다.
차량과 FAQ를 각각 어떤 source에서 가져오고, 어떤 표준 필드로 변환하고,
어떤 품질검사를 거쳐 어느 저장소에 넣을지 설명한다.
-->

> source: [AutoData Lab](http://192.168.0.51:4000/)  
> 차량 target: MySQL `car_listing`  
> FAQ target: MongoDB `brand_faq`

<!-- source는 데이터 출처, target은 전처리 후 데이터가 도착하는 최종 저장소를 뜻한다. -->

로컬 서버에서 차량 목록과 브랜드 FAQ를 각각 수집하고, 서로 다른 형태에 맞게 전처리한 뒤 저장한다.

Day21 교안의 원래 자동차 등록 통계 source 대신, 현재 팀 결정에 따라 로컬 서버의 차량 목록을 vehicle source로 사용한다. 따라서 이 문서의 차량 field는 등록 통계의 기준월·지역별 집계 field가 아니라 로컬 목록 field다.

## 1. 수집 source

<!--
이 절은 실제 수집 대상과 수집 방법을 고정한다.
차량은 /cars의 HTML/API, FAQ는 /faqs의 HTML을 기준으로 한다.
-->

### 1.1 차량정보

<!-- CSS 선택자는 HTML에서 차량 카드와 필드를 찾는 규칙이다. API를 사용할 때는 응답의 data와 links.next를 기준으로 페이지를 이어간다. -->

HTML 목록과 차량 API를 사용한다.

- HTML 시작 주소: `http://192.168.0.51:4000/cars?page=1&page_size=20`
- 차량 card: `article.car-card[data-car-id]`
- card field: `[data-field]`
- 다음 HTML page: `a[rel=next]`의 `href`
- 공개 키: `GET /api/v1/public-key`
- 차량 목록 API: `GET /api/v1/cars`
- cursor API: `GET /api/v1/cars/cursor?after_id=0&limit=100`
- API 응답: `data`, `meta`, `links`, `links.next`
- API 인증: 공개 키를 받은 뒤 `X-API-Key` header 사용
- cursor 순회: `after_id`를 직접 계산하지 않고 `links.next`를 그대로 사용
- API key: 파일·DB·log에 저장하지 않음

### 1.2 FAQ

<!-- FAQ는 질문·답변뿐 아니라 브랜드, 카테고리, 공식 출처와 확인일도 함께 수집해 나중에 출처를 추적할 수 있게 한다. -->

FAQ는 로컬 서버의 HTML에서 수집한다. 별도 FAQ API는 사용하지 않는다.

- 시작 주소: `http://192.168.0.51:4000/faqs`
- 브랜드 filter: `/faqs?brand=hyundai`와 같은 query의 값을 `brand_id`로 사용
- FAQ 영역: `[data-faq-brand-group]`
- FAQ 한 건: `article.faq-item`
- 현재 화면: 8개 브랜드 × 브랜드별 3문항 = 총 24문항
- 카드에서 수집할 값: FAQ ID, source 제공 brand_id, 브랜드명, category, 질문, 답변, 공식 source URL, 공식 자료 확인일
- 원문을 대량 복제하지 않고 로컬 서버의 교육용 질문·답변과 출처 정보만 수집한다.

## 2. Canonical field

<!--
Canonical field는 원본의 서로 다른 필드명을 우리 시스템의 표준 이름으로 통일한 값이다.
예를 들어 modelYear는 model_year로, 202,142km는 202142로 변환한다.
-->

### 2.1 차량정보

<!-- car_id는 차량 식별자이고, 화면의 순번은 페이지가 바뀌면 달라지므로 식별자로 사용하지 않는다. -->

| 화면 항목 | 저장 field | 예시 |
|---|---|---|
| 번호 | 저장하지 않음 | `1` |
| 제목 | `title` | `2008 기아 레이 트렌디` |
| 매물번호 | `listing_number` | `UC-00094191` |
| 브랜드 | `brand` | `기아` |
| 연식 | `model_year` | `2008` |
| 연료 | `fuel_type` | `가솔린` |
| 지역 | `region` | `광주광역시` |
| 기초지역 | `base_region` | `북구` |
| 주행거리 | `mileage_km` | `202142` |
| 가격 | `price_krw` | `1500000` |
| 통화 | `currency` | `KRW` |
| 상태 | `status` | `RESERVED` |
| 등록일 | `registered_at` | `2025-08-31` |

식별자 규칙:

- `car_id`: API `id` 또는 HTML `data-car-id`
- `listing_number`: API `listingNumber` 또는 HTML subtitle의 `UC-...`
- business key: `source_id + car_id`
- 화면의 `번호`는 페이지 순번이므로 key로 사용하지 않는다.

값 변환:

- `202,142km` → `202142`
- `1,500,000원` → `1500000`, `currency = KRW`
- `2008년` → `2008`
- `2025. 8. 31.` → `2025-08-31`
- `예약중` → API 상태값 `RESERVED`

지역 변환 규칙:

- `광주광역시 북구` → `region = 광주광역시`, `base_region = 북구`
- `서울특별시 강남구` → `region = 서울특별시`, `base_region = 강남구`

### 2.2 FAQ

<!-- FAQ의 source_id와 faq_id는 문서 식별에 사용하고, content_hash는 질문·답변 내용의 변경 여부를 확인하는 지문이다. -->

| field | 예시 |
|---|---|
| `faq_id` | `hyundai-support-001` |
| `brand_id` | `hyundai` |
| `brand` | `현대` |
| `category` | `고객지원` |
| `question` | FAQ 질문 heading |
| `answer` | FAQ 답변 paragraph |
| `source_url` | 공식 홈페이지 URL |
| `source_checked_at` | `2026-08-11` |
| `content_hash` | 질문·답변·출처 hash |

FAQ business key는 `source_id + faq_id`다. `brand_id`는 source가 제공하는 영문 브랜드 코드이고, `brand`는 표시명이다. 기업명이 변경되면 source가 제공하는 최신 `brand_id`와 `brand`를 반영한다. 같은 FAQ의 `content_hash`가 같으면 `skipped`, 달라지면 update한다.

## 3. Pipeline 흐름

<!--
collect는 수집, stage는 원본 보관, transform은 표준화, validate는 품질검사,
load는 DB 적재 단계다. raw는 원본이고 processed는 변환 결과다.
-->

```text
차량 HTML/API ──→ raw ──→ 차량 field 전처리 ──→ 품질검사 ──→ MySQL car_listing

FAQ HTML ───────→ raw ──→ FAQ document 전처리 ─→ 품질검사 ──→ MongoDB brand_faq
```

| 단계 | 차량정보 | FAQ |
|---|---|---|
| `collect` | `/cars` HTML 또는 차량 API 요청 | `/faqs` HTML 요청 |
| `stage` | 원본 HTML/JSON 보존 | 원본 FAQ HTML 보존 |
| `transform` | 숫자·가격·날짜·상태 변환 | FAQ ID·source brand_id·브랜드명·category·질문·답변·출처 추출 |
| `validate` | 필수값·형식·중복 key 검사 | 필수값·출처·FAQ ID·중복 hash 검사 |
| `load` | MySQL `car_listing` upsert | MongoDB `brand_faq` upsert |

## 4. 품질 기준

<!-- 필수값·자료형·허용 상태·중복 여부를 검사하고, 기준을 통과하지 못한 record는 DB에 넣지 않는다. -->

### 차량정보

- 필수값: `car_id`, `listing_number`, `title`, `brand`, `region`, `base_region`, `model_year`, `mileage_km`, `price_krw`, `status`, `registered_at`
- `model_year`, `mileage_km`, `price_krw`는 숫자 변환에 성공해야 한다.
- `status`는 `AVAILABLE`, `RESERVED`, `SOLD` 중 하나여야 한다.
- 같은 `source_id + car_id`가 한 수집 결과에 중복되면 오류로 처리한다.

### FAQ

- `faq_id`, `brand_id`, `brand`, `category`, `question`, `answer`, `source_url`, `source_checked_at`가 있어야 한다.
- 질문 또는 답변이 비어 있으면 적재하지 않는다.
- 공식 source URL이 없으면 적재하지 않는다.
- 같은 `source_id + faq_id`의 hash가 같으면 중복 적재하지 않는다.

## 5. 실행 결과

<!--
실행 결과의 count는 track(vehicle/faq)별로 기록한다.
input은 입력 수, accepted는 통과 수, rejected는 오류 수,
skipped는 같은 내용이라 건너뛴 수, loaded는 신규 저장 또는 갱신 수다.
-->

한 번의 실행마다 track별로 다음 값을 남긴다.

```text
track: vehicle | faq
run_id
input_count
accepted_count
rejected_count
skipped_count
loaded_count
collected_at
```

Day21 1일차에는 차량 1건과 FAQ 1건 fixture로 차량은 MySQL에, FAQ는 MongoDB에 연결되는지 확인한다. 전체 차량 수집과 FAQ 대량 수집은 오늘 범위가 아니다.
