#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 실행 중인 수집 작업 중단 및 재시작
"""

from database_config import DatabaseManager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def stop_and_restart_collection():
    """현재 실행 중인 수집 작업 중단 및 재시작"""
    db = DatabaseManager()
    
    try:
        if not db.connect():
            logging.error("❌ 데이터베이스 연결 실패")
            return
        
        # 1. 현재 실행 중인 작업 확인
        query_running = """
        SELECT id, job_type, status, progress_processed, progress_total
        FROM collection_jobs
        WHERE status = 'RUNNING' AND job_type = 'DAILY_COLLECTION'
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        running_job = db.fetch_one(query_running)
        
        if running_job:
            job_id = running_job['id']
            logging.info(f"🔄 실행 중인 작업 발견: ID {job_id}")
            logging.info(f"   진행률: {running_job['progress_processed']}/{running_job['progress_total']}")
            
            # 2. 작업 중단
            update_query = """
            UPDATE collection_jobs 
            SET status = 'CANCELLED', 
                end_time = NOW(),
                error_message = '사용자에 의해 중단됨 (코드 수정 후 재시작)'
            WHERE id = %s
            """
            
            if db.execute_query(update_query, (job_id,)):
                logging.info(f"✅ 작업 {job_id} 중단 완료")
            else:
                logging.error(f"❌ 작업 {job_id} 중단 실패")
        else:
            logging.info("ℹ️ 실행 중인 작업이 없습니다")
        
        # 3. 새로운 수집 작업 시작
        logging.info("🚀 새로운 수집 작업 시작...")
        
        from stock_data_collector import StockDataCollector
        collector = StockDataCollector()
        
        # 수집 작업 시작
        success_count, failed_count = collector.collect_all_stocks()
        
        logging.info(f"🎉 수집 완료!")
        logging.info(f"✅ 성공: {success_count}개")
        logging.info(f"❌ 실패: {failed_count}개")
        
    except Exception as e:
        logging.error(f"❌ 오류 발생: {e}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        db.disconnect()

if __name__ == "__main__":
    stop_and_restart_collection()

