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
        self.batch_size = 200  # 배치 크기 (100 → 200) [최적화]
        self.delay_between_requests = 0  # 요청 간 딜레이 제거 (DB 작업이므로 불필요) [최적화]
        
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
    
    def get_batch_daily_data(self, stock_codes: List[str]) -> dict:
        """배치로 여러 종목의 일봉 데이터 한 번에 조회 [최적화]"""
        try:
            if not stock_codes:
                return {}
            
            # IN 절을 위한 플레이스홀더 생성
            placeholders = ','.join(['%s'] * len(stock_codes))
            query = f"""
            SELECT stock_code, trade_date, open, high, low, close, volume
            FROM daily_data 
            WHERE stock_code IN ({placeholders})
            ORDER BY stock_code, trade_date ASC
            """
            
            result = self.db.fetch_all(query, tuple(stock_codes))
            
            if not result:
                logging.warning(f"⚠️ 배치 조회 결과 없음")
                return {}
            
            # 종목별로 데이터프레임 생성
            stock_data_dict = {}
            df_all = pd.DataFrame(result)
            
            for stock_code in stock_codes:
                stock_df = df_all[df_all['stock_code'] == stock_code].copy()
                if not stock_df.empty:
                    stock_df['trade_date'] = pd.to_datetime(stock_df['trade_date'])
                    stock_df.set_index('trade_date', inplace=True)
                    stock_df = stock_df[['open', 'high', 'low', 'close', 'volume']]
                    stock_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    
                    # Decimal 타입을 float로 변환
                    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                        stock_df[col] = stock_df[col].astype(float)
                    
                    stock_data_dict[stock_code] = stock_df
            
            logging.info(f"✅ 배치 조회 완료: {len(stock_data_dict)}/{len(stock_codes)}개 종목")
            return stock_data_dict
                
        except Exception as e:
            logging.error(f"❌ 배치 일봉 데이터 조회 실패: {e}")
            return {}
    
    def get_daily_data_for_stock(self, stock_code: str) -> Optional[pd.DataFrame]:
        """특정 종목의 일봉 데이터 조회 (DB 연결/해제 제거 - 배치에서 관리) [최적화]"""
        try:
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
    
    def save_technical_indicators_fixed(self, stock_code: str, df_with_indicators: pd.DataFrame) -> bool:
        """기술적 지표를 데이터베이스에 저장 (DB 연결/해제 제거, 청크 저장) [최적화]"""
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
            
            # 500개씩 나눠서 INSERT (최적화)
            chunk_size = 500
            total_saved = 0
            for i in range(0, len(technical_data), chunk_size):
                chunk = technical_data[i:i + chunk_size]
                if self.db.execute_many(technical_insert_sql, chunk):
                    total_saved += len(chunk)
                else:
                    logging.error(f"❌ {stock_code} 기술적 지표 청크 저장 실패 (시작: {i})")
                    return False
            
            logging.info(f"✅ {stock_code} 기술적 지표 {total_saved}개 저장 완료")
            return True
                
        except Exception as e:
            logging.error(f"❌ {stock_code} 기술적 지표 저장 중 오류: {e}")
            return False
    
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
            
            # ✅ 배치 시작 시 DB 연결 (한 번만) [최적화]
            if not self.db.connect():
                logging.error(f"❌ 배치 {batch_num} DB 연결 실패")
                total_failed += len(stock_batch)
                continue
            
            batch_success = 0
            batch_failed = 0
            
            # ✅ 배치 전체 종목의 데이터를 한 번에 조회 [최적화]
            stock_codes_only = [code for code, name in stock_batch]
            logging.info(f"🔍 배치 {batch_num}: {len(stock_codes_only)}개 종목 데이터 일괄 조회 중...")
            batch_data_dict = self.get_batch_daily_data(stock_codes_only)
            
            for i, (stock_code, stock_name) in enumerate(stock_batch, 1):
                logging.info(f"📊 [{i}/{len(stock_batch)}] {stock_code} ({stock_name}) 처리 중...")
                
                try:
                    # 미리 조회한 데이터 사용
                    if stock_code in batch_data_dict:
                        daily_data = batch_data_dict[stock_code]
                        if daily_data is not None and not daily_data.empty:
                            # 기술적 지표 계산
                            df_with_indicators = self.calculate_technical_indicators(daily_data.copy())
                            # 기술적 지표 저장
                            if self.save_technical_indicators_fixed(stock_code, df_with_indicators):
                                logging.info(f"✅ {stock_code} ({stock_name}) 보조지표 재수집 완료")
                                batch_success += 1
                            else:
                                logging.error(f"❌ {stock_code} ({stock_name}) 보조지표 저장 실패")
                                batch_failed += 1
                        else:
                            logging.warning(f"⚠️ {stock_code} ({stock_name}): 일봉 데이터가 비어있음")
                            batch_failed += 1
                    else:
                        logging.warning(f"⚠️ {stock_code} ({stock_name}): 배치 조회 결과에 없음")
                        batch_failed += 1
                    
                    # ✅ 딜레이 제거 (DB 작업이므로 불필요) [최적화]
                    # time.sleep 제거
                    
                except Exception as e:
                    logging.error(f"❌ {stock_code} ({stock_name}) 처리 중 오류: {e}")
                    batch_failed += 1
            
            # ✅ 배치 종료 시 DB 연결 해제 (한 번만) [최적화]
            self.db.disconnect()
            
            total_success += batch_success
            total_failed += batch_failed
            
            logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
            logging.info(f"✅ 성공: {batch_success}개, ❌ 실패: {batch_failed}개")
            logging.info("="*60)
            
            # ✅ 배치 간 딜레이 단축 (2초 → 0.5초) [최적화]
            if batch_num < total_batches:
                logging.info(f"⏳ 다음 배치까지 0.5초 대기...")
                time.sleep(0.5)
        
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
    import sys
    import glob
    
    print("🚀 기술적 지표 재수집 프로그램 시작")
    print("="*60)
    
    recollector = TechnicalIndicatorsRecollector()
    
    try:
        # 실패한 종목 파일 찾기
        failed_files = glob.glob("failed_technical_indicators_*.txt")
        specific_codes = None
        
        if failed_files:
            # 가장 최근 파일 사용
            latest_file = max(failed_files, key=lambda x: x.split('_')[-1].split('.')[0])
            print(f"📄 실패한 종목 파일 발견: {latest_file}")
            
            # 실패한 종목 코드 읽기
            with open(latest_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                specific_codes = []
                for line in lines:
                    line = line.strip()
                    # 헤더나 빈 줄 건너뛰기
                    if line and not line.startswith('기술') and not line.startswith('생성') and not line.startswith('총') and not line.startswith('=') and not line.startswith('개'):
                        specific_codes.append(line)
            
            if specific_codes:
                print(f"📊 실패한 종목 {len(specific_codes)}개를 재수집합니다.")
                print(f"   (예: {specific_codes[:5]})")
            else:
                print("⚠️ 실패한 종목 코드를 찾을 수 없습니다.")
                specific_codes = None
        
        # 현재 상태 확인
        print("\n📊 현재 보조지표 상태 확인 중...")
        recollector.check_technical_indicators_status()
        
        # 사용자 확인
        if specific_codes:
            print(f"\n⚠️ 실패한 종목 {len(specific_codes)}개의 보조지표를 재수집합니다.")
        else:
            print("\n전체 종목의 보조지표를 재수집합니다.")
        
        response = input("\n진행하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("사용자에 의해 중단되었습니다.")
            return
        
        # 보조지표 재수집 실행
        print("\n🔄 보조지표 재수집 시작...")
        success, failed = recollector.recollect_all_technical_indicators(specific_codes)
        
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
