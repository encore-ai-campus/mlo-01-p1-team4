# MySQL 적재 및 중복 처리 기준

## 1. 현재 구조

현재 `loader.py`는 `ON DUPLICATE KEY UPDATE`를 사용한다.

- 새 `car_id`: 신규 INSERT
- 이미 존재하는 `car_id`: 기존 행 UPDATE

따라서 `loader.py`가 반환하는 처리 건수만으로는 신규 INSERT와 기존
데이터 UPDATE를 구분할 수 없다.

## 2. 실행 전후 개수 비교

현재 크롤러는 한 번의 실행을 기준으로 다음 순서로 개수를 확인한다.

```text
실행 전 car_listing 전체 개수 확인
→ API 페이지 수집
→ 페이지별 MySQL upsert
→ 페이지 저장 후 현재 전체 개수 확인
→ 모든 페이지 처리
→ 실행 후 car_listing 전체 개수 확인
→ 실행 전후 차이와 처리 건수 계산
```

이 방식은 실행 중 다른 작업이 `car_listing`에 INSERT 또는 DELETE하지
않는다는 전제에서 사용한다.

## 3. 로그 건수 기준

페이지 로그:

```text
input_count       = 현재 페이지에서 API가 받은 차량 수
processed_count   = 현재 페이지에서 처리한 차량 수
loaded_count      = 현재 페이지까지 신규 INSERT 누적 수
duplicate_count   = 현재 페이지까지 기존 car_id 처리 누적 수
```

전체 실행 로그:

```text
total_input       = 전체 API 입력 차량 수
total_processed   = 전체 처리 차량 수
loaded_count      = 실행 후 전체 개수 - 실행 전 전체 개수
duplicate_count   = total_processed - loaded_count
```

예시:

```text
실행 전 개수: 100
API 입력·처리: 20
실행 후 개수: 117
```

```text
loaded_count = 17
duplicate_count = 3
```

즉, 20건 중 17건은 신규 INSERT이고 3건은 기존 `car_id`를 UPDATE한
것으로 기록한다.

## 4. 중복 데이터가 있어도 수집을 중단하지 않음

페이지 중간에 기존 `car_id`가 있어도 해당 차량만 UPDATE하고 다음 차량과
다음 페이지를 계속 처리한다. 중복 발견 즉시 종료하면 뒤에 있는 신규
차량을 놓칠 수 있다.

마지막 페이지 여부는 신규 INSERT 수가 아니라 API 응답의
`links.next` 존재 여부로 판단한다.

## 5. 실패 처리

API 수집 또는 MySQL 저장이 중간에 실패하면 정상 실행 결과로 건수 계산을
확정하지 않는다. DB 페이지 저장은 transaction으로 처리하며 오류가 나면
rollback한다.
