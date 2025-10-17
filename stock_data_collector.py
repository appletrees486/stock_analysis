#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주식 데이터 수집 및 데이터베이스 저장 모듈
2760개 종목을 100개씩 나누어 10년치 일봉 데이터 수집
속도 최적화 버전 - 병렬 처리 및 DB 연결 최적화
PyKrx 기반 데이터 수집 (Yahoo Finance 대체)
"""

# PyKrx 라이브러리 import (Yahoo Finance 대체)
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError as e:
    PYKRX_AVAILABLE = False
    print(f"⚠️ PyKrx 라이브러리 import 실패: {e}")
    print("💡 PyKrx 설치: pip install pykrx")

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from database_config import DatabaseManager
import time
import random
import concurrent.futures
import threading
from queue import Queue
from market_status_detector import MarketStatusDetector
from enhanced_data_validator import EnhancedDataValidator
from typing import Optional, Dict, Any


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class StockDataCollector:
    def __init__(self):
        """주식 데이터 수집기 초기화"""
        self.db = DatabaseManager()
        self.market_detector = MarketStatusDetector()  # 시장 상태 감지기
        self.data_validator = EnhancedDataValidator()  # 데이터 검증기
        self.batch_size = 200  # 배치 크기 증가 (안정성 유지) [최적화]
        self.delay_between_requests = 0.03  # 요청 간 딜레이 (30ms - 속도와 안정성 균형) [최적화]
        self.max_retries = 5  # 최대 재시도 횟수 (100% 수집 목표) [최적화]
        self.max_workers = 8  # 병렬 처리 워커 수 증가 (속도 개선) [최적화]
        self.batch_delay = 1  # 배치 간 딜레이 (1초 - 속도 개선) [최적화]
        self._db_lock = threading.Lock()  # DB 연결 동기화용 락
        
        # 유통주식수 배치 조회 최적화를 위한 캐시
        self._shares_cache = {}  # {stock_code: {'total_shares': int, 'market_cap': float}}
        self._shares_cache_date = None  # 캐시 생성 날짜
        
        # 진행률 업데이트 콜백 함수
        self.progress_callback = None
        self.stats_callback = None
        
        # 우선주 및 특수 종목코드 매핑 정보 (PyKrx 기반으로 대체되어 더 이상 사용하지 않음)
        self._preferred_stock_mapping = {}  # 빈 딕셔너리로 설정 (제거 예정)
        
        # KOSDAQ 특수 종목코드 매핑 (PyKrx 기반으로 대체되어 더 이상 사용하지 않음)
        self._kosdaq_special_mapping = {}  # 빈 딕셔너리로 설정 (제거 예정)
        
        # 상장폐지/비활성 의심 종목코드 패턴
        self._delisted_patterns = [
            # 추가 상장폐지 종목들...
        ]
    
    def set_progress_callback(self, callback):
        """진행률 업데이트 콜백 함수 설정"""
        self.progress_callback = callback
    
    def set_stats_callback(self, callback):
        """통계 업데이트 콜백 함수 설정"""
        self.stats_callback = callback
    
    def update_progress(self, total, processed, current_batch, total_batches):
        """진행률 업데이트"""
        if self.progress_callback:
            try:
                self.progress_callback(total, processed, current_batch, total_batches)
            except Exception as e:
                logging.warning(f"진행률 업데이트 콜백 실행 중 오류: {e}")
    
    def update_stats(self, success_count, failed_count, skipped_count=0):
        """통계 업데이트"""
        if self.stats_callback:
            try:
                self.stats_callback(success_count, failed_count, skipped_count)
            except Exception as e:
                logging.warning(f"통계 업데이트 콜백 실행 중 오류: {e}")
    
    def _get_optimized_ticker_symbols(self, stock_code, stock_name):
        """PyKrx 기반으로 대체되어 더 이상 사용하지 않음 - 제거 예정"""
        logging.warning(f"⚠️ {stock_code}: _get_optimized_ticker_symbols 함수는 더 이상 사용되지 않습니다. PyKrx 기반으로 대체되었습니다.")
        return []
    
    def _retry_with_alternative_methods(self, stock_code, stock_name, years):
        """PyKrx 기반으로 대체되어 더 이상 사용하지 않음 - 제거 예정"""
        logging.warning(f"⚠️ {stock_code}: _retry_with_alternative_methods 함수는 더 이상 사용되지 않습니다. PyKrx 기반으로 대체되었습니다.")
        return None
    
    def _is_likely_delisted(self, stock_code, stock_name):
        """상장폐지/비활성 의심 종목인지 확인 (간단한 필터링)"""
        try:
            # 1. 알려진 상장폐지 종목코드 체크
            if stock_code in self._delisted_patterns:
                return True
            
            # 2. 특수 패턴 체크 (알파벳이 포함된 특수 종목코드)
            if any(c.isalpha() for c in stock_code) and len(stock_code) > 6:
                # 6자리를 초과하는 알파벳 포함 종목은 의심
                return True
            
            # 3. 종목명에 특정 키워드가 포함된 경우
            delisted_keywords = ['상장폐지', '폐지', '청산', '해산', '파산', '부도']
            if any(keyword in stock_name for keyword in delisted_keywords):
                return True
            
            # 4. 9로 시작하는 7자리 이상 종목코드 (비정상 패턴)
            if stock_code.startswith('9') and len(stock_code) > 6:
                return True
            
            return False
            
        except Exception as e:
            logging.warning(f"⚠️ {stock_code} 상장폐지 여부 확인 중 오류: {e}")
            return False  # 오류 시 기본적으로 수집 시도
    
    def get_all_stock_codes(self):
        """데이터베이스에서 모든 종목 코드 조회"""
        try:
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    logging.error("데이터베이스 연결 실패")
                    return []
            
            query = "SELECT stock_code, stock_name FROM stocks WHERE is_active = TRUE ORDER BY stock_code"
            result = self.db.fetch_all(query)
            
            if result:
                stock_codes = [(row['stock_code'], row['stock_name']) for row in result]
                logging.info(f"총 {len(stock_codes)}개 종목을 찾았습니다.")
                return stock_codes
            else:
                logging.warning("활성 종목이 없습니다.")
                return []
                
        except Exception as e:
            logging.error(f"종목 코드 조회 실패: {e}")
            return []
        finally:
            # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
            pass
    
    def get_stock_by_code(self, stock_code):
        """특정 종목 코드로 종목 정보 조회"""
        try:
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    logging.error("데이터베이스 연결 실패")
                    return None
            
            query = "SELECT stock_code, stock_name FROM stocks WHERE stock_code = %s AND is_active = TRUE"
            result = self.db.fetch_one(query, (stock_code,))
            
            if result:
                stock_info = (result['stock_code'], result['stock_name'])
                logging.info(f"종목 {stock_code} ({result['stock_name']}) 정보 조회 완료")
                return stock_info
            else:
                logging.warning(f"종목 {stock_code}을(를) 찾을 수 없거나 비활성 상태입니다.")
                return None
                
        except Exception as e:
            logging.error(f"종목 {stock_code} 정보 조회 실패: {e}")
            return None
        finally:
            # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
            pass

    def calculate_technical_indicators(self, df):
        """기술적 지표 계산"""
        try:
            # 이동평균선
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()
            
            # 볼린저 밴드 계산 (20일 기준)
            df['BB_Middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
            
            # MACD 계산
            ema12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema26 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = ema12 - ema26
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
            
            # RSI 계산
            delta = df['Close'].diff()
            gain = delta.copy()
            loss = delta.copy()
            gain[gain < 0] = 0
            loss[loss > 0] = 0
            loss = abs(loss)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            return df
        except Exception as e:
            logging.error(f"기술적 지표 계산 실패: {e}")
            return df
    
    def get_batch_last_collected_dates(self, stock_codes):
        """배치 단위로 여러 종목의 마지막 수집 날짜 조회"""
        try:
            if not stock_codes:
                return {}
            
            # daily_data 테이블에서 배치로 조회
            daily_query = """
            SELECT stock_code, MAX(trade_date) as last_collected_date 
            FROM daily_data 
            WHERE stock_code IN ({})
            GROUP BY stock_code
            """.format(','.join(['%s'] * len(stock_codes)))
            
            daily_result = self.db.fetch_all(daily_query, stock_codes)
            
            # stock_collection_status 테이블에서 배치로 조회
            status_query = """
            SELECT stock_code, last_collected_date 
            FROM stock_collection_status 
            WHERE stock_code IN ({})
            """.format(','.join(['%s'] * len(stock_codes)))
            
            status_result = self.db.fetch_all(status_query, stock_codes)
            
            # 결과를 딕셔너리로 통합
            result = {}
            
            # daily_data 결과 처리
            for row in daily_result:
                stock_code = row['stock_code']
                last_date = row['last_collected_date']
                if last_date:
                    if isinstance(last_date, str):
                        last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
                    elif isinstance(last_date, datetime):
                        last_date = last_date.date()
                    result[stock_code] = last_date
            
            # stock_collection_status 결과 처리 (daily_data에 없는 경우만)
            for row in status_result:
                stock_code = row['stock_code']
                if stock_code not in result:  # daily_data에 없는 경우만
                    last_date = row['last_collected_date']
                    if last_date:
                        if isinstance(last_date, str):
                            last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
                        elif isinstance(last_date, datetime):
                            last_date = last_date.date()
                        result[stock_code] = last_date
            
            logging.info(f"📅 배치로 {len(result)}개 종목의 마지막 수집 날짜 조회 완료")
            return result
            
        except Exception as e:
            logging.error(f"배치 마지막 수집 날짜 조회 실패: {e}")
            return {}
    
    def get_last_collected_date(self, stock_code):
        """특정 종목의 마지막 수집 날짜 조회 - daily_data 테이블 우선 확인"""
        try:
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    logging.error("데이터베이스 연결 실패")
                    return None
            
            # 1. daily_data 테이블에서 실제 데이터 확인 (우선순위)
            daily_query = """
            SELECT MAX(trade_date) as last_collected_date 
            FROM daily_data 
            WHERE stock_code = %s
            """
            daily_result = self.db.fetch_one(daily_query, (stock_code,))
            
            if daily_result and daily_result['last_collected_date']:
                last_date = daily_result['last_collected_date']
                if isinstance(last_date, str):
                    last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
                elif isinstance(last_date, datetime):
                    last_date = last_date.date()
                logging.info(f"📅 {stock_code} daily_data 테이블에서 마지막 수집 날짜: {last_date}")
                return last_date
            
            # 2. daily_data에 데이터가 없으면 stock_collection_status 테이블 확인
            status_query = """
            SELECT last_collected_date 
            FROM stock_collection_status 
            WHERE stock_code = %s
            """
            status_result = self.db.fetch_one(status_query, (stock_code,))
            
            if status_result and status_result['last_collected_date']:
                last_date = status_result['last_collected_date']
                if isinstance(last_date, str):
                    last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
                elif isinstance(last_date, datetime):
                    last_date = last_date.date()
                logging.info(f"📅 {stock_code} stock_collection_status에서 마지막 수집 날짜: {last_date} (daily_data 없음)")
                return last_date
            else:
                logging.info(f"📅 {stock_code} 수집 이력이 없습니다. 최초 수집을 진행합니다.")
                return None
                
        except Exception as e:
            logging.error(f"{stock_code} 마지막 수집 날짜 조회 실패: {e}")
            return None
        finally:
            # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
            pass
    
    def get_last_collection_timestamp(self, stock_code):
        """마지막 수집 시간 정보 조회 (전일 데이터 품질 검증용)"""
        try:
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    return None
            
            query = """
            SELECT last_collected_timestamp, last_collected_date
            FROM stock_collection_status 
            WHERE stock_code = %s
            """
            result = self.db.fetch_one(query, (stock_code,))
            
            if result:
                return {
                    'timestamp': result.get('last_collected_timestamp'),
                    'date': result.get('last_collected_date')
                }
            return None
            
        except Exception as e:
            logging.error(f"수집 시간 정보 조회 실패: {e}")
            return None
        finally:
            # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
            pass
    
    def is_intraday_collection(self, collection_info):
        """장중에 수집된 데이터인지 확인"""
        try:
            if not collection_info or not collection_info.get('timestamp'):
                return False
            
            timestamp = collection_info['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            
            # 한국 시간으로 변환 (pytz 없이 기본 datetime 사용)
            if timestamp.tzinfo is None:
                # 로컬 시간으로 간주
                pass
            
            # 장 시간 확인 (9:00-15:30)
            from datetime import time
            market_open = time(9, 0)
            market_close = time(15, 30)
            
            collection_time = timestamp.time()
            
            # 장중에 수집된 데이터인지 확인
            if market_open <= collection_time <= market_close:
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"장중 수집 여부 확인 실패: {e}")
            return False
    
    def validate_previous_day_data_quality(self, stock_code, last_collected_date):
        """전일 데이터 품질 검증 (장중 vs 장 마감 데이터)"""
        try:
            if not last_collected_date:
                return True, "최초 수집"
            
            # 전일이 거래일인지 확인
            previous_day = last_collected_date - timedelta(days=1)
            if self.market_detector.is_holiday(previous_day) or self.market_detector.is_weekend(previous_day):
                return True, "전일 휴장일"
            
            # 마지막 수집 시간 정보 조회
            last_collection_info = self.get_last_collection_timestamp(stock_code)
            if not last_collection_info:
                return False, "수집 시간 정보 없음"
            
            # 장중에 수집되었는지 확인
            if self.is_intraday_collection(last_collection_info):
                logging.warning(f"⚠️ {stock_code}: 전일 장중 데이터 감지 - 장 마감 후 재수집 필요")
                return False, "장중 데이터"
            
            return True, "장 마감 후 데이터"
            
        except Exception as e:
            logging.error(f"전일 데이터 품질 검증 실패: {e}")
            return False, f"검증 오류: {e}"
    
    def is_optimal_collection_time(self):
        """현재가 데이터 수집 최적 시간인지 확인"""
        try:
            # 데이터 수집 권장 시간 확인
            is_collection_time, status = self.market_detector.is_data_collection_time()
            
            if not is_collection_time:
                logging.warning(f"⚠️ 현재는 데이터 수집 권장 시간이 아닙니다: {status}")
                logging.info("💡 권장 시간: 장 마감 후 1시간 이후 또는 다음날 장 시작 전")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"수집 시간 확인 실패: {e}")
            return True  # 오류 시 기본적으로 진행

    def get_incremental_data(self, stock_code, stock_name, start_date):
        """PyKrx 기반으로 대체되어 더 이상 사용하지 않음 - 제거 예정"""
        logging.warning(f"⚠️ {stock_code}: get_incremental_data 함수는 더 이상 사용되지 않습니다. PyKrx 기반으로 대체되었습니다.")
        return None

    def get_stock_data(self, stock_code, stock_name, years=10):
        """주식 데이터 조회 (PyKrx 기반) - 전일 데이터 품질 검증 포함"""
        try:
            # PyKrx 사용 가능 여부 확인
            if not PYKRX_AVAILABLE:
                logging.error("❌ PyKrx 라이브러리가 설치되지 않았습니다.")
                return None
            
            # 마지막 수집 날짜 확인
            last_collected_date = self.get_last_collected_date(stock_code)
            
            if last_collected_date:
                # 전일 데이터 품질 검증
                is_valid, reason = self.validate_previous_day_data_quality(stock_code, last_collected_date)
                
                if not is_valid:
                    logging.info(f"🔄 {stock_code} ({stock_name}): {reason} - 전일부터 재수집")
                    # 전일부터 재수집
                    start_date = last_collected_date - timedelta(days=1)
                    return self.get_incremental_data_pykrx(stock_code, stock_name, start_date)
                
                # 증분 수집: 마지막 수집 날짜 다음날부터
                next_date = last_collected_date + timedelta(days=1)
                today = datetime.now().date()
                
                if next_date <= today:
                    logging.info(f"🔄 {stock_code} ({stock_name}) 증분 수집을 진행합니다.")
                    return self.get_incremental_data_pykrx(stock_code, stock_name, next_date)
                else:
                    logging.info(f"✅ {stock_code} ({stock_name}) 이미 최신 데이터입니다. (마지막 수집: {last_collected_date})")
                    return None
            else:
                # 최초 수집: 10년치 전체 데이터
                logging.info(f"🔍 {stock_code} ({stock_name}) 10년치 일봉 데이터 조회 중... (PyKrx)")
                
                # PyKrx로 데이터 조회
                hist_data = self.get_stock_data_pykrx(stock_code, stock_name, years)
                
                if hist_data is not None:
                    return hist_data
                else:
                    logging.error(f"❌ {stock_code} ({stock_name}): PyKrx로 데이터를 찾을 수 없습니다")
                    logging.warning(f"   💡 이 종목은 상장폐지되었거나 더 이상 거래되지 않을 수 있습니다")
                    return None
                    
        except Exception as e:
            logging.error(f"{stock_code} ({stock_name}) 데이터 조회 실패: {e}")
            return None
    
    def get_stock_data_pykrx(self, stock_code, stock_name, years=10):
        """PyKrx를 사용한 주식 데이터 조회 (성능 최적화) - 거래대금 포함"""
        try:
            logging.info(f"📊 {stock_code} ({stock_name}) PyKrx로 {years}년치 데이터 조회 중... (거래대금 포함)")
            
            # 종료일 (오늘)
            end_date = datetime.now()
            # 시작일 고정: 2015-08-03 (전체 재수집 기준일)
            start_date = datetime(2015, 8, 3)
            
            # PyKrx로 데이터 조회 (거래대금 포함 - adjusted=False 옵션 사용)
            try:
                # 1차 시도: 개별 종목 데이터 조회 (주가 조정 적용)
                hist = stock.get_market_ohlcv_by_date(
                    fromdate=start_date.strftime('%Y%m%d'),
                    todate=end_date.strftime('%Y%m%d'),
                    ticker=stock_code,
                    adjusted=True  # 주가 조정 적용 (무상증자 등 반영)
                )
                
                if not hist.empty:
                    # PyKrx 응답 구조에 맞춰 컬럼명 매핑 (7개 컬럼: 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률)
                    if len(hist.columns) == 7:
                        # 7개 컬럼인 경우: 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Trading_Value', 'Change_Rate']
                        # 등락률 컬럼 제거 (기존 로직과 호환)
                        hist = hist.drop('Change_Rate', axis=1)
                    elif len(hist.columns) == 6:
                        # 6개 컬럼인 경우: 시가, 고가, 저가, 종가, 거래량, 등락률 (거래대금 없음)
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Change_Rate']
                        # 등락률 컬럼 제거 (기존 로직과 호환)
                        hist = hist.drop('Change_Rate', axis=1)
                        # 거래대금 계산 (거래량 × 종가)
                        hist['Trading_Value'] = hist['Volume'] * hist['Close']
                        logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                    elif len(hist.columns) == 5:
                        # 5개 컬럼인 경우: 기존 방식 유지
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        # 거래대금 계산 (거래량 × 종가)
                        hist['Trading_Value'] = hist['Volume'] * hist['Close']
                        logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                    else:
                        logging.warning(f"⚠️ {stock_code}: 예상치 못한 컬럼 수 ({len(hist.columns)})")
                        # 기본 컬럼명으로 설정
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        # 거래대금 계산 (거래량 × 종가)
                        hist['Trading_Value'] = hist['Volume'] * hist['Close']
                        logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                    
                    logging.info(f"✅ {stock_code} ({stock_name}): PyKrx로 {len(hist)}일의 일봉 데이터 조회 완료")
                    logging.info(f"📅 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
                    return hist
                else:
                    logging.warning(f"⚠️ {stock_code} ({stock_name}): PyKrx에서 데이터가 없습니다")
                    
            except Exception as e:
                logging.warning(f"⚠️ {stock_code} ({stock_name}): PyKrx 개별 종목 조회 실패: {e}")
            
            # 2차 시도: 짧은 기간 (3개월)으로 시도
            try:
                logging.info(f"🔄 {stock_code} ({stock_name}): 짧은 기간 (3개월)으로 재시도...")
                
                # 3개월 데이터로 재시도
                short_start = end_date - timedelta(days=90)
                market_data = stock.get_market_ohlcv_by_date(
                    fromdate=short_start.strftime('%Y%m%d'),
                    todate=end_date.strftime('%Y%m%d'),
                    ticker=stock_code,
                    adjusted=True
                )
                
                if not market_data.empty:
                    # PyKrx 응답 구조에 맞춰 컬럼명 매핑
                    if len(market_data.columns) == 7:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Trading_Value', 'Change_Rate']
                        market_data = market_data.drop('Change_Rate', axis=1)
                    elif len(market_data.columns) == 6:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Change_Rate']
                        market_data = market_data.drop('Change_Rate', axis=1)
                        market_data['Trading_Value'] = market_data['Volume'] * market_data['Close']
                    elif len(market_data.columns) == 5:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        market_data['Trading_Value'] = market_data['Volume'] * market_data['Close']
                    else:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        market_data['Trading_Value'] = market_data['Volume'] * market_data['Close']
                    
                    logging.info(f"✅ {stock_code} ({stock_name}): 짧은 기간 데이터 조회 성공 (3개월)")
                    return market_data
                else:
                    logging.warning(f"⚠️ {stock_code} ({stock_name}): 짧은 기간 데이터 조회에서 데이터를 찾을 수 없습니다")
                    
            except Exception as e2:
                logging.warning(f"⚠️ {stock_code} ({stock_name}): 짧은 기간 데이터 조회 실패: {e2}")
            
            # 3차 시도: 12개월 기간으로 시도
            try:
                logging.info(f"🔄 {stock_code} ({stock_name}): 12개월 기간으로 재시도...")
                
                # 12개월만 시도 (단순화)
                for period_months in [12]:
                    try:
                        period_start = end_date - timedelta(days=period_months * 30)
                        
                        hist = stock.get_market_ohlcv_by_date(
                            fromdate=period_start.strftime('%Y%m%d'),
                            todate=end_date.strftime('%Y%m%d'),
                            ticker=stock_code,
                            adjusted=True  # 거래대금 포함을 위해 False로 설정
                        )
                        
                        if not hist.empty:
                            # PyKrx 응답 구조에 맞춰 컬럼명 매핑 (거래대금 포함)
                            if len(hist.columns) == 7:
                                hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Trading_Value', 'Change_Rate']
                                hist = hist.drop('Change_Rate', axis=1)
                            elif len(hist.columns) == 6:
                                hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Change_Rate']
                                hist = hist.drop('Change_Rate', axis=1)
                                # 거래대금 계산 (거래량 × 종가)
                                hist['Trading_Value'] = hist['Volume'] * hist['Close']
                                logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                            elif len(hist.columns) == 5:
                                hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                                # 거래대금 계산 (거래량 × 종가)
                                hist['Trading_Value'] = hist['Volume'] * hist['Close']
                                logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                            else:
                                hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                                # 거래대금 계산 (거래량 × 종가)
                                hist['Trading_Value'] = hist['Volume'] * hist['Close']
                                logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                            
                            logging.info(f"✅ {stock_code} ({stock_name}): {period_months}개월 데이터로 성공")
                            return hist
                            
                    except Exception as e3:
                        continue
                        
            except Exception as e4:
                logging.error(f"❌ {stock_code} ({stock_name}): 짧은 기간 시도 실패: {e4}")
            
            logging.error(f"❌ {stock_code} ({stock_name}): 모든 PyKrx 방법 실패")
            return None
                    
        except Exception as e:
            logging.error(f"❌ {stock_code} ({stock_name}) PyKrx 데이터 조회 중 오류: {e}")
            return None
    
    def get_incremental_data_pykrx(self, stock_code, stock_name, start_date):
        """PyKrx를 사용한 증분 데이터 조회 (성능 최적화) - 거래대금 포함"""
        try:
            logging.info(f"🔄 {stock_code} ({stock_name}) PyKrx로 증분 데이터 조회 중... (시작일: {start_date}, 거래대금 포함)")
            
            # 종료일 (오늘)
            end_date = datetime.now()
            
            # PyKrx로 증분 데이터 조회 (거래대금 포함 - adjusted=False 옵션 사용)
            try:
                # 1차 시도: 개별 종목 조회
                # start_date가 문자열인 경우 datetime으로 변환
                if isinstance(start_date, str):
                    start_date_obj = datetime.strptime(start_date, '%Y%m%d')
                else:
                    start_date_obj = start_date
                
                hist = stock.get_market_ohlcv_by_date(
                    fromdate=start_date_obj.strftime('%Y%m%d'),
                    todate=end_date.strftime('%Y%m%d'),
                    ticker=stock_code,
                    adjusted=True  # 거래대금 포함을 위해 False로 설정
                )
                
                if not hist.empty:
                    # PyKrx 응답 구조에 맞춰 컬럼명 매핑 (거래대금 포함)
                    if len(hist.columns) == 7:
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Trading_Value', 'Change_Rate']
                        hist = hist.drop('Change_Rate', axis=1)
                    elif len(hist.columns) == 6:
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Change_Rate']
                        hist = hist.drop('Change_Rate', axis=1)
                        # 거래대금 계산 (거래량 × 종가)
                        hist['Trading_Value'] = hist['Volume'] * hist['Close']
                        logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                    elif len(hist.columns) == 5:
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        # 거래대금 계산 (거래량 × 종가)
                        hist['Trading_Value'] = hist['Volume'] * hist['Close']
                        logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                    else:
                        hist.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        # 거래대금 계산 (거래량 × 종가)
                        hist['Trading_Value'] = hist['Volume'] * hist['Close']
                        logging.info(f"📊 {stock_code}: 거래대금 계산 완료 (거래량 × 종가)")
                    
                    logging.info(f"✅ {stock_code} ({stock_name}): PyKrx로 {len(hist)}일의 증분 데이터 조회 완료")
                    logging.info(f"📅 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
                    return hist
                else:
                    logging.warning(f"⚠️ {stock_code} ({stock_name}): PyKrx에서 증분 데이터가 없습니다")
                    
            except Exception as e:
                logging.warning(f"⚠️ {stock_code} ({stock_name}): PyKrx 개별 종목 증분 조회 실패: {e}")
            
            # 2차 시도: 짧은 기간 (3개월)으로 재시도
            try:
                logging.info(f"🔄 {stock_code} ({stock_name}): 짧은 기간 (3개월)으로 재시도...")
                
                # 3개월 데이터로 재시도
                short_start = end_date - timedelta(days=90)
                market_data = stock.get_market_ohlcv_by_date(
                    fromdate=short_start.strftime('%Y%m%d'),
                    todate=end_date.strftime('%Y%m%d'),
                    ticker=stock_code,
                    adjusted=True
                )
                
                if not market_data.empty:
                    # PyKrx 응답 구조에 맞춰 컬럼명 매핑
                    if len(market_data.columns) == 7:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Trading_Value', 'Change_Rate']
                        market_data = market_data.drop('Change_Rate', axis=1)
                    elif len(market_data.columns) == 6:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Change_Rate']
                        market_data = market_data.drop('Change_Rate', axis=1)
                        market_data['Trading_Value'] = market_data['Volume'] * market_data['Close']
                    elif len(market_data.columns) == 5:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        market_data['Trading_Value'] = market_data['Volume'] * market_data['Close']
                    else:
                        market_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        market_data['Trading_Value'] = market_data['Volume'] * market_data['Close']
                    
                    logging.info(f"✅ {stock_code} ({stock_name}): 짧은 기간 데이터 조회 성공 (3개월)")
                    return market_data
                    
            except Exception as e2:
                logging.warning(f"⚠️ {stock_code} ({stock_name}): 짧은 기간 데이터 조회 실패: {e2}")
            
            logging.warning(f"⚠️ {stock_code} ({stock_name}): 모든 PyKrx 증분 데이터 조회 방법 실패")
            return None
                
        except Exception as e:
            logging.error(f"❌ {stock_code} ({stock_name}) PyKrx 증분 데이터 조회 실패: {e}")
            return None
    
    def get_stock_market_type(self, stock_code):
        """종목의 시장 구분 반환 (KOSPI/KOSDAQ) - 성능 최적화"""
        try:
            # 1차 시도: 데이터베이스에서 시장 구분 조회
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if self.db.is_connected():
                query = "SELECT market_type FROM stocks WHERE stock_code = %s"
                result = self.db.fetch_one(query, (stock_code,))
                # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
                
                if result and result['market_type']:
                    return result['market_type']
            
            # 2차 시도: 종목코드 패턴으로 추정 (빠른 방식)
            if stock_code.startswith('9'):
                return 'KOSDAQ'
            elif stock_code.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8')):
                return 'KOSPI'
            else:
                # 특수 종목코드의 경우 기본값
                return 'KOSPI'
                
        except Exception as e:
            logging.warning(f"⚠️ {stock_code} 시장 구분 조회 실패: {e}")
            # 기본값 반환 (안전한 방식)
            if stock_code.startswith('9'):
                return 'KOSDAQ'
            else:
                return 'KOSPI'
    
    def load_shares_cache_from_pykrx(self) -> bool:
        """PyKrx에서 전체 시장 유통주식수 데이터를 한 번에 로드하여 캐시에 저장"""
        try:
            if not PYKRX_AVAILABLE:
                logging.error("❌ PyKrx 라이브러리가 설치되지 않았습니다.")
                return False
            
            # 오늘 날짜
            today = datetime.now().strftime('%Y%m%d')
            
            # 캐시가 이미 오늘 날짜로 로드되어 있으면 재사용
            if self._shares_cache_date == today and self._shares_cache:
                logging.info(f"✅ 유통주식수 캐시가 이미 로드되어 있습니다. ({len(self._shares_cache)}개 종목)")
                return True
            
            logging.info(f"🚀 PyKrx에서 전체 시장 유통주식수 데이터 로드 중... (날짜: {today})")
            start_time = time.time()
            
            # PyKrx에서 전체 시장 데이터 한 번에 조회
            cap_data = stock.get_market_cap(today)
            
            if cap_data.empty:
                logging.error("❌ PyKrx에서 전체 시장 데이터를 가져올 수 없습니다.")
                return False
            
            # 캐시 초기화
            self._shares_cache = {}
            
            # 모든 종목의 유통주식수 데이터를 캐시에 저장
            for stock_code in cap_data.index:
                try:
                    row = cap_data.loc[stock_code]
                    total_shares = int(row.get('상장주식수', 0))
                    market_cap = float(row.get('시가총액', 0))
                    
                    if total_shares > 0:
                        self._shares_cache[stock_code] = {
                            'total_shares': total_shares,
                            'market_cap': market_cap
                        }
                except Exception as e:
                    logging.warning(f"⚠️ {stock_code} 캐시 저장 중 오류: {e}")
                    continue
            
            # 캐시 날짜 업데이트
            self._shares_cache_date = today
            
            load_time = time.time() - start_time
            logging.info(f"✅ 유통주식수 캐시 로드 완료! ({len(self._shares_cache)}개 종목, {load_time:.2f}초)")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ 유통주식수 캐시 로드 중 오류: {e}")
            return False
    
    def get_stock_shares_info_from_pykrx(self, stock_code: str, market_type: str) -> Optional[Dict[str, Any]]:
        """PyKrx에서 주식의 유통주식수 정보 조회 (배치 최적화 버전)"""
        try:
            if not PYKRX_AVAILABLE:
                logging.error("❌ PyKrx 라이브러리가 설치되지 않았습니다.")
                return None
            
            # 1차 시도: 캐시에서 조회 (가장 빠름)
            if stock_code in self._shares_cache:
                cache_data = self._shares_cache[stock_code]
                stock_data = {
                    'stock_code': stock_code,
                    'total_shares': cache_data['total_shares'],
                    'market_cap': cache_data['market_cap'],
                    'last_updated': datetime.now()
                }
                logging.debug(f"✅ {stock_code}: 캐시에서 유통주식수 {cache_data['total_shares']:,}주 조회")
                return stock_data
            
            # 2차 시도: 캐시가 비어있으면 전체 시장 데이터 로드
            if not self._shares_cache:
                logging.info(f"🔄 {stock_code}: 캐시가 비어있어 전체 시장 데이터 로드 중...")
                if not self.load_shares_cache_from_pykrx():
                    logging.warning(f"⚠️ {stock_code}: 전체 시장 데이터 로드 실패")
                    return None
                
                # 다시 캐시에서 조회 시도
                if stock_code in self._shares_cache:
                    cache_data = self._shares_cache[stock_code]
                    stock_data = {
                        'stock_code': stock_code,
                        'total_shares': cache_data['total_shares'],
                        'market_cap': cache_data['market_cap'],
                        'last_updated': datetime.now()
                    }
                    logging.debug(f"✅ {stock_code}: 전체 로드 후 캐시에서 유통주식수 {cache_data['total_shares']:,}주 조회")
                    return stock_data
            
            # 3차 시도: 개별 조회 (fallback)
            logging.warning(f"⚠️ {stock_code}: 캐시에 없어 개별 조회 시도...")
            return self._get_stock_shares_info_individual(stock_code, market_type)
                
        except Exception as e:
            logging.error(f"❌ {stock_code} PyKrx 유통주식수 조회 중 오류: {e}")
            return None
    
    def _get_stock_shares_info_individual(self, stock_code: str, market_type: str) -> Optional[Dict[str, Any]]:
        """개별 종목 유통주식수 조회 (fallback용)"""
        try:
            logging.debug(f"🔍 {stock_code} ({market_type}) PyKrx로 개별 유통주식수 조회 중...")
            
            # 오늘 날짜
            today = datetime.now().strftime('%Y%m%d')
            
            # 1차 시도: 지정된 시장에서 조회
            try:
                cap_data = stock.get_market_cap(today)
                
                if not cap_data.empty and stock_code in cap_data.index:
                    row = cap_data.loc[stock_code]
                    
                    total_shares = int(row.get('상장주식수', 0))
                    market_cap = float(row.get('시가총액', 0))
                    
                    if total_shares > 0:
                        stock_data = {
                            'stock_code': stock_code,
                            'total_shares': total_shares,
                            'market_cap': market_cap,
                            'last_updated': datetime.now()
                        }
                        
                        logging.debug(f"✅ {stock_code}: 개별 조회로 유통주식수 {total_shares:,}주, 시가총액 {market_cap:,}")
                        return stock_data
                    else:
                        logging.warning(f"⚠️ {stock_code}: PyKrx에서 유통주식수가 0입니다")
                        
            except Exception as e:
                logging.warning(f"⚠️ {stock_code}: 개별 조회 실패: {e}")
            
            logging.warning(f"⚠️ {stock_code}: 모든 개별 조회 방법 실패")
            return None
                
        except Exception as e:
            logging.error(f"❌ {stock_code} 개별 유통주식수 조회 중 오류: {e}")
            return None
    
    def get_past_data_for_indicators(self, stock_code, days=120):
        """기술적 지표 계산을 위해 DB에서 과거 데이터 조회"""
        try:
            query = """
            SELECT trade_date, open, high, low, close, volume
            FROM daily_data
            WHERE stock_code = %s
            ORDER BY trade_date DESC
            LIMIT %s
            """
            
            result = self.db.fetch_all(query, (stock_code, days))
            
            if result and len(result) > 0:
                df = pd.DataFrame(result)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df.set_index('trade_date', inplace=True)
                df = df.sort_index()  # 오름차순 정렬 (오래된 것부터)
                
                # 컬럼명 변경
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                
                # Decimal 타입을 float로 변환
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = df[col].astype(float)
                
                return df
            else:
                return None
                
        except Exception as e:
            logging.error(f"❌ {stock_code} 과거 데이터 조회 중 오류: {e}")
            return None
    
    def save_daily_data(self, stock_code, hist_data):
        """일봉 데이터와 유통주식수, 시가총액을 함께 데이터베이스에 저장"""
        try:
            if hist_data is None:
                logging.warning(f"⚠️ {stock_code} hist_data가 None입니다")
                return False
            if hist_data.empty:
                logging.warning(f"⚠️ {stock_code} hist_data가 비어있습니다")
                return False
            
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    return False
            
            # 유통주식수 정보 조회 (PyKrx에서)
            shares_info = self.get_stock_shares_info_from_pykrx(stock_code, "")
            total_shares = shares_info.get('total_shares', 0) if shares_info else 0
            market_cap = shares_info.get('market_cap', 0) if shares_info else 0
            
            # 일봉 데이터 삽입 (거래대금 포함)
            daily_insert_sql = """
            INSERT INTO daily_data 
            (stock_code, trade_date, open, high, low, close, volume, trading_value, outstanding_shares, market_cap)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open = VALUES(open), high = VALUES(high), low = VALUES(low), 
            close = VALUES(close), volume = VALUES(volume), trading_value = VALUES(trading_value),
            outstanding_shares = VALUES(outstanding_shares), market_cap = VALUES(market_cap),
            updated_at = CURRENT_TIMESTAMP
            """
            
            daily_data = []
            logging.info(f"📊 {stock_code} 데이터 처리 시작: {len(hist_data)}행")
            
            for date, row in hist_data.iterrows():
                # NaN 값 처리
                open_price = row['Open'] if pd.notna(row['Open']) else None
                high_price = row['High'] if pd.notna(row['High']) else None
                low_price = row['Low'] if pd.notna(row['Low']) else None
                close_price = row['Close'] if pd.notna(row['Close']) else None
                volume = row['Volume'] if pd.notna(row['Volume']) else 0
                trading_value = row['Trading_Value'] if pd.notna(row['Trading_Value']) else None
                
                # None 값이 있으면 해당 행 건너뛰기
                if open_price is None or high_price is None or low_price is None or close_price is None:
                    logging.warning(f"⚠️ {stock_code} {date.strftime('%Y-%m-%d')}: NaN 값이 있어 건너뜀")
                    continue
                
                # 거래대금이 없으면 계산 (Typical Price 방식: (H+L+C)/3 × V)
                if trading_value is None and close_price and volume and high_price and low_price:
                    typical_price = (high_price + low_price + close_price) / 3
                    trading_value = int(volume * typical_price)
                    logging.info(f"📊 {stock_code} {date.strftime('%Y-%m-%d')}: 거래대금 계산 완료 (Typical Price 방식: {trading_value:,}원)")
                elif trading_value is None and close_price and volume:
                    # Typical Price 계산이 불가능한 경우에만 Close Price 사용
                    trading_value = int(volume * close_price)
                    logging.info(f"📊 {stock_code} {date.strftime('%Y-%m-%d')}: 거래대금 계산 완료 (Close Price 방식: {trading_value:,}원)")
                
                # 유통주식수와 시가총액 검증 및 보정
                if total_shares and total_shares > 0:
                    # 시가총액이 0이면 종가로 계산
                    if market_cap == 0 and close_price:
                        market_cap = float(close_price) * total_shares
                        logging.info(f"📊 {stock_code} {date.strftime('%Y-%m-%d')}: 시가총액 계산 완료 ({market_cap:,.0f})")
                    
                    # 데이터 유효성 검증
                    if market_cap > 0 and close_price:
                        calculated_shares = market_cap / float(close_price)
                        if abs(calculated_shares - total_shares) / total_shares > 0.1:  # 10% 이상 차이나면 경고
                            logging.warning(f"⚠️ {stock_code} {date.strftime('%Y-%m-%d')}: 유통주식수와 시가총액 불일치 의심 (계산값: {calculated_shares:,.0f}주)")
                else:
                    # 유통주식수가 0이거나 None이면 None으로 설정
                    total_shares = None
                    market_cap = None
                    logging.warning(f"⚠️ {stock_code} {date.strftime('%Y-%m-%d')}: 유통주식수 정보 없음")
                
                daily_data.append((
                    stock_code,
                    date.strftime('%Y-%m-%d'),
                    float(open_price),
                    float(high_price),
                    float(low_price),
                    float(close_price),
                    int(volume),
                    int(trading_value) if trading_value else None,
                    total_shares,
                    market_cap
                ))
            
            if daily_data:
                logging.info(f"📊 {stock_code} 저장할 데이터: {len(daily_data)}개")
                for i, data in enumerate(daily_data[:3]):  # 처음 3개만 로그 출력
                    logging.info(f"  데이터 {i+1}: {data}")
                
                if self.db.execute_many(daily_insert_sql, daily_data):
                    logging.info(f"✅ {stock_code} 일봉 데이터 {len(daily_data)}개 저장 완료")
                    
                    # 유통주식수 정보가 있으면 stock_shares_history에도 저장
                    if shares_info and total_shares > 0:
                        self.update_stock_shares_history_direct(stock_code, total_shares, market_cap)
                        logging.info(f"✅ {stock_code} 유통주식수 정보 저장 완료: {total_shares:,}주, 시가총액 {market_cap:,}")
                    
                    # 기술적 지표 계산 및 저장
                    # 증분 수집 시 충분한 데이터 확보를 위해 DB에서 과거 데이터 조회
                    if len(hist_data) < 120:
                        logging.info(f"🔧 {stock_code} 기술적 지표 계산을 위해 DB에서 과거 120일 데이터 조회 중...")
                        past_data = self.get_past_data_for_indicators(stock_code, 120)
                        if past_data is not None and not past_data.empty:
                            # 과거 데이터와 새 데이터 합치기 (중복 제거)
                            combined_data = pd.concat([past_data, hist_data])
                            combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
                            combined_data = combined_data.sort_index()
                            logging.info(f"✅ {stock_code} 과거 데이터 {len(past_data)}일 + 새 데이터 {len(hist_data)}일 = 총 {len(combined_data)}일")
                            df_with_indicators = self.calculate_technical_indicators(combined_data.copy())
                            # 새로운 데이터의 지표만 저장 (hist_data의 날짜에 해당하는 것만)
                            new_dates = hist_data.index
                            df_to_save = df_with_indicators.loc[df_with_indicators.index.isin(new_dates)]
                            self.save_technical_indicators(stock_code, df_to_save)
                        else:
                            logging.warning(f"⚠️ {stock_code} 과거 데이터 조회 실패, 현재 데이터만으로 계산")
                            df_with_indicators = self.calculate_technical_indicators(hist_data.copy())
                            self.save_technical_indicators(stock_code, df_with_indicators)
                    else:
                        # 이미 충분한 데이터가 있으면 그대로 계산
                        df_with_indicators = self.calculate_technical_indicators(hist_data.copy())
                        self.save_technical_indicators(stock_code, df_with_indicators)
                    
                    # 수집 상태 업데이트
                    self.update_collection_status(stock_code, hist_data)
                    
                    return True
                else:
                    logging.error(f"❌ {stock_code} 일봉 데이터 저장 실패 - execute_many 반환값이 False")
                    return False
            else:
                logging.warning(f"⚠️ {stock_code} 저장할 데이터가 없습니다")
                return False
                
        except Exception as e:
            logging.error(f"{stock_code} 일봉 데이터 저장 중 오류: {e}")
            return False
        finally:
            # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
            pass
    
    def save_technical_indicators(self, stock_code, df_with_indicators):
        """기술적 지표를 데이터베이스에 저장"""
        try:
            technical_insert_sql = """
            INSERT INTO technical_indicators 
            (stock_code, trade_date, ma5, ma20, ma60, ma120, rsi, macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            ma5 = VALUES(ma5), ma20 = VALUES(ma20), ma60 = VALUES(ma60), ma120 = VALUES(ma120),
            rsi = VALUES(rsi), macd = VALUES(macd), macd_signal = VALUES(macd_signal), macd_histogram = VALUES(macd_histogram),
            bb_upper = VALUES(bb_upper), bb_middle = VALUES(bb_middle), bb_lower = VALUES(bb_lower),
            updated_at = CURRENT_TIMESTAMP
            """
            
            technical_data = []
            for date, row in df_with_indicators.iterrows():
                # NaN 값 처리
                ma5 = row['MA5'] if pd.notna(row['MA5']) else None
                ma20 = row['MA20'] if pd.notna(row['MA20']) else None
                ma60 = row['MA60'] if pd.notna(row['MA60']) else None
                ma120 = row['MA120'] if pd.notna(row['MA120']) else None
                rsi = row['RSI'] if pd.notna(row['RSI']) else None
                macd = row['MACD'] if pd.notna(row['MACD']) else None
                macd_signal = row['MACD_Signal'] if pd.notna(row['MACD_Signal']) else None
                macd_histogram = row['MACD_Histogram'] if pd.notna(row['MACD_Histogram']) else None
                bb_upper = row['BB_Upper'] if pd.notna(row['BB_Upper']) else None
                bb_middle = row['BB_Middle'] if pd.notna(row['BB_Middle']) else None
                bb_lower = row['BB_Lower'] if pd.notna(row['BB_Lower']) else None
                
                technical_data.append((
                    stock_code,
                    date.strftime('%Y-%m-%d'),
                    ma5, ma20, ma60, ma120,
                    rsi,
                    macd, macd_signal, macd_histogram,
                    bb_upper, bb_middle, bb_lower
                ))
            
            if self.db.execute_many(technical_insert_sql, technical_data):
                logging.info(f"✅ {stock_code} 기술적 지표 {len(technical_data)}개 저장 완료")
                return True
            else:
                logging.error(f"❌ {stock_code} 기술적 지표 저장 실패")
                return False
                
        except Exception as e:
            logging.error(f"{stock_code} 기술적 지표 저장 중 오류: {e}")
            return False
    
    def update_collection_status(self, stock_code, hist_data):
        """종목별 수집 상태 업데이트"""
        try:
            status_insert_sql = """
            INSERT INTO stock_collection_status 
            (stock_code, last_collected_date, last_collected_timestamp, last_collected_close, last_collected_volume, 
             data_start_date, data_end_date, total_records, collection_quality)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            last_collected_date = VALUES(last_collected_date),
            last_collected_timestamp = VALUES(last_collected_timestamp),
            last_collected_close = VALUES(last_collected_close),
            last_collected_volume = VALUES(last_collected_volume),
            data_start_date = VALUES(data_start_date),
            data_end_date = VALUES(data_end_date),
            total_records = VALUES(total_records),
            collection_quality = VALUES(collection_quality)
            """
            
            last_date = hist_data.index[-1]
            first_date = hist_data.index[0]
            last_row = hist_data.iloc[-1]
            
            # 현재 시간을 수집 시간으로 기록
            current_timestamp = datetime.now()
            
            # 데이터 품질 판단 (현재 시간 기준으로 장중/장마감 구분)
            current_time = current_timestamp.time()
            from datetime import time
            market_open = time(9, 0)
            market_close = time(15, 30)
            
            if market_open <= current_time <= market_close:
                collection_quality = 'INTRADAY'  # 장중 데이터
            else:
                collection_quality = 'CLOSING'   # 장 마감 후 데이터
            
            status_data = (
                stock_code,
                last_date.strftime('%Y-%m-%d'),
                current_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                float(last_row['Close']),
                int(last_row['Volume']),
                first_date.strftime('%Y-%m-%d'),
                last_date.strftime('%Y-%m-%d'),
                len(hist_data),
                collection_quality
            )
            
            if self.db.execute_query(status_insert_sql, status_data):
                logging.info(f"✅ {stock_code} 수집 상태 업데이트 완료 (품질: {collection_quality})")
                return True
            else:
                logging.error(f"❌ {stock_code} 수집 상태 업데이트 실패")
                return False
                
        except Exception as e:
            logging.error(f"{stock_code} 수집 상태 업데이트 중 오류: {e}")
            return False

    def process_single_stock(self, stock_info):
        """단일 종목 처리 (병렬 처리용) - 스마트 재시도 + 다중 소스 폴백"""
        stock_code, stock_name = stock_info
        max_retries = self.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # 지수적 백오프: 1초 → 2초 → 4초 → 8초 → 16초 → 32초 → 60초
                    wait_time = min(2 ** attempt, 60)
                    jitter = random.uniform(0, wait_time * 0.2)  # 지터 추가
                    total_wait = wait_time + jitter
                    
                    logging.info(f"🔄 {stock_code} ({stock_name}) 재시도 {attempt}/{max_retries} ({total_wait:.1f}초 대기)...")
                    time.sleep(total_wait)
                
                logging.info(f"📊 {stock_code} ({stock_name}) 처리 중... (시도 {attempt + 1}/{max_retries + 1})")
                
                # 통합 수집 메서드 사용 (일봉 데이터 + 유통주식수)
                if self.collect_stock_data_with_shares(stock_code, stock_name):
                    logging.info(f"✅ {stock_code} ({stock_name}) 데이터 수집 완료")
                    if attempt > 0:
                        logging.info(f"💡 재시도로 성공: {attempt}회 시도")
                    return True, stock_code
                else:
                    logging.error(f"❌ {stock_code} ({stock_name}) 수집 실패")
                    if attempt < max_retries:
                        continue  # 재시도
                    return False, stock_code
                    
            except Exception as e:
                error_msg = str(e)
                logging.error(f"❌ {stock_code} ({stock_name}) 처리 중 오류 (시도 {attempt + 1}): {e}")
                
                # 스마트 재시도: 오류 유형 분석 및 대응
                if attempt < max_retries:
                    action, delay = self._analyze_and_adapt_error(stock_code, error_msg)
                    
                    if action == 'skip':
                        logging.info(f"⏭️ {stock_code} 건너뛰기 (상장폐지)")
                        return False, stock_code
                    elif action in ['retry_immediate', 'retry_short', 'retry_long']:
                        time.sleep(delay)
                        continue
                    elif action == 'try_alternative':
                        # 대체 소스 시도
                        if self._try_alternative_sources(stock_code, stock_name):
                            logging.info(f"✅ {stock_code} 대체 소스로 수집 완료")
                            return True, stock_code
                        continue
                
                if attempt >= max_retries:
                    return False, stock_code
            finally:
                # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
                pass
        
        # 모든 재시도 실패
        logging.error(f"❌ {stock_code} ({stock_name}): 최대 재시도 횟수 초과")
        return False, stock_code
    
    def _analyze_and_adapt_error(self, stock_code, error_msg):
        """오류 분석 및 자동 대응 전략 결정"""
        error_lower = error_msg.lower()
        
        # 네트워크 오류 → 즉시 재시도
        if any(keyword in error_lower for keyword in ['network', 'timeout', 'connection']):
            logging.info(f"🔍 {stock_code}: 네트워크 오류 감지 → 즉시 재시도")
            return 'retry_immediate', 2
        
        # API 제한 → 긴 대기 후 재시도
        elif any(keyword in error_lower for keyword in ['rate limit', '429', 'too many']):
            logging.warning(f"⚠️ {stock_code}: API 제한 감지 → 60초 대기")
            self.delay_between_requests = min(self.delay_between_requests * 1.5, 0.15)
            return 'retry_long', 60
        
        # 데이터 없음 → 대체 소스 시도
        elif any(keyword in error_lower for keyword in ['404', 'not found', 'no data']):
            logging.info(f"🔍 {stock_code}: 데이터 없음 → 대체 소스 시도")
            return 'try_alternative', 0
        
        # 상장폐지 → 건너뛰기
        elif any(keyword in error_lower for keyword in ['delisted', '상장폐지', '거래정지']):
            logging.info(f"ℹ️ {stock_code}: 상장폐지 종목")
            return 'skip', 0
        
        # API 오류 → 대기 후 재시도
        elif any(keyword in error_lower for keyword in ['api error', '500', '503']):
            logging.warning(f"⚠️ {stock_code}: API 오류 → 30초 대기")
            return 'retry_long', 30
        
        # 일시적 오류 → 짧은 대기 후 재시도
        elif any(keyword in error_lower for keyword in ['temporary', 'retry']):
            logging.info(f"🔍 {stock_code}: 일시적 오류 → 5초 대기")
            return 'retry_short', 5
        
        # 기타 오류 → 일반 재시도
        else:
            logging.info(f"🔍 {stock_code}: 일반 오류 → 5초 대기")
            return 'retry_short', 5
    
    def _try_alternative_sources(self, stock_code, stock_name):
        """다중 소스 폴백: PyKrx 실패 시 대체 소스 시도"""
        try:
            # 1순위: FinanceDataReader 시도
            try:
                logging.info(f"📊 {stock_code}: FinanceDataReader 시도...")
                import FinanceDataReader as fdr
                from datetime import timedelta
                
                data = fdr.DataReader(stock_code, datetime.now() - timedelta(days=3650))
                if data is not None and not data.empty:
                    # 컬럼명 통일 및 거래대금 계산
                    if 'Close' in data.columns:
                        data['Trading_Value'] = data.get('Volume', 0) * data['Close']
                        # 데이터 저장
                        if self.save_daily_data(stock_code, data):
                            logging.info(f"✅ {stock_code}: FinanceDataReader 성공!")
                            return True
            except Exception as e:
                logging.debug(f"FinanceDataReader 실패: {e}")
            
            # 2순위: Yahoo Finance 시도
            try:
                logging.info(f"📊 {stock_code}: Yahoo Finance 시도...")
                import yfinance as yf
                
                for ticker in [f"{stock_code}.KS", f"{stock_code}.KQ"]:
                    try:
                        data = yf.download(ticker, period="10y", progress=False)
                        if data is not None and not data.empty:
                            data['Trading_Value'] = data.get('Volume', 0) * data['Close']
                            # 데이터 저장
                            if self.save_daily_data(stock_code, data):
                                logging.info(f"✅ {stock_code}: Yahoo Finance 성공! ({ticker})")
                                return True
                    except:
                        continue
            except Exception as e:
                logging.debug(f"Yahoo Finance 실패: {e}")
            
            return False
            
        except Exception as e:
            logging.error(f"❌ {stock_code}: 대체 소스 시도 중 오류: {e}")
            return False

    def process_batch_parallel(self, stock_batch, batch_num, total_batches):
        """배치 단위로 종목을 병렬 처리"""
        logging.info(f"🚀 배치 {batch_num}/{total_batches} 시작 ({len(stock_batch)}개 종목)")
        logging.info("="*60)
        
        success_count = 0
        failed_count = 0
        
        # 병렬 처리로 종목 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 종목을 동시에 제출
            future_to_stock = {executor.submit(self.process_single_stock, stock_info): stock_info for stock_info in stock_batch}
            
            # 결과 수집
            for future in concurrent.futures.as_completed(future_to_stock):
                stock_info = future_to_stock[future]
                try:
                    success, stock_code = future.result()
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logging.error(f"{stock_info[0]} 처리 중 예외 발생: {e}")
                    failed_count += 1
                
                # API 제한 방지를 위한 짧은 딜레이
                time.sleep(self.delay_between_requests + random.uniform(0.1, 0.5))
        
        logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
        logging.info(f"✅ 성공: {success_count}개, ❌ 실패: {failed_count}개")
        logging.info("="*60)
        
        return success_count, failed_count
    
    def process_batch(self, stock_batch, batch_num, total_batches):
        """배치 단위로 종목 처리 (기존 순차 처리 방식)"""
        logging.info(f"🚀 배치 {batch_num}/{total_batches} 시작 ({len(stock_batch)}개 종목)")
        logging.info("="*60)
        
        success_count = 0
        failed_count = 0
        
        for i, (stock_code, stock_name) in enumerate(stock_batch, 1):
            logging.info(f"📊 [{i}/{len(stock_batch)}] {stock_code} ({stock_name}) 처리 중...")
            
            try:
                # 데이터 조회
                hist_data = self.get_stock_data(stock_code, stock_name)
                
                if hist_data is not None:
                    # 데이터베이스에 저장
                    if self.save_daily_data(stock_code, hist_data):
                        logging.info(f"✅ {stock_code} ({stock_name}) 데이터 수집 완료")
                        success_count += 1
                    else:
                        logging.error(f"❌ {stock_code} ({stock_name}) 데이터베이스 저장 실패")
                        failed_count += 1
                elif hist_data is None:
                    # 이미 최신 데이터이거나 데이터가 없는 경우
                    logging.info(f"✅ {stock_code} ({stock_name}) 이미 최신 데이터이거나 수집할 데이터가 없습니다.")
                    success_count += 1
                else:
                    logging.warning(f"❌ {stock_code} ({stock_name}) 데이터 조회 실패")
                    failed_count += 1
                
                # API 호출 간격 조절 (랜덤 딜레이로 API 제한 방지)
                delay = self.delay_between_requests + random.uniform(0.01, 0.03)
                time.sleep(delay)
                
            except Exception as e:
                logging.error(f"{stock_code} ({stock_name}) 처리 중 오류: {e}")
                failed_count += 1
                
                # API 제한 감지 시 더 긴 딜레이
                if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                    logging.warning("⚠️ API 제한 감지! 30초 대기 후 계속...")
                    time.sleep(30)
        
        logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
        logging.info(f"✅ 성공: {success_count}개, ❌ 실패: {failed_count}개")
        logging.info("="*60)
        
        return success_count, failed_count
    
    def process_batch_optimized(self, stock_batch, batch_num, total_batches):
        """배치 단위로 종목 처리 (DB 연결 최적화 버전) - 오류 처리 강화"""
        logging.info(f"🚀 배치 {batch_num}/{total_batches} 시작 ({len(stock_batch)}개 종목) - 최적화 모드")
        logging.info("="*60)
        
        # 배치 시작 시 DB 연결 한 번만 (재시도 로직 포함)
        max_db_retries = 3
        db_connected = False
        for db_attempt in range(max_db_retries):
            try:
                if self.db.connect():
                    db_connected = True
                    break
                else:
                    logging.warning(f"⚠️ 배치 {batch_num} DB 연결 시도 {db_attempt + 1}/{max_db_retries} 실패")
                    if db_attempt < max_db_retries - 1:
                        time.sleep(2)  # 2초 대기 후 재시도
                    else:
                        logging.error(f"❌ 배치 {batch_num} DB 연결 최대 재시도 횟수 초과")
                        return 0, len(stock_batch)
            except Exception as e:
                logging.error(f"❌ 배치 {batch_num} DB 연결 중 오류: {e}")
                if db_attempt < max_db_retries - 1:
                    time.sleep(2)
                else:
                    return 0, len(stock_batch)
        
        if not db_connected:
            logging.error(f"❌ 배치 {batch_num} DB 연결 실패")
            return 0, len(stock_batch)
        
        # 🚀 유통주식수 캐시 미리 로드 (배치 최적화)
        if batch_num == 1:  # 첫 번째 배치에서만 캐시 로드
            logging.info(f"🚀 배치 {batch_num}: 유통주식수 캐시 미리 로드 중...")
            if self.load_shares_cache_from_pykrx():
                logging.info(f"✅ 배치 {batch_num}: 유통주식수 캐시 로드 완료! (이제 모든 종목이 0.1초 내에 조회됩니다)")
            else:
                logging.warning(f"⚠️ 배치 {batch_num}: 유통주식수 캐시 로드 실패 - 개별 조회로 fallback")
        
        try:
            logging.info(f"🔄 배치 {batch_num} 처리 시작 - 전체 try-catch 블록 진입")
            success_count = 0
            failed_count = 0
            skipped_count = 0  # 건너뛴 종목 카운트 추가
            
            # 배치 내 모든 종목의 마지막 수집 날짜를 한 번에 조회
            stock_codes = [stock[0] for stock in stock_batch]
            batch_last_dates = self.get_batch_last_collected_dates(stock_codes)
            
            # 배치 내 모든 종목 데이터를 수집
            batch_daily_data = []
            batch_technical_data = []
            batch_status_data = []
            
            logging.info(f"🔄 배치 {batch_num} 종목 처리 루프 시작 - {len(stock_batch)}개 종목 처리 예정")
            
            for i, (stock_code, stock_name) in enumerate(stock_batch, 1):
                # 10개 종목마다만 상세 로그 출력
                if i % 10 == 0 or i == 1:
                    logging.info(f"🔄 배치 {batch_num} [{i}/{len(stock_batch)}] 처리 중 - 현재 종목: {stock_code} ({stock_name})")
                else:
                    logging.debug(f"📊 [{i}/{len(stock_batch)}] {stock_code} ({stock_name}) 데이터 수집 중...")
                
                try:
                    # 상장폐지/비활성 종목 체크 (간단한 필터링)
                    if self._is_likely_delisted(stock_code, stock_name):
                        logging.warning(f"⚠️ {stock_code} ({stock_name}): 상장폐지/비활성 의심 종목으로 건너뜀")
                        skipped_count += 1
                        continue
                    
                    # 배치로 조회한 마지막 수집 날짜 사용
                    last_collected_date = batch_last_dates.get(stock_code)
                    
                    # 데이터 조회 (마지막 수집 날짜 정보 전달)
                    hist_data = self.get_stock_data_with_last_date(stock_code, stock_name, last_collected_date)
                    
                    if hist_data is not None and not hist_data.empty:
                        # 데이터 준비 (저장하지 않고 메모리에 보관)
                        daily_data, technical_data, status_data = self.prepare_stock_data(stock_code, hist_data)
                        
                        if daily_data and len(daily_data) > 0:
                            batch_daily_data.extend(daily_data)
                            batch_technical_data.extend(technical_data)
                            batch_status_data.append(status_data)
                            success_count += 1
                            # 10개 종목마다만 성공 로그 출력
                            if i % 10 == 0 or i == 1:
                                logging.info(f"✅ {stock_code} ({stock_name}) 데이터 준비 완료 ({len(daily_data)}일)")
                            else:
                                logging.debug(f"✅ {stock_code} ({stock_name}) 데이터 준비 완료 ({len(daily_data)}일)")
                            
                            # 유통주식수는 save_daily_data에서 이미 통합 처리됨 (중복 로직 제거)
                        else:
                            failed_count += 1
                            logging.error(f"❌ {stock_code} ({stock_name}) 데이터 준비 실패 (빈 데이터)")
                    elif hist_data is None:
                        # 이미 최신 데이터이거나 데이터가 없는 경우 - 즉시 건너뛰기 (딜레이 없음)
                        if i % 10 == 0 or i == 1:
                            logging.info(f"✅ {stock_code} ({stock_name}) 이미 최신 데이터이거나 수집할 데이터가 없습니다. (즉시 건너뛰기)")
                        else:
                            logging.debug(f"✅ {stock_code} ({stock_name}) 이미 최신 데이터 (즉시 건너뛰기)")
                        success_count += 1
                        continue  # 즉시 다음 종목으로 (time.sleep 없음)
                    else:
                        logging.warning(f"❌ {stock_code} ({stock_name}) 데이터 조회 실패")
                        failed_count += 1
                    
                    # API 호출 간격 조절 (랜덤 딜레이로 API 제한 방지)
                    delay = self.delay_between_requests + random.uniform(0.01, 0.03)
                    time.sleep(delay)
                    
                    # DB 연결 상태 주기적 확인 (10개 종목마다)
                    if i % 10 == 0:
                        if self.db.is_connected():
                            logging.info(f"✅ 배치 {batch_num} [{i}/{len(stock_batch)}] DB 연결 상태 정상")
                        else:
                            logging.warning(f"⚠️ 배치 {batch_num} [{i}/{len(stock_batch)}] DB 연결 끊어짐 감지")
                    
                except Exception as e:
                    logging.error(f"❌ {stock_code} ({stock_name}) 처리 중 오류: {e}")
                    failed_count += 1
                    
                    # API 제한 감지 시 더 긴 딜레이
                    if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                        logging.warning("⚠️ API 제한 감지! 30초 대기 후 계속...")
                        time.sleep(30)
                    elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                        logging.warning("⚠️ 연결 오류 감지! 10초 대기 후 계속...")
                        time.sleep(10)
            
            # 배치 처리 루프 완료 로깅
            logging.info(f"🔄 배치 {batch_num} 종목 처리 루프 완료 - 저장 단계로 진행")
            logging.info(f"🔄 배치 {batch_num} 배치 데이터 현황:")
            logging.info(f"   📊 일봉 데이터: {len(batch_daily_data)}개")
            logging.info(f"   📊 기술적 지표: {len(batch_technical_data)}개")
            logging.info(f"   📊 수집 상태: {len(batch_status_data)}개")
            logging.info(f"   📊 성공: {success_count}개, 실패: {failed_count}개, 건너뜀: {skipped_count}개")
            
            # 배치 단위로 데이터베이스에 저장 (오류 처리 강화)
            logging.info(f"💾 배치 {batch_num} 데이터베이스 저장 시작...")
            logging.info(f"💾 배치 {batch_num} 저장 전 DB 연결 상태 확인 중...")
            
            # DB 연결 상태 재확인
            if not self.db.is_connected():
                logging.warning(f"⚠️ 배치 {batch_num} 저장 전 DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    logging.error(f"❌ 배치 {batch_num} 저장 전 DB 재연결 실패")
                    return 0, len(stock_batch)
                else:
                    logging.info(f"✅ 배치 {batch_num} 저장 전 DB 재연결 성공")
            else:
                logging.info(f"✅ 배치 {batch_num} 저장 전 DB 연결 상태 정상")
            
            if batch_daily_data:
                try:
                    logging.info(f"💾 배치 {batch_num} 일봉 데이터 저장 시작... ({len(batch_daily_data)}개)")
                    logging.info(f"💾 배치 {batch_num} 저장할 데이터 샘플: {batch_daily_data[0] if batch_daily_data else 'None'}")
                    
                    save_result = self.save_batch_daily_data(batch_daily_data)
                    logging.info(f"💾 배치 {batch_num} save_batch_daily_data 결과: {save_result}")
                    
                    if save_result:
                        logging.info(f"✅ 배치 {batch_num} 일봉 데이터 {len(batch_daily_data)}개 저장 완료")
                    else:
                        logging.error(f"❌ 배치 {batch_num} 일봉 데이터 저장 실패")
                        # 저장 실패 시 성공 카운트 조정
                        failed_count += len(batch_daily_data)
                        success_count -= len(batch_daily_data)
                except Exception as e:
                    logging.error(f"❌ 배치 {batch_num} 일봉 데이터 저장 중 예외 발생: {e}")
                    import traceback
                    logging.error(f"❌ 배치 {batch_num} 상세 오류: {traceback.format_exc()}")
                    failed_count += len(batch_daily_data)
                    success_count -= len(batch_daily_data)
            else:
                logging.warning(f"⚠️ 배치 {batch_num}: 저장할 일봉 데이터가 없습니다.")
            
            if batch_technical_data:
                try:
                    logging.info(f"💾 기술적 지표 저장 중... ({len(batch_technical_data)}개)")
                    if self.save_batch_technical_indicators(batch_technical_data):
                        logging.info(f"✅ 배치 {batch_num} 기술적 지표 {len(batch_technical_data)}개 저장 완료")
                    else:
                        logging.error(f"❌ 배치 {batch_num} 기술적 지표 저장 실패")
                except Exception as e:
                    logging.error(f"❌ 배치 {batch_num} 기술적 지표 저장 중 예외 발생: {e}")
            
            if batch_status_data:
                try:
                    logging.info(f"💾 수집 상태 업데이트 중... ({len(batch_status_data)}개)")
                    if self.save_batch_collection_status(batch_status_data):
                        logging.info(f"✅ 배치 {batch_num} 수집 상태 {len(batch_status_data)}개 업데이트 완료")
                    else:
                        logging.error(f"❌ 배치 {batch_num} 수집 상태 업데이트 실패")
                except Exception as e:
                    logging.error(f"❌ 배치 {batch_num} 수집 상태 업데이트 중 예외 발생: {e}")
            
            logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
            logging.info(f"✅ 성공: {success_count}개, ❌ 실패: {failed_count}개, ⏭️ 건너뜀: {skipped_count}개")
            logging.info("="*60)
            
            # 마지막 배치에서만 기술지표 검증 실행
            if batch_num == total_batches and success_count > 0:
                logging.info("\n🔍 마지막 배치 완료 - 기술지표 검증 및 수정 시작...")
                validation_success = self.validate_and_fix_technical_indicators()
                if validation_success:
                    logging.info("✅ 기술지표 검증 및 수정 완료")
                else:
                    logging.warning("⚠️ 기술지표 검증 및 수정에 문제가 있습니다. 로그를 확인해주세요.")
            
            # 진행률 및 통계 업데이트 콜백 호출 (DB 연결 없이)
            try:
                # 전체 진행률 업데이트 (실제 데이터로 계산)
                if hasattr(self, 'progress_callback') and self.progress_callback:
                    # 전체 처리된 종목 수 계산
                    total_processed = (batch_num - 1) * self.batch_size + success_count + failed_count + skipped_count
                    # 전체 종목 수는 배치 크기와 총 배치 수로 계산
                    total_stocks = total_batches * self.batch_size
                    self.update_progress(total_stocks, total_processed, batch_num, total_batches)
                
                # 통계 업데이트
                if hasattr(self, 'stats_callback') and self.stats_callback:
                    self.update_stats(success_count, failed_count, skipped_count)
            except Exception as e:
                logging.warning(f"⚠️ 진행률 업데이트 콜백 실행 중 오류: {e}")
            
            return success_count, failed_count
            
        except Exception as e:
            logging.error(f"❌ 배치 {batch_num} 처리 중 예상치 못한 오류: {e}")
            return 0, len(stock_batch)
        finally:
            # 배치 끝에 DB 연결 해제 (안전하게)
            try:
                self.db.disconnect()
            except Exception as e:
                logging.warning(f"⚠️ 배치 {batch_num} DB 연결 해제 중 오류: {e}")
    
    def prepare_stock_data(self, stock_code, hist_data):
        """종목 데이터를 저장용으로 준비 (메모리에 보관) - 유통주식수 통합"""
        try:
            if hist_data is None or hist_data.empty:
                return [], [], None
            
            # 유통주식수 정보 조회 (PyKrx에서)
            shares_info = self.get_stock_shares_info_from_pykrx(stock_code, "")
            total_shares = shares_info.get('total_shares', 0) if shares_info else 0
            market_cap = shares_info.get('market_cap', 0) if shares_info else 0
            
            # 일봉 데이터 준비
            daily_data = []
            for date, row in hist_data.iterrows():
                # NaN 값 처리
                open_price = row['Open'] if pd.notna(row['Open']) else None
                high_price = row['High'] if pd.notna(row['High']) else None
                low_price = row['Low'] if pd.notna(row['Low']) else None
                close_price = row['Close'] if pd.notna(row['Close']) else None
                volume = row['Volume'] if pd.notna(row['Volume']) else 0
                trading_value = row['Trading_Value'] if pd.notna(row['Trading_Value']) else None
                
                # None 값이 있으면 해당 행 건너뛰기
                if open_price is None or high_price is None or low_price is None or close_price is None:
                    logging.warning(f"⚠️ {stock_code} {date.strftime('%Y-%m-%d')}: NaN 값이 있어 건너뜀")
                    continue
                
                # 거래대금이 없으면 계산 (Typical Price 방식: (H+L+C)/3 × V)
                if trading_value is None and close_price and volume and high_price and low_price:
                    typical_price = (high_price + low_price + close_price) / 3
                    trading_value = int(volume * typical_price)
                    logging.info(f"📊 {stock_code} {date.strftime('%Y-%m-%d')}: 거래대금 계산 완료 (Typical Price 방식: {trading_value:,}원)")
                elif trading_value is None and close_price and volume:
                    # Typical Price 계산이 불가능한 경우에만 Close Price 사용
                    trading_value = int(volume * close_price)
                    logging.info(f"📊 {stock_code} {date.strftime('%Y-%m-%d')}: 거래대금 계산 완료 (Close Price 방식: {trading_value:,}원)")
                
                # 유통주식수와 시가총액 검증 및 보정
                current_total_shares = total_shares
                current_market_cap = market_cap
                
                if total_shares and total_shares > 0:
                    # 시가총액이 0이면 종가로 계산
                    if market_cap == 0 and close_price:
                        current_market_cap = float(close_price) * total_shares
                        logging.info(f"📊 {stock_code} {date.strftime('%Y-%m-%d')}: 시가총액 계산 완료 ({current_market_cap:,.0f})")
                    
                    # 데이터 유효성 검증
                    if current_market_cap > 0 and close_price:
                        calculated_shares = current_market_cap / float(close_price)
                        if abs(calculated_shares - total_shares) / total_shares > 0.1:  # 10% 이상 차이나면 경고
                            logging.warning(f"⚠️ {stock_code} {date.strftime('%Y-%m-%d')}: 유통주식수와 시가총액 불일치 의심 (계산값: {calculated_shares:,.0f}주)")
                else:
                    # 유통주식수가 0이거나 None이면 None으로 설정
                    current_total_shares = None
                    current_market_cap = None
                    logging.warning(f"⚠️ {stock_code} {date.strftime('%Y-%m-%d')}: 유통주식수 정보 없음")
                
                daily_data.append((
                    stock_code,
                    date.strftime('%Y-%m-%d'),
                    float(open_price),
                    float(high_price),
                    float(low_price),
                    float(close_price),
                    int(volume),
                    int(trading_value) if trading_value else None,
                    current_total_shares,
                    current_market_cap
                ))
            
            # 기술적 지표 계산 및 준비
            # 증분 수집 시 충분한 데이터 확보를 위해 DB에서 과거 데이터 조회
            if len(hist_data) < 120:
                logging.info(f"🔧 {stock_code} 기술적 지표 계산을 위해 DB에서 과거 120일 데이터 조회 중...")
                past_data = self.get_past_data_for_indicators(stock_code, 120)
                if past_data is not None and not past_data.empty:
                    # 과거 데이터와 새 데이터 합치기 (중복 제거)
                    combined_data = pd.concat([past_data, hist_data])
                    combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
                    combined_data = combined_data.sort_index()
                    logging.info(f"✅ {stock_code} 과거 데이터 {len(past_data)}일 + 새 데이터 {len(hist_data)}일 = 총 {len(combined_data)}일")
                    df_with_indicators = self.calculate_technical_indicators(combined_data.copy())
                    # 새로운 데이터의 지표만 저장 (hist_data의 날짜에 해당하는 것만)
                    new_dates = hist_data.index
                    df_with_indicators = df_with_indicators.loc[df_with_indicators.index.isin(new_dates)]
                else:
                    logging.warning(f"⚠️ {stock_code} 과거 데이터 조회 실패, 현재 데이터만으로 계산")
                    df_with_indicators = self.calculate_technical_indicators(hist_data.copy())
            else:
                # 이미 충분한 데이터가 있으면 그대로 계산
                df_with_indicators = self.calculate_technical_indicators(hist_data.copy())
            
            technical_data = []
            for date, row in df_with_indicators.iterrows():
                # NaN 값 처리
                ma5 = row['MA5'] if pd.notna(row['MA5']) else None
                ma20 = row['MA20'] if pd.notna(row['MA20']) else None
                ma60 = row['MA60'] if pd.notna(row['MA60']) else None
                ma120 = row['MA120'] if pd.notna(row['MA120']) else None
                rsi = row['RSI'] if pd.notna(row['RSI']) else None
                macd = row['MACD'] if pd.notna(row['MACD']) else None
                macd_signal = row['MACD_Signal'] if pd.notna(row['MACD_Signal']) else None
                macd_histogram = row['MACD_Histogram'] if pd.notna(row['MACD_Histogram']) else None
                bb_upper = row['BB_Upper'] if pd.notna(row['BB_Upper']) else None
                bb_middle = row['BB_Middle'] if pd.notna(row['BB_Middle']) else None
                bb_lower = row['BB_Lower'] if pd.notna(row['BB_Lower']) else None
                
                technical_data.append((
                    stock_code,
                    date.strftime('%Y-%m-%d'),
                    ma5, ma20, ma60, ma120,
                    rsi,
                    macd, macd_signal, macd_histogram,
                    bb_upper, bb_middle, bb_lower
                ))
            
            # 수집 상태 데이터 준비
            last_date = hist_data.index[-1]
            first_date = hist_data.index[0]
            last_row = hist_data.iloc[-1]
            current_timestamp = datetime.now()
            
            # 데이터 품질 판단
            current_time = current_timestamp.time()
            from datetime import time
            market_open = time(9, 0)
            market_close = time(15, 30)
            
            if market_open <= current_time <= market_close:
                collection_quality = 'INTRADAY'  # 장중 데이터
            else:
                collection_quality = 'CLOSING'   # 장 마감 후 데이터
            
            status_data = (
                stock_code,
                last_date.strftime('%Y-%m-%d'),
                current_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                float(last_row['Close']),
                int(last_row['Volume']),
                first_date.strftime('%Y-%m-%d'),
                last_date.strftime('%Y-%m-%d'),
                len(hist_data),
                collection_quality
            )
            
            # 유통주식수 정보가 있으면 stock_shares_history에도 저장
            if shares_info and total_shares > 0:
                try:
                    self.update_stock_shares_history_direct(stock_code, total_shares, market_cap)
                    logging.info(f"✅ {stock_code} 유통주식수 정보 저장 완료: {total_shares:,}주, 시가총액 {market_cap:,}")
                except Exception as e:
                    logging.warning(f"⚠️ {stock_code} 유통주식수 히스토리 업데이트 중 오류: {e}")
            
            return daily_data, technical_data, status_data
            
        except Exception as e:
            logging.error(f"{stock_code} 데이터 준비 중 오류: {e}")
            return [], [], None
    
    def save_batch_daily_data(self, batch_daily_data):
        """배치 단위로 일봉 데이터 저장 - 오류 처리 강화"""
        try:
            logging.info(f"💾 save_batch_daily_data 함수 진입 - 데이터 개수: {len(batch_daily_data) if batch_daily_data else 0}")
            
            if not batch_daily_data:
                logging.info("📝 배치 일봉 데이터가 없습니다.")
                return True
            
            logging.info(f"💾 일봉 데이터 저장 시작: {len(batch_daily_data)}개")
            logging.info(f"💾 첫 번째 데이터 샘플: {batch_daily_data[0] if batch_daily_data else 'None'}")
            
            # 데이터 유효성 검증 (거래대금 포함)
            valid_data = []
            invalid_data = []
            for i, data in enumerate(batch_daily_data):
                if len(data) == 10 and all(data[i] is not None for i in range(1, 6)):  # stock_code 제외하고 OHLCV 검증 (trading_value, outstanding_shares, market_cap은 None 허용)
                    valid_data.append(data)
                else:
                    invalid_data.append((i, data))
                    logging.warning(f"⚠️ 잘못된 일봉 데이터 형식 (인덱스 {i}): {data}")
            
            if invalid_data:
                logging.warning(f"⚠️ 잘못된 데이터 {len(invalid_data)}개 발견")
            
            if not valid_data:
                logging.error("❌ 유효한 일봉 데이터가 없습니다.")
                return False
            
            logging.info(f"✅ 유효한 데이터 {len(valid_data)}개 검증 완료")
            
            # 첫 번째와 마지막 데이터 샘플 로깅
            if valid_data:
                first_data = valid_data[0]
                last_data = valid_data[-1]
                logging.info(f"📊 첫 번째 데이터: {first_data[0]} ({first_data[1]}) - O:{first_data[2]}, H:{first_data[3]}, L:{first_data[4]}, C:{first_data[5]}, V:{first_data[6]}, T:{first_data[7]}, S:{first_data[8]}, M:{first_data[9]}")
                logging.info(f"📊 마지막 데이터: {last_data[0]} ({last_data[1]}) - O:{last_data[2]}, H:{last_data[3]}, L:{last_data[4]}, C:{last_data[5]}, V:{last_data[6]}, T:{last_data[7]}, S:{last_data[8]}, M:{last_data[9]}")
            
            daily_insert_sql = """
            INSERT INTO daily_data 
            (stock_code, trade_date, open, high, low, close, volume, trading_value, outstanding_shares, market_cap)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open = VALUES(open), high = VALUES(high), low = VALUES(low), 
            close = VALUES(close), volume = VALUES(volume), trading_value = VALUES(trading_value),
            outstanding_shares = VALUES(outstanding_shares), market_cap = VALUES(market_cap),
            updated_at = CURRENT_TIMESTAMP
            """
            
            logging.info(f"💾 일봉 데이터 {len(valid_data):,}개를 청크 단위로 저장 시작...")
            logging.info(f"💾 DB 연결 상태: {self.db.is_connected()}")
            
            # 🚀 청크 단위로 분할 저장 (1,000개씩)
            chunk_size = 1000
            total_chunks = (len(valid_data) + chunk_size - 1) // chunk_size
            saved_count = 0
            failed_count = 0
            
            for i in range(0, len(valid_data), chunk_size):
                chunk = valid_data[i:i+chunk_size]
                chunk_num = (i // chunk_size) + 1
                
                try:
                    # DB 연결 확인
                    if not self.db.is_connected():
                        logging.warning(f"⚠️ 일봉 데이터 청크 {chunk_num}/{total_chunks} 저장 전 DB 재연결 시도...")
                        if not self.db.connect():
                            logging.error(f"❌ 일봉 데이터 청크 {chunk_num}/{total_chunks} DB 재연결 실패")
                            failed_count += len(chunk)
                            continue
                    
                    # 청크 저장 시도
                    result = self.db.execute_many(daily_insert_sql, chunk)
                    if result:
                        saved_count += len(chunk)
                        if chunk_num % 10 == 0 or chunk_num == total_chunks:  # 10개마다 또는 마지막
                            logging.info(f"✅ 일봉 데이터 청크 {chunk_num}/{total_chunks} 저장 완료 ({len(chunk):,}개)")
                    else:
                        logging.error(f"❌ 일봉 데이터 청크 {chunk_num}/{total_chunks} 저장 실패")
                        failed_count += len(chunk)
                        
                except Exception as chunk_e:
                    logging.error(f"❌ 일봉 데이터 청크 {chunk_num}/{total_chunks} 저장 중 예외: {chunk_e}")
                    failed_count += len(chunk)
                    
                    # MySQL 연결 오류 시 재연결
                    if "lost connection" in str(chunk_e).lower() or "gone away" in str(chunk_e).lower():
                        logging.warning("🔄 MySQL 연결 끊김 감지, 재연결 시도...")
                        self.db.connect()
                        time.sleep(2)
            
            # 최종 결과
            success = (failed_count == 0)
            if success:
                logging.info(f"✅ 배치 일봉 데이터 전체 저장 성공: {saved_count:,}개")
                
                # 저장 후 데이터베이스에서 확인
                try:
                    sample_stock_code = valid_data[0][0] if valid_data else None
                    if sample_stock_code:
                        count_query = "SELECT COUNT(*) as count FROM daily_data WHERE stock_code = %s"
                        count_result = self.db.fetch_one(count_query, (sample_stock_code,))
                        if count_result:
                            logging.info(f"✅ {sample_stock_code} 종목의 저장된 일봉 데이터: {count_result['count']}개")
                except Exception as e:
                    logging.warning(f"⚠️ 저장 확인 중 오류: {e}")
            else:
                logging.error(f"⚠️ 배치 일봉 데이터 부분 저장: 성공 {saved_count:,}개, 실패 {failed_count:,}개")
            
            return success
            
        except Exception as e:
            logging.error(f"❌ 배치 일봉 데이터 저장 중 예외 발생: {e}")
            import traceback
            logging.error(f"❌ 상세 오류: {traceback.format_exc()}")
            return False
    
    def save_batch_technical_indicators(self, batch_technical_data):
        """배치 단위로 기술적 지표 저장 - 청크 분할 저장 (MySQL 연결 끊김 방지)"""
        try:
            if not batch_technical_data:
                logging.info("📝 배치 기술적 지표 데이터가 없습니다.")
                return True
            
            # 데이터 유효성 검증 (수정: NULL 값 허용)
            valid_data = []
            for data in batch_technical_data:
                # stock_code와 trade_date만 필수, 보조지표는 NULL 허용
                if len(data) == 13 and data[0] is not None and data[1] is not None:
                    valid_data.append(data)
                else:
                    logging.warning(f"⚠️ 잘못된 기술적 지표 데이터 형식: {data}")
            
            if not valid_data:
                logging.error("❌ 유효한 기술적 지표 데이터가 없습니다.")
                return False
            
            logging.info(f"💾 기술적 지표 {len(valid_data):,}개를 청크 단위로 저장 시작...")
            
            technical_insert_sql = """
            INSERT INTO technical_indicators 
            (stock_code, trade_date, ma5, ma20, ma60, ma120, rsi, macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            ma5 = VALUES(ma5), ma20 = VALUES(ma20), ma60 = VALUES(ma60), ma120 = VALUES(ma120),
            rsi = VALUES(rsi), macd = VALUES(macd), macd_signal = VALUES(macd_signal), macd_histogram = VALUES(macd_histogram),
            bb_upper = VALUES(bb_upper), bb_middle = VALUES(bb_middle), bb_lower = VALUES(bb_lower),
            updated_at = CURRENT_TIMESTAMP
            """
            
            # 🚀 청크 단위로 분할 저장 (1,000개씩)
            chunk_size = 1000
            total_chunks = (len(valid_data) + chunk_size - 1) // chunk_size
            saved_count = 0
            failed_count = 0
            
            for i in range(0, len(valid_data), chunk_size):
                chunk = valid_data[i:i+chunk_size]
                chunk_num = (i // chunk_size) + 1
                
                try:
                    # DB 연결 확인
                    if not self.db.is_connected():
                        logging.warning(f"⚠️ 기술적 지표 청크 {chunk_num}/{total_chunks} 저장 전 DB 재연결 시도...")
                        if not self.db.connect():
                            logging.error(f"❌ 기술적 지표 청크 {chunk_num}/{total_chunks} DB 재연결 실패")
                            failed_count += len(chunk)
                            continue
                    
                    # 청크 저장 시도
                    result = self.db.execute_many(technical_insert_sql, chunk)
                    if result:
                        saved_count += len(chunk)
                        if chunk_num % 10 == 0 or chunk_num == total_chunks:  # 10개마다 또는 마지막
                            logging.info(f"✅ 기술적 지표 청크 {chunk_num}/{total_chunks} 저장 완료 ({len(chunk):,}개)")
                    else:
                        logging.error(f"❌ 기술적 지표 청크 {chunk_num}/{total_chunks} 저장 실패")
                        failed_count += len(chunk)
                        
                except Exception as chunk_e:
                    logging.error(f"❌ 기술적 지표 청크 {chunk_num}/{total_chunks} 저장 중 예외: {chunk_e}")
                    failed_count += len(chunk)
                    
                    # MySQL 연결 오류 시 재연결
                    if "lost connection" in str(chunk_e).lower() or "gone away" in str(chunk_e).lower():
                        logging.warning("🔄 MySQL 연결 끊김 감지, 재연결 시도...")
                        self.db.connect()
                        time.sleep(2)
            
            # 최종 결과
            success = (failed_count == 0)
            if success:
                logging.info(f"✅ 배치 기술적 지표 전체 저장 성공: {saved_count:,}개")
            else:
                logging.error(f"⚠️ 배치 기술적 지표 부분 저장: 성공 {saved_count:,}개, 실패 {failed_count:,}개")
            
            return success
            
        except Exception as e:
            logging.error(f"❌ 배치 기술적 지표 저장 중 예외 발생: {e}")
            import traceback
            logging.error(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def save_batch_collection_status(self, batch_status_data):
        """배치 단위로 수집 상태 업데이트 - 오류 처리 강화"""
        try:
            if not batch_status_data:
                logging.info("📝 배치 수집 상태 데이터가 없습니다.")
                return True
            
            # 데이터 유효성 검증
            valid_data = []
            for data in batch_status_data:
                if len(data) == 9 and data[0] is not None and data[1] is not None:  # stock_code와 last_collected_date는 필수
                    valid_data.append(data)
                else:
                    logging.warning(f"⚠️ 잘못된 수집 상태 데이터 형식: {data}")
            
            if not valid_data:
                logging.error("❌ 유효한 수집 상태 데이터가 없습니다.")
                return False
            
            status_insert_sql = """
            INSERT INTO stock_collection_status 
            (stock_code, last_collected_date, last_collected_timestamp, last_collected_close, last_collected_volume, 
             data_start_date, data_end_date, total_records, collection_quality)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            last_collected_date = VALUES(last_collected_date),
            last_collected_timestamp = VALUES(last_collected_timestamp),
            last_collected_close = VALUES(last_collected_close),
            last_collected_volume = VALUES(last_collected_volume),
            data_start_date = VALUES(data_start_date),
            data_end_date = VALUES(data_end_date),
            total_records = VALUES(total_records),
            collection_quality = VALUES(collection_quality)
            """
            
            result = self.db.execute_many(status_insert_sql, valid_data)
            if result:
                logging.info(f"✅ 배치 수집 상태 {len(valid_data)}개 업데이트 성공")
            else:
                logging.error(f"❌ 배치 수집 상태 업데이트 실패")
            
            return result
            
        except Exception as e:
            logging.error(f"❌ 배치 수집 상태 업데이트 중 예외 발생: {e}")
            return False

    def collect_all_stocks(self, auto_confirm=False):
        """모든 종목 데이터 수집 (수집 시간 최적화 포함)"""
        logging.info("🚀 전체 종목 데이터 수집 시작 (시장 상태 기반 최적화)")
        logging.info("="*60)
        
        # 웹 인터페이스에서 호출 시에는 시간 체크 건너뛰기
        if not auto_confirm:
            # 수집 시간 최적화 확인 (명령줄에서만)
            if not self.is_optimal_collection_time():
                response = input("권장 시간이 아닙니다. 계속 진행하시겠습니까? (y/N): ")
                if response.lower() != 'y':
                    logging.info("사용자에 의해 수집이 중단되었습니다.")
                    return 0, 0
        else:
            logging.info("🌐 웹 인터페이스에서 호출됨 - 시간 제한 없이 바로 수집을 시작합니다.")
        
        # 모든 종목 코드 조회
        all_stocks = self.get_all_stock_codes()
        if not all_stocks:
            logging.error("수집할 종목이 없습니다.")
            return 0, 0
        
        # 배치로 나누기
        total_stocks = len(all_stocks)
        total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
        
        logging.info(f"📊 총 {total_stocks}개 종목을 {total_batches}개 배치로 나누어 처리합니다.")
        logging.info(f"📦 배치 크기: {self.batch_size}개")
        logging.info(f"🔧 병렬 처리 워커 수: {self.max_workers}개")
        
        total_success = 0
        total_failed = 0
        
        for batch_num in range(1, total_batches + 1):
            start_idx = (batch_num - 1) * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_stocks)
            stock_batch = all_stocks[start_idx:end_idx]
            
            try:
                # 최적화된 배치 처리 사용 (DB 연결 재사용)
                success, failed = self.process_batch_optimized(stock_batch, batch_num, total_batches)
                total_success += success
                total_failed += failed
                
                # 배치 간 딜레이 (API 제한 방지)
                if batch_num < total_batches:
                    logging.info(f"⏳ 다음 배치까지 {self.batch_delay}초 대기...")
                    time.sleep(self.batch_delay)
                
            except KeyboardInterrupt:
                logging.warning("⚠️ 사용자에 의해 중단되었습니다.")
                logging.info(f"📊 현재까지 진행 상황: 성공 {total_success}개, 실패 {total_failed}개")
                break
                
            except Exception as e:
                logging.error(f"배치 {batch_num} 처리 중 오류: {e}")
                logging.info("⏳ 30초 대기 후 다음 배치 계속...")
                time.sleep(30)
                continue
        
        logging.info(f"\n🎉 전체 데이터 수집 완료!")
        logging.info(f"✅ 총 성공: {total_success}개")
        logging.info(f"❌ 총 실패: {total_failed}개")
        logging.info(f"📊 성공률: {(total_success / total_stocks * 100):.1f}%")
        
        # 기술지표 검증 및 수정 실행
        if total_success > 0:
            logging.info("\n🔍 기술지표 검증 및 수정 시작...")
            validation_success = self.validate_and_fix_technical_indicators()
            if validation_success:
                logging.info("✅ 기술지표 검증 및 수정 완료")
            else:
                logging.warning("⚠️ 기술지표 검증 및 수정에 문제가 있습니다. 로그를 확인해주세요.")
        
        return total_success, total_failed

    def collect_single_stock(self, stock_code):
        """특정 종목 하나만 수집 (일봉 데이터 + 유통주식수 통합)"""
        logging.info(f"🚀 종목 {stock_code} 데이터 + 유통주식수 수집 시작")
        logging.info("=" * 60)
        
        # 종목 정보 조회
        stock_info = self.get_stock_by_code(stock_code)
        if not stock_info:
            logging.error(f"종목 {stock_code} 정보를 찾을 수 없습니다.")
            return False, 0
        
        stock_code, stock_name = stock_info
        
        try:
            # 통합 수집 메서드 사용 (일봉 데이터 + 유통주식수)
            if self.collect_stock_data_with_shares(stock_code, stock_name):
                logging.info(f"✅ {stock_code} ({stock_name}) 데이터 + 유통주식수 수집 완료")
                
                # 수집된 일봉 데이터 수 확인
                try:
                    # DB 연결 상태 확인 (이미 연결되어 있어야 함)
                    if self.db.is_connected():
                        count_query = "SELECT COUNT(*) as count FROM daily_data WHERE stock_code = %s"
                        count_result = self.db.fetch_one(count_query, (stock_code,))
                        if count_result:
                            logging.info(f"📊 수집된 일봉 데이터: {count_result['count']}일")
                except Exception as e:
                    logging.warning(f"⚠️ 데이터 수 확인 중 오류: {e}")
                
                return True, 1  # 성공
            else:
                logging.error(f"❌ {stock_code} ({stock_name}) 통합 수집 실패")
                return False, 0
                
        except Exception as e:
            logging.error(f"{stock_code} ({stock_name}) 처리 중 오류: {e}")
            return False, 0

    def collect_failed_stocks_batch(self, specific_codes=None):
        """특정 종목들을 100개씩 배치로 나누어 수집 (최적화된 배치 처리) - 개선된 버전"""
        logging.info("🚀 종목 배치 수집 시작 (최적화된 배치 처리 + 개선된 티커 매핑)")
        logging.info("="*60)
        
        # 특정 종목코드가 지정된 경우 해당 종목만 처리
        if specific_codes:
            target_codes = specific_codes
            logging.info(f"🧪 특정 종목 {len(target_codes)}개를 수집합니다.")
        else:
            logging.error("수집할 종목코드가 지정되지 않았습니다.")
            return 0, 0
        
        if not target_codes:
            logging.error("수집할 종목이 없습니다.")
            return 0, 0
        
        # 배치로 나누기
        total_stocks = len(target_codes)
        total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
        
        logging.info(f"📊 총 {total_stocks}개 종목을 {total_batches}개 배치로 나누어 처리합니다.")
        logging.info(f"📦 배치 크기: {self.batch_size}개")
        logging.info(f"🔧 최적화된 배치 처리 + 개선된 티커 매핑 사용")
        
        total_success = 0
        total_failed = 0
        
        for batch_num in range(1, total_batches + 1):
            start_idx = (batch_num - 1) * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_stocks)
            stock_batch_codes = target_codes[start_idx:end_idx]
            
            # 종목코드만으로 종목 정보 조회하여 stock_batch 생성
            stock_batch = []
            for stock_code in stock_batch_codes:
                stock_info = self.get_stock_by_code(stock_code)
                if stock_info:
                    stock_batch.append(stock_info)
                else:
                    logging.warning(f"⚠️ {stock_code}: 데이터베이스에서 종목 정보를 찾을 수 없습니다.")
                    total_failed += 1
            
            if not stock_batch:
                logging.warning(f"⚠️ 배치 {batch_num}: 처리할 종목이 없습니다.")
                continue
            
            try:
                # 최적화된 배치 처리 사용 (DB 연결 재사용)
                success, failed = self.process_batch_optimized(stock_batch, batch_num, total_batches)
                total_success += success
                total_failed += failed
                
                # 배치 간 딜레이 (API 제한 방지)
                if batch_num < total_batches:
                    logging.info(f"⏳ 다음 배치까지 {self.batch_delay}초 대기...")
                    time.sleep(self.batch_delay)
                    
            except Exception as e:
                logging.error(f"배치 {batch_num} 처리 중 오류: {e}")
                logging.info("⏳ 30초 대기 후 다음 배치 계속...")
                time.sleep(30)
                continue
        
        logging.info(f"\n🎉 종목 배치 수집 완료!")
        logging.info(f"✅ 총 성공: {total_success}개")
        logging.info(f"❌ 총 실패: {total_failed}개")
        logging.info(f"📊 성공률: {(total_success / total_stocks * 100):.1f}%")
        
        return total_success, total_failed
    
    def collect_missing_stocks_from_csv(self, csv_file_path):
        """CSV 파일에서 누락된 종목들을 읽어와서 수집"""
        try:
            import pandas as pd
            
            logging.info(f"📁 CSV 파일에서 누락된 종목 목록 읽기: {csv_file_path}")
            
            # CSV 파일 읽기
            df = pd.read_csv(csv_file_path)
            
            if 'stock_code' not in df.columns:
                logging.error("❌ CSV 파일에 'stock_code' 컬럼이 없습니다.")
                return 0, 0
            
            # 종목코드 추출
            missing_stock_codes = df['stock_code'].tolist()
            
            logging.info(f"📊 CSV에서 {len(missing_stock_codes)}개 누락 종목을 찾았습니다.")
            
            # 배치 수집 실행
            return self.collect_failed_stocks_batch(missing_stock_codes)
            
        except Exception as e:
            logging.error(f"❌ CSV 파일 처리 중 오류: {e}")
            return 0, 0
    
    def get_stock_data_with_last_date(self, stock_code, stock_name, last_collected_date):
        """주식 데이터 조회 (마지막 수집 날짜 정보를 받아서 처리) - PyKrx 기반"""
        try:
            if last_collected_date:
                # 전일 데이터 품질 검증
                is_valid, reason = self.validate_previous_day_data_quality(stock_code, last_collected_date)
                
                if not is_valid:
                    logging.info(f"🔄 {stock_code} ({stock_name}): {reason} - 전일부터 재수집")
                    # 전일부터 재수집
                    start_date = last_collected_date - timedelta(days=1)
                    return self.get_incremental_data_pykrx(stock_code, stock_name, start_date)
                
                # 증분 수집: 마지막 수집 날짜 다음날부터
                next_date = last_collected_date + timedelta(days=1)
                today = datetime.now().date()
                
                if next_date <= today:
                    logging.info(f"🔄 {stock_code} ({stock_name}) 증분 수집을 진행합니다.")
                    return self.get_incremental_data_pykrx(stock_code, stock_name, next_date)
                else:
                    logging.info(f"✅ {stock_code} ({stock_name}) 이미 최신 데이터입니다. (마지막 수집: {last_collected_date})")
                    return None
            else:
                # 최초 수집: 10년치 전체 데이터
                logging.info(f"🔍 {stock_code} ({stock_name}) 10년치 일봉 데이터 조회 중... (PyKrx)")
                
                # PyKrx로 데이터 조회
                hist_data = self.get_stock_data_pykrx(stock_code, stock_name, 10)
                
                if hist_data is not None:
                    return hist_data
                else:
                    logging.error(f"❌ {stock_code} ({stock_name}): PyKrx로 데이터를 찾을 수 없습니다")
                    logging.warning(f"   💡 이 종목은 상장폐지되었거나 더 이상 거래되지 않을 수 있습니다")
                    return None
                    
        except Exception as e:
            logging.error(f"{stock_code} ({stock_name}) 데이터 조회 실패: {e}")
            return None

    def get_stock_shares_info_from_yahoo(self, stock_code: str, market_type: str) -> Optional[Dict[str, Any]]:
        """Yahoo Finance에서 주식의 유통주식수 정보 조회 - PyKrx로 대체"""
        # PyKrx 기반 함수로 대체
        return self.get_stock_shares_info_from_pykrx(stock_code, market_type)
    
    def is_active_stock(self, stock_code: str, stock_name: str, volume: int) -> bool:
        """활성 종목인지 확인 (상폐/비활성 종목 제외) - 거래량 필터링 제거"""
        try:
            # 거래량 필터링 완전 제거 - 모든 종목 수집
            # if volume < 1000:
            #     logging.info(f"⚠️ {stock_code} ({stock_name}): 거래량 {volume:,}주로 비활성 종목 의심")
            #     return False
            
            # 특수 종목코드 체크 제거 - 모든 종목 수집
            # if any(c.isalpha() for c in stock_code) or len(stock_code) > 6:
            #     logging.info(f"⚠️ {stock_code} ({stock_name}): 특수 종목코드로 처리 제외")
            #     return False
            
            # 3. 알려진 상장폐지/비활성 종목코드만 체크 (실제 상장폐지된 종목만)
            delisted_codes = {
                '397810',  # 애드포러스 (상장폐지 아님 신규 종목)
                '0044K0',  # 삼성기업인수목적10호 (상장폐지 아님 신규 종목 8월 21일일)
                '0010V0',  # 제이피아이헬스케어 (상장폐지)
                # 추가 상장폐지 종목들...
            }
            if stock_code in delisted_codes:
                logging.info(f"⚠️ {stock_code} ({stock_name}): 알려진 상장폐지 종목")
                return False
            
            # 종목명 키워드 체크 제거 - 모든 종목 수집
            # delisted_keywords = ['상장폐지', '폐지', '청산', '해산', '파산', '부도', '정리']
            # if any(keyword in stock_name for keyword in delisted_keywords):
            #     logging.info(f"⚠️ {stock_code} ({stock_name}): 종목명에 상장폐지 관련 키워드 포함")
            #     return False
            
            # 종목코드 패턴 체크 제거 - 모든 종목 수집
            # if stock_code.startswith('9') and len(stock_code) > 6:
            #     logging.info(f"⚠️ {stock_code} ({stock_name}): 비정상 종목코드 패턴")
            #     return False
            
            # 모든 종목을 기본적으로 활성으로 간주
            return True
            
        except Exception as e:
            logging.warning(f"⚠️ {stock_code} 활성 종목 확인 중 오류: {e}")
            return True  # 오류 시 기본적으로 활성으로 간주
    
    def collect_shares_for_all_stocks(self, batch_size: int = 100):
        """전체 종목에 대해 유통주식수 수집 (PyKrx 기반)"""
        logging.info("🚀 전체 종목 유통주식수 수집 시작 (PyKrx 기반)")
        logging.info("="*60)
        
        # 모든 종목 코드 조회
        all_stocks = self.get_all_stock_codes()
        if not all_stocks:
            logging.error("수집할 종목이 없습니다.")
            return 0, 0
        
        logging.info(f"📊 총 {len(all_stocks)}개 종목을 대상으로 유통주식수 수집합니다.")
        
        # 1단계: 기존 stock_shares_history에 있는 데이터로 빠른 업데이트
        logging.info("\n🔄 1단계: 기존 데이터로 빠른 업데이트 시작")
        fast_updated = self._fast_update_existing_shares(all_stocks)
        
        # 2단계: stock_shares_history에 없는 새로운 종목들 PyKrx에서 수집
        logging.info("\n🔄 2단계: 새로운 종목 PyKrx에서 수집 시작")
        new_collected = self._collect_new_shares_from_yahoo(all_stocks, batch_size)
        
        # 3단계: 최종 통계
        total_success = fast_updated + new_collected
        total_failed = len(all_stocks) - total_success
        
        logging.info(f"\n🎉 전체 유통주식수 수집 완료!")
        logging.info(f"✅ 총 성공: {total_success:,}개")
        logging.info(f"❌ 총 실패: {total_failed:,}개")
        logging.info(f"📊 성공률: {(total_success / len(all_stocks) * 100):.1f}%")
        logging.info(f"   - 빠른 업데이트: {fast_updated:,}개")
        logging.info(f"   - 새로운 수집: {new_collected:,}개")
        
        return total_success, total_failed
    
    def _fast_update_existing_shares(self, all_stocks):
        """기존 stock_shares_history에 있는 데이터로 빠른 업데이트"""
        logging.info("기존 데이터로 빠른 업데이트 중...")
        
        # DB 연결 상태 확인 (이미 연결되어 있어야 함)
        if not self.db.is_connected():
            logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
            if not self.db.connect():
                logging.error("데이터베이스 연결 실패")
                return 0
        
        try:
            # stock_shares_history에 데이터가 있는 종목들 조회
            existing_shares_query = """
            SELECT DISTINCT stock_code, total_shares
            FROM stock_shares_history 
            WHERE total_shares > 0
            """
            
            existing_shares = self.db.fetch_all(existing_shares_query)
            
            if not existing_shares:
                logging.info("기존 stock_shares_history 데이터가 없습니다.")
                return 0
            
            logging.info(f"기존 데이터로 업데이트할 종목 수: {len(existing_shares):,}개")
            
            updated_count = 0
            
            for stock in existing_shares:
                stock_code = stock['stock_code']
                total_shares = stock['total_shares']
                
                try:
                    # 해당 종목의 최근 종가 조회
                    recent_price_query = """
                    SELECT close FROM daily_data 
                    WHERE stock_code = %s 
                    ORDER BY trade_date DESC 
                    LIMIT 1
                    """
                    
                    recent_price_result = self.db.fetch_one(recent_price_query, (stock_code,))
                    
                    if recent_price_result:
                        recent_close = recent_price_result['close']
                        market_cap = total_shares * recent_close
                        
                        # daily_data 테이블 업데이트
                        update_query = """
                        UPDATE daily_data 
                        SET outstanding_shares = %s, market_cap = %s
                        WHERE stock_code = %s AND (outstanding_shares IS NULL OR outstanding_shares = 0 OR market_cap IS NULL OR market_cap = 0)
                        """
                        
                        params = (total_shares, market_cap, stock_code)
                        success = self.db.execute_query(update_query, params)
                        
                        if success:
                            # 업데이트된 레코드 수 확인
                            updated_records_query = """
                            SELECT COUNT(*) as updated_count
                            FROM daily_data 
                            WHERE stock_code = %s AND outstanding_shares = %s
                            """
                            
                            updated_records_result = self.db.fetch_one(updated_records_query, (stock_code, total_shares))
                            updated_records = updated_records_result['updated_count'] if updated_records_result else 0
                            
                            if updated_records > 0:
                                logging.info(f"✅ {stock_code}: {updated_records:,}개 레코드 빠른 업데이트 완료")
                                updated_count += 1
                            else:
                                logging.info(f"ℹ️ {stock_code}: 이미 업데이트된 상태")
                        else:
                            logging.warning(f"⚠️ {stock_code}: 데이터베이스 업데이트 실패")
                    else:
                        logging.warning(f"⚠️ {stock_code}: 최근 종가를 찾을 수 없음")
                        
                except Exception as e:
                    logging.warning(f"⚠️ {stock_code} 빠른 업데이트 중 오류: {e}")
                    continue
            
            logging.info(f"빠른 업데이트 완료: {updated_count:,}개 종목")
            return updated_count
            
        except Exception as e:
            logging.error(f"빠른 업데이트 중 오류: {e}")
            return 0
        finally:
            # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
            pass
    
    def _collect_new_shares_from_yahoo(self, all_stocks, batch_size):
        """stock_shares_history에 없는 새로운 종목들을 PyKrx에서 수집 (성능 최적화)"""
        logging.info("새로운 종목 PyKrx에서 수집 중...")
        
        # DB 연결 상태 확인 (이미 연결되어 있어야 함)
        if not self.db.is_connected():
            logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
            if not self.db.connect():
                logging.error("데이터베이스 연결 실패")
                return 0
        
        try:
            # 이미 stock_shares_history에 있는 종목들 조회
            existing_codes_query = "SELECT DISTINCT stock_code FROM stock_shares_history WHERE total_shares > 0"
            existing_codes_result = self.db.fetch_all(existing_codes_query)
            existing_codes = {row['stock_code'] for row in existing_codes_result} if existing_codes_result else set()
            
            # 새로운 종목들 필터링
            new_stocks = [(code, name) for code, name in all_stocks if code not in existing_codes]
            
            if not new_stocks:
                logging.info("새로운 종목이 없습니다.")
                return 0
            
            logging.info(f"PyKrx에서 수집할 새로운 종목 수: {len(new_stocks):,}개")
            
            # 배치로 나누기
            total_batches = (len(new_stocks) + batch_size - 1) // batch_size
            
            total_success = 0
            
            for batch_num in range(1, total_batches + 1):
                start_idx = (batch_num - 1) * batch_size
                end_idx = min(start_idx + batch_size, len(new_stocks))
                stock_batch = new_stocks[start_idx:end_idx]
                
                logging.info(f"🚀 배치 {batch_num}/{total_batches} 시작 ({len(stock_batch)}개 종목)")
                
                batch_success = 0
                batch_failed = 0
                
                for i, (stock_code, stock_name) in enumerate(stock_batch, 1):
                    logging.info(f"📊 [{i}/{len(stock_batch)}] {stock_code} ({stock_name}) 유통주식수 수집 중...")
                    
                    try:
                        # 종목의 시장 구분 조회 (최적화된 방식)
                        market_type = self.get_stock_market_type(stock_code)
                        
                        # PyKrx에서 유통주식수 조회 (최적화된 방식)
                        shares_data = self.get_stock_shares_info_from_pykrx(stock_code, market_type)
                        
                        if shares_data:
                            # stock_shares_history 업데이트
                            if self.update_stock_shares_history(shares_data):
                                # daily_data의 outstanding_shares와 market_cap 업데이트
                                if self.update_daily_data_shares(stock_code, shares_data['total_shares'], shares_data['market_cap']):
                                    logging.info(f"✅ {stock_code} ({stock_name}) 유통주식수 수집 완료")
                                    batch_success += 1
                                else:
                                    logging.error(f"❌ {stock_code} ({stock_name}) daily_data 업데이트 실패")
                                    batch_failed += 1
                            else:
                                logging.error(f"❌ {stock_code} ({stock_name}) 유통주식수 히스토리 업데이트 실패")
                                batch_failed += 1
                        else:
                            logging.warning(f"⚠️ {stock_code} ({stock_name}) 유통주식수 정보 수집 실패")
                            batch_failed += 1
                        
                        # API 호출 간격 조절 (PyKrx 최적화)
                        time.sleep(self.delay_between_requests + random.uniform(0.05, 0.15))
                        
                    except Exception as e:
                        logging.error(f"❌ {stock_code} ({stock_name}) 처리 중 오류: {e}")
                        batch_failed += 1
                        
                        # PyKrx API 제한 감지 시 더 긴 딜레이
                        if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                            logging.warning("⚠️ PyKrx API 제한 감지! 15초 대기 후 계속...")
                            time.sleep(15)
                
                total_success += batch_success
                
                logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
                logging.info(f"✅ 성공: {batch_success}개, ❌ 실패: {batch_failed}개")
                
                # 배치 간 딜레이 (PyKrx 최적화)
                if batch_num < total_batches:
                    logging.info(f"⏳ 다음 배치까지 {self.batch_delay}초 대기...")
                    time.sleep(self.batch_delay)
            
            logging.info(f"새로운 종목 수집 완료: {total_success:,}개 종목")
            return total_success
            
        except Exception as e:
            logging.error(f"새로운 종목 수집 중 오류: {e}")
            return 0
        finally:
            # DB 연결은 배치 단위로 관리하므로 여기서는 해제하지 않음
            pass

    def update_stock_shares_history(self, stock_data: Dict[str, Any]) -> bool:
        """stock_shares_history 테이블에 유통주식수 정보 추가"""
        try:
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    logging.error("❌ 데이터베이스 연결 실패")
                    return False
            
            # 오늘 날짜로 유통주식수 히스토리 추가
            today = datetime.now().date()
            
            insert_query = """
                INSERT INTO stock_shares_history 
                (stock_code, effective_date, total_shares, change_reason)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_shares = VALUES(total_shares),
                updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                stock_data['stock_code'],
                today,
                stock_data['total_shares'],
                '주식 데이터 수집 시 함께 업데이트'
            )
            
            success = self.db.execute_query(insert_query, params)
            
            if success:
                logging.info(f"✅ {stock_data['stock_code']} 유통주식수 히스토리 업데이트 완료")
                return True
            else:
                logging.error(f"❌ {stock_data['stock_code']} 유통주식수 히스토리 업데이트 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ {stock_data['stock_code']} 유통주식수 히스토리 업데이트 중 오류: {e}")
            return False
    
    def update_stock_shares_history_direct(self, stock_code: str, total_shares: int, market_cap: float = 0) -> bool:
        """stock_shares_history 테이블에 유통주식수 정보 직접 추가 (개별 매개변수용)"""
        try:
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    logging.error("❌ 데이터베이스 연결 실패")
                    return False
            
            # 오늘 날짜로 유통주식수 히스토리 추가
            today = datetime.now().date()
            
            insert_query = """
                INSERT INTO stock_shares_history 
                (stock_code, effective_date, total_shares, change_reason)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_shares = VALUES(total_shares),
                updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                stock_code,
                today,
                total_shares,
                '일봉 데이터 수집 시 함께 업데이트'
            )
            
            success = self.db.execute_query(insert_query, params)
            
            if success:
                logging.info(f"✅ {stock_code} 유통주식수 히스토리 업데이트 완료")
                return True
            else:
                logging.error(f"❌ {stock_code} 유통주식수 히스토리 업데이트 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ {stock_code} 유통주식수 히스토리 업데이트 중 오류: {e}")
            return False
    
    def update_daily_data_shares(self, stock_code: str, total_shares: int, market_cap: float = 0) -> bool:
        """daily_data 테이블의 outstanding_shares와 market_cap 업데이트"""
        try:
            # DB 연결 상태 확인 (이미 연결되어 있어야 함)
            if not self.db.is_connected():
                logging.warning("⚠️ DB 연결이 끊어져 있습니다. 재연결 시도...")
                if not self.db.connect():
                    logging.error("❌ 데이터베이스 연결 실패")
                    return False
            
            # 해당 종목의 모든 daily_data 레코드의 outstanding_shares와 market_cap 업데이트
            update_query = """
                UPDATE daily_data 
                SET outstanding_shares = %s, market_cap = %s
                WHERE stock_code = %s AND (outstanding_shares IS NULL OR outstanding_shares = 0 OR market_cap IS NULL OR market_cap = 0)
            """
            
            params = (total_shares, market_cap, stock_code)
            
            success = self.db.execute_query(update_query, params)
            
            if success:
                logging.info(f"✅ {stock_code} daily_data outstanding_shares, market_cap 업데이트 완료")
                return True
            else:
                logging.error(f"❌ {stock_code} daily_data 업데이트 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ {stock_code} daily_data 업데이트 중 오류: {e}")
            return False
    
    def collect_historical_shares_data(self, stock_code: str, market_type: str, start_date: str, end_date: str) -> bool:
        """과거 기간의 유통주식수 데이터 수집 (PyKrx 기반) - 성능 최적화"""
        try:
            logging.info(f"🔍 {stock_code} 과거 유통주식수 데이터 수집 중... ({start_date} ~ {end_date})")
            
            # PyKrx에서 현재 유통주식수 조회 (최적화된 방식)
            shares_data = self.get_stock_shares_info_from_pykrx(stock_code, market_type)
            
            if not shares_data:
                logging.warning(f"⚠️ {stock_code} 유통주식수 정보 수집 실패")
                return False
            
            # stock_shares_history에 기록
            if not self.update_stock_shares_history(shares_data):
                logging.error(f"❌ {stock_code} 유통주식수 히스토리 업데이트 실패")
                return False
            
            # daily_data의 해당 기간 데이터에 유통주식수 업데이트
            if not self.update_daily_data_shares(stock_code, shares_data['total_shares'], shares_data['market_cap']):
                logging.error(f"❌ {stock_code} daily_data 업데이트 실패")
                return False
            
            logging.info(f"✅ {stock_code} 과거 유통주식수 데이터 수집 완료")
            return True
            
        except Exception as e:
            logging.error(f"❌ {stock_code} 과거 유통주식수 데이터 수집 중 오류: {e}")
            return False
    
    def collect_stock_data_with_shares(self, stock_code: str, stock_name: str) -> bool:
        """주식 데이터와 유통주식수를 함께 수집 (PyKrx 기반)"""
        try:
            logging.info(f"📊 {stock_code} ({stock_name}) 데이터 + 유통주식수 수집 시작 (PyKrx)")
            
            # 1. 기존 일봉 데이터 수집 (PyKrx 기반)
            hist_data = self.get_stock_data(stock_code, stock_name)
            
            if hist_data is not None:
                logging.info(f"📊 {stock_code} ({stock_name}) 수집된 데이터: {len(hist_data)}일")
                # 2. 일봉 데이터 저장 (기존 로직 유지)
                if self.save_daily_data(stock_code, hist_data):
                    logging.info(f"✅ {stock_code} ({stock_name}) 일봉 데이터 수집 완료")
                    
                    # 3. 유통주식수 정보 수집 (PyKrx 기반)
                    try:
                        # 종목의 시장 구분 조회
                        market_query = "SELECT market_type FROM stocks WHERE stock_code = %s"
                        market_result = self.db.fetch_one(market_query, (stock_code,))
                        market_type = market_result['market_type'] if market_result else "KOSPI"
                        
                        # PyKrx에서 유통주식수 조회
                        shares_data = self.get_stock_shares_info_from_pykrx(stock_code, market_type)
                        
                        if shares_data:
                            # 4. stock_shares_history 업데이트
                            if self.update_stock_shares_history(shares_data):
                                # 5. daily_data의 유통주식수 정보 업데이트
                                self.update_daily_data_shares(stock_code, shares_data['total_shares'], shares_data['market_cap'])
                                logging.info(f"✅ {stock_code} ({stock_name}) 유통주식수 정보 업데이트 완료: {shares_data['total_shares']:,}주")
                            else:
                                logging.warning(f"⚠️ {stock_code} ({stock_name}) 유통주식수 히스토리 업데이트 실패")
                        else:
                            logging.warning(f"⚠️ {stock_code} ({stock_name}) 유통주식수 정보 조회 실패")
                            
                    except Exception as e:
                        logging.warning(f"⚠️ {stock_code} ({stock_name}) 유통주식수 정보 처리 중 오류: {e}")
                    
                    return True
            elif hist_data is None:
                # 이미 최신 데이터이거나 데이터가 없는 경우
                logging.info(f"✅ {stock_code} ({stock_name}) 이미 최신 데이터이거나 수집할 데이터가 없습니다.")
                
                # 유통주식수만 업데이트 시도
                try:
                    market_query = "SELECT market_type FROM stocks WHERE stock_code = %s"
                    market_result = self.db.fetch_one(market_query, (stock_code,))
                    market_type = market_result['market_type'] if market_result else "KOSPI"
                    
                    shares_data = self.get_stock_shares_info_from_pykrx(stock_code, market_type)
                    
                    if shares_data:
                        if self.update_stock_shares_history(shares_data):
                            self.update_daily_data_shares(stock_code, shares_data['total_shares'], shares_data['market_cap'])
                            logging.info(f"✅ {stock_code} ({stock_name}) 유통주식수 정보 업데이트 완료: {shares_data['total_shares']:,}주")
                        else:
                            logging.warning(f"⚠️ {stock_code} ({stock_name}) 유통주식수 히스토리 업데이트 실패")
                    else:
                        logging.warning(f"⚠️ {stock_code} ({stock_name}) 유통주식수 정보 조회 실패")
                        
                except Exception as e:
                    logging.warning(f"⚠️ {stock_code} ({stock_name}) 유통주식수 정보 처리 중 오류: {e}")
                
                return True
            else:
                logging.warning(f"❌ {stock_code} ({stock_name}) 데이터 조회 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ {stock_code} ({stock_name}) 데이터 + 유통주식수 수집 중 오류: {e}")
            return False
    
    def collect_historical_shares_data_pykrx(self, stock_code: str, market_type: str, start_date: str, end_date: str) -> bool:
        """과거 기간의 유통주식수 데이터 수집 (PyKrx 기반) - 성능 최적화"""
        try:
            logging.info(f"🔍 {stock_code} 과거 유통주식수 데이터 수집 중... ({start_date} ~ {end_date})")
            
            # PyKrx에서 현재 유통주식수 조회 (최적화된 방식)
            shares_data = self.get_stock_shares_info_from_pykrx(stock_code, market_type)
            
            if not shares_data:
                logging.warning(f"⚠️ {stock_code} 유통주식수 정보 수집 실패")
                return False
            
            # stock_shares_history에 기록
            if not self.update_stock_shares_history(shares_data):
                logging.error(f"❌ {stock_code} 유통주식수 히스토리 업데이트 실패")
                return False
            
            # daily_data의 해당 기간 데이터에 유통주식수 업데이트
            if not self.update_daily_data_shares(stock_code, shares_data['total_shares'], shares_data['market_cap']):
                logging.error(f"❌ {stock_code} daily_data 업데이트 실패")
                return False
            
            logging.info(f"✅ {stock_code} 과거 유통주식수 데이터 수집 완료")
            return True
            
        except Exception as e:
            logging.error(f"❌ {stock_code} 과거 유통주식수 데이터 수집 중 오류: {e}")
            return False
    
    def check_technical_indicators_null_ratio(self):
        """기술지표 NULL 값 비율 검사"""
        try:
            if not self.db.is_connected():
                if not self.db.connect():
                    logging.error("❌ 데이터베이스 연결 실패")
                    return {'null_ratio': 1.0, 'failed_stocks': []}
            
            # 전체 기술지표 NULL 값 통계 조회
            query = """
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN ma5 IS NULL THEN 1 ELSE 0 END) as ma5_null,
                SUM(CASE WHEN ma20 IS NULL THEN 1 ELSE 0 END) as ma20_null,
                SUM(CASE WHEN ma60 IS NULL THEN 1 ELSE 0 END) as ma60_null,
                SUM(CASE WHEN ma120 IS NULL THEN 1 ELSE 0 END) as ma120_null,
                SUM(CASE WHEN rsi IS NULL THEN 1 ELSE 0 END) as rsi_null,
                SUM(CASE WHEN macd IS NULL THEN 1 ELSE 0 END) as macd_null,
                SUM(CASE WHEN bb_upper IS NULL THEN 1 ELSE 0 END) as bb_upper_null
            FROM technical_indicators
            """
            
            result = self.db.fetch_one(query)
            
            if not result or result['total_records'] == 0:
                logging.warning("⚠️ 기술지표 데이터가 없습니다.")
                return {'null_ratio': 0.0, 'failed_stocks': []}
            
            total_records = result['total_records']
            null_counts = [
                result['ma5_null'], result['ma20_null'], result['ma60_null'], 
                result['ma120_null'], result['rsi_null'], result['macd_null'], 
                result['bb_upper_null']
            ]
            
            # 가장 많은 NULL 값을 가진 지표의 비율 계산
            max_null_count = max(null_counts)
            null_ratio = max_null_count / total_records
            
            # NULL 값이 있는 종목들 조회
            failed_stocks_query = """
            SELECT DISTINCT stock_code 
            FROM technical_indicators 
            WHERE ma5 IS NULL OR ma20 IS NULL OR ma60 IS NULL OR ma120 IS NULL 
               OR rsi IS NULL OR macd IS NULL OR bb_upper IS NULL
            """
            failed_stocks_result = self.db.fetch_all(failed_stocks_query)
            failed_stocks = [row['stock_code'] for row in failed_stocks_result] if failed_stocks_result else []
            
            logging.info(f"📊 기술지표 NULL 값 검사 결과:")
            logging.info(f"   총 레코드: {total_records:,}개")
            logging.info(f"   MA5 NULL: {result['ma5_null']:,}개 ({result['ma5_null']/total_records*100:.1f}%)")
            logging.info(f"   MA20 NULL: {result['ma20_null']:,}개 ({result['ma20_null']/total_records*100:.1f}%)")
            logging.info(f"   MA60 NULL: {result['ma60_null']:,}개 ({result['ma60_null']/total_records*100:.1f}%)")
            logging.info(f"   MA120 NULL: {result['ma120_null']:,}개 ({result['ma120_null']/total_records*100:.1f}%)")
            logging.info(f"   RSI NULL: {result['rsi_null']:,}개 ({result['rsi_null']/total_records*100:.1f}%)")
            logging.info(f"   MACD NULL: {result['macd_null']:,}개 ({result['macd_null']/total_records*100:.1f}%)")
            logging.info(f"   BB_UPPER NULL: {result['bb_upper_null']:,}개 ({result['bb_upper_null']/total_records*100:.1f}%)")
            logging.info(f"   최대 NULL 비율: {null_ratio:.2%}")
            logging.info(f"   문제 종목 수: {len(failed_stocks)}개")
            
            return {
                'null_ratio': null_ratio,
                'failed_stocks': failed_stocks,
                'total_records': total_records,
                'null_counts': {
                    'ma5': result['ma5_null'],
                    'ma20': result['ma20_null'],
                    'ma60': result['ma60_null'],
                    'ma120': result['ma120_null'],
                    'rsi': result['rsi_null'],
                    'macd': result['macd_null'],
                    'bb_upper': result['bb_upper_null']
                }
            }
            
        except Exception as e:
            logging.error(f"❌ 기술지표 NULL 값 검사 실패: {e}")
            return {'null_ratio': 1.0, 'failed_stocks': []}
    
    def fix_technical_indicators_for_failed_stocks(self, failed_stocks):
        """실패한 종목들의 기술지표 재수집"""
        try:
            if not failed_stocks:
                logging.info("✅ 재수집할 종목이 없습니다.")
                return True
            
            logging.info(f"🔄 {len(failed_stocks)}개 종목의 기술지표 재수집 시작")
            
            # technical_indicators_recollector 모듈 import
            try:
                from technical_indicators_recollector import TechnicalIndicatorsRecollector
                recollector = TechnicalIndicatorsRecollector()
                
                # 특정 종목들만 재수집
                success, failed = recollector.recollect_all_technical_indicators(specific_codes=failed_stocks)
                
                logging.info(f"✅ 기술지표 재수집 완료: 성공 {success}개, 실패 {failed}개")
                return success > 0
                
            except ImportError as e:
                logging.error(f"❌ technical_indicators_recollector 모듈 import 실패: {e}")
                return False
            except Exception as e:
                logging.error(f"❌ 기술지표 재수집 중 오류: {e}")
                return False
                
        except Exception as e:
            logging.error(f"❌ 기술지표 재수집 실패: {e}")
            return False
    
    def save_failed_stocks_report(self, failed_stocks):
        """실패한 종목 리스트를 파일로 저장"""
        try:
            if not failed_stocks:
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"failed_technical_indicators_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"기술지표 수집 실패 종목 리스트\n")
                f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"총 {len(failed_stocks)}개 종목\n")
                f.write("="*50 + "\n")
                for stock_code in failed_stocks:
                    f.write(f"{stock_code}\n")
            
            logging.info(f"📄 실패 종목 리스트 저장: {filename}")
            
        except Exception as e:
            logging.error(f"❌ 실패 종목 리스트 저장 실패: {e}")
    
    def validate_and_fix_technical_indicators(self, max_retries=3, null_threshold=0.05, ma120_null_threshold=0.06):
        """기술지표 검증 및 수정 (최대 3회 재시도, 5% 임계치, ma120은 6% 임계치)"""
        try:
            logging.info("🔍 기술지표 검증 및 수정 시작")
            logging.info(f"   최대 재시도: {max_retries}회")
            logging.info(f"   NULL 임계치: {null_threshold:.1%} (ma120: {ma120_null_threshold:.1%})")
            
            for attempt in range(max_retries):
                logging.info(f"🔄 {attempt + 1}차 검증 시도")
                
                # 1. NULL 값 검사
                null_stats = self.check_technical_indicators_null_ratio()
                
                # 2. ma120은 별도 임계치 적용, 나머지는 기본 임계치 적용
                ma120_null_ratio = null_stats['null_counts']['ma120'] / null_stats['total_records'] if null_stats['total_records'] > 0 else 0
                other_null_ratio = max([
                    null_stats['null_counts']['ma5'] / null_stats['total_records'] if null_stats['total_records'] > 0 else 0,
                    null_stats['null_counts']['ma20'] / null_stats['total_records'] if null_stats['total_records'] > 0 else 0,
                    null_stats['null_counts']['ma60'] / null_stats['total_records'] if null_stats['total_records'] > 0 else 0,
                    null_stats['null_counts']['rsi'] / null_stats['total_records'] if null_stats['total_records'] > 0 else 0,
                    null_stats['null_counts']['macd'] / null_stats['total_records'] if null_stats['total_records'] > 0 else 0,
                    null_stats['null_counts']['bb_upper'] / null_stats['total_records'] if null_stats['total_records'] > 0 else 0,
                ])
                
                # 임계치 이하면 성공으로 간주
                if ma120_null_ratio < ma120_null_threshold and other_null_ratio < null_threshold:
                    logging.info(f"✅ 기술지표 검증 완료 (ma120 NULL 비율: {ma120_null_ratio:.2%}, 기타 NULL 비율: {other_null_ratio:.2%})")
                    return True
                
                # 3. 재시도 필요
                if attempt < max_retries - 1:
                    logging.warning(f"⚠️ 기술지표 NULL 값 발견 - {attempt + 1}차 재시도")
                    logging.warning(f"   ma120 NULL 비율: {ma120_null_ratio:.2%} (임계치: {ma120_null_threshold:.1%})")
                    logging.warning(f"   기타 지표 NULL 비율: {other_null_ratio:.2%} (임계치: {null_threshold:.1%})")
                    if self.fix_technical_indicators_for_failed_stocks(null_stats['failed_stocks']):
                        logging.info(f"✅ {attempt + 1}차 재수집 완료")
                    else:
                        logging.error(f"❌ {attempt + 1}차 재수집 실패")
                else:
                    # 최종 실패
                    logging.error(f"❌ {max_retries}회 재시도 후에도 기술지표 문제 지속")
                    logging.error(f"   ma120 최종 NULL 비율: {ma120_null_ratio:.2%} (임계치: {ma120_null_threshold:.1%})")
                    logging.error(f"   기타 지표 최종 NULL 비율: {other_null_ratio:.2%} (임계치: {null_threshold:.1%})")
                    logging.error(f"   문제 종목 수: {len(null_stats['failed_stocks'])}개")
                    
                    # 실패한 종목 리스트 저장
                    self.save_failed_stocks_report(null_stats['failed_stocks'])
                    return False
            
            return False
            
        except Exception as e:
            logging.error(f"❌ 기술지표 검증 및 수정 중 오류: {e}")
            return False


def main():
    """메인 함수 - 일봉 데이터 + 유통주식수 + 시가총액 통합 수집"""
    logging.info("🚀 주식 데이터 수집 프로그램 시작 (일봉 데이터 + 유통주식수 + 시가총액 통합 수집)")
    logging.info("="*60)
    
    collector = StockDataCollector()
    
    try:
        # 기본 동작: 전체 종목 일봉 데이터 + 유통주식수 + 시가총액 통합 수집
        logging.info("📊 전체 종목 일봉 데이터 + 유통주식수 + 시가총액 통합 수집을 시작합니다.")
        total_success, total_failed = collector.collect_all_stocks()
        
        if total_success > 0:
            logging.info(f"\n🎉 전체 종목 통합 데이터 수집 완료!")
            logging.info(f"✅ 성공: {total_success}개")
            logging.info(f"❌ 실패: {total_failed}개")
            logging.info(f"\n💡 수집된 데이터:")
            logging.info(f"   - 일봉 데이터 (OHLCV)")
            logging.info(f"   - 유통주식수 (outstanding_shares)")
            logging.info(f"   - 시가총액 (market_cap)")
            logging.info(f"   - 기술적 지표 (MA, RSI, MACD, 볼린저밴드)")
            logging.info(f"\n💡 다음 단계:")
            logging.info(f"   1. 데이터베이스에서 수집된 데이터 확인")
            logging.info(f"   2. 전일 데이터 품질 검증 결과 확인")
            logging.info(f"   3. 필요시 주봉, 월봉 데이터 생성")
        else:
            logging.error("\n❌ 모든 종목 통합 데이터 수집에 실패했습니다.")
            
    except Exception as e:
        logging.error(f"데이터 수집 중 오류: {e}")

if __name__ == "__main__":
    main()
