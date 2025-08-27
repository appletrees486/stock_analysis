# 🚀 CI/CD 배포 설정 가이드

이 문서는 GitHub Actions를 사용한 자동 배포 설정 방법을 설명합니다.

## 📋 필수 설정

### 1. GitHub Secrets 설정

GitHub 저장소의 Settings > Secrets and variables > Actions에서 다음 secrets을 설정해야 합니다:

```
PRODUCTION_HOST=211.188.61.165
PRODUCTION_USER=your_username
PRODUCTION_SSH_KEY=your_private_ssh_key
PRODUCTION_PORT=22
PRODUCTION_PATH=/path/to/stock_analysis
```

### 2. SSH 키 생성 및 설정

#### 로컬에서 SSH 키 생성
```bash
# SSH 키 페어 생성
ssh-keygen -t rsa -b 4096 -C "deploy-key-for-stock-analysis"

# 생성된 키 확인
ls ~/.ssh/
```

#### 서버에 공개키 설정
```bash
# 서버에 SSH 접속
ssh user@211.188.61.165

# .ssh 디렉토리 생성 (없는 경우)
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 공개키를 authorized_keys에 추가
echo "your_public_key_content" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

#### GitHub Secrets에 개인키 등록
1. GitHub 저장소 > Settings > Secrets and variables > Actions
2. New repository secret 클릭
3. Name: `PRODUCTION_SSH_KEY`
4. Secret: 개인키 내용 전체 복사 (`cat ~/.ssh/id_rsa`)

### 3. 서버 환경 설정

#### 프로젝트 디렉토리 설정
```bash
# 서버에 SSH 접속
ssh user@211.188.61.165

# 프로젝트 디렉토리 생성
mkdir -p /home/user/stock_analysis
cd /home/user/stock_analysis

# Git 저장소 클론
git clone https://github.com/your-username/stock_analysis.git .

# Python 의존성 설치
pip install -r requirements.txt --user
```

#### 방화벽 설정 (필요한 경우)
```bash
# 포트 5000 열기
sudo ufw allow 5000
# 또는
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

## 🔄 배포 프로세스

### 자동 배포 (GitHub Actions)
1. `main` 브랜치에 코드 푸시
2. GitHub Actions가 자동으로 실행
3. 테스트 실행
4. 서버에 자동 배포

### 수동 배포 (서버에서 직접)
```bash
# 서버에 SSH 접속
ssh user@211.188.61.165

# 프로젝트 디렉토리로 이동
cd /path/to/stock_analysis

# 배포 스크립트 실행
./deploy.sh
```

## 📊 배포 상태 확인

### 애플리케이션 상태 확인
```bash
# 프로세스 확인
pgrep -f "python.*app.py"

# 웹서버 응답 확인
curl http://localhost:5000

# 로그 확인
tail -f app.log
```

### 포트 확인
```bash
# 포트 5000 사용 확인
netstat -tlnp | grep :5000
# 또는
ss -tlnp | grep :5000
```

## 🛠️ 문제 해결

### 배포 실패 시
1. GitHub Actions 로그 확인
2. 서버 로그 확인: `tail -20 app.log`
3. SSH 연결 확인: `ssh user@211.188.61.165`
4. 방화벽 설정 확인

### 애플리케이션 재시작
```bash
# 기존 프로세스 종료
pkill -f "python.*app.py"

# 새 프로세스 시작
nohup python app.py > app.log 2>&1 &
```

### 수동 롤백
```bash
# 이전 커밋으로 롤백
git log --oneline -10  # 최근 10개 커밋 확인
git reset --hard <commit_hash>

# 애플리케이션 재시작
./deploy.sh
```

## 🔐 보안 고려사항

1. **SSH 키 관리**: 개인키는 절대 공개하지 마세요
2. **방화벽 설정**: 필요한 포트만 열어두세요
3. **사용자 권한**: 최소 권한 원칙을 적용하세요
4. **정기 업데이트**: 시스템 및 의존성 정기 업데이트

## 📝 배포 체크리스트

- [ ] GitHub Secrets 설정 완료
- [ ] SSH 키 생성 및 서버 등록 완료
- [ ] 서버에 프로젝트 디렉토리 생성 완료
- [ ] 방화벽 설정 완료 (포트 5000)
- [ ] 첫 번째 수동 배포 테스트 완료
- [ ] GitHub Actions 자동 배포 테스트 완료
- [ ] 웹서버 접속 확인 완료 (http://211.188.61.165:5000)

## 🌐 접속 정보

- **개발 서버**: http://localhost:5000
- **운영 서버**: http://211.188.61.165:5000
- **GitHub 저장소**: https://github.com/your-username/stock_analysis
