#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env}"
PYTHON_BIN="/usr/bin/python3"
LOG_DIR="${LOG_DIR:-${PROJECT_DIR}/logs}"
PIPELINE_LOG="${PIPELINE_LOG:-${LOG_DIR}/car_pipeline.log}"
LOCK_FILE="/tmp/project1_car_pipeline.lock"
RUN_STATUS="UNKNOWN"

mkdir -p "${LOG_DIR}"
umask 027
exec >>"${PIPELINE_LOG}" 2>&1

finish() {
    local exit_code=$?

    if [[ "${exit_code}" -ne 0 ]]; then
        RUN_STATUS="FAIL"
    fi

    printf '[%s] run_status=%s exit_code=%s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" "${RUN_STATUS}" "${exit_code}"
}

trap finish EXIT

printf '[%s] run_status=START\n' "$(date '+%Y-%m-%d %H:%M:%S')"

if [[ ! -r "${ENV_FILE}" ]]; then
    echo "환경변수 파일이 없습니다: ${ENV_FILE}" >&2
    exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Python 실행 파일이 없습니다: ${PYTHON_BIN}" >&2
    exit 1
fi

if ! command -v flock >/dev/null 2>&1; then
    echo "flock 명령을 찾을 수 없습니다." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

for required_var in MYSQL_HOST MYSQL_PORT MYSQL_DATABASE MYSQL_USER MYSQL_PASSWORD; do
    if [[ -z "${!required_var:-}" ]]; then
        echo "필수 환경변수가 없습니다: ${required_var}" >&2
        exit 1
    fi
done

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    RUN_STATUS="SKIP_LOCKED"
    echo "이전 파이프라인이 아직 실행 중이므로 이번 실행을 건너뜁니다."
    exit 0
fi

cd "${PROJECT_DIR}"

echo "크롤러 시작"
"${PYTHON_BIN}" "${PROJECT_DIR}/config/car_api_crawler.py"

echo "품질 검증 시작"
"${PYTHON_BIN}" "${PROJECT_DIR}/config/vehicle_quality.py"

QUALITY_REPORT="${PROJECT_DIR}/output/quality-report.json"
if [[ ! -s "${QUALITY_REPORT}" ]]; then
    echo "품질 검증 리포트가 없습니다: ${QUALITY_REPORT}" >&2
    exit 1
fi

if ! grep -q '"quality_status": "PASS"' "${QUALITY_REPORT}"; then
    echo "품질 검증 결과가 PASS가 아닙니다." >&2
    exit 1
fi

RUN_STATUS="PASS"
echo "크롤링·적재·품질 검증 완료"
