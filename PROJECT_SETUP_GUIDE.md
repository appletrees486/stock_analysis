# 📋 주식 분석 프로그램 - 프로젝트 이전 가이드

> **목적**: 이 프로젝트를 다른 PC로 완전히 이전하고 동일한 환경에서 실행하기 위한 상세 가이드

---

## 📌 목차

1. [시스템 요구사항](#1-시스템-요구사항)
2. [Python 환경 설정](#2-python-환경-설정)
3. [MySQL 데이터베이스 설정](#3-mysql-데이터베이스-설정)
4. [프로젝트 파일 복사](#4-프로젝트-파일-복사)
5. [Python 라이브러리 설치](#5-python-라이브러리-설치)
6. [API 키 및 설정 파일](#6-api-키-및-설정-파일)
7. [데이터베이스 초기화](#7-데이터베이스-초기화)
8. [폴더 구조 생성](#8-폴더-구조-생성)
9. [웹 서버 실행 테스트](#9-웹-서버-실행-테스트)
10. [블로그 자동화 추가 설정](#10-블로그-자동화-추가-설정)
11. [환경 변수 설정](#11-환경-변수-설정-선택사항)
12. [트러블슈팅](#12-트러블슈팅)
13. [체크리스트](#13-최종-체크리스트)

---

## 1. 시스템 요구사항

### 1.1 운영체제
- **Windows**: Windows 10 이상 (64bit)
- **Linux**: Ubuntu 20.04 LTS 이상 / CentOS 8 이상
- **macOS**: macOS 11.0 (Big Sur) 이상

### 1.2 필수 소프트웨어
| 소프트웨어 | 최소 버전 | 권장 버전 | 다운로드 |
|-----------|----------|----------|---------|
| Python | 3.7 | 3.9 이상 | https://www.python.org/downloads/ |
| MySQL | 8.0 | 8.0.33 이상 | https://dev.mysql.com/downloads/mysql/ |
| Chrome 브라우저 | 최신 | 최신 | https://www.google.com/chrome/ (블로그 자동화 기능 사용 시) |

### 1.3 하드웨어 권장 사양
- **CPU**: 4코어 이상
- **RAM**: 8GB 이상
- **저장공간**: 10GB 이상 여유 공간
- **네트워크**: 안정적인 인터넷 연결

### 1.4 포트 사용
- **MySQL**: 3306 (기본값, 변경 가능)
- **Flask 웹서버**: 5000 (기본값)

---

## 2. Python 환경 설정

### 2.1 Python 설치 확인

```bash
# Windows
python --version

# Linux/macOS
python3 --version
```

**예상 출력**: `Python 3.9.x` 또는 그 이상

### 2.2 Python 설치 (필요시)

**Windows:**
1. https://www.python.org/downloads/ 접속
2. "Download Python 3.9.x" 클릭
3. 설치 시 **"Add Python to PATH"** 체크박스 필수 선택
4. "Install Now" 클릭

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install python@3.9
```

### 2.3 pip 업그레이드

```bash
# Windows
python -m pip install --upgrade pip

# Linux/macOS
python3 -m pip install --upgrade pip
```

### 2.4 가상환경 생성 (권장)

```bash
# Windows
cd D:\project\stock_analysis
python -m venv venv
venv\Scripts\activate

# Linux/macOS
cd /path/to/stock_analysis
python3 -m venv venv
source venv/bin/activate
```

**가상환경 활성화 확인**: 커맨드 라인 앞에 `(venv)` 표시

---

## 3. MySQL 데이터베이스 설정

### 3.1 MySQL 설치

**Windows:**
1. https://dev.mysql.com/downloads/mysql/ 접속
2. MySQL Community Server 다운로드
3. 설치 마법사 실행
   - Server Configuration Type: `Development Computer`
   - Authentication Method: `Use Strong Password Encryption`
   - root 비밀번호 설정: `1234` (또는 원하는 비밀번호)

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
```

**macOS:**
```bash
brew install mysql@8.0
brew services start mysql@8.0
```

### 3.2 MySQL 서비스 시작 및 확인

**Windows:**
```bash
# 서비스 시작
net start MySQL80

# 서비스 확인
sc query MySQL80
```

**Linux:**
```bash
# 서비스 시작
sudo systemctl start mysql

# 서비스 확인
sudo systemctl status mysql

# 부팅 시 자동 시작 설정
sudo systemctl enable mysql
```

**macOS:**
```bash
brew services start mysql@8.0
```

### 3.3 MySQL 접속 테스트

```bash
# Windows
mysql -u root -p

# Linux/macOS
mysql -u root -p
```

비밀번호 입력 후 `mysql>` 프롬프트가 나타나면 성공

### 3.4 데이터베이스 생성

MySQL 접속 후:
```sql
CREATE DATABASE stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SHOW DATABASES;
EXIT;
```

### 3.5 MySQL 사용자 권한 설정 (선택사항)

별도 사용자 생성 시:
```sql
CREATE USER 'stockapp'@'localhost' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON stock_analysis.* TO 'stockapp'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 4. 프로젝트 파일 복사

### 4.1 Git으로 복사 (권장)

```bash
# Git이 설치되어 있다면
cd D:\project
git clone [repository_url] stock_analysis
cd stock_analysis
```

### 4.2 직접 복사

기존 PC에서 다음 폴더/파일을 USB 또는 네트워크로 복사:

```
stock_analysis/
├── *.py (모든 Python 파일)
├── requirements.txt
├── stock_mapping.json
├── templates/ (폴더 전체)
├── static/ (폴더 전체)
├── api/ (폴더 전체)
├── blog_auto/ (폴더 전체)
├── docs/ (폴더 전체)
└── *.sql (모든 SQL 파일)
```

**⚠️ 제외할 파일/폴더** (복사하지 않음):
```
__pycache__/
*.pyc
venv/
.git/ (필요시 제외)
*.log
config.txt (새로 생성 필요)
database_config.txt (새로 생성 필요)
gmail_config.txt (새로 생성 필요)
.secret_key (자동 생성됨)
```

---

## 5. Python 라이브러리 설치

### 5.1 메인 프로젝트 라이브러리

```bash
cd D:\project\stock_analysis

# 가상환경 활성화 (사용하는 경우)
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 라이브러리 설치
pip install -r requirements.txt
```

### 5.2 설치되는 주요 라이브러리

```
데이터 조회 및 처리:
- yfinance>=0.2.0 (야후 파이낸스 데이터)
- pandas>=1.3.0 (데이터 처리)
- numpy>=1.21.0 (수치 계산)
- pykrx>=1.0.0 (한국 주식 데이터)

차트 시각화:
- matplotlib>=3.5.0
- mplfinance>=0.12.0

데이터베이스:
- mysql-connector-python>=8.0.0

웹 서버:
- Flask>=2.3.0
- Flask-CORS>=4.0.0
- Werkzeug>=2.3.0

AI 분석:
- google-generativeai>=0.3.0
- Pillow>=9.0.0

스케줄링:
- APScheduler>=3.10.0

기타:
- python-dateutil>=2.8.0
- json5>=0.9.0
- python-docx>=0.8.11
- openpyxl>=3.1.0
- requests>=2.28.0
- PyJWT>=2.8.0
```

### 5.3 자동 설치 스크립트 사용

**Windows:**
```bash
install.bat
```

**Linux/macOS:**
```bash
chmod +x install.sh
./install.sh
```

### 5.4 설치 확인

```bash
# 주요 패키지 설치 확인
python -c "import yfinance; print('yfinance OK')"
python -c "import pandas; print('pandas OK')"
python -c "import flask; print('Flask OK')"
python -c "import mysql.connector; print('MySQL Connector OK')"
python -c "import google.generativeai; print('Google Gemini OK')"
```

---

## 6. API 키 및 설정 파일

### 6.1 Google Gemini API 키 설정 (필수)

#### API 키 발급
1. https://makersuite.google.com/app/apikey 접속
2. Google 계정으로 로그인
3. "Create API Key" 클릭
4. API 키 복사 (예: `AIzaSyAaBbCcDdEeFf...`)

#### API 키 저장 방법 1: 자동 스크립트 사용 (권장)
```bash
python setup_api_key.py
```
프롬프트에 API 키 입력

#### API 키 저장 방법 2: 수동으로 파일 생성
`config.txt` 파일 생성:
```
AIzaSyAaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPp
```
(API 키만 한 줄로 입력, 앞뒤 공백 없이)

### 6.2 MySQL 데이터베이스 연결 설정 (필수)

`database_config.txt` 파일 생성:
```ini
# MySQL 데이터베이스 설정
host=localhost
port=3306
user=root
password=1234
database=stock_analysis
```

**⚠️ 주의**: 비밀번호를 실제 MySQL root 비밀번호로 변경하세요.

### 6.3 Gmail API 설정 (선택사항)

블로그 자동 포스팅 알림 기능 사용 시에만 필요

#### OAuth 2.0 클라이언트 ID 발급
1. https://console.cloud.google.com/ 접속
2. 프로젝트 생성 또는 선택
3. "API 및 서비스" → "사용자 인증 정보" → "사용자 인증 정보 만들기"
4. "OAuth 클라이언트 ID" 선택
5. 애플리케이션 유형: "데스크톱 앱"
6. Client ID와 Client Secret 복사

#### 설정 파일 생성
`gmail_config.txt` 파일 생성:
```ini
# Gmail API 설정
client_id=your_client_id.apps.googleusercontent.com
client_secret=your_client_secret
redirect_uri=http://localhost:8080/callback
```

---

## 7. 데이터베이스 초기화

### 7.1 테이블 생성 순서

**반드시 순서대로 실행:**

```bash
# 1. 기본 스키마 생성 (stocks, daily_data, weekly_data, monthly_data, technical_indicators 등)
python create_database_schema.py

# 2. 프롬프트 관리 테이블 생성
python create_prompt_tables.py

# 3. 수집 작업 관리 테이블 생성
python create_collection_management_tables.py

# 4. 자동 분석 테이블 생성
python create_auto_analysis_tables.py
```

### 7.2 예상 출력

```
🚀 MySQL 데이터베이스 스키마 생성 시작
==================================================
✅ stocks 테이블 생성 완료
✅ daily_data 테이블 생성 완료
✅ weekly_data 테이블 생성 완료
✅ monthly_data 테이블 생성 완료
✅ technical_indicators 테이블 생성 완료
✅ data_collection_log 테이블 생성 완료
✅ stock_collection_status 테이블 생성 완료
✅ 테스트 종목 5개 삽입 완료
🎉 데이터베이스 스키마 생성 완료!
```

### 7.3 테이블 생성 확인

```bash
mysql -u root -p
```

MySQL 접속 후:
```sql
USE stock_analysis;
SHOW TABLES;
```

**예상 테이블 목록:**
```
+--------------------------------+
| Tables_in_stock_analysis       |
+--------------------------------+
| auto_analysis_jobs             |
| batch_schedules                |
| collection_jobs                |
| daily_data                     |
| daily_data_collection_log      |
| data_collection_log            |
| monthly_data                   |
| prompt_categories              |
| prompts                        |
| secure_configs                 |
| stock_collection_status        |
| stocks                         |
| technical_indicators           |
| weekly_data                    |
+--------------------------------+
```

### 7.4 초기 데이터 수집 (선택사항)

테스트를 위한 샘플 종목 데이터 수집:
```bash
python stock_data_collector.py
```

**처리 시간**: 종목당 약 30초~1분 (네트워크 속도에 따라 다름)

### 7.5 주봉/월봉 데이터 생성 (선택사항)

일봉 데이터 수집 후:
```bash
python week_month_data_generator.py
```

---

## 8. 폴더 구조 생성

### 8.1 자동 생성되는 폴더

프로그램 실행 시 자동으로 생성되지만, 미리 만들어두면 권한 문제 방지:

```bash
# Windows
mkdir daily_charts weekly_charts monthly_charts
mkdir ai_analysis_results chart_data_json chart_data_text
mkdir uploads\charts uploads\stock_lists
mkdir results logs

# Linux/macOS
mkdir -p daily_charts weekly_charts monthly_charts
mkdir -p ai_analysis_results chart_data_json chart_data_text
mkdir -p uploads/charts uploads/stock_lists
mkdir -p results logs
```

### 8.2 전체 폴더 구조

```
stock_analysis/
├── api/                          # 웹 API 모듈
│   ├── __init__.py
│   ├── routes.py
│   ├── batch_analyzer.py
│   ├── prompt_routes.py
│   ├── daily_collection_routes.py
│   ├── batch_schedule_routes.py
│   ├── auto_batch_routes.py
│   ├── utils.py
│   └── volume_ranking_utils.py
├── blog_auto/                    # 블로그 자동화 모듈
│   ├── auto_blog.py
│   ├── requirements.txt
│   └── ...
├── static/                       # 웹 정적 파일
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── single.js
│       ├── batch.js
│       └── multi_batch.js
├── templates/                    # 웹 템플릿
│   ├── index.html
│   ├── single_analysis.html
│   ├── batch_analysis.html
│   ├── prompt_management.html
│   ├── volume_ranking.html
│   ├── daily_collection.html
│   └── batch_schedule.html
├── daily_charts/                 # 일봉 차트 저장
├── weekly_charts/                # 주봉 차트 저장
├── monthly_charts/               # 월봉 차트 저장
├── ai_analysis_results/          # AI 분석 결과
├── chart_data_json/              # 차트 JSON 데이터
├── chart_data_text/              # 차트 텍스트 데이터
├── uploads/                      # 웹 업로드 파일
│   ├── charts/
│   └── stock_lists/
├── results/                      # 배치 분석 결과
├── logs/                         # 로그 파일
├── docs/                         # 문서
├── config.txt                    # Google AI API 키 (생성 필요)
├── database_config.txt           # MySQL 접속 정보 (생성 필요)
├── gmail_config.txt              # Gmail API 설정 (선택사항)
├── stock_mapping.json            # 종목 코드-이름 매핑
├── requirements.txt              # Python 라이브러리 목록
├── app.py                        # Flask 웹 서버
├── batch_scheduler.py            # 배치 스케줄러
└── ... (기타 Python 스크립트들)
```

---

## 9. 웹 서버 실행 테스트

### 9.1 Flask 웹 서버 시작

```bash
python app.py
```

### 9.2 예상 출력

```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### 9.3 웹 인터페이스 접속

브라우저에서 다음 URL 접속:

- **메인 페이지**: http://localhost:5000
- **단일 분석**: http://localhost:5000/single
- **배치 분석**: http://localhost:5000/batch
- **프롬프트 관리**: http://localhost:5000/prompts
- **거래량 랭킹**: http://localhost:5000/volume-ranking
- **일일 수집**: http://localhost:5000/daily-collection
- **배치 스케줄**: http://localhost:5000/batch-schedule

### 9.4 배치 스케줄러 시작 (선택사항)

별도 터미널에서:
```bash
python batch_scheduler.py
```

---

## 10. 블로그 자동화 추가 설정

블로그 자동 포스팅 기능을 사용할 경우에만 필요

### 10.1 Chrome 브라우저 설치 확인

```bash
# Chrome이 설치되어 있는지 확인
# Windows: C:\Program Files\Google\Chrome\Application\chrome.exe
# Linux: /usr/bin/google-chrome
# macOS: /Applications/Google Chrome.app
```

### 10.2 블로그 자동화 전용 라이브러리 설치

```bash
cd blog_auto
pip install -r requirements.txt
```

**설치되는 라이브러리:**
- selenium>=4.15.2 (웹 자동화)
- pyperclip>=1.8.2 (클립보드)
- webdriver-manager>=4.0.1 (Chrome 드라이버 자동 관리)
- python-docx>=1.2.0 (Word 문서)
- Pillow>=9.0.0 (이미지 처리)

### 10.3 ChromeDriver 자동 설치

webdriver-manager가 자동으로 처리하므로 별도 설치 불필요

### 10.4 블로그 자동화 테스트

```bash
cd blog_auto
python auto_blog.py
```

---

## 11. 환경 변수 설정 (선택사항)

### 11.1 Windows 환경 변수

시스템 설정에서 환경 변수 추가:

```bash
# Windows 명령 프롬프트 (관리자 권한)
setx GOOGLE_AI_API_KEY "your_api_key_here"
setx DB_HOST "localhost"
setx DB_USER "root"
setx DB_PASSWORD "1234"
setx DB_PORT "3306"
setx DB_NAME "stock_analysis"
```

또는 **시스템 속성** → **고급** → **환경 변수**에서 GUI로 설정

### 11.2 Linux/macOS 환경 변수

`~/.bashrc` 또는 `~/.zshrc`에 추가:

```bash
export GOOGLE_AI_API_KEY="your_api_key_here"
export DB_HOST="localhost"
export DB_USER="root"
export DB_PASSWORD="1234"
export DB_PORT="3306"
export DB_NAME="stock_analysis"
```

적용:
```bash
source ~/.bashrc  # 또는 source ~/.zshrc
```

### 11.3 환경 변수 확인

```bash
# Windows
echo %GOOGLE_AI_API_KEY%
echo %DB_HOST%

# Linux/macOS
echo $GOOGLE_AI_API_KEY
echo $DB_HOST
```

**⚠️ 주의**: 환경 변수 설정은 선택사항입니다. 설정 파일(config.txt, database_config.txt)을 사용하는 것을 권장합니다.

---

## 12. 트러블슈팅

### 12.1 Python 관련 오류

#### `python: command not found` (Linux/macOS)
```bash
# python3로 시도
python3 --version
python3 -m pip install -r requirements.txt
```

#### `pip: command not found`
```bash
# Windows
python -m ensurepip --upgrade

# Linux/macOS
python3 -m ensurepip --upgrade
```

#### 라이브러리 설치 실패
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 관리자 권한으로 재시도 (Windows)
# 관리자 권한으로 명령 프롬프트 실행 후
python -m pip install -r requirements.txt

# Linux/macOS
sudo pip3 install -r requirements.txt
```

### 12.2 MySQL 관련 오류

#### `ERROR 2003 (HY000): Can't connect to MySQL server`

**원인**: MySQL 서비스가 실행되지 않음

**해결방법:**
```bash
# Windows
net start MySQL80

# Linux
sudo systemctl start mysql
sudo systemctl status mysql

# macOS
brew services start mysql@8.0
```

#### `Access denied for user 'root'@'localhost'`

**원인**: 비밀번호 불일치

**해결방법:**
1. MySQL root 비밀번호 확인
2. `database_config.txt`의 비밀번호 수정
3. 또는 MySQL 비밀번호 재설정

#### MySQL 비밀번호 재설정 (Windows)
```bash
# MySQL 서비스 중지
net stop MySQL80

# 안전 모드로 시작
mysqld --console --skip-grant-tables --shared-memory

# 새 터미널에서
mysql -u root
```

MySQL 접속 후:
```sql
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY '1234';
FLUSH PRIVILEGES;
EXIT;
```

#### `Database 'stock_analysis' doesn't exist`

**해결방법:**
```bash
mysql -u root -p
```

```sql
CREATE DATABASE stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 12.3 API 키 관련 오류

#### `API key not valid. Please pass a valid API key.`

**원인**: Google Gemini API 키 미설정 또는 잘못된 키

**해결방법:**
1. https://makersuite.google.com/app/apikey 에서 새 API 키 발급
2. `config.txt` 파일 확인 (앞뒤 공백, 줄바꿈 없이 순수 키만)
3. `python setup_api_key.py` 재실행

### 12.4 웹 서버 관련 오류

#### `Address already in use`

**원인**: 5000 포트가 이미 사용 중

**해결방법:**
```bash
# Windows - 포트 사용 프로세스 확인
netstat -ano | findstr :5000

# 프로세스 종료
taskkill /PID [프로세스ID] /F

# Linux/macOS
lsof -i :5000
kill -9 [PID]
```

또는 `app.py`에서 포트 변경:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)  # 5001로 변경
```

#### `Template not found`

**원인**: templates 폴더 누락

**해결방법:**
```bash
# templates 폴더가 있는지 확인
ls templates/  # Linux/macOS
dir templates\ # Windows

# 없으면 프로젝트 파일 재복사
```

### 12.5 블로그 자동화 관련 오류

#### `selenium.common.exceptions.WebDriverException`

**원인**: Chrome 드라이버 문제

**해결방법:**
```bash
# Chrome 브라우저 최신 버전 설치 확인
# webdriver-manager가 자동으로 처리하므로 재실행
cd blog_auto
python auto_blog.py
```

#### `ModuleNotFoundError: No module named 'PIL'`

**원인**: Pillow 라이브러리 미설치

**해결방법:**
```bash
pip install Pillow
```

### 12.6 권한 관련 오류

#### `PermissionError: [Errno 13] Permission denied`

**원인**: 폴더/파일 쓰기 권한 부족

**해결방법 (Windows):**
- 프로젝트 폴더 우클릭 → 속성 → 보안 → 편집 → 사용자에게 모든 권한 부여

**해결방법 (Linux/macOS):**
```bash
chmod -R 755 /path/to/stock_analysis
```

---

## 13. 최종 체크리스트

프로젝트 이전 완료 전 다음 항목을 확인하세요:

### ✅ 시스템 환경
- [ ] Python 3.7 이상 설치 완료
- [ ] pip 최신 버전으로 업그레이드
- [ ] MySQL 8.0 이상 설치 완료
- [ ] MySQL 서비스 실행 중
- [ ] Chrome 브라우저 설치 (블로그 자동화 사용 시)

### ✅ 프로젝트 파일
- [ ] 모든 Python 스크립트 복사 완료
- [ ] `requirements.txt` 파일 존재
- [ ] `stock_mapping.json` 파일 존재
- [ ] `templates/` 폴더 전체 복사
- [ ] `static/` 폴더 전체 복사
- [ ] `api/` 폴더 전체 복사
- [ ] `blog_auto/` 폴더 전체 복사 (사용 시)

### ✅ Python 라이브러리
- [ ] `pip install -r requirements.txt` 실행 완료
- [ ] `blog_auto/requirements.txt` 설치 완료 (사용 시)
- [ ] 주요 라이브러리 import 테스트 완료
  - [ ] `import yfinance`
  - [ ] `import pandas`
  - [ ] `import flask`
  - [ ] `import mysql.connector`
  - [ ] `import google.generativeai`

### ✅ 설정 파일
- [ ] `config.txt` 생성 및 Google Gemini API 키 설정
- [ ] `database_config.txt` 생성 및 MySQL 접속 정보 설정
- [ ] `gmail_config.txt` 생성 (선택사항)

### ✅ 데이터베이스
- [ ] MySQL `stock_analysis` 데이터베이스 생성
- [ ] `create_database_schema.py` 실행 완료
- [ ] `create_prompt_tables.py` 실행 완료
- [ ] `create_collection_management_tables.py` 실행 완료
- [ ] `create_auto_analysis_tables.py` 실행 완료
- [ ] `SHOW TABLES;`로 테이블 생성 확인

### ✅ 폴더 구조
- [ ] `daily_charts/` 폴더 생성
- [ ] `weekly_charts/` 폴더 생성
- [ ] `monthly_charts/` 폴더 생성
- [ ] `ai_analysis_results/` 폴더 생성
- [ ] `chart_data_json/` 폴더 생성
- [ ] `chart_data_text/` 폴더 생성
- [ ] `uploads/charts/` 폴더 생성
- [ ] `uploads/stock_lists/` 폴더 생성
- [ ] `results/` 폴더 생성
- [ ] `logs/` 폴더 생성

### ✅ 실행 테스트
- [ ] `python app.py` 실행 성공
- [ ] http://localhost:5000 접속 가능
- [ ] 웹 인터페이스 정상 표시
- [ ] `python batch_scheduler.py` 실행 성공 (선택사항)
- [ ] `python stock_data_collector.py` 실행 성공 (선택사항)

### ✅ 추가 테스트 (선택사항)
- [ ] 단일 종목 분석 테스트
- [ ] 배치 분석 테스트
- [ ] 프롬프트 관리 페이지 동작 확인
- [ ] 거래량 랭킹 조회 확인
- [ ] 일일 데이터 수집 테스트
- [ ] 블로그 자동 포스팅 테스트

---

## 📞 추가 지원

### 공식 문서
- **프로젝트 README**: `README.md` 참조
- **블로그 자동화**: `blog_auto/README.md` 참조
- **배치 스케줄링**: `DEPLOYMENT_*.md` 문서 참조

### 로그 파일 위치
- **웹 서버 로그**: `logs/batch_analysis_YYYYMMDD.log`
- **데이터베이스 로그**: `database.log`
- **시장 상태 로그**: `market_status.log`
- **데이터 검증 로그**: `enhanced_data_validator.log`
- **랭킹 추출 로그**: `ranking_extractor.log`
- **Gmail 발송 로그**: `gmail_sender.log`

### 유용한 명령어
```bash
# 프로젝트 버전 확인
python -c "import sys; print(f'Python: {sys.version}')"
python -c "import mysql.connector; print(f'MySQL Connector: {mysql.connector.__version__}')"
python -c "import flask; print(f'Flask: {flask.__version__}')"

# 데이터베이스 상태 확인
mysql -u root -p -e "SELECT COUNT(*) FROM stock_analysis.stocks;"
mysql -u root -p -e "SELECT COUNT(*) FROM stock_analysis.daily_data;"

# 로그 확인 (최근 50줄)
# Windows
type logs\batch_analysis_*.log | more
# Linux/macOS
tail -n 50 logs/batch_analysis_*.log
```

---

## 🎉 설치 완료!

모든 체크리스트가 완료되었다면 프로젝트 이전이 성공적으로 완료된 것입니다.

웹 서버를 시작하고 http://localhost:5000 에서 주식 분석을 시작하세요!

```bash
# 웹 서버 시작
python app.py

# 배치 스케줄러 시작 (별도 터미널)
python batch_scheduler.py
```

---

**작성일**: 2025-10-16  
**버전**: 1.0  
**작성자**: Stock Analysis Project Team

