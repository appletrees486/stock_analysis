#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 분석 시스템 DB 테이블 생성 스크립트
"""

import logging
from database_config import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_auto_analysis_tables():
    """자동 분석 시스템을 위한 DB 테이블 생성"""
    db = DatabaseManager()
    
    try:
        if not db.connect():
            logging.error("❌ 데이터베이스 연결 실패")
            return False
        
        logging.info("🔧 자동 분석 시스템 DB 테이블 생성 시작...")
        
        # 1. batch_schedules 테이블에 컬럼 추가
        logging.info("batch_schedules 테이블 수정 중...")
        
        # 컬럼 존재 여부 확인 후 추가
        columns_to_add = [
            ('collection_completed', 'BOOLEAN DEFAULT FALSE'),
            ('collection_completed_at', 'DATETIME NULL'),
            ('ranking_extracted', 'BOOLEAN DEFAULT FALSE'),
            ('ranking_extracted_at', 'DATETIME NULL'),
            ('analysis_started', 'BOOLEAN DEFAULT FALSE'),
            ('analysis_started_at', 'DATETIME NULL')
        ]
        
        # 기존 컬럼 확인
        check_column_query = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'batch_schedules'
        """
        existing_columns = [row['COLUMN_NAME'] for row in db.fetch_all(check_column_query)]
        
        for col_name, col_def in columns_to_add:
            if col_name in existing_columns:
                logging.info(f"컬럼 {col_name}이 이미 존재합니다. 건너뜀")
            else:
                try:
                    query = f"ALTER TABLE batch_schedules ADD COLUMN {col_name} {col_def}"
                    db.execute_query(query)
                    logging.info(f"컬럼 {col_name} 추가 성공")
                except Exception as e:
                    logging.warning(f"컬럼 {col_name} 추가 중 오류: {e}")
        
        # 2. auto_analysis_jobs 테이블 생성
        logging.info("📊 auto_analysis_jobs 테이블 생성 중...")
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS auto_analysis_jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_type VARCHAR(50) NOT NULL COMMENT '작업 유형: ranking_extraction, analysis',
            job_status VARCHAR(20) NOT NULL COMMENT '작업 상태: pending, running, completed, failed',
            trading_type VARCHAR(20) COMMENT '거래 타입: 거래율, 거래대금',
            target_date DATE NOT NULL COMMENT '대상 날짜',
            stock_list_path VARCHAR(500) COMMENT '종목 리스트 파일 경로',
            batch_id VARCHAR(100) COMMENT '배치 ID',
            error_message TEXT COMMENT '에러 메시지',
            retry_count INT DEFAULT 0 COMMENT '재시도 횟수',
            max_retries INT DEFAULT 3 COMMENT '최대 재시도 횟수',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정 시간',
            INDEX idx_status (job_status),
            INDEX idx_date (target_date),
            INDEX idx_job_type (job_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='자동 분석 작업 상태 관리 테이블'
        """
        
        db.execute_query(create_table_query)
        logging.info("✅ auto_analysis_jobs 테이블 생성 완료")
        
        # 3. 테이블 확인
        logging.info("🔍 생성된 테이블 확인 중...")
        
        check_query = """
        SELECT 
            COLUMN_NAME, 
            DATA_TYPE, 
            COLUMN_COMMENT 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'auto_analysis_jobs'
        ORDER BY ORDINAL_POSITION
        """
        
        columns = db.fetch_all(check_query)
        if columns:
            logging.info("📋 auto_analysis_jobs 테이블 컬럼:")
            for col in columns:
                logging.info(f"   - {col['COLUMN_NAME']}: {col['DATA_TYPE']} ({col['COLUMN_COMMENT']})")
        
        logging.info("자동 분석 시스템 DB 테이블 생성 완료!")
        return True
        
    except Exception as e:
        logging.error(f"DB 테이블 생성 중 오류: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False
    finally:
        db.disconnect()

if __name__ == "__main__":
    success = create_auto_analysis_tables()
    if success:
        print("\n[SUCCESS] DB 테이블 생성이 완료되었습니다!")
        print("다음 단계로 진행하세요.")
    else:
        print("\n[ERROR] DB 테이블 생성에 실패했습니다.")
        print("로그를 확인해주세요.")

