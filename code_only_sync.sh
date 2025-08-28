#!/bin/bash

# 🔄 코드만 동기화하는 초안전 배포 스크립트
# 패키지 설치 없이 순수하게 코드만 업데이트

echo "🛡️ 코드 전용 동기화 시작..."
echo "⚠️ 패키지 설치 없음 - 서버 안전 최우선"

# 서버 접속 정보
SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SERVER_PATH="/home/ubuntu/stock_analysis"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

echo "📊 배포 전 서버 상태 확인..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    echo '=== 서버 리소스 상태 ==='
    uptime
    free -h
    df -h | head -5
    echo '=========================='
"

echo "📥 코드 동기화 중 (패키지 설치 없음)..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    cd $SERVER_PATH
    
    echo '현재 Git 상태:'
    git log --oneline -1
    
    echo '코드 업데이트 중...'
    git fetch origin --quiet
    git reset --hard origin/main --quiet
    
    echo '업데이트된 코드:'
    git log --oneline -1
    
    echo '✅ 코드 동기화 완료 (패키지 변경 없음)'
"

echo "🔄 애플리케이션 재시작 (메모리 안전 모드)..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    cd $SERVER_PATH
    
    # 기존 프로세스 안전하게 종료
    echo '기존 프로세스 종료 중...'
    pkill -f 'python.*app.py' || echo '실행 중인 프로세스 없음'
    sleep 3
    
    # 메모리 사용량 최소화 모드로 시작
    echo '초절약 모드로 애플리케이션 시작...'
    source venv/bin/activate
    
    # 극도로 보수적인 메모리 설정
    export PYTHONHASHSEED=0
    export PYTHONUNBUFFERED=1  
    export PYTHONOPTIMIZE=2  # 최대 최적화
    ulimit -v 300000  # 300MB 엄격한 제한
    ulimit -n 1024    # 파일 디스크립터 제한
    
    # 애플리케이션 시작
    nohup python app.py > app.log 2>&1 &
    
    sleep 5
    
    # 결과 확인
    if pgrep -f 'python.*app.py' > /dev/null; then
        echo '✅ 애플리케이션 시작 성공 (초절약 모드)'
        echo '📊 최종 시스템 상태:'
        free -h
        echo '🌐 서버: http://211.188.61.165:5000'
    else
        echo '❌ 애플리케이션 시작 실패'
        echo '로그 확인:'
        tail -10 app.log
    fi
"

echo "🎉 코드 전용 동기화 완료!"
echo ""
echo "📋 특징:"
echo "- ✅ 패키지 설치 없음 (서버 다운 위험 제거)"  
echo "- ✅ 코드만 업데이트 (Git 동기화)"
echo "- ✅ 300MB 메모리 제한 (초절약 모드)"
echo "- ✅ 서버 안전성 최우선"
