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

if __name__ == '__main__':
    logger.info("AI 주식 차트 분석 웹 서버 시작")
    logger.info("서버 주소: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 