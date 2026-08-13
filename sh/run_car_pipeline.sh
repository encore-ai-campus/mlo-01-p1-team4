#!/usr/bin/env bash

PROJECT_DIR="/home/ec2-user/first-pj-web"
ENV_FILE="${PROJECT_DIR}/.env"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/car_pipeline.log"
QUALITY_REPORT="${PROJECT_DIR}/quality_check_output/quality-report.json"

mkdir -p "${LOG_DIR}"
cd "${PROJECT_DIR}" || exit 1

if [ ! -r "${ENV_FILE}" ]; then
    echo "환경변수 파일이 없습니다: ${ENV_FILE}" >&2
    exit 1
fi

if [ ! -x "${PYTHON_BIN}" ]; then
    echo "가상환경 Python이 없습니다: ${PYTHON_BIN}" >&2
    exit 1
fi

set -a
. "${ENV_FILE}"
set +a

echo "[$(date '+%Y-%m-%d %H:%M:%S')] pipeline_start" >> "${LOG_FILE}"
"${PYTHON_BIN}" "${PROJECT_DIR}/src/car_api_crawler.py" >> "${LOG_FILE}" 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] crawler_fail" >> "${LOG_FILE}"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] quality_start" >> "${LOG_FILE}"
"${PYTHON_BIN}" "${PROJECT_DIR}/src/vehicle_quality.py" >> "${LOG_FILE}" 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] quality_fail" >> "${LOG_FILE}"
    exit 1
fi

if [ ! -s "${QUALITY_REPORT}" ]; then
    echo "품질 결과 파일이 없습니다: ${QUALITY_REPORT}" >&2
    exit 1
fi

if ! grep -q '"quality_status": "PASS"' "${QUALITY_REPORT}"; then
    echo "품질 검증 결과가 PASS가 아닙니다." >&2
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] pipeline_pass" >> "${LOG_FILE}"
