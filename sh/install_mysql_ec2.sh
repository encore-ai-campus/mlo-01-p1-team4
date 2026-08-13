#!/usr/bin/env bash

# 오류가 발생하거나 정의되지 않은 변수를 사용하면 즉시 종료합니다.
set -Eeuo pipefail

# 스크립트 기준으로 경로를 설정합니다.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/project1_schema.sql"

# 오류가 발생한 줄 번호와 종료 코드를 출력합니다.
handle_error() {
    local exit_code=$?
    echo "명령 실행 중 오류가 발생했습니다. 줄 번호: ${BASH_LINENO[0]}, 종료 코드: ${exit_code}" >&2
    exit "$exit_code"
}

trap handle_error ERR

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

# 실행 전에 아래 예시 값을 실제 계정 정보로 변경합니다.
MYSQL_ROOT_PASSWORD="CHANGE_ME_ROOT_PASSWORD"
MYSQL_USER="aaa"
MYSQL_PASSWORD="CHANGE_ME_MYSQL_PASSWORD"

MYSQL_ALREADY_INSTALLED=false

if command -v mysql >/dev/null 2>&1 && \
   rpm -q mysql-community-server >/dev/null 2>&1; then

    MYSQL_ALREADY_INSTALLED=true
    echo "MySQL Community Server가 이미 설치되어 있습니다."

else

# 1. MySQL 저장소 RPM을 다운로드합니다.
echo "[1/12] MySQL 저장소 RPM을 다운로드합니다."
$SUDO wget https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm

# 2. 최신 MySQL GPG 키를 다운로드합니다.
echo "[2/12] 최신 MySQL GPG 키를 다운로드합니다."
$SUDO curl -fsSL \
    https://repo.mysql.com/RPM-GPG-KEY-mysql-2025 \
    -o /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025

# 3. MySQL GPG 키를 등록합니다.
echo "[3/12] MySQL GPG 키를 등록합니다."
$SUDO rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025

# 4. 기존 저장소 파일의 GPG 키 경로를 수정합니다.
echo "[4/12] MySQL 저장소의 GPG 키 경로를 수정합니다."
$SUDO sed -i \
    's/RPM-GPG-KEY-mysql-[0-9]{4}/RPM-GPG-KEY-mysql-2025/g' \
    /etc/yum.repos.d/mysql-community*.repo || true

# 5. DNF 캐시를 정리합니다.
echo "[5/12] DNF 캐시를 정리합니다."
$SUDO dnf clean all

# 6. 기존 DNF 캐시 폴더를 삭제합니다.
echo "[6/12] 기존 DNF 캐시 폴더를 삭제합니다."
$SUDO rm -rf /var/cache/dnf

# 7. 저장소 메타데이터를 갱신합니다.
echo "[7/12] DNF 저장소 메타데이터를 갱신합니다."
$SUDO dnf makecache

# 8. MySQL 저장소 패키지를 설치합니다.
echo "[8/12] MySQL 저장소 패키지를 설치합니다."
$SUDO dnf install mysql80-community-release-el9-1.noarch.rpm -y

# 9. 저장소 패키지 설치 후 GPG 키 경로를 다시 수정합니다.
echo "[9/12] 설치된 MySQL 저장소의 GPG 키 경로를 수정합니다."
$SUDO sed -i \
    's/RPM-GPG-KEY-mysql-[0-9]{4}/RPM-GPG-KEY-mysql-2025/g' \
    /etc/yum.repos.d/mysql-community*.repo

# 10. 저장소 변경 사항을 반영하기 위해 DNF 정보를 다시 갱신합니다.
echo "[10/12] 저장소 변경 후 DNF 정보를 다시 갱신합니다."
$SUDO dnf clean all
$SUDO dnf makecache

# 11. MySQL Community Server를 설치합니다.
echo "[11/12] MySQL Community Server를 설치합니다."
$SUDO dnf install mysql-community-server -y
fi

# 12. MySQL을 시작하고 자동 실행을 설정합니다.
if [[ "$MYSQL_ALREADY_INSTALLED" == false ]]; then
    echo "[12/12] MySQL을 시작하고 자동 실행을 설정합니다."
    $SUDO systemctl enable --now mysqld

    # 현재 설정을 적용하기 위해 MySQL을 재시작합니다.
    echo "MySQL을 재시작합니다."
    $SUDO systemctl restart mysqld

    # 설치된 버전과 서비스 상태를 출력합니다.
    echo "MySQL 설치가 완료되었습니다."
    mysql --version
    $SUDO systemctl --no-pager --full status mysqld

    # 최초 설치 때 생성된 임시 root 비밀번호를 읽습니다.
    echo "임시 MySQL root 비밀번호를 확인합니다."
    MYSQL_TEMP_ROOT_PASSWORD="$($SUDO awk '/temporary password/ {print $NF}' /var/log/mysqld.log | tail -n 1)"

    if [[ -z "$MYSQL_TEMP_ROOT_PASSWORD" ]]; then
        echo "임시 MySQL root 비밀번호를 찾을 수 없습니다." >&2
        exit 1
    fi

    # 임시 root 비밀번호로 접속할 명령을 구성합니다.
    MYSQL_COMMAND=(
        --connect-expired-password
        -u root
        -p"$MYSQL_TEMP_ROOT_PASSWORD"
    )

    # root 비밀번호를 변경하고 프로젝트 계정을 생성합니다.
    echo "root 비밀번호를 변경하고 ${MYSQL_USER}@% 계정을 생성합니다."
    $SUDO mysql "${MYSQL_COMMAND[@]}" <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';

CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';

ALTER USER '${MYSQL_USER}'@'%'
IDENTIFIED BY '${MYSQL_PASSWORD}';

GRANT ALL PRIVILEGES ON *.* TO '${MYSQL_USER}'@'%' WITH GRANT OPTION;

FLUSH PRIVILEGES;
SQL

    echo "root 비밀번호와 ${MYSQL_USER}@% 계정 설정이 완료되었습니다."

# 스키마 파일은 이 스크립트와 같은 디렉터리에 있어야 합니다.
if [[ ! -f "$SQL_FILE" ]]; then
    echo "SQL 스키마 파일을 찾을 수 없습니다: $SQL_FILE" >&2
    exit 1
fi

# 생성한 MySQL 계정으로 프로젝트 스키마를 적용합니다.
echo "SQL 스키마 파일을 실행합니다: $SQL_FILE"
$SUDO mysql \
    -u "$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" \
    < "$SQL_FILE"

echo "SQL 스키마 적용이 완료되었습니다."
fi
