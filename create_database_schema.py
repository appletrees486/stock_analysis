#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 데이터베이스 스키마 생성 스크립트
"""

from database_config import DatabaseManager
import logging

def create_tables(db):
    """데이터베이스 테이블 생성"""
    
    # 1. 종목 정보 테이블
    stocks_table = """
    CREATE TABLE IF NOT EXISTS stocks (
        stock_code VARCHAR(6) PRIMARY KEY,
        stock_name VARCHAR(100) NOT NULL,
        market_type ENUM('KOSPI', 'KOSDAQ') NOT NULL,
        listing_date DATE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_market_type (market_type),
        INDEX idx_is_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 2. 일봉 데이터 테이블
    daily_data_table = """
    CREATE TABLE IF NOT EXISTS daily_data (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(6) NOT NULL,
        trade_date DATE NOT NULL,
        open DECIMAL(10,2) NOT NULL,
        high DECIMAL(10,2) NOT NULL,
        low DECIMAL(10,2) NOT NULL,
        close DECIMAL(10,2) NOT NULL,
        volume BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
        UNIQUE KEY unique_stock_date (stock_code, trade_date),
        INDEX idx_stock_code (stock_code),
        INDEX idx_trade_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 3. 주봉 데이터 테이블 (보조지표 컬럼 추가)
    weekly_data_table = """
    CREATE TABLE IF NOT EXISTS weekly_data (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(6) NOT NULL,
        week_start DATE NOT NULL,
        open DECIMAL(10,2) NOT NULL,
        high DECIMAL(10,2) NOT NULL,
        low DECIMAL(10,2) NOT NULL,
        close DECIMAL(10,2) NOT NULL,
        volume BIGINT NOT NULL,
        -- 보조지표 컬럼 추가
        ma5 DECIMAL(10,2),
        ma20 DECIMAL(10,2),
        ma60 DECIMAL(10,2),
        rsi DECIMAL(5,2),
        stoch_k DECIMAL(5,2),
        stoch_d DECIMAL(5,2),
        bb_upper DECIMAL(10,2),
        bb_middle DECIMAL(10,2),
        bb_lower DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
        UNIQUE KEY unique_stock_week (stock_code, week_start),
        INDEX idx_stock_code (stock_code),
        INDEX idx_week_start (week_start)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 4. 월봉 데이터 테이블 (보조지표 컬럼 추가)
    monthly_data_table = """
    CREATE TABLE IF NOT EXISTS monthly_data (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(6) NOT NULL,
        month_start DATE NOT NULL,
        open DECIMAL(10,2) NOT NULL,
        high DECIMAL(10,2) NOT NULL,
        low DECIMAL(10,2) NOT NULL,
        close DECIMAL(10,2) NOT NULL,
        volume BIGINT NOT NULL,
        -- 보조지표 컬럼 추가
        ma5 DECIMAL(10,2),
        ma20 DECIMAL(10,2),
        ma60 DECIMAL(10,2),
        cci DECIMAL(10,2),
        adx DECIMAL(5,2),
        plus_di DECIMAL(5,2),
        minus_di DECIMAL(5,2),
        bb_upper DECIMAL(10,2),
        bb_middle DECIMAL(10,2),
        bb_lower DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
        UNIQUE KEY unique_stock_month (stock_code, month_start),
        INDEX idx_stock_code (stock_code),
        INDEX idx_month_start (month_start)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 5. 기술적 지표 테이블
    technical_indicators_table = """
    CREATE TABLE IF NOT EXISTS technical_indicators (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(6) NOT NULL,
        trade_date DATE NOT NULL,
        ma5 DECIMAL(10,2),
        ma20 DECIMAL(10,2),
        ma60 DECIMAL(10,2),
        ma120 DECIMAL(10,2),
        rsi DECIMAL(5,2),
        macd DECIMAL(10,4),
        macd_signal DECIMAL(10,4),
        macd_histogram DECIMAL(10,4),
        bb_upper DECIMAL(10,2),
        bb_middle DECIMAL(10,2),
        bb_lower DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
        UNIQUE KEY unique_stock_date (stock_code, trade_date),
        INDEX idx_stock_code (stock_code),
        INDEX idx_trade_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 6. 데이터 수집 이력 테이블
    data_collection_log_table = """
    CREATE TABLE IF NOT EXISTS data_collection_log (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        collection_date DATE NOT NULL,
        total_stocks INT NOT NULL,
        success_count INT NOT NULL,
        failed_count INT NOT NULL,
        collection_type ENUM('DAILY', 'WEEKLY', 'MONTHLY') NOT NULL,
        started_at TIMESTAMP NOT NULL,
        completed_at TIMESTAMP,
        status ENUM('RUNNING', 'COMPLETED', 'FAILED') DEFAULT 'RUNNING',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 7. 종목별 수집 상태 테이블
    stock_collection_status_table = """
    CREATE TABLE IF NOT EXISTS stock_collection_status (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(6) NOT NULL,
        last_collected_date DATE NOT NULL,
        last_collected_timestamp TIMESTAMP NULL COMMENT '마지막 수집 시간 (장중/장마감 구분용)',
        last_collected_close DECIMAL(10,2) NOT NULL,
        last_collected_volume BIGINT NOT NULL,
        data_start_date DATE NOT NULL,
        data_end_date DATE NOT NULL,
        total_records INT NOT NULL,
        collection_quality VARCHAR(20) DEFAULT 'UNKNOWN' COMMENT '수집 데이터 품질 (INTRADAY/CLOSING/UNKNOWN)',
        last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE,
        UNIQUE KEY unique_stock_code (stock_code),
        INDEX idx_last_collected_date (last_collected_date),
        INDEX idx_data_end_date (data_end_date),
        INDEX idx_collection_quality (collection_quality)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 테이블 생성 실행
    tables = [
        ("stocks", stocks_table),
        ("daily_data", daily_data_table),
        ("weekly_data", weekly_data_table),
        ("monthly_data", monthly_data_table),
        ("technical_indicators", technical_indicators_table),
        ("data_collection_log", data_collection_log_table),
        ("stock_collection_status", stock_collection_status_table)
    ]
    
    for table_name, table_sql in tables:
        try:
            if db.execute_query(table_sql):
                logging.info(f"✅ {table_name} 테이블 생성 완료")
            else:
                logging.error(f"❌ {table_name} 테이블 생성 실패")
                return False
        except Exception as e:
            logging.error(f"❌ {table_name} 테이블 생성 중 오류: {e}")
            return False
    
    return True

def insert_test_stocks(db):
    """테스트용 종목 데이터 삽입"""
    test_stocks = [
        ('019210', '이화전기공업', 'KOSPI', None),
        ('023410', '한국정보통신', 'KOSPI', None),
        ('145720', '덕우전자', 'KOSDAQ', None),
        ('005930', '삼성전자', 'KOSPI', None),
        ('014280', '상화', 'KOSPI', None)
    ]
    
    insert_sql = """
    INSERT IGNORE INTO stocks (stock_code, stock_name, market_type, listing_date)
    VALUES (%s, %s, %s, %s)
    """
    
    try:
        if db.execute_many(insert_sql, test_stocks):
            logging.info(f"✅ 테스트 종목 {len(test_stocks)}개 삽입 완료")
            return True
        else:
            logging.error("❌ 테스트 종목 삽입 실패")
            return False
    except Exception as e:
        logging.error(f"❌ 테스트 종목 삽입 중 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 MySQL 데이터베이스 스키마 생성 시작")
    print("="*50)
    
    # 데이터베이스 연결
    db = DatabaseManager()
    if not db.connect():
        print("❌ 데이터베이스 연결 실패")
        return
    
    try:
        # 테이블 생성
        print("📋 데이터베이스 테이블 생성 중...")
        if create_tables(db):
            print("✅ 모든 테이블 생성 완료")
        else:
            print("❌ 테이블 생성 실패")
            return
        
        # 테스트 종목 데이터 삽입
        print("\n📊 테스트 종목 데이터 삽입 중...")
        if insert_test_stocks(db):
            print("✅ 테스트 종목 데이터 삽입 완료")
        else:
            print("❌ 테스트 종목 데이터 삽입 실패")
            return
        
        print("\n🎉 데이터베이스 스키마 생성 완료!")
        print("📊 생성된 테이블:")
        print("   - stocks: 종목 정보")
        print("   - daily_data: 일봉 데이터")
        print("   - weekly_data: 주봉 데이터")
        print("   - monthly_data: 월봉 데이터")
        print("   - technical_indicators: 기술적 지표")
        print("   - data_collection_log: 수집 이력")
        print("   - stock_collection_status: 종목별 수집 상태")
        
    except Exception as e:
        logging.error(f"❌ 스키마 생성 중 오류: {e}")
        print(f"❌ 오류 발생: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    main()
