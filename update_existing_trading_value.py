#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 데이터에 거래대금 계산하여 업데이트
"""

from database_config import DatabaseManager

def update_existing_trading_value():
    """기존 데이터에 거래대금 계산하여 업데이트"""
    db = DatabaseManager()
    
    try:
        if not db.connect():
            print("❌ 데이터베이스 연결 실패")
            return False
        
        print("🔄 기존 데이터에 거래대금 계산 중...")
        
        # 기존 데이터에 거래대금 계산하여 업데이트
        update_sql = """
        UPDATE daily_data 
        SET trading_value = volume * close 
        WHERE trading_value IS NULL
        """
        
        if db.execute_query(update_sql):
            print("✅ 기존 데이터 거래대금 계산 완료")
            
            # 업데이트된 데이터 수 확인
            count_sql = "SELECT COUNT(*) as count FROM daily_data WHERE trading_value IS NOT NULL"
            result = db.fetch_one(count_sql)
            if result:
                print(f"📊 거래대금이 있는 데이터: {result['count']:,}개")
            
            # 전체 데이터 수 확인
            total_sql = "SELECT COUNT(*) as count FROM daily_data"
            total_result = db.fetch_one(total_sql)
            if total_result:
                print(f"📊 전체 일봉 데이터: {total_result['count']:,}개")
            
            return True
        else:
            print("❌ 기존 데이터 거래대금 계산 실패")
            return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False
    finally:
        db.disconnect()

if __name__ == "__main__":
    update_existing_trading_value()
