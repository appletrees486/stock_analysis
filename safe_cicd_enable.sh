#!/bin/bash

# 🛡️ 스왑 파일 생성 후 안전한 CI/CD 재활성화 스크립트
# 1GB 메모리 + 1GB 스왑으로 총 2GB 환경에서 안전한 배포

echo "🛡️ 안전한 CI/CD 재활성화 준비..."

# 서버 접속 정보
SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

echo "📊 서버 메모리 상태 확인 중..."
SWAP_STATUS=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "free -h | grep Swap | awk '{print \$2}'")

if [ "$SWAP_STATUS" = "0B" ]; then
    echo "🚨 경고: 스왑 파일이 설정되지 않았습니다!"
    echo "📋 먼저 SWAP_SETUP_GUIDE.md를 참고하여 스왑 파일을 생성해주세요."
    echo "⚠️ 스왑 파일 없이는 CI/CD 재활성화를 권장하지 않습니다."
    exit 1
else
    echo "✅ 스왑 파일 확인됨: $SWAP_STATUS"
fi

echo ""
echo "🔧 CI/CD 파이프라인 재활성화 중..."

# GitHub Actions 워크플로우 수정
cat > .github/workflows/deploy.yml << 'EOF'
name: Deploy to Production Server

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python 3.9
      uses: actions/setup-python@v4
      with:
        python-version: 3.9
    
    - name: Install minimal dependencies
      run: |
        python -m pip install --upgrade pip
        pip install flask==2.3.0 requests==2.28.0
    
    - name: Run basic syntax check
      run: |
        python -m py_compile app.py
        echo "Basic syntax check completed"

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    timeout-minutes: 20
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to Production Server (1GB + Swap Optimized)
      uses: appleboy/ssh-action@v1.0.3
      with:
        host: ${{ secrets.PRODUCTION_HOST }}
        username: ${{ secrets.PRODUCTION_USER }}
        key: ${{ secrets.PRODUCTION_SSH_KEY }}
        port: ${{ secrets.PRODUCTION_PORT }}
        script: |
          echo "🛡️ 1GB+스왑 최적화 배포 시작..."
          
          # 메모리 상태 확인
          echo "📊 메모리 상태:"
          free -h
          
          # 프로젝트 디렉토리로 이동
          cd /home/ubuntu/stock_analysis
          
          # Git에서 최신 변경사항 가져오기
          echo "📥 코드 업데이트 중..."
          git fetch origin
          git reset --hard origin/main
          
          # 패키지 설치 (스왑 파일로 안전함)
          echo "📦 필수 패키지만 업데이트..."
          source venv/bin/activate
          pip install --no-cache-dir --prefer-binary flask requests APScheduler
          
          # 기존 프로세스 종료
          echo "🛑 기존 애플리케이션 종료..."
          pkill -f "python.*app.py" || echo "실행 중인 프로세스 없음"
          sleep 5
          
          # 메모리 최적화 모드로 애플리케이션 시작
          echo "🚀 메모리 최적화 모드로 애플리케이션 시작..."
          export PYTHONHASHSEED=0
          export PYTHONUNBUFFERED=1
          export PYTHONOPTIMIZE=1
          ulimit -v 600000  # 600MB 제한 (스왑 있으므로 여유있게)
          
          nohup python app.py > app.log 2>&1 &
          
          sleep 10
          
          # 배포 결과 확인
          if pgrep -f "python.*app.py" > /dev/null; then
            echo "✅ 배포 성공! 메모리 최적화 모드로 실행 중"
            echo "📊 최종 메모리 상태:"
            free -h
          else
            echo "❌ 배포 실패!"
            tail -20 app.log
            exit 1
          fi

    - name: Notify Deployment Status
      if: always()
      run: |
        if [ "${{ job.status }}" == "success" ]; then
          echo "✅ 1GB+스왑 최적화 배포 성공!"
        else
          echo "❌ 배포 중 오류가 발생했습니다."
        fi
EOF

echo "✅ CI/CD 파이프라인이 1GB+스왑 최적화 모드로 재활성화되었습니다!"
echo "🎯 이제 안전하게 자동 배포가 가능합니다."
echo ""
echo "📋 다음 단계:"
echo "1. git add .github/workflows/deploy.yml"
echo "2. git commit -m '스왑 파일 기반 안전한 CI/CD 재활성화'"
echo "3. git push origin main"
