#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env}"
PYTHON_BIN="${PYTHON_BIN:-${PROJECT_DIR}/.venv/bin/python}"
LOG_FILE="${PROJECT_DIR}/src/car_api_crawler.log"
LOCK_FILE="/tmp/car_api_crawler.lock"

if [[ ! -r "${ENV_FILE}" ]]; then
    echo "환경변수 파일이 없습니다: ${ENV_FILE}" >&2
    exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Python 실행 파일이 없습니다: ${PYTHON_BIN}" >&2
    exit 1
fi

umask 027
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    echo "이전 크롤러가 아직 실행 중이므로 이번 실행을 건너뜁니다."
    exit 0
fi

cd "${PROJECT_DIR}"
"${PYTHON_BIN}" "${PROJECT_DIR}/src/car_api_crawler.py" >>"${LOG_FILE}" 2>&1
