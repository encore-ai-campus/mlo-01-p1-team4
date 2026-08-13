#!/usr/bin/env bash

PROJECT_DIR="/home/ec2-user/project"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/car_pipeline.log"

mkdir -p "${LOG_DIR}"
cd "${PROJECT_DIR}" || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 크롤러 시작" >> "${LOG_FILE}"
/usr/bin/python3 src/car_api_crawler.py >> "${LOG_FILE}" 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 크롤러 실패" >> "${LOG_FILE}"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 품질 검증 시작" >> "${LOG_FILE}"
/usr/bin/python3 src/vehicle_quality.py >> "${LOG_FILE}" 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 품질 검증 실패" >> "${LOG_FILE}"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 크롤링 및 품질 검증 완료" >> "${LOG_FILE}"
