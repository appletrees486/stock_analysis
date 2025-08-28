#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹훅 기반 자동 배포 서버
GitHub에서 push 이벤트 발생 시 자동으로 배포 실행
"""

from flask import Flask, request, jsonify
import subprocess
import threading
import os
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook_deploy.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# 웹훅 시크릿 (보안을 위해 설정)
WEBHOOK_SECRET = "your_webhook_secret_here"  # GitHub에서 설정한 시크릿과 동일

def deploy_application():
    """애플리케이션 배포 실행"""
    try:
        logging.info("🚀 웹훅 배포 시작...")
        
        # 1. Git에서 최신 코드 가져오기
        logging.info("📥 Git에서 최신 코드 가져오는 중...")
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd="/home/ubuntu/stock_analysis",
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logging.error(f"Git pull 실패: {result.stderr}")
            return False
        
        logging.info(f"Git pull 성공: {result.stdout}")
        
        # 2. 기존 애플리케이션 중지
        logging.info("🛑 기존 애플리케이션 중지 중...")
        subprocess.run(["pkill", "-f", "python.*app.py"], 
                      capture_output=True)
        
        # 3. 잠시 대기
        import time
        time.sleep(3)
        
        # 4. 새 애플리케이션 시작
        logging.info("🚀 새 애플리케이션 시작 중...")
        
        # 환경 변수 설정
        env = os.environ.copy()
        env.update({
            'PYTHONHASHSEED': '0',
            'PYTHONOPTIMIZE': '1',
            'PYTHONUNBUFFERED': '1'
        })
        
        # 메모리 제한 설정
        subprocess.run(["bash", "-c", "ulimit -v 350000"], shell=True)
        
        # 애플리케이션 시작
        with open('/home/ubuntu/stock_analysis/app.log', 'w') as log_file:
            process = subprocess.Popen(
                ["python", "app.py"],
                cwd="/home/ubuntu/stock_analysis",
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env
            )
        
        # 시작 확인
        time.sleep(5)
        
        # 프로세스 확인
        check_result = subprocess.run(
            ["pgrep", "-f", "python.*app.py"],
            capture_output=True
        )
        
        if check_result.returncode == 0:
            logging.info("✅ 웹훅 배포 성공!")
            return True
        else:
            logging.error("❌ 애플리케이션 시작 실패!")
            return False
            
    except Exception as e:
        logging.error(f"배포 중 오류 발생: {str(e)}")
        return False

@app.route('/webhook', methods=['POST'])
def github_webhook():
    """GitHub 웹훅 엔드포인트"""
    try:
        # 웹훅 데이터 확인
        payload = request.json
        
        # push 이벤트만 처리
        if request.headers.get('X-GitHub-Event') != 'push':
            return jsonify({"message": "Not a push event"}), 200
        
        # main 브랜치 push만 처리
        if payload.get('ref') != 'refs/heads/main':
            return jsonify({"message": "Not main branch"}), 200
        
        logging.info(f"📨 웹훅 수신: {payload.get('head_commit', {}).get('message', 'No message')}")
        
        # 백그라운드에서 배포 실행
        def background_deploy():
            success = deploy_application()
            if success:
                logging.info("🎉 웹훅 배포 완료!")
            else:
                logging.error("💥 웹훅 배포 실패!")
        
        thread = threading.Thread(target=background_deploy)
        thread.daemon = True
        thread.start()
        
        return jsonify({"message": "Deployment started"}), 200
        
    except Exception as e:
        logging.error(f"웹훅 처리 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def deployment_status():
    """배포 상태 확인"""
    try:
        # 애플리케이션 실행 상태 확인
        check_result = subprocess.run(
            ["pgrep", "-f", "python.*app.py"],
            capture_output=True
        )
        
        is_running = check_result.returncode == 0
        
        # 최근 Git 커밋 정보
        git_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd="/home/ubuntu/stock_analysis",
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "application_running": is_running,
            "latest_commit": git_result.stdout.strip() if git_result.returncode == 0 else "Unknown",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.info("🌐 웹훅 배포 서버 시작...")
    logging.info("📋 엔드포인트:")
    logging.info("  - POST /webhook : GitHub 웹훅 수신")
    logging.info("  - GET /status   : 배포 상태 확인")
    
    # 포트 8080에서 웹훅 서버 실행 (메인 앱과 분리)
    app.run(host='0.0.0.0', port=8080, debug=False)
