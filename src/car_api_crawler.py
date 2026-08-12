"""로컬 중고차 API를 페이지 단위로 수집하고 MySQL에 저장한다."""

from datetime import datetime
from pathlib import Path

import requests

from loader import count_car_listings, insert_cars


# API 주소와 실행 조건은 여기서 수정한다.
BASE_URL = "http://192.168.0.51:4000"
PUBLIC_KEY_PATH = "/api/v1/public-key"
CARS_PATH = "/api/v1/cars"
PAGE_SIZE = 20

# 처음에는 한 페이지만 수집해서 확인한다.
# 전체 페이지를 수집하려면 0으로 바꾼다.
MAX_PAGES = 2
REQUEST_TIMEOUT = 10
LOG_FILE = Path(__file__).with_name("car_api_crawler.log")


def write_log(message):
    """실행 날짜·시간과 작업 결과를 log 파일에 기록한다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(f"[{now}] {message}\n")


def get_api_key():
    """공개 키 API에서 오늘 사용할 API 키를 가져온다."""
    response = requests.get(
        BASE_URL + PUBLIC_KEY_PATH,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    payload = response.json()
    api_key = payload["data"]["current"]["api_key"]

    if not api_key:
        raise ValueError("API 키가 응답에 없습니다.")

    return api_key


def fetch_page(url, api_key, first_page=False):
    """API 키로 중고차 한 페이지를 요청한다."""
    if first_page:
        params = {
            "sort": "newest",
            "page_size": PAGE_SIZE,
        }
    else:
        params = None

    response = requests.get(
        url,
        params=params,
        headers={"X-API-Key": api_key},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    return response.json()


def get_cars(payload):
    """목록 응답의 data에서 자동차 목록을 꺼낸다."""
    cars = payload.get("data")

    if not isinstance(cars, list):
        raise ValueError("API 응답의 data가 자동차 목록이 아닙니다.")

    return cars


def get_next_url(payload):
    """응답의 links.next에서 다음 페이지 주소를 가져온다."""
    links = payload.get("links")

    if links is None:
        return None

    next_url = links.get("next")

    if not next_url:
        return None

    if next_url.startswith("http"):
        return next_url

    return BASE_URL + next_url


def collect_and_save():
    """저장에 성공한 경우에만 다음 페이지로 이동한다."""
    api_source = BASE_URL + CARS_PATH
    api_key = get_api_key()

    # 크롤링 시작 전 car_listing 전체 행 개수를 확인한다.
    before_count = count_car_listings()

    # 첫 요청 주소는 BASE_URL과 CARS_PATH를 합쳐서 만든다.
    next_url = api_source
    page_number = 1
    total_input = 0
    total_processed = 0

    # next_url에 주소가 들어 있는 동안 페이지 수집을 반복한다.
    # next_url이 None이 되면 더 가져올 페이지가 없다는 뜻이다.
    while next_url:
        # MAX_PAGES가 0이면 전체 페이지를 수집한다.
        # MAX_PAGES가 1 이상이면 정해진 페이지 수까지만 수집한다.
        if MAX_PAGES != 0 and page_number > MAX_PAGES:
            break

        # 첫 번째 요청인지 표시한다.
        # 첫 페이지일 때만 sort와 page_size 조건을 사용한다.
        is_first_page = False
        if page_number == 1:
            is_first_page = True

        # 현재 페이지 주소로 API를 요청한다.
        # fetch_page가 반환하는 전체 API 응답을 payload에 저장한다.
        payload = fetch_page(next_url, api_key, is_first_page)

        # 전체 응답 중 data 안에 있는 차량 목록만 cars에 저장한다.
        cars = get_cars(payload)

        # 현재 페이지에 차량이 없으면 더 저장할 데이터가 없으므로 종료한다.
        if not cars:
            write_log(
                f"api_source={api_source} page={page_number} "
                "mysql_insert=PASS input_count=0 processed_count=0 "
                "loaded_count=0 duplicate_count=0"
            )
            break

        input_count = len(cars)

        # 차량 목록을 loader.py로 보내 정제·검증한 뒤 MySQL에 저장한다.
        try:
            processed_count = insert_cars(cars)
        except Exception as error:
            # 저장 중 오류가 나면 오류 내용을 문자열로 바꿔 로그에 남긴다.
            message = str(error).replace("\n", " ")
            write_log(
                f"api_source={api_source} page={page_number} "
                f"mysql_insert=FAIL input_count={input_count} "
                "processed_count=0 loaded_count=0 duplicate_count=0 "
                f"error={message}"
            )

            # 오류를 다시 발생시켜 main()에서도 실패를 알 수 있게 한다.
            raise

        # 전체 실행의 입력 수와 처리 수를 누적한다.
        total_input += input_count
        total_processed += processed_count

        # 현재 페이지까지의 car_listing 전체 행 개수를 확인한다.
        current_count = count_car_listings()

        # 실행 시작 후 새로 INSERT된 누적 행 개수를 계산한다.
        current_loaded_count = current_count - before_count

        # 실행 시작 후 기존 car_id로 처리된 누적 행 개수를 계산한다.
        current_duplicate_count = total_processed - current_loaded_count

        # 현재 페이지의 MySQL 저장이 성공했다는 로그를 남긴다.
        write_log(
            f"api_source={api_source} page={page_number}, "
            f"mysql_insert=PASS input_count={input_count}, "
            f"processed_count={processed_count}, "
            f"loaded_count={current_loaded_count}, "
            f"duplicate_count={current_duplicate_count}"
        )

        # 현재 페이지 적재가 끝난 뒤에만 다음 주소를 가져온다.
        next_url = get_next_url(payload)
        page_number += 1

    # 크롤링 종료 후 car_listing 전체 행 개수를 다시 확인한다.
    after_count = count_car_listings()
    loaded_count = after_count - before_count
    duplicate_count = total_processed - loaded_count

    # 전체 실행 결과를 로그에 남긴다.
    write_log(
        f"api_source={api_source} run_status=PASS, "
        f"total_input={total_input}, "
        f"total_processed={total_processed}, "
        f"loaded_count={loaded_count}, "
        f"duplicate_count={duplicate_count}, "
        f"before_count={before_count} after_count={after_count}"
    )

    print(f"수집 출처: {api_source}")
    print(f"전체 입력 건수: {total_input}")
    print(f"전체 처리 건수: {total_processed}")
    print(f"전체 신규 적재 건수: {loaded_count}")
    print(f"전체 중복 처리 건수: {duplicate_count}")
    print(f"로그 파일: {LOG_FILE}")

    return loaded_count


def main():
    try:
        collect_and_save()
    except Exception as error:
        message = str(error).replace("\n", " ")
        write_log(
            f"api_source={BASE_URL + CARS_PATH} "
            f"mysql_insert=NOT_RUN error={message}"
        )
        print(f"수집 또는 적재 실패: {error}")
        return 1

    return 0


if __name__ == "__main__":
    main()
