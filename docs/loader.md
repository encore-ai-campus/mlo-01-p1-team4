# loader.py 메모

## 역할

`src/loader.py`는 크롤러가 전달한 차량 목록을 정리하고 검증한 뒤
`project1.car_listing`에 저장한다.

```text
API 원본 차량
  → normalize_car()
  → validate_car()
  → save_cars()
  → MySQL car_listing upsert
```

실행의 시작점은 `src/car_api_crawler.py`이며, `loader.py`는 크롤러에서
함수로 호출된다.

## 필드 변환

```text
id                         → car_id
location.province          → region
location.city              → sub_region
brand.name                 → brand
modelYear                  → model_year
fuelType                   → fuel_type
mileageKm                  → mileage_km
price                      → price_krw
status                     → status
firstRegistration          → registration_date
```

연식·주행거리·가격은 정수로 변환하고 등록일은 `DATE` 값으로 변환한다.
`status`는 `AVAILABLE`, `RESERVED`, `SOLD` 중 하나만 허용한다.

## 저장

`save_cars()`는 페이지의 차량들을 하나의 transaction으로 저장한다.

```python
for car in cars:
    cursor.execute(INSERT_SQL, car_values(car))

connection.commit()
```

`INSERT_SQL`은 `car_id` 기본키가 이미 있으면
`ON DUPLICATE KEY UPDATE`로 기존 행의 차량 정보를 갱신한다.

- 새 `car_id`: INSERT
- 기존 `car_id`: UPDATE
- 중간 오류: 해당 페이지 transaction rollback

`insert_cars()`의 반환값은 신규 INSERT 수가 아니라 검증과 저장이 끝난
현재 페이지의 처리 차량 수다. 신규 INSERT 수와 중복 처리 수는 크롤러가
실행 전후 테이블 개수로 계산한다.

## DB 연결

DB 접속 정보는 다음 환경변수를 사용한다.

```text
MYSQL_HOST
MYSQL_PORT
MYSQL_DATABASE
MYSQL_USER
MYSQL_PASSWORD
```

## 테이블과 개수 확인

테이블 생성 SQL은 `sql/project1_schema.sql`에 있다.

`count_car_listings()`는 다음 쿼리로 현재 행 개수를 확인한다.

```sql
SELECT COUNT(*) FROM car_listing;
```

크롤러는 이 값을 사용해 다음 결과를 계산한다.

```text
loaded_count = 실행 후 전체 행 개수 - 실행 전 전체 행 개수
duplicate_count = total_processed - loaded_count
```

## 오류 처리

차량 필수값 또는 상태값 검증에 실패하면 저장하지 않고 오류를 발생시킨다.
DB 저장 중 오류가 나면 rollback한 뒤 크롤러에 오류를 전달하고, 크롤러가
실행 로그를 남긴다.
