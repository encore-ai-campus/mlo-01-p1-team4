# car_api_crawler.py 메모

## 역할
로컬 중고차 API에서 차량을 가져와 `loader.py`에 넘긴다.

```text
API 키 → 자동차 API → 차량 목록 → loader → 로그 → 다음 페이지
```

## 실행
```python
if __name__ == "__main__":
    main()
```
파일을 실행하면 `main()`이 실행되고 `collect_and_save()`를 부른다.

## 주소
```python
BASE_URL = "http://192.168.0.51:4000"
PUBLIC_KEY_PATH = "/api/v1/public-key"
CARS_PATH = "/api/v1/cars"
```
```python
api_source = BASE_URL + CARS_PATH
next_url = api_source
```
첫 자동차 API 주소는 `http://192.168.0.51:4000/api/v1/cars`이다.

## API 키
```python
api_key = get_api_key()
```
`get_api_key()`는 `/api/v1/public-key`에서 `data.current.api_key`를 꺼낸다.

## 페이지 요청
```python
payload = fetch_page(next_url, api_key, is_first_page)
```
여기서 `next_url`이 `fetch_page()`의 `url`로 들어간다.
`fetch_page()`는 API 키를 헤더에 넣어 요청한다.
```python
headers={"X-API-Key": api_key}
```
첫 페이지에는 다음 조건을 보낸다.
```python
params = {"sort": "newest", "page_size": PAGE_SIZE}
```
`newest`는 최신 등록순이다.

## 차량 목록
```python
cars = get_cars(payload)
```
`payload`는 API 응답 전체이고, `get_cars()`는 그 안의 `data`만 꺼낸다.
```python
cars = payload.get("data")
```
따라서 `cars`는 차량 목록이다.
차량이 없으면 로그를 남기고 반복을 끝낸다.

## loader 호출
```python
loaded_count = insert_cars(cars)
```
차량 정리, 검증, MySQL 저장은 `loader.py`가 담당한다.
저장 성공 시 `PASS`, 실패 시 `FAIL` 로그를 남긴다.

## 다음 페이지
```python
next_url = get_next_url(payload)
```
`get_next_url()`은 응답의 `links.next`를 확인한다.
```text
next 주소 있음 → 다음 페이지 요청
next 주소 없음 → 수집 종료
```
현재 페이지 저장이 성공한 뒤에만 다음 주소를 가져오며, `while next_url:` 동안 반복한다.

## 페이지 설정
```python
PAGE_SIZE = 20
MAX_PAGES = 1
```
`PAGE_SIZE`는 한 페이지의 차량 수다.
`MAX_PAGES`는 처리할 최대 페이지 수다.
```text
1 → 1페이지
2 → 1페이지부터 2페이지
0 → 마지막 페이지까지
```
`MAX_PAGES = 2`는 2페이지부터 시작한다는 뜻이 아니다.

## 로그
로그 파일은 `config/car_api_crawler.log`이다.
시간, API 출처, 페이지, 저장 결과, 차량 수를 기록한다.
```text
mysql_insert=PASS input_count=20 loaded_count=20
```

## 한 줄 정리
API에서 차량을 페이지별로 가져와 loader에 넘기고 결과를 기록한다.
