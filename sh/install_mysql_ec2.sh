#!/usr/bin/env bash

# 오류 발생 시 스크립트를 중단하고 오류 줄 번호를 표시
set -Eeuo pipefail

# 현재 쉘 스크립트가 있는 디렉터리와 실행할 SQL 파일 경로 설정
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/project1_schema.sql"

# 오류 발생 시 오류 줄 번호와 종료 코드 출력
handle_error() {
    local exit_code=$?
    echo "명령 실행 중 오류가 발생했습니다. line ${BASH_LINENO[0]}, exit code ${exit_code}" >&2
    exit "$exit_code"
}

trap handle_error ERR

# root 계정이 아니면 sudo 사용
if [[ "${EUID}" -eq 0 ]]; then
    SUDO=""
else
    if ! command -v sudo >/dev/null 2>&1; then
        echo "sudo 명령어를 찾을 수 없습니다. root 계정으로 실행하세요." >&2
        exit 1
    fi
    SUDO="sudo"
fi

# dnf가 없으면 yum으로 dnf 설치
if ! command -v dnf >/dev/null 2>&1; then
    echo "dnf가 없습니다. yum으로 dnf를 설치합니다."

    if ! command -v yum >/dev/null 2>&1; then
        echo "dnf와 yum을 모두 찾을 수 없어 dnf를 설치할 수 없습니다." >&2
        exit 1
    fi

    # sudo 권한으로 yum을 사용해 dnf 패키지를 자동 설치하고 추가 확인 없이 진행
    $SUDO yum install -y dnf
fi

# root 및 생성할 MySQL 계정의 정보를 직접 작성
MYSQL_ROOT_PASSWORD="root 비밀번호를 입력하세요"
MYSQL_USER="aaa"
MYSQL_PASSWORD="aaa 계정 비밀번호를 입력하세요"

# 1. Python 3와 pip 설치
echo "[1] Python3와 pip를 설치합니다."
$SUDO dnf install -y python3 python3-pip

# 2. Python에서 MySQL에 연결할 수 있도록 Connector 설치
echo "[2] Python용 MySQL Connector를 설치합니다."
$SUDO python3 -m pip install mysql-connector-python

# 3. MySQL 저장소 RPM 다운로드
echo "[3] MySQL 저장소 RPM을 다운로드합니다."
$SUDO wget https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm

# 4. 최신 MySQL GPG 키 다운로드
echo "[4] 최신 MySQL GPG 키를 다운로드합니다."
$SUDO curl -fsSL \
    https://repo.mysql.com/RPM-GPG-KEY-mysql-2025 \
    -o /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025

# 5. RPM 키 저장소에 MySQL GPG 키 등록
echo "[5] MySQL GPG 키를 RPM 키 저장소에 등록합니다."
$SUDO rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025

# 6. 기존 MySQL 저장소의 GPG 키 경로를 2025년 키로 변경
# 최초 실행 시 저장소 파일이 없을 수 있으므로 오류가 나도 다음 단계로 진행
echo "[6] 기존 MySQL 저장소의 GPG 키 경로를 변경합니다."
$SUDO sed -i \
    's/RPM-GPG-KEY-mysql-[0-9]{4}/RPM-GPG-KEY-mysql-2025/g' \
    /etc/yum.repos.d/mysql-community*.repo || true

# 7. DNF 캐시 정리
echo "[7] DNF 캐시를 정리합니다."
$SUDO dnf clean all

# 8. DNF 캐시 폴더 삭제
echo "[8] DNF 캐시 폴더를 삭제합니다."
$SUDO rm -rf /var/cache/dnf

# 9. 저장소 메타데이터 갱신
echo "[9] DNF 저장소 메타데이터를 갱신합니다."
$SUDO dnf makecache

# 10. MySQL 저장소 설치
echo "[10] MySQL 저장소를 설치합니다."
$SUDO dnf install mysql80-community-release-el9-1.noarch.rpm -y

# 11. MySQL 저장소 설치 후 GPG 키 경로를 다시 변경
echo "[11] 설치된 MySQL 저장소의 GPG 키 경로를 변경합니다."
$SUDO sed -i \
    's/RPM-GPG-KEY-mysql-[0-9]{4}/RPM-GPG-KEY-mysql-2025/g' \
    /etc/yum.repos.d/mysql-community*.repo

# 12. 저장소 변경 내용을 반영하기 위해 DNF 메타데이터 갱신
echo "[12] 변경된 MySQL 저장소 정보를 반영합니다."
$SUDO dnf clean all
$SUDO dnf makecache

# 13. MySQL Community Server 설치
echo "[13] MySQL Community Server를 설치합니다."
$SUDO dnf install mysql-community-server -y

# 14. MySQL 서비스 시작 및 부팅 시 자동 실행 설정
echo "[14] MySQL 서비스를 시작하고 자동 실행을 설정합니다."
$SUDO systemctl enable --now mysqld

# MySQL 서비스 재시작
echo "MySQL 서비스를 재시작합니다."
$SUDO systemctl restart mysqld

# MySQL 서비스 상태 확인
echo "MySQL 설치가 완료되었습니다."
mysql --version

# MySQL 서비스의 현재 상태를 페이징 없이 전체 출력
$SUDO systemctl --no-pager --full status mysqld

# MySQL 로그에서 최초 설치 시 생성된 임시 root 비밀번호 확인
echo "임시 MySQL root 비밀번호를 확인합니다."
MYSQL_TEMP_ROOT_PASSWORD="$($SUDO awk '/temporary password/ {print $NF}' /var/log/mysqld.log | tail -n 1)"

if [[ -z "$MYSQL_TEMP_ROOT_PASSWORD" ]]; then
    echo "임시 MySQL root 비밀번호를 찾을 수 없습니다." >&2
    exit 1
fi

# 임시 root 비밀번호로 접속하기 위한 MySQL 옵션 구성
MYSQL_COMMAND=(
    # 만료된 임시 비밀번호 사용 허용
    --connect-expired-password
    # MySQL root 계정으로 접속
    -u root
    # 설치 과정에서 생성된 임시 root 비밀번호 사용
    -p"$MYSQL_TEMP_ROOT_PASSWORD"
)

# 임시 root 비밀번호로 MySQL에 접속해 설정 SQL 실행
echo "root 비밀번호를 변경하고 ${MYSQL_USER}@% 계정을 생성합니다."
$SUDO mysql "${MYSQL_COMMAND[@]}" <<SQL
# root 계정 비밀번호를 하드코딩한 비밀번호로 변경
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';

# 지정한 계정이 없으면 생성
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';

# 지정한 계정의 비밀번호 변경
ALTER USER '${MYSQL_USER}'@'%'
IDENTIFIED BY '${MYSQL_PASSWORD}';

# 지정한 계정에 모든 데이터베이스와 테이블의 전체 권한 부여
GRANT ALL PRIVILEGES ON *.* TO '${MYSQL_USER}'@'%' WITH GRANT OPTION;

# 변경된 권한을 즉시 반영
FLUSH PRIVILEGES;
SQL

echo "root 비밀번호 설정 및 ${MYSQL_USER}@% 계정 생성이 완료되었습니다."

# 스크립트와 같은 디렉터리의 SQL 파일이 있는지 확인
if [[ ! -f "$SQL_FILE" ]]; then
    echo "SQL 파일을 찾을 수 없습니다: $SQL_FILE" >&2
    exit 1
fi

# 생성한 MySQL 계정으로 SQL 파일 실행
echo "SQL 파일을 실행합니다: $SQL_FILE"
$SUDO mysql \
    -u "$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" \
    < "$SQL_FILE"

echo "SQL 파일 실행이 완료되었습니다."

