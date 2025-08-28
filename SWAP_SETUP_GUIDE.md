# 🔄 스왑 파일 설정 가이드

## 📋 1GB 메모리 서버를 위한 필수 스왑 파일 생성

### 🚨 **중요**: 서버 관리자가 직접 실행해야 합니다

다음 명령어들을 서버에서 **직접 실행**해주세요:

```bash
# 1. 서버에 SSH 접속
ssh ubuntu@211.188.61.165

# 2. 1GB 스왑 파일 생성
sudo fallocate -l 1G /swapfile

# 3. 권한 설정
sudo chmod 600 /swapfile

# 4. 스왑 파일로 설정
sudo mkswap /swapfile

# 5. 스왑 활성화
sudo swapon /swapfile

# 6. 부팅 시 자동 마운트 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 7. 스왑 사용률 설정 (메모리 60%에서 스왑 시작)
echo 'vm.swappiness=60' | sudo tee -a /etc/sysctl.conf

# 8. 설정 확인
free -h
```

### ✅ **예상 결과**
```
              total        used        free      shared  buff/cache   available
Mem:           957Mi       532Mi       181Mi       0.0Ki       243Mi       282Mi
Swap:          1.0Gi          0B       1.0Gi
```

### 🎯 **효과**
- 메모리 부족 시 1GB 추가 공간 사용 가능
- 서버 다운 위험 대폭 감소
- 패키지 설치 시 안정성 향상

## 📊 **스왑 파일 생성 후 할 일**

1. **서버 재시작 없이 즉시 적용됨**
2. **메모리 사용량 모니터링**: `free -h` 명령어로 확인
3. **CI/CD 재활성화 가능**: 스왑 파일로 안정성 확보

## ⚠️ **주의사항**

- 스왑 파일은 물리 메모리보다 느림 (하지만 서버 다운보다 훨씬 나음)
- 디스크 공간 1GB 추가 사용
- 처음 스왑 사용 시 약간의 성능 저하 가능 (정상)
