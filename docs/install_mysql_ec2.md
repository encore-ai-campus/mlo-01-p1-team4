# EC2 MySQL 설치 스크립트 사용 안내

Amazon Linux 2023 EC2에 MySQL Community Server를 설치하고, 프로젝트용 데이터베이스와 테이블을 준비하는 문서입니다.

## 1. 전체 작업 순서

스크립트는 다음 작업을 순서대로 진행합니다.

1. dnf 사용 가능 여부 확인
2. MySQL 공식 저장소와 서명 키 등록
3. MySQL Community Server 설치
4. MySQL 서비스 시작 및 자동 시작 등록
5. 초기 root 비밀번호 확인과 변경
6. 웹 서버용 DB 계정 생성
7. 스키마 파일 실행
8. 데이터베이스와 테이블 확인

## 2. 파일 구조

실행 전 파일을 한 디렉터리에 둡니다.

~~~text
mysql-install/
├── install_mysql_ec2.sh
└── project1_schema.sql
~~~

스키마 파일을 실행하는 경로는 실제 파일 위치와 일치해야 합니다.

## 3. 설치 변수 확인

설치 스크립트의 계정 설정을 확인합니다.

~~~bash
MYSQL_ROOT_PASSWORD='root_password_here'
MYSQL_USER='web_user'
MYSQL_PASSWORD='web_password_here'
~~~

괄호 안의 예시 값은 실제 사용할 값으로 변경합니다.
비밀번호는 다른 사람에게 공유하지 않습니다.

## 4. EC2 운영체제 확인

~~~bash
cat /etc/os-release
command -v dnf
~~~

dnf 명령이 없을 때만 다음 명령을 실행합니다.

~~~bash
sudo yum install -y dnf
~~~

## 5. 설치 스크립트 실행

스크립트가 있는 디렉터리로 이동한 뒤 실행 권한을 부여합니다.

~~~bash
cd ~/mysql-install
chmod +x install_mysql_ec2.sh
./install_mysql_ec2.sh
~~~

## 6. MySQL 저장소 등록

필요한 도구를 설치합니다.

~~~bash
sudo dnf install -y wget curl
~~~

MySQL 저장소 패키지를 내려받아 설치합니다.

~~~bash
sudo wget -O /tmp/mysql80-community-release-el9-1.noarch.rpm https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm
sudo rpm -Uvh /tmp/mysql80-community-release-el9-1.noarch.rpm
~~~

공식 서명 키를 등록합니다.

~~~bash
sudo curl -fsSL https://repo.mysql.com/RPM-GPG-KEY-mysql-2025 -o /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025
sudo rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025
~~~

저장소의 키 경로를 확인하거나 수정합니다.

~~~bash
sudo nano /etc/yum.repos.d/mysql-community.repo
~~~

gpgkey 항목이 다음 경로를 사용하도록 확인합니다.

~~~ini
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-mysql-2025
~~~

## 7. MySQL 설치와 서비스 시작

저장소 정보를 갱신합니다.

~~~bash
sudo dnf clean all
sudo rm -rf /var/cache/dnf
sudo dnf makecache
~~~

MySQL 서버를 설치합니다.

~~~bash
sudo dnf install -y mysql-community-server
~~~

서비스를 시작하고 EC2 재부팅 후에도 자동으로 실행되도록 설정합니다.

~~~bash
sudo systemctl enable --now mysqld
sudo systemctl restart mysqld
sudo systemctl status mysqld --no-pager
~~~

active (running)이 보이면 정상적으로 실행 중입니다.

## 8. root 계정 비밀번호 설정

설치 직후 생성된 임시 비밀번호를 확인합니다.

~~~bash
sudo grep 'temporary password' /var/log/mysqld.log
~~~

확인한 임시 비밀번호로 접속합니다.

~~~bash
mysql --connect-expired-password -u root -p
~~~

MySQL 화면에서 root 비밀번호를 변경합니다.

~~~sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '새로운_root_비밀번호';
~~~

비밀번호 정책에 맞는 대문자, 소문자, 숫자, 특수문자를 사용합니다.

## 9. 웹 서버용 계정 생성

root 계정으로 MySQL에 접속한 상태에서 실행합니다.

~~~sql
CREATE USER IF NOT EXISTS 'web_user'@'%' IDENTIFIED BY '웹_사용자_비밀번호';
ALTER USER 'web_user'@'%' IDENTIFIED BY '웹_사용자_비밀번호';
GRANT ALL PRIVILEGES ON project1.* TO 'web_user'@'%';
FLUSH PRIVILEGES;
~~~

웹 애플리케이션은 root 계정 대신 web_user를 사용합니다.
실제 운영 환경에서는 필요한 범위의 권한만 부여하는 것이 안전합니다.

## 10. 프로젝트 스키마 적용

스키마 파일을 실행합니다.

~~~bash
mysql -u web_user -p < /경로/project1_schema.sql
~~~

비밀번호를 물으면 웹 서버용 DB 계정의 비밀번호를 입력합니다.

스키마 파일은 프로젝트 데이터베이스와 차량 데이터 조회에 필요한 테이블 및 인덱스를 준비합니다.

## 11. 설치 결과 확인

데이터베이스 목록을 확인합니다.

~~~bash
mysql -u web_user -p -e "SHOW DATABASES;"
~~~

프로젝트 데이터베이스의 테이블을 확인합니다.

~~~bash
mysql -u web_user -p -e "USE project1; SHOW TABLES;"
~~~

## 12. AWS 보안 그룹 설정

MySQL EC2의 인바운드 규칙에 다음 규칙을 추가합니다.

| 항목 | 설정 |
|---|---|
| 유형 | 사용자 지정 TCP |
| 포트 | 3306 |
| 소스 | 웹 서버 보안 그룹 또는 웹 서버의 내부 IP |

0.0.0.0/0으로 전체 인터넷에 공개하지 않습니다.

## 13. 운영 시 주의사항

- 웹 서버에서 root 계정으로 접속하지 않습니다.
- DB 비밀번호를 문서, 소스 코드, 공개 저장소에 남기지 않습니다.
- 스키마 파일의 실제 경로가 틀리면 테이블이 생성되지 않습니다.
- 웹 서버가 접속할 수 있도록 보안 그룹의 포트와 소스 범위를 확인합니다.
- 설치 후 SHOW DATABASES와 SHOW TABLES로 실제 생성 결과를 확인합니다.

## 14. 정리

이 문서는 MySQL 설치, 서비스 실행, 계정 생성, 스키마 적용, 내부망 접속 허용, 설치 결과 확인에 필요한 내용만 정리한 것입니다.
