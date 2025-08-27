#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
누락된 종목들 수집 실행 스크립트
"""

from stock_data_collector import StockDataCollector
import logging
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('collect_missing_stocks.log', encoding='utf-8')
    ]
)

def collect_missing_stocks():
    """누락된 종목들 수집 실행"""
    print("🚀 누락된 종목들 수집 시작")
    print("=" * 60)
    
    try:
        # StockDataCollector 인스턴스 생성
        collector = StockDataCollector()
        
        # CSV 파일 경로
        csv_file = "missing_stocks_report_20250822_175637.csv"
        
        if not os.path.exists(csv_file):
            print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_file}")
            print("💡 먼저 stock_data_comparison.py를 실행하여 누락 종목 목록을 생성하세요.")
            return
        
        print(f"📁 CSV 파일 발견: {csv_file}")
        print("🔍 누락된 종목들을 읽어와서 수집을 시작합니다...")
        print()
        
        # CSV에서 누락된 종목들을 읽어와서 수집
        success, failed = collector.collect_missing_stocks_from_csv(csv_file)
        
        print()
        print("=" * 60)
        print("📊 누락된 종목 수집 완료!")
        print(f"✅ 성공: {success}개")
        print(f"❌ 실패: {failed}개")
        
        if success > 0:
            print("🎉 일부 종목이 성공적으로 수집되었습니다!")
            print("💡 실패한 종목들은 상장폐지되었거나 더 이상 거래되지 않을 수 있습니다.")
        else:
            print("⚠️ 모든 종목에서 실패했습니다.")
            print("💡 추가 개선이 필요할 수 있습니다.")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 수집 중 오류 발생: {str(e)}")
        logging.error(f"수집 중 오류: {str(e)}", exc_info=True)

if __name__ == "__main__":
    collect_missing_stocks()
