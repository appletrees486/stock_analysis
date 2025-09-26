#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터 검증 및 수정 모듈
daily_data 테이블의 거래량 0 + OHLC 변동 논리적 모순 데이터 검증 및 수정
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from database_config import DatabaseManager
import time
import yfinance as yf
from typing import List, Dict, Tuple, Optional
import concurrent.futures
import threading

# PyKrx 라이브러리 import
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError as e:
    PYKRX_AVAILABLE = False
    print(f"⚠️ PyKrx 라이브러리 import 실패: {e}")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_validation_fix.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DataValidationAndFix:
    def __init__(self):
        """데이터 검증 및 수정 클래스 초기화"""
        self.db = DatabaseManager()
        self.problem_data = []  # 문제 데이터 저장
        self.fixed_data = []    # 수정된 데이터 저장
        self.failed_fixes = []  # 수정 실패 데이터 저장
        
        # 진행률 추적
        self.total_stocks = 0
        self.processed_stocks = 0
        self.progress_callback = None
        
    def set_progress_callback(self, callback):
        """진행률 업데이트 콜백 함수 설정"""
        self.progress_callback = callback
    
    def update_progress(self, current, total, message=""):
        """진행률 업데이트"""
        if self.progress_callback:
            try:
                self.progress_callback(current, total, message)
            except Exception as e:
                logging.warning(f"진행률 업데이트 콜백 실행 중 오류: {e}")
    
    def scan_problem_data(self) -> List[Dict]:
        """
        daily_data 테이블에서 거래량 0 + OHLC 변동 논리적 모순 데이터 검색
        
        Returns:
            List[Dict]: 문제 데이터 리스트
        """
        logging.info("🔍 daily_data 테이블 전수 조사 시작...")
        
        try:
            if not self.db.connect():
                logging.error("❌ 데이터베이스 연결 실패")
                return []
            
            # 거래량이 0인데 OHLC가 변동하는 데이터 찾기
            query = """
            SELECT DISTINCT stock_code
            FROM daily_data 
            WHERE volume = 0 
            AND (
                open != close OR 
                high != low OR 
                high != open OR 
                low != open
            )
            ORDER BY stock_code
            """
            
            result = self.db.fetch_all(query)
            
            if not result:
                logging.info("✅ 문제 데이터가 없습니다.")
                return []
            
            problem_stocks = [row['stock_code'] for row in result]
            logging.info(f"🚨 문제 데이터 발견: {len(problem_stocks)}개 종목")
            
            # 각 종목별 상세 정보 수집
            detailed_problems = []
            
            for i, stock_code in enumerate(problem_stocks):
                self.update_progress(i + 1, len(problem_stocks), f"종목 {stock_code} 분석 중...")
                
                # 해당 종목의 문제 데이터 상세 조회
                detail_query = """
                SELECT trade_date, open, high, low, close, volume, trading_value
                FROM daily_data 
                WHERE stock_code = %s 
                AND volume = 0 
                AND (
                    open != close OR 
                    high != low OR 
                    high != open OR 
                    low != open
                )
                ORDER BY trade_date
                """
                
                detail_result = self.db.fetch_all(detail_query, (stock_code,))
                
                if detail_result:
                    # 종목명 조회
                    name_query = "SELECT stock_name FROM stocks WHERE stock_code = %s"
                    name_result = self.db.fetch_one(name_query, (stock_code,))
                    stock_name = name_result['stock_name'] if name_result else stock_code
                    
                    detailed_problems.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'problem_count': len(detail_result),
                        'problem_dates': [row['trade_date'] for row in detail_result],
                        'sample_data': detail_result[:5]  # 처음 5개 샘플
                    })
            
            self.db.disconnect()
            self.problem_data = detailed_problems
            
            logging.info(f"📊 문제 데이터 분석 완료:")
            logging.info(f"   - 문제 종목 수: {len(detailed_problems)}개")
            logging.info(f"   - 총 문제 데이터 수: {sum(p['problem_count'] for p in detailed_problems)}개")
            
            return detailed_problems
            
        except Exception as e:
            logging.error(f"❌ 문제 데이터 스캔 중 오류: {e}")
            if self.db.connection:
                self.db.disconnect()
            return []
    
    def fix_stock_data(self, stock_code: str, stock_name: str) -> Dict:
        """
        특정 종목의 데이터 수정
        
        Args:
            stock_code (str): 종목코드
            stock_name (str): 종목명
            
        Returns:
            Dict: 수정 결과
        """
        logging.info(f"🔧 {stock_code} ({stock_name}) 데이터 수정 시작...")
        
        fix_result = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'pykrx_success': False,
            'yfinance_success': False,
            'trading_value_calculated': False,
            'updated_records': 0,
            'error_message': None
        }
        
        try:
            # 1단계: pykrx로 재수집 시도
            if PYKRX_AVAILABLE:
                fix_result = self._try_pykrx_fix(stock_code, stock_name, fix_result)
            
            # 2단계: pykrx 실패 시 yfinance로 시도
            if not fix_result['pykrx_success']:
                fix_result = self._try_yfinance_fix(stock_code, stock_name, fix_result)
            
            # 3단계: 거래대금 계산 (공식 적용)
            if fix_result['pykrx_success'] or fix_result['yfinance_success']:
                fix_result = self._calculate_trading_value(stock_code, fix_result)
            
            return fix_result
            
        except Exception as e:
            logging.error(f"❌ {stock_code} 데이터 수정 중 오류: {e}")
            fix_result['error_message'] = str(e)
            return fix_result
    
    def _try_pykrx_fix(self, stock_code: str, stock_name: str, fix_result: Dict) -> Dict:
        """pykrx로 데이터 재수집 시도"""
        try:
            logging.info(f"   📡 pykrx로 {stock_code} 재수집 시도...")
            
            # 문제 데이터의 날짜 범위 조회
            if not self.db.connect():
                return fix_result
            
            date_query = """
            SELECT MIN(trade_date) as start_date, MAX(trade_date) as end_date
            FROM daily_data 
            WHERE stock_code = %s 
            AND volume = 0 
            AND (
                open != close OR 
                high != low OR 
                high != open OR 
                low != open
            )
            """
            
            date_result = self.db.fetch_one(date_query, (stock_code,))
            if not date_result:
                self.db.disconnect()
                return fix_result
            
            start_date = date_result['start_date']
            end_date = date_result['end_date']
            
            # pykrx로 데이터 조회
            hist = stock.get_market_ohlcv_by_date(
                fromdate=start_date.strftime('%Y%m%d'),
                todate=end_date.strftime('%Y%m%d'),
                ticker=stock_code,
                adjusted=False
            )
            
            if hist is not None and len(hist) > 0:
                # 거래량이 0이 아닌 데이터가 있는지 확인
                non_zero_volume = hist[hist['거래량'] != 0]
                if len(non_zero_volume) > 0:
                    logging.info(f"   ✅ pykrx에서 {len(non_zero_volume)}개 거래량 데이터 발견")
                    fix_result['pykrx_success'] = True
                    fix_result['updated_records'] = self._update_database_with_pykrx_data(stock_code, hist)
                else:
                    logging.warning(f"   ⚠️ pykrx에서도 거래량이 모두 0")
            else:
                logging.warning(f"   ⚠️ pykrx에서 데이터를 가져올 수 없음")
            
            self.db.disconnect()
            return fix_result
            
        except Exception as e:
            logging.error(f"   ❌ pykrx 수정 시도 중 오류: {e}")
            fix_result['error_message'] = str(e)
            return fix_result
    
    def _try_yfinance_fix(self, stock_code: str, stock_name: str, fix_result: Dict) -> Dict:
        """yfinance로 데이터 재수집 시도"""
        try:
            logging.info(f"   📡 yfinance로 {stock_code} 재수집 시도...")
            
            # 한국 주식 심볼 생성 (KOSDAQ 우선)
            symbols = [f"{stock_code}.KQ", f"{stock_code}.KS", stock_code]
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    
                    # 문제 데이터의 날짜 범위 조회
                    if not self.db.connect():
                        continue
                    
                    date_query = """
                    SELECT MIN(trade_date) as start_date, MAX(trade_date) as end_date
                    FROM daily_data 
                    WHERE stock_code = %s 
                    AND volume = 0 
                    AND (
                        open != close OR 
                        high != low OR 
                        high != open OR 
                        low != open
                    )
                    """
                    
                    date_result = self.db.fetch_one(date_query, (stock_code,))
                    if not date_result:
                        self.db.disconnect()
                        continue
                    
                    start_date = date_result['start_date']
                    end_date = date_result['end_date']
                    
                    # yfinance로 데이터 조회
                    hist = ticker.history(
                        start=start_date.strftime('%Y-%m-%d'),
                        end=(end_date + timedelta(days=1)).strftime('%Y-%m-%d')
                    )
                    
                    if hist is not None and len(hist) > 0:
                        # 거래량이 0이 아닌 데이터가 있는지 확인
                        non_zero_volume = hist[hist['Volume'] != 0]
                        if len(non_zero_volume) > 0:
                            logging.info(f"   ✅ yfinance에서 {len(non_zero_volume)}개 거래량 데이터 발견")
                            fix_result['yfinance_success'] = True
                            fix_result['updated_records'] = self._update_database_with_yfinance_data(stock_code, hist)
                            break
                        else:
                            logging.warning(f"   ⚠️ yfinance에서도 거래량이 모두 0")
                    else:
                        logging.warning(f"   ⚠️ yfinance에서 데이터를 가져올 수 없음")
                    
                    self.db.disconnect()
                    
                except Exception as e:
                    logging.warning(f"   ⚠️ yfinance 심볼 {symbol} 시도 실패: {e}")
                    continue
            
            return fix_result
            
        except Exception as e:
            logging.error(f"   ❌ yfinance 수정 시도 중 오류: {e}")
            fix_result['error_message'] = str(e)
            return fix_result
    
    def _update_database_with_pykrx_data(self, stock_code: str, hist: pd.DataFrame) -> int:
        """pykrx 데이터로 데이터베이스 업데이트"""
        updated_count = 0
        
        try:
            for date, row in hist.iterrows():
                if row['거래량'] > 0:  # 거래량이 0이 아닌 경우만 업데이트
                    update_query = """
                    UPDATE daily_data 
                    SET volume = %s, trading_value = %s
                    WHERE stock_code = %s AND trade_date = %s
                    """
                    
                    # 거래대금 계산 (종가 × 거래량)
                    trading_value = int(row['종가'] * row['거래량'])
                    
                    params = (int(row['거래량']), trading_value, stock_code, date.date())
                    
                    if self.db.execute_query(update_query, params):
                        updated_count += 1
            
            logging.info(f"   ✅ pykrx 데이터로 {updated_count}개 레코드 업데이트")
            return updated_count
            
        except Exception as e:
            logging.error(f"   ❌ pykrx 데이터베이스 업데이트 중 오류: {e}")
            return updated_count
    
    def _update_database_with_yfinance_data(self, stock_code: str, hist: pd.DataFrame) -> int:
        """yfinance 데이터로 데이터베이스 업데이트"""
        updated_count = 0
        
        try:
            for date, row in hist.iterrows():
                if row['Volume'] > 0:  # 거래량이 0이 아닌 경우만 업데이트
                    update_query = """
                    UPDATE daily_data 
                    SET volume = %s, trading_value = %s
                    WHERE stock_code = %s AND trade_date = %s
                    """
                    
                    # 거래대금 계산 (종가 × 거래량)
                    trading_value = int(row['Close'] * row['Volume'])
                    
                    params = (int(row['Volume']), trading_value, stock_code, date.date())
                    
                    if self.db.execute_query(update_query, params):
                        updated_count += 1
            
            logging.info(f"   ✅ yfinance 데이터로 {updated_count}개 레코드 업데이트")
            return updated_count
            
        except Exception as e:
            logging.error(f"   ❌ yfinance 데이터베이스 업데이트 중 오류: {e}")
            return updated_count
    
    def _calculate_trading_value(self, stock_code: str, fix_result: Dict) -> Dict:
        """거래대금 계산 (공식 적용)"""
        try:
            logging.info(f"   🧮 {stock_code} 거래대금 계산 중...")
            
            if not self.db.connect():
                return fix_result
            
            # 거래대금이 없는 데이터 조회
            query = """
            SELECT trade_date, open, high, low, close, volume
            FROM daily_data 
            WHERE stock_code = %s 
            AND (trading_value IS NULL OR trading_value = 0)
            AND volume > 0
            ORDER BY trade_date
            """
            
            result = self.db.fetch_all(query, (stock_code,))
            
            if result:
                updated_count = 0
                
                for row in result:
                    # 거래대금 계산: (고가 + 저가 + 종가) / 3 × 거래량
                    typical_price = (row['high'] + row['low'] + row['close']) / 3
                    trading_value = int(typical_price * row['volume'])
                    
                    update_query = """
                    UPDATE daily_data 
                    SET trading_value = %s
                    WHERE stock_code = %s AND trade_date = %s
                    """
                    
                    params = (trading_value, stock_code, row['trade_date'])
                    
                    if self.db.execute_query(update_query, params):
                        updated_count += 1
                
                fix_result['trading_value_calculated'] = True
                fix_result['updated_records'] += updated_count
                logging.info(f"   ✅ 거래대금 계산으로 {updated_count}개 레코드 추가 업데이트")
            
            self.db.disconnect()
            return fix_result
            
        except Exception as e:
            logging.error(f"   ❌ 거래대금 계산 중 오류: {e}")
            fix_result['error_message'] = str(e)
            return fix_result
    
    def run_full_validation_and_fix(self):
        """전체 검증 및 수정 프로세스 실행"""
        logging.info("🚀 데이터 검증 및 수정 프로세스 시작")
        
        # 1단계: 문제 데이터 스캔
        problem_data = self.scan_problem_data()
        
        if not problem_data:
            logging.info("✅ 수정할 문제 데이터가 없습니다.")
            return
        
        self.total_stocks = len(problem_data)
        self.processed_stocks = 0
        
        # 2단계: 각 종목별 데이터 수정
        for i, problem in enumerate(problem_data):
            self.processed_stocks = i + 1
            self.update_progress(
                self.processed_stocks, 
                self.total_stocks, 
                f"수정 중: {problem['stock_code']} ({problem['stock_name']})"
            )
            
            fix_result = self.fix_stock_data(
                problem['stock_code'], 
                problem['stock_name']
            )
            
            if fix_result['pykrx_success'] or fix_result['yfinance_success']:
                self.fixed_data.append(fix_result)
                logging.info(f"✅ {problem['stock_code']} 수정 완료: {fix_result['updated_records']}개 레코드")
            else:
                self.failed_fixes.append(fix_result)
                logging.error(f"❌ {problem['stock_code']} 수정 실패: {fix_result.get('error_message', 'Unknown error')}")
        
        # 3단계: 결과 요약
        self._print_summary()
    
    def _print_summary(self):
        """수정 결과 요약 출력"""
        logging.info("📊 데이터 검증 및 수정 결과 요약")
        logging.info(f"   - 총 문제 종목: {self.total_stocks}개")
        logging.info(f"   - 수정 성공: {len(self.fixed_data)}개")
        logging.info(f"   - 수정 실패: {len(self.failed_fixes)}개")
        
        if self.fixed_data:
            total_updated = sum(fix['updated_records'] for fix in self.fixed_data)
            logging.info(f"   - 총 업데이트된 레코드: {total_updated}개")
        
        if self.failed_fixes:
            logging.warning("❌ 수정 실패한 종목들:")
            for fix in self.failed_fixes:
                logging.warning(f"   - {fix['stock_code']} ({fix['stock_name']}): {fix.get('error_message', 'Unknown error')}")

def main():
    """메인 실행 함수"""
    validator = DataValidationAndFix()
    
    # 진행률 콜백 설정
    def progress_callback(current, total, message):
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"[{percentage:.1f}%] {message}")
    
    validator.set_progress_callback(progress_callback)
    
    # 전체 검증 및 수정 실행
    validator.run_full_validation_and_fix()

if __name__ == "__main__":
    main()
