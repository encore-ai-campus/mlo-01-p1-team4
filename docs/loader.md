# loader.py 메모

## 로컬 비밀번호 재설정법 
nano ~/.project1.env


## 역할
Crawler가 가져온 차량을 정리해서 MySQL에 저장한다.

```text
원본 차량 → 필요한 값 추출 → 값 검사 → MySQL 저장
```
저장 위치는 `project1` 데이터베이스의 `car_listing` 테이블이다.
테이블은 `schema/mysql.sql`로 먼저 만든다.

## 호출
Crawler에서 다음 코드로 시작한다.
```python
loaded_count = insert_cars(cars)
```
`cars`는 API에서 받은 차량 여러 건이다.

## 함수 순서
```text
insert_cars()
→ normalize_car()
→ validate_car()
→ save_cars()
→ MySQL 저장
```

## insert_cars()
차량 목록을 하나씩 처리한다.
```python
for number, raw in enumerate(raw_cars, start=1):
    car = normalize_car(raw)
    errors = validate_car(car)
```
`raw`는 API 원본 한 건이고 `car`는 DB에 넣도록 정리한 한 건이다.
검사를 모두 통과하면 `save_cars(cars)`를 호출한다.

## normalize_car()
API 이름을 DB 이름으로 바꾼다.
```text
id → car_id
location.province → region
location.city → sub_region
brand.name → brand
modelYear → model_year
fuelType → fuel_type
mileageKm → mileage_km
price → price_krw
status → status
firstRegistration → registration_date
```
`brand` 객체에서는 `name`만 꺼낸다.
날짜 문자열은 날짜 값으로 바꾼다.

## validate_car()
DB에 넣기 전에 필수값을 확인한다.
판매 상태는 다음 세 값만 허용한다.
```text
AVAILABLE, RESERVED, SOLD
```
문제가 있으면 저장하지 않고 오류를 발생시킨다.

## save_cars()
MySQL에 연결한 뒤 차량별로 SQL을 실행한다.
```python
connection = connect_mysql()
cursor = connection.cursor()
```
```python
for car in cars:
    cursor.execute(INSERT_SQL, car_values(car))
```
모두 성공하면 `connection.commit()`으로 확정한다.
하나라도 실패하면 `connection.rollback()`으로 이번 페이지 저장을 취소한다.

## 중복 처리
`car_id`는 `car_listing`의 기본키다.
SQL의 `ON DUPLICATE KEY UPDATE`는 다음처럼 작동한다.
```text
새 car_id → INSERT
이미 있는 car_id → UPDATE
```
같은 페이지를 다시 실행해도 중복 행이 생기지 않는다.
내용이 같으면 그대로이고 값이 다르면 최신 값으로 바뀐다.

## 로그 연결
Loader가 저장한 건수를 Crawler에 돌려준다.
```text
input_count=20
loaded_count=20
```
저장 오류가 나면 rollback하고 오류를 Crawler에 전달한다.
그러면 Crawler가 실패 로그를 남긴다.

## 한 줄 정리
loader는 차량을 DB 컬럼에 맞게 정리하고 검사한 뒤 `project1.car_listing`에 저장한다.
