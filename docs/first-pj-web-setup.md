# AWS EC2 차량 데이터 웹사이트 구축 절차

## 1. 최종 구성

현재 구성은 EC2 웹 서버에서 Flask가 실행되고, Flask가 MySQL과 MongoDB를 조회해 하나의 화면에 출력하는 방식이다.

```text
사용자 내부망
      ↓
EC2 웹 서버
      └── first-pj-web
          └── Flask + Gunicorn
              ├── MySQL 차량 데이터 조회
              └── MongoDB FAQ 데이터 조회
```

데이터 흐름은 다음과 같다.

```text
MySQL project1.car_listing  ─┐
                              ├─> Flask ─> templates/index.html
MongoDB 실제_DB.brand_faq   ─┘
```

중요한 점:

- 웹 서버에는 DB 서버 자체를 설치하지 않는다.
- 웹 서버에는 Python 프로그램과 DB 커넥터만 설치한다.
- MongoDB 데이터베이스명은 실제 데이터가 들어 있는 이름으로 `.env`에 입력한다.
- FAQ 컬렉션명은 `brand_faq`로 사용한다.
- `index.html`을 파일로 직접 열지 말고 Flask 주소로 접속해야 한다.

## 2. 디렉토리 구조

웹 서버의 최종 구조는 다음과 같다.
`first-pj-web`은 기존 웹사이트 프로젝트이므로 그대로 유지하고, 차량 크롤러는 별도 `project` 폴더에서 관리한다.

```text
/home/ec2-user/
├── first-pj-web/                    # 기존 웹사이트 프로젝트(그대로 유지)
│   ├── app.py                       # Flask 서버 및 DB 조회 코드
│   ├── .env                         # DB 접속정보
│   ├── requirements.txt             # 설치 패키지 목록(선택)
│   ├── templates/
│   │   └── index.html               # 차량 + FAQ 화면
│   └── static/                      # CSS, JavaScript, 이미지
│
├── project/                       # 차량 크롤러
│   ├── .env                       # 차량 DB 접속정보
│   │
│   ├── config/
│   │   ├── car_api_crawler.py     # 차량 API 수집
│   │   ├── db_config.py           # MySQL 접속정보 관리
│   │   ├── loader.py              # 차량 정제·검증·MySQL 적재
│   │   ├── requirements.txt       # Python 패키지 목록
│   │   ├── vehicle_quality.py     # 적재 데이터 품질검증
│   │   └── car_api_crawler.log    # 크롤러 실행 로그
│   │
│   ├── logs/
│   │   ├── car_pipeline.log       # 파이프라인 실행 로그
│   │   └── car_pipeline.log-날짜  # 날짜별 보관 로그
│   │
│   ├── quality_check_output/
│   │   ├── processed-cars.json    # 처리된 차량 데이터
│   │   └── quality-report.json    # 품질검증 결과
│   │
│   └── sh/
│       ├── run_car_pipeline.sh    # 크롤러·품질검증 실행
│       ├── car_pipeline.cron      # 크론탭 주기 설정
│       └── car_pipeline.logrotate # 로그 순환 설정
│
├── project_faq/
│   ├── config/
│   │   ├── faq_crawler.py          # FAQ 크롤링·DB 적재
│   │   └── requirements.txt        # Python 패키지 목록
│   ├── sh/
│   │   └── car_faq.sh              # 크롤러·품질검증 실행
│   └── logs/
│       ├── faq_run.log             # 실행시작/종료 로그
│       ├── faq_result.log          # 신규적재와 실패건수 로그
│       └── faq_error.log           # 실제 오류 내용기록 로그
```

### 크롤러 위치는 별도 관리

크롤러 소스는 `first-pj-web` 안에 넣지 않는다.
차량 크롤러는 `project`, FAQ 크롤러는 `project_faq`에 각각 둔다.

```text
/home/ec2-user/first-pj-web                # 기존 웹사이트 폴더, 수정하지 않음
/home/ec2-user/project/config
/home/ec2-user/project/logs
/home/ec2-user/project/quality_check_output
/home/ec2-user/project/sh
/home/ec2-user/project_faq/logs             # FAQ 크롤러 폴더
```

차량 크롤러는 EC2의 `project` 아래 `config`와 `sh`를 사용한다.
FAQ 크롤러는 EC2의 `project_faq` 아래 `config`와 `sh`를 사용한다.

역할은 다음처럼 분리한다.

```text
차량 크롤러 → MySQL에 차량 데이터 저장
FAQ 크롤러  → MongoDB에 FAQ 데이터 저장
웹사이트    → 두 DB의 데이터를 조회해서 출력
```

차량 크롤러 파일 역할은 다음과 같다.

```text
project/.env                       # 차량 크롤러의 DB 접속정보를 저장한다.
project/config/car_api_crawler.py # 차량 API를 페이지 단위로 호출하고 loader를 실행한다.
project/config/loader.py           # 차량 데이터를 정제·검증하고 MySQL에 저장한다.
project/config/db_config.py        # MySQL 접속 정보를 한 곳에서 관리한다.
project/config/vehicle_quality.py  # car_listing에 저장된 차량 데이터 품질을 검사한다.
project/config/requirements.txt    # Python 실행에 필요한 패키지를 적는다.
project/config/car_api_crawler.log # 차량 크롤러 실행 결과를 기록한다.
project/sh/run_car_pipeline.sh     # 차량 크롤링과 품질검증을 순서대로 실행한다.
project/sh/car_pipeline.cron       # 파이프라인을 실행할 cron 설정을 적는다.
project/sh/car_pipeline.logrotate  # 실행 로그를 순환 보관하도록 설정한다.
project/logs/car_pipeline.log      # 파이프라인 전체 실행 로그를 기록한다.
project/quality_check_output/processed-cars.json # 품질검증 후 차량 데이터를 저장한다.
project/quality_check_output/quality-report.json # 품질검증 결과와 상태를 저장한다.
```
FAQ 크롤러 파일 역할은 다음과 같다.

```text
project_faq/config/faq_crawler.py
project_faq/sh/car_faq.sh
project_faq/logs/faq_run.log
project_faq/logs/faq_result.log
project_faq/logs/faq_error.log
```

## 3. Amazon Linux에 Python 설치

EC2가 Amazon Linux이므로 `apt`가 아니라 `dnf`를 사용한다.

```bash
# Python 본체를 설치한다.
sudo dnf install -y python3
```

```bash
# Python 패키지를 설치할 수 있도록 pip를 설치한다.
sudo dnf install -y python3-pip
```

```bash
# Python 패키지 설치 중 필요한 개발 파일을 설치한다.
sudo dnf install -y python3-devel
```

설치 확인:

```bash
# Python 버전을 확인한다.
python3 --version
```

```bash
# pip가 설치됐는지 확인한다.
python3 -m pip --version
```

## 4. 웹 서버에 필요한 패키지 설치

현재는 시스템 Python을 사용한다. 아래 패키지는 웹 서버의 Python에서 직접 사용한다.

```bash
# Flask: 웹 서버 프레임워크
# Gunicorn: Flask를 상시 실행하기 위한 서버
# mysql-connector-python: MySQL 연결 모듈
# pymongo: MongoDB 연결 모듈
# python-dotenv: .env 읽기 모듈
sudo /usr/bin/python3 -m pip install \
    flask \
    gunicorn \
    mysql-connector-python \
    pymongo \
    python-dotenv
```

설치 확인:

```bash
# 모든 주요 모듈을 불러와 설치 여부를 확인한다.
/usr/bin/python3 -c "import flask, gunicorn, mysql.connector, pymongo, dotenv; print('필수 패키지 설치 완료')"
```

`externally-managed-environment` 오류가 발생하는 경우에만 다음 명령어를 사용한다.

```bash
# 시스템 Python에 설치를 허용하는 옵션이다.
sudo /usr/bin/python3 -m pip install --break-system-packages \
    flask gunicorn mysql-connector-python pymongo python-dotenv
```

## 5. 웹 프로젝트 디렉토리 생성

```bash
# HTML 템플릿과 정적 파일 폴더를 함께 만든다.
mkdir -p ~/first-pj-web/templates
mkdir -p ~/first-pj-web/static
```

```bash
# Flask 실행 파일과 환경변수 파일을 만든다.
touch ~/first-pj-web/app.py
touch ~/first-pj-web/.env
```

```bash
# DB 비밀번호가 들어 있는 .env를 다른 사용자가 읽지 못하게 한다.
chmod 600 ~/first-pj-web/.env
```

## 6. `.env` 작성

`.env`는 `app.py`와 같은 디렉토리에 둔다.

```bash
# 웹 프로젝트의 환경변수 파일을 연다.
nano ~/first-pj-web/.env
```

아래 내용을 실제 값으로 수정한다.

```env
# MySQL 접속정보
MYSQL_HOST=MySQL_내부_IP_또는_호스트명
MYSQL_PORT=3306
MYSQL_USER=MySQL사용자명
MYSQL_PASSWORD=MySQL비밀번호
MYSQL_DATABASE=project1

# MongoDB 접속정보
# 실제 FAQ 데이터가 들어 있는 MongoDB 서버 주소를 입력한다.
MONGO_URI=mongodb://MongoDB_내부_IP:27017

# 실제 FAQ 데이터가 들어 있는 데이터베이스명을 입력한다.
# project1이 아니라면 실제 이름으로 변경한다.
MONGO_DATABASE=실제_MongoDB_데이터베이스명
```

저장 방법:

```text
Ctrl + O → Enter → Ctrl + X
```

주의:

- `MONGO_DATABASE`는 컬렉션명이 아니라 데이터베이스명이다.
- FAQ 컬렉션명은 코드에서 `brand_faq`로 지정한다.
- `.env`의 MongoDB 데이터베이스명을 잘못 입력하면 연결은 성공해도 데이터 개수가 0으로 나올 수 있다.
- `.env`를 공개 저장소에 올리지 않는다.

## 7. 데이터베이스 구조

### 7.1 MySQL 차량 데이터 구조

MySQL은 차량 정보를 표 형태로 저장한다.

```text
데이터베이스: project1
테이블: car_listing
의미: 차량 1대당 테이블의 1개 행(row)
```

구조:

```text
project1
└── car_listing
    ├── car_id              차량 고유번호
    ├── region              광역 지역
    ├── sub_region          세부 지역
    ├── brand               차량 브랜드
    ├── model_year          차량 연식
    ├── fuel_type           연료 종류
    ├── mileage_km          주행거리(km)
    ├── price_krw           가격(원)
    ├── status               판매 상태
    └── registration_date   등록일
```

컬럼별 의미:

| 컬럼 | 타입 | 역할 |
|---|---|---|
| `car_id` | `INT` | 차량을 구분하는 고유번호, 기본키 |
| `region` | `VARCHAR(50)` | 광역 지역 |
| `sub_region` | `VARCHAR(50)` | 시·군·구 등 세부 지역 |
| `brand` | `VARCHAR(50)` | 차량 브랜드 |
| `model_year` | `INT` | 차량 연식 |
| `fuel_type` | `VARCHAR(30)` | 연료 종류 |
| `mileage_km` | `INT` | 주행거리(km) |
| `price_krw` | `INT` | 차량 가격(원) |
| `status` | `VARCHAR(20)` | `AVAILABLE`, `RESERVED`, `SOLD` 등 판매 상태 |
| `registration_date` | `DATE` | 차량 등록일 |

차량 데이터의 이동 과정:

```text
차량 크롤러
    ↓ 차량 정보 저장
MySQL project1.car_listing
    ↓ app.py의 get_cars()가 SELECT 실행
Flask
    ↓ cars 변수로 index.html에 전달
차량 목록 테이블에 출력
```

웹 서버가 실행하는 기본 조회문은 다음과 같다.

```sql
-- 차량 데이터베이스를 선택한다.
USE project1;

-- 차량 목록을 최신 고유번호 순서로 조회한다.
SELECT
    car_id,
    region,
    sub_region,
    brand,
    model_year,
    fuel_type,
    mileage_km,
    price_krw,
    status,
    registration_date
FROM car_listing
ORDER BY car_id DESC;
```

`car_id`는 차량을 구분하는 값이므로 같은 차량을 다시 저장할 때 중복 여부를 판단하는 기준으로 사용할 수 있다. 차량 데이터와 FAQ 데이터는 서로 다른 DB에 있고 직접 연결되는 공통 키가 없으므로 MySQL과 MongoDB 사이에 SQL JOIN을 사용하지 않는다.

검색 성능을 높이기 위해 지역·브랜드·연식으로 자주 검색한다면 다음과 같은 인덱스를 사용할 수 있다.

```sql
-- 지역, 세부 지역, 브랜드, 연식 검색을 빠르게 한다.
CREATE INDEX idx_car_search
ON car_listing (region, sub_region, brand, model_year);
```

### 7.2 MongoDB FAQ 문서 구조

현재 웹 화면은 아래 필드를 기준으로 FAQ를 출력한다.

```text
데이터베이스: project1
컬렉션: brand_faq
company
category
question
answer
link
collected_at
```

구조:
```text
project1
└── brand_faq
    ├── _id                FAQ 고유 식별자
    ├── company            회사명
    ├── category           카테고리
    ├── question           질문 제목
    ├── answer             답변 내용
    ├── link               원본 링크
    └── collected_at       수집일
```
// FAQ 데이터베이스를 선택한다.
use project1

// FAQ 목록을 조회한다.
db.brand_faq.find(
  {},
  {
    _id: 0,
    company: 1,
    category: 1,
    question: 1,
    answer: 1,
    link: 1,
    collected_at: 1
  }
)

db.brand_faq.createIndex({
  company: 1,
  category: 1
})

예시:

```json
{
  "company": "현대",
  "category": "고객지원",
  "question": "공식 FAQ에서 원하는 답을 찾지 못하면 어디로 문의하나요?",
  "answer": "현대자동차 공식 FAQ 화면의 1:1 문의를 이용하거나 고객센터 안내를 확인합니다.",
  "link": "현대자동차 자주하는 질문 ↗",
  "collected_at": "2026-08-11"
}
```

화면 출력 연결:

```text
faq.company      → 회사명
faq.category     → 카테고리
faq.question     → 질문 제목
faq.answer       → 답변 내용
faq.link         → 링크 정보
faq.collected_at → 수집일
```

## 8. `app.py` 역할

```bash
# Flask 서버 파일을 연다.
nano ~/first-pj-web/app.py
```

`app.py`는 다음 순서로 작동한다.

```text
1. 같은 폴더의 .env를 읽는다.
2. MySQL 연결 정보를 읽는다.
3. MongoDB 연결 정보를 읽는다.
4. / 주소에서 MySQL 차량과 MongoDB FAQ를 조회한다.
5. 두 결과를 index.html에 전달한다.
```

핵심 구조:

```python
# app.py와 같은 위치의 .env를 읽는다.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH, override=True)


# 메인 페이지가 열리면 두 DB를 모두 조회한다.
@app.route("/")
def index():
    cars = get_cars()       # MySQL 조회
    faqs = get_faqs()       # MongoDB 조회

    return render_template(
        "index.html",
        cars=cars,
        faqs=faqs,
    )
```

MySQL 차량 조회:

```python
# MySQL의 차량 테이블에서 데이터를 가져온다.
cursor.execute("""
    SELECT
        car_id,
        region,
        sub_region,
        brand,
        model_year,
        fuel_type,
        mileage_km,
        price_krw,
        status,
        registration_date
    FROM car_listing
    ORDER BY car_id DESC
""")
```

MongoDB FAQ 조회:

```python
# 실제 데이터베이스 안의 brand_faq 컬렉션을 조회한다.
documents = list(
    mongo_db["brand_faq"].find(
        {},
        {
            "_id": 0,
            "company": 1,
            "category": 1,
            "question": 1,
            "answer": 1,
            "link": 1,
            "collected_at": 1,
        },
    )
)
```

`_id`는 화면에 필요하지 않으므로 조회 결과에서 제외한다.

## 9. `index.html` 역할

```bash
# Flask가 찾는 templates 폴더 안에 화면 파일을 만든다.
nano ~/first-pj-web/templates/index.html
```

Flask가 전달한 데이터를 Jinja 문법으로 받는다.

```html
<!-- Flask가 전달한 MySQL 차량 목록 -->
<script>
    let allCars = {{ cars | tojson }};

    // Flask가 전달한 MongoDB FAQ 목록
    const allFaqs = {{ faqs | tojson }};
</script>
```

FAQ 출력 부분:

```javascript
function renderFaqs(faqs) {
    const target = document.getElementById("faqList");

    if (!faqs || faqs.length === 0) {
        target.innerHTML = "<div>FAQ 데이터가 없습니다.</div>";
        return;
    }

    target.innerHTML = faqs.map(faq => `
        <article class="faq-card">
            <div>${faq.company ?? "-"} · ${faq.category ?? "-"}</div>
            <h3>${faq.question ?? "질문 없음"}</h3>
            <p>${faq.answer ?? "답변 없음"}</p>
            <p>수집일: ${faq.collected_at ?? "-"}</p>
            <a href="#">링크: ${faq.link ?? "-"}</a>
        </article>
    `).join("");
}

// 페이지가 열릴 때 MongoDB FAQ를 화면에 출력한다.
renderFaqs(allFaqs);
```

## 10. 로컬 파일이 아닌 Flask 주소로 접속

다음 방식은 정상 작동하지 않는다.

```text
file:///C:/.../index.html
```

이유는 `{{ cars | tojson }}`와 `{{ faqs | tojson }}`가 Flask에서만 실제 JSON으로 변환되는 문법이기 때문이다.

Flask 서버를 실행한 뒤 아래 주소로 접속한다.

```text
http://EC2_PRIVATE_IP:8000/
```

예시:

```text
http://10.0.1.25:8000/
```

## 11. 웹 서비스 테스트 실행

먼저 터미널에서 직접 실행해 오류를 확인한다.

```bash
# 프로젝트 폴더로 이동한다.
cd ~/first-pj-web
```

```bash
# 시스템 Python으로 Flask를 실행한다.
/usr/bin/python3 app.py
```

다른 터미널이나 내부 PC에서 접속한다.

```text
http://EC2_PRIVATE_IP:8000/
```

테스트가 끝나면 Flask를 종료한다.

```text
Ctrl + C
```

## 12. Gunicorn과 systemd로 상시 실행

SSH를 종료해도 웹사이트가 계속 실행되도록 `systemd` 서비스로 등록한다.

### 12.1 서비스 파일 작성

```bash
# systemd 서비스 파일을 연다.
sudo nano /etc/systemd/system/first-pj-web.service
```

```ini
[Unit]
Description=First PJ Vehicle Web
After=network.target

[Service]
# EC2에서 실제로 사용하는 Linux 사용자명
User=ec2-user

# app.py가 있는 프로젝트 폴더
WorkingDirectory=/home/ec2-user/first-pj-web

# 웹 프로젝트 안의 .env를 읽는다.
EnvironmentFile=/home/ec2-user/first-pj-web/.env

# 시스템 Python으로 Gunicorn을 실행한다.
ExecStart=/usr/bin/python3 -m gunicorn --bind 0.0.0.0:8000 app:app

# 오류로 종료되면 자동으로 다시 시작한다.
Restart=always

[Install]
WantedBy=multi-user.target
```

### 12.2 서비스 등록 및 시작

```bash
# systemd가 새 서비스 파일을 다시 읽도록 한다.
sudo systemctl daemon-reload
```

```bash
# EC2 재부팅 후에도 자동 시작하도록 설정한다.
sudo systemctl enable first-pj-web
```

```bash
# 웹 서비스를 시작한다.
sudo systemctl start first-pj-web
```

```bash
# 실행 상태를 확인한다.
sudo systemctl status first-pj-web --no-pager
```

다음처럼 나오면 정상이다.

```text
active (running)
```

코드나 `.env`를 수정한 뒤에는 다음 명령어로 재시작한다.

```bash
sudo systemctl restart first-pj-web
```

## 13. 오류 확인

### 서비스 로그

```bash
# 최근 웹 서비스 오류를 확인한다.
sudo journalctl -u first-pj-web -n 100 --no-pager
```

```bash
# 로그를 실시간으로 확인한다.
sudo journalctl -u first-pj-web -f
```

### `TemplateNotFound: index.html`

HTML 파일이 잘못된 위치에 있는 오류다.

```bash
ls -l ~/first-pj-web/templates/index.html
```

정상 위치:

```text
/home/ec2-user/first-pj-web/templates/index.html
```

### `ModuleNotFoundError`

서비스가 사용하는 시스템 Python에 패키지가 없는 오류다.

```bash
sudo /usr/bin/python3 -m pip install \
    flask gunicorn mysql-connector-python pymongo python-dotenv
```

### FAQ 데이터가 화면에 안 나오는 경우

다음 순서로 확인한다.

```text
1. .env의 MONGO_URI가 실제 MongoDB 서버 주소인지 확인
2. .env의 MONGO_DATABASE가 실제 데이터베이스명인지 확인
3. brand_faq 컬렉션에 문서가 있는지 확인
4. app.py가 company/category/question/answer/link/collected_at을 조회하는지 확인
5. systemd 서비스를 재시작
6. file://가 아닌 http://EC2_PRIVATE_IP:8000으로 접속
```

### 서비스 설정 확인

```bash
# systemd가 실제로 어떤 설정으로 실행되는지 확인한다.
sudo systemctl cat first-pj-web
```

다음 경로가 현재 구조와 일치해야 한다.

```ini
WorkingDirectory=/home/ec2-user/first-pj-web
EnvironmentFile=/home/ec2-user/first-pj-web/.env
ExecStart=/usr/bin/python3 -m gunicorn --bind 0.0.0.0:8000 app:app
```

## 14. AWS 보안 그룹

필요한 통신은 다음과 같다.

```text
내부 사용자 → 웹 서버       TCP 8000
웹 서버 → MySQL 서버        TCP 3306
웹 서버 → MongoDB 서버      TCP 27017
```

- 웹 서버 보안 그룹에서 내부 사용자에게만 TCP 8000을 허용한다.
- MySQL 서버는 웹 서버의 내부 IP 또는 보안 그룹에서만 TCP 3306을 허용한다.
- MongoDB 서버는 웹 서버의 내부 IP 또는 보안 그룹에서만 TCP 27017을 허용한다.
- `3306`, `27017`을 인터넷 전체에 공개하지 않는다.

## 15. 최종 확인 순서

```text
1. EC2에서 Python과 pip 설치
2. 시스템 Python에 Flask/Gunicorn/MySQL/MongoDB 패키지 설치
3. first-pj-web/templates 디렉토리 확인
4. first-pj-web/.env 작성
5. MONGO_DATABASE를 실제 데이터베이스명으로 입력
6. MongoDB brand_faq 데이터 개수 확인
7. app.py에 MySQL과 MongoDB 조회 코드 작성
8. templates/index.html에 차량과 FAQ 출력 코드 작성
9. /usr/bin/python3 app.py로 직접 테스트
10. systemd + Gunicorn 등록
11. active (running) 상태 확인
12. http://EC2_PRIVATE_IP:8000/으로 접속
```

## 최종 요약

```text
first-pj-web/app.py
    ├── MySQL project1.car_listing 조회
    └── MongoDB 실제_DB.brand_faq 조회

first-pj-web/templates/index.html
    ├── 차량 데이터 출력
    └── FAQ 데이터 출력

first-pj-web/.env
    ├── MySQL 접속정보
    └── MongoDB 접속정보

project/
    ├── .env 차량 DB 접속정보
    ├── config/ 차량 크롤러 Python 파일과 실행 로그
    ├── sh/ 차량 파이프라인·cron 설정
    ├── logs/ 파이프라인 실행 로그
    └── quality_check_output/ 품질검증 결과

project_faq/
    ├── config/ 차량FAQ 크롤러 Python 파일과 실행 로그
    ├── sh/ 차량FAQ 파이프라인·cron 설정
    └── logs/ 파이프라인 실행 로그
```

웹사이트는 기존 `first-pj-web`에서 데이터를 조회한다.
차량 크롤러는 `project`, FAQ 소스는 `faq`에 분리해 웹사이트 코드와 섞이지 않게 관리한다.
이번 차량 크롤러 작업에서는 `first-pj-web`의 파일을 삭제하거나 수정하지 않는다.
