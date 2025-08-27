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
from .volume_ranking_utils import VolumeRankingDataManager

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

@api_bp.route('/volume-ranking', methods=['GET'])
def get_volume_ranking():
    """거래량 상위 50개 종목 조회 API"""
    try:
        logger.info("거래량 랭킹 조회 API 요청")
        
        # 날짜 파라미터 확인
        date_str = request.args.get('date', '')
        if not date_str:
            return jsonify({'error': '날짜 파라미터가 필요합니다 (YYYY-MM-DD 형식)'}), 400
        
        # 날짜 형식 검증
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': '날짜 형식이 올바르지 않습니다 (YYYY-MM-DD 형식)'}), 400
        
        # 거래량 랭킹 조회
        from .utils import get_volume_ranking
        result = get_volume_ranking(date_str)
        
        if 'error' in result:
            return jsonify(result), 500
        
        logger.info(f"거래량 랭킹 조회 완료: {date_str}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"거래량 랭킹 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/volume-ranking/dates', methods=['GET'])
def get_available_dates():
    """거래량 랭킹을 조회할 수 있는 날짜 목록 API"""
    try:
        logger.info("사용 가능한 날짜 목록 조회 API 요청")
        
        # 사용 가능한 날짜 목록 조회
        from .utils import get_available_dates
        dates = get_available_dates()
        
        logger.info(f"사용 가능한 날짜 목록 조회 완료: {len(dates)}개")
        return jsonify({
            'dates': dates,
            'total_count': len(dates),
            'message': '사용 가능한 날짜 목록을 조회했습니다.'
        })
        
    except Exception as e:
        logger.error(f"사용 가능한 날짜 목록 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500 

# VolumeRankingDataManager import 추가
from .volume_ranking_utils import VolumeRankingDataManager

@api_bp.route('/volume-ranking/daily/volume', methods=['GET'])
def get_daily_volume_ranking():
    """일일 거래량 상위 종목 조회 API"""
    try:
        logger.info("일일 거래량 랭킹 조회 API 요청")
        
        # 날짜 파라미터 확인
        date_str = request.args.get('date', '')
        limit = int(request.args.get('limit', 50))
        
        # VolumeRankingDataManager 사용
        manager = VolumeRankingDataManager()
        result = manager.get_daily_volume_ranking(date_str, limit)
        
        logger.info(f"일일 거래량 랭킹 조회 완료: {date_str}")
        return jsonify({
            'type': 'daily_volume',
            'date': date_str,
            'limit': limit,
            'data': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        logger.error(f"일일 거래량 랭킹 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/volume-ranking/daily/turnover', methods=['GET'])
def get_daily_turnover_ranking():
    """일일 거래률 상위 종목 조회 API"""
    try:
        logger.info("일일 거래률 랭킹 조회 API 요청")
        
        # 날짜 파라미터 확인
        date_str = request.args.get('date', '')
        limit = int(request.args.get('limit', 50))
        
        # VolumeRankingDataManager 사용
        manager = VolumeRankingDataManager()
        result = manager.get_daily_turnover_ranking(date_str, limit)
        
        logger.info(f"일일 거래률 랭킹 조회 완료: {date_str}")
        return jsonify({
            'type': 'daily_turnover',
            'date': date_str,
            'limit': limit,
            'data': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        logger.error(f"일일 거래률 랭킹 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/volume-ranking/weekly/volume', methods=['GET'])
def get_weekly_volume_ranking():
    """주간 거래량 상위 종목 조회 API"""
    try:
        logger.info("주간 거래량 랭킹 조회 API 요청")
        
        # 주 시작일 파라미터 확인
        week_start = request.args.get('week_start', '')
        limit = int(request.args.get('limit', 50))
        
        # VolumeRankingDataManager 사용
        manager = VolumeRankingDataManager()
        result = manager.get_weekly_volume_ranking(week_start, limit)
        
        logger.info(f"주간 거래량 랭킹 조회 완료: {week_start}")
        return jsonify({
            'type': 'weekly_volume',
            'week_start': week_start,
            'limit': limit,
            'data': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        logger.error(f"주간 거래량 랭킹 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/volume-ranking/weekly/turnover', methods=['GET'])
def get_weekly_turnover_ranking():
    """주간 거래률 상위 종목 조회 API"""
    try:
        logger.info("주간 거래률 랭킹 조회 API 요청")
        
        # 주 시작일 파라미터 확인
        week_start = request.args.get('week_start', '')
        limit = int(request.args.get('limit', 50))
        
        # VolumeRankingDataManager 사용
        manager = VolumeRankingDataManager()
        result = manager.get_weekly_turnover_ranking(week_start, limit)
        
        logger.info(f"주간 거래률 랭킹 조회 완료: {week_start}")
        return jsonify({
            'type': 'weekly_turnover',
            'week_start': week_start,
            'limit': limit,
            'data': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        logger.error(f"주간 거래률 랭킹 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/volume-ranking/monthly/volume', methods=['GET'])
def get_monthly_volume_ranking():
    """월간 거래량 상위 종목 조회 API"""
    try:
        logger.info("월간 거래량 랭킹 조회 API 요청")
        
        # 년월 파라미터 확인
        year_month = request.args.get('year_month', '')
        limit = int(request.args.get('limit', 50))
        
        # VolumeRankingDataManager 사용
        manager = VolumeRankingDataManager()
        result = manager.get_monthly_volume_ranking(year_month, limit)
        
        logger.info(f"월간 거래량 랭킹 조회 완료: {year_month}")
        return jsonify({
            'type': 'monthly_volume',
            'year_month': year_month,
            'limit': limit,
            'data': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        logger.error(f"월간 거래량 랭킹 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/volume-ranking/monthly/turnover', methods=['GET'])
def get_monthly_turnover_ranking():
    """월간 거래률 상위 종목 조회 API"""
    try:
        logger.info("월간 거래률 랭킹 조회 API 요청")
        
        # 년월 파라미터 확인
        year_month = request.args.get('year_month', '')
        limit = int(request.args.get('limit', 50))
        
        # VolumeRankingDataManager 사용
        manager = VolumeRankingDataManager()
        result = manager.get_monthly_turnover_ranking(year_month, limit)
        
        logger.info(f"월간 거래률 랭킹 조회 완료: {year_month}")
        return jsonify({
            'type': 'monthly_turnover',
            'year_month': year_month,
            'limit': limit,
            'data': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        logger.error(f"월간 거래률 랭킹 조회 API 오류: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/volume-ranking/cache/clear', methods=['POST'])
def clear_volume_ranking_cache():
    """거래량 랭킹 캐시 초기화 API"""
    try:
        logger.info("거래량 랭킹 캐시 초기화 API 요청")
        
        # VolumeRankingDataManager 사용
        manager = VolumeRankingDataManager()
        manager.clear_cache()
        
        logger.info("거래량 랭킹 캐시 초기화 완료")
        return jsonify({
            'message': '거래량 랭킹 캐시가 초기화되었습니다.',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"거래량 랭킹 캐시 초기화 API 오류: {e}")
        return jsonify({'error': str(e)}), 500 