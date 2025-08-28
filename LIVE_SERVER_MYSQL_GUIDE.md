# 🗄️ 라이브 서버 MySQL 접속 가이드

## 📊 **라이브 서버 MySQL 현황**

### ✅ **확인된 정보**
- **MySQL 버전**: 8.0.42 (Ubuntu 22.04)
- **서비스 상태**: ✅ 활성화 및 실행 중
- **메모리 사용량**: 429.4MB
- **포트**: 3306 (내부 접속만)
- **웹 애플리케이션**: ✅ 정상 작동 중 (포트 5000)

### ⚠️ **접속 제한사항**
- **직접 MySQL 접속**: 현재 인증 문제로 제한됨
- **root 사용자**: auth_socket 또는 특별한 인증 방식 사용
- **외부 접속**: 방화벽으로 차단됨 (보안상 올바름)

---

## 🔐 **현재 작동 중인 데이터베이스 설정**

### 📋 **실제 사용 중인 설정** (`database_config.txt`)
```ini
# 데이터베이스 설정 파일
# 생성일시: 2025-08-28

host=localhost
port=3306
user=root
password=1234
database=stock_analysis
```

### 🐍 **Python 애플리케이션을 통한 접속**
웹 애플리케이션이 정상 작동하고 있으므로, Python을 통한 DB 접속은 정상적으로 이루어지고 있습니다.

---

## 🛠️ **라이브 서버에서 데이터베이스 작업 방법**

### 1️⃣ **Python 스크립트를 통한 DB 작업** (권장)

#### 데이터 조회 스크립트 생성
```bash
# 서버에 접속
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165

# 프로젝트 디렉토리로 이동
cd ~/stock_analysis

# 가상환경 활성화
source venv/bin/activate

# Python으로 데이터 조회
python -c "
from database_config import DatabaseManager
db = DatabaseManager()
if db.connect():
    # 테이블 목록 조회
    tables = db.fetch_all('SHOW TABLES')
    print('📋 테이블 목록:')
    for table in tables:
        print(f'  - {list(table.values())[0]}')
    
    # 주식 개수 확인
    result = db.fetch_one('SELECT COUNT(*) as count FROM stocks')
    if result:
        print(f'📈 등록된 주식 종목 수: {result[\"count\"]}개')
    
    db.disconnect()
else:
    print('❌ 데이터베이스 연결 실패')
"
```

#### 간단한 DB 조회 스크립트 파일 생성
```bash
# 서버에서 실행
cat > ~/stock_analysis/db_query.py << 'EOF'
#!/usr/bin/env python3
from database_config import DatabaseManager
import sys

def main():
    db = DatabaseManager()
    if not db.connect():
        print("❌ 데이터베이스 연결 실패")
        return
    
    try:
        # 기본 통계 정보
        print("=== 📊 데이터베이스 통계 ===")
        
        # 테이블별 데이터 개수
        queries = {
            "주식 종목": "SELECT COUNT(*) as count FROM stocks",
            "일봉 데이터": "SELECT COUNT(*) as count FROM daily_stock_data", 
            "주봉 데이터": "SELECT COUNT(*) as count FROM weekly_stock_data",
            "월봉 데이터": "SELECT COUNT(*) as count FROM monthly_stock_data"
        }
        
        for name, query in queries.items():
            try:
                result = db.fetch_one(query)
                if result:
                    print(f"{name}: {result['count']:,}개")
            except:
                print(f"{name}: 테이블 없음")
        
        # 최신 데이터 날짜
        print("\n=== 📅 최신 데이터 날짜 ===")
        latest_daily = db.fetch_one("SELECT MAX(date) as latest FROM daily_stock_data")
        if latest_daily and latest_daily['latest']:
            print(f"일봉 최신 날짜: {latest_daily['latest']}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    main()
EOF

# 실행 권한 부여
chmod +x ~/stock_analysis/db_query.py

# 실행
python ~/stock_analysis/db_query.py
```

### 2️⃣ **웹 인터페이스를 통한 데이터 확인**

#### 웹 애플리케이션 접속
- **URL**: http://211.188.61.165:5000
- **기능**: 주식 데이터 조회, 차트 분석 등
- **장점**: GUI를 통한 직관적인 데이터 확인

### 3️⃣ **로그를 통한 데이터베이스 상태 모니터링**

#### 애플리케이션 로그 확인
```bash
# 실시간 로그 모니터링
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && tail -f app.log"

# 데이터베이스 관련 로그만 필터링
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && tail -50 app.log | grep -i 'mysql\|database\|연결'"
```

#### MySQL 시스템 로그 확인
```bash
# MySQL 서비스 로그
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "journalctl -u mysql -n 20 --no-pager"
```

---

## 🔧 **데이터베이스 관리 작업**

### 📊 **데이터 백업**

#### Python 스크립트를 통한 백업
```bash
# 서버에서 실행
cat > ~/stock_analysis/db_backup.py << 'EOF'
#!/usr/bin/env python3
from database_config import DatabaseManager
import json
from datetime import datetime

def backup_stocks_data():
    """주식 기본 정보 백업"""
    db = DatabaseManager()
    if not db.connect():
        return False
    
    try:
        stocks = db.fetch_all("SELECT * FROM stocks ORDER BY code")
        
        backup_file = f"stocks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 주식 데이터 백업 완료: {backup_file}")
        print(f"📊 백업된 종목 수: {len(stocks)}개")
        return True
        
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return False
    finally:
        db.disconnect()

if __name__ == "__main__":
    backup_stocks_data()
EOF

# 백업 실행
python ~/stock_analysis/db_backup.py
```

### 📈 **데이터 분석**

#### 주식 데이터 통계 스크립트
```bash
cat > ~/stock_analysis/db_stats.py << 'EOF'
#!/usr/bin/env python3
from database_config import DatabaseManager

def analyze_data():
    db = DatabaseManager()
    if not db.connect():
        return
    
    try:
        print("=== 📈 주식 데이터 분석 ===")
        
        # 시장별 종목 수
        market_stats = db.fetch_all("""
            SELECT market, COUNT(*) as count 
            FROM stocks 
            GROUP BY market 
            ORDER BY count DESC
        """)
        
        print("\n🏢 시장별 종목 수:")
        for stat in market_stats:
            print(f"  {stat['market']}: {stat['count']}개")
        
        # 데이터 수집 현황
        data_stats = db.fetch_one("""
            SELECT 
                COUNT(DISTINCT stock_id) as stocks_with_data,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                COUNT(*) as total_records
            FROM daily_stock_data
        """)
        
        if data_stats:
            print(f"\n📊 일봉 데이터 현황:")
            print(f"  데이터 보유 종목: {data_stats['stocks_with_data']}개")
            print(f"  최초 데이터: {data_stats['earliest_date']}")
            print(f"  최신 데이터: {data_stats['latest_date']}")
            print(f"  총 레코드: {data_stats['total_records']:,}개")
        
    except Exception as e:
        print(f"❌ 분석 중 오류: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    analyze_data()
EOF

python ~/stock_analysis/db_stats.py
```

---

## 🚨 **트러블슈팅**

### ❌ **직접 MySQL 접속이 안 되는 경우**

#### 현재 상황
- MySQL 8.0에서 root 사용자가 특별한 인증 방식 사용
- 보안상 외부 접속 차단됨
- **해결책**: Python 스크립트를 통한 접속 사용

#### 대안 방법
1. **Python DatabaseManager 클래스 사용** (권장)
2. **웹 인터페이스 활용**
3. **애플리케이션 로그 모니터링**

### 🔧 **MySQL 서비스 문제**

#### 서비스 재시작
```bash
# MySQL 서비스 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "systemctl status mysql --no-pager"

# 필요시 재시작 (주의: 애플리케이션에 영향)
# ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "sudo systemctl restart mysql"
```

#### 메모리 사용량 모니터링
```bash
# MySQL 메모리 사용량 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "ps aux | grep mysql | grep -v grep"
```

---

## 📋 **일상적인 DB 관리 명령어**

### ⚡ **빠른 상태 확인**
```bash
# 종합 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && source venv/bin/activate && python db_query.py && echo '=== 웹 서비스 상태 ===' && curl -s -o /dev/null -w 'HTTP Status: %{http_code}\n' http://localhost:5000"

# 데이터베이스 통계
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && source venv/bin/activate && python db_stats.py"
```

### 📊 **정기 점검 스크립트**
```bash
# 매일 실행할 점검 스크립트
cat > ~/stock_analysis/daily_check.py << 'EOF'
#!/usr/bin/env python3
from database_config import DatabaseManager
from datetime import datetime, timedelta

def daily_check():
    print(f"=== 📅 일일 점검 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
    db = DatabaseManager()
    if not db.connect():
        print("❌ 데이터베이스 연결 실패")
        return
    
    try:
        # 최근 데이터 업데이트 확인
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        recent_data = db.fetch_one(f"""
            SELECT COUNT(*) as count 
            FROM daily_stock_data 
            WHERE date >= '{yesterday}'
        """)
        
        print(f"📊 최근 업데이트 데이터: {recent_data['count']}건")
        
        # 시스템 상태
        total_stocks = db.fetch_one("SELECT COUNT(*) as count FROM stocks")
        print(f"📈 총 등록 종목: {total_stocks['count']}개")
        
        print("✅ 일일 점검 완료")
        
    except Exception as e:
        print(f"❌ 점검 중 오류: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    daily_check()
EOF

# 실행 권한 부여
chmod +x ~/stock_analysis/daily_check.py
```

---

## 🎯 **요약**

### ✅ **현재 상황**
- **웹 애플리케이션**: 정상 작동 중
- **데이터베이스**: MySQL 8.0 정상 운영
- **접속 방법**: Python 스크립트를 통한 간접 접속

### 🛠️ **권장 사용 방법**
1. **일상 관리**: Python 스크립트 (`db_query.py`, `db_stats.py`)
2. **데이터 확인**: 웹 인터페이스 (http://211.188.61.165:5000)
3. **모니터링**: 애플리케이션 로그 및 시스템 로그

### 🔐 **보안 상태**
- **외부 접속 차단**: ✅ 올바른 보안 설정
- **애플리케이션 접속**: ✅ 정상 작동
- **데이터 보호**: ✅ 적절한 권한 관리

**🎯 이 가이드를 통해 라이브 서버의 MySQL을 안전하고 효율적으로 관리하세요!**
