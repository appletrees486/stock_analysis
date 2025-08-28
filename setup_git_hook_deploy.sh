#!/bin/bash

# 🔗 Git Hook 기반 자동 배포 시스템 설정
# GitHub Actions 없이 서버에서 직접 Git 변경사항 감지

echo "🔗 Git Hook 기반 자동 배포 시스템 설정..."

SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

echo "📝 서버에 Git Hook 설정 중..."

ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    cd ~/stock_analysis
    
    # Git Hook 디렉토리 생성
    mkdir -p .git/hooks
    
    # post-merge hook 생성 (git pull 후 자동 실행)
    cat > .git/hooks/post-merge << 'EOF'
#!/bin/bash

echo '🔄 Git Hook 자동 배포 시작...'
echo '📅 시간: \$(date)'

# 로그 파일 설정
DEPLOY_LOG=\"~/stock_analysis/deploy_hook.log\"

{
    echo \"=== Git Hook 자동 배포 시작 ===\" 
    echo \"시간: \$(date)\"
    
    # 변경된 파일 확인
    echo \"변경된 파일:\"
    git diff --name-only HEAD@{1} HEAD
    
    # 애플리케이션 재시작 (패키지 설치 없음)
    echo \"애플리케이션 재시작 중...\"
    pkill -f 'python.*app.py' || echo '실행 중인 프로세스 없음'
    sleep 3
    
    # 가상환경에서 재시작
    source venv/bin/activate
    export PYTHONHASHSEED=0
    export PYTHONOPTIMIZE=1
    ulimit -v 350000
    
    nohup python app.py > app.log 2>&1 &
    
    sleep 3
    
    if pgrep -f 'python.*app.py' > /dev/null; then
        echo \"✅ Git Hook 자동 배포 성공!\"
    else
        echo \"❌ Git Hook 자동 배포 실패!\"
        tail -10 app.log
    fi
    
    echo \"=== Git Hook 자동 배포 완료 ===\" 
    echo \"\"
    
} >> \"\$DEPLOY_LOG\" 2>&1

echo '📋 배포 로그는 deploy_hook.log에서 확인 가능'
EOF

    # Hook 실행 권한 부여
    chmod +x .git/hooks/post-merge
    
    echo '✅ Git Hook 설정 완료!'
    echo '📋 이제 git pull 실행 시 자동으로 애플리케이션 재시작됩니다.'
"

echo "🔄 자동 배포 테스트용 스크립트 생성..."

cat > auto_deploy_via_git.sh << 'EOF'
#!/bin/bash

# Git Hook 기반 자동 배포 실행 스크립트

echo "🔄 Git Hook 기반 자동 배포 실행..."

SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
    cd ~/stock_analysis
    
    echo '현재 Git 상태:'
    git log --oneline -1
    
    echo 'Git에서 최신 변경사항 가져오기...'
    git pull origin main
    
    echo '배포 로그 확인:'
    tail -20 deploy_hook.log 2>/dev/null || echo '아직 배포 로그 없음'
"

echo "✅ Git Hook 기반 자동 배포 완료!"
EOF

chmod +x auto_deploy_via_git.sh

echo "✅ Git Hook 기반 자동 배포 시스템 설정 완료!"
echo ""
echo "📋 사용 방법:"
echo "1. 로컬에서 코드 수정 후 git push"
echo "2. ./auto_deploy_via_git.sh 실행"
echo "3. 서버에서 자동으로 git pull 후 애플리케이션 재시작"
echo ""
echo "🎯 장점:"
echo "- GitHub Actions 불필요"
echo "- 서버 리소스 최소 사용"
echo "- 패키지 설치 없이 코드만 업데이트"
