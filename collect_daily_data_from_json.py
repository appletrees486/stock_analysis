#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 파일의 주식 종목들에 대한 일봉 데이터 수집 및 DB 저장
"""

import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import DatabaseManager

# 로깅 설정 - 더 상세한 정보 표시
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_data_collection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DailyDataCollector:
    def __init__(self):
        """일봉 데이터 수집기 초기화"""
        self.db = DatabaseManager()
        self.collection_date = datetime.now().strftime('%Y-%m-%d')
        self.start_time = datetime.now()
        
    def load_stock_list_from_json(self, json_file_path):
        """JSON 파일에서 주식 종목 목록 로드"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                stock_list = json.load(f)
            
            logging.info(f"✅ JSON 파일에서 {len(stock_list)}개 종목 로드 완료")
            logging.info(f"📋 종목 목록:")
            for i, stock in enumerate(stock_list, 1):
                logging.info(f"   {i:2d}. {stock['종목명']}({stock['종목번호']}) - {stock['시장구분']}")
            return stock_list
            
        except Exception as e:
            logging.error(f"❌ JSON 파일 로드 실패: {e}")
            return []
    
    def calculate_technical_indicators(self, df):
        """기술적 지표 계산 (일봉 기준)"""
        try:
            logging.info(f"   🔧 기술적 지표 계산 중...")
            
            # 이동평균선 (5, 20, 60, 120일)
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()
            
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
            
            logging.info(f"   ✅ 기술적 지표 계산 완료")
            return df
            
        except Exception as e:
            logging.error(f"   ❌ 기술적 지표 계산 실패: {e}")
            return df
    
    def get_stock_data(self, stock_code, market_type):
        """주식 일봉 데이터 조회 (240일 = 1년)"""
        try:
            logging.info(f"   🔍 Yahoo Finance에서 데이터 조회 중...")
            
            # 시장 구분에 따른 Yahoo Finance 심볼 설정
            if market_type == "KOSPI":
                ticker_symbol = f"{stock_code}.KS"
            elif market_type == "KOSDAQ":
                ticker_symbol = f"{stock_code}.KQ"
            else:
                ticker_symbol = f"{stock_code}.KS"  # 기본값
            
            ticker = yf.Ticker(ticker_symbol)
            
            # 240일 (1년) 데이터 조회
            hist = ticker.history(period="240d")
            
            if not hist.empty:
                logging.info(f"   ✅ 데이터 조회 완료: {len(hist)}일")
                logging.info(f"   📅 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
                logging.info(f"   💰 최근 종가: {hist['Close'].iloc[-1]:,.0f}원")
                logging.info(f"   📊 최근 거래량: {hist['Volume'].iloc[-1]:,}")
                
                # 종목명 가져오기
                stock_name = ticker.info.get('longName', stock_code)
                if not stock_name or stock_name == 'N/A':
                    stock_name = stock_code
                
                return hist, stock_name
            else:
                logging.warning(f"   ❌ 데이터가 없습니다")
                return None, None
                
        except Exception as e:
            logging.error(f"   ❌ 데이터 조회 실패: {e}")
            return None, None
    
    def create_daily_data_table(self):
        """일봉 데이터 테이블 생성"""
        try:
            logging.info("🏗️ 일봉 데이터 테이블 생성 중...")
            
            create_table_query = """
            CREATE TABLE IF NOT EXISTS daily_stock_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(100) NOT NULL,
                market_type VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                open_price DECIMAL(10,2),
                high_price DECIMAL(10,2),
                low_price DECIMAL(10,2),
                close_price DECIMAL(10,2),
                volume BIGINT,
                ma5 DECIMAL(10,2),
                ma20 DECIMAL(10,2),
                ma60 DECIMAL(10,2),
                ma120 DECIMAL(10,2),
                macd DECIMAL(10,4),
                macd_signal DECIMAL(10,4),
                macd_histogram DECIMAL(10,4),
                rsi DECIMAL(5,2),
                collection_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_stock_date (stock_code, date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            if self.db.execute_query(create_table_query):
                logging.info("✅ 일봉 데이터 테이블 생성 완료")
                return True
            else:
                logging.error("❌ 일봉 데이터 테이블 생성 실패")
                return False
                
        except Exception as e:
            logging.error(f"테이블 생성 오류: {e}")
            return False
    
    def save_daily_data_to_db(self, stock_code, stock_name, market_type, df):
        """일봉 데이터를 DB에 저장"""
        try:
            if df is None or df.empty:
                logging.warning(f"   ❌ 저장할 데이터가 없습니다")
                return False
            
            logging.info(f"   💾 데이터베이스에 저장 중...")
            
            # 데이터 삽입 쿼리
            insert_query = """
            INSERT INTO daily_stock_data (
                stock_code, stock_name, market_type, date, open_price, high_price, 
                low_price, close_price, volume, ma5, ma20, ma60, ma120,
                macd, macd_signal, macd_histogram, rsi, collection_date
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                volume = VALUES(volume),
                ma5 = VALUES(ma5),
                ma20 = VALUES(ma20),
                ma60 = VALUES(ma60),
                ma120 = VALUES(ma120),
                macd = VALUES(macd),
                macd_signal = VALUES(macd_signal),
                macd_histogram = VALUES(macd_histogram),
                rsi = VALUES(rsi),
                collection_date = VALUES(collection_date)
            """
            
            # 데이터 준비
            data_to_insert = []
            for date, row in df.iterrows():
                data_row = (
                    stock_code,
                    stock_name,
                    market_type,
                    date.strftime('%Y-%m-%d'),
                    float(row['Open']) if pd.notna(row['Open']) else None,
                    float(row['High']) if pd.notna(row['High']) else None,
                    float(row['Low']) if pd.notna(row['Low']) else None,
                    float(row['Close']) if pd.notna(row['Close']) else None,
                    int(row['Volume']) if pd.notna(row['Volume']) else None,
                    float(row['MA5']) if pd.notna(row['MA5']) else None,
                    float(row['MA20']) if pd.notna(row['MA20']) else None,
                    float(row['MA60']) if pd.notna(row['MA60']) else None,
                    float(row['MA120']) if pd.notna(row['MA120']) else None,
                    float(row['MACD']) if pd.notna(row['MACD']) else None,
                    float(row['MACD_Signal']) if pd.notna(row['MACD_Signal']) else None,
                    float(row['MACD_Histogram']) if pd.notna(row['MACD_Histogram']) else None,
                    float(row['RSI']) if pd.notna(row['RSI']) else None,
                    self.collection_date
                )
                data_to_insert.append(data_row)
            
            # 배치 삽입 실행
            if self.db.execute_many(insert_query, data_to_insert):
                self.db.commit()
                logging.info(f"   ✅ DB 저장 완료: {len(data_to_insert)}일의 데이터")
                return True
            else:
                logging.error(f"   ❌ DB 저장 실패")
                return False
                
        except Exception as e:
            logging.error(f"   ❌ DB 저장 오류: {e}")
            return False
    
    def show_progress_bar(self, current, total, width=50):
        """진행률 바 표시"""
        progress = current / total
        filled = int(width * progress)
        bar = '█' * filled + '░' * (width - filled)
        percentage = progress * 100
        return f"[{bar}] {percentage:5.1f}% ({current:3d}/{total:3d})"
    
    def estimate_remaining_time(self, current, total, elapsed_time):
        """남은 시간 추정"""
        if current == 0:
            return "계산 중..."
        
        avg_time_per_item = elapsed_time / current
        remaining_items = total - current
        remaining_time = avg_time_per_item * remaining_items
        
        if remaining_time < 60:
            return f"{remaining_time:.0f}초"
        elif remaining_time < 3600:
            return f"{remaining_time/60:.0f}분"
        else:
            return f"{remaining_time/3600:.1f}시간"
    
    def collect_all_stocks_data(self, json_file_path):
        """모든 주식 종목의 일봉 데이터 수집 및 저장"""
        try:
            # 데이터베이스 연결
            logging.info("🔌 데이터베이스 연결 중...")
            if not self.db.connect():
                logging.error("❌ 데이터베이스 연결 실패")
                return False
            logging.info("✅ 데이터베이스 연결 성공")
            
            # 테이블 생성
            if not self.create_daily_data_table():
                logging.error("❌ 테이블 생성 실패")
                return False
            
            # 주식 목록 로드
            stock_list = self.load_stock_list_from_json(json_file_path)
            if not stock_list:
                logging.error("❌ 주식 목록 로드 실패")
                return False
            
            # 수집 결과 통계
            success_count = 0
            fail_count = 0
            total_data_points = 0
            
            logging.info("=" * 80)
            logging.info("🚀 주식 일봉 데이터 수집 시작")
            logging.info(f"📊 총 처리 대상: {len(stock_list)}개 종목")
            logging.info(f"📅 수집 일시: {self.collection_date}")
            logging.info(f"⏰ 시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logging.info("=" * 80)
            
            for i, stock_info in enumerate(stock_list, 1):
                stock_code = stock_info['종목번호']
                stock_name = stock_info['종목명']
                market_type = stock_info['시장구분']
                
                # 현재 시간과 경과 시간 계산
                current_time = datetime.now()
                elapsed_time = (current_time - self.start_time).total_seconds()
                
                # 진행률 표시
                progress_bar = self.show_progress_bar(i, len(stock_list))
                remaining_time = self.estimate_remaining_time(i, len(stock_list), elapsed_time)
                
                logging.info("")
                logging.info(f"📊 [{i:2d}/{len(stock_list):2d}] {stock_name}({stock_code}) - {market_type}")
                logging.info(f"⏱️ 진행률: {progress_bar}")
                logging.info(f"⏳ 경과 시간: {elapsed_time/60:.1f}분 | 예상 남은 시간: {remaining_time}")
                logging.info("-" * 60)
                
                try:
                    # 주식 데이터 조회
                    hist, retrieved_name = self.get_stock_data(stock_code, market_type)
                    
                    if hist is not None and retrieved_name:
                        # 기술적 지표 계산
                        hist_with_indicators = self.calculate_technical_indicators(hist)
                        
                        # DB에 저장
                        if self.save_daily_data_to_db(stock_code, retrieved_name, market_type, hist_with_indicators):
                            success_count += 1
                            total_data_points += len(hist_with_indicators)
                            logging.info(f"✅ {stock_name}({stock_code}): 완료 - {len(hist_with_indicators)}일 데이터")
                        else:
                            fail_count += 1
                            logging.error(f"❌ {stock_name}({stock_code}): 저장 실패")
                    else:
                        fail_count += 1
                        logging.warning(f"⚠️ {stock_name}({stock_code}): 데이터 없음")
                    
                    # API 호출 제한 방지를 위한 대기
                    logging.info(f"   ⏳ 1초 대기 중...")
                    time.sleep(1)
                    
                except Exception as e:
                    fail_count += 1
                    logging.error(f"❌ {stock_name}({stock_code}): 처리 중 오류 발생 - {e}")
                
                # 중간 진행률 요약 (10개마다)
                if i % 10 == 0 or i == len(stock_list):
                    logging.info("")
                    logging.info("📈 중간 진행률 요약")
                    logging.info(f"   ✅ 성공: {success_count}개")
                    logging.info(f"   ❌ 실패: {fail_count}개")
                    logging.info(f"   📊 총 데이터 포인트: {total_data_points:,}개")
                    logging.info(f"   ⏱️ 경과 시간: {elapsed_time/60:.1f}분")
                    logging.info("-" * 60)
            
            # 최종 결과 요약
            total_time = (datetime.now() - self.start_time).total_seconds()
            
            logging.info("")
            logging.info("=" * 80)
            logging.info("🎯 일봉 데이터 수집 완료 요약")
            logging.info(f"✅ 성공: {success_count}개")
            logging.info(f"❌ 실패: {fail_count}개")
            logging.info(f"📊 총 처리: {len(stock_list)}개")
            logging.info(f"📈 총 데이터 포인트: {total_data_points:,}개")
            logging.info(f"📅 수집 일시: {self.collection_date}")
            logging.info(f"⏰ 시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logging.info(f"⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logging.info(f"⏱️ 총 소요 시간: {total_time/60:.1f}분")
            if success_count > 0:
                avg_time_per_stock = total_time / success_count
                logging.info(f"📊 종목당 평균 처리 시간: {avg_time_per_stock:.1f}초")
            logging.info("=" * 80)
            
            return success_count > 0
            
        except Exception as e:
            logging.error(f"일봉 데이터 수집 중 오류 발생: {e}")
            return False
        
        finally:
            # 데이터베이스 연결 해제
            logging.info("🔌 데이터베이스 연결 해제 중...")
            self.db.disconnect()
            logging.info("✅ 데이터베이스 연결 해제 완료")

def main():
    """메인 실행 함수"""
    try:
        # JSON 파일 경로
        json_file_path = "stock_list_20250819_161304.json"
        
        if not os.path.exists(json_file_path):
            logging.error(f"❌ JSON 파일을 찾을 수 없습니다: {json_file_path}")
            return
        
        # 일봉 데이터 수집기 초기화 및 실행
        collector = DailyDataCollector()
        
        logging.info("🚀 주식 일봉 데이터 수집 시작")
        logging.info(f"📁 JSON 파일: {json_file_path}")
        
        # 데이터 수집 실행
        success = collector.collect_all_stocks_data(json_file_path)
        
        if success:
            logging.info("🎉 일봉 데이터 수집이 성공적으로 완료되었습니다!")
        else:
            logging.error("❌ 일봉 데이터 수집 중 오류가 발생했습니다.")
            
    except Exception as e:
        logging.error(f"메인 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
