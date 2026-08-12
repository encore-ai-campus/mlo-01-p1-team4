# 중고차 데이터 파이프라인 설계

이 문서는 **로컬 서버의 중고차 JSON을 MySQL에 저장하는 기본 처리 흐름**을 설명한다.
Python 함수로 데이터를 읽고 정리한 뒤 SQL `INSERT`와 `SELECT`로 저장 결과를 확인한다.

## 1. 처리 범위

```text
JSON 파일
  → 값 정리
  → 필수값 확인
  → MySQL INSERT
  → SELECT로 확인
```

입력은 테스트용 중고차 JSON 한 건으로 시작한다. 처리 결과는 MySQL의 한 행으로 저장하고, 저장 후 `SELECT` 결과로 내용을 확인한다. 같은 `car_id`가 다시 입력되면 `PRIMARY KEY`(고유 식별자) 규칙과 오류 메시지를 통해 중복 여부를 확인한다.

## 2. 입력

입력 파일:

```text
data/fixtures/vehicle_105764.json
```

원본 JSON에서 DB에 필요한 값을 꺼내 표준 컬럼명으로 바꾼다.

| 원본 값 | 저장할 이름 |
|---|---|
| `id` | `car_id` |
| `location.province` | `region` |
| `location.city` | `sub_region` |
| `brand.name` | `brand` |
| `modelYear` | `model_year` |
| `fuelType` | `fuel_type` |
| `mileageKm` | `mileage_km` |
| `price` | `price_krw` |
| `status` | `status` |
| `firstRegistration` | `registration_date` |

`brand.name`처럼 점으로 표시한 값은 JSON 안의 `brand` 객체에서 `name`을 꺼낸다는 뜻이다.

## 3. 처리 단계

### 3.1 읽기

`loader.py`가 JSON 파일을 읽어 Python dictionary(키와 값의 묶음)로 만든다.

### 3.2 정리

원본 필드명을 MySQL 컬럼 이름으로 바꾸고, 연식·주행거리·가격을 정수로 변환한다.

### 3.3 확인

다음 필드를 차량 데이터의 필수값으로 검사한다.

```text
car_id, region, sub_region, brand, model_year,
fuel_type, mileage_km, price_krw, status, registration_date
```

`status`는 `AVAILABLE`, `RESERVED`, `SOLD` 중 하나로 관리한다.

### 3.4 저장

검사를 통과한 차량 한 건을 `car_listing` 테이블에 `INSERT`한다.

`INSERT`(새 행을 추가하는 SQL)로 저장하고 `SELECT`(저장된 행을 조회하는 SQL)로 결과를 확인한다.

## 4. 실행

먼저 패키지를 설치한다.

```powershell
python -m pip install -r requirements.txt
```

DB에 넣기 전에 변환 결과만 확인한다.

```powershell
python .\src\loader.py `
  --input .\data\fixtures\vehicle_105764.json `
  --dry-run
```

실제 적재는 MySQL 접속 환경변수를 설정한 뒤 실행한다.

```powershell
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_DATABASE="project1"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="mysql"

python .\src\loader.py `
  --input .\data\fixtures\vehicle_105764.json
```

비밀번호는 실행할 때 환경변수로 전달한다.

## 5. 결과 확인

실행 결과에서 다음을 확인한다.

```text
input_count   입력 건수
valid_count   검사 통과 건수
rejected_count 검사 실패 건수
loaded_count  INSERT 건수
```

그 다음 MySQL에서 직접 확인한다.

```sql
USE project1;

SELECT car_id, region, sub_region, brand, model_year,
       fuel_type, mileage_km, price_krw, status, registration_date
FROM car_listing;
```

## 6. 수정할 때 보는 곳

필드가 추가되거나 이름이 바뀌면 `loader.py`의 `normalize_car()`와 `INSERT` 문을 함께 수정한다.

테이블 컬럼이 바뀌면 `carStorage.md`의 DDL(테이블 생성 SQL)과 loader의 `INSERT` 문을 같은 순서로 수정한다.

수정 순서는 다음과 같다.

```text
입력 JSON 확인
  → carStorage.md의 컬럼 수정
  → loader.py의 normalize_car 수정
  → INSERT 문 수정
  → SELECT로 확인
```

## 7. FAQ 저장 구조

FAQ는 `brand_faq` collection에 document 한 건씩 저장한다. FAQ document의 기준 필드는 다음과 같다.

| 원본 의미 | 저장할 이름 |
|---|---|
| 식별자 | `_id` |
| source 식별자 | `source_id` |
| FAQ 식별자 | `faq_id` |
| 영문 기업명 | `brand_en` |
| 기업명 | `brand` |
| 카테고리 | `category` |
| 질문 | `question` |
| 답변 | `answer` |
| 원본 링크 | `source_url` |
| 수집일 | `collected_at` |

차량은 `car_listing` 테이블, FAQ는 `brand_faq` collection을 사용한다. 차량 JSON 처리와 FAQ document 처리는 서로 다른 저장 방식에 맞춰 각각의 코드와 절차로 구성한다.
