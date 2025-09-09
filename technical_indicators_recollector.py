#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기술적 지표 재수집 스크립트
technical_indicators 테이블의 NULL 값 문제를 해결하기 위한 전용 스크립트
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from database_config import DatabaseManager
import time
import random
from typing import List, Tuple, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('technical_indicators_recollector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class TechnicalIndicatorsRecollector:
    """기술적 지표 재수집 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        self.batch_size = 100  # 배치 크기
        self.delay_between_requests = 0.1  # 요청 간 딜레이
        
    def calculate_technical_indicators(self, df):
        """기술적 지표 계산 (stock_data_collector.py와 동일한 로직)"""
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
    
    def get_all_stock_codes(self) -> List[Tuple[str, str]]:
        """모든 종목 코드 조회"""
        try:
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
            self.db.disconnect()
    
    def get_daily_data_for_stock(self, stock_code: str) -> Optional[pd.DataFrame]:
        """특정 종목의 일봉 데이터 조회"""
        try:
            if not self.db.connect():
                logging.error("데이터베이스 연결 실패")
                return None
            
            query = """
            SELECT trade_date, open, high, low, close, volume
            FROM daily_data 
            WHERE stock_code = %s 
            ORDER BY trade_date ASC
            """
            
            result = self.db.fetch_all(query, (stock_code,))
            
            if result:
                df = pd.DataFrame(result)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df.set_index('trade_date', inplace=True)
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                
                # Decimal 타입을 float로 변환
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = df[col].astype(float)
                
                logging.info(f"✅ {stock_code}: {len(df)}일의 일봉 데이터 조회 완료")
                return df
            else:
                logging.warning(f"⚠️ {stock_code}: 일봉 데이터가 없습니다")
                return None
                
        except Exception as e:
            logging.error(f"❌ {stock_code} 일봉 데이터 조회 실패: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def save_technical_indicators_fixed(self, stock_code: str, df_with_indicators: pd.DataFrame) -> bool:
        """기술적 지표를 데이터베이스에 저장 (수정된 버전 - NULL 값 허용)"""
        try:
            if not self.db.connect():
                logging.error("데이터베이스 연결 실패")
                return False
            
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
                # NaN 값 처리 (NULL 값 허용)
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
            logging.error(f"❌ {stock_code} 기술적 지표 저장 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def process_single_stock(self, stock_code: str, stock_name: str) -> bool:
        """단일 종목의 보조지표 재수집"""
        try:
            logging.info(f"📊 {stock_code} ({stock_name}) 보조지표 재수집 시작")
            
            # 1. 일봉 데이터 조회
            daily_data = self.get_daily_data_for_stock(stock_code)
            if daily_data is None or daily_data.empty:
                logging.warning(f"⚠️ {stock_code} ({stock_name}): 일봉 데이터가 없어 건너뜀")
                return False
            
            # 2. 기술적 지표 계산
            df_with_indicators = self.calculate_technical_indicators(daily_data.copy())
            
            # 3. 기술적 지표 저장
            if self.save_technical_indicators_fixed(stock_code, df_with_indicators):
                logging.info(f"✅ {stock_code} ({stock_name}) 보조지표 재수집 완료")
                return True
            else:
                logging.error(f"❌ {stock_code} ({stock_name}) 보조지표 저장 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ {stock_code} ({stock_name}) 보조지표 재수집 중 오류: {e}")
            return False
    
    def recollect_all_technical_indicators(self, specific_codes: Optional[List[str]] = None):
        """전체 종목의 보조지표 재수집"""
        logging.info("🚀 전체 종목 보조지표 재수집 시작")
        logging.info("="*60)
        
        # 종목 목록 조회
        if specific_codes:
            # 특정 종목만 처리
            all_stocks = []
            for stock_code in specific_codes:
                if not self.db.connect():
                    continue
                query = "SELECT stock_code, stock_name FROM stocks WHERE stock_code = %s AND is_active = TRUE"
                result = self.db.fetch_one(query, (stock_code,))
                if result:
                    all_stocks.append((result['stock_code'], result['stock_name']))
                self.db.disconnect()
        else:
            # 모든 종목 처리
            all_stocks = self.get_all_stock_codes()
        
        if not all_stocks:
            logging.error("처리할 종목이 없습니다.")
            return
        
        # 배치로 나누기
        total_stocks = len(all_stocks)
        total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
        
        logging.info(f"📊 총 {total_stocks}개 종목을 {total_batches}개 배치로 나누어 처리합니다.")
        logging.info(f"📦 배치 크기: {self.batch_size}개")
        
        total_success = 0
        total_failed = 0
        
        for batch_num in range(1, total_batches + 1):
            start_idx = (batch_num - 1) * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_stocks)
            stock_batch = all_stocks[start_idx:end_idx]
            
            logging.info(f"🚀 배치 {batch_num}/{total_batches} 시작 ({len(stock_batch)}개 종목)")
            logging.info("="*60)
            
            batch_success = 0
            batch_failed = 0
            
            for i, (stock_code, stock_name) in enumerate(stock_batch, 1):
                logging.info(f"📊 [{i}/{len(stock_batch)}] {stock_code} ({stock_name}) 처리 중...")
                
                try:
                    if self.process_single_stock(stock_code, stock_name):
                        batch_success += 1
                    else:
                        batch_failed += 1
                    
                    # API 호출 간격 조절
                    time.sleep(self.delay_between_requests + random.uniform(0.05, 0.15))
                    
                except Exception as e:
                    logging.error(f"❌ {stock_code} ({stock_name}) 처리 중 오류: {e}")
                    batch_failed += 1
            
            total_success += batch_success
            total_failed += batch_failed
            
            logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
            logging.info(f"✅ 성공: {batch_success}개, ❌ 실패: {batch_failed}개")
            logging.info("="*60)
            
            # 배치 간 딜레이
            if batch_num < total_batches:
                logging.info(f"⏳ 다음 배치까지 2초 대기...")
                time.sleep(2)
        
        logging.info(f"\n🎉 전체 보조지표 재수집 완료!")
        logging.info(f"✅ 총 성공: {total_success}개")
        logging.info(f"❌ 총 실패: {total_failed}개")
        logging.info(f"📊 성공률: {(total_success / total_stocks * 100):.1f}%")
        
        return total_success, total_failed
    
    def check_technical_indicators_status(self, stock_code: str = None) -> dict:
        """보조지표 상태 확인"""
        try:
            if not self.db.connect():
                logging.error("데이터베이스 연결 실패")
                return {}
            
            if stock_code:
                # 특정 종목 확인
                query = """
                SELECT 
                    COUNT(*) as total_records,
                    SUM(CASE WHEN ma5 IS NULL THEN 1 ELSE 0 END) as ma5_null,
                    SUM(CASE WHEN ma20 IS NULL THEN 1 ELSE 0 END) as ma20_null,
                    SUM(CASE WHEN ma60 IS NULL THEN 1 ELSE 0 END) as ma60_null,
                    SUM(CASE WHEN ma120 IS NULL THEN 1 ELSE 0 END) as ma120_null,
                    SUM(CASE WHEN rsi IS NULL THEN 1 ELSE 0 END) as rsi_null,
                    SUM(CASE WHEN macd IS NULL THEN 1 ELSE 0 END) as macd_null
                FROM technical_indicators 
                WHERE stock_code = %s
                """
                result = self.db.fetch_one(query, (stock_code,))
            else:
                # 전체 종목 확인
                query = """
                SELECT 
                    COUNT(DISTINCT stock_code) as total_stocks,
                    COUNT(*) as total_records,
                    SUM(CASE WHEN ma5 IS NULL THEN 1 ELSE 0 END) as ma5_null,
                    SUM(CASE WHEN ma20 IS NULL THEN 1 ELSE 0 END) as ma20_null,
                    SUM(CASE WHEN ma60 IS NULL THEN 1 ELSE 0 END) as ma60_null,
                    SUM(CASE WHEN ma120 IS NULL THEN 1 ELSE 0 END) as ma120_null,
                    SUM(CASE WHEN rsi IS NULL THEN 1 ELSE 0 END) as rsi_null,
                    SUM(CASE WHEN macd IS NULL THEN 1 ELSE 0 END) as macd_null
                FROM technical_indicators
                """
                result = self.db.fetch_one(query)
            
            if result:
                logging.info(f"📊 보조지표 상태:")
                if stock_code:
                    logging.info(f"   종목: {stock_code}")
                else:
                    logging.info(f"   전체 종목: {result['total_stocks']}개")
                logging.info(f"   총 레코드: {result['total_records']:,}개")
                logging.info(f"   MA5 NULL: {result['ma5_null']:,}개 ({result['ma5_null']/result['total_records']*100:.1f}%)")
                logging.info(f"   MA20 NULL: {result['ma20_null']:,}개 ({result['ma20_null']/result['total_records']*100:.1f}%)")
                logging.info(f"   MA60 NULL: {result['ma60_null']:,}개 ({result['ma60_null']/result['total_records']*100:.1f}%)")
                logging.info(f"   MA120 NULL: {result['ma120_null']:,}개 ({result['ma120_null']/result['total_records']*100:.1f}%)")
                logging.info(f"   RSI NULL: {result['rsi_null']:,}개 ({result['rsi_null']/result['total_records']*100:.1f}%)")
                logging.info(f"   MACD NULL: {result['macd_null']:,}개 ({result['macd_null']/result['total_records']*100:.1f}%)")
                return result
            else:
                logging.warning("보조지표 데이터가 없습니다.")
                return {}
                
        except Exception as e:
            logging.error(f"보조지표 상태 확인 실패: {e}")
            return {}
        finally:
            self.db.disconnect()

def main():
    """메인 함수"""
    print("🚀 기술적 지표 재수집 프로그램 시작")
    print("="*60)
    
    recollector = TechnicalIndicatorsRecollector()
    
    try:
        # 현재 상태 확인
        print("📊 현재 보조지표 상태 확인 중...")
        recollector.check_technical_indicators_status()
        
        # 사용자 확인
        response = input("\n전체 종목의 보조지표를 재수집하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("사용자에 의해 중단되었습니다.")
            return
        
        # 보조지표 재수집 실행
        print("\n🔄 보조지표 재수집 시작...")
        success, failed = recollector.recollect_all_technical_indicators()
        
        # 재수집 후 상태 확인
        print("\n📊 재수집 후 보조지표 상태:")
        recollector.check_technical_indicators_status()
        
        if success > 0:
            print(f"\n🎉 보조지표 재수집 완료!")
            print(f"✅ 성공: {success}개")
            print(f"❌ 실패: {failed}개")
        else:
            print("\n❌ 보조지표 재수집에 실패했습니다.")
            
    except Exception as e:
        logging.error(f"보조지표 재수집 중 오류: {e}")
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
