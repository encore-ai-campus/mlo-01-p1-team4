# EC2 MySQL 설치 스크립트 사용 안내

이 문서는 스크립트명이 [`install_mysql_ec2.sh`](./install_mysql_ec2.sh)를 기준으로 작성되었습니다.
스크립트는 Amazon Linux 계열 EC2에서 다음 작업을 순서대로 수행합니다.

1. `dnf` 사용 가능 여부 확인
2. Python 3와 pip 설치
3. `mysql-connector-python` 설치
4. MySQL 저장소 RPM 및 GPG 키 설정
5. MySQL Community Server 설치
6. MySQL 서비스 시작 및 재시작
7. 임시 root 비밀번호 확인
8. root 비밀번호 변경
9. 원격 접속용 MySQL 계정 생성
10. 같은 디렉터리의 SQL 스키마 파일 실행

## 디렉터리 구성

스크립트는 `project1_schema.sql` 파일을 스크립트와 같은 디렉터리에서 찾습니다.

```text
mysql-install/
├── install_mysql_ec2.sh
└── project1_schema.sql
```

SQL 파일명이 다르면 스크립트의 다음 값을 실제 파일명으로 변경해야 합니다.

```bash
SQL_FILE="$SCRIPT_DIR/project1_schema.sql"
```
`다른 sql 파일이 실행됨을 방지하기 위함이며 최초 기본 설정 스크립트인점을 감안해서 설계하였습니다.

## 실행 전 설정

스크립트 상단의 계정 정보를 실제 값으로 수정합니다.

```bash
MYSQL_ROOT_PASSWORD="root 비밀번호"
MYSQL_USER="aaa"
MYSQL_PASSWORD="aaa 계정 비밀번호"
```
`해당 라인의 설정할 root 비밀번호를 입력하고 생성할 user를 입력하면 스크립트 실행시 생성하는 로직으로 설계하였습니다. 
MYSQL_ROOT_PASSWORD`는 최초 설치 후 root 계정에 설정할 비밀번호입니다.
`MYSQL_USER`와 `MYSQL_PASSWORD`는 원격 접속에 사용할 별도 계정 정보입니다.

## 실행 권한 부여

```bash
chmod +x install_mysql_ec2.sh
```

## 스크립트 실행

```bash
./install_mysql_ec2.sh
```

스크립트는 root 계정으로 실행하거나, 실행 계정에 `sudo` 권한이 있어야 합니다.

## Python 설치

다음 패키지를 설치합니다.

```bash
sudo dnf install -y python3 python3-pip
```

이후 Python에서 MySQL에 연결하기 위한 커넥터를 설치합니다.

```bash
sudo python3 -m pip install mysql-connector-python
```

## MySQL 저장소 설정

스크립트는 다음 순서로 MySQL 저장소를 설정합니다.

```bash
sudo wget https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm
```

```bash
sudo curl -fsSL \
  https://repo.mysql.com/RPM-GPG-KEY-mysql-2025 \
  -o /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025
```

```bash
sudo rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025
```

저장소 설치 후 GPG 키 경로를 2025년 키 경로로 변경합니다.

```bash
sudo sed -i \
  's/RPM-GPG-KEY-mysql-[0-9]{4}/RPM-GPG-KEY-mysql-2025/g' \
  /etc/yum.repos.d/mysql-community*.repo
```

## MySQL 설치 및 서비스 시작

저장소 메타데이터를 갱신한 뒤 MySQL Community Server를 설치합니다.

```bash
sudo dnf clean all
sudo rm -rf /var/cache/dnf
sudo dnf makecache
sudo dnf install mysql-community-server -y
```

서비스는 다음 명령으로 시작하고 부팅 시 자동 실행하도록 설정합니다.

```bash
sudo systemctl enable --now mysqld
sudo systemctl restart mysqld
```

서비스 상태 확인:

```bash
sudo systemctl --no-pager --full status mysqld
```

## root 비밀번호 변경 및 계정 생성

MySQL 최초 설치 시 `/var/log/mysqld.log`에 임시 root 비밀번호가 기록됩니다. 스크립트가 해당 값을 확인해 MySQL에 접속합니다.

```bash
MYSQL_TEMP_ROOT_PASSWORD="$($SUDO awk '/temporary password/ {print $NF}' /var/log/mysqld.log | tail -n 1)"
```
이후 다음 SQL을 실행합니다.

```sql
ALTER USER 'root'@'localhost'
IDENTIFIED BY 'MYSQL_ROOT_PASSWORD 값';

CREATE USER IF NOT EXISTS 'MYSQL_USER 값'@'%'
IDENTIFIED BY 'MYSQL_PASSWORD 값';

ALTER USER 'MYSQL_USER 값'@'%'
IDENTIFIED BY 'MYSQL_PASSWORD 값';

GRANT ALL PRIVILEGES ON *.*
TO 'MYSQL_USER 값'@'%'
WITH GRANT OPTION;

FLUSH PRIVILEGES;
```

## SQL 파일 실행

root 및 별도 계정 생성이 끝나면 스크립트와 같은 디렉터리의 `project1_schema.sql`을 실행합니다.

```bash
$SUDO mysql \
    -u "$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" \
    < "$SQL_FILE"
```

SQL 파일에는 데이터베이스 생성, 테이블 생성, 인덱스 생성 등의 구문을 작성할 수 있습니다.

## 외부 접속에 필요한 AWS 설정

MySQL 계정의 Host가 `%`이므로 MySQL 내부에서는 모든 호스트에서 접속할 수 있습니다. 하지만 실제 외부 접속은 EC2 Security Group이 허용해야 합니다.
Security Group 인바운드 규칙:

```text
Protocol: TCP
Port: 3306
Source: 허용할 IP/32 또는 필요한 Security Group
```
`0.0.0.0/0`은 모든 인터넷에서 접속할 수 있으므로 운영 환경에서는 사용하지 않는 걸 상정합니다.

## Python 소스에서 접속

설치된 커넥터는 다음과 같이 사용할 수 있습니다.

```python
import mysql.connector

connection = mysql.connector.connect(
    host="EC2_PUBLIC_IP 또는 DNS",
    port=3306,
    user="aaa",
    password="aaa 계정 비밀번호",
    database="project1",
)
```

운영 환경에서는 DB 주소와 비밀번호를 Python 소스에 직접 작성하지 말고 환경변수, AWS Systems Manager Parameter Store 또는 AWS Secrets Manager를 사용하는 것이 좋습니다.

## 주요 주의사항

- `MYSQL_ROOT_PASSWORD`와 `MYSQL_PASSWORD`는 스크립트에 평문으로 저장됩니다.
- `aaa@'%'` 계정에는 전체 권한과 `WITH GRANT OPTION`이 부여됩니다.
- MySQL CLI에 `-p비밀번호`를 사용하면 비밀번호 관련 보안 경고가 출력될 수 있습니다.
- Amazon Linux 2023에서는 `curl-minimal`이 기본 설치되어 일반 `curl` 패키지와 충돌할 수 있습니다.
- `project1_schema.sql` 파일이 스크립트와 같은 디렉터리에 있어야 합니다.
- 설치 저장소에 접근하려면 EC2에 Internet Gateway, NAT Gateway 또는 적절한 VPC Endpoint 경로가 필요합니다.

##  설계의도

- `최초 아무것도 존재하지 않는 Ec2 작업시 일일히 Python 및 mysql을 설치하고 최초 DB 테이블 세팅에 대한 부담을 줄이기 위함입니다.
- `해당 스크립트를 실행할 경우 Python 및 Python Connector가 설치되며 이후 순차적으로 mysql 설치를 완료합니다.
- `이후 Mysql 설치가 완료되면 최초 root 계정 및 사전에 세팅한 admin 권한을 가진 user 계정을 생성합니다.
- `admin 권한을 가진 user 계정 기반으로 사전에 적재한 .sql 파일을 실행함으로써 기본적인 테이블 세팅이 완료되므로 효율적으로 생각할수 있겠습니다.

