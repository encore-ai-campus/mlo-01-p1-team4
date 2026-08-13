# car_api_crawler.py 메모

## 역할

`src/car_api_crawler.py`는 로컬 중고차 API에서 차량을 페이지 단위로
가져와 `src/loader.py`에 전달하고, MySQL 저장 결과를 로그로 남긴다.

```text
공개 키 → 차량 API → data 목록 → loader.py → MySQL → 로그 → 다음 페이지
```

## 주소와 설정

```python
BASE_URL = "http://192.168.0.51:4000"
PUBLIC_KEY_PATH = "/api/v1/public-key"
CARS_PATH = "/api/v1/cars"
PAGE_SIZE = 20
MAX_PAGES = 0
```

- `PAGE_SIZE`는 한 페이지 요청 건수다.
- `MAX_PAGES`는 처리할 최대 페이지 수다.
- `MAX_PAGES=0`은 API의 다음 페이지가 없어질 때까지 처리한다.
- 로그 파일은 `src/car_api_crawler.log`다.

## API 키

```python
api_key = get_api_key()
```

`get_api_key()`는 `/api/v1/public-key`를 호출하고 응답의
`data.current.api_key` 값을 사용한다. 이 키를 파일·로그에 저장하지 않고
차량 API 요청의 `X-API-Key` header에만 넣는다.

## 페이지 요청

첫 페이지에는 다음 조건을 보낸다.

```python
params = {"sort": "newest", "page_size": PAGE_SIZE}
headers = {"X-API-Key": api_key}
```

첫 페이지 이후에는 API 응답의 다음 주소를 그대로 요청한다.
현재 코드는 `payload.links.next` 또는 `payload.crawl.next`를 읽어 다음 URL을 만든다.

```python
cars = payload.get("data")
next_url = (payload.get("links") or {}).get("next") or (payload.get("crawl") or {}).get("next")
```

차량 목록이 비어 있으면 해당 로그를 남기고 수집을 종료한다.

## 처리와 저장

```python
processed_count = insert_cars(cars)
```

`insert_cars()`는 차량 필드를 정리하고 필수값과 상태값을 검증한 뒤
`ON DUPLICATE KEY UPDATE` 방식으로 MySQL에 저장한다. 반환값은 신규
INSERT 수가 아니라 현재 페이지에서 처리한 차량 수다.

크롤러는 실행 전 `car_listing` 개수를 저장하고, 각 페이지 저장 후와 실행
종료 후 개수를 다시 조회한다.

```text
loaded_count = after_count - before_count
duplicate_count = total_processed - loaded_count
```

## 로그

페이지 로그의 `loaded_count`, `duplicate_count`는 현재 페이지까지의
실행 누적값이다.

```text
mysql_insert=PASS input_count=20 processed_count=20 loaded_count=17 duplicate_count=3
```

전체 실행이 끝나면 다음과 같은 실행 로그를 추가한다.

```text
run_status=PASS total_input=40 total_processed=40 loaded_count=17 duplicate_count=23 before_count=100 after_count=117
```

API 요청 또는 MySQL 저장 중 오류가 나면 `FAIL` 또는 `NOT_RUN` 로그를
남기고 오류를 출력한다.

## 실행

프로젝트 루트에서 다음처럼 실행한다.

```powershell
python .\src\car_api_crawler.py
```
