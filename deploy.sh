#!/bin/bash

# 주식 분석 웹 애플리케이션 배포 스크립트
# 사용법: ./deploy.sh

set -e  # 오류 발생 시 스크립트 중단

echo "=========================================="
echo "🚀 주식 분석 웹 애플리케이션 배포 시작"
echo "=========================================="

# 현재 시간 기록
DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo "📅 배포 시작 시간: $DEPLOY_TIME"

# 1. Git에서 최신 변경사항 가져오기
echo ""
echo "📥 Git에서 최신 변경사항 가져오는 중..."
git fetch origin
git reset --hard origin/main
echo "✅ 최신 코드 업데이트 완료"

# 2. Python 의존성 확인 및 업데이트
echo ""
echo "📦 Python 의존성 확인 중..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --user --quiet
    echo "✅ Python 의존성 업데이트 완료"
else
    echo "⚠️ requirements.txt 파일이 없습니다."
fi

# 3. 기존 애플리케이션 프로세스 확인 및 종료
echo ""
echo "🔍 기존 애플리케이션 프로세스 확인 중..."
if pgrep -f "python.*app.py" > /dev/null; then
    echo "🛑 기존 프로세스를 종료하는 중..."
    pkill -f "python.*app.py"
    echo "⏳ 프로세스 종료 대기 중..."
    sleep 5
    
    # 강제 종료가 필요한지 확인
    if pgrep -f "python.*app.py" > /dev/null; then
        echo "🔨 강제 종료 중..."
        pkill -9 -f "python.*app.py"
        sleep 2
    fi
    echo "✅ 기존 프로세스 종료 완료"
else
    echo "ℹ️ 실행 중인 프로세스가 없습니다."
fi

# 4. 데이터베이스 연결 테스트 (선택적)
echo ""
echo "🔗 데이터베이스 연결 테스트..."
if python -c "from database_config import DatabaseManager; db = DatabaseManager(); result = db.connect(); print('✅ 데이터베이스 연결 성공' if result else '❌ 데이터베이스 연결 실패'); db.disconnect()" 2>/dev/null; then
    echo "✅ 데이터베이스 연결 확인 완료"
else
    echo "⚠️ 데이터베이스 연결 테스트 실패 (계속 진행)"
fi

# 5. 로그 파일 백업 (크기가 큰 경우)
echo ""
echo "📋 로그 파일 관리..."
if [ -f "app.log" ] && [ $(stat -f%z "app.log" 2>/dev/null || stat -c%s "app.log" 2>/dev/null || echo 0) -gt 10485760 ]; then
    mv app.log "app_backup_$(date +%Y%m%d_%H%M%S).log"
    echo "✅ 기존 로그 파일 백업 완료"
fi

# 6. 새 애플리케이션 시작
echo ""
echo "🚀 새 애플리케이션 시작 중..."
nohup python app.py > app.log 2>&1 &
APP_PID=$!

echo "⏳ 애플리케이션 시작 대기 중..."
sleep 10

# 7. 애플리케이션 시작 확인
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✅ 애플리케이션이 성공적으로 시작되었습니다!"
    echo "🆔 프로세스 ID: $(pgrep -f 'python.*app.py')"
    echo "🌐 웹서버 주소: http://localhost:5000"
    echo "🌐 외부 접속: http://$(hostname -I | awk '{print $1}'):5000"
    
    # 애플리케이션 상태 확인
    echo ""
    echo "🔍 애플리케이션 상태 확인 중..."
    sleep 5
    if curl -s http://localhost:5000 > /dev/null; then
        echo "✅ 웹서버가 정상적으로 응답하고 있습니다!"
    else
        echo "⚠️ 웹서버 응답 확인 실패 (방화벽 또는 포트 설정 확인 필요)"
    fi
else
    echo "❌ 애플리케이션 시작에 실패했습니다!"
    echo "📋 최근 로그 (마지막 20줄):"
    tail -20 app.log 2>/dev/null || echo "로그 파일을 읽을 수 없습니다."
    exit 1
fi

# 8. 배포 완료 정보
DEPLOY_END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo ""
echo "=========================================="
echo "🎉 배포가 성공적으로 완료되었습니다!"
echo "=========================================="
echo "📅 배포 시작: $DEPLOY_TIME"
echo "📅 배포 완료: $DEPLOY_END_TIME"
echo "🌐 웹서버 주소: http://localhost:5000"
echo "📋 로그 파일: app.log"
echo "🔧 프로세스 관리:"
echo "   - 중지: pkill -f 'python.*app.py'"
echo "   - 상태 확인: pgrep -f 'python.*app.py'"
echo "   - 로그 확인: tail -f app.log"
echo "=========================================="
