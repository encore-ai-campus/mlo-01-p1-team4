# BRD · 자동차 등록·FAQ 데이터 파이프라인

> starter_id: `encore.chapter1.brd-prd-requirements-workshop.starter`  
> starter_version: `v1`  
> 작성 규칙: `<TODO>`만 채우고 실제 credential·private endpoint·개인정보는 쓰지 않는다.

- document_id: `BRD-VF-001`
- version: `v1`
- document_state: `Draft`
- owner_role: `<Product Manager>`
- reviewer_roles: [`<Tech Lead ,Engineering,Manager,Designer>`]
- baseline_date: `2026-08-11`
- provenance: `사용자 제공 자동차 등록·기업 FAQ 수행계획을 우선하고, 과정 PDF의 일반 24시간 프로젝트 계약 및 기존 prj/1st 버전과의 차이는 docs/change-log.md에 기록한다.`

## 1. 배경과 현재 문제

월별 자동차 통계와 FAQ가 서로 다른 파일과 정리 방식으로 관리되어 동일 기준월의 결과를 다시 확인하거나 비교하기 어려운 문제가 있으며 데이터 출처와 수집 시점, 정제 여부의 대한 성공 여부가 데이터베이스에 남지 않아 데이터 적재 오류 발생 시 원인을 확인하고 재현하는 데 있어서 리소스가 많이 투입됩니다. 또한 담당자 교체가 될 경우 이력 추적 또한 어려워 업무 이관 및 인수인계 문제가 존재합니다.

## 2. 이해관계자와 필요한 결과

| ID | 이해관계자 | 필요한 업무 결과 |
|---|---|---|
| `STK-AN-001` | 분석 담당자 | 기준월·지역·차종별 자동차 결과와 출처를 함께 확인한다. |
| `STK-FAQ-001` | FAQ 사용자 | 회사·category별 질문·답변과 출처를 함께 확인한다. |
| `STK-OPS-001` | pipeline 운영자 | 실패 지점과 안전한 재실행 필요 여부를 판정한다. |
| `STK-AUD-001` | 검토자 | source·품질·처리 결과를 evidence로 감사한다. |

## 3. 업무 목표와 측정 방법

| ID | 업무 목표 | 측정 방법 |
|---|---|---|
| `BR-OBJ-001` | 분석 담당자가 자동차 결과와 출처를 함께 확인한다. | 기준월·지역·차종별 결과 및 식별자가 모두 존재하면 `PASS`, 하나라도 없으면 `FAIL` |
| `BR-OBJ-002` | FAQ 사용자가 질문·답변과 출처를 함께 확인한다. | 허용된 각 FAQ page의 질문·답변·source 식별자가 모두 존재하면 `PASS`, 하나라도 없으면 `FAIL` |
| `BR-OBJ-003` | 운영 담당자가 재실행 필요 여부와 실패 지점을 판단한다. | 운영 시나리오에서 두 판정 근거가 모두 보인다. |
| `BR-OBJ-004` | 검토자가 데이터와 실행의 출처·처리 결과를 감사한다. | 검토 시나리오의 근거 항목 누락이 0건이다. |

## 4. In scope

- `BR-SCOPE-001`: 승인된 자동차 기준월 1개를 수집·정제·저장·조회한다.
- `BR-SCOPE-002`: allowlist FAQ page 최대 2개를 제한 수집·정제·저장·조회한다.
- `BR-SCOPE-003`: 한 번 실행, 안전한 재실행, 예약 1회와 sanitized evidence를 검증한다.
- `BR-SCOPE-004`: 작은 `output/sample/dashboard.json` 인계 snapshot을 만든다.

## 5. Out of scope

- `BR-OOS-001`: 차량번호·차대번호·소유자·연락처 같은 개인정보
- `BR-OOS-002`: 로그인·CAPTCHA 뒤 콘텐츠와 robots·403·429 우회
- `BR-OOS-003`: 웹 dashboard·UI 개발·배포와 ML 모델
- `BR-OOS-004`: production HA·DR·자동 failover·CI/CD

## 6. 업무 규칙·제약·가정

- `BR-CON-001`: 수행계획에서 지정한 MySQL·MongoDB 저장 요구를 충족한다.
- `BR-CON-002`: 실제 key·credential·private endpoint는 문서와 Git에 기록하지 않는다.
- `BR-CON-003`: live source 승인 여부와 무관하게 official-shape fixture로 Must do를 재현한다.
- `BR-ASM-001`: starter v1을 제공하고 본편 100~150분에 source registry의 owner·범위·fallback을 검증한다.

## 7. 위험·대응·미결 질문

| ID | 발생 조건 | 영향 | 대응 | owner | 상태 |
|---|---|---|---|---|---|
| `BR-RISK-001` | API key 승인 지연 | live 수집 불가 | official-shape fixture 또는 승인 XLSX 사용 | open |
| `BR-RISK-002` | robots·license·schema 변경 | 수집·재배포 경계 불명확 | write 없이 중단하고 변경 검토 | open |
| `BR-OQ-001` | live source의 최종 승인 여부와 승인 책임자는 누구인가? | 실제 수집 경로와 검증 일정 확정 지연 | fixture로 Must do를 진행하고 본편 시작 전 승인 여부와 책임자를 확정한다. | `프로젝트 책임자` | open |

## 8. 검토 기록과 변경 원칙

| reviewed_at | reviewer_role | review_result | note |
|---|---|---|---|
| `2026-08-11` | `Product Manager` | `PASS | FAIL` | `초안 작성 완료; 협의 후 내용 확정` |

- peer review가 끝나면 `document_state: Baselined`로 바꾼다.
- baseline 뒤 요구 의미 변경은 `docs/change-log.md` 한 곳에 기록한다.
- 실제 회사의 경영진 승인을 받지 않았다면 승인 서명을 꾸미지 않는다.
