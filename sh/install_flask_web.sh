#!/usr/bin/env bash

# 이 파일은 AWS EC2 웹 서버에 Flask 실행 환경을 자동으로 준비합니다.
# 가상환경은 만들지 않고 서버 전체에서 사용할 수 있도록 설치합니다.
#
# 초보자 실행 순서
# 1. 이 파일을 EC2 서버에 업로드합니다.
# 2. chmod +x install_flask_web.sh
# 3. ./install_flask_web.sh
# 4. 생성된 .env 파일에 실제 DB 접속 정보를 입력합니다.
# 5. app.py와 templates/index.html을 first-pj-web에 업로드합니다.
#
# 오류가 발생하거나 정의되지 않은 변수를 사용하면 즉시 종료합니다.
set -Eeuo pipefail

# 문제가 생기면 어느 줄에서 멈췄는지 알려줍니다.
handle_error() {
    local exit_code=$?
    echo "명령 실행 중 오류가 발생했습니다." >&2
    echo "문제가 발생한 줄 번호: ${BASH_LINENO[0]}" >&2
    echo "스크립트를 중단합니다. 위의 오류 내용을 확인하세요." >&2
    exit "${exit_code}"
}

trap handle_error ERR

# 관리자 권한이 필요할 때 sudo를 사용합니다.
SUDO_CMD=()
if [[ "${EUID}" -ne 0 ]]; then
    if ! command -v sudo >/dev/null 2>&1; then
        echo "sudo를 찾을 수 없습니다. root 계정으로 실행하세요." >&2
        exit 1
    fi
    SUDO_CMD=(sudo)
fi

# Amazon Linux에서 프로그램을 설치할 때 사용하는 dnf를 확인합니다.
if ! command -v dnf >/dev/null 2>&1; then
    echo "프로그램 설치 도구 dnf가 없습니다. yum으로 dnf를 설치합니다."

    if ! command -v yum >/dev/null 2>&1; then
        echo "dnf와 yum을 모두 찾을 수 없어 설치를 중단합니다." >&2
        exit 1
    fi

    "${SUDO_CMD[@]}" yum install -y dnf
fi

# 파일을 업로드한 사용자의 홈 디렉터리를 찾습니다.
# 일반적인 EC2 사용자는 ec2-user입니다.
if [[ -n "${SUDO_USER:-}" ]] && id "${SUDO_USER}" >/dev/null 2>&1; then
    APP_USER="${SUDO_USER}"
elif id ec2-user >/dev/null 2>&1; then
    APP_USER="ec2-user"
else
    APP_USER="$(id -un)"
fi

# 사용할 사용자의 그룹과 홈 디렉터리를 확인합니다.
APP_GROUP="$(id -gn "${APP_USER}")"
APP_HOME="$(getent passwd "${APP_USER}" | cut -d: -f6)"

if [[ -z "${APP_HOME}" ]]; then
    echo "사용자 홈 디렉터리를 확인할 수 없습니다: ${APP_USER}" >&2
    exit 1
fi

APP_DIR="${APP_HOME}/first-pj-web"
TEMPLATES_DIR="${APP_DIR}/templates"
STATIC_DIR="${APP_DIR}/static"
PROJECT_DIR="${APP_HOME}/project"
ENV_FILE="${APP_DIR}/.env"
REQUIREMENTS_FILE="${APP_DIR}/requirements.txt"
SERVICE_FILE="/etc/systemd/system/first-pj-web.service"

# 1단계: Python 설치
# Python은 Flask 프로그램을 실행하는 기본 프로그램입니다.
# pip는 Flask 같은 추가 프로그램을 설치할 때 사용합니다.
echo
echo "========== 1단계 / Python 설치 =========="
echo "Flask 프로그램을 실행할 Python과 추가 프로그램 설치 도구를 설치합니다."
"${SUDO_CMD[@]}" dnf install -y python3 python3-pip python3-devel

PYTHON_BIN="$(command -v python3)"

# 2단계: Flask와 DB 연결 기능 설치
# 가상환경을 만들지 않고 서버 전체에서 사용할 수 있도록 설치합니다.
# Flask: 웹 페이지를 만드는 도구
# Gunicorn: Flask를 계속 실행해 주는 실행 프로그램
# MySQL과 MongoDB 패키지: 각 DB에 연결하는 기능
# python-dotenv: .env 파일의 설정을 읽는 기능
echo
echo "========== 2단계 / Flask와 DB 연결 기능 설치 =========="
echo "웹 화면과 DB 연결에 필요한 프로그램을 설치합니다."
PIP_EXTRA_ARGS=()
if "${PYTHON_BIN}" -m pip install --help 2>&1 | grep -q -- '--break-system-packages'; then
    PIP_EXTRA_ARGS+=(--break-system-packages)
fi

"${SUDO_CMD[@]}" "${PYTHON_BIN}" -m pip install "${PIP_EXTRA_ARGS[@]}" \
    flask \
    gunicorn \
    mysql-connector-python \
    pymongo \
    python-dotenv

# 3단계: 사용할 폴더 생성
# first-pj-web: Flask 웹 사이트 파일을 보관하는 폴더
# templates: HTML 파일을 보관하는 폴더
# static: CSS, 이미지 같은 꾸밈 파일을 보관하는 폴더
# project: 나중에 크롤러 파일을 보관할 폴더
echo
echo "========== 3단계 / 웹 사이트 폴더 생성 =========="
echo "웹 사이트와 크롤러 파일을 넣을 폴더를 만듭니다."
"${SUDO_CMD[@]}" mkdir -p "${TEMPLATES_DIR}" "${STATIC_DIR}" "${PROJECT_DIR}"

# 4단계: 설치 목록 기록
# 나중에 어떤 프로그램을 설치했는지 확인할 수 있도록 목록을 저장합니다.
# 기존 파일이 있으면 사용자가 작성한 내용을 보호하기 위해 덮어쓰지 않습니다.
echo
echo "========== 4단계 / 설치 목록 기록 =========="
echo "설치한 Python 프로그램 목록을 기록합니다."
if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
    "${SUDO_CMD[@]}" tee "${REQUIREMENTS_FILE}" > /dev/null <<'EOF'
flask
gunicorn
mysql-connector-python
pymongo
python-dotenv
EOF
fi

# 5단계: DB 접속 정보 파일 생성
# .env에는 DB 주소, 계정, 비밀번호를 적습니다.
# 기존 .env 파일은 비밀번호가 들어 있을 수 있으므로 덮어쓰지 않습니다.
echo
echo "========== 5단계 / DB 접속 정보 파일 준비 =========="
echo "DB 주소와 계정을 적어 넣을 .env 파일을 준비합니다."
if [[ ! -f "${ENV_FILE}" ]]; then
    "${SUDO_CMD[@]}" tee "${ENV_FILE}" > /dev/null <<'EOF'
# MySQL 접속 정보
MYSQL_HOST=MYSQL_PRIVATE_IP
MYSQL_PORT=3306
MYSQL_USER=MYSQL_USER_NAME
MYSQL_PASSWORD=MYSQL_PASSWORD
MYSQL_DATABASE=project1

# MongoDB 접속 정보
MONGO_URI=mongodb://MONGODB_PRIVATE_IP:27017
MONGO_DATABASE=MONGODB_DATABASE_NAME
EOF
    echo ".env 예시 파일을 만들었습니다."
    echo "설치가 끝난 뒤 실제 MySQL과 MongoDB 정보로 반드시 수정하세요."
else
    echo "기존 .env 파일이 있어 그대로 유지합니다."
fi

# 6단계: 파일 권한 설정
# 웹 서버 사용자가 파일을 읽을 수 있도록 소유자를 맞춥니다.
# .env는 비밀번호가 들어가므로 본인만 읽을 수 있게 잠급니다.
echo
echo "========== 6단계 / 파일 권한 설정 =========="
echo "웹 서버가 파일을 읽을 수 있도록 권한을 설정합니다."
"${SUDO_CMD[@]}" chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}" "${PROJECT_DIR}"
"${SUDO_CMD[@]}" chmod 600 "${ENV_FILE}"

# 7단계: 자동 실행 서비스 등록
# SSH 접속을 끊어도 웹 사이트가 계속 실행되도록 설정합니다.
# 서버가 다시 켜져도 Flask가 자동으로 시작됩니다.
echo
echo "========== 7단계 / Flask 자동 실행 설정 =========="
echo "SSH를 종료해도 웹 사이트가 계속 실행되도록 설정합니다."
"${SUDO_CMD[@]}" tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=First PJ Flask Web
After=network-online.target
Wants=network-online.target

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
Environment=PYTHONUNBUFFERED=1
ExecStart=${PYTHON_BIN} -m gunicorn --bind 0.0.0.0:8000 --workers 1 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

"${SUDO_CMD[@]}" systemctl daemon-reload

# 8단계: 웹 사이트 실행
# app.py가 이미 있으면 지금 바로 서비스를 시작합니다.
# 아직 app.py를 업로드하지 않았다면 폴더 준비만 하고 기다립니다.
echo
echo "========== 8단계 / 웹 사이트 실행 =========="
if [[ -f "${APP_DIR}/app.py" ]]; then
    "${SUDO_CMD[@]}" systemctl enable --now first-pj-web
    echo "app.py를 찾았습니다. Flask 웹 사이트를 시작했습니다."
    echo "브라우저에서 http://EC2_PRIVATE_IP:8000/ 으로 접속하세요."
else
    echo "app.py가 아직 없어 웹 사이트는 시작하지 않았습니다."
    echo "아래 경로에 파일을 업로드한 뒤 다음 명령어로 시작하세요."
    echo "${APP_DIR}/app.py"
    echo "${TEMPLATES_DIR}/index.html"
    echo "서비스 시작 명령: sudo systemctl enable --now first-pj-web"
fi

# 마지막으로 설치한 프로그램을 실제로 불러올 수 있는지 확인합니다.
"${PYTHON_BIN}" -c 'import flask, gunicorn, mysql.connector, pymongo, dotenv; print("필수 패키지 설치 확인 완료")'

echo
echo "Flask 웹 서버 기본 설정이 완료되었습니다."
echo "이제 아래에 표시되는 순서대로 DB 정보와 웹 파일을 준비하면 됩니다."
echo "웹 프로젝트 경로: ${APP_DIR}"
echo "크롤러 보관 경로: ${PROJECT_DIR}"
echo "환경 변수 파일: ${ENV_FILE}"
echo "마지막으로 AWS 보안 그룹에서 웹 서버의 TCP 8000 포트를 허용해야 합니다."
echo "이 설정이 없으면 브라우저에서 웹 사이트에 접속할 수 없습니다."
