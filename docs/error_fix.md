# 차량 수집 방식 변경 기록

## 1. 기존 문제

기존에는 웹 화면 주소인 `/cars`를 기준으로 차량을 수집했다.

웹 화면은 최대 500페이지까지만 제공하고, 한 페이지에 차량 20건이 표시된다.

```text
20건 × 500페이지 = 최대 10,000건
```

따라서 서버에 10만 건 이상의 차량이 있어도 `/cars`를 이용하면 10,000건에서 수집이 끝났다.

`MAX_PAGES = 0`으로 바꾸는 것만으로는 이 문제가 해결되지 않는다.
이 값은 우리 Python 코드의 페이지 수 제한만 없애며, `/cars` 웹 화면의 500페이지 제한까지 없애지는 못한다.

## 2. 변경한 방법

웹 화면 `/cars`가 아니라 차량 API `/api/v1/cars`를 호출하도록 변경했다.

```text
기존: /cars HTML 목록
변경: /api/v1/cars JSON API
```

API 방식에서는 다음 순서로 처리한다.

```text
공개 키 API 호출
→ 차량 API 호출
→ JSON의 data에서 차량 목록 추출
→ MySQL 적재
→ JSON의 links.next 확인
→ 다음 API 주소 반복 호출
```

API 응답에 `links.next`가 있으면 다음 페이지를 요청하고,
`links.next`가 없을 때 수집을 끝낸다.

이제 `/cars`의 HTML 500페이지 제한을 기준으로 수집하지 않는다.

## 3. 실제 코드에서 바뀐 부분

### 차량 목록 주소

```python
PUBLIC_KEY_PATH = "/api/v1/public-key"
CARS_PATH = "/api/v1/cars"
```

차량 API 주소는 다음처럼 만들어진다.

```python
api_source = BASE_URL + CARS_PATH
```

따라서 차량 요청 주소는 다음과 같다.

```text
http://43.203.233.157/api/v1/cars
```

### API 키 사용

```python
api_key = get_api_key()
```

차량 API 요청에 API 키를 넣는다.

```python
response = requests.get(
    url,
    headers={"X-API-Key": api_key},
    timeout=REQUEST_TIMEOUT,
)
```

### HTML 대신 JSON 사용

API 응답의 `data`에서 차량 목록을 가져온다.

```python
cars = payload.get("data")
```

HTML 태그나 웹 화면의 차량 카드를 찾는 방식이 아니다.

### API가 준 다음 주소 사용

```python
next_url = links.get("next")
```

다음 페이지 번호를 직접 만들어 요청하지 않고,
API 응답에 있는 `links.next`를 다음 요청 주소로 사용한다.

```python
while next_url:
    payload = fetch_page(next_url, api_key, is_first_page)
    cars = get_cars(payload)
    insert_cars(cars)
    next_url = get_next_url(payload)
```

## 4. 실행 설정

`PAGE_SIZE`는 한 번의 API 요청에서 받는 차량 수다.
`MAX_PAGES`는 Python 코드가 자체적으로 제한하는 최대 페이지 수다.

```python
PAGE_SIZE = 100
MAX_PAGES = 0
```

이 설정은 API의 `links.next`가 없어질 때까지 API 페이지를 반복 요청한다.

단, 현재 `C:\Project1\config\car_api_crawler.py`의 실제 값이 `MAX_PAGES = 20`이면 20페이지에서 종료한다.
전체 API 순회를 실행할 때는 실제 코드 값도 `0`인지 확인한다.

## 5. 확인 기준

로그의 `api_source`가 다음 주소인지 확인한다.

```text
http://43.203.233.157/api/v1/cars
```

다음처럼 `/cars`만 표시되면 HTML 수집 주소이므로 전체 API 수집 방식이 아니다.

```text
http://43.203.233.157/cars
```

정리하면 이번 수정의 핵심은 `MAX_PAGES` 숫자 변경이 아니라,
10,000건에서 끝나는 `/cars` HTML 수집을 `/api/v1/cars` API 수집으로 바꾼 것이다.
