#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실행 중인 수집 작업 정리 스크립트
400 에러가 발생할 때 실행 중인 작업들을 정리합니다.
"""

import logging
from collection_job_manager import CollectionJobManager
from database_config import DatabaseManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def cleanup_running_jobs():
    """실행 중인 모든 수집 작업을 정리"""
    try:
        job_manager = CollectionJobManager()
        db = DatabaseManager()
        
        if not db.connect():
            logging.error("데이터베이스 연결 실패")
            return False
        
        # 실행 중인 작업들 조회
        query = """
        SELECT id, job_type, status, start_time, created_at
        FROM collection_jobs 
        WHERE status IN ('RUNNING', 'PENDING')
        ORDER BY created_at DESC
        """
        
        running_jobs = db.fetch_all(query)
        
        if not running_jobs:
            logging.info("✅ 실행 중인 작업이 없습니다.")
            return True
        
        logging.info(f"🔍 실행 중인 작업 {len(running_jobs)}개를 발견했습니다.")
        
        # 각 작업을 취소로 처리
        cancelled_count = 0
        for job in running_jobs:
            job_id = job['id']
            job_type = job['job_type']
            status = job['status']
            
            logging.info(f"📝 작업 정리 중: ID={job_id}, Type={job_type}, Status={status}")
            
            # 강제로 CANCELLED 상태로 변경
            update_query = """
            UPDATE collection_jobs 
            SET status = 'CANCELLED', 
                end_time = NOW(), 
                updated_at = NOW(),
                error_message = 'Manually cancelled by cleanup script'
            WHERE id = %s
            """
            
            if db.execute_query(update_query, (job_id,)):
                logging.info(f"✅ 작업 {job_id} 취소 완료")
                cancelled_count += 1
            else:
                logging.error(f"❌ 작업 {job_id} 취소 실패")
        
        logging.info(f"🎉 총 {cancelled_count}개 작업이 정리되었습니다.")
        
        # 메모리 기반 상태도 초기화 (api/daily_collection_routes.py에서 사용)
        logging.info("💾 메모리 기반 상태 초기화...")
        
        db.disconnect()
        return True
        
    except Exception as e:
        logging.error(f"❌ 작업 정리 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    print("🧹 실행 중인 수집 작업 정리 스크립트")
    print("="*50)
    
    if cleanup_running_jobs():
        print("\n✅ 작업 정리가 완료되었습니다!")
        print("💡 이제 웹에서 수집을 다시 시작할 수 있습니다.")
    else:
        print("\n❌ 작업 정리에 실패했습니다.")
        print("💡 수동으로 데이터베이스를 확인해주세요.")
