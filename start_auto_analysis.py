#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 분석 시작 스크립트
"""

import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import DatabaseManager
from ranking_data_extractor import RankingDataExtractor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """자동 분석 시작"""
    db = DatabaseManager()
    ranking_extractor = RankingDataExtractor()
    
    try:
        if not db.connect():
            logger.error("[ERROR] DB 연결 실패")
            return False
        
        # 최신 활성 스케줄 확인
        query = """
        SELECT id, schedule_name
        FROM batch_schedules 
        WHERE is_active = TRUE 
        AND job_type = 'DAILY_COLLECTION'
        ORDER BY id DESC
        LIMIT 1
        """
        
        schedule = db.fetch_one(query)
        
        if not schedule:
            logger.error("[ERROR] 활성 스케줄이 없습니다.")
            return False
        
        schedule_id = schedule['id']
        schedule_name = schedule['schedule_name']
        
        logger.info(f"[스케줄] ID={schedule_id}, 이름={schedule_name}")
        
        # 오늘 날짜로 랭킹 추출
        today = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        batch_id = f"schedule_{schedule_id}_{timestamp}"
        
        logger.info(f"[랭킹 추출 시작] 날짜={today}, 배치ID={batch_id}")
        
        # 랭킹 추출 실행
        result = ranking_extractor.extract_rankings_for_auto_analysis(
            target_date=today, 
            batch_id=batch_id
        )
        
        if result.get('success'):
            logger.info("[OK] 랭킹 추출 완료!")
            logger.info(f"  - 거래율 파일: {result.get('turnover_file')}")
            logger.info(f"  - 거래대금 파일: {result.get('volume_file')}")
            logger.info(f"  - 거래율 종목 수: {result.get('turnover_count')}")
            logger.info(f"  - 거래대금 종목 수: {result.get('volume_count')}")
            
            # DB에 작업 기록
            insert_query = """
            INSERT INTO auto_analysis_jobs 
            (job_type, job_status, trading_type, target_date, stock_list_path, batch_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            # 거래율 작업 기록
            db.execute_query(insert_query, (
                'ranking_extraction',
                'completed',
                '거래율',
                today,
                result.get('turnover_file'),
                batch_id
            ))
            
            # 거래대금 작업 기록
            db.execute_query(insert_query, (
                'ranking_extraction',
                'completed',
                '거래대금',
                today,
                result.get('volume_file'),
                batch_id
            ))
            
            # 스케줄 플래그 업데이트
            update_query = """
            UPDATE batch_schedules 
            SET ranking_extracted = TRUE, ranking_extracted_at = %s
            WHERE id = %s
            """
            db.execute_query(update_query, (datetime.now(), schedule_id))
            
            logger.info("[OK] 스케줄 플래그 업데이트 완료!")
            logger.info("\n[다음 단계]")
            logger.info("  대량 분석을 시작하려면:")
            logger.info("  python start_batch_analysis.py")
            
            return True
        else:
            logger.error(f"[ERROR] 랭킹 추출 실패: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        db.disconnect()

if __name__ == "__main__":
    success = main()
    if success:
        print("\n[SUCCESS] 자동 분석 시작 완료!")
    else:
        print("\n[ERROR] 자동 분석 시작 실패")

