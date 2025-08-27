#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stocks 테이블 구조 및 데이터 분석 스크립트
"""

from database_config import DatabaseManager
import json

def analyze_stocks_table():
    """stocks 테이블 구조 및 데이터 분석"""
    try:
        db = DatabaseManager()
        if not db.connect():
            print("❌ 데이터베이스 연결 실패")
            return
        
        print("🔍 stocks 테이블 구조 분석 중...")
        print("=" * 60)
        
        # 1. 테이블 구조 확인
        print("\n📋 테이블 구조:")
        structure_result = db.fetch_all("DESCRIBE stocks")
        for row in structure_result:
            field = row['Field']
            field_type = row['Type']
            null_allowed = row['Null']
            key_type = row['Key']
            default_value = row['Default']
            print(f"  {field:15} | {field_type:20} | {null_allowed:3} | {key_type:8} | {default_value}")
        
        # 2. 전체 종목 수 확인
        print("\n📊 데이터 현황:")
        count_result = db.fetch_one("SELECT COUNT(*) as total FROM stocks")
        total_stocks = count_result['total']
        print(f"  전체 종목 수: {total_stocks:,}개")
        
        # 3. 시장별 종목 수 확인
        market_result = db.fetch_all("SELECT market_type, COUNT(*) as count FROM stocks GROUP BY market_type")
        for row in market_result:
            print(f"  {row['market_type']}: {row['count']:,}개")
        
        # 4. 유통주식수 데이터 현황
        shares_result = db.fetch_all("""
            SELECT 
                CASE 
                    WHEN total_shares = 0 THEN '0 (빈 값)'
                    WHEN total_shares = 10000000 THEN '10000000 (임시값)'
                    ELSE '기타 값'
                END as shares_status,
                COUNT(*) as count
            FROM stocks 
            GROUP BY 
                CASE 
                    WHEN total_shares = 0 THEN '0 (빈 값)'
                    WHEN total_shares = 10000000 THEN '10000000 (임시값)'
                    ELSE '기타 값'
                END
        """)
        
        print(f"\n  유통주식수 데이터 현황:")
        for row in shares_result:
            print(f"    {row['shares_status']}: {row['count']:,}개")
        
        # 5. 샘플 데이터 확인 (상위 5개)
        print(f"\n📈 샘플 데이터 (상위 5개):")
        sample_result = db.fetch_all("""
            SELECT stock_code, stock_name, market_type, total_shares, market_cap, created_at, updated_at
            FROM stocks 
            ORDER BY stock_code 
            LIMIT 5
        """)
        
        for row in sample_result:
            print(f"  {row['stock_code']} | {row['stock_name']:15} | {row['market_type']:6} | {row['total_shares']:10,} | {row['market_cap']:8} | {row['updated_at']}")
        
        # 6. 최근 업데이트된 종목 확인
        print(f"\n🕒 최근 업데이트된 종목 (상위 5개):")
        recent_result = db.fetch_all("""
            SELECT stock_code, stock_name, market_type, total_shares, updated_at
            FROM stocks 
            ORDER BY updated_at DESC 
            LIMIT 5
        """)
        
        for row in recent_result:
            print(f"  {row['stock_code']} | {row['stock_name']:15} | {row['market_type']:6} | {row['total_shares']:10,} | {row['updated_at']}")
        
        db.disconnect()
        
        print("\n" + "=" * 60)
        print("✅ stocks 테이블 분석 완료")
        
    except Exception as e:
        print(f"❌ 테이블 분석 중 오류 발생: {e}")

if __name__ == "__main__":
    analyze_stocks_table()
