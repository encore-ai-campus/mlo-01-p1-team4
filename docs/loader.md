# loader.py

## 역할

크롤러가 받은 차량 JSON을 MySQL `project1.car_listing` 테이블에 맞게 바꾸고 저장한다.

```text
원본 차량 JSON → normalize_car() → validate_car() → save_cars() → MySQL
```

## 필드 변환

```text
id                    → car_id
location.province     → region
location.city         → sub_region
brand.name            → brand
modelYear             → model_year
fuelType              → fuel_type
mileageKm             → mileage_km
price                 → price_krw
status                → status
firstRegistration     → registration_date
```

## 함수 흐름

### `normalize_car(raw)`

API 원본에서 필요한 값만 꺼낸다.
필드 이름을 MySQL 컬럼명으로 바꾸고, 숫자와 날짜 형식도 변환한다.

### `validate_car(car)`

필수값이 비어 있는지 확인한다.
`status`는 `AVAILABLE`, `RESERVED`, `SOLD` 중 하나인지 확인한다.

### `connect_mysql()`

`db_config.py`의 `DB_CONFIG`를 가져와 MySQL에 연결한다.

```python
return mysql.connect(**DB_CONFIG)
```

### `count_car_listings()`

`car_listing` 테이블의 전체 행 수를 반환한다.
크롤러가 신규 적재 건수를 계산할 때 사용한다.

### `car_values(car)`

정제된 차량 dictionary를 SQL에 넣을 tuple 순서로 바꾼다.

### `save_cars(cars)`

차량 목록을 한 번에 저장한다.
모두 성공하면 `commit()`하고, 중간에 오류가 나면 `rollback()`한다.

### `insert_cars(raw_cars)`

크롤러가 직접 호출하는 함수다.
각 차량을 정제하고 검증한 뒤 `save_cars()`로 보낸다.

## 중복 처리

`car_id`가 이미 있으면 `ON DUPLICATE KEY UPDATE`가 실행된다.

```text
새 car_id       → INSERT
기존 car_id     → 기존 차량 정보 UPDATE
```

따라서 `insert_cars()`의 반환값은 새로 추가된 행 수가 아니라 처리한 차량 수다.
실제 신규 적재 수는 크롤러가 실행 전후 테이블 개수로 계산한다.

## 데이터베이스 설정

DB 접속 정보는 `src/db_config.py`에서 관리한다.
환경변수를 직접 읽는 방식이 아니라 `DB_CONFIG` dictionary를 사용한다.
