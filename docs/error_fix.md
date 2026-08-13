# HTML 수집 방식 변경 기록

## 기존 문제

기존 방식은 웹 화면의 HTML 목록을 수집했다.

웹 화면에서 이동할 수 있는 페이지가 500페이지까지였고, 한 페이지에 차량 20건이 표시되었다.

```text
500페이지 × 20건 = 최대 10,000건
```

서버에 10,000건보다 많은 차량이 있어도 웹 화면 방식으로는 나머지 데이터를 가져올 수 없었다.

## 변경한 방식

차량 목록 API를 직접 호출하는 방식으로 변경했다.

```text
공개 키 API에서 API 키 확인
→ /api/v1/cars 호출
→ JSON data에서 차량 목록 확인
→ MySQL 적재
→ links.next가 있으면 다음 페이지 호출
```

API가 제공하는 다음 페이지 주소를 계속 사용하므로 HTML 화면의 500페이지 제한을 기준으로 종료하지 않는다.

## 실제 코드 변경 부분

### API 주소 설정 추가

```python
PUBLIC_KEY_PATH = "/api/v1/public-key"
CARS_PATH = "/api/v1/cars"
```

### API 키를 받아 요청에 사용

```python
api_key = get_api_key()

requests.get(
    url,
    headers={"X-API-Key": api_key},
    timeout=REQUEST_TIMEOUT,
)
```

### API JSON에서 차량과 다음 주소 추출

```python
cars = payload.get("data")
next_url = get_next_url(payload)
```

### 다음 페이지가 없을 때까지 반복

```python
while next_url:
    payload = fetch_page(next_url, api_key, is_first_page)
    cars = get_cars(payload)
    insert_cars(cars)
    next_url = get_next_url(payload)
```

## 실행 설정

현재 코드는 먼저 한 건을 확인하도록 설정되어 있다.

```python
PAGE_SIZE = 1
MAX_PAGES = 1
```

전체 데이터를 적재할 때는 다음 설정을 사용한다.

```python
PAGE_SIZE = 100
MAX_PAGES = 0
```

전체 적재는 API가 더 이상 `links.next`를 주지 않을 때 종료된다.
