# ⚡ 빠른 배포 참조 가이드

## 🚀 **원클릭 배포 명령어**

### 🎯 **완전 자동 배포** (권장)
```bash
git add . && git commit -m "Update" && git push origin main && ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull origin main && pkill -f 'python.*app.py' || echo 'No process' && sleep 3 && source venv/bin/activate && export PYTHONHASHSEED=0 && export PYTHONOPTIMIZE=1 && ulimit -v 350000 && (nohup python app.py > app.log 2>&1 &) && sleep 3 && echo 'Deployment completed successfully'"
```

### 🔄 **코드만 업데이트** (서버 재시작 없음)
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull origin main"
```

### 🔄 **애플리케이션만 재시작**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && pkill -f 'python.*app.py' || echo 'No process' && sleep 3 && source venv/bin/activate && export PYTHONHASHSEED=0 && export PYTHONOPTIMIZE=1 && ulimit -v 350000 && (nohup python app.py > app.log 2>&1 &) && sleep 3 && echo 'Application restarted'"
```

---

## 🛠️ **스크립트 활용**

### 📁 **코드 전용 동기화**
```bash
chmod +x code_only_sync.sh && ./code_only_sync.sh
```

### 🚨 **긴급 복구**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && chmod +x emergency_recovery.sh && ./emergency_recovery.sh"
```

### 📊 **서버 모니터링**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && chmod +x server_monitor.sh && ./server_monitor.sh"
```

---

## 🔍 **상태 확인 명령어**

### 🌐 **웹서버 연결 테스트**
```bash
Test-NetConnection 211.188.61.165 -Port 5000
```

### 📊 **서버 리소스 확인**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "free -h && df -h && uptime"
```

### 🔄 **Git 상태 확인**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git status && git log --oneline -3"
```

### 📝 **애플리케이션 로그**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && tail -20 app.log"
```

### 🔄 **실행 중인 프로세스**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "ps aux | grep python"
```

---

## 🚨 **문제 해결 명령어**

### 🔧 **포트 5000 사용 중인 프로세스 확인**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "netstat -tlnp | grep 5000"
```

### 🔧 **강제 프로세스 종료**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "pkill -9 -f 'python.*app.py'"
```

### 🔧 **메모리 사용량 상세 확인**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "free -m && cat /proc/meminfo | head -10"
```

### 🔧 **디스크 사용량 확인**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "df -h && du -sh ~/stock_analysis"
```

---

## 📋 **체크리스트**

### ✅ **배포 전**
- [ ] 로컬 테스트 완료
- [ ] 변경사항 커밋 완료
- [ ] 웹사이트 현재 상태 확인

### ✅ **배포 중**
- [ ] Git push 성공
- [ ] 서버 코드 동기화 성공
- [ ] 애플리케이션 재시작 성공

### ✅ **배포 후**
- [ ] 웹사이트 접속 테스트 (http://211.188.61.165:5000)
- [ ] 주요 기능 동작 확인
- [ ] 에러 로그 확인

---

## 🎯 **자주 사용하는 조합**

### 📝 **개발 → 배포 전체 플로우**
```bash
# 1. 로컬 변경사항 저장
git add .
git commit -m "기능 개선"
git push origin main

# 2. 서버 배포
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull origin main && pkill -f 'python.*app.py' || echo 'No process' && sleep 3 && source venv/bin/activate && export PYTHONHASHSEED=0 && export PYTHONOPTIMIZE=1 && ulimit -v 350000 && (nohup python app.py > app.log 2>&1 &) && sleep 3 && echo 'Deployment completed'"

# 3. 배포 확인
Test-NetConnection 211.188.61.165 -Port 5000
```

### 🔍 **배포 후 전체 상태 점검**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && echo '=== Git Status ===' && git log --oneline -1 && echo '=== Server Resources ===' && free -h && echo '=== Application Process ===' && ps aux | grep python | grep -v grep && echo '=== Port Status ===' && netstat -tlnp | grep 5000"
```

---

## 🆘 **응급 상황 대응**

### 🚨 **서버 완전 다운 시**
```bash
# 1. 서버 재부팅 후 즉시 실행
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && ./emergency_recovery.sh"

# 2. 웹사이트 복구 확인
Test-NetConnection 211.188.61.165 -Port 5000
```

### 🚨 **애플리케이션만 크래시 시**
```bash
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && source venv/bin/activate && export PYTHONHASHSEED=0 && export PYTHONOPTIMIZE=1 && ulimit -v 350000 && (nohup python app.py > app.log 2>&1 &) && sleep 3 && echo 'Application recovered'"
```

---

## 📱 **모바일/간단 접근용**

### 📲 **최소 명령어 (복사해서 사용)**
```bash
# 빠른 배포
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull && pkill -f python && sleep 2 && source venv/bin/activate && nohup python app.py > app.log 2>&1 &"

# 상태 확인
Test-NetConnection 211.188.61.165 -Port 5000
```

---

## 💡 **팁과 트릭**

### 🔧 **PowerShell 별칭 설정** (선택사항)
```powershell
# PowerShell 프로필에 추가
function Deploy-StockApp {
    ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull origin main && pkill -f 'python.*app.py' || echo 'No process' && sleep 3 && source venv/bin/activate && export PYTHONHASHSEED=0 && export PYTHONOPTIMIZE=1 && ulimit -v 350000 && (nohup python app.py > app.log 2>&1 &) && sleep 3 && echo 'Deployment completed'"
}

function Test-StockApp {
    Test-NetConnection 211.188.61.165 -Port 5000
}

# 사용법
Deploy-StockApp  # 배포
Test-StockApp    # 테스트
```

### 📊 **배포 시간 측정**
```bash
$start = Get-Date; Deploy-StockApp; $end = Get-Date; Write-Host "배포 완료 시간: $($end - $start)"
```

---

## 🎯 **요약**

**가장 많이 사용할 명령어:**
1. **완전 배포**: 위의 "원클릭 배포" 명령어
2. **상태 확인**: `Test-NetConnection 211.188.61.165 -Port 5000`
3. **긴급 복구**: `./emergency_recovery.sh`

**웹사이트**: http://211.188.61.165:5000

이 가이드를 북마크해서 빠르게 참조하세요! ⚡
