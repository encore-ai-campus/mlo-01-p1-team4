# EC2 실행·자동화 정리

## 1. Git에 올릴 파일

```text
src/car_api_crawler.py       차량 API 수집·페이지 반복·로그
src/loader.py                차량 정제·검증·MySQL upsert
src/vehicle_quality.py       적재 데이터 품질검증
src/requirements.txt         Python 패키지 목록
sql/project1_schema.sql      MySQL 테이블 생성 SQL
sh/run_car_crawler.sh        EC2에서 실행할 셸 스크립트
sh/car_api_crawler.logrotate logrotate 설정 예시
.env.example                 환경변수 이름만 제공하는 예시
.gitignore                   비밀정보·로그·캐시 제외
docs/ec2_operation.md        EC2 설치·실행·자동화 절차
```

## 2. Git에 올리면 안 되는 파일

```text
.env
*.log
__pycache__/
.venv/
실제 DB 비밀번호·API key
```

## 3. EC2 접속 후 최초 1회

저장소를 `/home/ec2-user/project`에 배치하는 기준이다.

```bash
git clone <저장소_URL> /home/ec2-user/project
cd /home/ec2-user/project

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r src/requirements.txt

mysql -u <DB_USER> -p project1 < sql/project1_schema.sql

cp .env.example .env
vi .env
chmod 600 .env
chmod +x sh/run_car_crawler.sh
```

`.env`에는 EC2의 실제 DB 접속 정보만 입력한다. 이 파일은 Git에 올리지
않는다.

## 4. 수동 실행 확인

```bash
./sh/run_car_crawler.sh
tail -n 50 src/car_api_crawler.log
python3 src/vehicle_quality.py
```

현재 `src/car_api_crawler.py`의 `MAX_PAGES=0`은 다음 페이지가 없을 때까지
전체 페이지를 수집한다. 테스트만 할 때는 작은 값으로 바꿨다가 운영 전에
다시 `0`으로 되돌린다.

## 5. crontab 등록

`crontab`은 크롤러 실행 시각만 관리한다.

```bash
crontab -e
```

예를 들어 한 시간마다 실행한다.

```cron
0 * * * * /home/ec2-user/project/sh/run_car_crawler.sh
```

`run_car_crawler.sh`의 `flock`이 이전 실행이 끝나지 않았으면 중복 실행을
막는다.

## 6. logrotate 등록

`logrotate`는 로그 파일을 날짜별로 분리·압축·보관한다. logrotate 자체는
대부분의 Linux 이미지에서 이미 매일 실행되므로 별도 crontab을 추가하지
않는다.

```bash
sudo cp sh/car_api_crawler.logrotate /etc/logrotate.d/car_api_crawler
sudo chmod 644 /etc/logrotate.d/car_api_crawler

sudo logrotate -d /etc/logrotate.d/car_api_crawler
sudo logrotate -f /etc/logrotate.d/car_api_crawler
```

저장소를 다른 경로에 clone했다면 `sh/car_api_crawler.logrotate`의 로그
경로를 실제 경로로 바꾼 뒤 `/etc/logrotate.d/car_api_crawler`에 다시
복사한다.

## 7. 운영 확인 명령

```bash
crontab -l
tail -f src/car_api_crawler.log
sudo logrotate -d /etc/logrotate.d/car_api_crawler
```

로그에는 처리 건수와 오류만 남기고 API key나 DB 비밀번호는 남기지 않는다.
