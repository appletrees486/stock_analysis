# 국내 주식 차트 분석 및 AI 분석 프로그램

국내 주식의 일봉/주봉/월봉 데이터를 조회하고 기술적 분석을 제공하며, AI 제미나이를 활용한 차트 분석까지 수행하는 Python 프로그램입니다. MySQL 데이터베이스 기반의 효율적인 데이터 관리와 웹 인터페이스를 통해 사용자 친화적인 분석 환경을 제공합니다.

## 🚀 주요 기능

### 📊 차트 데이터 조회 (일봉/주봉/월봉 지원)
- **1년간 일봉 데이터** 자동 조회 (240일)
- **5년간 주봉 데이터** 지원 (240주)
- **10년간 월봉 데이터** 지원 (120개월)
- **Yahoo Finance API** 활용
- **국내 주식 종목코드** 지원 (6자리 숫자)

### 📈 기술적 지표 분석

#### 일봉 차트 보조지표
- **이동평균선**: 5일, 20일, 60일, 120일
- **거래량**
- **MACD**: 12일/26일 EMA, 9일 Signal, Histogram
- **RSI**: 14일 기준 과매수/과매도 구간 분석

#### 주봉 차트 보조지표
- **이동평균선**: 5주, 20주, 60주
- **거래량**
- **Stochastic Slow**
- **Bollinger Band**

#### 월봉 차트 보조지표
- **이동평균선**: 5개월, 20개월, 60개월
- **거래량**
- **CCI**
- **ADX**

### 📊 차트 시각화
- **일봉/주봉/월봉 캔들차트** + 이동평균선
- **거래량 차트**
- **보조지표 차트** (차트 유형별 특화)

### 🤖 AI 차트 분석
- **Google Gemini AI** 활용한 차트 이미지 분석
- **일봉/주봉/월봉별 특화 프롬프트** 지원
- **자동 기술적 지표 해석**
- **투자 아이디어 및 매매 시점 제안**
- **JSON 형태의 구조화된 분석 결과**
- **종목코드-종목명 자동 매핑** (stock_mapping.json)

### 🔍 분석 리포트
- **가격 정보**: 시작가, 종가, 최고가, 최저가
- **변동 정보**: 가격 변동, 변동률
- **거래량 정보**: 평균/최대/최소 거래량
- **기술적 지표**: 최신값 및 신호 분석
- **이동평균 신호**: 추세 분석
- **캔들 패턴**: 최근 패턴 분석

## 🆕 최신 업데이트

### 🧹 프로젝트 정리 및 최적화 (2025-08-27)
- **백업 파일 정리**: 불필요한 백업 파일들 제거하여 ~6.8MB 용량 절약
- **SQLite 완전 제거**: MySQL 이전 완료로 SQLite 관련 파일들 모두 정리
- **빈 로그 파일 정리**: 사용되지 않는 빈 로그 파일들 제거
- **중복 스크립트 정리**: 웹에서 사용되지 않는 중복 스크립트들 제거
- **테스트 파일 정리**: 완료된 테스트 및 디버그 파일들 정리
- **파일 구조 최적화**: 18개 파일 제거로 프로젝트 구조 간소화
- **README 업데이트**: 현재 프로젝트 상태에 맞게 문서 업데이트

### 🚀 거래량 랭킹 시스템 (2025-08-23)
- **일/주/월별 거래량 랭킹**: 상위 50개 종목 자동 조회 및 정렬
- **거래량 vs 거래률 구분**: 거래량과 거래률을 별도로 계산하여 다른 결과 제공
- **실시간 데이터 캐싱**: 1시간 TTL을 가진 효율적인 캐시 시스템
- **웹 인터페이스 통합**: 거래량 랭킹 전용 웹 페이지 제공
- **API 엔드포인트**: REST API를 통한 거래량 랭킹 데이터 조회

### 🔧 데이터베이스 스키마 업데이트 (2025-08-23)
- **유통주식수 컬럼 추가**: `stocks` 테이블에 `total_shares`, `market_cap` 컬럼 추가
- **거래률 계산 지원**: 거래량 대비 거래률을 계산할 수 있는 기반 구축
- **시장 상태 추적**: `daily_data_collection_log` 테이블에 `market_status` 컬럼 추가
- **기술적 지표 확장**: `technical_indicators` 테이블에 필요한 보조지표 컬럼들 추가

### 🚀 전일 데이터 품질 검증 시스템 (2025-08-22)
- **스마트 데이터 품질 관리**: 장중 데이터 vs 장 마감 데이터 자동 구분
- **자동 재수집 시스템**: 장중에 수집된 전일 데이터 자동 감지 및 재수집
- **수집 시간 추적**: `last_collected_timestamp` 컬럼으로 정확한 수집 시간 기록
- **데이터 품질 분류**: `INTRADAY` (장중), `CLOSING` (장 마감 후) 자동 분류
- **검증 로직 통합**: `market_status_detector.py`와 `enhanced_data_validator.py` 활용
- **중복 코드 방지**: 기존 모듈 재사용으로 일관성 유지

### 🎯 프롬프트 관리 시스템 (2025-08-22)
- **체계적인 프롬프트 관리**: `ChartAnalysisPrompts` 클래스로 프롬프트 체계적 관리
- **데이터베이스 기반 프롬프트 저장**: 프롬프트를 DB에 저장하여 동적 관리
- **차트 유형별 특화 프롬프트**: 일봉/주봉/월봉별 최적화된 분석 프롬프트
- **프롬프트 버전 관리**: 프롬프트 수정 이력 추적 및 버전 관리
- **웹 인터페이스 통합**: 프롬프트 관리 웹 페이지 제공

### 🔧 데이터 변경 추적 시스템 (2025-08-22)
- **데이터 변경 모니터링**: 주봉/월봉 데이터 생성 시 변경 사항 자동 추적
- **변경 이력 관리**: 데이터 수정, 삭제, 추가 이력 자동 기록
- **데이터 무결성 보장**: 변경 사항에 대한 검증 및 롤백 지원
- **감사 로그**: 모든 데이터 변경 사항에 대한 상세한 감사 로그

### 🗄️ MySQL 데이터베이스 시스템
- **효율적인 데이터 관리**: 종목별 일봉 데이터를 데이터베이스에 저장하여 중복 수집 방지
- **10년치 일봉 데이터**: 각 종목별로 10년간의 일봉 데이터 자동 수집 및 저장
- **기술적 지표 저장**: 이동평균선, RSI, MACD, 볼린저밴드 등 보조지표를 미리 계산하여 저장
- **하이브리드 방식**: 핵심 OHLCV + 기본 보조지표는 저장, 복잡한 지표는 필요시 계산
- **증분 업데이트**: 빈 일자만 채우는 방식으로 빠른 데이터 업데이트
- **데이터 무결성**: 마감 전 수집 데이터 검증 및 최종 데이터 보장

### 🔍 향상된 데이터 검증 시스템
- **스마트 검증**: 데이터 품질 점수 기반 자동 검증
- **최신일 데이터 신뢰성 검증**: 장마감 후 데이터 재수집 권장 시스템
- **보조지표 품질 관리**: 0값, 음수값, 극단값 등 비정상 데이터 자동 감지
- **자동 업데이트**: 데이터 품질 문제 시 자동으로 보조지표 재계산

### 📊 주봉/월봉 데이터 자동 생성
- **일봉 기반 변환**: 일봉 데이터를 기반으로 주봉, 월봉 데이터 자동 생성
- **한국 공휴일 고려**: 공휴일을 고려한 정확한 주봉/월봉 데이터 생성
- **배치 처리**: 100개 종목씩 배치로 효율적인 데이터 생성
- **데이터베이스 저장**: 생성된 주봉/월봉 데이터를 별도 테이블에 저장

### 🌐 웹 인터페이스 시스템
- **Flask 기반 웹 애플리케이션**: 브라우저에서 직접 분석 실행
- **배치 분석 및 단일 분석**: 웹 인터페이스를 통한 편리한 분석 실행
- **파일 업로드/다운로드**: 종목 목록 파일 업로드 및 결과 파일 다운로드
- **실시간 진행률**: 배치 분석 진행 상황 실시간 모니터링
- **프롬프트 관리**: AI 분석용 프롬프트 웹 인터페이스에서 관리
- **거래량 랭킹**: 일/주/월별 거래량 및 거래률 상위 50개 종목 조회
- **REST API 제공**: 배치 분석, 프롬프트 관리, 거래량 랭킹 등을 위한 API 엔드포인트
- **반응형 디자인**: 모바일과 데스크톱 모두 지원하는 반응형 웹 인터페이스

## 📋 설치 요구사항

### Python 버전
- Python 3.7 이상

### 필수 라이브러리
```
# 데이터 조회 및 처리
yfinance>=0.2.0
pandas>=1.3.0
numpy>=1.21.0
requests>=2.28.0
PyJWT>=2.8.0
pykrx>=1.0.0

# 차트 시각화
matplotlib>=3.5.0
mplfinance>=0.12.0

# 날짜 처리
python-dateutil>=2.8.0

# AI API 및 HTTP 요청
google-generativeai>=0.3.0
Pillow>=9.0.0

# JSON 처리
json5>=0.9.0

# Word 문서 생성
python-docx>=0.8.11

# Excel 파일 생성
openpyxl>=3.1.0

# 데이터베이스
mysql-connector-python>=8.0.0

# 웹 서버
Flask>=2.3.0
Flask-CORS>=4.0.0
Werkzeug>=2.3.0
```

### 종목 매핑 파일
- `stock_mapping.json`: 종목코드와 종목명을 매핑하는 JSON 파일
- 기본 제공: 019210(YG-1), 023410(유진기업), 145720(덴티움), 005930(삼성전자), 014280(금강철강)

### AI API 요구사항
- **Google AI API 키** (Gemini)
- https://makersuite.google.com/app/apikey 에서 발급 가능

### 데이터베이스 요구사항
- **MySQL 8.0 이상**
- **포트**: 3306 (기본값)
- **사용자**: root
- **비밀번호**: 1234 (설정 가능)
- **데이터베이스**: stock_analysis (자동 생성)

## 🛠️ 설치 방법

### 1. 라이브러리 설치

**Windows:**
```bash
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
pip3 install -r requirements.txt
```

### 2. 자동 설치 스크립트 사용

**Windows:**
```bash
install.bat
```

**Linux/macOS:**
```bash
chmod +x install.sh
./install.sh
```

### 3. AI API 키 설정

```bash
python setup_api_key.py
```

### 4. MySQL 데이터베이스 설정

```bash
# MySQL 스키마 생성
python create_database_schema.py

# 주식 데이터 수집 (통합 수집기)
python stock_data_collector.py

# 주봉/월봉 데이터 생성 (선택사항)
python week_month_data_generator.py

# 프롬프트 테이블 생성 (AI 분석용)
python create_prompt_tables.py
```

## 🎯 사용 방법

### 1. 통합 실행 (권장)
```bash
python integrated_stock_analysis.py
```
**새로운 플로우:**
1. 종목명 입력 (예: 삼성전자, SK하이닉스)
2. 차트 유형 선택 (일봉/주봉/월봉)
3. 차트 생성
4. AI 분석
5. 결과 저장 (JSON + Word 문서)

### 2. 배치 분석
```bash
python batch_stock_analyzer_optimized.py
```
**배치 처리 플로우:**
1. 종목 목록 입력 (직접 입력 또는 파일에서 읽기)
2. 차트 유형 선택 (일봉/주봉/월봉)
3. 병렬 처리 설정 (동시 처리할 종목 수)
4. 자동 배치 분석 실행
5. 결과 요약 및 개별 파일 저장

**특징:**
- **병렬 처리**: 여러 종목을 동시에 분석하여 시간 단축
- **진행률 표시**: 실시간 진행률 및 예상 완료 시간 표시
- **유연한 입력**: 종목코드, 종목명 혼합 입력 지원
- **파일 기반 입력**: `stock_list.txt` 파일에서 종목 목록 읽기
- **결과 요약**: 전체 분석 결과 통계 및 개별 파일 저장

### 3. 개별 차트 생성
```bash
# 일봉 차트
python day_stock_analysis.py

# 주봉 차트  
python week_stock_analysis.py

# 월봉 차트
python month_stock_analysis.py
```

### 4. AI 차트 분석 (차트 이미지 필요)
```bash
python ai_chart_analysis.py
```

### 5. 웹 인터페이스
```bash
python app.py
```
- Flask 기반 웹 애플리케이션
- 배치 분석 및 단일 분석 지원
- 거래량 랭킹 조회 기능
- 프롬프트 관리 기능
- 결과 파일 다운로드 기능

### 6. 데이터베이스 관리
```bash
# 데이터베이스 스키마 생성
python create_database_schema.py

# 주식 데이터 수집 (통합 수집기)
python stock_data_collector.py

# 주봉/월봉 데이터 생성
python week_month_data_generator.py

# 데이터베이스 상태 확인
python check_database_data.py

# 프롬프트 테이블 생성 및 관리
python create_prompt_tables.py
python save_daily_prompt.py
python check_saved_prompt.py

# 프롬프트 관리자 실행
python prompt_manager.py
```

### 7. 프롬프트 관리
```bash
# 프롬프트 테이블 생성
python create_prompt_tables.py

# 일일 프롬프트 저장
python save_daily_prompt.py

# 저장된 프롬프트 확인
python check_saved_prompt.py

# 프롬프트 관리자 실행
python prompt_manager.py
```

### 8. 거래량 랭킹
```bash
# 데이터베이스 스키마 업데이트 (유통주식수 컬럼 추가)
python update_database_schema.py

# 웹 인터페이스에서 거래량 랭킹 조회
# http://localhost:5000/volume-ranking
```

## 📁 파일 구조

```
stock_analysis/
├── app.py                           # Flask 웹 애플리케이션
├── day_stock_analysis.py            # 일봉 차트 생성 스크립트
├── week_stock_analysis.py           # 주봉 차트 생성 스크립트
├── month_stock_analysis.py          # 월봉 차트 생성 스크립트
├── ai_chart_analysis.py             # AI 차트 분석 스크립트
├── integrated_stock_analysis.py     # 통합 실행 스크립트
├── batch_stock_analyzer_optimized.py # 배치 분석 스크립트
├── setup_api_key.py                 # API 키 설정 스크립트
├── config.py                        # 설정 관리 모듈

├── requirements.txt                  # 필수 라이브러리 목록
├── stock_list.txt                   # 배치 분석용 종목 목록 파일
├── stock_mapping.json               # 종목코드-종목명 매핑 파일
├── daily_charts/                    # 일봉 차트 이미지 저장 폴더
├── weekly_charts/                   # 주봉 차트 이미지 저장 폴더
├── monthly_charts/                  # 월봉 차트 이미지 저장 폴더
├── ai_analysis_results/             # AI 분석 결과 저장 폴더
├── results/                         # 배치 분석 결과 폴더
├── chart_data_csv/                  # 차트 데이터 CSV 파일 저장 폴더
├── chart_data_json/                 # 차트 데이터 JSON 파일 저장 폴더
├── chart_data_text/                 # 차트 데이터 텍스트 요약 저장 폴더
├── api/                             # 웹 API 모듈
│   ├── __init__.py
│   ├── routes.py                    # API 라우트
│   ├── utils.py                     # 유틸리티 함수
│   ├── batch_analyzer.py            # 배치 분석 API
│   ├── prompt_routes.py             # 프롬프트 관리 API
│   └── volume_ranking_utils.py      # 거래량 랭킹 유틸리티
├── templates/                       # 웹 템플릿
│   ├── index.html                   # 메인 페이지
│   ├── single_analysis.html         # 단일 분석 페이지
│   ├── batch_analysis.html          # 배치 분석 페이지
│   ├── prompt_management.html       # 프롬프트 관리 페이지
│   └── volume_ranking.html          # 거래량 랭킹 페이지
├── static/                          # 웹 정적 파일
│   ├── css/
│   │   └── style.css                # 메인 스타일시트
│   └── js/
│       ├── single.js                # 단일 분석 JavaScript
│       └── batch.js                 # 배치 분석 JavaScript
├── uploads/                         # 파일 업로드 폴더
│   ├── charts/                      # 업로드된 차트
│   └── stock_lists/                 # 업로드된 종목 목록
├── etc/                             # 기타 문서 및 파일
├── .cursor/                         # Cursor IDE 설정
├── .git/                            # Git 버전 관리
├── __pycache__/                     # Python 캐시 파일
├── database_config.py                # MySQL 데이터베이스 연결 설정
├── create_database_schema.py         # MySQL 스키마 생성 스크립트
├── stock_data_collector.py           # 통합 주식 데이터 수집 모듈
├── week_month_data_generator.py      # 주봉/월봉 데이터 생성 모듈
├── enhanced_data_validator.py        # 향상된 데이터 검증 시스템
├── korean_holiday_manager.py         # 한국 공휴일 관리 모듈
├── check_database_data.py            # 데이터베이스 상태 확인 스크립트
├── update_database_schema.py         # 데이터베이스 스키마 업데이트 (유통주식수, 거래률 지원)
├── debug_database.py                 # 데이터베이스 디버깅 도구
├── data_change_tracker.py            # 데이터 변경 추적 시스템
├── market_status_detector.py         # 시장 상태 감지 시스템
├── fix_indicators.py                 # 기술적 지표 수정 도구
├── check_indicators.py               # 기술적 지표 확인 도구
├── collect_daily_data_from_json.py   # JSON에서 일봉 데이터 수집
├── update_stocks_table.py            # 종목 테이블 업데이트
├── update_stocks_from_json.py        # JSON에서 종목 정보 업데이트
├── database.log                      # 데이터베이스 로그
├── market_status.log                 # 시장 상태 감지 로그
├── prompt_manager.py                 # 프롬프트 관리 모듈
├── create_prompt_tables.py          # 프롬프트 테이블 생성
├── save_daily_prompt.py             # 일일 프롬프트 저장
├── check_saved_prompt.py            # 저장된 프롬프트 확인
├── test_web_interface.py            # 웹 인터페이스 테스트
├── .secret_key                      # 보안 키 파일
├── config.txt                       # 설정 텍스트 파일
├── Special_Interface.doc            # 특별 인터페이스 문서
├── .gitattributes                   # Git 속성 설정
├── .gitignore                       # Git 무시 파일 설정
├── install.sh                       # Linux/macOS 설치 스크립트
└── install.bat                      # Windows 설치 스크립트
```

## 🤖 AI 분석 기능

### 차트 유형별 특화 분석

#### 📊 일봉 차트 분석
- **단기 모멘텀** 분석
- **최근 5일간** 가격 움직임
- **단기 투자 아이디어** 제공

#### 📈 주봉 차트 분석  
- **중기 추세** 분석
- **최근 8주간** 가격 움직임
- **중기 투자 전략** 제공

#### 📊 월봉 차트 분석
- **장기 추세** 분석
- **최근 12개월간** 가격 움직임
- **장기 투자 전략** 제공

### 분석 항목
1. **가격 및 거래량 분석**
   - 차트 유형별 기간 가격 움직임
   - 거래량 변화 및 특이점
   - 주요 가격대 돌파/이탈 여부

2. **이동평균선 분석**
   - 정배열/역배열 여부
   - 골든 크로스/데드 크로스 발생 여부
   - 이동평균선 밀집도 분석

3. **보조지표 분석**
   - **일봉**: MACD, RSI 분석
   - **주봉**: Stochastic, Bollinger Band 분석
   - **월봉**: CCI, ADX 분석

4. **투자 아이디어**
   - 차트 유형별 추세 및 모멘텀 종합 판단
   - 매수/매도 시점 제안

### 프롬프트 관리 시스템
- **데이터베이스 기반 프롬프트 저장**: AI 분석용 프롬프트를 DB에 저장하여 동적 관리
- **차트 유형별 최적화**: 일봉/주봉/월봉별 특화된 분석 프롬프트 제공
- **프롬프트 버전 관리**: 프롬프트 수정 이력 추적 및 버전 관리
- **웹 인터페이스 통합**: 프롬프트 편집 및 관리를 위한 웹 페이지 제공
- **카테고리별 분류**: 차트 유형, 분석 목적별 체계적인 프롬프트 분류

## 📝 프로젝트 정리 내역 (2025-08-27)

### 🗑️ 삭제된 파일들
다음 파일들은 프로젝트 정리 과정에서 안전하게 삭제되었습니다:

#### 백업 파일들 (6.6MB 절약)
- `ai_chart_analysis_backup.py` - AI 분석 백업 파일
- `stock_data_collector_backup.py` - 데이터 수집기 백업 파일
- `stock_analysis_backup.db` - SQLite 백업 데이터베이스

#### SQLite 관련 파일들 (11KB 절약)
- `stock_analysis.db` - 빈 SQLite 데이터베이스 파일
- `database_sqlite.log` - SQLite 로그 파일

#### 빈 로그 파일들
- `scheduler_service.log`
- `enhanced_data_validator.log`
- `daily_data_collection.log`
- `stock_collector_mysql.log`
- `stock_collector.log`
- `data_change_tracker.log`

#### 웹 미사용 스크립트들 (23KB 절약)
- `stock_data_collector_mysql.py` - 테스트용 독립 스크립트
- `naver_data_module.py` - 사용되지 않는 네이버 모듈

#### 테스트/디버그 파일들 (14KB 절약)
- `test_fixed_scheduler.py` - 스케줄러 테스트 파일
- `debug_db_connection.py` - DB 연결 디버그 파일
- `test_total_analysis_20250825_125934.json` - 테스트 결과 파일

#### 임시 분석 파일들 (22KB 절약)
- `missing_stocks_report_20250822_175637.csv`
- `missing_stocks_report_20250822_175637.xlsx`
- `stocks_only_in_stocks_table.csv`
- `database_config.txt` - config.py로 통합됨

### ✅ 정리 효과
- **총 삭제 파일**: 18개
- **총 용량 절약**: ~6.8MB
- **비즈니스 로직 영향**: 전혀 없음
- **웹 애플리케이션 동작**: 정상 유지

## 🔧 설정 및 문제해결

### API 키 설정
1. https://makersuite.google.com/app/apikey 접속
2. Google 계정으로 로그인
3. 'Create API Key' 클릭하여 API 키 생성
4. `python setup_api_key.py` 실행하여 키 입력

### 환경변수 설정 (선택사항)
```bash
# Windows
set GOOGLE_AI_API_KEY=your_api_key_here

# Linux/macOS
export GOOGLE_AI_API_KEY=your_api_key_here
```

### MySQL 데이터베이스 설정
1. **MySQL 설치**: MySQL 8.0 이상 설치 (포트: 3306)
2. **사용자 설정**: root 사용자 비밀번호를 '1234'로 설정
3. **데이터베이스 생성**: `python create_database_schema.py` 실행
4. **테스트 데이터 수집**: `python stock_data_collector_mysql.py` 실행

### 환경변수 설정 (데이터베이스)
```bash
# Windows
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=1234
set DB_PORT=3306
set DB_NAME=stock_analysis

# Linux/macOS
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=1234
export DB_PORT=3306
export DB_NAME=stock_analysis
```

### 문제해결
- **차트 이미지가 없는 경우**: 먼저 해당 차트 생성 프로그램을 실행
- **API 키 오류**: `setup_api_key.py`로 키 재설정
- **라이브러리 오류**: `pip install -r requirements.txt` 재실행
- **MySQL 연결 오류**: MySQL 서비스 실행 상태 및 포트 확인
- **데이터베이스 권한 오류**: root 사용자 비밀번호 및 권한 확인

## 📊 실행 예시

### MySQL 데이터베이스 설정
```
🚀 MySQL 데이터베이스 스키마 생성 시작
==================================================
📋 데이터베이스 테이블 생성 중...
✅ stocks 테이블 생성 완료
✅ daily_data 테이블 생성 완료
✅ weekly_data 테이블 생성 완료
✅ monthly_data 테이블 생성 완료
✅ technical_indicators 테이블 생성 완료
✅ data_collection_log 테이블 생성 완료
✅ stock_collection_status 테이블 생성 완료
✅ 모든 테이블 생성 완료

📊 테스트 종목 데이터 삽입 중...
✅ 테스트 종목 5개 삽입 완료

🎉 데이터베이스 스키마 생성 완료!
📊 생성된 테이블:
   - stocks: 종목 정보
   - daily_data: 일봉 데이터
   - weekly_data: 주봉 데이터
   - monthly_data: 월봉 데이터
   - technical_indicators: 기술적 지표
   - data_collection_log: 수집 이력
   - stock_collection_status: 종목별 수집 상태

🚀 프롬프트 관리 테이블 생성 시작
==================================================
📋 프롬프트 관련 테이블 생성 중...
✅ prompt_categories 테이블 생성 완료
✅ prompts 테이블 생성 완료
✅ secure_configs 테이블 생성 완료

📊 프롬프트 카테고리 데이터 삽입 중...
✅ 프롬프트 카테고리 3개 삽입 완료

🎉 프롬프트 관리 테이블 생성 완료!
📊 생성된 테이블:
   - prompt_categories: 프롬프트 카테고리
   - prompts: 프롬프트 내용
   - secure_configs: 보안 설정 (API 키 등)
```

### 주식 데이터 수집
```
🚀 MySQL 기반 주식 데이터 수집 프로그램 시작
==================================================
🚀 MySQL 기반 테스트 종목 데이터 수집 시작
==================================================

📊 [1/5] 019210 처리 중...
🔍 019210 10년치 일봉 데이터 조회 중...
✅ 019210: 2450일의 일봉 데이터 조회 완료
   📅 기간: 2015-08-20 ~ 2025-08-19
✅ 019210 일봉 데이터 2450개 저장 완료
✅ 019210 기술적 지표 2450개 저장 완료
✅ 019210 수집 상태 업데이트 완료
✅ 019210 (YG-1) 데이터 수집 완료

📊 [2/5] 023410 처리 중...
🔍 023410 10년치 일봉 데이터 조회 중...
✅ 023410: 2450일의 일봉 데이터 조회 완료
   📅 기간: 2015-08-20 ~ 2025-08-19
✅ 023410 일봉 데이터 2450개 저장 완료
✅ 023410 기술적 지표 2450개 저장 완료
✅ 023410 수집 상태 업데이트 완료
✅ 023410 (유진기업) 데이터 수집 완료

📊 [3/5] 145720 처리 중...
🔍 145720 10년치 일봉 데이터 조회 중...
✅ 145720: 2064일의 일봉 데이터 조회 완료
   📅 기간: 2017-03-16 ~ 2025-08-20
✅ 145720 일봉 데이터 2064개 저장 완료
✅ 145720 기술적 지표 2064개 저장 완료
✅ 145720 수집 상태 업데이트 완료
✅ 145720 (덴티움) 데이터 수집 완료

📊 [4/5] 005930 처리 중...
🔍 005930 10년치 일봉 데이터 조회 중...
✅ 005930: 2451일의 일봉 데이터 조회 완료
   📅 기간: 2015-08-20 ~ 2025-08-20
✅ 005930 일봉 데이터 2451개 저장 완료
✅ 005930 기술적 지표 2451개 저장 완료
✅ 005930 수집 상태 업데이트 완료
✅ 005930 (삼성전자) 데이터 수집 완료

📊 [5/5] 014280 처리 중...
🔍 014280 10년치 일봉 데이터 조회 중...
✅ 014280: 2451일의 일봉 데이터 조회 완료
   📅 기간: 2015-08-20 ~ 2025-08-20
✅ 014280 일봉 데이터 2451개 저장 완료
✅ 014280 기술적 지표 2451개 저장 완료
✅ 014280 수집 상태 업데이트 완료
✅ 014280 (금강철강) 데이터 수집 완료

🎉 데이터 수집 완료!
✅ 성공: 5개
❌ 실패: 0개

💡 다음 단계:
   1. MySQL 데이터베이스에서 수집된 데이터 확인
   2. 주봉, 월봉 데이터 생성
   3. 차트 생성 모듈을 DB 기반으로 수정
```

### 주봉/월봉 데이터 생성
```
🚀 주봉 및 월봉 데이터 생성 시작
==================================================
📊 일봉 데이터가 있는 종목 5개를 찾았습니다.

📈 주봉 데이터 생성 중...
📊 [1/5] 019210 처리 중...
✅ 019210 주봉 데이터 생성 완료: 480주
📊 [2/5] 023410 처리 중...
✅ 023410 주봉 데이터 생성 완료: 480주
📊 [3/5] 145720 처리 중...
✅ 145720 주봉 데이터 생성 완료: 403주
📊 [4/5] 005930 처리 중...
✅ 005930 주봉 데이터 생성 완료: 480주
📊 [5/5] 014280 처리 중...
✅ 014280 주봉 데이터 생성 완료: 480주

📈 월봉 데이터 생성 중...
📊 [1/5] 019210 처리 중...
✅ 019210 월봉 데이터 생성 완료: 120개월
📊 [2/5] 023410 처리 중...
✅ 023410 월봉 데이터 생성 완료: 120개월
📊 [3/5] 145720 처리 중...
✅ 145720 월봉 데이터 생성 완료: 100개월
📊 [4/5] 005930 처리 중...
✅ 005930 월봉 데이터 생성 완료: 120개월
📊 [5/5] 014280 처리 중...
✅ 014280 월봉 데이터 생성 완료: 120개월

🎉 주봉 및 월봉 데이터 생성 완료!
📊 총 처리된 종목: 5개
📈 주봉 데이터: 2,323주
📈 월봉 데이터: 580개월
```

### 통합 분석
```
🚀 통합 주식 분석 프로그램
============================================================
📊 종목명 입력 → 차트 유형 선택 → 차트 생성 → AI 분석
============================================================

📈 1단계: 종목명 입력
--------------------------------------------------
📈 종목명을 입력하세요 (예: 삼성전자, SK하이닉스): 삼성전자

📊 2단계: 차트 유형 선택
--------------------------------------------------
📊 분석할 차트 유형을 선택하세요:
   1. 일봉 차트
   2. 주봉 차트
   3. 월봉 차트

📊 차트 유형을 선택하세요 (1-3): 1

📈 3단계: 일봉 차트 생성
--------------------------------------------------
🔍 삼성전자 일봉 데이터 조회 중...
✅ 일봉 차트 생성 완료

🤖 4단계: AI 일봉 차트 분석
--------------------------------------------------
🔍 분석 시작: 삼성전자
📁 파일: daily_charts/daily_Samsung_Electronics_Co.,_Ltd._005930_20250115.png
📊 차트 유형: 일봉
✅ AI 분석 완료
📄 JSON 결과 파일: ai_analysis_results/analysis_daily_삼성전자_20250115_143025.json
📄 Word 문서 파일: ai_analysis_results/analysis_daily_삼성전자_20250115_143025.docx
```

### 배치 분석
```
🚀 배치 주식 분석 프로그램
============================================================
📊 다중 종목 빠른 분석 시스템
============================================================

📈 배치 분석을 위한 종목 목록 입력
--------------------------------------------------
📝 입력 방법:
   1. 종목코드만 입력 (예: 005930, 000660, 035420)
   2. 종목명만 입력 (예: 삼성전자, SK하이닉스, NAVER)
   3. 혼합 입력 가능 (예: 005930, SK하이닉스, 035420)
   4. 파일에서 읽기 (stock_list.txt 파일에 한 줄에 하나씩)

📊 입력 방법을 선택하세요 (1: 직접입력, 2: 파일읽기): 2
✅ 파일에서 읽은 종목 수: 50개

📊 차트 유형 선택
--------------------------------------------------
📊 분석할 차트 유형을 선택하세요:
   1. 일봉 차트
   2. 주봉 차트
   3. 월봉 차트

📊 차트 유형을 선택하세요 (1-3): 1

⚙️ 병렬 처리 설정
--------------------------------------------------
🔧 동시 처리할 종목 수 (기본값: 5, 권장: 3-10): 5

🚀 배치 분석 시작
📊 총 50개 종목 | 차트 유형: 일봉 | 동시 처리: 5개
------------------------------------------------------------
📊 진행률: 100.0% (50/50) | 성공: 48 | 실패: 2 | 예상 남은 시간: 0.0분

====================================
🎉 배치 분석 완료!
====================================

📊 분석 통계:
   📈 총 종목 수: 50개
   ✅ 완전 성공: 48개 (96.0%)
   📊 차트만 성공: 0개
   ❌ 실패: 2개 (4.0%)
   📊 차트 유형: 일봉

✅ 완전 성공한 종목들:
   - 005930 (삼성전자)
   - 000660 (SK하이닉스)
   - 035420 (NAVER)
   ...

❌ 실패한 종목들:
   - 999999: 종목코드를 찾을 수 없습니다
   - 테스트종목: 종목코드를 찾을 수 없습니다

📁 생성된 파일들:
   📈 차트 이미지: daily_charts/ 폴더
   🤖 AI 분석 결과: ai_analysis_results/ 폴더
   📄 배치 요약: batch_analysis_summary_일봉_20250115_143025.json

⏱️ 총 소요 시간: 15.2분 (912초)
📊 평균 처리 시간: 18.2초/종목
```

### 웹 인터페이스
```
🌐 웹 브라우저에서 http://localhost:5000 접속
📊 배치 분석 및 단일 분석을 웹 인터페이스로 실행
📈 거래량 랭킹 조회 (http://localhost:5000/volume-ranking)
📝 프롬프트 관리 (http://localhost:5000/prompts)
📁 결과 파일 다운로드 및 관리
```

## 🆕 주요 기능

### 🚀 배치 분석 시스템
- **병렬 처리**: ThreadPoolExecutor를 활용한 다중 종목 동시 분석
- **진행률 추적**: 실시간 진행률 및 예상 완료 시간 표시
- **유연한 입력**: 종목코드, 종목명 혼합 입력 및 파일 기반 입력 지원
- **결과 요약**: 전체 분석 통계 및 개별 파일 자동 저장
- **에러 처리**: 개별 종목 실패 시에도 전체 프로세스 계속 진행

### 🌐 웹 인터페이스
- **Flask 기반 웹 애플리케이션**
- **배치 분석 및 단일 분석 지원**
- **거래량 랭킹 조회 기능**
- **프롬프트 관리 기능**
- **파일 업로드 및 다운로드 기능**
- **실시간 진행률 표시**

### 📊 프롬프트 관리 시스템
- **ChartAnalysisPrompts 클래스**로 프롬프트 체계적 관리
- **일봉/주봉/월봉별 특화 프롬프트** 제공
- **차트 유형별 최적화된 분석** 수행
- **데이터베이스 기반 프롬프트 저장**: 프롬프트를 DB에 저장하여 동적 관리
- **프롬프트 버전 관리**: 프롬프트 수정 이력 추적 및 버전 관리
- **웹 인터페이스 통합**: 프롬프트 관리 웹 페이지에서 편집 및 관리
- **카테고리별 프롬프트 분류**: 차트 유형, 분석 목적별 체계적 분류

### 📈 거래량 랭킹 시스템
- **일/주/월별 거래량 상위 50개 종목 조회**
- **거래량 vs 거래률 구분**: 같은 종목이라도 다른 순위 제공
- **실시간 데이터 캐싱**: 1시간 TTL로 효율적인 데이터 관리
- **웹 인터페이스 통합**: 전용 거래량 랭킹 페이지 제공
- **REST API 지원**: 외부 시스템과의 연동 가능

### 🔄 개선된 플로우
- **종목명 기반 입력** (종목코드 자동 매핑)
- **차트 유형 선택** (일봉/주봉/월봉)
- **자동화된 차트 생성 및 AI 분석**
- **차트 유형별 파일명 구분**

### 📁 체계적인 파일 관리
- **차트 유형별 폴더 분리**
- **분석 결과 파일명에 차트 유형 포함**
- **종목별 결과 파일 그룹화**

### 🗄️ MySQL 데이터베이스 시스템
- **효율적인 데이터 관리**: 종목별 일봉 데이터를 데이터베이스에 저장하여 중복 수집 방지
- **10년치 일봉 데이터**: 각 종목별로 10년간의 일봉 데이터 자동 수집 및 저장
- **기술적 지표 저장**: 이동평균선, RSI, MACD, 볼린저밴드 등 보조지표를 미리 계산하여 저장
- **하이브리드 방식**: 핵심 OHLCV + 기본 보조지표는 저장, 복잡한 지표는 필요시 계산
- **증분 업데이트**: 빈 일자만 채우는 방식으로 빠른 데이터 업데이트
- **데이터 무결성**: 마감 전 수집 데이터 검증 및 최종 데이터 보장

#### 데이터베이스 구조

##### 📊 핵심 데이터 테이블

###### **stocks** - 종목 정보
- `stock_code` (VARCHAR(6), PK): 종목코드
- `stock_name` (VARCHAR(100)): 종목명
- `market_type` (ENUM): KOSPI, KOSDAQ
- `listing_date` (DATE): 상장일
- `is_active` (BOOLEAN): 활성화 상태
- `total_shares` (BIGINT): 유통주식수
- `market_cap` (DECIMAL(20,2)): 시가총액
- `created_at`, `updated_at`: 생성/수정 시간

###### **daily_data** - 일봉 데이터
- `id` (BIGINT, PK): 자동 증가 ID
- `stock_code` (VARCHAR(6), FK): 종목코드
- `trade_date` (DATE): 거래일
- `open`, `high`, `low`, `close` (DECIMAL(10,2)): OHLC 가격
- `volume` (BIGINT): 거래량
- `created_at`, `updated_at`: 생성/수정 시간
- 인덱스: `stock_code`, `trade_date`, `unique_stock_date`

###### **weekly_data** - 주봉 데이터 (보조지표 포함)
- `id` (BIGINT, PK): 자동 증가 ID
- `stock_code` (VARCHAR(6), FK): 종목코드
- `week_start` (DATE): 주 시작일
- `open`, `high`, `low`, `close` (DECIMAL(10,2)): OHLC 가격
- `volume` (BIGINT): 거래량
- **보조지표**: `ma5`, `ma20`, `ma60`, `rsi`, `stoch_k`, `stoch_d`
- **볼린저밴드**: `bb_upper`, `bb_middle`, `bb_lower`
- `created_at`, `updated_at`: 생성/수정 시간
- 인덱스: `stock_code`, `week_start`, `unique_stock_week`

###### **monthly_data** - 월봉 데이터 (보조지표 포함)
- `id` (BIGINT, PK): 자동 증가 ID
- `stock_code` (VARCHAR(6), FK): 종목코드
- `month_start` (DATE): 월 시작일
- `open`, `high`, `low`, `close` (DECIMAL(10,2)): OHLC 가격
- `volume` (BIGINT): 거래량
- **보조지표**: `ma5`, `ma20`, `ma60`, `cci`, `adx`
- **DI 지표**: `plus_di`, `minus_di`
- **볼린저밴드**: `bb_upper`, `bb_middle`, `bb_lower`
- `created_at`, `updated_at`: 생성/수정 시간
- 인덱스: `stock_code`, `month_start`, `unique_stock_month`

###### **technical_indicators** - 일봉 기술적 지표
- `id` (BIGINT, PK): 자동 증가 ID
- `stock_code` (VARCHAR(6), FK): 종목코드
- `trade_date` (DATE): 거래일
- **이동평균**: `ma5`, `ma20`, `ma60`, `ma120`
- **RSI**: `rsi` (DECIMAL(5,2))
- **MACD**: `macd`, `macd_signal`, `macd_histogram`
- **볼린저밴드**: `bb_upper`, `bb_middle`, `bb_lower`
- `created_at`, `updated_at`: 생성/수정 시간
- 인덱스: `stock_code`, `trade_date`, `unique_stock_date`

##### 🔍 관리 및 모니터링 테이블

###### **data_collection_log** - 데이터 수집 이력
- `id` (BIGINT, PK): 자동 증가 ID
- `collection_date` (DATE): 수집일
- `total_stocks` (INT): 총 종목 수
- `success_count` (INT): 성공 수
- `failed_count` (INT): 실패 수
- `collection_type` (ENUM): DAILY, WEEKLY, MONTHLY
- `is_market_closed` (BOOLEAN): 장 마감 여부
- `market_status` (VARCHAR(50)): 장 상태 (non_trading_day, before_market_open, during_market, near_market_close, after_market_close)
- `started_at`, `completed_at` (TIMESTAMP): 시작/완료 시간
- `status` (ENUM): RUNNING, COMPLETED, FAILED
- `error_message` (TEXT): 오류 메시지

###### **stock_collection_status** - 종목별 수집 상태
- `id` (BIGINT, PK): 자동 증가 ID
- `stock_code` (VARCHAR(6), FK): 종목코드
- `last_collected_date` (DATE): 마지막 수집일
- `last_collected_timestamp` (TIMESTAMP): 마지막 수집 시간 (장중/장마감 구분용)
- `last_collected_close` (DECIMAL(10,2)): 마지막 종가
- `last_collected_volume` (BIGINT): 마지막 거래량
- `data_start_date`, `data_end_date` (DATE): 데이터 보유 기간
- `total_records` (INT): 총 데이터 레코드 수
- `collection_quality` (VARCHAR(20)): 수집 데이터 품질 (INTRADAY/CLOSING/UNKNOWN)
- `last_updated_at`, `created_at`: 수정/생성 시간
- 인덱스: `last_collected_date`, `data_end_date`, `collection_quality`

##### 🤖 프롬프트 관리 테이블

###### **prompt_categories** - 프롬프트 카테고리
- `id` (INT, PK): 자동 증가 ID
- `name` (VARCHAR(50), UNIQUE): 카테고리명 (일봉, 주봉, 월봉)
- `description` (TEXT): 카테고리 설명
- `is_active` (BOOLEAN): 활성화 상태
- `created_at`, `updated_at`: 생성/수정 시간
- 인덱스: `name`, `is_active`

###### **prompts** - 프롬프트 내용
- `id` (INT, PK): 자동 증가 ID
- `category_id` (INT, FK): 카테고리 ID
- `name` (VARCHAR(200)): 프롬프트명
- `content` (TEXT): 프롬프트 내용
- `version` (VARCHAR(50)): 버전 정보
- `is_active` (BOOLEAN): 활성화 상태
- `is_default` (BOOLEAN): 기본 프롬프트 여부
- `created_by` (VARCHAR(100)): 생성자
- `change_log` (TEXT): 변경 이력
- `created_at`, `updated_at`: 생성/수정 시간
- 인덱스: `category_id`, `is_active`, `is_default`, `version`

###### **secure_configs** - 보안 설정 (API 키 등)
- `id` (INT, PK): 자동 증가 ID
- `config_key` (VARCHAR(100), UNIQUE): 설정 키
- `encrypted_value` (TEXT): 암호화된 값
- `description` (TEXT): 설정 설명
- `is_active` (BOOLEAN): 활성화 상태
- `created_at`, `updated_at`: 생성/수정 시간
- 인덱스: `config_key`, `is_active`

##### 🔗 테이블 관계도
```
stocks (1) ←→ (N) daily_data
stocks (1) ←→ (N) weekly_data  
stocks (1) ←→ (N) monthly_data
stocks (1) ←→ (N) technical_indicators
stocks (1) ←→ (1) stock_collection_status
prompt_categories (1) ←→ (N) prompts
```

##### 📊 데이터 품질 관리
- **장중/장마감 구분**: `last_collected_timestamp`로 데이터 수집 시점 추적
- **품질 분류**: `collection_quality`로 INTRADAY/CLOSING/UNKNOWN 자동 분류
- **자동 검증**: 데이터 품질 점수 기반 자동 검증 및 재수집 권장
- **변경 추적**: 모든 데이터 변경 사항에 대한 상세한 감사 로그

#### 테스트 종목
- **019210**: YG-1 (KOSPI)
- **023410**: 유진기업 (KOSPI)
- **145720**: 덴티움 (KOSDAQ)
- **005930**: 삼성전자 (KOSPI)
- **014280**: 금강철강 (KOSPI)

## 📋 프로젝트 규칙 및 표준

### 🎯 데이터 수집 우선순위
- **1순위**: Yahoo Finance (야후 파이낸스)
- **2순위**: KRX, 키움증권 API, 네이버 금융

### 🗄️ 종목 정보 관리 원칙
**모든 종목 관련 정보는 반드시 DB의 'stocks' 테이블을 우선 참조해야 함**

- 종목코드, 종목명, 마켓 구분은 `stocks` 테이블에서 조회
- 하드코딩된 종목 정보 사용 금지
- 외부 API에서 종목 정보 직접 파싱 금지

### 🔍 기존 코드 참고 규칙 (중요!)
**모든 코드 수정 작업 전에 반드시 기존 코드나 파일을 먼저 검토하고 참고해야 함**

#### ✅ 해야 할 것
1. **기존 코드 검토**: 수정하려는 기능과 유사한 기존 코드가 있는지 먼저 확인
2. **기존 함수 활용**: 이미 구현된 함수나 클래스가 있다면 재사용
3. **기존 패턴 따르기**: 프로젝트의 코딩 스타일과 패턴을 일관성 있게 유지
4. **기존 테이블 활용**: 새로운 테이블 생성 전에 기존 테이블 구조 검토

#### ❌ 하지 말아야 할 것
1. **중복 코드 작성**: 기존에 있는 기능을 새로 구현하지 않음
2. **기존 코드 무시**: 기존 구현을 확인하지 않고 새로운 코드 작성
3. **일관성 없는 패턴**: 프로젝트 전체와 다른 코딩 스타일 사용
4. **불필요한 의존성 추가**: 기존 모듈로 해결 가능한 기능에 새 라이브러리 도입

자세한 규칙은 `.cursor/rules/stockchart.mdc` 파일을 참조하세요.

## 📝 라이선스

이 프로젝트는 교육 및 개인 사용 목적으로 제작되었습니다.

## 🤝 기여

버그 리포트나 기능 제안은 이슈를 통해 제출해주세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 통해 문의해주세요.

## 🔄 개발 로드맵

### ✅ 현재 완료된 기능
- ✅ MySQL 데이터베이스 구축
- ✅ 테스트 종목 5개 데이터 수집 (10년치 일봉)
- ✅ 기술적 지표 자동 계산 및 저장
- ✅ 데이터베이스 스키마 설계
- ✅ 향상된 데이터 검증 시스템
- ✅ 주봉/월봉 데이터 자동 생성
- ✅ 웹 인터페이스 시스템
- ✅ 배치 분석 시스템
- ✅ 통합 분석 시스템
- ✅ 전일 데이터 품질 검증 시스템 (2025-08-22)
- ✅ 프롬프트 관리 시스템 (2025-08-22)
- ✅ 데이터 변경 추적 시스템 (2025-08-22)
- ✅ REST API 시스템 (2025-08-22)
- ✅ 프롬프트 관리 웹 인터페이스 (2025-08-22)
- ✅ 거래량 랭킹 시스템 (2025-08-23)
- ✅ 데이터베이스 스키마 업데이트 (2025-08-23)
- ✅ 프로젝트 정리 및 최적화 (2025-08-27)

### 🔄 현재 진행 중인 기능
- 🔄 차트 생성 모듈을 DB 기반으로 수정
- 🔄 증분 업데이트 시스템 구현

### 📋 다음 개발 계획
- 🔄 전체 상장 종목 자동 수집
- 🔄 자동화된 일일 데이터 수집 (장마감 후)
- 🔄 실시간 데이터 수집 시스템
- 🔄 고급 기술적 지표 추가
- 🔄 백테스팅 시스템 구현
- 🔄 포트폴리오 분석 기능
- 🔄 알림 시스템 구현
- 🔄 거래량 랭킹 실시간 업데이트
- 🔄 외부 API를 통한 유통주식수 자동 수집
C I / C D   LѤ¸� 
 C I / C D   ��ٳ  0���  LѤ¸�  -   0 8 / 2 8 / 2 0 2 5   0 9 : 0 7 : 0 4  
  
 # #     C I / C D   ��ٳ  0���  LѤ¸�  -   2 0 2 5 - 0 8 - 2 8   1 0 : 2 3 : 4 0  
 G i t H u b   A c t i o n s |�  ��\�  ��ٳ  0��� �  1����<�\�  ��ٳX��  �ǵ�Ȳ�!    
 