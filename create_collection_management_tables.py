#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수집 작업 관리 및 배치 스케줄링을 위한 DB 테이블 생성
기존 데이터베이스 스키마에 추가하는 스크립트
"""

import logging
from database_config import DatabaseManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_collection_management_tables():
    """수집 작업 관리 및 배치 스케줄링 테이블 생성"""
    db = DatabaseManager()
    
    try:
        if not db.connect():
            logging.error("데이터베이스 연결 실패")
            return False
        
        logging.info("🚀 수집 작업 관리 테이블 생성 시작")
        
        # 1. 수집 작업 관리 테이블
        collection_jobs_table = """
        CREATE TABLE IF NOT EXISTS collection_jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_type ENUM('DAILY_COLLECTION', 'BATCH_ANALYSIS', 'DATA_VALIDATION') NOT NULL,
            status ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED') DEFAULT 'PENDING',
            trigger_type ENUM('MANUAL', 'SCHEDULED', 'API') NOT NULL,
            start_time DATETIME,
            end_time DATETIME,
            progress_total INT DEFAULT 0,
            progress_processed INT DEFAULT 0,
            progress_current_batch INT DEFAULT 0,
            progress_total_batches INT DEFAULT 0,
            success_count INT DEFAULT 0,
            failed_count INT DEFAULT 0,
            skipped_count INT DEFAULT 0,
            error_message TEXT,
            job_config JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_status (status),
            INDEX idx_job_type (job_type),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        if db.execute_query(collection_jobs_table):
            logging.info("✅ collection_jobs 테이블 생성 완료")
        else:
            logging.error("❌ collection_jobs 테이블 생성 실패")
            return False
        
        # 2. 배치 스케줄 관리 테이블
        batch_schedules_table = """
        CREATE TABLE IF NOT EXISTS batch_schedules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            schedule_name VARCHAR(100) NOT NULL,
            job_type ENUM('DAILY_COLLECTION', 'BATCH_ANALYSIS', 'DATA_VALIDATION') NOT NULL,
            cron_expression VARCHAR(50) NOT NULL COMMENT '크론 표현식 (예: 0 16 * * 1-5)',
            is_active BOOLEAN DEFAULT TRUE,
            last_run DATETIME,
            next_run DATETIME,
            last_job_id INT,
            description TEXT,
            job_config JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_schedule_name (schedule_name),
            INDEX idx_is_active (is_active),
            INDEX idx_next_run (next_run),
            FOREIGN KEY (last_job_id) REFERENCES collection_jobs(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        if db.execute_query(batch_schedules_table):
            logging.info("✅ batch_schedules 테이블 생성 완료")
        else:
            logging.error("❌ batch_schedules 테이블 생성 실패")
            return False
        
        # 3. 기본 배치 스케줄 데이터 삽입
        default_schedules = [
            {
                'name': '일일 시세 수집 (평일 오후 4시)',
                'job_type': 'DAILY_COLLECTION',
                'cron': '0 16 * * 1-5',  # 평일 오후 4시
                'description': '평일 장 마감 후 전체 종목 일일 시세 데이터 수집',
                'config': '{"batch_size": 100, "max_workers": 5}'
            },
            {
                'name': '일일 시세 수집 (평일 오후 6시)',
                'job_type': 'DAILY_COLLECTION', 
                'cron': '0 18 * * 1-5',  # 평일 오후 6시
                'description': '평일 장 마감 후 전체 종목 일일 시세 데이터 수집 (백업)',
                'config': '{"batch_size": 100, "max_workers": 5}'
            }
        ]
        
        for schedule in default_schedules:
            insert_schedule = """
            INSERT IGNORE INTO batch_schedules 
            (schedule_name, job_type, cron_expression, description, job_config, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = (
                schedule['name'],
                schedule['job_type'],
                schedule['cron'],
                schedule['description'],
                schedule['config'],
                False  # 기본적으로 비활성화 상태로 생성
            )
            
            if db.execute_query(insert_schedule, params):
                logging.info(f"✅ 기본 스케줄 생성: {schedule['name']}")
            else:
                logging.warning(f"⚠️ 기본 스케줄 생성 실패 또는 이미 존재: {schedule['name']}")
        
        logging.info("🎉 수집 작업 관리 테이블 생성 완료")
        return True
        
    except Exception as e:
        logging.error(f"테이블 생성 중 오류: {e}")
        return False
    finally:
        db.disconnect()

def main():
    """메인 함수"""
    logging.info("🚀 수집 작업 관리 시스템 DB 스키마 생성 시작")
    
    if create_collection_management_tables():
        logging.info("✅ 모든 테이블 생성 완료")
        logging.info("💡 다음 단계:")
        logging.info("   1. 배치 스케줄러 구현")
        logging.info("   2. API 라우트 개선")
        logging.info("   3. 웹 UI 업데이트")
    else:
        logging.error("❌ 테이블 생성 실패")

if __name__ == "__main__":
    main()
