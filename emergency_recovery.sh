#!/bin/bash

# 🚑 서버 다운 후 긴급 복구 스크립트
# 서버 재시작 후 즉시 실행

echo "🚑 긴급 서버 복구 시작..."

# 서버 접속 정보
SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

echo "🔍 서버 상태 확인 중..."

# 서버 접속 가능할 때까지 대기
for i in {1..10}; do
    echo "서버 접속 시도 $i/10..."
    
    if ssh -o ConnectTimeout=5 -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "echo 'SSH 연결 성공'" 2>/dev/null; then
        echo "✅ 서버 접속 성공!"
        break
    else
        echo "❌ 서버 접속 실패, 10초 후 재시도..."
        sleep 10
    fi
    
    if [ $i -eq 10 ]; then
        echo "🚨 서버 접속 불가능! 수동으로 확인 필요"
        exit 1
    fi
done

echo "📊 서버 복구 상태 확인..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    echo '=== 서버 부팅 정보 ==='
    uptime
    echo ''
    echo '=== 메모리 상태 ==='  
    free -h
    echo ''
    echo '=== 디스크 상태 ==='
    df -h | head -5
    echo ''
    echo '=== 스왑 파일 상태 ==='
    swapon --show
"

echo "🚀 애플리케이션 긴급 시작..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    cd /home/ubuntu/stock_analysis
    
    # 가상환경 활성화
    source venv/bin/activate
    
    # 극도로 보수적인 설정
    export PYTHONHASHSEED=0
    export PYTHONUNBUFFERED=1
    export PYTHONOPTIMIZE=2
    ulimit -v 250000  # 250MB 극한 제한
    
    # 기존 프로세스 정리
    pkill -f 'python.*app.py' || echo '기존 프로세스 없음'
    
    # 애플리케이션 시작
    nohup python app.py > app.log 2>&1 &
    
    sleep 3
    
    # 결과 확인
    if pgrep -f 'python.*app.py' > /dev/null; then
        echo '✅ 긴급 복구 성공!'
        echo '🌐 웹서버: http://211.188.61.165:5000'
        
        # 프로세스 정보
        ps aux | grep 'python.*app.py' | grep -v grep
    else
        echo '❌ 긴급 복구 실패!'
        tail -20 app.log
    fi
"

echo "🎯 복구 완료!"
echo "📝 다음 확인사항:"
echo "1. 웹브라우저에서 http://211.188.61.165:5000 접속"
echo "2. Test-NetConnection 211.188.61.165 -Port 5000 실행"
