# EC2 MongoDB 설치 스크립트 사용 안내

Amazon Linux 2023 EC2에서 MongoDB를 설치하고, 같은 내부망의 웹 서버가 접속할 수 있도록 설정하는 문서입니다.

## 1. 전체 작업 순서

스크립트는 다음 작업을 순서대로 진행합니다.

1. dnf 사용 가능 여부 확인
2. MongoDB 공식 저장소 등록
3. MongoDB Community Edition 설치
4. 설정 파일 백업
5. 외부 접속을 위한 네트워크 설정
6. MongoDB 서비스 시작 및 자동 시작 등록
7. 초기화 파일 실행
8. 서비스와 데이터베이스 접속 확인

## 2. 파일 구조

실행 전 파일을 한 디렉터리에 둡니다.

~~~text
mongodb-install/
├── install_mongodb_ec2.sh
└── MongoDB 초기화 파일
~~~

초기화 파일을 실행하는 경로는 실제 파일 위치와 일치해야 합니다.

## 3. EC2 운영체제 확인

~~~bash
cat /etc/os-release
command -v dnf
~~~

dnf 명령이 없을 때만 다음 명령을 실행합니다.

~~~bash
sudo yum install -y dnf
~~~

## 4. 설치 스크립트 실행

스크립트가 있는 디렉터리로 이동한 뒤 실행 권한을 부여합니다.

~~~bash
cd ~/mongodb-install
chmod +x install_mongodb_ec2.sh
./install_mongodb_ec2.sh
~~~

## 5. MongoDB 저장소 등록

저장소 파일을 엽니다.

~~~bash
sudo nano /etc/yum.repos.d/mongodb-org-8.0.repo
~~~

다음 내용을 저장합니다.

~~~ini
[mongodb-org-8.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/8.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-8.0.asc
~~~

저장소 정보를 갱신합니다.

~~~bash
sudo dnf clean all
sudo dnf makecache
~~~

## 6. MongoDB 설치

~~~bash
sudo dnf install -y mongodb-org
~~~

## 7. 설정 파일 백업

설정을 변경하기 전에 원본 파일을 백업합니다.

~~~bash
sudo cp /etc/mongod.conf /etc/mongod.conf.backup
~~~

문제가 생기면 백업 파일을 참고해 원래 설정으로 되돌릴 수 있습니다.

## 8. 웹 서버 접속 허용 설정

MongoDB 설정 파일을 엽니다.

~~~bash
sudo nano /etc/mongod.conf
~~~

net 항목을 다음과 같이 설정합니다.

~~~yaml
net:
  port: 27017
  bindIp: 0.0.0.0
~~~

0.0.0.0은 모든 네트워크 인터페이스에서 접속을 받을 수 있다는 뜻입니다.
실제 접근 가능한 대역은 AWS 보안 그룹에서 웹 서버로만 제한해야 합니다.

## 9. MongoDB 서비스 시작

~~~bash
sudo systemctl daemon-reload
sudo systemctl enable --now mongod
sudo systemctl restart mongod
~~~

서비스 상태를 확인합니다.

~~~bash
sudo systemctl status mongod --no-pager
~~~

active (running)이 보이면 정상적으로 실행 중입니다.

## 10. 데이터베이스 초기화

초기화 파일의 실제 경로를 넣어 실행합니다.

~~~bash
mongosh --quiet --host 127.0.0.1 --port 27017 < /초기화_파일_경로
~~~

초기화 작업은 다음 구조를 준비합니다.

- project1 데이터베이스
- brand_faq 컬렉션
- 중복 방지를 위한 식별자 인덱스
- 브랜드와 카테고리 조회를 위한 인덱스

이 작업은 기본 구조와 인덱스를 준비하는 단계이며, FAQ 문서를 자동으로 추가하는 작업은 아닙니다.

## 11. 데이터베이스와 컬렉션 확인

MongoDB 서비스가 응답하는지 확인합니다.

~~~bash
mongosh --quiet --eval 'db.runCommand({ ping: 1 })'
~~~

project1 데이터베이스의 컬렉션 목록을 확인합니다.

~~~bash
mongosh --quiet --eval 'printjson(db.getSiblingDB("project1").getCollectionNames())'
~~~

FAQ 문서 개수를 확인합니다.

~~~bash
mongosh --quiet --eval 'print(db.getSiblingDB("project1").brand_faq.countDocuments({}))'
~~~

## 12. AWS 보안 그룹 설정

MongoDB EC2의 인바운드 규칙에 다음 규칙을 추가합니다.

| 항목 | 설정 |
|---|---|
| 유형 | 사용자 지정 TCP |
| 포트 | 27017 |
| 소스 | 웹 서버 보안 그룹 또는 웹 서버의 내부 IP |

0.0.0.0/0으로 전체 인터넷에 공개하지 않습니다.

## 13. 운영 시 주의사항

- bindIp를 열어 둔 만큼 보안 그룹의 소스 범위를 반드시 제한합니다.
- 운영 환경에서는 MongoDB 인증과 강한 비밀번호를 사용합니다.
- 웹 서버에서 관리자 계정으로 접속하지 않습니다.
- 초기화 파일의 경로가 틀리면 구조 생성 단계가 실행되지 않습니다.
- 데이터 입력 후에는 문서 개수와 실제 조회 결과를 함께 확인합니다.

## 14. 정리

이 문서는 MongoDB 설치, 서비스 실행, 내부망 접속 허용, 초기 구조 생성, 상태 확인에 필요한 내용만 정리한 것입니다.
