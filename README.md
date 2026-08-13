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
-  mlo-01-p1-team4 data crawling project

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


## 4. 요구사항 명세서

- 첨부된 brd.md 문서를 참조

## 5. ERD

- 첨부된 erd.md 문서를 참조

## 6. 주요 프로시저

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


## 7. 수행결과(테스트/시연 페이지)

- 추가 예정

## 8. 한 줄 회고

| 이름 | 회고 |
|---|---|
|김영주| 전체적인 구조를 기획 및 설계하는 과정의 결과가 실제 개발에 반영될수 있도록 개선하는것이 중요하다고 생각했습니다.|
|오재석| llm을 사용하여 결과물을 산출하는 것보다 통제 가능한 수준의 결과물을 만드는 것이 더 중요하다 생각했습니다.|
|강한솔| 단순히 웹 데이터를 수집하는 크롤링에서 끝나는 것이 아니라, 수집한 데이터를 저장하고, 주기적으로 자동 실행하며, 오류 발생 시 로그를 통해 원인을 추적하는 과정까지 연결되어야 하나의 데이터 파이프라인이 완성된다는 점을 이해했습니다.|
