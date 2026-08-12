# 1st_error

## 1. 문제

현재 `DUPLICATE KEY UPDATE`를 사용해 중복 `car_id`가 있어도 오류 없이 기존 데이터를 갱신하는 구조임.

`loader.py`가 반환하는 값은 현재 페이지에서 처리한 차량 수임.

따라서 실제 신규 INSERT 건수와 기존 데이터 처리 건수를 구분할 수 없는 문제 발생.

기존 구조에서는 `MAX_PAGES=1`로 20개를 처리한 뒤 바로 다시 실행해도 `loaded_count=20`으로 기록되는 문제 발생.

## 2. 중복 차량 처리 기준

중복 `car_id` 발견 즉시 크롤러를 종료하는 방식은 사용하지 않을 것.

중간에 기존 차량이 있으면 그 뒤의 신규 차량까지 수집하지 못하는 문제 발생.

`DUPLICATE KEY UPDATE`는 유지할 것.

중복 여부와 신규 적재 수는 크롤러 1회 실행 전후의 전체 `car_listing` 행 개수로 계산할 것.

## 3. 전체 개수 비교 흐름

최종 신규 적재 수는 크롤러 실행 전후의 전체 `car_listing` 행 개수로 계산할 것.
페이지 처리 후에는 현재 전체 행 개수를 확인해 페이지 로그에 누적 결과를 기록할 것.

```text
실행 전 car_listing 전체 개수 확인
→ API 차량 데이터 수집
→ 페이지별 MySQL 적재
→ 현재 전체 행 개수 확인 및 페이지 로그 기록
→ 모든 수집과 적재 완료
→ 실행 후 car_listing 전체 개수 확인
→ 실행 전후 개수 차이 계산
```

실행 전후 다른 작업이 `car_listing`에 INSERT 또는 DELETE를 하지 않는다는 전제 필요.

## 4. 개수 기준

```text
input_count = 현재 페이지에서 API가 받은 차량 수
processed_count = 현재 페이지에서 처리한 차량 수
loaded_count = 실행 시작 후 새로 INSERT된 누적 차량 수
duplicate_count = 실행 시작 후 기존 car_id로 처리된 누적 차량 수
```

계산식:

```text
loaded_count = 실행 후 전체 개수 - 실행 전 전체 개수
duplicate_count = processed_count - loaded_count
```

`processed_count`는 `loader.py`가 반환하는 처리 건수로 기록할 것.

`loaded_count`는 실행 전후 `car_listing` 전체 행 개수 차이로 계산할 것.

`duplicate_count`는 처리 건수에서 신규 적재 건수를 뺀 값으로 계산할 것.

페이지 로그의 필드 순서는 다음과 같이 기록할 것.

```text
input_count → processed_count → loaded_count → duplicate_count
```

페이지 로그의 `loaded_count`와 `duplicate_count`는 해당 페이지까지의 실행 누적값임.

## 5. 실행 예시

```text
실행 전 car_listing 개수: 100
API에서 받은 차량 수: 20
실행 후 car_listing 개수: 117
```

결과:

```text
input_count = 20
processed_count = 20
loaded_count = 17
duplicate_count = 3
```

의미:

```text
API에서 받은 20개 중 17개는 신규 INSERT
3개는 기존 데이터라 UPDATE 처리
```

## 6. 실행 결과 확인

크롤러가 모든 페이지의 수집과 적재를 완료한 뒤 실행 후 전체 개수를 확인할 것.

API 수집 또는 MySQL 적재가 중간에 실패하면 정상 실행 결과로 계산하지 않을 것.

실패한 경우 로그의 오류 내용을 먼저 확인할 것.

API 응답의 `next_url`은 다음 페이지 존재 여부를 판단하는 값임.

신규 데이터 개수는 실행 전후 `car_listing` 전체 행 개수 차이로 판단할 것.

크롤러는 크론탭에서 정해진 주기로 실행할 것.

## 7. 평가

실행 전후 전체 개수 비교 방식: 8점 / 10점

현재 프로젝트 수준에서 구현하기 쉽고 이해하기 쉬운 방식임.
