#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 스키마 업데이트 스크립트
거래률 계산을 위한 유통주식수 컬럼 추가
"""

from database_config import DatabaseManager
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_daily_data_collection_log_table():
    """daily_data_collection_log 테이블에 market_status 컬럼 추가"""
    try:
        db = DatabaseManager()
        if not db.connect():
            print("❌ 데이터베이스 연결 실패")
            return False
        
        print("🔍 daily_data_collection_log 테이블 스키마 확인 중...")
        
        # 1. 테이블 존재 여부 확인
        check_table_query = """
        SELECT COUNT(*) as table_exists 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'daily_data_collection_log'
        """
        
        table_exists = db.fetch_one(check_table_query)
        
        if not table_exists or table_exists['table_exists'] == 0:
            print("❌ daily_data_collection_log 테이블이 존재하지 않습니다")
            return False
        
        # 2. market_status 컬럼 존재 여부 확인
        check_column_query = """
        SELECT COUNT(*) as column_exists 
        FROM information_schema.columns 
        WHERE table_schema = DATABASE() 
        AND table_name = 'daily_data_collection_log' 
        AND column_name = 'market_status'
        """
        
        column_exists = db.fetch_one(check_column_query)
        
        if column_exists and column_exists['column_exists'] > 0:
            print("✅ market_status 컬럼이 이미 존재합니다")
            return True
        
        # 3. market_status 컬럼 추가
        print("📋 market_status 컬럼을 추가합니다...")
        
        add_column_query = """
        ALTER TABLE daily_data_collection_log 
        ADD COLUMN market_status VARCHAR(50) DEFAULT 'unknown' 
        AFTER is_market_closed
        """
        
        db.execute_query(add_column_query)
        print("✅ market_status 컬럼 추가 완료")
        
        # 4. 컬럼 설명 추가
        print("📝 컬럼 설명을 추가합니다...")
        
        add_comment_query = """
        ALTER TABLE daily_data_collection_log 
        MODIFY COLUMN market_status VARCHAR(50) 
        DEFAULT 'unknown' 
        COMMENT '장 상태: non_trading_day, before_market_open, during_market, near_market_close, after_market_close'
        """
        
        db.execute_query(add_comment_query)
        print("✅ 컬럼 설명 추가 완료")
        
        # 5. 기존 데이터에 기본값 설정
        print("🔄 기존 데이터에 기본값을 설정합니다...")
        
        update_default_query = """
        UPDATE daily_data_collection_log 
        SET market_status = 'unknown' 
        WHERE market_status IS NULL
        """
        
        db.execute_query(update_default_query)
        print("✅ 기존 데이터 기본값 설정 완료")
        
        # 6. 최종 확인
        print("🔍 최종 스키마 확인...")
        
        final_check_query = """
        DESCRIBE daily_data_collection_log
        """
        
        table_structure = db.fetch_all(final_check_query)
        
        print("📊 테이블 구조:")
        for column in table_structure:
            print(f"   {column['Field']}: {column['Type']} - {column.get('Comment', '')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 스키마 업데이트 실패: {e}")
        return False
    finally:
        if 'db' in locals():
            db.disconnect()

def update_technical_indicators_table():
    """technical_indicators 테이블에 필요한 컬럼들 추가"""
    try:
        db = DatabaseManager()
        if not db.connect():
            print("❌ 데이터베이스 연결 실패")
            return False
        
        print("🔍 technical_indicators 테이블 스키마 확인 중...")
        
        # 1. 테이블 존재 여부 확인
        check_table_query = """
        SELECT COUNT(*) as table_exists 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'technical_indicators'
        """
        
        table_exists = db.fetch_one(check_table_query)
        
        if not table_exists or table_exists['table_exists'] == 0:
            print("❌ technical_indicators 테이블이 존재하지 않습니다")
            return False
        
        # 2. 필요한 컬럼들 확인 및 추가
        required_columns = [
            ('ma5', 'DECIMAL(10,2)', '5일 이동평균'),
            ('ma20', 'DECIMAL(10,2)', '20일 이동평균'),
            ('ma60', 'DECIMAL(10,2)', '60일 이동평균'),
            ('ma120', 'DECIMAL(10,2)', '120일 이동평균'),
            ('rsi', 'DECIMAL(5,2)', 'RSI'),
            ('macd', 'DECIMAL(10,4)', 'MACD'),
            ('macd_signal', 'DECIMAL(10,4)', 'MACD Signal'),
            ('macd_histogram', 'DECIMAL(10,4)', 'MACD Histogram'),
            ('bb_upper', 'DECIMAL(10,2)', '볼린저 밴드 상단'),
            ('bb_middle', 'DECIMAL(10,2)', '볼린저 밴드 중간'),
            ('bb_lower', 'DECIMAL(10,2)', '볼린저 밴드 하단')
        ]
        
        for column_name, column_type, column_comment in required_columns:
            # 컬럼 존재 여부 확인
            check_column_query = """
            SELECT COUNT(*) as column_exists 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'technical_indicators' 
            AND column_name = %s
            """
            
            column_exists = db.fetch_one(check_column_query, (column_name,))
            
            if not column_exists or column_exists['column_exists'] == 0:
                print(f"📋 {column_name} 컬럼을 추가합니다...")
                
                add_column_query = f"""
                ALTER TABLE technical_indicators 
                ADD COLUMN {column_name} {column_type} 
                COMMENT '{column_comment}'
                """
                
                db.execute_query(add_column_query)
                print(f"✅ {column_name} 컬럼 추가 완료")
            else:
                print(f"✅ {column_name} 컬럼이 이미 존재합니다")
        
        return True
        
    except Exception as e:
        print(f"❌ technical_indicators 테이블 업데이트 실패: {e}")
        return False
    finally:
        if 'db' in locals():
            db.disconnect()

def update_stocks_table():
    """stocks 테이블에 유통주식수 컬럼 추가"""
    try:
        db = DatabaseManager()
        if not db.connect():
            logging.error("데이터베이스 연결 실패")
            return False
        
        # stocks 테이블에 유통주식수 컬럼 추가
        alter_query = """
        ALTER TABLE stocks 
        ADD COLUMN total_shares BIGINT DEFAULT 0 COMMENT '유통주식수',
        ADD COLUMN market_cap DECIMAL(20,2) DEFAULT 0.00 COMMENT '시가총액',
        ADD INDEX idx_total_shares (total_shares),
        ADD INDEX idx_market_cap (market_cap)
        """
        
        try:
            if db.execute_query(alter_query):
                logging.info("✅ stocks 테이블에 유통주식수 컬럼 추가 완료")
                return True
            else:
                logging.error("❌ stocks 테이블 컬럼 추가 실패")
                return False
        except Exception as e:
            # 컬럼이 이미 존재하는 경우 무시
            if "Duplicate column name" in str(e):
                logging.info("ℹ️ 유통주식수 컬럼이 이미 존재합니다")
                return True
            else:
                logging.error(f"❌ stocks 테이블 컬럼 추가 중 오류: {e}")
                return False
        finally:
            db.disconnect()
            
    except Exception as e:
        logging.error(f"❌ 데이터베이스 스키마 업데이트 실패: {e}")
        return False

def update_volume_ranking_utils():
    """거래률 계산을 위한 유통주식수 데이터 업데이트"""
    try:
        db = DatabaseManager()
        if not db.connect():
            logging.error("데이터베이스 연결 실패")
            return False
        
        # 임시로 유통주식수 데이터 설정 (실제로는 외부 API에서 가져와야 함)
        update_query = """
        UPDATE stocks 
        SET total_shares = 10000000,  -- 임시값: 1000만주
            market_cap = 0.00
        WHERE total_shares = 0 OR total_shares IS NULL
        """
        
        try:
            if db.execute_query(update_query):
                logging.info("✅ 유통주식수 임시 데이터 설정 완료")
                return True
            else:
                logging.error("❌ 유통주식수 데이터 설정 실패")
                return False
        finally:
            db.disconnect()
            
    except Exception as e:
        logging.error(f"❌ 유통주식수 데이터 업데이트 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔧 데이터베이스 스키마 업데이트 시작...")
    
    # 1. daily_data_collection_log 테이블 업데이트
    print("\n📋 1단계: daily_data_collection_log 테이블 업데이트")
    if update_daily_data_collection_log_table():
        print("✅ daily_data_collection_log 테이블 업데이트 완료")
    else:
        print("❌ daily_data_collection_log 테이블 업데이트 실패")
        return
    
    # 2. technical_indicators 테이블 업데이트
    print("\n📋 2단계: technical_indicators 테이블 업데이트")
    if update_technical_indicators_table():
        print("✅ technical_indicators 테이블 업데이트 완료")
    else:
        print("❌ technical_indicators 테이블 업데이트 실패")
        return
    
    # 3. stocks 테이블에 유통주식수 컬럼 추가
    print("\n📋 3단계: stocks 테이블에 유통주식수 컬럼 추가")
    if update_stocks_table():
        print("✅ stocks 테이블 스키마 업데이트 완료")
        
        # 4. 임시 유통주식수 데이터 설정
        if update_volume_ranking_utils():
            print("✅ 유통주식수 임시 데이터 설정 완료")
        else:
            print("⚠️ 유통주식수 데이터 설정 실패")
    else:
        print("❌ stocks 테이블 스키마 업데이트 실패")
        return
    
    print("\n🎉 모든 데이터베이스 스키마 업데이트가 완료되었습니다!")
    print("\n📋 다음 단계:")
    print("1. 실제 유통주식수 데이터를 외부 API에서 수집")
    print("2. volume_ranking_utils.py에서 거래률 계산 로직 구현")
    print("3. 거래량과 거래률이 다른 결과를 반환하도록 테스트")

if __name__ == "__main__":
    main()
