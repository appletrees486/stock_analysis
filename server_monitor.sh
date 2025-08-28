#!/bin/bash

# 🔍 서버 실시간 모니터링 스크립트
# 위험한 상황을 사전에 감지하고 알림

SERVER_USER="ubuntu"
SERVER_HOST="211.188.61.165"
SSH_KEY="C:/Users/jdari/.ssh/master-key.pem"

echo "🔍 서버 모니터링 시작..."
echo "📅 모니터링 시간: $(date)"

while true; do
    echo "=================================="
    echo "⏰ 체크 시간: $(date '+%H:%M:%S')"
    
    # SSH로 서버 상태 확인
    ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "
        # 메모리 사용률 확인
        MEMORY_USAGE=\$(free | awk '/^Mem:/ {printf \"%.0f\", \$3/\$2 * 100}')
        
        # CPU 사용률 확인 (1초간 평균)
        CPU_USAGE=\$(top -bn1 | grep 'Cpu(s)' | awk '{print \$2}' | cut -d'%' -f1)
        
        # 애플리케이션 프로세스 확인
        APP_PROCESS=\$(pgrep -f 'python.*app.py' | wc -l)
        
        echo \"📊 메모리 사용률: \${MEMORY_USAGE}%\"
        echo \"🔥 CPU 사용률: \${CPU_USAGE}%\"
        echo \"🐍 Python 프로세스: \${APP_PROCESS}개\"
        
        # 위험 상황 감지
        if [ \"\$MEMORY_USAGE\" -gt 80 ]; then
            echo \"🚨 위험: 메모리 사용률 80% 초과!\"
        fi
        
        if [ \"\$APP_PROCESS\" -eq 0 ]; then
            echo \"🚨 경고: 애플리케이션이 실행되지 않고 있습니다!\"
        fi
        
        # 디스크 사용률 확인
        DISK_USAGE=\$(df -h / | awk 'NR==2 {print \$5}' | cut -d'%' -f1)
        echo \"💾 디스크 사용률: \${DISK_USAGE}%\"
        
        if [ \"\$DISK_USAGE\" -gt 90 ]; then
            echo \"🚨 위험: 디스크 사용률 90% 초과!\"
        fi
    " || echo "❌ 서버 접속 실패!"
    
    echo "⏳ 30초 후 다시 확인..."
    sleep 30
done
