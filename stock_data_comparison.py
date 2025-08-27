#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주식 데이터 비교 분석 도구
stocks 테이블과 daily_data 테이블을 비교하여 누락된 데이터를 분석
"""

import pandas as pd
from datetime import datetime, timedelta
from database_config import DatabaseManager
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('stock_data_comparison.log', encoding='utf-8')
    ]
)

class StockDataComparator:
    """주식 데이터 비교 분석 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        self.comparison_results = {}
        
    def connect_database(self):
        """데이터베이스 연결"""
        try:
            if self.db.connect():
                logging.info("✅ 데이터베이스 연결 성공")
                return True
            else:
                logging.error("❌ 데이터베이스 연결 실패")
                return False
        except Exception as e:
            logging.error(f"❌ 데이터베이스 연결 중 오류: {e}")
            return False
    
    def disconnect_database(self):
        """데이터베이스 연결 해제"""
        try:
            self.db.disconnect()
            logging.info("🔌 데이터베이스 연결 해제")
        except Exception as e:
            logging.error(f"❌ 데이터베이스 연결 해제 중 오류: {e}")
    
    def get_stocks_table_data(self):
        """stocks 테이블 데이터 조회"""
        try:
            query = """
            SELECT stock_code, stock_name, market_type, is_active, created_at, updated_at
            FROM stocks 
            WHERE is_active = 1
            ORDER BY stock_code
            """
            result = self.db.fetch_all(query)
            
            if result:
                stocks_df = pd.DataFrame(result)
                logging.info(f"✅ stocks 테이블 조회 완료: {len(stocks_df)}개 종목")
                return stocks_df
            else:
                logging.warning("⚠️ stocks 테이블에 데이터가 없습니다.")
                return pd.DataFrame()
                
        except Exception as e:
            logging.error(f"❌ stocks 테이블 조회 중 오류: {e}")
            return pd.DataFrame()
    
    def get_daily_data_summary(self):
        """daily_data 테이블 요약 정보 조회"""
        try:
            query = """
            SELECT 
                stock_code,
                COUNT(*) as record_count,
                MIN(trade_date) as first_date,
                MAX(trade_date) as last_date,
                MAX(updated_at) as last_updated
            FROM daily_data 
            GROUP BY stock_code
            ORDER BY stock_code
            """
            result = self.db.fetch_all(query)
            
            if result:
                daily_df = pd.DataFrame(result)
                logging.info(f"✅ daily_data 테이블 요약 조회 완료: {len(daily_df)}개 종목")
                return daily_df
            else:
                logging.warning("⚠️ daily_data 테이블에 데이터가 없습니다.")
                return pd.DataFrame()
                
        except Exception as e:
            logging.error(f"❌ daily_data 테이블 조회 중 오류: {e}")
            return pd.DataFrame()
    
    def compare_stocks_and_daily_data(self):
        """stocks 테이블과 daily_data 테이블 비교"""
        try:
            logging.info("🔍 stocks 테이블과 daily_data 테이블 비교 시작")
            
            # 데이터 조회
            stocks_df = self.get_stocks_table_data()
            daily_df = self.get_daily_data_summary()
            
            if stocks_df.empty:
                logging.error("❌ stocks 테이블 데이터가 없어 비교를 진행할 수 없습니다.")
                return None
            
            # 비교 분석
            comparison_results = {
                'total_stocks': len(stocks_df),
                'stocks_with_daily_data': len(daily_df),
                'stocks_without_daily_data': 0,
                'missing_stocks': [],
                'stocks_with_incomplete_data': [],
                'comparison_timestamp': datetime.now()
            }
            
            # daily_data에 없는 종목 찾기
            stocks_codes = set(stocks_df['stock_code'])
            daily_codes = set(daily_df['stock_code']) if not daily_df.empty else set()
            
            missing_codes = stocks_codes - daily_codes
            comparison_results['stocks_without_daily_data'] = len(missing_codes)
            
            # 누락된 종목 상세 정보
            for code in missing_codes:
                stock_info = stocks_df[stocks_df['stock_code'] == code].iloc[0]
                missing_stock = {
                    'stock_code': code,
                    'stock_name': stock_info['stock_name'],
                    'market_type': stock_info['market_type'],
                    'created_at': stock_info['created_at'],
                    'status': '완전 누락'
                }
                comparison_results['missing_stocks'].append(missing_stock)
            
            # 데이터가 있지만 불완전한 종목 찾기 (최근 30일 데이터 없음)
            if not daily_df.empty:
                recent_date = datetime.now().date() - timedelta(days=30)
                
                for _, daily_row in daily_df.iterrows():
                    code = daily_row['stock_code']
                    last_date = daily_row['last_date']
                    
                    if last_date and last_date < recent_date:
                        stock_info = stocks_df[stocks_df['stock_code'] == code].iloc[0]
                        incomplete_stock = {
                            'stock_code': code,
                            'stock_name': stock_info['stock_name'],
                            'market_type': stock_info['market_type'],
                            'last_data_date': last_date,
                            'days_since_last_data': (datetime.now().date() - last_date).days,
                            'status': '데이터 오래됨'
                        }
                        comparison_results['stocks_with_incomplete_data'].append(incomplete_stock)
            
            self.comparison_results = comparison_results
            logging.info("✅ 비교 분석 완료")
            return comparison_results
            
        except Exception as e:
            logging.error(f"❌ 비교 분석 중 오류: {e}")
            return None
    
    def generate_missing_stocks_report(self, output_file=None):
        """누락된 종목 보고서 생성"""
        if not self.comparison_results:
            logging.error("❌ 비교 결과가 없습니다. 먼저 compare_stocks_and_daily_data()를 실행하세요.")
            return False
        
        try:
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"missing_stocks_report_{timestamp}.csv"
            
            # 완전히 누락된 종목들
            missing_df = pd.DataFrame(self.comparison_results['missing_stocks'])
            
            # 데이터가 오래된 종목들
            incomplete_df = pd.DataFrame(self.comparison_results['stocks_with_incomplete_data'])
            
            # 전체 요약 정보
            summary_data = {
                '분석 항목': [
                    '총 종목 수',
                    'daily_data 있는 종목 수',
                    'daily_data 없는 종목 수',
                    '데이터 오래된 종목 수',
                    '분석 일시'
                ],
                '수치': [
                    self.comparison_results['total_stocks'],
                    self.comparison_results['stocks_with_daily_data'],
                    self.comparison_results['stocks_without_daily_data'],
                    len(self.comparison_results['stocks_with_incomplete_data']),
                    self.comparison_results['comparison_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            
            # Excel 파일로 저장
            excel_file = output_file.replace('.csv', '.xlsx')
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='요약', index=False)
                
                if not missing_df.empty:
                    missing_df.to_excel(writer, sheet_name='완전_누락_종목', index=False)
                
                if not incomplete_df.empty:
                    incomplete_df.to_excel(writer, sheet_name='데이터_오래된_종목', index=False)
            
            logging.info(f"✅ 보고서 생성 완료: {excel_file}")
            
            # CSV 파일도 생성 (간단한 형식)
            if not missing_df.empty:
                missing_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                logging.info(f"✅ CSV 보고서 생성 완료: {output_file}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ 보고서 생성 중 오류: {e}")
            return False
    
    def print_summary(self):
        """요약 정보 출력"""
        if not self.comparison_results:
            logging.error("❌ 비교 결과가 없습니다.")
            return
        
        print("\n" + "="*80)
        print("📊 주식 데이터 비교 분석 결과")
        print("="*80)
        
        results = self.comparison_results
        print(f"📈 총 종목 수: {results['total_stocks']:,}개")
        print(f"✅ daily_data 있는 종목: {results['stocks_with_daily_data']:,}개")
        print(f"❌ daily_data 없는 종목: {results['stocks_without_daily_data']:,}개")
        print(f"⚠️ 데이터 오래된 종목: {len(results['stocks_with_incomplete_data']):,}개")
        print(f"📅 분석 일시: {results['comparison_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        if results['missing_stocks']:
            print(f"\n🔍 완전히 누락된 종목 (상위 10개):")
            for i, stock in enumerate(results['missing_stocks'][:10]):
                print(f"   {i+1:2d}. {stock['stock_code']} - {stock['stock_name']} ({stock['market_type']})")
            
            if len(results['missing_stocks']) > 10:
                print(f"   ... 외 {len(results['missing_stocks']) - 10}개 종목")
        
        if results['stocks_with_incomplete_data']:
            print(f"\n⚠️ 데이터가 오래된 종목 (상위 10개):")
            incomplete_sorted = sorted(results['stocks_with_incomplete_data'], 
                                     key=lambda x: x['days_since_last_data'], reverse=True)
            for i, stock in enumerate(incomplete_sorted[:10]):
                print(f"   {i+1:2d}. {stock['stock_code']} - {stock['stock_name']} "
                      f"(마지막 데이터: {stock['last_data_date']}, {stock['days_since_last_data']}일 전)")
            
            if len(results['stocks_with_incomplete_data']) > 10:
                print(f"   ... 외 {len(results['stocks_with_incomplete_data']) - 10}개 종목")
        
        print("="*80)
    
    def run_full_analysis(self, output_file=None):
        """전체 분석 실행"""
        try:
            logging.info("🚀 전체 주식 데이터 비교 분석 시작")
            
            # 데이터베이스 연결
            if not self.connect_database():
                return False
            
            # 비교 분석 실행
            comparison_result = self.compare_stocks_and_daily_data()
            if comparison_result is None:
                return False
            
            # 요약 정보 출력
            self.print_summary()
            
            # 보고서 생성
            if self.generate_missing_stocks_report(output_file):
                logging.info("✅ 전체 분석 완료")
                return True
            else:
                logging.error("❌ 보고서 생성 실패")
                return False
                
        except Exception as e:
            logging.error(f"❌ 전체 분석 중 오류: {e}")
            return False
        finally:
            self.disconnect_database()

def main():
    """메인 함수"""
    print("🔍 주식 데이터 비교 분석 도구")
    print("="*50)
    
    comparator = StockDataComparator()
    
    # 전체 분석 실행
    success = comparator.run_full_analysis()
    
    if success:
        print("\n✅ 분석이 성공적으로 완료되었습니다.")
        print("📁 결과 파일이 생성되었습니다.")
    else:
        print("\n❌ 분석 중 오류가 발생했습니다.")
        print("📋 로그 파일을 확인해주세요.")

if __name__ == "__main__":
    main()
