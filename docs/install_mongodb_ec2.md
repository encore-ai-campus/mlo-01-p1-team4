# EC2 MongoDB 설치 스크립트 사용 안내

이 문서는 [`install_mongodb_ec2.sh`](./install_mongodb_ec2.sh)를 기준으로 작성되었습니다.

스크립트는 Amazon Linux 2023 EC2에서 다음 작업을 순서대로 수행합니다.

1. `dnf` 사용 가능 여부 확인 및 설치
2. Python 3와 pip 설치
3. Python용 PyMongo 설치
4. MongoDB 공식 저장소 설정
5. MongoDB Community Edition 설치
6. MongoDB 설정 파일 백업
7. `bindIp`를 `0.0.0.0`으로 변경
8. MongoDB 서비스 시작 및 재시작
9. MongoDB 초기화 JS 파일 실행
10. MongoDB 서비스 상태 및 접속 확인

## 디렉터리 구성

두 파일은 같은 디렉터리에 있어야 합니다.

```text
mongodb-install/
├── install_mongodb_ec2.sh
└── project1_brand_faq_init.js
```

셸 스크립트는 현재 스크립트가 있는 디렉터리를 기준으로 다음 파일을 찾습니다.

```bash
MONGODB_INIT_SCRIPT="$SCRIPT_DIR/project1_brand_faq_init.js"
```

초기화 파일명이 다르면 셸 스크립트의 해당 값을 변경해야 합니다.

## 실행 전 운영체제 확인

이 스크립트는 Amazon Linux 2023 환경을 기준으로 작성되었습니다.

```bash
cat /etc/os-release
```

`dnf`가 설치되어 있지 않으면 스크립트가 `yum`을 사용해 `dnf`를 설치합니다.

```bash
sudo yum install -y dnf
```

## 실행 권한 부여

```bash
chmod +x install_mongodb_ec2.sh
```

## 스크립트 실행

```bash
./install_mongodb_ec2.sh
```

스크립트는 root 계정으로 실행하거나, 실행 계정에 `sudo` 권한이 있어야 합니다.

## Python 및 PyMongo 설치

Python 3와 pip를 설치합니다.

```bash
sudo dnf install -y python3 python3-pip
```

Python에서 MongoDB에 연결할 수 있도록 PyMongo를 설치합니다.

```bash
sudo python3 -m pip install pymongo
```

Python 소스에서는 다음과 같이 사용할 수 있습니다.

```python
from pymongo import MongoClient

client = MongoClient("mongodb://MongoDB_IP_address:27017")
database = client["project1"]
```

## MongoDB 저장소 설정

스크립트는 MongoDB 8.0 Amazon Linux 2023 저장소 파일을 생성합니다.

```ini
[mongodb-org-8.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/8.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-8.0.asc
```

저장소 캐시를 초기화하고 저장소 정보를 갱신합니다.

```bash
sudo dnf clean all
sudo dnf makecache
```

## MongoDB 설치

MongoDB Community Edition을 설치합니다.

```bash
sudo dnf install -y mongodb-org
```

## MongoDB 설정 파일 백업

설정 변경 전에 `/etc/mongod.conf`를 날짜와 시간이 포함된 파일명으로 백업합니다.

```bash
MONGODB_CONFIG_BACKUP="/etc/mongod.conf.$(date +%Y%m%d%H%M%S).bak"
sudo cp -a /etc/mongod.conf "$MONGODB_CONFIG_BACKUP"
```

설정 변경에 문제가 발생하면 백업 파일을 사용해 복구할 수 있습니다.

## bindIp 설정

MongoDB 설정 파일의 `bindIp`를 `0.0.0.0`으로 변경합니다.

```yaml
net:
  bindIp: 0.0.0.0
```

`0.0.0.0`은 모든 IPv4 네트워크 인터페이스에서 접속을 받도록 설정합니다. 실제 외부 접속 가능 여부는 AWS Security Group 규칙에도 영향을 받습니다.

변경된 설정은 다음 명령으로 확인할 수 있습니다.

```bash
sudo grep -nE '^[[:space:]]*bindIp:' /etc/mongod.conf
```

## MongoDB 서비스 시작 및 재시작

systemd 설정을 갱신하고 MongoDB를 시작합니다. 또한 EC2가 재부팅될 때 MongoDB가 자동으로 실행되도록 설정합니다.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mongod
sudo systemctl restart mongod
```

## MongoDB 초기화 JS 파일 실행

셸 스크립트는 같은 디렉터리에 있는 `project1_brand_faq_init.js` 파일을 확인한 뒤 `mongosh`로 실행합니다.

```bash
mongosh \
  --quiet \
  --host 127.0.0.1 \
  --port 27017 \
  project1_brand_faq_init.js
```

초기화 파일은 최초 데이터 삽입 없이 다음 작업만 수행합니다.

- `project1` 데이터베이스 선택
- 빈 `brand_faq` 컬렉션 생성
- `{ source_id: 1, faq_id: 1 }` 고유 인덱스 생성
- `{ brand_en: 1, brand: 1, category: 1 }` 검색용 인덱스 생성

초기화 JS 파일의 주요 구문은 다음과 같습니다.

```javascript
// project1 데이터베이스를 선택합니다.
const project1Db = db.getSiblingDB("project1");

// brand_faq 컬렉션이 없을 때만 빈 컬렉션을 생성합니다.
if (!project1Db.getCollectionNames().includes("brand_faq")) {
  project1Db.createCollection("brand_faq");
}

// source_id와 faq_id 조합에 중복을 허용하지 않는 고유 인덱스를 생성합니다.
project1Db.brand_faq.createIndex(
  { source_id: 1, faq_id: 1 },
  { unique: true }
);

// 브랜드와 카테고리 검색을 위한 인덱스를 생성합니다.
project1Db.brand_faq.createIndex(
  { brand_en: 1, brand: 1, category: 1 }
);
```

`.js` 파일에서는 `use project1;` 대신 `db.getSiblingDB("project1")` 방식을 사용해야 합니다.

## 서비스 상태 및 접속 확인

MongoDB 서비스 상태를 확인합니다.

```bash
sudo systemctl --no-pager --full status mongod
```

MongoDB에 정상적으로 접속되는지 확인합니다.

```bash
mongosh --quiet --eval 'db.runCommand({ ping: 1 })'
```

컬렉션과 인덱스를 확인합니다.

```bash
mongosh --quiet --eval '
const project1Db = db.getSiblingDB("project1");
printjson(project1Db.getCollectionNames());
printjson(project1Db.brand_faq.getIndexes());
'
```

## AWS Security Group 설정

MongoDB 외부 접속을 위해 EC2 Security Group에서 TCP `27017` 포트를 허용해야 합니다.

```text
Protocol: TCP
Port: 27017
Source: Web 서버 EC2의 Security Group 또는 허용할 내부 IP 대역
```

`0.0.0.0/0`은 모든 인터넷에서 접속할 수 있으므로 운영 환경에서는 사용하지 않는 것이 좋습니다.

## 주요 주의사항

- `bindIp: 0.0.0.0`은 모든 IPv4 인터페이스에서 접속을 받도록 설정합니다.
- MongoDB 인증이 현재 활성화되어 있지 않으므로 운영 환경에서는 계정 인증을 설정해야 합니다.
- AWS Security Group에서는 `27017` 포트를 Web 서버 또는 내부망으로 제한하는 것이 좋습니다.
- `install_mongodb_ec2.sh`와 `project1_brand_faq_init.js`는 반드시 같은 디렉터리에 있어야 합니다.
- 초기화 JS 파일은 데이터를 삽입하지 않고 컬렉션과 인덱스만 생성합니다.
- 스크립트는 MongoDB 설정 변경 전에 `/etc/mongod.conf`를 백업합니다.

##  설계의도

- `최초 아무것도 존재하지 않는 Ec2 작업시 Python 및 mongodb를 설치하고 최초 DB 및 documents 세팅에 대한 부담을 줄이기 위함입니다.
- `해당 스크립트를 실행할 경우 Python 및 Python mongodb connector가 설치되며 이후 순차적으로 mongodb 설치를 완료합니다.
- `이후 mongodb 설치가 완료되면 bind.ip 0.0.0.0 으로 수정하기 위해 mongodb 설정파일을 백업하고 bind ip를 수정합니다.
- `Aws에서 27017 Port를 보안그룹을 통해 open 했다면 내부망 기준으로 쉽게 MongoDB 접속이 가능해짐을 확인할수 있겠습니다. 