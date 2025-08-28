# 🚀 Stock Analysis 최종 배포 시스템 가이드

## 📊 현재 배포 시스템 상태

### ✅ 안정적인 배포 시스템
- **배포 방식**: 수동 코드 동기화 (Manual Code Sync)
- **서버 환경**: Ubuntu 20.04, 1GB RAM, 무료 서버
- **안정성**: 서버 다운 위험 없음 ✅
- **효율성**: 패키지 설치 없이 코드만 동기화

### ❌ 비활성화된 시스템
- **GitHub Actions CI/CD**: 서버 메모리 부족으로 완전 비활성화
- **자동 배포**: 서버 다운 위험으로 사용 불가

---

## 🎯 **권장 배포 방법: 안전한 수동 배포**

### 1️⃣ 기본 배포 명령어

```bash
# 1. 로컬에서 변경사항 커밋 및 푸시
git add .
git commit -m "변경사항 설명"
git push origin main

# 2. 서버에 안전하게 배포
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull origin main && pkill -f 'python.*app.py' || echo 'No process' && sleep 3 && source venv/bin/activate && export PYTHONHASHSEED=0 && export PYTHONOPTIMIZE=1 && ulimit -v 350000 && (nohup python app.py > app.log 2>&1 &) && sleep 3 && echo 'Deployment completed successfully'"
```

### 2️⃣ 단계별 배포 (안전한 방법)

```bash
# 1단계: 코드 업데이트만
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && git pull origin main"

# 2단계: 애플리케이션 재시작
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && pkill -f 'python.*app.py' || echo 'No process' && sleep 3 && source venv/bin/activate && export PYTHONHASHSEED=0 && export PYTHONOPTIMIZE=1 && ulimit -v 350000 && (nohup python app.py > app.log 2>&1 &) && sleep 3 && echo 'Application restarted'"
```

### 3️⃣ 배포 후 확인

```bash
# PowerShell에서 연결 테스트
Test-NetConnection 211.188.61.165 -Port 5000

# 웹브라우저에서 확인
# http://211.188.61.165:5000
```

---

## 🛠️ **배포 스크립트 활용**

### 📁 사용 가능한 스크립트들

1. **`code_only_sync.sh`** - 코드만 동기화 (가장 안전)
2. **`emergency_recovery.sh`** - 서버 크래시 시 긴급 복구
3. **`manual_deploy.sh`** - 수동 배포 (메모리 최적화 포함)
4. **`server_monitor.sh`** - 서버 리소스 모니터링

### 🚨 긴급 상황 대응

서버가 다운되었을 때:

```bash
# 1. 서버 재시작 후 즉시 실행
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && chmod +x emergency_recovery.sh && ./emergency_recovery.sh"
```

---

## 📈 **메모리 최적화 설정**

### 🔧 현재 적용된 최적화

```bash
# Python 메모리 최적화 환경변수
export PYTHONHASHSEED=0      # 해시 랜덤화 비활성화
export PYTHONOPTIMIZE=1      # 바이트코드 최적화
export PYTHONUNBUFFERED=1    # 출력 버퍼링 비활성화

# 가상 메모리 제한 (350MB)
ulimit -v 350000

# 백그라운드 실행
nohup python app.py > app.log 2>&1 &
```

### 💾 스왑 파일 (1GB 설정됨)

```bash
# 스왑 상태 확인
free -h

# 스왑 파일 정보
sudo swapon --show
```

---

## 🚫 **사용하지 않는 시스템들**

### GitHub Actions CI/CD
- **파일**: `.github/workflows/deploy.yml`
- **상태**: `if: false` - 완전 비활성화
- **이유**: 서버 메모리 부족으로 배포 중 서버 다운 발생

### 대안 시스템들 (구현되어 있으나 미사용)
- **Git Hooks**: `setup_git_hook_deploy.sh`
- **Webhook 서버**: `webhook_deploy_server.py`
- **하이브리드 배포**: `hybrid_deploy_system.yml`

---

## 📋 **배포 체크리스트**

### 배포 전 확인사항
- [ ] 로컬 테스트 완료
- [ ] Git 커밋 및 푸시 완료
- [ ] 서버 상태 정상 (웹사이트 접속 가능)

### 배포 실행
- [ ] 안전한 수동 배포 명령어 실행
- [ ] 애플리케이션 재시작 확인

### 배포 후 확인
- [ ] 웹사이트 접속 테스트 (http://211.188.61.165:5000)
- [ ] 주요 기능 동작 확인
- [ ] 서버 로그 확인 (필요시)

---

## 🔧 **트러블슈팅**

### 일반적인 문제들

#### 1. 애플리케이션이 시작되지 않음
```bash
# 프로세스 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "ps aux | grep python"

# 로그 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "cd ~/stock_analysis && tail -20 app.log"
```

#### 2. 포트 5000 연결 실패
```bash
# 포트 사용 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "netstat -tlnp | grep 5000"
```

#### 3. 메모리 부족
```bash
# 메모리 상태 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "free -h"

# 스왑 활성화 확인
ssh -i C:\Users\jdari\.ssh\master-key.pem ubuntu@211.188.61.165 "sudo swapon --show"
```

---

## 📞 **지원 및 연락처**

- **프로젝트**: Stock Analysis System
- **서버**: 211.188.61.165:5000
- **배포 방식**: Manual Code Sync
- **문서 작성일**: 2025-08-28

---

## 🎯 **요약**

**✅ 현재 시스템**: 안전하고 안정적인 수동 배포
**❌ 비활성화**: GitHub Actions CI/CD (메모리 부족)
**🚀 권장**: 코드 변경 시 수동 배포 명령어 사용
**🛡️ 안전성**: 서버 다운 위험 없음

이 가이드를 따라 안전하게 배포하세요! 🎉
