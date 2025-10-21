#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
신규 상장 종목 감지 모듈
stock 테이블과 pykrx 종목 리스트를 비교하여 신규 상장된 종목을 감지합니다.
"""

import sys
import os
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# PyKrx 라이브러리 import
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError as e:
    PYKRX_AVAILABLE = False
    print(f"⚠️ PyKrx 라이브러리 import 실패: {e}")
    print("💡 PyKrx 설치: pip install pykrx")

from database_config import DatabaseManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('new_stock_detector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class NewStockDetector:
    """신규 상장 종목 감지 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        self.start_time = datetime.now()
        self.new_stocks = []
        
        # PyKrx 사용 가능 여부 확인
        if not PYKRX_AVAILABLE:
            raise ImportError("PyKrx 라이브러리가 설치되지 않았습니다. 'pip install pykrx'로 설치해주세요.")
    
    def get_existing_stocks(self) -> Set[str]:
        """데이터베이스에서 기존 종목 목록 조회"""
        try:
            logging.info("📊 데이터베이스에서 기존 종목 목록 조회 중...")
            
            if not self.db.connect():
                raise Exception("데이터베이스 연결 실패")
            
            # 활성화된 종목만 조회
            query = """
                SELECT stock_code, stock_name, market_type 
                FROM stocks 
                WHERE is_active = TRUE
                ORDER BY stock_code
            """
            
            results = self.db.fetch_all(query)
            
            if not results:
                logging.warning("⚠️ stocks 테이블에 데이터가 없습니다.")
                return set()
            
            existing_stocks = set()
            logging.info(f"✅ 기존 종목 {len(results)}개 조회 완료")
            
            # 종목별 정보 로깅 (처음 10개만)
            for i, stock_info in enumerate(results[:10]):
                logging.info(f"   {i+1:2d}. {stock_info['stock_code']} - {stock_info['stock_name']} ({stock_info['market_type']})")
            
            if len(results) > 10:
                logging.info(f"   ... 외 {len(results) - 10}개 종목")
            
            # 종목 코드만 추출
            existing_stocks = {stock_info['stock_code'] for stock_info in results}
            
            return existing_stocks
            
        except Exception as e:
            logging.error(f"❌ 기존 종목 조회 실패: {e}")
            return set()
        finally:
            self.db.disconnect()
    
    def get_latest_stocks(self, market: Optional[str] = None) -> Dict[str, List[str]]:
        """pykrx를 통해 최신 종목 목록 조회"""
        try:
            logging.info("🔍 PyKrx에서 최신 종목 목록 조회 중...")
            
            latest_stocks = {}
            
            # 조회할 시장 목록
            markets_to_check = []
            if market:
                markets_to_check = [market.upper()]
            else:
                markets_to_check = ['KOSPI', 'KOSDAQ']
            
            for market_type in markets_to_check:
                try:
                    logging.info(f"   📈 {market_type} 종목 조회 중...")
                    
                    # PyKrx로 종목 목록 조회
                    tickers = stock.get_market_ticker_list(market=market_type)
                    
                    if tickers:
                        latest_stocks[market_type] = tickers
                        logging.info(f"   ✅ {market_type}: {len(tickers)}개 종목 조회 완료")
                        
                        # 처음 5개 종목 코드 표시
                        sample_tickers = tickers[:5]
                        logging.info(f"      샘플: {', '.join(sample_tickers)}")
                    else:
                        logging.warning(f"   ⚠️ {market_type}: 종목 데이터가 없습니다.")
                        latest_stocks[market_type] = []
                        
                except Exception as e:
                    logging.error(f"   ❌ {market_type} 종목 조회 실패: {e}")
                    latest_stocks[market_type] = []
            
            return latest_stocks
            
        except Exception as e:
            logging.error(f"❌ 최신 종목 조회 실패: {e}")
            return {}
    
    def get_stock_info_from_pykrx(self, stock_code: str) -> Optional[Dict[str, str]]:
        """pykrx에서 특정 종목의 상세 정보 조회"""
        try:
            # 종목명 조회
            stock_name = stock.get_market_ticker_name(stock_code)
            
            if stock_name:
                return {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'market_type': self._determine_market_type(stock_code)
                }
            return None
            
        except Exception as e:
            logging.debug(f"종목 정보 조회 실패 ({stock_code}): {e}")
            return None
    
    def _determine_market_type(self, stock_code: str) -> str:
        """종목 코드로 시장 구분 판단 (pykrx에서 직접 확인)"""
        try:
            # KOSPI에서 먼저 확인
            kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
            if stock_code in kospi_tickers:
                return "KOSPI"
            
            # KOSDAQ에서 확인
            kosdaq_tickers = stock.get_market_ticker_list(market="KOSDAQ")
            if stock_code in kosdaq_tickers:
                return "KOSDAQ"
            
            return "UNKNOWN"
            
        except Exception as e:
            logging.debug(f"시장 구분 실패 ({stock_code}): {e}")
            return "UNKNOWN"
    
    def compare_stocks(self, existing_stocks: Set[str], latest_stocks: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """신규 종목 식별"""
        try:
            logging.info("🔍 신규 종목 식별 중...")
            
            # 모든 최신 종목을 하나의 세트로 합치기
            all_latest_stocks = set()
            for market_type, tickers in latest_stocks.items():
                all_latest_stocks.update(tickers)
            
            # 신규 종목 찾기
            new_stock_codes = all_latest_stocks - existing_stocks
            
            if not new_stock_codes:
                logging.info("✅ 신규 상장 종목이 없습니다.")
                return []
            
            logging.info(f"🎉 신규 상장 종목 {len(new_stock_codes)}개 발견!")
            
            # 신규 종목의 상세 정보 수집
            new_stocks = []
            for i, stock_code in enumerate(new_stock_codes, 1):
                logging.info(f"   📊 신규 종목 {i}/{len(new_stock_codes)}: {stock_code} 정보 수집 중...")
                
                stock_info = self.get_stock_info_from_pykrx(stock_code)
                if stock_info:
                    new_stocks.append(stock_info)
                    logging.info(f"      ✅ {stock_code} - {stock_info['stock_name']} ({stock_info['market_type']})")
                else:
                    logging.warning(f"      ⚠️ {stock_code} - 정보 수집 실패")
            
            self.new_stocks = new_stocks
            return new_stocks
            
        except Exception as e:
            logging.error(f"❌ 신규 종목 식별 실패: {e}")
            return []
    
    def update_database(self, new_stocks: List[Dict[str, str]]) -> bool:
        """신규 종목을 데이터베이스에 추가"""
        try:
            if not new_stocks:
                logging.info("추가할 신규 종목이 없습니다.")
                return True
            
            logging.info(f"💾 {len(new_stocks)}개 신규 종목을 데이터베이스에 추가 중...")
            
            if not self.db.connect():
                raise Exception("데이터베이스 연결 실패")
            
            # 배치 삽입을 위한 데이터 준비
            insert_data = []
            for stock_info in new_stocks:
                insert_data.append((
                    stock_info['stock_code'],
                    stock_info['stock_name'],
                    stock_info['market_type'],
                    None,  # listing_date (pykrx에서 제공하지 않음)
                    True,   # is_active
                    datetime.now(),  # created_at
                    datetime.now()   # updated_at
                ))
            
            # 배치 삽입 쿼리
            insert_query = """
                INSERT INTO stocks (stock_code, stock_name, market_type, listing_date, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    stock_name = VALUES(stock_name),
                    market_type = VALUES(market_type),
                    is_active = VALUES(is_active),
                    updated_at = VALUES(updated_at)
            """
            
            # 배치 실행
            success = self.db.execute_many(insert_query, insert_data)
            
            if success:
                logging.info(f"✅ {len(new_stocks)}개 신규 종목이 데이터베이스에 추가되었습니다.")
                return True
            else:
                logging.error("❌ 신규 종목 데이터베이스 추가 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ 데이터베이스 업데이트 실패: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def print_summary(self, new_stocks: List[Dict[str, str]], execution_time: float):
        """결과 요약 출력"""
        print("\n" + "="*60)
        print("[RESULT] 신규 상장 종목 감지 결과")
        print("="*60)
        
        if not new_stocks:
            print("[INFO] 신규 상장 종목이 없습니다.")
        else:
            print(f"[SUCCESS] 신규 상장 종목 {len(new_stocks)}개 발견!")
            print("\n[LIST] 신규 종목 목록:")
            print("-" * 60)
            print(f"{'순번':<4} {'종목코드':<8} {'종목명':<20} {'시장':<8}")
            print("-" * 60)
            
            for i, stock_info in enumerate(new_stocks, 1):
                print(f"{i:<4} {stock_info['stock_code']:<8} {stock_info['stock_name']:<20} {stock_info['market_type']:<8}")
        
        print("-" * 60)
        print(f"[TIME] 실행 시간: {execution_time:.2f}초")
        print(f"[DATE] 실행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
    
    def run(self, market: Optional[str] = None, auto_update: bool = True) -> bool:
        """메인 실행 함수"""
        try:
            logging.info("🚀 신규 상장 종목 감지 시작")
            logging.info(f"   시장: {market if market else '전체 (KOSPI + KOSDAQ)'}")
            logging.info(f"   자동 업데이트: {'예' if auto_update else '아니오'}")
            
            # 1. 기존 종목 조회
            existing_stocks = self.get_existing_stocks()
            if not existing_stocks:
                logging.error("❌ 기존 종목 조회 실패")
                return False
            
            # 2. 최신 종목 조회
            latest_stocks = self.get_latest_stocks(market)
            if not latest_stocks:
                logging.error("❌ 최신 종목 조회 실패")
                return False
            
            # 3. 신규 종목 식별
            new_stocks = self.compare_stocks(existing_stocks, latest_stocks)
            
            # 4. 신규 종목이 있으면 자동으로 DB 업데이트
            if new_stocks and auto_update:
                update_success = self.update_database(new_stocks)
                if not update_success:
                    logging.error("❌ 데이터베이스 업데이트 실패")
                    return False
            
            # 5. 결과 요약
            execution_time = (datetime.now() - self.start_time).total_seconds()
            self.print_summary(new_stocks, execution_time)
            
            logging.info("✅ 신규 상장 종목 감지 완료")
            return True
            
        except Exception as e:
            logging.error(f"❌ 실행 중 오류 발생: {e}")
            return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="신규 상장 종목 감지 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python new_stock_detector.py                    # 전체 시장 신규 종목 확인 및 DB 자동 업데이트
  python new_stock_detector.py --market KOSPI     # KOSPI만 확인 및 DB 자동 업데이트
  python new_stock_detector.py --no-update        # 신규 종목 확인만 (DB 업데이트 안함)
        """
    )
    
    parser.add_argument(
        '--market',
        choices=['KOSPI', 'KOSDAQ'],
        help='확인할 시장 (KOSPI 또는 KOSDAQ). 지정하지 않으면 전체 시장 확인'
    )
    
    parser.add_argument(
        '--no-update',
        action='store_true',
        help='신규 종목을 데이터베이스에 추가하지 않고 확인만 수행'
    )
    
    args = parser.parse_args()
    
    try:
        # 신규 종목 감지기 생성 및 실행
        detector = NewStockDetector()
        success = detector.run(market=args.market, auto_update=not args.no_update)
        
        if success:
            print("\n[SUCCESS] 신규 상장 종목 감지가 성공적으로 완료되었습니다.")
            sys.exit(0)
        else:
            print("\n[ERROR] 신규 상장 종목 감지 중 오류가 발생했습니다.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n[WARNING] 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
