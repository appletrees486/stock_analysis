#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_data 테이블에 거래대금 컬럼 추가
"""

from database_config import DatabaseManager

def add_trading_value_column():
    """daily_data 테이블에 거래대금 컬럼 추가"""
    db = DatabaseManager()
    
    try:
        if not db.connect():
            print("❌ 데이터베이스 연결 실패")
            return False
        
        print("🔄 daily_data 테이블에 거래대금 컬럼 추가 중...")
        
        # 거래대금 컬럼 추가
        alter_sql = """
        ALTER TABLE daily_data 
        ADD COLUMN trading_value BIGINT NULL COMMENT '거래대금 (거래량 × 종가)' 
        AFTER volume
        """
        
        if db.execute_query(alter_sql):
            print("✅ 거래대금 컬럼 추가 완료")
        else:
            print("❌ 거래대금 컬럼 추가 실패")
            return False
        
        # 기존 데이터에 거래대금 계산하여 업데이트
        print("🔄 기존 데이터에 거래대금 계산 중...")
        
        update_sql = """
        UPDATE daily_data 
        SET trading_value = volume * close 
        WHERE trading_value IS NULL
        """
        
        if db.execute_query(update_sql):
            print("✅ 기존 데이터 거래대금 계산 완료")
        else:
            print("❌ 기존 데이터 거래대금 계산 실패")
            return False
        
        # 거래대금 컬럼에 인덱스 추가
        print("🔄 거래대금 컬럼에 인덱스 추가 중...")
        
        index_sql = """
        CREATE INDEX idx_trading_value ON daily_data(trading_value DESC)
        """
        
        if db.execute_query(index_sql):
            print("✅ 거래대금 인덱스 추가 완료")
        else:
            print("⚠️ 거래대금 인덱스 추가 실패 (이미 존재할 수 있음)")
        
        # 컬럼 추가 확인
        print("🔄 컬럼 추가 확인 중...")
        
        describe_sql = "DESCRIBE daily_data"
        result = db.fetch_all(describe_sql)
        
        if result:
            print("✅ daily_data 테이블 구조:")
            for row in result:
                print(f"  {row['Field']}: {row['Type']} - {row['Null']} - {row['Key']} - {row['Default']} - {row['Extra']}")
        
        # 샘플 데이터 확인
        print("🔄 샘플 데이터 확인 중...")
        
        sample_sql = """
        SELECT stock_code, trade_date, close, volume, trading_value 
        FROM daily_data 
        WHERE trading_value IS NOT NULL 
        ORDER BY trade_date DESC 
        LIMIT 5
        """
        
        sample_result = db.fetch_all(sample_sql)
        
        if sample_result:
            print("✅ 거래대금 샘플 데이터:")
            for row in sample_result:
                print(f"  {row['stock_code']} {row['trade_date']}: 종가 {row['close']:,}원, 거래량 {row['volume']:,}주, 거래대금 {row['trading_value']:,}원")
        
        print("🎉 거래대금 컬럼 추가 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False
    finally:
        db.disconnect()

if __name__ == "__main__":
    add_trading_value_column()
