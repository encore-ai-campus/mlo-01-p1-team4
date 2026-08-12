#!/usr/bin/env bash

 # 오류가 발생하면 스크립트를 중단하고, 정의되지 않은 변수를 오류로 처리하며,
 # 파이프라인의 명령 중 하나라도 실패하면 전체 명령을 실패로 처리합니다.
set -Eeuo pipefail

# 현재 셸 스크립트가 있는 디렉터리와 MongoDB 초기화 파일 경로를 설정합니다.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MONGODB_INIT_SCRIPT="$SCRIPT_DIR/project1_brand_faq_init.js"

# MongoDB 공식 저장소 설정 파일 경로
MONGODB_REPO_FILE="/etc/yum.repos.d/mongodb-org-8.0.repo"

# MongoDB 설정 파일 경로
MONGODB_CONFIG_FILE="/etc/mongod.conf"

# MongoDB가 모든 IPv4 네트워크 인터페이스에서 접속을 받도록 설정
MONGODB_BIND_IP="0.0.0.0"

# root 계정이 아니면 sudo를 사용하도록 설정
if [[ "${EUID}" -eq 0 ]]; then
    SUDO=""
else
    if ! command -v sudo >/dev/null 2>&1; then
        echo "sudo was not found. Run this script as root." >&2
        exit 1
    fi
    SUDO="sudo"
fi

# dnf가 설치되어 있는지 확인하고, 없으면 yum으로 설치
if ! command -v dnf >/dev/null 2>&1; then
    echo "dnf was not found. Installing dnf with yum."

    if ! command -v yum >/dev/null 2>&1; then
        echo "Neither dnf nor yum was found. Cannot install dnf." >&2
        exit 1
    fi

    $SUDO yum install -y dnf
fi

# 1. Python 3와 pip 설치
echo "[1/10] Python3와 pip를 설치합니다."
$SUDO dnf install -y python3 python3-pip

# 2. Python에서 MongoDB에 연결할 수 있도록 PyMongo 설치
echo "[2/10] Python용 MongoDB Connector를 설치합니다."
$SUDO python3 -m pip install pymongo

# 3. MongoDB 공식 저장소 설정 파일 생성
echo "[3/10] MongoDB 공식 저장소 설정 파일을 생성합니다."
$SUDO tee "$MONGODB_REPO_FILE" > /dev/null <<'EOF'
[mongodb-org-8.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/8.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-8.0.asc
EOF

# 4. DNF 저장소 캐시 초기화 및 저장소 정보 갱신
echo "[4/10] DNF 저장소 캐시를 초기화하고 정보를 갱신합니다."
$SUDO dnf clean all
$SUDO dnf makecache

# 5. MongoDB Community Edition 설치
# gpgkey를 기준으로 DNF가 MongoDB 패키지 서명을 검증합니다.
echo "[5/10] MongoDB Community Edition을 설치합니다."
$SUDO dnf install -y mongodb-org

# 6. 기존 MongoDB 설정 파일 백업
# 설정 변경에 문제가 생기면 이 백업 파일을 사용해 복구할 수 있습니다.
echo "[6/10] 기존 MongoDB 설정 파일을 백업합니다."
MONGODB_CONFIG_BACKUP="${MONGODB_CONFIG_FILE}.$(date +%Y%m%d%H%M%S).bak"
$SUDO cp -a "$MONGODB_CONFIG_FILE" "$MONGODB_CONFIG_BACKUP"

# 7. MongoDB 외부 접속용 bindIp 설정
# 내부망 환경을 전제로 모든 IPv4 인터페이스에서 접속을 허용합니다.
echo "[7/10] MongoDB bindIp를 ${MONGODB_BIND_IP}로 설정합니다."
$SUDO sed -E -i \
    "s|^[[:space:]]*bindIp:.*|  bindIp: ${MONGODB_BIND_IP}|" \
    "$MONGODB_CONFIG_FILE"

# 변경된 bindIp 설정을 출력해 확인
$SUDO grep -nE '^[[:space:]]*bindIp:' "$MONGODB_CONFIG_FILE"

# 8. systemd가 MongoDB 서비스 파일을 다시 인식하도록 갱신
echo "[8/10] systemd를 갱신합니다."
$SUDO systemctl daemon-reload

# 9. MongoDB 서비스를 시작하고 부팅 시 자동 실행하도록 설정
echo "[9/10] MongoDB 서비스를 시작하고 자동 실행을 설정합니다."
$SUDO systemctl enable --now mongod

# bindIp 설정을 서비스에 반영하기 위해 MongoDB 재시작
echo "bindIp 설정을 적용하기 위해 MongoDB를 재시작합니다."
$SUDO systemctl restart mongod

# 10. 같은 디렉터리의 MongoDB 초기화 파일 존재 여부 확인
echo "[10/11] MongoDB 초기화 파일을 확인합니다."
if [[ ! -f "$MONGODB_INIT_SCRIPT" ]]; then
    echo "MongoDB 초기화 파일을 찾을 수 없습니다: $MONGODB_INIT_SCRIPT" >&2
    exit 1
fi

# MongoDB 초기화 파일을 실행해 빈 컬렉션과 인덱스를 생성
echo "MongoDB 초기화 파일을 실행합니다: $MONGODB_INIT_SCRIPT"
$SUDO mongosh --quiet --host 127.0.0.1 --port 27017 "$MONGODB_INIT_SCRIPT"

# 11. 서비스 상태 및 로컬 연결 확인
echo "[11/11] MongoDB 서비스 상태와 로컬 연결을 확인합니다."
$SUDO systemctl --no-pager --full status mongod
mongosh --quiet --eval 'db.runCommand({ ping: 1 })'

echo
echo "MongoDB 설치가 완료되었습니다."
echo "설정 백업 파일: ${MONGODB_CONFIG_BACKUP}"
echo "설정된 bindIp: ${MONGODB_BIND_IP}"
