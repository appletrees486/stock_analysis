# 🖥️ 서버 접속 및 MySQL DB 관리 가이드

## 🔐 **서버 접속 방법**

### 📋 **서버 정보**
- **서버 IP**: `211.188.61.165`
- **사용자**: `ubuntu`
- **접속 방식**: SSH Key 인증
- **SSH 키**: `C:\Users\jdari\.ssh\master-key.pem`
- **웹 포트**: `5000`

### 🚀 **기본 SSH 접속**

#### Windows PowerShell에서 접속
```bash
# 기본 접속
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165

# 접속과 동시에 프로젝트 디렉토리 이동
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && bash"
```

#### 접속 후 기본 작업 디렉토리
```bash
cd ~/stock_analysis  # 프로젝트 루트 디렉토리
```

### ⚡ **원격 명령어 실행**

#### 단일 명령어 실행
```bash
# 서버 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "uptime && free -h && df -h"

# 애플리케이션 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "ps aux | grep python"

# Git 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git status"
```

#### 복합 명령어 실행
```bash
# 배포 및 재시작
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull origin main && pkill -f 'python.*app.py' || echo 'No process' && sleep 3 && source venv/bin/activate && nohup python app.py > app.log 2>&1 &"
```

### 🔧 **SSH 연결 트러블슈팅**

#### 연결 시간 초과 문제
```bash
# 연결 타임아웃 설정 (30초)
ssh -i C:\Users\jdari\.ssh\master-key.pem -o ConnectTimeout=30 ubuntu@211.188.61.165

# 연결 유지 설정
ssh -i C:\Users\jdari\.ssh\master-key.pem -o ServerAliveInterval=60 -o ServerAliveCountMax=3 ubuntu@211.188.61.165
```

#### 권한 문제 해결
```bash
# SSH 키 권한 확인 (Windows)
icacls C:\Users\jdari\.ssh\master-key.pem

# 필요시 권한 수정
icacls C:\Users\jdari\.ssh\master-key.pem /inheritance:r /grant:r "%USERNAME%:R"
```

---

## 🗄️ **MySQL 데이터베이스 접속**

### 📋 **데이터베이스 정보**
- **호스트**: `localhost` (서버 내부)
- **포트**: `3306`
- **사용자**: `root`
- **비밀번호**: `1234`
- **데이터베이스**: `stock_analysis`
- **문자셋**: `utf8mb4`

### 🔐 **접속 방법들**

#### 1️⃣ **서버에서 직접 MySQL 접속**
```bash
# SSH로 서버 접속 후
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165

# MySQL 접속
mysql -u root -p1234 stock_analysis

# 또는 비밀번호 입력 방식
mysql -u root -p stock_analysis
```

#### 2️⃣ **원격에서 MySQL 명령어 실행**
```bash
# 단일 쿼리 실행
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SHOW TABLES;'"

# 복합 쿼리 실행
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SELECT COUNT(*) as total_stocks FROM stocks; SELECT COUNT(*) as total_daily_data FROM daily_stock_data;'"
```

#### 3️⃣ **Python을 통한 DB 접속 테스트**
```bash
# 서버에서 Python DB 연결 테스트
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && python -c 'from database_config import DatabaseManager; db = DatabaseManager(); print(\"✅ 연결 성공\" if db.connect() else \"❌ 연결 실패\"); db.disconnect()'"
```

### 📊 **데이터베이스 구조 확인**

#### 테이블 목록 조회
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SHOW TABLES;'"
```

#### 주요 테이블 구조 확인
```bash
# 주식 정보 테이블
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'DESCRIBE stocks;'"

# 일봉 데이터 테이블
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'DESCRIBE daily_stock_data;'"

# 주봉 데이터 테이블
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'DESCRIBE weekly_stock_data;'"
```

#### 데이터 개수 확인
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SELECT 
    (SELECT COUNT(*) FROM stocks) as 주식종목수,
    (SELECT COUNT(*) FROM daily_stock_data) as 일봉데이터수,
    (SELECT COUNT(*) FROM weekly_stock_data) as 주봉데이터수,
    (SELECT COUNT(*) FROM monthly_stock_data) as 월봉데이터수;'"
```

---

## 🛠️ **데이터베이스 관리 작업**

### 📊 **데이터 조회 예제**

#### 최신 주식 데이터 확인
```bash
# 최근 업데이트된 일봉 데이터 (최근 5건)
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SELECT s.name, d.date, d.close, d.volume FROM daily_stock_data d JOIN stocks s ON d.stock_id = s.id ORDER BY d.date DESC LIMIT 5;'"

# 특정 종목 최근 데이터
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SELECT d.date, d.open, d.high, d.low, d.close, d.volume FROM daily_stock_data d JOIN stocks s ON d.stock_id = s.id WHERE s.code = \"005930\" ORDER BY d.date DESC LIMIT 10;'"
```

#### 데이터베이스 통계
```bash
# 테이블별 용량 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SELECT table_name, ROUND(((data_length + index_length) / 1024 / 1024), 2) AS \"Size in MB\" FROM information_schema.tables WHERE table_schema = \"stock_analysis\" ORDER BY (data_length + index_length) DESC;'"
```

### 🔧 **데이터베이스 백업 및 복원**

#### 전체 데이터베이스 백업
```bash
# 서버에서 백업 생성
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysqldump -u root -p1234 stock_analysis > ~/stock_analysis_backup_$(date +%Y%m%d_%H%M%S).sql"

# 백업 파일 목록 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "ls -la ~/*backup*.sql"
```

#### 특정 테이블만 백업
```bash
# 주식 기본 정보만 백업
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysqldump -u root -p1234 stock_analysis stocks > ~/stocks_backup_$(date +%Y%m%d).sql"
```

#### 백업 복원
```bash
# 전체 데이터베이스 복원
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis < ~/stock_analysis_backup_YYYYMMDD_HHMMSS.sql"
```

---

## 🔍 **모니터링 및 진단**

### 📊 **서버 리소스 모니터링**

#### 실시간 시스템 상태
```bash
# 종합 시스템 상태
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "echo '=== CPU/Memory ===' && top -bn1 | head -5 && echo '=== Disk Usage ===' && df -h && echo '=== Memory Details ===' && free -h && echo '=== Load Average ===' && uptime"

# MySQL 프로세스 상태
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "ps aux | grep mysql"

# Python 애플리케이션 상태
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "ps aux | grep python"
```

#### 네트워크 연결 상태
```bash
# 포트 사용 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "netstat -tlnp | grep -E ':(3306|5000)'"

# 외부에서 연결 테스트 (PowerShell)
Test-NetConnection 211.188.61.165 -Port 5000  # 웹 애플리케이션
Test-NetConnection 211.188.61.165 -Port 3306  # MySQL (일반적으로 외부 접속 차단됨)
```

### 🗄️ **MySQL 상태 모니터링**

#### MySQL 서버 상태
```bash
# MySQL 서비스 상태
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "systemctl status mysql"

# MySQL 프로세스 리스트
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 -e 'SHOW PROCESSLIST;'"

# MySQL 상태 변수
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 -e 'SHOW STATUS LIKE \"Threads%\";'"
```

#### 데이터베이스 연결 테스트
```bash
# Python을 통한 연결 테스트
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && python database_config.py"
```

---

## 🚨 **문제 해결 가이드**

### 🔧 **SSH 연결 문제**

#### 연결 거부 (Connection refused)
```bash
# 서버 상태 확인
ping 211.188.61.165

# 다른 포트로 연결 시도 (SSH 기본 포트가 변경되었을 수 있음)
ssh -i C:\Users\jdari\.ssh\master-key.pem -p 22 ubuntu@211.188.61.165
```

#### 권한 거부 (Permission denied)
```bash
# SSH 키 권한 확인
ls -la C:\Users\jdari\.ssh\master-key.pem

# 키 파일 권한 수정 (필요시)
chmod 600 C:\Users\jdari\.ssh\master-key.pem
```

### 🗄️ **MySQL 연결 문제**

#### 연결 실패 (Access denied)
```bash
# MySQL 서비스 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "systemctl status mysql"

# MySQL 재시작
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "sudo systemctl restart mysql"
```

#### 데이터베이스 없음 (Database doesn't exist)
```bash
# 데이터베이스 생성
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 -e 'CREATE DATABASE IF NOT EXISTS stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'"

# 데이터베이스 목록 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 -e 'SHOW DATABASES;'"
```

### 🐍 **Python 애플리케이션 문제**

#### 애플리케이션 실행 실패
```bash
# 로그 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && tail -20 app.log"

# 가상환경 활성화 후 수동 실행
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && source venv/bin/activate && python app.py"
```

---

## 📋 **자주 사용하는 명령어 모음**

### ⚡ **빠른 접속 및 상태 확인**
```bash
# 서버 전체 상태 한 번에 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "echo '=== System Info ===' && uptime && free -h && echo '=== Disk Usage ===' && df -h && echo '=== Application Status ===' && ps aux | grep python | grep -v grep && echo '=== MySQL Status ===' && systemctl status mysql --no-pager -l"

# 데이터베이스 연결 및 기본 정보 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "mysql -u root -p1234 stock_analysis -e 'SELECT COUNT(*) as stocks FROM stocks; SELECT COUNT(*) as daily_data FROM daily_stock_data; SELECT MAX(date) as latest_date FROM daily_stock_data;'"
```

### 📊 **모니터링 대시보드**
```bash
# 실시간 모니터링 (서버에서 실행)
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && ./server_monitor.sh"
```

### 🔄 **일상적인 관리 작업**
```bash
# 애플리케이션 재시작
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && pkill -f 'python.*app.py' && sleep 3 && source venv/bin/activate && nohup python app.py > app.log 2>&1 &"

# 로그 실시간 모니터링
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && tail -f app.log"
```

---

## 🎯 **보안 고려사항**

### 🔐 **SSH 보안**
- SSH 키는 안전한 위치에 보관 (`C:\Users\jdari\.ssh\`)
- 키 파일 권한을 적절히 설정 (읽기 전용)
- 불필요한 포트 노출 방지

### 🗄️ **MySQL 보안**
- 데이터베이스 비밀번호 정기 변경 권장
- 외부 접속 차단 (localhost만 허용)
- 정기적인 백업 수행

### 🌐 **웹 애플리케이션 보안**
- 방화벽 설정 확인
- HTTPS 적용 고려 (향후)
- 로그 모니터링

---

## 📞 **지원 및 문의**

### 🔧 **문제 발생 시 순서**
1. **연결 테스트**: `Test-NetConnection 211.188.61.165 -Port 5000`
2. **서버 상태 확인**: SSH로 접속하여 시스템 리소스 확인
3. **애플리케이션 로그**: `tail -20 ~/stock_analysis/app.log`
4. **MySQL 상태**: `systemctl status mysql`
5. **긴급 복구**: `./emergency_recovery.sh` 실행

### 📊 **정기 점검 항목**
- [ ] 서버 리소스 사용량 (메모리, 디스크)
- [ ] MySQL 데이터베이스 상태
- [ ] 웹 애플리케이션 접속 가능 여부
- [ ] 로그 파일 용량 및 오류 메시지
- [ ] 백업 파일 생성 및 보관

**🎯 이 가이드를 통해 서버와 데이터베이스를 안전하고 효율적으로 관리하세요!**
