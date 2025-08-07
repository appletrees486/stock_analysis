#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 엔드포인트 정의
단일 분석과 대량 분석을 위한 RESTful API
"""

from flask import Blueprint, request, jsonify, send_file, current_app
import os
import time
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
import json

# 로깅 설정
logger = logging.getLogger(__name__)

# 블루프린트 생성
api_bp = Blueprint('api', __name__)

# 허용된 파일 확장자
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_TEXT_EXTENSIONS = {'txt'}

def allowed_image_file(filename):
    """이미지 파일 확장자 확인"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_text_file(filename):
    """텍스트 파일 확장자 확인"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_TEXT_EXTENSIONS

@api_bp.route('/analyze/single', methods=['POST'])
def analyze_single():
    """단일 차트 분석 API (이미지 업로드 방식)"""
    try:
        logger.info("단일 분석 요청 시작 (이미지 업로드)")
        
        # 파일 확인
        if 'image' not in request.files:
            return jsonify({'error': '차트 이미지 파일이 필요합니다'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
        
        if not allowed_image_file(file.filename):
            return jsonify({'error': '지원하지 않는 이미지 형식입니다'}), 400
        
        # 폼 데이터 추출
        stock_name = request.form.get('stock_name', '')
        chart_type = request.form.get('chart_type', '일봉')
        
        logger.info(f"분석 요청: 종목={stock_name}, 차트타입={chart_type}")
        
        # 파일 저장
        filename = secure_filename(f"chart_{int(time.time())}_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'charts', filename)
        file.save(filepath)
        
        logger.info(f"파일 저장 완료: {filepath}")
        
        # 단일 분석 실행
        from .utils import analyze_single_chart
        result = analyze_single_chart(filepath, stock_name, chart_type)
        
        logger.info("단일 분석 완료")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"단일 분석 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analyze/single/chart', methods=['POST'])
def analyze_single_chart():
    """단일 차트 분석 API (종목코드 기반 차트 생성 및 분석)"""
    try:
        logger.info("단일 차트 분석 요청 시작 (종목코드 기반)")
        
        # JSON 데이터 확인
        data = request.get_json()
        if not data:
            return jsonify({'error': '요청 데이터가 필요합니다'}), 400
        
        stock_code = data.get('stock_code', '').strip()
        chart_type = data.get('chart_type', '일봉')
        
        if not stock_code:
            return jsonify({'error': '종목코드가 필요합니다'}), 400
        
        logger.info(f"차트 생성 및 분석 요청: 종목코드={stock_code}, 차트타입={chart_type}")
        
        # 차트 생성 및 분석 실행
        from .utils import generate_and_analyze_chart
        result = generate_and_analyze_chart(stock_code, chart_type)
        
        logger.info("차트 생성 및 분석 완료")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"차트 생성 및 분석 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analyze/batch', methods=['POST'])
def analyze_batch():
    """대량 분석 API"""
    try:
        logger.info("대량 분석 요청 시작")
        
        # 파일 확인
        if 'stock_list' not in request.files:
            return jsonify({'error': '종목 리스트 파일이 필요합니다'}), 400
        
        stock_list_file = request.files['stock_list']
        if stock_list_file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
        
        if not allowed_text_file(stock_list_file.filename):
            return jsonify({'error': '텍스트 파일만 업로드 가능합니다'}), 400
        
        # 폼 데이터 추출
        chart_type = request.form.get('chart_type', '일봉')
        
        logger.info(f"대량 분석 요청: 차트타입={chart_type}")
        
        # 종목 리스트 파일 저장
        filename = secure_filename(f"stock_list_{int(time.time())}_{stock_list_file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'stock_lists', filename)
        stock_list_file.save(filepath)
        
        logger.info(f"종목 리스트 파일 저장 완료: {filepath}")
        
        # 대량 분석 시작 (비동기 처리)
        batch_id = f"batch_{int(time.time())}"
        from .batch_analyzer import BatchAnalyzer
        analyzer = BatchAnalyzer()
        analyzer.start_batch_analysis(filepath, chart_type, batch_id)
        
        logger.info(f"대량 분석 시작: batch_id={batch_id}")
        
        return jsonify({
            'batch_id': batch_id,
            'message': '대량 분석이 시작되었습니다. 진행 상황을 확인해주세요.'
        })
    
    except Exception as e:
        logger.error(f"대량 분석 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/batch/status/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """대량 분석 진행 상황 조회"""
    try:
        from .batch_analyzer import BatchAnalyzer
        analyzer = BatchAnalyzer()
        status = analyzer.get_batch_status(batch_id)
        return jsonify(status)
    except Exception as e:
        logger.error(f"배치 상태 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/batch/results/<batch_id>', methods=['GET'])
def get_batch_results(batch_id):
    """대량 분석 결과 조회"""
    try:
        from .batch_analyzer import BatchAnalyzer
        analyzer = BatchAnalyzer()
        results = analyzer.get_batch_results(batch_id)
        return jsonify(results)
    except Exception as e:
        logger.error(f"배치 결과 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/download/<batch_id>', methods=['GET'])
def download_results(batch_id):
    """분석 결과 다운로드"""
    try:
        filepath = os.path.join(current_app.config['RESULTS_FOLDER'], f"{batch_id}_results.zip")
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': '결과 파일을 찾을 수 없습니다'}), 404
    except Exception as e:
        logger.error(f"결과 다운로드 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/stocks', methods=['GET'])
def get_stock_list():
    """종목 목록 조회 API"""
    try:
        from .utils import get_stock_list_from_file
        stocks = get_stock_list_from_file()
        return jsonify({'stocks': stocks})
    except Exception as e:
        logger.error(f"종목 목록 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chart-types', methods=['GET'])
def get_chart_types():
    """차트 유형 목록 조회"""
    try:
        chart_types = [
            {'name': '일봉', 'value': '일봉'},
            {'name': '주봉', 'value': '주봉'},
            {'name': '월봉', 'value': '월봉'}
        ]
        return jsonify({'chart_types': chart_types})
    except Exception as e:
        logger.error(f"차트 유형 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500 