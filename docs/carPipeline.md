# 차량정보·FAQ 수집·전처리 파이프라인 (`carPipeline`)

> source: [AutoData Lab](http://192.168.0.51:4000/)  
> 차량 target: MySQL `car_listing`  
> FAQ target: MongoDB `brand_faq`

로컬 서버에서 차량 목록과 브랜드 FAQ를 각각 수집하고, 서로 다른 형태에 맞게 전처리한 뒤 저장한다.

Day21 교안의 원래 자동차 등록 통계 source 대신, 현재 팀 결정에 따라 로컬 서버의 차량 목록을 vehicle source로 사용한다. 따라서 이 문서의 차량 field는 등록 통계의 기준월·지역별 집계 field가 아니라 로컬 목록 field다.

## 0. 1일차 공통 완료선

| 교안 기준 | 현재 프로젝트 반영 |
|---|---|
| source와 수집 범위 확정 | 로컬 `/cars` 차량정보와 `/faqs` FAQ를 source로 고정 |
| 수집·전처리·적재 흐름 | 차량은 MySQL, FAQ는 MongoDB로 분리 |
| 품질검증 | 전처리 전·후 JSON/CSV와 input·accepted·rejected·loaded 건수 비교 |
| 주기 실행 | Day1 smoke는 한 번 실행하고, 이후 cron 또는 APScheduler로 주기 설정 |
| 실행 관리 | run_id, track, stage, 상태, 건수, 오류를 log로 기록 |
| AWS 연결 | 승인된 MySQL/MongoDB target에 소량 sample만 연결 확인 |

Day1에는 전체 차량 수집, FAQ 대량 수집, production 장애조치를 하지 않는다.

필수 산출물은 이 두 설계 문서와 함께 MySQL DDL·ERD, MongoDB document·index·query, 전처리 전·후 CSV/JSON, 품질 결과, README, `requirements.txt`, `.env.example`, 실행 log로 구성한다.

## 1. 수집 source

### 1.1 차량정보

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

FAQ는 로컬 서버의 HTML에서 수집한다. 별도 FAQ API는 사용하지 않는다.

- 시작 주소: `http://192.168.0.51:4000/faqs`
- 브랜드 filter: `/faqs?brand=hyundai`와 같은 query
- FAQ 영역: `[data-faq-brand-group]`
- FAQ 한 건: `article.faq-item`
- 현재 화면: 8개 브랜드 × 브랜드별 3문항 = 총 24문항
- 카드에서 수집할 값: FAQ ID, 브랜드, category, 질문, 답변, 공식 source URL, 공식 자료 확인일
- 원문을 대량 복제하지 않고 로컬 서버의 교육용 질문·답변과 출처 정보만 수집한다.

## 2. Canonical field

### 2.1 차량정보

| 화면 항목 | 저장 field | 예시 |
|---|---|---|
| 번호 | 저장하지 않음 | `1` |
| 제목 | `title` | `2008 기아 레이 트렌디` |
| 매물번호 | `listing_number` | `UC-00094191` |
| 브랜드 | `brand` | `기아` |
| 연식 | `model_year` | `2008` |
| 연료 | `fuel_type` | `가솔린` |
| 소재지 | `location` | `광주광역시 북구` |
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

### 2.2 FAQ

| field | 예시 |
|---|---|
| `faq_id` | `hyundai-support-001` |
| `brand` | `현대` |
| `category` | `고객지원` |
| `question` | FAQ 질문 heading |
| `answer` | FAQ 답변 paragraph |
| `source_url` | 공식 홈페이지 URL |
| `source_checked_at` | `2026-08-11` |
| `content_hash` | 질문·답변·출처 hash |

FAQ business key는 `source_id + faq_id`다. 같은 FAQ의 `content_hash`가 같으면 `skipped`, 달라지면 update한다.

## 3. Pipeline 흐름

```text
차량 HTML/API ──→ raw ──→ 차량 field 전처리 ──→ 품질검사 ──→ MySQL car_listing

FAQ HTML ───────→ raw ──→ FAQ document 전처리 ─→ 품질검사 ──→ MongoDB brand_faq
```

| 단계 | 차량정보 | FAQ |
|---|---|---|
| `collect` | `/cars` HTML 또는 차량 API 요청 | `/faqs` HTML 요청 |
| `stage` | 원본 HTML/JSON 보존 | 원본 FAQ HTML 보존 |
| `transform` | 숫자·가격·날짜·상태 변환 | FAQ ID·브랜드·category·질문·답변·출처 추출 |
| `validate` | 필수값·형식·중복 key 검사 | 필수값·출처·FAQ ID·중복 hash 검사 |
| `load` | MySQL `car_listing` upsert | MongoDB `brand_faq` upsert |

## 4. 품질 기준

### 차량정보

- 필수값: `car_id`, `listing_number`, `title`, `brand`, `model_year`, `mileage_km`, `price_krw`, `status`, `registered_at`
- `model_year`, `mileage_km`, `price_krw`는 숫자 변환에 성공해야 한다.
- `status`는 `AVAILABLE`, `RESERVED`, `SOLD` 중 하나여야 한다.
- 같은 `source_id + car_id`가 한 수집 결과에 중복되면 오류로 처리한다.

### FAQ

- `faq_id`, `brand`, `category`, `question`, `answer`, `source_url`, `source_checked_at`가 있어야 한다.
- 질문 또는 답변이 비어 있으면 적재하지 않는다.
- 공식 source URL이 없으면 적재하지 않는다.
- 같은 `source_id + faq_id`의 hash가 같으면 중복 적재하지 않는다.

## 5. 실행 결과

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

## 6. schedule·log

### schedule

- Day1: `--once` 또는 수동 실행
- 이후: 고객 설정에 따라 cron 또는 APScheduler 사용
- schedule 값과 timezone은 source/환경 설정으로 관리한다.

### log

```text
run_id
track: vehicle | faq
stage: collect | transform | validate | load
status: running | success | failed
input_count
accepted_count
rejected_count
loaded_count
error_code
started_at
finished_at
```

API key와 credential은 log에 기록하지 않는다.
