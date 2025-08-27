#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yahoo Finance를 사용한 stocks 테이블 유통주식수 업데이트 시스템
"""

import yfinance as yf
import time
import logging
from datetime import datetime
from database_config import DatabaseManager
from typing import Dict, Any, Optional, List

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('yahoo_stocks_updater.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class YahooStocksUpdater:
    """Yahoo Finance를 사용한 주식 정보 업데이트 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db_manager = DatabaseManager()
        self.update_count = 0
        self.error_count = 0
        self.batch_size = 50  # 한 번에 처리할 종목 수
        
    def get_stock_info_from_yahoo(self, stock_code: str, market_type: str) -> Optional[Dict[str, Any]]:
        """Yahoo Finance에서 주식 정보 조회"""
        try:
            # 한국 주식은 .KS (KOSPI) 또는 .KQ (KOSDAQ) 접미사 필요
            suffix = ".KS" if market_type == "KOSPI" else ".KQ"
            ticker_symbol = f"{stock_code}{suffix}"
            
            logger.info(f"🔍 {stock_code} ({market_type}) Yahoo Finance 조회 중...")
            
            # Yahoo Finance에서 정보 조회
            stock = yf.Ticker(ticker_symbol)
            info = stock.info
            
            # 필요한 정보 추출
            stock_data = {
                'stock_code': stock_code,
                'stock_name': info.get('longName', ''),
                'total_shares': info.get('sharesOutstanding', 0),
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'country': info.get('country', ''),
                'currency': info.get('currency', ''),
                'exchange': info.get('exchange', ''),
                'market': info.get('market', ''),
                'last_updated': datetime.now()
            }
            
            # 유통주식수가 0이면 None으로 처리
            if stock_data['total_shares'] == 0:
                logger.warning(f"⚠️ {stock_code}: 유통주식수가 0입니다")
                return None
            
            logger.info(f"✅ {stock_code}: 유통주식수 {stock_data['total_shares']:,}주, 시가총액 {stock_data['market_cap']:,}")
            return stock_data
            
        except Exception as e:
            logger.error(f"❌ {stock_code} Yahoo Finance 조회 실패: {e}")
            return None
    
    def update_stock_in_database(self, stock_data: Dict[str, Any]) -> bool:
        """데이터베이스에 주식 정보 업데이트"""
        try:
            if not self.db_manager.connect():
                logger.error("❌ 데이터베이스 연결 실패")
                return False
            
            # stocks 테이블 업데이트
            update_query = """
                UPDATE stocks 
                SET 
                    stock_name = %s,
                    total_shares = %s,
                    market_cap = %s,
                    updated_at = %s
                WHERE stock_code = %s
            """
            
            params = (
                stock_data['stock_name'],
                stock_data['total_shares'],
                stock_data['market_cap'],
                stock_data['last_updated'],
                stock_data['stock_code']
            )
            
            success = self.db_manager.execute_query(update_query, params)
            
            if success:
                logger.info(f"✅ {stock_data['stock_code']} 데이터베이스 업데이트 완료")
                self.update_count += 1
                return True
            else:
                logger.error(f"❌ {stock_data['stock_code']} 데이터베이스 업데이트 실패")
                self.error_count += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ {stock_data['stock_code']} 데이터베이스 업데이트 중 오류: {e}")
            self.error_count += 1
            return False
        finally:
            self.db_manager.disconnect()
    
    def get_stocks_to_update(self, limit: int = None) -> List[Dict[str, Any]]:
        """업데이트할 주식 목록 조회"""
        try:
            if not self.db_manager.connect():
                logger.error("❌ 데이터베이스 연결 실패")
                return []
            
            # 임시값(10000000)을 가진 종목들 조회
            query = """
                SELECT stock_code, stock_name, market_type, total_shares, updated_at
                FROM stocks 
                WHERE total_shares = 10000000 OR total_shares = 0
                ORDER BY updated_at ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = self.db_manager.fetch_all(query)
            logger.info(f"📋 업데이트 대상: {len(result)}개 종목")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 업데이트 대상 조회 실패: {e}")
            return []
        finally:
            self.db_manager.disconnect()
    
    def update_stocks_batch(self, batch_size: int = 50) -> None:
        """배치 단위로 주식 정보 업데이트"""
        try:
            stocks_to_update = self.get_stocks_to_update(batch_size)
            
            if not stocks_to_update:
                logger.info("📋 업데이트할 종목이 없습니다")
                return
            
            logger.info(f"🚀 {len(stocks_to_update)}개 종목 배치 업데이트 시작")
            
            for i, stock in enumerate(stocks_to_update, 1):
                stock_code = stock['stock_code']
                market_type = stock['market_type']
                
                logger.info(f"📊 진행률: {i}/{len(stocks_to_update)} - {stock_code}")
                
                # Yahoo Finance에서 정보 조회
                stock_data = self.get_stock_info_from_yahoo(stock_code, market_type)
                
                if stock_data:
                    # 데이터베이스 업데이트
                    self.update_stock_in_database(stock_data)
                else:
                    logger.warning(f"⚠️ {stock_code}: 정보 수집 실패로 건너뜀")
                
                # API 호출 제한 방지 (초당 1회)
                if i < len(stocks_to_update):
                    time.sleep(1)
            
            logger.info(f"🎉 배치 업데이트 완료: 성공 {self.update_count}개, 실패 {self.error_count}개")
            
        except Exception as e:
            logger.error(f"❌ 배치 업데이트 중 오류: {e}")
    
    def update_single_stock(self, stock_code: str) -> bool:
        """단일 종목 정보 업데이트"""
        try:
            if not self.db_manager.connect():
                logger.error("❌ 데이터베이스 연결 실패")
                return False
            
            # 종목 정보 조회
            query = "SELECT stock_code, stock_name, market_type FROM stocks WHERE stock_code = %s"
            stock = self.db_manager.fetch_one(query, (stock_code,))
            
            if not stock:
                logger.error(f"❌ {stock_code}: 데이터베이스에서 찾을 수 없음")
                return False
            
            # Yahoo Finance에서 정보 조회
            stock_data = self.get_stock_info_from_yahoo(stock_code, stock['market_type'])
            
            if stock_data:
                # 데이터베이스 업데이트
                return self.update_stock_in_database(stock_data)
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ {stock_code} 단일 업데이트 중 오류: {e}")
            return False
    
    def get_update_statistics(self) -> Dict[str, Any]:
        """업데이트 통계 정보 조회"""
        try:
            if not self.db_manager.connect():
                return {}
            
            # 전체 통계
            total_query = "SELECT COUNT(*) as total FROM stocks"
            total_result = self.db_manager.fetch_one(total_query)
            total_stocks = total_result['total'] if total_result else 0
            
            # 업데이트된 종목 수
            updated_query = "SELECT COUNT(*) as count FROM stocks WHERE total_shares != 10000000 AND total_shares != 0"
            updated_result = self.db_manager.fetch_one(updated_query)
            updated_count = updated_result['count'] if updated_result else 0
            
            # 임시값 종목 수
            temp_query = "SELECT COUNT(*) as count FROM stocks WHERE total_shares = 10000000"
            temp_result = self.db_manager.fetch_one(temp_query)
            temp_count = temp_result['count'] if temp_result else 0
            
            # 빈 값 종목 수
            empty_query = "SELECT COUNT(*) as count FROM stocks WHERE total_shares = 0"
            empty_result = self.db_manager.fetch_one(empty_query)
            empty_count = empty_result['count'] if empty_result else 0
            
            return {
                'total_stocks': total_stocks,
                'updated_stocks': updated_count,
                'temp_value_stocks': temp_count,
                'empty_value_stocks': empty_count,
                'update_progress': round((updated_count / total_stocks) * 100, 2) if total_stocks > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ 통계 조회 실패: {e}")
            return {}
        finally:
            self.db_manager.disconnect()

def main():
    """메인 실행 함수"""
    print("🚀 Yahoo Finance 주식 정보 업데이트 시스템 시작")
    print("=" * 60)
    
    updater = YahooStocksUpdater()
    
    # 1. 현재 통계 확인
    print("\n📊 현재 데이터 현황:")
    stats = updater.get_update_statistics()
    if stats:
        print(f"  전체 종목: {stats['total_stocks']:,}개")
        print(f"  업데이트 완료: {stats['updated_stocks']:,}개")
        print(f"  임시값: {stats['temp_value_stocks']:,}개")
        print(f"  빈 값: {stats['empty_value_stocks']:,}개")
        print(f"  진행률: {stats['update_progress']}%")
    
    # 2. 배치 업데이트 실행
    print(f"\n🔄 배치 업데이트 시작 (배치 크기: 50개)")
    updater.update_stocks_batch(50)
    
    # 3. 최종 통계 확인
    print(f"\n📊 업데이트 완료 통계:")
    final_stats = updater.get_update_statistics()
    if final_stats:
        print(f"  전체 종목: {final_stats['total_stocks']:,}개")
        print(f"  업데이트 완료: {final_stats['updated_stocks']:,}개")
        print(f"  임시값: {final_stats['temp_value_stocks']:,}개")
        print(f"  빈 값: {final_stats['empty_value_stocks']:,}개")
        print(f"  진행률: {final_stats['update_progress']}%")
    
    print(f"\n🎉 업데이트 완료!")
    print(f"  성공: {updater.update_count}개")
    print(f"  실패: {updater.error_count}개")

if __name__ == "__main__":
    main()
