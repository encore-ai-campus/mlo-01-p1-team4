# mlo-01-p1-team4
# MLO 1기 1차 프로젝트

## 1. 팀 소개

### 팀명
- 팀명: `MLO-01-04`

### 멤버
| 이름 | 역할 | GitHub |
|---|---|---|
|김영주| 팀장 |(https://github.com/escapedaily99) |
|오재석| 팀원 |(https://github.com/1ritaron8) |
|강한솔| 팀원 |(https://github.com/hansolsmart) |

## 2. 프로젝트 개요

### 프로젝트 명
-  

### 프로젝트 소개
-  Encore MLops 1기 과정에서 특정 데이터를 수집하고 해당 데이터를 처리 할 수 있는 솔루션을 만들기 위해 작성되었습니다.

### 프로젝트 필요성(배경)
- 본 프로젝트는 서로 다른 형태와 출처를 가진 데이터를 통합 하고 제어할 수 있는 방법은 없을까 라는 고민을 통해 최초 설계 되었습니다.

### 프로젝트 목표
- 차량 등록 데이터, 차량 관련 FAQ 데이터 수집시 출처 및 데이터 정합성을 확보할 수 있도록 한다.
- 차량 등록 데이터 및 FAQ 데이터 수집시 logging을 반드시 진행하며 데이터의 출처를 판단할수 있도록 한다.
- Mysql 및 MongoDB Insert aciton시 중복 데이터에 대한 처리를 할 수 있도록 한다.
- Mysql 및 MongoDB 호출시 반드시 logging을 반드시 진행하며 수집된 데이터에 대한 처리건수를 기록한다.
- 추후 서로 다른 형태와 출처를 가진 데이터들에 대한 솔루션으로 변화 시킬 수 있는 기반을 마련한다. 

## 3. 기술 스택

| 구분 | 기술 |
|---|---|
| Language | Python |
| Data | MySQL, MongoDB |
| Collaboration | GitHub |

## 4. WBS

- 추가 예정

## 5. 요구사항 명세서

- 첨부된 brd.md 문서를 참조

## 6. ERD

- 첨부된 erd.md 문서를 참조

## 7. 주요 프로시저

## car_listing 프로시저

- `car_pipeline.cron`: 매시 정각에 자동 실행
- `run_car_pipeline.sh`: 전체 실행 순서 관리
- `car_api_crawler.py`: 외부 자동차 API 데이터 수집
- `loader.py`: 데이터 정제·검증 및 MySQL 저장
- `vehicle_quality.py`: 적재 데이터 품질 검증
- `car_pipeline.logrotate`: 로그 파일 분리·압축 관리
- `quality_check_output/quality-report.json`: 품질 검증 결과 저장
- `config/car_api_crawler.log`: 크롤링·적재 로그 저장
- `logs/car_pipeline.log`: 전체 파이프라인 실행 로그 저장

`text
car_pipeline.cron
  → run_car_pipeline.sh
  → car_api_crawler.py
  → loader.py
  → vehicle_quality.py
  → quality-report.json




## 8. 수행결과(테스트/시연 페이지)

- 추가 예정

## 9. 한 줄 회고

| 이름 | 회고 |
|---|---|
|  | 한 줄 회고를 작성하세요. |
|  | 한 줄 회고를 작성하세요. |
|  | 한 줄 회고를 작성하세요. |
