#!/bin/bash

# 🔄 1GB 스왑 파일 생성 스크립트
# 메모리 부족 문제 해결을 위한 필수 설정

echo "🔄 스왑 파일 생성 시작..."

# 서버 접속 정보
SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

echo "📊 현재 메모리 상태:"
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "free -h"

echo ""
echo "🔄 1GB 스왑 파일 생성 중..."

ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    # 1GB 스왑 파일 생성
    sudo fallocate -l 1G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
    
    # 권한 설정
    sudo chmod 600 /swapfile
    
    # 스왑 파일로 설정
    sudo mkswap /swapfile
    
    # 스왑 활성화
    sudo swapon /swapfile
    
    # 부팅 시 자동 마운트 설정
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    
    # 스왑 사용률 설정 (메모리 사용률 60%에서 스왑 시작)
    echo 'vm.swappiness=60' | sudo tee -a /etc/sysctl.conf
    
    echo '✅ 스왑 파일 생성 완료!'
    echo '📊 새로운 메모리 상태:'
    free -h
"

echo "🎉 스왑 파일 설정 완료!"
echo "💡 이제 메모리 부족 시 1GB 추가 공간 사용 가능"
