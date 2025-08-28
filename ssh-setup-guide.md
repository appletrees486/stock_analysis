# 🔑 SSH 키 설정 완전 가이드

## 1. 로컬에서 SSH 키 생성

```bash
# SSH 키 페어 생성 (Windows Git Bash, Linux, macOS)
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy-key"

# 저장 위치 묻는 질문에 엔터 (기본 경로 사용)
# Enter file in which to save the key (/c/Users/username/.ssh/id_rsa): [엔터]

# 비밀번호 묻는 질문에 엔터 (비밀번호 없이 사용)
# Enter passphrase (empty for no passphrase): [엔터]
# Enter same passphrase again: [엔터]
```

## 2. 생성된 키 확인

```bash
# SSH 키 디렉토리로 이동
cd ~/.ssh

# 생성된 파일 확인
ls -la
# 결과: id_rsa (개인키), id_rsa.pub (공개키)

# 공개키 내용 확인 (서버에 등록할 키)
cat id_rsa.pub
# 결과 예시: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAC... github-actions-deploy-key

# 개인키 내용 확인 (GitHub Secrets에 등록할 키)
cat id_rsa
# 결과 예시:
# -----BEGIN RSA PRIVATE KEY-----
# MIIEpAIBAAKCAQEA...
# ...여러 줄...
# -----END RSA PRIVATE KEY-----
```

## 3. 서버에 공개키 등록

```bash
# 서버에 SSH 접속 (기존 방법으로)
ssh username@211.188.61.165

# .ssh 디렉토리 생성 (없는 경우)
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# authorized_keys 파일에 공개키 추가
# 방법 1: 직접 편집
nano ~/.ssh/authorized_keys
# 위에서 복사한 공개키 내용을 붙여넣기 (ssh-rsa AAAAB3... 전체)

# 방법 2: echo 명령어 사용
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAC... github-actions-deploy-key" >> ~/.ssh/authorized_keys

# 권한 설정
chmod 600 ~/.ssh/authorized_keys

# 설정 확인
cat ~/.ssh/authorized_keys
```

## 4. GitHub Secrets에 개인키 등록

### 개인키 복사 방법:

**Windows (Git Bash):**
```bash
# 개인키를 클립보드에 복사
cat ~/.ssh/id_rsa | clip
```

**Linux/macOS:**
```bash
# 개인키를 클립보드에 복사
cat ~/.ssh/id_rsa | pbcopy  # macOS
cat ~/.ssh/id_rsa | xclip -selection clipboard  # Linux
```

**또는 직접 출력해서 복사:**
```bash
cat ~/.ssh/id_rsa
# 출력된 내용을 수동으로 복사 (-----BEGIN부터 -----END까지 전체)
```

### GitHub에서 등록:
1. GitHub → Repository → Settings → Secrets and variables → Actions
2. New repository secret 클릭
3. Name: `PRODUCTION_SSH_KEY`
4. Secret: 복사한 개인키 전체 내용 붙여넣기
5. Add secret 클릭

## 5. SSH 연결 테스트

```bash
# 로컬에서 SSH 키로 서버 접속 테스트
ssh -i ~/.ssh/id_rsa username@211.188.61.165

# 성공하면 비밀번호 없이 바로 접속됨
# 실패하면 권한이나 키 설정 확인 필요
```

## 6. 서버에 프로젝트 디렉토리 준비

```bash
# 서버에 SSH 접속 후
ssh username@211.188.61.165

# 프로젝트 디렉토리 생성
mkdir -p /home/username/stock_analysis
cd /home/username/stock_analysis

# Git 저장소 클론
git clone https://github.com/appletrees486/stock_analysis.git .

# Python 의존성 설치
pip install -r requirements.txt --user

# 실행 권한 부여
chmod +x deploy.sh
```

## 🚨 주의사항

1. **개인키 보안**: 개인키는 절대 공개하거나 공유하지 마세요
2. **공개키만 서버에**: 서버에는 공개키(.pub)만 등록하세요
3. **권한 설정**: SSH 디렉토리와 파일 권한을 정확히 설정하세요
4. **테스트 필수**: 설정 후 반드시 SSH 연결 테스트를 하세요

## ✅ 설정 완료 체크리스트

- [ ] SSH 키 페어 생성 완료
- [ ] 서버에 공개키 등록 완료
- [ ] GitHub Secrets에 개인키 등록 완료
- [ ] SSH 연결 테스트 성공
- [ ] 서버에 프로젝트 디렉토리 준비 완료
- [ ] 모든 GitHub Secrets 등록 완료 (5개)
