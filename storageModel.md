# MySQL·MongoDB 저장소 설계 표준

> 이 문서는 고객 주제와 무관한 저장소 부모 표준이다.
> 자동차 등록 데이터는 MySQL 자식 사례, 기업 FAQ는 MongoDB 자식 사례로 적용한다.

## 1. 목적

고객 데이터의 구조와 조회 목적에 따라 저장소를 선택하고, 원본 보존·정제 데이터·실행 metadata·index·upsert 정책을 일관되게 설계한다.

## 2. 저장소 선택 기준

| 질문 | MySQL | MongoDB |
|---|---|---|
| 데이터 구조 | 정형·컬럼이 안정적 | 문서·필드가 유동적 |
| 주요 조회 | 기간·지역·분류 집계, join | 문서 단위 검색, category/filter |
| 무결성 | primary key·unique·foreign key | document validation·unique index |
| 대표 사례 | 통계·거래·측정값 | FAQ·상품 설명·문서 |

저장소는 주제 이름이 아니라 **데이터 구조와 query pattern**으로 결정한다.

## 3. 공통 저장 계층

```text
raw/staging
    ↓
canonical/core
    ↓
serving/mart
    ↓
query·dashboard·report
```

- `raw/staging`: 원본 snapshot과 source metadata를 보존한다.
- `canonical/core`: 정제·표준화된 record를 저장한다.
- `serving/mart`: 대시보드와 업무 조회에 최적화된 결과를 저장한다.
- 모든 계층은 `source_id`, `run_id`, `schema_version`으로 추적한다.

## 4. 공통 metadata contract

모든 저장 record 또는 연결된 실행 record는 다음 정보를 추적할 수 있어야 한다.

| field | 목적 |
|---|---|
| `source_id` | 원본 출처 식별 |
| `run_id` | 실행 단위 추적 |
| `schema_version` | 구조 변경 추적 |
| `record_hash` | 내용 변경·중복 감지 |
| `collected_at` | 수집 시각 |
| `ingested_at` | 적재 시각 |
| `quality_status` | pass·reject·quarantine 판정 |

## 5. MySQL 부모 표준

### 5.1 테이블 설계 규칙

- 테이블 이름은 업무 의미가 드러나도록 정한다.
- 한 행의 grain을 문서로 먼저 고정한다.
- primary key 또는 업무 unique key를 정의한다.
- 기간·source·business key에 필요한 index를 설계한다.
- 원본 표기값과 분석용 타입을 구분한다.
- 적재는 insert만 사용하지 않고 idempotent upsert를 지원한다.
- 합계·파생값을 상세값과 중복 집계하지 않도록 구분한다.

### 5.2 일반적인 관계

```text
source
  1 ─── N ingestion_run
              1 ─── N canonical_record
              1 ─── N quality_result
```

`source`는 출처, `ingestion_run`은 실행, `canonical_record`는 정제 결과, `quality_result`는 검사 결과를 의미한다.

### 5.3 DDL 작성 순서

1. table grain 결정
2. column·type·nullable 결정
3. primary/unique key 결정
4. index와 query pattern 결정
5. source·run metadata 연결
6. insert/update/reject 결과 정의

## 6. MongoDB 부모 표준

### 6.1 document 설계 규칙

- document 하나가 무엇을 의미하는지 정의한다.
- 자주 함께 읽는 값은 같은 document에 둔다.
- 무한히 커지는 배열은 분리한다.
- `record_hash`, source, fetched_at을 보존한다.
- schema가 바뀌면 `schema_version`을 기록한다.
- query pattern을 먼저 정하고 index를 만든다.

### 6.2 일반 document envelope

```json
{
  "record_id": "<stable-id>",
  "source_id": "<source>",
  "run_id": "<run>",
  "schema_version": "v1",
  "record_hash": "<hash>",
  "quality_status": "pass",
  "payload": {},
  "collected_at": "<ISO-8601>",
  "ingested_at": "<ISO-8601>"
}
```

### 6.3 index 설계 순서

1. 실제 query pattern을 목록화한다.
2. equality filter와 sort 조건을 확인한다.
3. unique field를 정한다.
4. compound index를 만든다.
5. explain 결과와 중복·누락을 evidence로 남긴다.

## 7. 자동차 등록 데이터 자식 사례: MySQL

자동차 데이터는 기간·지역·차종·용도별 집계가 핵심이므로 MySQL 자식 사례로 설계한다.

```text
vehicle_registration_fact
  grain: period + region + vehicle_type + usage_type
  key: period_month, sido_name, sigungu_name,
       vehicle_type, usage_type
  measure: registered_count
```

권장 query pattern:

- 기준월·시도·시군구별 등록대수
- 차종·용도별 합계
- 기간별 증감률
- source와 run별 적재 건수

원본의 `계`·`총계`는 상세 행과 중복될 수 있으므로 `row_type` 또는 별도 aggregate 정책을 자식 contract에서 확정한다.

## 8. 기업 FAQ 자식 사례: MongoDB

FAQ는 문서 단위 조회와 기업·category 검색이 핵심이므로 MongoDB 자식 사례로 설계한다.

```json
{
  "faq_id": "<stable-id>",
  "company": "<company>",
  "category": "<category>",
  "question": "<question>",
  "answer": "<answer>",
  "source_url": "<approved-url>",
  "content_hash": "<hash>",
  "license": "<policy>",
  "attribution": "<attribution>",
  "fetched_at": "<ISO-8601>"
}
```

권장 index/query pattern:

- `company + category` 검색
- `faq_id` unique 검사
- `content_hash` 변경·중복 검사
- source URL별 최신 문서 확인

## 9. 부모 표준을 상속하는 자식 설계 양식

새 고객 주제는 아래 항목만 채워 부모 저장소 표준에 연결한다.

```yaml
child_domain: <topic>
parent_standard: storage-design-standard@v1
data_grain: <one-record-meaning>
source_metadata: [source_id, run_id, schema_version]
target_store: mysql | mongodb
business_key: [<field>]
query_patterns:
  - <query-1>
indexes:
  - <index-1>
upsert_policy: <idempotency-rule>
quality_policy: <quality-contract-reference>
```

## 10. 1일차 설계 완료 기준

- MySQL과 MongoDB 선택 기준을 설명할 수 있다.
- 부모 표준과 자동차·FAQ 자식 사례의 차이를 구분한다.
- 각 자식의 grain·business key·query pattern·index가 정의되어 있다.
- DDL 또는 document schema를 작성할 입력 정보가 준비되어 있다.
