#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_data 테이블에 시가총액 컬럼 추가 스크립트
"""

from database_config import DatabaseManager

def add_market_cap_column():
    """daily_data 테이블에 시가총액 컬럼 추가"""
    db = DatabaseManager()
    
    try:
        if not db.connect():
            print("❌ 데이터베이스 연결 실패")
            return
        
        print("=== daily_data 테이블에 시가총액 컬럼 추가 ===")
        
        # market_cap_at_date 컬럼 추가
        alter_query = """
        ALTER TABLE daily_data 
        ADD COLUMN market_cap_at_date DECIMAL(20,2) DEFAULT 0.00 COMMENT '해당 거래일의 시가총액',
        ADD INDEX idx_market_cap_at_date (market_cap_at_date)
        """
        
        success = db.execute_query(alter_query)
        
        if success:
            print("✅ market_cap_at_date 컬럼 추가 완료")
            
            # 테이블 구조 확인
            print("\n=== 수정된 daily_data 테이블 구조 ===")
            result = db.fetch_all("DESCRIBE daily_data")
            for row in result:
                print(f"{row['Field']}: {row['Type']} {row['Null']} {row['Key']} {row['Default']} {row['Extra']}")
        else:
            print("❌ market_cap_at_date 컬럼 추가 실패")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    add_market_cap_column()
