# car_api_crawler.py

## 역할

중고차 API에서 차량을 페이지 단위로 받아 `loader.py`에 전달한다.
저장이 끝나면 응답의 다음 페이지 주소를 요청하고, 실행 결과를 로그에 남긴다.

```text
API 요청 → 차량 목록 추출 → loader.py → MySQL car_listing → 로그
```

## 주요 설정

```python
BASE_URL = "http://43.203.233.157"
PUBLIC_KEY_PATH = "/api/v1/public-key"
CARS_PATH = "/api/v1/cars"
PAGE_SIZE = 100
MAX_PAGES = 1
REQUEST_TIMEOUT = 10
REQUEST_INTERVAL = 2
```

- `PAGE_SIZE`: 한 페이지에서 요청할 차량 수
- `MAX_PAGES = 1`: 첫 페이지만 테스트
- `MAX_PAGES = 0`: `next_url`이 없어질 때까지 전체 페이지 요청
- `REQUEST_TIMEOUT`: API 응답을 기다리는 최대 시간(초)
- `REQUEST_INTERVAL`: 다음 페이지 요청 전 대기 시간(초)
- 로그 파일: `src/car_api_crawler.log`

## 실행 흐름

### 1. `get_api_key()`

`/api/v1/public-key`를 요청하고 응답의
`data.current.api_key`를 가져온다.

### 2. `fetch_page()`

API 키를 `X-API-Key` 헤더에 넣어 한 페이지를 요청한다.
첫 요청에는 `sort=newest`와 `page_size=100`을 함께 보낸다.

### 3. `get_cars()`와 `get_next_url()`

- `get_cars()`: 응답의 `data`에서 차량 목록을 꺼낸다.
- `get_next_url()`: 응답의 `links.next`에서 다음 페이지 주소를 꺼낸다.

### 4. `collect_and_save()`

1. 실행 전 `car_listing` 전체 행 수를 확인한다.
2. 현재 페이지를 요청한다.
3. 차량 목록을 `insert_cars()`에 전달한다.
4. 저장에 성공하면 현재 페이지의 처리 결과를 계산한다.
5. 다음 페이지가 있으면 2초 기다린 뒤 요청한다.
6. 실행 후 전체 행 수를 다시 확인한다.

```text
input_count       = API에서 받은 차량 수
processed_count   = loader가 처리한 차량 수
loaded_count      = 실행 전후 전체 행 수 차이
duplicate_count   = processed_count - loaded_count
```

`car_id`가 이미 있으면 `loader.py`의 중복 처리 SQL이 기존 행을 갱신한다.
그래서 `processed_count`와 실제 신규 행 수는 다를 수 있다.

### 5. `main()`

전체 수집을 실행한다.
오류가 발생하면 `NOT_RUN` 로그를 남기고 종료 상태를 실패로 반환한다.

## 로그 예시

```text
mysql_insert=PASS input_count=100 processed_count=100 loaded_count=97 duplicate_count=3
```

## 실행

프로젝트 루트에서 실행한다.

```powershell
python .\src\car_api_crawler.py
```

전체 수집은 한 페이지 테스트가 성공한 뒤 `MAX_PAGES = 0`으로 실행한다.
`MAX_PAGES = 0`이면 API 응답의 `links.next`가 없어질 때까지
다음 페이지를 계속 요청한다.
