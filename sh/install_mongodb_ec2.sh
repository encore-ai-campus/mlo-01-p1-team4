#!/usr/bin/env bash

# 오류가 발생하거나 정의되지 않은 변수를 사용하면 즉시 종료합니다.
set -Eeuo pipefail

# 현재 위치와 관계없이 실행할 수 있도록 스크립트 기준 경로를 사용합니다.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MONGODB_INIT_SCRIPT="$SCRIPT_DIR/project1_brand_faq_init.js"

# MongoDB 저장소와 설정 파일 경로입니다.
MONGODB_REPO_FILE="/etc/yum.repos.d/mongodb-org-8.0.repo"
MONGODB_CONFIG_FILE="/etc/mongod.conf"
MONGODB_BIND_IP="0.0.0.0"

# root 계정이 아닌 경우 sudo를 사용합니다.
if [[ "${EUID}" -eq 0 ]]; then
    SUDO=""
else
    if ! command -v sudo >/dev/null 2>&1; then
        echo "sudo를 찾을 수 없습니다. root 계정으로 실행하세요." >&2
        exit 1
    fi
    SUDO="sudo"
fi

# dnf가 없을 때만 yum으로 dnf를 설치합니다.
if ! command -v dnf >/dev/null 2>&1; then
    echo "dnf가 없습니다. yum으로 dnf를 설치합니다."

    if ! command -v yum >/dev/null 2>&1; then
        echo "dnf와 yum을 모두 찾을 수 없어 dnf를 설치할 수 없습니다." >&2
        exit 1
    fi

    $SUDO yum install -y dnf
fi

# 1. MongoDB 공식 저장소 설정 파일을 생성합니다.
echo "[1/9] MongoDB 공식 저장소 설정 파일을 생성합니다."
$SUDO tee "$MONGODB_REPO_FILE" > /dev/null <<'EOF'
[mongodb-org-8.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/8.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-8.0.asc
EOF

# 2. DNF 저장소 정보를 갱신합니다.
echo "[2/9] DNF 저장소 정보를 갱신합니다."
$SUDO dnf clean all
$SUDO dnf makecache

# 3. MongoDB Community Edition을 설치합니다.
echo "[3/9] MongoDB Community Edition을 설치합니다."
$SUDO dnf install -y mongodb-org

# 4. 기존 MongoDB 설정 파일을 백업합니다.
echo "[4/9] 기존 MongoDB 설정 파일을 백업합니다."
MONGODB_CONFIG_BACKUP="${MONGODB_CONFIG_FILE}.$(date +%Y%m%d%H%M%S).bak"
$SUDO cp -a "$MONGODB_CONFIG_FILE" "$MONGODB_CONFIG_BACKUP"

# 5. 모든 IPv4 인터페이스에서 접속을 받을 수 있도록 설정합니다.
echo "[5/9] MongoDB bindIp를 ${MONGODB_BIND_IP}(으)로 설정합니다."
$SUDO sed -E -i \
    "s|^[[:space:]]*bindIp:.*|  bindIp: ${MONGODB_BIND_IP}|" \
    "$MONGODB_CONFIG_FILE"

# bindIp 설정이 적용되었는지 확인합니다.
$SUDO grep -nE '^[[:space:]]*bindIp:' "$MONGODB_CONFIG_FILE"

# 6. 현재 서비스 설정을 반영하도록 systemd를 다시 불러옵니다.
echo "[6/9] systemd를 다시 불러옵니다."
$SUDO systemctl daemon-reload

# 7. MongoDB를 시작하고 재부팅 후 자동 실행되도록 설정합니다.
echo "[7/9] MongoDB를 시작하고 자동 실행을 설정합니다."
$SUDO systemctl enable --now mongod

# 실행 중인 서비스에 bindIp 설정을 적용하기 위해 MongoDB를 재시작합니다.
echo "bindIp 설정을 적용하기 위해 MongoDB를 재시작합니다."
$SUDO systemctl restart mongod

# 8. MongoDB 초기화 파일을 확인하고 실행합니다.
echo "[8/9] MongoDB 초기화 파일을 확인합니다."
if [[ ! -f "$MONGODB_INIT_SCRIPT" ]]; then
    echo "MongoDB 초기화 파일을 찾을 수 없습니다: $MONGODB_INIT_SCRIPT" >&2
    exit 1
fi

echo "MongoDB 초기화 파일을 실행합니다: $MONGODB_INIT_SCRIPT"
$SUDO mongosh --quiet --host 127.0.0.1 --port 27017 "$MONGODB_INIT_SCRIPT"

# 9. MongoDB 서비스 상태와 로컬 접속을 확인합니다.
echo "[9/9] MongoDB 서비스 상태와 로컬 접속을 확인합니다."
$SUDO systemctl --no-pager --full status mongod
mongosh --quiet --eval 'db.runCommand({ ping: 1 })'

echo
echo "MongoDB 설치가 완료되었습니다."
echo "설정 백업 파일: ${MONGODB_CONFIG_BACKUP}"
echo "설정된 bindIp: ${MONGODB_BIND_IP}"
