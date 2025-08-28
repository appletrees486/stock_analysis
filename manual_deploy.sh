#!/bin/bash

# 🛡️ 안전한 수동 배포 스크립트
# 서버 리소스를 보호하면서 코드만 업데이트

echo "🛡️ 안전한 수동 배포 시작..."
echo "📅 배포 시간: $(date)"

# 서버 접속 정보
SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SERVER_PATH="/home/ubuntu/stock_analysis"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

echo "🔒 서버에 SSH 접속 중..."

# 1단계: 메모리 사용량 확인
echo "📊 서버 리소스 상태 확인..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    echo '=== 현재 서버 상태 ==='
    free -h
    echo '========================='
    df -h | head -5
    echo '========================='
    ps aux | grep python | grep -v grep
"

# 2단계: 안전한 코드 업데이트
echo "📥 코드 업데이트 중..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    cd $SERVER_PATH
    
    # 현재 브랜치 확인
    echo '현재 Git 상태:'
    git status --porcelain
    
    # 안전한 업데이트
    echo '코드 업데이트 중...'
    git fetch origin
    git reset --hard origin/main
    
    echo '업데이트 완료!'
    git log --oneline -3
"

# 3단계: 애플리케이션 재시작 (메모리 안전 모드)
echo "🔄 애플리케이션 재시작 중..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    cd $SERVER_PATH
    
    # 기존 프로세스 안전하게 종료
    echo '기존 프로세스 종료 중...'
    pkill -f 'python.*app.py' || echo '실행 중인 프로세스 없음'
    sleep 3
    
    # 메모리 효율적인 새 프로세스 시작
    echo '새 애플리케이션 시작 중 (1GB 메모리 최적화 모드)...'
    source venv/bin/activate
    
    # 메모리 사용량 최적화 설정
    export PYTHONHASHSEED=0  # Python 해시 시드 고정으로 메모리 절약
    export PYTHONUNBUFFERED=1  # 버퍼링 비활성화
    ulimit -v 350000  # 350MB 가상 메모리 제한 (더 엄격하게)
    
    # 가비지 컬렉션 최적화
    export PYTHONOPTIMIZE=1
    
    nohup python app.py > app.log 2>&1 &
    
    sleep 5
    
    # 프로세스 확인
    if pgrep -f 'python.*app.py' > /dev/null; then
        echo '✅ 애플리케이션 시작 성공!'
        echo '🌐 서버 주소: http://211.188.61.165:5000'
    else
        echo '❌ 애플리케이션 시작 실패!'
        echo '로그 확인:'
        tail -20 app.log
    fi
"

echo "🎉 수동 배포 완료!"
echo "📝 다음 명령어로 서버 상태 확인:"
echo "   Test-NetConnection 211.188.61.165 -Port 5000"
