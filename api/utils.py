#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 유틸리티 함수들
기존 분석 모듈과의 연동을 위한 래퍼 함수들
"""

# matplotlib 백엔드를 Agg로 설정 (tkinter 에러 방지)
import matplotlib
matplotlib.use('Agg')

import os
import logging
from typing import Dict, Any, List
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

def get_stock_list_from_file(file_path: str = "stock_list.txt") -> List[str]:
    """파일에서 종목 목록 가져오기"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            # 종목코드만 추출 (6자리 숫자인 경우만)
            stocks = []
            for line in lines:
                if line.isdigit() and len(line) == 6:
                    stocks.append(line)
            
            logger.info(f"종목 목록 로드 완료: {len(stocks)}개")
            return stocks
        else:
            logger.warning(f"종목 리스트 파일을 찾을 수 없습니다: {file_path}")
            return []
    except Exception as e:
        logger.error(f"종목 목록 로드 오류: {e}")
        return []

def analyze_single_chart(image_path: str, stock_name: str, chart_type: str, chart_data=None) -> Dict[str, Any]:
    """단일 차트 분석 실행"""
    try:
        logger.info(f"단일 차트 분석 시작: {stock_name}, {chart_type}")
        
        # AI 차트 분석 모듈 import
        from ai_chart_analysis import AIChartAnalyzer
        from config import config
        
        # API 키 확인
        api_key = config.get_api_key()
        if not api_key:
            raise Exception("API 키가 설정되지 않았습니다. setup_api_key.py를 실행해주세요.")
        
        # AI 분석기 초기화
        analyzer = AIChartAnalyzer(api_key)
        
        # 차트 데이터가 있는 경우 AI 분석에 전달
        if chart_data is not None:
            logger.info(f"차트 데이터 정보: {len(chart_data)}개 데이터 포인트")
            result = analyzer.analyze_chart_image(image_path, stock_name, chart_type, chart_data)
        else:
            logger.info("차트 데이터가 없어 이미지만으로 분석을 진행합니다.")
            result = analyzer.analyze_chart_image(image_path, stock_name, chart_type)
        
        if result is None:
            raise Exception("차트 분석에 실패했습니다.")
        
        logger.info("단일 차트 분석 완료")
        return result
        
    except Exception as e:
        logger.error(f"단일 차트 분석 오류: {e}")
        # 에러 정보를 포함한 결과 반환
        return {
            'error': str(e),
            'stock_name': stock_name,
            'chart_type': chart_type,
            'analysis_score': 0,
            'summary': '분석 중 오류가 발생했습니다.',
            'detailed_analysis': f'오류 내용: {str(e)}'
        }

def extract_stock_code(stock_name: str) -> str:
    """종목코드 추출"""
    # 이미 6자리 숫자면 종목코드로 인식
    if stock_name.isdigit() and len(stock_name) == 6:
        return stock_name
    # 종목명이면 그대로 반환
    return stock_name

def validate_chart_type(chart_type: str) -> bool:
    """차트 유형 검증"""
    valid_types = ['일봉', '주봉', '월봉']
    return chart_type in valid_types

def get_chart_type_options() -> List[tuple]:
    """차트 유형 옵션 반환"""
    return [
        ("일봉", "일봉"),
        ("주봉", "주봉"), 
        ("월봉", "월봉")
    ]

def create_error_response(error_message: str, error_type: str = "general") -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'error': error_message,
        'error_type': error_type,
        'timestamp': None,
        'analysis_score': 0,
        'summary': '분석 중 오류가 발생했습니다.',
        'detailed_analysis': f'오류 내용: {error_message}'
    }

def validate_file_size(file_path: str, max_size_mb: int = 16) -> bool:
    """파일 크기 검증"""
    try:
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
    except Exception as e:
        logger.error(f"파일 크기 검증 오류: {e}")
        return False

def cleanup_temp_files(file_paths: List[str]):
    """임시 파일 정리"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"임시 파일 삭제: {file_path}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {file_path}, 오류: {e}")

def generate_and_analyze_chart(stock_code: str, chart_type: str) -> Dict[str, Any]:
    """종목코드 기반 차트 생성 및 분석"""
    try:
        logger.info(f"차트 생성 및 분석 시작: {stock_code}, {chart_type}")
        
        # 차트 생성 및 데이터 조회
        chart_path, chart_data = generate_stock_chart_with_data(stock_code, chart_type)
        if not chart_path:
            raise Exception(f"차트 생성에 실패했습니다: {stock_code}")
        
        # 종목명 조회
        stock_name = get_stock_name(stock_code)
        
        # AI 분석 실행 (차트 데이터 포함)
        result = analyze_single_chart(chart_path, stock_name, chart_type, chart_data)
        
        # 프론트엔드 형식으로 변환
        frontend_result = convert_ai_result_to_frontend_format(result, stock_name, stock_code, chart_type)
        
        logger.info(f"차트 생성 및 분석 완료: {stock_code}")
        return frontend_result
        
    except Exception as e:
        logger.error(f"차트 생성 및 분석 오류: {e}")
        return create_error_response(str(e), "chart_generation_error")

def convert_ai_result_to_frontend_format(ai_result: Dict[str, Any], stock_name: str, stock_code: str, chart_type: str) -> Dict[str, Any]:
    """AI 분석 결과를 프론트엔드에서 기대하는 형태로 변환"""
    try:
        # 기본 정보
        result = {
            'stock_name': stock_name,
            'stock_code': stock_code,
            'chart_type': chart_type,
            'analysis_score': 0,
            'summary': '',
            'detailed_analysis': ''
        }
        
        # 종합 분석 점수 추출
        if '종합분석점수' in ai_result:
            score_data = ai_result['종합분석점수']
            if '점수' in score_data:
                result['analysis_score'] = score_data['점수']
            if '요약' in score_data:
                result['summary'] = score_data['요약']
        
        # 상세 분석 구성
        detailed_parts = []
        
        # 단기 투자 아이디어
        if '단기투자아이디어' in ai_result:
            idea_data = ai_result['단기투자아이디어']
            if '매매시그널' in idea_data:
                detailed_parts.append(f"📈 매매 시그널: {idea_data['매매시그널']}")
            if '추세요약' in idea_data:
                detailed_parts.append(f"📊 추세 요약: {idea_data['추세요약']}")
        
        # 세부 분석
        if '세부분석' in ai_result:
            detail_data = ai_result['세부분석']
            if '가격및거래량' in detail_data:
                price_data = detail_data['가격및거래량']
                if '거래량비교' in price_data:
                    detailed_parts.append(f"📊 거래량: {price_data['거래량비교']}")
                if '주요가격대' in price_data:
                    detailed_parts.append(f"💰 주요 가격대: {price_data['주요가격대']}")
            
            if '모멘텀' in detail_data:
                momentum_data = detail_data['모멘텀']
                if 'MACD분석' in momentum_data:
                    detailed_parts.append(f"📈 MACD: {momentum_data['MACD분석']}")
                if 'RSI분석' in momentum_data:
                    detailed_parts.append(f"📊 RSI: {momentum_data['RSI분석']}")
            
            if '이동평균선' in detail_data:
                ma_data = detail_data['이동평균선']
                if '밀집도' in ma_data:
                    detailed_parts.append(f"📊 이동평균선: {ma_data['밀집도']}")
                if '현재가위치' in ma_data:
                    detailed_parts.append(f"📍 현재가 위치: {ma_data['현재가위치']}")
        
        # 오늘의 일봉
        if '오늘의일봉' in ai_result:
            today_data = ai_result['오늘의일봉']
            if '주요특징' in today_data:
                detailed_parts.append(f"📅 오늘의 특징: {today_data['주요특징']}")
            if '종가' in today_data and '등락률' in today_data:
                detailed_parts.append(f"💰 종가: {today_data['종가']}원 ({today_data['등락률']})")
        
        # 핵심 기술적 지표
        if '핵심기술적지표' in ai_result:
            tech_data = ai_result['핵심기술적지표']
            tech_parts = []
            if 'MACD상태' in tech_data:
                tech_parts.append(f"MACD: {tech_data['MACD상태']}")
            if 'RSI상태' in tech_data:
                tech_parts.append(f"RSI: {tech_data['RSI상태']}")
            if '볼린저밴드' in tech_data:
                tech_parts.append(f"볼린저밴드: {tech_data['볼린저밴드']}")
            if tech_parts:
                detailed_parts.append(f"🔧 기술적 지표: {' | '.join(tech_parts)}")
        
        result['detailed_analysis'] = '\n\n'.join(detailed_parts)
        
        return result
        
    except Exception as e:
        logger.error(f"AI 결과 변환 오류: {e}")
        return {
            'stock_name': stock_name,
            'stock_code': stock_code,
            'chart_type': chart_type,
            'analysis_score': 0,
            'summary': '결과 변환 중 오류가 발생했습니다.',
            'detailed_analysis': f'오류 내용: {str(e)}'
        }

def generate_stock_chart_with_data(stock_code: str, chart_type: str) -> tuple[str, object]:
    """종목코드 기반 차트 생성 (데이터 포함)"""
    try:
        logger.info(f"차트 생성 시작: {stock_code}, {chart_type}")
        
        # 차트 타입에 따른 모듈 선택
        if chart_type == '일봉':
            from day_stock_analysis import get_stock_data, create_stock_chart
        elif chart_type == '주봉':
            from week_stock_analysis import get_weekly_stock_data, create_weekly_stock_chart
        elif chart_type == '월봉':
            from month_stock_analysis import get_monthly_stock_data, create_monthly_stock_chart
        else:
            raise Exception(f"지원하지 않는 차트 타입: {chart_type}")
        
        # 주식 데이터 조회
        if chart_type == '일봉':
            hist = get_stock_data(stock_code)
        elif chart_type == '주봉':
            hist = get_weekly_stock_data(stock_code)
        elif chart_type == '월봉':
            hist = get_monthly_stock_data(stock_code)
        
        if hist is None or hist.empty:
            raise Exception(f"주식 데이터를 가져올 수 없습니다: {stock_code}")
        
        # 차트 생성
        if chart_type == '일봉':
            chart_path = create_stock_chart(hist, stock_code)
        elif chart_type == '주봉':
            chart_path = create_weekly_stock_chart(hist, stock_code)
        elif chart_type == '월봉':
            chart_path = create_monthly_stock_chart(hist, stock_code)
        
        if not chart_path:
            raise Exception("차트 생성에 실패했습니다.")
        
        logger.info(f"차트 생성 완료: {chart_path}")
        return chart_path, hist
        
    except Exception as e:
        logger.error(f"차트 생성 오류: {e}")
        return None, None

def generate_stock_chart(stock_code: str, chart_type: str) -> str:
    """종목코드 기반 차트 생성 (기존 호환성 유지)"""
    chart_path, _ = generate_stock_chart_with_data(stock_code, chart_type)
    return chart_path

def get_stock_name(stock_code: str) -> str:
    """종목코드로 종목명 조회"""
    try:
        import yfinance as yf
        
        # Yahoo Finance에서 종목 정보 조회
        tickers_to_try = [
            f"{stock_code}.KS",   # 코스피
            f"{stock_code}.KQ",   # 코스닥
        ]
        
        for ticker in tickers_to_try:
            try:
                stock = yf.Ticker(ticker)
                stock_info = stock.info
                
                # 종목명 우선순위: longName > shortName > 종목코드
                if 'longName' in stock_info and stock_info['longName'] and stock_info['longName'] != 'N/A':
                    return stock_info['longName']
                elif 'shortName' in stock_info and stock_info['shortName'] and stock_info['shortName'] != 'N/A':
                    if stock_info['shortName'] != stock_code and not stock_info['shortName'].startswith(stock_code):
                        return stock_info['shortName']
            except:
                continue
        
        # 종목명을 찾을 수 없으면 종목코드 반환
        return stock_code
        
    except Exception as e:
        logger.warning(f"종목명 조회 오류: {e}")
        return stock_code 