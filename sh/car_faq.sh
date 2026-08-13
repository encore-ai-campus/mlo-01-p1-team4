#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

RUN_LOG="$LOG_DIR/faq_run.log"
RESULT_LOG="$LOG_DIR/faq_result.log"
ERROR_LOG="$LOG_DIR/faq_error.log"

SOURCE="http://192.168.0.51:4000/faqs"

mkdir -p "$LOG_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 실행 시작 | 수집출처: $SOURCE" >> "$RUN_LOG"

/home/kanghansol/encore-linux-lab/venv/bin/python -u "$SCRIPT_DIR/faq_crawler.py" \
    >> "$RESULT_LOG" \
    2>> "$ERROR_LOG"

EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS | 실행 성공" >> "$RESULT_LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAIL | 종료코드: $EXIT_CODE" >> "$ERROR_LOG"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 실행 종료 | 종료코드: $EXIT_CODE" >> "$RUN_LOG"

exit "$EXIT_CODE"
