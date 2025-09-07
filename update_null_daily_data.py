#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_data 테이블의 null 데이터 업데이트 모듈
OHLCV, Outstanding_shares, Market_cap 컬럼의 null 데이터를 PyKrx로 수집하여 업데이트
stock_data_collector.py의 검증된 로직을 활용하여 안정적인 데이터 수집
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time
import random
import argparse
from typing import List, Dict, Any, Optional, Tuple
from database_config import DatabaseManager
from stock_data_collector import StockDataCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('null_data_updater.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class NullDailyDataUpdater:
    """daily_data 테이블의 null 데이터 업데이트 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        self.stock_collector = StockDataCollector()
        self.batch_size = 100  # 배치 크기
        self.delay_between_requests = 0.1  # 요청 간 딜레이
        self.batch_delay = 2  # 배치 간 딜레이
        
        # 통계 정보
        self.stats = {
            'total_stocks': 0,
            'ohlcv_null': 0,
            'shares_null': 0,
            'market_cap_null': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def find_null_data_stocks(self) -> List[Dict[str, Any]]:
        """null 데이터가 있는 종목들 조회 및 분석"""
        try:
            logging.info("🔍 null 데이터가 있는 종목들 조회 중...")
            
            # DB 연결
            if not self.db.connect():
                logging.error("❌ 데이터베이스 연결 실패")
                return []
            
            # null 데이터가 있는 종목들 조회
            null_query = """
            SELECT DISTINCT stock_code,
                   COUNT(CASE WHEN open IS NULL THEN 1 END) as open_null_count,
                   COUNT(CASE WHEN high IS NULL THEN 1 END) as high_null_count,
                   COUNT(CASE WHEN low IS NULL THEN 1 END) as low_null_count,
                   COUNT(CASE WHEN close IS NULL THEN 1 END) as close_null_count,
                   COUNT(CASE WHEN volume IS NULL THEN 1 END) as volume_null_count,
                   COUNT(CASE WHEN outstanding_shares IS NULL THEN 1 END) as shares_null_count,
                   COUNT(CASE WHEN market_cap IS NULL THEN 1 END) as market_cap_null_count,
                   COUNT(*) as total_records
            FROM daily_data 
            WHERE (open IS NULL OR 
                   high IS NULL OR 
                   low IS NULL OR 
                   close IS NULL OR 
                   volume IS NULL OR 
                   outstanding_shares IS NULL OR 
                   market_cap IS NULL)
            GROUP BY stock_code
            ORDER BY stock_code
            """
            
            result = self.db.fetch_all(null_query)
            
            if not result:
                logging.info("✅ null 데이터가 있는 종목이 없습니다.")
                return []
            
            # 종목 정보와 함께 상세 정보 조회
            detailed_stocks = []
            for row in result:
                stock_code = row['stock_code']
                
                # 종목명 조회
                stock_name_query = "SELECT stock_name FROM stocks WHERE stock_code = %s"
                stock_name_result = self.db.fetch_one(stock_name_query, (stock_code,))
                stock_name = stock_name_result['stock_name'] if stock_name_result else "Unknown"
                
                # null 데이터 상세 정보
                stock_info = {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'open_null_count': row['open_null_count'],
                    'high_null_count': row['high_null_count'],
                    'low_null_count': row['low_null_count'],
                    'close_null_count': row['close_null_count'],
                    'volume_null_count': row['volume_null_count'],
                    'shares_null_count': row['shares_null_count'],
                    'market_cap_null_count': row['market_cap_null_count'],
                    'total_records': row['total_records'],
                    'has_ohlcv_null': any([
                        row['open_null_count'] > 0,
                        row['high_null_count'] > 0,
                        row['low_null_count'] > 0,
                        row['close_null_count'] > 0,
                        row['volume_null_count'] > 0
                    ]),
                    'has_shares_null': row['shares_null_count'] > 0,
                    'has_market_cap_null': row['market_cap_null_count'] > 0
                }
                
                detailed_stocks.append(stock_info)
            
            # 통계 업데이트
            self.stats['total_stocks'] = len(detailed_stocks)
            self.stats['ohlcv_null'] = sum(1 for s in detailed_stocks if s['has_ohlcv_null'])
            self.stats['shares_null'] = sum(1 for s in detailed_stocks if s['has_shares_null'])
            self.stats['market_cap_null'] = sum(1 for s in detailed_stocks if s['has_market_cap_null'])
            
            logging.info(f"📊 null 데이터 분석 결과:")
            logging.info(f"   - 총 null 데이터 종목: {self.stats['total_stocks']:,}개")
            logging.info(f"   - OHLCV null 종목: {self.stats['ohlcv_null']:,}개")
            logging.info(f"   - Outstanding_shares null 종목: {self.stats['shares_null']:,}개")
            logging.info(f"   - Market_cap null 종목: {self.stats['market_cap_null']:,}개")
            
            return detailed_stocks
            
        except Exception as e:
            logging.error(f"❌ null 데이터 조회 중 오류: {e}")
            return []
        finally:
            self.db.disconnect()
    
    def get_null_data_details(self, stock_code: str) -> Dict[str, Any]:
        """특정 종목의 null 데이터 상세 정보 조회"""
        try:
            if not self.db.connect():
                return {}
            
            # 해당 종목의 null 데이터 상세 조회
            detail_query = """
            SELECT trade_date, open, high, low, close, volume, outstanding_shares, market_cap
            FROM daily_data 
            WHERE stock_code = %s 
            AND (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR 
                 volume IS NULL OR outstanding_shares IS NULL OR market_cap IS NULL)
            ORDER BY trade_date DESC
            LIMIT 10
            """
            
            result = self.db.fetch_all(detail_query, (stock_code,))
            
            null_details = []
            for row in result:
                null_details.append({
                    'trade_date': row['trade_date'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume'],
                    'outstanding_shares': row['outstanding_shares'],
                    'market_cap': row['market_cap']
                })
            
            return {
                'stock_code': stock_code,
                'null_records': null_details,
                'null_count': len(null_details)
            }
            
        except Exception as e:
            logging.error(f"❌ {stock_code} null 데이터 상세 조회 중 오류: {e}")
            return {}
        finally:
            self.db.disconnect()
    
    def update_single_stock_data(self, stock_info: Dict[str, Any]) -> bool:
        """단일 종목의 null 데이터 업데이트"""
        stock_code = stock_info['stock_code']
        stock_name = stock_info['stock_name']
        
        try:
            logging.info(f"🔄 {stock_code} ({stock_name}) null 데이터 업데이트 시작...")
            
            success = False
            
            # OHLCV null이 있는 경우
            if stock_info['has_ohlcv_null']:
                logging.info(f"   📊 {stock_code}: OHLCV null 데이터 수집 중...")
                
                # PyKrx로 일봉 데이터 수집
                hist_data = self.stock_collector.get_stock_data_pykrx(stock_code, stock_name, 10)
                
                if hist_data is not None and not hist_data.empty:
                    # 일봉 데이터 저장 (ON DUPLICATE KEY UPDATE로 null 데이터만 업데이트)
                    if self.save_daily_data_selective(stock_code, hist_data):
                        logging.info(f"   ✅ {stock_code}: OHLCV 데이터 업데이트 완료")
                        success = True
                    else:
                        logging.error(f"   ❌ {stock_code}: OHLCV 데이터 저장 실패")
                else:
                    logging.warning(f"   ⚠️ {stock_code}: OHLCV 데이터 수집 실패")
            
            # Outstanding_shares 또는 Market_cap null이 있는 경우
            if stock_info['has_shares_null'] or stock_info['has_market_cap_null']:
                logging.info(f"   📊 {stock_code}: 유통주식수/Market_cap null 데이터 수집 중...")
                
                # PyKrx로 유통주식수 정보 수집
                shares_info = self.stock_collector.get_stock_shares_info_from_pykrx(stock_code, "")
                
                if shares_info:
                    total_shares = shares_info.get('total_shares', 0)
                    market_cap = shares_info.get('market_cap', 0)
                    
                    if total_shares > 0:
                        # daily_data 테이블의 null 데이터만 업데이트
                        if self.update_null_shares_data(stock_code, total_shares, market_cap):
                            logging.info(f"   ✅ {stock_code}: 유통주식수/Market_cap 업데이트 완료")
                            success = True
                        else:
                            logging.error(f"   ❌ {stock_code}: 유통주식수/Market_cap 저장 실패")
                    else:
                        logging.warning(f"   ⚠️ {stock_code}: 유통주식수 정보 없음")
                else:
                    logging.warning(f"   ⚠️ {stock_code}: 유통주식수 정보 수집 실패")
            
            if success:
                logging.info(f"✅ {stock_code} ({stock_name}) null 데이터 업데이트 완료")
                return True
            else:
                logging.error(f"❌ {stock_code} ({stock_name}) null 데이터 업데이트 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ {stock_code} ({stock_name}) null 데이터 업데이트 중 오류: {e}")
            return False
    
    def save_daily_data_selective(self, stock_code: str, hist_data: pd.DataFrame) -> bool:
        """선택적으로 일봉 데이터 저장 (null 데이터만 업데이트)"""
        try:
            if not self.db.connect():
                return False
            
            # null 데이터가 있는 날짜들만 조회
            null_dates_query = """
            SELECT trade_date 
            FROM daily_data 
            WHERE stock_code = %s 
            AND (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL)
            """
            
            null_dates_result = self.db.fetch_all(null_dates_query, (stock_code,))
            null_dates = {row['trade_date'] for row in null_dates_result} if null_dates_result else set()
            
            if not null_dates:
                logging.info(f"   ℹ️ {stock_code}: 업데이트할 OHLCV null 데이터가 없습니다.")
                return True
            
            # 해당 날짜들의 데이터만 필터링
            filtered_data = []
            for date, row in hist_data.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                if date_str in null_dates:
                    # NaN 값 처리
                    open_price = row['Open'] if pd.notna(row['Open']) else None
                    high_price = row['High'] if pd.notna(row['High']) else None
                    low_price = row['Low'] if pd.notna(row['Low']) else None
                    close_price = row['Close'] if pd.notna(row['Close']) else None
                    volume = row['Volume'] if pd.notna(row['Volume']) else 0
                    
                    if open_price is not None and high_price is not None and low_price is not None and close_price is not None:
                        filtered_data.append((
                            stock_code,
                            date_str,
                            float(open_price),
                            float(high_price),
                            float(low_price),
                            float(close_price),
                            int(volume)
                        ))
            
            if not filtered_data:
                logging.warning(f"   ⚠️ {stock_code}: 필터링된 OHLCV 데이터가 없습니다.")
                return False
            
            # 선택적 업데이트 (null인 컬럼만 업데이트)
            update_sql = """
            UPDATE daily_data 
            SET open = CASE WHEN open IS NULL THEN %s ELSE open END,
                high = CASE WHEN high IS NULL THEN %s ELSE high END,
                low = CASE WHEN low IS NULL THEN %s ELSE low END,
                close = CASE WHEN close IS NULL THEN %s ELSE close END,
                volume = CASE WHEN volume IS NULL THEN %s ELSE volume END,
                updated_at = CURRENT_TIMESTAMP
            WHERE stock_code = %s AND trade_date = %s
            """
            
            success_count = 0
            for data in filtered_data:
                params = (data[2], data[3], data[4], data[5], data[6], data[0], data[1])
                if self.db.execute_query(update_sql, params):
                    success_count += 1
            
            logging.info(f"   📊 {stock_code}: {success_count}/{len(filtered_data)}개 OHLCV 레코드 업데이트 완료")
            return success_count > 0
            
        except Exception as e:
            logging.error(f"❌ {stock_code} 선택적 일봉 데이터 저장 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def update_null_shares_data(self, stock_code: str, total_shares: int, market_cap: float) -> bool:
        """null인 outstanding_shares와 market_cap 데이터만 업데이트"""
        try:
            if not self.db.connect():
                return False
            
            # null 데이터가 있는 레코드들만 업데이트
            update_sql = """
            UPDATE daily_data 
            SET outstanding_shares = CASE WHEN outstanding_shares IS NULL THEN %s ELSE outstanding_shares END,
                market_cap = CASE WHEN market_cap IS NULL THEN %s ELSE market_cap END,
                updated_at = CURRENT_TIMESTAMP
            WHERE stock_code = %s 
            AND (outstanding_shares IS NULL OR market_cap IS NULL)
            """
            
            params = (total_shares, market_cap, stock_code)
            success = self.db.execute_query(update_sql, params)
            
            if success:
                # 업데이트된 레코드 수 확인
                count_query = """
                SELECT COUNT(*) as updated_count
                FROM daily_data 
                WHERE stock_code = %s AND outstanding_shares = %s
                """
                count_result = self.db.fetch_one(count_query, (stock_code, total_shares))
                updated_count = count_result['updated_count'] if count_result else 0
                
                logging.info(f"   📊 {stock_code}: {updated_count}개 유통주식수/Market_cap 레코드 업데이트 완료")
                
                # stock_shares_history에도 업데이트
                self.stock_collector.update_stock_shares_history_direct(stock_code, total_shares, market_cap)
                
                return True
            else:
                logging.error(f"   ❌ {stock_code}: 유통주식수/Market_cap 업데이트 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ {stock_code} null shares 데이터 업데이트 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def update_null_data_batch(self, stock_batch: List[Dict[str, Any]], batch_num: int, total_batches: int) -> Tuple[int, int]:
        """배치 단위로 null 데이터 업데이트"""
        logging.info(f"🚀 배치 {batch_num}/{total_batches} 시작 ({len(stock_batch)}개 종목)")
        logging.info("="*60)
        
        success_count = 0
        failed_count = 0
        
        for i, stock_info in enumerate(stock_batch, 1):
            stock_code = stock_info['stock_code']
            stock_name = stock_info['stock_name']
            
            logging.info(f"📊 [{i}/{len(stock_batch)}] {stock_code} ({stock_name}) 처리 중...")
            
            try:
                if self.update_single_stock_data(stock_info):
                    success_count += 1
                    self.stats['success'] += 1
                else:
                    failed_count += 1
                    self.stats['failed'] += 1
                
                # API 호출 간격 조절
                delay = self.delay_between_requests + random.uniform(0.05, 0.2)
                time.sleep(delay)
                
            except Exception as e:
                logging.error(f"❌ {stock_code} ({stock_name}) 처리 중 오류: {e}")
                failed_count += 1
                self.stats['failed'] += 1
            
            self.stats['processed'] += 1
        
        logging.info(f"🎉 배치 {batch_num}/{total_batches} 완료!")
        logging.info(f"✅ 성공: {success_count}개, ❌ 실패: {failed_count}개")
        logging.info("="*60)
        
        return success_count, failed_count
    
    def update_all_null_data(self, specific_codes: Optional[List[str]] = None, dry_run: bool = False) -> Tuple[int, int]:
        """전체 null 데이터 업데이트 실행"""
        logging.info("🚀 null 데이터 업데이트 시작")
        logging.info("="*60)
        
        if dry_run:
            logging.info("🔍 DRY RUN 모드: 실제 업데이트 없이 조회만 수행합니다.")
        
        # null 데이터가 있는 종목들 조회
        null_stocks = self.find_null_data_stocks()
        
        if not null_stocks:
            logging.info("✅ 업데이트할 null 데이터가 없습니다.")
            return 0, 0
        
        # 특정 종목코드가 지정된 경우 필터링
        if specific_codes:
            null_stocks = [s for s in null_stocks if s['stock_code'] in specific_codes]
            logging.info(f"🧪 특정 종목 {len(null_stocks)}개만 처리합니다.")
        
        if not null_stocks:
            logging.info("✅ 처리할 null 데이터가 없습니다.")
            return 0, 0
        
        if dry_run:
            logging.info("🔍 DRY RUN 결과:")
            for stock in null_stocks[:10]:  # 처음 10개만 표시
                logging.info(f"   - {stock['stock_code']} ({stock['stock_name']}): "
                           f"OHLCV null: {stock['has_ohlcv_null']}, "
                           f"Shares null: {stock['has_shares_null']}")
            if len(null_stocks) > 10:
                logging.info(f"   ... 외 {len(null_stocks) - 10}개 종목")
            return len(null_stocks), 0
        
        # 배치로 나누기
        total_stocks = len(null_stocks)
        total_batches = (total_stocks + self.batch_size - 1) // self.batch_size
        
        logging.info(f"📊 총 {total_stocks}개 종목을 {total_batches}개 배치로 나누어 처리합니다.")
        logging.info(f"📦 배치 크기: {self.batch_size}개")
        
        total_success = 0
        total_failed = 0
        
        for batch_num in range(1, total_batches + 1):
            start_idx = (batch_num - 1) * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_stocks)
            stock_batch = null_stocks[start_idx:end_idx]
            
            try:
                success, failed = self.update_null_data_batch(stock_batch, batch_num, total_batches)
                total_success += success
                total_failed += failed
                
                # 배치 간 딜레이
                if batch_num < total_batches:
                    logging.info(f"⏳ 다음 배치까지 {self.batch_delay}초 대기...")
                    time.sleep(self.batch_delay)
                
            except KeyboardInterrupt:
                logging.warning("⚠️ 사용자에 의해 중단되었습니다.")
                break
            except Exception as e:
                logging.error(f"배치 {batch_num} 처리 중 오류: {e}")
                continue
        
        # 최종 통계
        logging.info(f"\n🎉 null 데이터 업데이트 완료!")
        logging.info(f"✅ 총 성공: {total_success}개")
        logging.info(f"❌ 총 실패: {total_failed}개")
        logging.info(f"📊 성공률: {(total_success / total_stocks * 100):.1f}%")
        
        return total_success, total_failed
    
    def show_null_data_stats(self):
        """null 데이터 통계 표시"""
        logging.info("📊 null 데이터 통계 조회 중...")
        
        null_stocks = self.find_null_data_stocks()
        
        if not null_stocks:
            logging.info("✅ null 데이터가 있는 종목이 없습니다.")
            return
        
        # 상세 통계
        ohlcv_null_stocks = [s for s in null_stocks if s['has_ohlcv_null']]
        shares_null_stocks = [s for s in null_stocks if s['has_shares_null']]
        market_cap_null_stocks = [s for s in null_stocks if s['has_market_cap_null']]
        
        logging.info(f"\n📊 null 데이터 상세 통계:")
        logging.info(f"   - 총 null 데이터 종목: {len(null_stocks):,}개")
        logging.info(f"   - OHLCV null 종목: {len(ohlcv_null_stocks):,}개")
        logging.info(f"   - Outstanding_shares null 종목: {len(shares_null_stocks):,}개")
        logging.info(f"   - Market_cap null 종목: {len(market_cap_null_stocks):,}개")
        
        # null 데이터가 많은 상위 10개 종목 표시
        logging.info(f"\n🔝 null 데이터가 많은 상위 10개 종목:")
        sorted_stocks = sorted(null_stocks, key=lambda x: x['total_records'], reverse=True)
        for i, stock in enumerate(sorted_stocks[:10], 1):
            logging.info(f"   {i:2d}. {stock['stock_code']} ({stock['stock_name']}): "
                        f"총 {stock['total_records']}개 레코드 중 "
                        f"OHLCV null: {stock['has_ohlcv_null']}, "
                        f"Shares null: {stock['has_shares_null']}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='daily_data 테이블의 null 데이터 업데이트')
    parser.add_argument('--batch-size', type=int, default=100, help='배치 크기 (기본값: 100)')
    parser.add_argument('--specific-codes', nargs='+', help='특정 종목코드만 업데이트')
    parser.add_argument('--dry-run', action='store_true', help='실제 업데이트 없이 조회만 수행')
    parser.add_argument('--show-stats', action='store_true', help='null 데이터 통계만 표시')
    
    args = parser.parse_args()
    
    # NullDailyDataUpdater 인스턴스 생성
    updater = NullDailyDataUpdater()
    
    # 배치 크기 설정
    updater.batch_size = args.batch_size
    
    try:
        if args.show_stats:
            # 통계만 표시
            updater.show_null_data_stats()
        else:
            # null 데이터 업데이트 실행
            total_success, total_failed = updater.update_all_null_data(
                specific_codes=args.specific_codes,
                dry_run=args.dry_run
            )
            
            if not args.dry_run:
                logging.info(f"\n💡 업데이트 완료:")
                logging.info(f"   - 성공: {total_success}개")
                logging.info(f"   - 실패: {total_failed}개")
                logging.info(f"   - 로그 파일: null_data_updater.log")
    
    except Exception as e:
        logging.error(f"❌ 프로그램 실행 중 오류: {e}")


if __name__ == "__main__":
    main()
