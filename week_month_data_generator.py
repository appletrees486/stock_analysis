#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주봉 및 월봉 데이터 생성 모듈
일봉 데이터를 기반으로 주봉, 월봉 데이터를 생성하여 데이터베이스에 저장
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from database_config import DatabaseManager
import time
from korean_holiday_manager import KoreanHolidayManager
from week_calculator import get_week_number, get_week_number_string

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('week_month_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class WeekMonthDataGenerator:
    def __init__(self):
        """주봉/월봉 데이터 생성기 초기화"""
        self.db = DatabaseManager()
        self.holiday_manager = KoreanHolidayManager()
        self.batch_size = 100  # 배치 크기
        
    def get_stocks_with_daily_data(self):
        """일봉 데이터가 있는 종목 목록 조회"""
        try:
            if not self.db.connect():
                logging.error("데이터베이스 연결 실패")
                return []
            
            query = """
            SELECT DISTINCT d.stock_code, s.stock_name, s.market_type
            FROM daily_data d
            JOIN stocks s ON d.stock_code = s.stock_code
            WHERE s.is_active = TRUE
            ORDER BY d.stock_code
            """
            
            result = self.db.fetch_all(query)
            
            if result:
                stocks = [(row['stock_code'], row['stock_name'], row['market_type']) for row in result]
                logging.info(f"일봉 데이터가 있는 종목 {len(stocks)}개를 찾았습니다.")
                return stocks
            else:
                logging.warning("일봉 데이터가 있는 종목이 없습니다.")
                return []
                
        except Exception as e:
            logging.error(f"종목 목록 조회 실패: {e}")
            return []
        finally:
            self.db.disconnect()
    
    def get_daily_data_for_stock(self, stock_code, start_date=None, end_date=None):
        """특정 종목의 일봉 데이터 조회"""
        try:
            if not self.db.connect():
                return None
            
            if start_date and end_date:
                query = """
                SELECT trade_date, open, high, low, close, volume
                FROM daily_data
                WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
                ORDER BY trade_date
                """
                params = (stock_code, start_date, end_date)
            else:
                query = """
                SELECT trade_date, open, high, low, close, volume
                FROM daily_data
                WHERE stock_code = %s
                ORDER BY trade_date
                """
                params = (stock_code,)
            
            result = self.db.fetch_all(query, params)
            
            if result:
                # DataFrame으로 변환
                df = pd.DataFrame(result)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df.set_index('trade_date', inplace=True)
                return df
            else:
                return None
                
        except Exception as e:
            logging.error(f"{stock_code} 일봉 데이터 조회 실패: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def generate_weekly_data(self, daily_df):
        """일봉 데이터를 주봉 데이터로 변환 (보조지표 포함) - 미완성 주 제외"""
        try:
            if daily_df is None or daily_df.empty:
                return None
            
            # 주봉 데이터 생성
            weekly_data = []
            
            # 현재 날짜 (미완성 주 제외를 위해)
            current_date = datetime.now()
            current_year = current_date.year
            current_week = current_date.isocalendar()[1]  # ISO 주차
            
            # 주차별로 그룹화 (월요일 시작)
            daily_df['week_start'] = daily_df.index.to_period('W-MON').asfreq('D')
            
            for week_start, week_group in daily_df.groupby('week_start'):
                if week_group.empty:
                    continue
                
                # 미완성 주 제외 로직 추가
                week_start_date = week_start.to_timestamp()
                week_year = week_start_date.year
                week_week = week_start_date.isocalendar()[1]  # ISO 주차
                
                # 미래 주인 경우만 제외 (현재 주는 포함)
                if week_year > current_year or (week_year == current_year and week_week > current_week):
                    logging.info(f"미래 주 제외: {week_year}년 {week_week}주차")
                    continue
                
                # 주봉 OHLCV 계산
                week_open = week_group.iloc[0]['open']
                week_high = week_group['high'].max()
                week_low = week_group['low'].min()
                week_close = week_group.iloc[-1]['close']
                week_volume = week_group['volume'].sum()
                
                # 거래일 수 확인 (최소 4일 이상 거래된 주만 포함)
                if len(week_group) >= 4:
                    weekly_data.append({
                        'trade_date': week_start,
                        'open': week_open,
                        'high': week_high,
                        'low': week_low,
                        'close': week_close,
                        'volume': week_volume
                    })
            
            if weekly_data:
                weekly_df = pd.DataFrame(weekly_data)
                weekly_df.set_index('trade_date', inplace=True)
                
                # 보조지표 계산
                weekly_df = self.calculate_weekly_indicators(weekly_df)
                
                return weekly_df
            
            return None
            
        except Exception as e:
            logging.error(f"주봉 데이터 생성 실패: {e}")
            return None
    
    def generate_monthly_data(self, daily_df):
        """일봉 데이터를 월봉 데이터로 변환 (보조지표 포함) - 미완성 월 제외"""
        try:
            if daily_df is None or daily_df.empty:
                return None
            
            # 월봉 데이터 생성
            monthly_data = []
            
            # 현재 날짜 (미완성 월 제외를 위해)
            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month
            
            # 월별로 그룹화
            daily_df['month_start'] = daily_df.index.to_period('M').asfreq('D')
            
            for month_start, month_group in daily_df.groupby('month_start'):
                if month_group.empty:
                    continue
                
                # 미완성 월 제외 로직 추가
                month_start_date = month_start.to_timestamp()
                month_year = month_start_date.year
                month_month = month_start_date.month
                
                # 현재 월이거나 미래 월인 경우 제외
                if month_year > current_year or (month_year == current_year and month_month >= current_month):
                    logging.info(f"미완성 월 제외: {month_year}년 {month_month}월")
                    continue
                
                # 월봉 OHLCV 계산
                month_open = month_group.iloc[0]['open']
                month_high = month_group['high'].max()
                month_low = month_group['low'].min()
                month_close = month_group.iloc[-1]['close']
                month_volume = month_group['volume'].sum()
                
                # 거래일 수 확인 (최소 10일 이상 거래된 월만 포함)
                if len(month_group) >= 10:
                    monthly_data.append({
                        'trade_date': month_start,
                        'open': month_open,
                        'high': month_high,
                        'low': month_low,
                        'close': month_close,
                        'volume': month_volume
                    })
            
            if monthly_data:
                monthly_df = pd.DataFrame(monthly_data)
                monthly_df.set_index('trade_date', inplace=True)
                
                # 보조지표 계산
                monthly_df = self.calculate_monthly_indicators(monthly_df)
                
                return monthly_df
            
            return None
            
        except Exception as e:
            logging.error(f"월봉 데이터 생성 실패: {e}")
            return None
    
    def calculate_weekly_indicators(self, weekly_df):
        """주봉 보조지표 계산"""
        try:
            if weekly_df is None or weekly_df.empty:
                return weekly_df
            
            # 이동평균선
            weekly_df['ma5'] = weekly_df['close'].rolling(window=5).mean()
            weekly_df['ma20'] = weekly_df['close'].rolling(window=20).mean()
            weekly_df['ma60'] = weekly_df['close'].rolling(window=60).mean()
            
            # RSI 계산 (14주 기준)
            delta = weekly_df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            weekly_df['rsi'] = 100 - (100 / (1 + rs))
            
            # Stochastic Slow (14주 기준)
            lowest_low = weekly_df['low'].rolling(window=14).min()
            highest_high = weekly_df['high'].rolling(window=14).max()
            weekly_df['stoch_k'] = ((weekly_df['close'] - lowest_low) / (highest_high - lowest_low)) * 100
            weekly_df['stoch_d'] = weekly_df['stoch_k'].rolling(window=3).mean()
            
            # 볼린저 밴드 (20주 기준)
            weekly_df['bb_middle'] = weekly_df['close'].rolling(window=20).mean()
            bb_std = weekly_df['close'].rolling(window=20).std()
            weekly_df['bb_upper'] = weekly_df['bb_middle'] + (bb_std * 2)
            weekly_df['bb_lower'] = weekly_df['bb_middle'] - (bb_std * 2)
            
            logging.info(f"주봉 보조지표 계산 완료: {len(weekly_df)}주 (ISO 8601 표준)")
            return weekly_df
            
        except Exception as e:
            logging.error(f"주봉 보조지표 계산 실패: {e}")
            return weekly_df
    
    def calculate_monthly_indicators(self, monthly_df):
        """월봉 보조지표 계산"""
        try:
            if monthly_df is None or monthly_df.empty:
                return monthly_df
            
            # 이동평균선
            monthly_df['ma5'] = monthly_df['close'].rolling(window=5).mean()
            monthly_df['ma20'] = monthly_df['close'].rolling(window=20).mean()
            monthly_df['ma60'] = monthly_df['close'].rolling(window=60).mean()
            
            # CCI 계산 (20개월 기준)
            typical_price = (monthly_df['high'] + monthly_df['low'] + monthly_df['close']) / 3
            sma_tp = typical_price.rolling(window=20).mean()
            mean_deviation = typical_price.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
            monthly_df['cci'] = (typical_price - sma_tp) / (0.015 * mean_deviation)
            
            # ADX 계산 (14개월 기준)
            high_diff = monthly_df['high'].diff()
            low_diff = monthly_df['low'].diff()
            
            plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
            minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), -low_diff, 0)
            
            tr1 = monthly_df['high'] - monthly_df['low']
            tr2 = np.abs(monthly_df['high'] - monthly_df['close'].shift(1))
            tr3 = np.abs(monthly_df['low'] - monthly_df['close'].shift(1))
            true_range = np.maximum(tr1, np.maximum(tr2, tr3))
            
            period = min(14, len(monthly_df) // 2)
            if period < 5:
                period = 5
            
            atr = true_range.rolling(window=period).mean()
            atr = atr.replace(0, np.nan)
            
            plus_dm_avg = pd.Series(plus_dm).rolling(window=period).mean()
            minus_dm_avg = pd.Series(minus_dm).rolling(window=period).mean()
            
            plus_di = pd.Series(index=monthly_df.index, dtype=float)
            minus_di = pd.Series(index=monthly_df.index, dtype=float)
            
            for i in range(len(monthly_df)):
                if pd.notna(atr.iloc[i]) and atr.iloc[i] > 0:
                    plus_di.iloc[i] = (plus_dm_avg.iloc[i] / atr.iloc[i]) * 100
                    minus_di.iloc[i] = (minus_dm_avg.iloc[i] / atr.iloc[i]) * 100
                else:
                    plus_di.iloc[i] = 0
                    minus_di.iloc[i] = 0
            
            dx = pd.Series(index=monthly_df.index, dtype=float)
            for i in range(len(monthly_df)):
                di_sum = plus_di.iloc[i] + minus_di.iloc[i]
                if di_sum > 0:
                    dx.iloc[i] = abs(plus_di.iloc[i] - minus_di.iloc[i]) / di_sum * 100
                else:
                    dx.iloc[i] = 0
            
            monthly_df['adx'] = pd.Series(dx).rolling(window=period).mean()
            monthly_df['plus_di'] = plus_di
            monthly_df['minus_di'] = minus_di
            
            # 볼린저 밴드 (20개월 기준)
            monthly_df['bb_middle'] = monthly_df['close'].rolling(window=20).mean()
            bb_std = monthly_df['close'].rolling(window=20).std()
            monthly_df['bb_upper'] = monthly_df['bb_middle'] + (bb_std * 2)
            monthly_df['bb_lower'] = monthly_df['bb_middle'] - (bb_std * 2)
            
            # NaN 값 처리
            monthly_df['adx'] = monthly_df['adx'].fillna(0)
            monthly_df['plus_di'] = monthly_df['plus_di'].fillna(0)
            monthly_df['minus_di'] = monthly_df['minus_di'].fillna(0)
            
            logging.info(f"월봉 보조지표 계산 완료: {len(monthly_df)}개월")
            return monthly_df
            
        except Exception as e:
            logging.error(f"월봉 보조지표 계산 실패: {e}")
            return monthly_df
    
    def save_weekly_data(self, stock_code, weekly_df):
        """주봉 데이터를 데이터베이스에 저장 (보조지표 포함)"""
        try:
            if weekly_df is None or weekly_df.empty:
                return False
            
            if not self.db.connect():
                return False
            
            # 주봉 데이터 삽입 (보조지표 포함)
            weekly_insert_sql = """
            INSERT INTO weekly_data 
            (stock_code, week_start, open, high, low, close, volume,
             ma5, ma20, ma60, rsi, stoch_k, stoch_d, bb_upper, bb_middle, bb_lower)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open = VALUES(open), high = VALUES(high), low = VALUES(low), 
            close = VALUES(close), volume = VALUES(volume),
            ma5 = VALUES(ma5), ma20 = VALUES(ma20), ma60 = VALUES(ma60),
            rsi = VALUES(rsi), stoch_k = VALUES(stoch_k), stoch_d = VALUES(stoch_d),
            bb_upper = VALUES(bb_upper), bb_middle = VALUES(bb_middle), bb_lower = VALUES(bb_lower),
            updated_at = CURRENT_TIMESTAMP
            """
            
            success_count = 0
            for date, row in weekly_df.iterrows():
                weekly_data = (
                    stock_code,
                    date.strftime('%Y-%m-%d'),
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['volume']),
                    float(row.get('ma5', 0)) if pd.notna(row.get('ma5')) else None,
                    float(row.get('ma20', 0)) if pd.notna(row.get('ma20')) else None,
                    float(row.get('ma60', 0)) if pd.notna(row.get('ma60')) else None,
                    float(row.get('rsi', 0)) if pd.notna(row.get('rsi')) else None,
                    float(row.get('stoch_k', 0)) if pd.notna(row.get('stoch_k')) else None,
                    float(row.get('stoch_d', 0)) if pd.notna(row.get('stoch_d')) else None,
                    float(row.get('bb_upper', 0)) if pd.notna(row.get('bb_upper')) else None,
                    float(row.get('bb_middle', 0)) if pd.notna(row.get('bb_middle')) else None,
                    float(row.get('bb_lower', 0)) if pd.notna(row.get('bb_lower')) else None
                )
                
                if self.db.execute_query(weekly_insert_sql, weekly_data):
                    success_count += 1
                else:
                    logging.error(f"{stock_code} 주봉 데이터 저장 실패: {date}")
            
            logging.info(f"{stock_code} 주봉 데이터 {success_count}개 저장 완료 (보조지표 포함)")
            return success_count > 0
            
        except Exception as e:
            logging.error(f"{stock_code} 주봉 데이터 저장 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def save_monthly_data(self, stock_code, monthly_df):
        """월봉 데이터를 데이터베이스에 저장 (보조지표 포함)"""
        try:
            if monthly_df is None or monthly_df.empty:
                return False
            
            if not self.db.connect():
                return False
            
            # 월봉 데이터 삽입 (보조지표 포함)
            monthly_insert_sql = """
            INSERT INTO monthly_data 
            (stock_code, month_start, open, high, low, close, volume,
             ma5, ma20, ma60, cci, adx, plus_di, minus_di, bb_upper, bb_middle, bb_lower)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open = VALUES(open), high = VALUES(high), low = VALUES(low), 
            close = VALUES(close), volume = VALUES(volume),
            ma5 = VALUES(ma5), ma20 = VALUES(ma20), ma60 = VALUES(ma60),
            cci = VALUES(cci), adx = VALUES(adx), plus_di = VALUES(plus_di), minus_di = VALUES(minus_di),
            bb_upper = VALUES(bb_upper), bb_middle = VALUES(bb_middle), bb_lower = VALUES(bb_lower),
            updated_at = CURRENT_TIMESTAMP
            """
            
            success_count = 0
            for date, row in monthly_df.iterrows():
                monthly_data = (
                    stock_code,
                    date.strftime('%Y-%m-%d'),
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['volume']),
                    float(row.get('ma5', 0)) if pd.notna(row.get('ma5')) else None,
                    float(row.get('ma20', 0)) if pd.notna(row.get('ma20')) else None,
                    float(row.get('ma60', 0)) if pd.notna(row.get('ma60')) else None,
                    float(row.get('cci', 0)) if pd.notna(row.get('cci')) else None,
                    float(row.get('adx', 0)) if pd.notna(row.get('adx')) else None,
                    float(row.get('plus_di', 0)) if pd.notna(row.get('plus_di')) else None,
                    float(row.get('minus_di', 0)) if pd.notna(row.get('minus_di')) else None,
                    float(row.get('bb_upper', 0)) if pd.notna(row.get('bb_upper')) else None,
                    float(row.get('bb_middle', 0)) if pd.notna(row.get('bb_middle')) else None,
                    float(row.get('bb_lower', 0)) if pd.notna(row.get('bb_lower')) else None
                )
                
                if self.db.execute_query(monthly_insert_sql, monthly_data):
                    success_count += 1
                else:
                    logging.error(f"{stock_code} 월봉 데이터 저장 실패: {date}")
            
            logging.info(f"{stock_code} 월봉 데이터 {success_count}개 저장 완료 (보조지표 포함)")
            return success_count > 0
            
        except Exception as e:
            logging.error(f"{stock_code} 월봉 데이터 저장 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def process_single_stock(self, stock_info):
        """단일 종목의 주봉/월봉 데이터 생성"""
        stock_code, stock_name, market_type = stock_info
        
        try:
            logging.info(f"📊 {stock_code} ({stock_name}) 주봉/월봉 데이터 생성 중...")
            
            # 일봉 데이터 조회
            daily_df = self.get_daily_data_for_stock(stock_code)
            
            if daily_df is None or daily_df.empty:
                logging.warning(f"⚠️ {stock_code} ({stock_name}): 일봉 데이터가 없습니다.")
                return False, stock_code
            
            # 주봉 데이터 생성
            weekly_df = self.generate_weekly_data(daily_df)
            if weekly_df is not None:
                if self.save_weekly_data(stock_code, weekly_df):
                    logging.info(f"✅ {stock_code} ({stock_name}) 주봉 데이터 생성 완료 ({len(weekly_df)}개)")
                else:
                    logging.error(f"❌ {stock_code} ({stock_name}) 주봉 데이터 저장 실패")
            
            # 월봉 데이터 생성
            monthly_df = self.generate_monthly_data(daily_df)
            if monthly_df is not None:
                if self.save_monthly_data(stock_code, monthly_df):
                    logging.info(f"✅ {stock_code} ({stock_name}) 월봉 데이터 생성 완료 ({len(monthly_df)}개)")
                else:
                    logging.error(f"❌ {stock_code} ({stock_name}) 월봉 데이터 저장 실패")
            
            return True, stock_code
            
        except Exception as e:
            logging.error(f"{stock_code} ({stock_name}) 주봉/월봉 데이터 생성 중 오류: {e}")
            return False, stock_code
    
    def generate_all_weekly_monthly_data(self):
        """모든 종목의 주봉/월봉 데이터 생성"""
        logging.info("🚀 주봉/월봉 데이터 생성 시작")
        logging.info("="*60)
        
        # 일봉 데이터가 있는 종목 목록 조회
        stocks = self.get_stocks_with_daily_data()
        
        if not stocks:
            logging.error("처리할 종목이 없습니다.")
            return 0, 0
        
        total_stocks = len(stocks)
        total_success = 0
        total_failed = 0
        
        # 배치 단위로 처리
        for i in range(0, total_stocks, self.batch_size):
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
            
            stock_batch = stocks[i:i + self.batch_size]
            
            logging.info(f"🚀 배치 {batch_num}/{total_batches} 시작 ({len(stock_batch)}개 종목)")
            logging.info("="*60)
            
            batch_success = 0
            batch_failed = 0
            
            for j, stock_info in enumerate(stock_batch, 1):
                logging.info(f"📊 [{j}/{len(stock_batch)}] {stock_info[0]} ({stock_info[1]}) 처리 중...")
                
                success, stock_code = self.process_single_stock(stock_info)
                
                if success:
                    batch_success += 1
                else:
                    batch_failed += 1
                
                # 처리 간격 조절
                time.sleep(0.1)
            
            total_success += batch_success
            total_failed += batch_failed
            
            logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
            logging.info(f"✅ 성공: {batch_success}개, ❌ 실패: {batch_failed}개")
            logging.info("="*60)
            
            # 배치 간 딜레이
            if batch_num < total_batches:
                logging.info(f"⏳ 다음 배치까지 1초 대기...")
                time.sleep(1)
        
        logging.info(f"\n🎉 주봉/월봉 데이터 생성 완료!")
        logging.info(f"✅ 총 성공: {total_success}개")
        logging.info(f"❌ 총 실패: {total_failed}개")
        logging.info(f"📊 성공률: {(total_success / total_stocks * 100):.1f}%")
        
        return total_success, total_failed
    
    def generate_weekly_monthly_for_chart(self, stock_code, start_date=None, end_date=None):
        """차트 생성 시점에만 주봉/월봉 데이터 생성 (저장하지 않음)"""
        try:
            logging.info(f"📊 {stock_code} 차트용 주봉/월봉 데이터 생성 중...")
            
            # 일봉 데이터 조회
            daily_df = self.get_daily_data_for_stock(stock_code, start_date, end_date)
            
            if daily_df is None or daily_df.empty:
                logging.warning(f"⚠️ {stock_code}: 일봉 데이터가 없습니다.")
                return None, None
            
            # 주봉 데이터 생성 (저장하지 않음)
            weekly_df = self.generate_weekly_data(daily_df)
            
            # 월봉 데이터 생성 (저장하지 않음)
            monthly_df = self.generate_monthly_data(daily_df)
            
            logging.info(f"✅ {stock_code} 차트용 주봉/월봉 데이터 생성 완료")
            return weekly_df, monthly_df
            
        except Exception as e:
            logging.error(f"{stock_code} 차트용 주봉/월봉 데이터 생성 중 오류: {e}")
            return None, None


def main():
    """메인 함수"""
    logging.info("🚀 주봉/월봉 데이터 생성 프로그램 시작")
    logging.info("="*60)
    
    generator = WeekMonthDataGenerator()
    
    try:
        # 모든 종목의 주봉/월봉 데이터 생성
        success, failed = generator.generate_all_weekly_monthly_data()
        
        if success > 0:
            logging.info(f"\n💡 주봉/월봉 데이터 생성 완료!")
            logging.info(f"📊 성공: {success}개, 실패: {failed}개")
            logging.info(f"\n💡 다음 단계:")
            logging.info(f"   1. 데이터베이스에서 생성된 주봉/월봉 데이터 확인")
            logging.info(f"   2. 차트 생성 모듈을 DB 기반으로 수정")
            logging.info(f"   3. 기술적 지표 계산 및 저장")
        else:
            logging.error("\n❌ 모든 종목의 주봉/월봉 데이터 생성에 실패했습니다.")
            
    except Exception as e:
        logging.error(f"데이터 생성 중 오류: {e}")


if __name__ == "__main__":
    main()
