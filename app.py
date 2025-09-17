#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 주식 차트 분석 웹 서버
단일 분석과 대량 분석을 지원하는 Flask 기반 웹 애플리케이션
"""

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask 앱 초기화
app = Flask(__name__)
CORS(app)

# 설정
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 제한
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'

# 업로드 폴더 생성
os.makedirs('uploads/charts', exist_ok=True)
os.makedirs('uploads/stock_lists', exist_ok=True)
os.makedirs('results', exist_ok=True)

# API 블루프린트 등록
try:
    from api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    logger.info("API 블루프린트 등록 완료")
except ImportError as e:
    logger.error(f"API 블루프린트 등록 실패: {e}")

# 프롬프트 관리 블루프린트 등록
try:
    from api.prompt_routes import prompt_bp
    app.register_blueprint(prompt_bp)
    logger.info("프롬프트 관리 블루프린트 등록 완료")
except ImportError as e:
    logger.error(f"프롬프트 관리 블루프린트 등록 실패: {e}")

# 일일 시세 수집 블루프린트 등록
try:
    from api.daily_collection_routes import daily_collection_bp
    app.register_blueprint(daily_collection_bp)
    logger.info("일일 시세 수집 블루프린트 등록 완료")
except ImportError as e:
    logger.error(f"일일 시세 수집 블루프린트 등록 실패: {e}")

# 배치 스케줄 관리 블루프린트 등록
try:
    from api.batch_schedule_routes import batch_schedule_bp
    app.register_blueprint(batch_schedule_bp)
    logger.info("배치 스케줄 관리 블루프린트 등록 완료")
except ImportError as e:
    logger.error(f"배치 스케줄 관리 블루프린트 등록 실패: {e}")

@app.route('/')
def index():
    """메인 페이지 - 분석 타입 선택"""
    logger.info("메인 페이지 접속")
    return render_template('index.html')

@app.route('/single')
def single_analysis():
    """단일 분석 페이지"""
    logger.info("단일 분석 페이지 접속")
    return render_template('single_analysis.html')

@app.route('/batch')
def batch_analysis():
    """대량 분석 페이지"""
    logger.info("대량 분석 페이지 접속")
    return render_template('batch_analysis.html')

@app.route('/multi-batch')
def multi_batch_analysis():
    """다중 대량 분석 페이지"""
    logger.info("다중 대량 분석 페이지 접속")
    return render_template('multi_batch_analysis.html')

@app.route('/prompts')
def prompt_management():
    """프롬프트 관리 페이지"""
    logger.info("프롬프트 관리 페이지 접속")
    return render_template('prompt_management.html')

@app.route('/volume-ranking')
def volume_ranking():
    """거래량 랭킹 페이지"""
    logger.info("거래량 랭킹 페이지 접속")
    return render_template('volume_ranking.html')

@app.route('/daily-collection')
def daily_collection():
    """일일 시세 수집 페이지"""
    logger.info("일일 시세 수집 페이지 접속")
    return render_template('daily_collection.html')

@app.route('/batch-schedule')
def batch_schedule():
    """배치 스케줄 관리 페이지"""
    logger.info("배치 스케줄 관리 페이지 접속")
    return render_template('batch_schedule.html')

@app.route('/health')
def health_check():
    """서버 상태 확인"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({'error': '페이지를 찾을 수 없습니다'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    logger.error(f"서버 내부 오류: {error}")
    return jsonify({'error': '서버 내부 오류가 발생했습니다'}), 500

@app.errorhandler(413)
def too_large(error):
    """파일 크기 초과 에러 핸들러"""
    return jsonify({'error': '파일 크기가 너무 큽니다 (최대 16MB)'}), 413

# 배치 스케줄러 상태 확인 (자동 시작은 별도 서비스로 처리)
try:
    from batch_scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler.is_running:
        logger.info("✅ 배치 스케줄러가 이미 실행 중입니다")
    else:
        logger.warning("⚠️ 배치 스케줄러가 실행되지 않았습니다")
        logger.info("💡 'python start_scheduler_service.py' 명령으로 스케줄러를 시작하세요")
except ImportError as e:
    logger.warning(f"배치 스케줄러를 사용할 수 없습니다: {e}")
except Exception as e:
    logger.error(f"배치 스케줄러 확인 중 오류: {e}")

def run_with_scheduler(debug=False):
    """스케줄러와 함께 Flask 앱 실행"""
    import threading
    import time
    
    def start_scheduler_thread():
        """스케줄러를 별도 스레드에서 실행"""
        try:
            from batch_scheduler import start_scheduler, get_scheduler
            
            logger.info("🚀 스케줄러 스레드 시작")
            
            if start_scheduler():
                scheduler = get_scheduler()
                logger.info("✅ 스케줄러 시작 완료")
                
                # 등록된 작업 확인
                jobs = scheduler.get_scheduled_jobs()
                logger.info(f"📅 등록된 스케줄 작업: {len(jobs)}개")
                
                for job in jobs:
                    logger.info(f"  - {job.get('name', 'Unknown')}: {job.get('next_run', 'None')}")
                
                # 스케줄러 유지
                while scheduler.is_running:
                    time.sleep(10)
                    
            else:
                logger.error("❌ 스케줄러 시작 실패")
                
        except Exception as e:
            logger.error(f"스케줄러 스레드 실행 중 오류: {e}")
    
    # Debug 모드가 아닐 때만 스케줄러 시작
    if not debug:
        # 스케줄러 스레드 시작
        scheduler_thread = threading.Thread(target=start_scheduler_thread, daemon=True)
        scheduler_thread.start()
        logger.info("✅ 스케줄러 스레드 시작됨")
        
        # 스케줄러가 시작될 시간을 줌
        time.sleep(2)
        
        logger.info("📡 스케줄러와 웹 서버가 동시에 실행됩니다")
    else:
        logger.info("🔧 Debug 모드 - 스케줄러는 별도로 시작하세요")
    
    # Flask 앱 실행
    logger.info("AI 주식 차트 분석 웹 서버 시작")
    logger.info("서버 주소: http://localhost:5000")
    
    app.run(
        debug=debug, 
        host='0.0.0.0', 
        port=5000, 
        threaded=True, 
        use_reloader=debug  # Debug 모드일 때만 reloader 사용
    )

if __name__ == '__main__':
    import sys
    
    # 명령행 인자로 debug 모드 제어
    debug_mode = '--debug' in sys.argv or '-d' in sys.argv
    
    if debug_mode:
        logger.info("🔧 Debug 모드로 실행")
        run_with_scheduler(debug=True)
    else:
        logger.info("🚀 운영 모드로 실행 (스케줄러 포함)")
        run_with_scheduler(debug=False) 