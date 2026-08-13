# db_config.py

## 역할

MySQL 접속 정보를 한 곳에서 관리하는 파일이다.

```python
DB_CONFIG = {
    "host": "MySQL 서버 주소",
    "port": 3306,
    "database": "project1",
    "user": "MySQL 계정",
    "password": "MySQL 비밀번호",
}
```

`loader.py`가 이 dictionary를 가져와 MySQL에 연결한다.

```python
from db_config import DB_CONFIG

mysql.connect(**DB_CONFIG)
```

## 수정 방법

MySQL 서버 주소나 계정이 바뀌면 `src/db_config.py`의 해당 값만 수정한다.

- `host`: MySQL 서버 IP 또는 주소
- `port`: 기본 MySQL 포트 `3306`
- `database`: 현재 데이터베이스 `project1`
- `user`: MySQL 계정
- `password`: MySQL 비밀번호

## 주의

이 파일에는 실제 비밀번호가 들어갈 수 있다.
비밀번호를 문서에 적거나 GitHub에 공개하지 않는다.
`host` 문자열 뒤에 불필요한 공백이 들어가지 않도록 확인한다.
