# 중고차 API 데이터 파이프라인

이 문서는 현재 Git 프로젝트의 `src/car_api_crawler.py`와 `src/loader.py`가
실제로 수행하는 차량 수집·전처리·MySQL 적재 흐름을 설명한다.

## 1. 전체 흐름

```text
공개 키 API
  → 차량 목록 API 페이지 요청
  → 응답 data에서 차량 목록 추출
  → loader.py에서 필드 변환·검증
  → MySQL car_listing upsert
  → 실행 전후 행 개수 비교
  → 로그 기록
  → links.next 또는 crawl.next가 있으면 다음 페이지 처리
```

차량 수집의 실행 파일은 `src/car_api_crawler.py`다. `src/loader.py`는
크롤러가 전달한 차량 목록을 정리하고 저장하며, 단독 CLI 프로그램으로
사용하는 구조는 아니다.

## 2. API 입력

```python
BASE_URL = "http://192.168.0.51:4000"
PUBLIC_KEY_PATH = "/api/v1/public-key"
CARS_PATH = "/api/v1/cars"
PAGE_SIZE = 20
MAX_PAGES = 0
```

- `/api/v1/public-key`에서 `data.current.api_key`를 가져온다.
- 차량 API 요청에는 `X-API-Key` header를 사용한다.
- 첫 페이지에는 `sort=newest`, `page_size=20`을 보낸다.
- 응답의 차량 목록은 `payload.data`에서 가져온다.
- 다음 페이지는 `payload.links.next` 또는 `payload.crawl.next`를 사용한다.
- `MAX_PAGES=0`이면
  다음 페이지가 없을 때까지 처리한다.

## 3. 원본 필드와 MySQL 컬럼

| API 원본 | MySQL 컬럼 |
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

연식·주행거리·가격은 정수로 변환하고, 등록일은 `DATE` 값으로 변환한다.
`status`는 `AVAILABLE`, `RESERVED`, `SOLD`만 허용한다.

## 4. 처리 단계

1. `car_api_crawler.py`가 공개 키를 받고 차량 페이지를 요청한다.
2. `get_cars()`가 응답의 `data` 목록을 꺼낸다.
3. `insert_cars()`가 각 차량을 `normalize_car()`로 변환한다.
4. `validate_car()`가 필수값과 상태값을 검사한다.
5. 검사를 통과한 차량을 한 transaction으로 MySQL에 저장한다.
6. 저장 중 오류가 발생하면 해당 transaction을 rollback한다.
7. 저장 성공 후에만 `links.next` 또는 `crawl.next`를 확인해 다음 페이지로 이동한다.

## 5. 실행

프로젝트 루트에서 실행한다.

```powershell
python -m pip install -r .\src\requirements.txt

$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_DATABASE="project1"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="실제 비밀번호"

python .\src\car_api_crawler.py
```

테이블은 먼저 `sql/project1_schema.sql`을 실행해 만든다.

품질 검증은 다음 명령으로 실행한다.

```powershell
python .\src\vehicle_quality.py
```

검증 결과는 프로젝트 루트의 `quality_check_output` 아래에 저장된다.

## 6. 중복 처리와 실행 결과

`car_id`는 `car_listing`의 기본키다. 같은 `car_id`가 다시 들어오면
`ON DUPLICATE KEY UPDATE`로 기존 행을 갱신한다.

페이지 로그 기준:

```text
input_count       = 현재 API 페이지에서 받은 차량 수
processed_count   = 현재 페이지에서 변환·검증·저장한 차량 수
loaded_count      = 실행 시작 이후 신규 INSERT 누적 수
duplicate_count   = 실행 시작 이후 기존 car_id 처리 누적 수
```

전체 실행 로그는 다음 필드를 사용한다.

```text
total_input       = 전체 페이지에서 받은 차량 수
total_processed   = 전체 페이지에서 처리한 차량 수
loaded_count      = 실행 후 전체 행 수 - 실행 전 전체 행 수
duplicate_count   = total_processed - loaded_count
```

실행 전후 행 개수 비교는 같은 시간에 다른 작업이 `car_listing`에
INSERT 또는 DELETE하지 않는다는 전제에서 사용한다.

## 7. FAQ 저장 구조

FAQ 수집·MongoDB 적재는 차량 Python 크롤러와 별도 담당이다. FAQ는
`brand_faq` collection에 document 한 건씩 저장한다.

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

차량 Python 파이프라인은 차량 API와 MySQL `car_listing`을 처리하고,
FAQ pipeline은 별도 담당으로 유지한다.
