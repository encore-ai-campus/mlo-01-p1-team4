# 수집·전처리·적재 파이프라인 및 데이터 품질 표준

> 이 문서는 특정 주제에 종속되지 않는 부모 표준이다.
> 자동차 등록 데이터와 기업 FAQ는 이 표준을 적용하는 자식 사례다.

## 1. 목적

고객이 어떤 주제와 source를 제공하더라도 같은 실행 구조와 품질 판정 기준으로 데이터를 수집·정제·적재·인계한다. 고객별 차이는 설정, field mapping, business rule로 분리하고 파이프라인의 공통 lifecycle과 관찰 방식을 재사용한다.

## 2. 표준 파이프라인 흐름

```text
요구사항·source contract
        ↓
source config
        ↓
collect
        ↓
raw/staging snapshot
        ↓
transform·normalize
        ↓
quality validate
        ↓
load·upsert
        ↓
query·dashboard·report
        ↓
schedule·log·evidence·handoff
```

### 2.1 단계별 부모 계약

| 단계 | 입력 | 출력 | 반드시 기록할 값 | 실패 처리 |
|---|---|---|---|---|
| `collect` | source config | raw payload 또는 file | source_id, fetched_at, checksum | 허용된 retry 후 중단 |
| `stage` | raw payload | 재현 가능한 snapshot | source_version, raw_count | snapshot 저장 실패로 종료 |
| `transform` | raw snapshot | canonical record | mapping version, transformed_count | 원본 행과 오류 사유 기록 |
| `validate` | canonical record | pass/reject/quarantine | rule별 결과, accepted·rejected count | 실패 record는 load 금지 |
| `load` | pass record | DB upsert 결과 | inserted·updated·skipped count | DB 오류 상태 기록 |
| `publish` | 적재 결과 | query/report/dashboard input | output path, schema version | 산출물 생성 실패 기록 |
| `handoff` | 결과·evidence | 다음 작업자가 재현 가능한 산출물 | job_id, run_id, branch/PR, evidence path | 미완료 link는 open 유지 |

## 3. 고정되는 공통 요소와 고객별 설정

### 3.1 모든 job이 공통으로 가져야 하는 요소

- `job_id`: 실행 업무 식별자
- `source_id`: 원본 source 식별자
- `schema_version`: canonical schema 버전
- `run_id`: 한 번의 실행 식별자
- stage별 상태와 건수
- business key와 중복 방지 정책
- quality result와 sanitized error
- source·license·robots·개인정보 정책 결과

### 3.2 고객별로 설정하는 요소

- source 유형: API, Excel/CSV/JSON, 허용된 web page
- source 위치와 수집 주기
- field mapping과 정규화 규칙
- business key
- 필수 field와 업무별 품질 rule
- target store와 query pattern
- dashboard/report 지표

## 4. 부모 데이터 품질 기준

| 품질 차원 | 공통 판정 기준 | 기본 실패 처리 |
|---|---|---|
| completeness | 필수 field가 비어 있지 않음 | reject |
| validity | 날짜·숫자·enum이 contract와 일치 | reject |
| uniqueness | business key 중복이 0건 | load 중단 또는 quarantine |
| consistency | 같은 record의 관련 값이 서로 모순되지 않음 | reject |
| reconciliation | input = accepted + rejected + skipped | 판정 보류 후 원인 기록 |
| freshness | 요구된 주기와 수집 시각이 일치 | warning 또는 fail |
| provenance | source·수집 시각·schema version 추적 가능 | fail |
| policy | license·robots·allowlist·privacy 위반 없음 | 수집·적재 중단 |

## 5. 상태와 실행 로그

### 5.1 표준 상태

```text
planned → running → succeeded
                  ├→ failed
                  ├→ quarantine
                  └→ skipped
```

`pass`는 품질 rule을 통과했다는 뜻이고, `succeeded`는 전체 실행이 종료됐다는 뜻이다. 두 상태를 같은 의미로 사용하지 않는다.

### 5.2 최소 로그 필드

- `job_id`, `run_id`, `source_id`
- started_at, finished_at
- stage, status, error_code
- input_count, accepted_count, rejected_count, loaded_count
- retry_count
- schema_version, source_version
- sanitized_error
- output_path와 evidence_path

credential·private endpoint·개인정보는 로그에 기록하지 않는다.

## 6. 재실행과 변경 기준

- 같은 input을 다시 실행해도 business row가 중복되지 않아야 한다.
- transport 오류는 제한된 횟수만 retry한다.
- robots·license·schema 경계가 불명확하면 retry나 우회 대신 중단한다.
- source field·business key·품질 rule이 바뀌면 schema version과 change log를 갱신한다.
- 미래 실행의 evidence는 `planned`로 두고 실행 전 `pass`로 바꾸지 않는다.

## 7. 자식 사례 적용 형식

새 주제를 추가할 때 아래 형식으로 부모 표준을 상속한다.

```yaml
child_job_id: <topic-job>
parent_standard: pipeline-quality-standard@v1
source:
  type: api | file | web
  source_id: <approved-source>
  schedule: <trigger>
canonical_schema: <schema-id>@<version>
business_key: [<field-1>, <field-2>]
quality_rules:
  - <common-rule>
  - <topic-specific-rule>
target_store: mysql | mongodb
outputs:
  - <query-or-report>
```

## 8. 자동차 등록 데이터 자식 사례

- source type: 공식 Excel 또는 API
- schedule: monthly
- canonical grain: 기준월·시도·시군구·차종·용도별 측정값
- topic-specific rule: 등록대수 숫자 변환, `계`·`총계` 합계 행 중복 집계 방지
- target store: MySQL
- output: 지역·기간·차종별 집계

자동차의 field mapping과 최종 table은 부모 표준을 바탕으로 별도 child contract에서 확정한다.

## 9. 기업 FAQ 자식 사례

- source type: allowlisted web page
- schedule: weekly 또는 on-demand
- canonical grain: FAQ 문서 1개
- topic-specific rule: 질문·답변·source URL 필수, content hash 중복 검사
- target store: MongoDB
- output: 기업·category별 검색

CAPTCHA·403·429를 우회하지 않으며 license·robots가 확인되지 않은 page는 수집하지 않는다.

## 10. 1일차 설계 완료 기준

- 새로운 주제를 source config와 child contract로 표현할 수 있다.
- 모든 job이 같은 collect→transform→validate→load lifecycle을 사용한다.
- 공통 품질 rule과 주제별 rule을 구분한다.
- 재실행·실패·quarantine·handoff 상태를 로그로 재현할 수 있다.
