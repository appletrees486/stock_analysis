#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 분석 트리거 모듈
DB 플래그 폴링하여 랭킹 추출 → 분석 실행 오케스트레이션
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import DatabaseManager
from ranking_data_extractor import RankingDataExtractor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_analysis_trigger.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class AutoAnalysisTrigger:
    """자동 분석 트리거 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        self.ranking_extractor = RankingDataExtractor()
        self.polling_interval = 60  # 1분마다 폴링
        self.is_running = False
        
        # API 모듈 import (배치 분석 실행용)
        try:
            from api.batch_analyzer import BatchAnalyzer
            self.batch_analyzer = BatchAnalyzer()
        except ImportError as e:
            logger.error(f"BatchAnalyzer import 실패: {e}")
            self.batch_analyzer = None
    
    def start_polling(self):
        """폴링 시작 (무한 루프)"""
        self.is_running = True
        logger.info("자동 분석 트리거 시작 (1분마다 폴링)")
        
        try:
            while self.is_running:
                try:
                    self._check_and_process()
                except Exception as e:
                    logger.error(f"폴링 중 오류: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                # 1분 대기
                time.sleep(self.polling_interval)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단되었습니다.")
            self.stop_polling()
    
    def stop_polling(self):
        """폴링 중지"""
        self.is_running = False
        logger.info("자동 분석 트리거 중지")
    
    def _check_and_process(self):
        """DB 플래그 확인 및 처리"""
        try:
            if not self.db.connect():
                logger.error("DB 연결 실패")
                return
            
            # 활성 스케줄 확인 (일일 수집 완료 대기)
            query = """
            SELECT id, schedule_name, collection_completed, ranking_extracted, analysis_started
            FROM batch_schedules 
            WHERE is_active = TRUE 
            AND job_type = 'DAILY_COLLECTION'
            ORDER BY id DESC
            LIMIT 1
            """
            
            schedule = self.db.fetch_one(query)
            
            if not schedule:
                logger.debug("활성 스케줄 없음")
                return
            
            schedule_id = schedule['id']
            collection_completed = schedule.get('collection_completed', False)
            ranking_extracted = schedule.get('ranking_extracted', False)
            analysis_started = schedule.get('analysis_started', False)
            
            logger.debug(f"스케줄 {schedule_id} 상태: 수집={collection_completed}, 랭킹={ranking_extracted}, 분석={analysis_started}")
            
            # 1. 수집 완료 → 랭킹 추출
            if collection_completed and not ranking_extracted:
                logger.info(f"수집 완료 감지! 랭킹 추출 시작...")
                self._extract_rankings(schedule_id)
            
            # 2. 랭킹 추출 완료 → 분석 시작
            elif ranking_extracted and not analysis_started:
                logger.info(f"랭킹 추출 완료! 분석 시작...")
                self._start_analysis(schedule_id)
            
        except Exception as e:
            logger.error(f"폴링 처리 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.db.disconnect()
    
    def _extract_rankings(self, schedule_id: int):
        """
        랭킹 추출 실행
        
        Args:
            schedule_id (int): 스케줄 ID
        """
        try:
            logger.info(f"랭킹 추출 시작 (스케줄 {schedule_id})")
            
            # 오늘 날짜로 랭킹 추출
            today = datetime.now().strftime('%Y-%m-%d')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            # 배치 ID 생성 (스케줄 ID + 타임스탬프)
            batch_id = f"schedule_{schedule_id}_{timestamp}"
            
            # 랭킹 추출 실행
            result = self.ranking_extractor.extract_rankings_for_auto_analysis(
                target_date=today, 
                batch_id=batch_id
            )
            
            if result.get('success'):
                # DB에 작업 기록
                self._record_job(
                    job_type='ranking_extraction',
                    job_status='completed',
                    trading_type=None,
                    target_date=today,
                    stock_list_path=None,
                    batch_id=None,
                    error_message=None
                )
                
                # 스케줄 플래그 업데이트
                self._update_schedule_flag(schedule_id, 'ranking_extracted', True)
                
                logger.info(f"랭킹 추출 완료!")
                logger.info(f"  - 거래율 파일: {result.get('turnover_file')}")
                logger.info(f"  - 거래대금 파일: {result.get('volume_file')}")
            else:
                # 실패 시 재시도 큐에 추가
                self._record_job(
                    job_type='ranking_extraction',
                    job_status='failed',
                    trading_type=None,
                    target_date=today,
                    stock_list_path=None,
                    batch_id=None,
                    error_message=result.get('error')
                )
                logger.error(f"랭킹 추출 실패: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"랭킹 추출 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _start_analysis(self, schedule_id: int):
        """
        대량 분석 시작
        
        Args:
            schedule_id (int): 스케줄 ID
        """
        try:
            logger.info(f"대량 분석 시작 (스케줄 {schedule_id})")
            
            if not self.batch_analyzer:
                logger.error("BatchAnalyzer를 사용할 수 없습니다.")
                return
            
            # DB에서 최근 랭킹 추출 작업 조회 (파일 경로 가져오기)
            if not self.db.connect():
                logger.error("DB 연결 실패")
                return
            
            query = """
            SELECT stock_list_path, batch_id, trading_type
            FROM auto_analysis_jobs 
            WHERE job_type = 'ranking_extraction' 
            AND job_status = 'completed'
            AND target_date = %s
            ORDER BY created_at DESC
            LIMIT 2
            """
            
            today = datetime.now().strftime('%Y-%m-%d')
            jobs = self.db.fetch_all(query, (today,))
            
            if not jobs or len(jobs) < 2:
                logger.error("랭킹 추출 작업을 찾을 수 없습니다.")
                return
            
            # 거래율/거래대금 파일 찾기
            turnover_file = None
            volume_file = None
            
            for job in jobs:
                trading_type = job.get('trading_type')
                if trading_type == '거래율':
                    turnover_file = job.get('stock_list_path')
                elif trading_type == '거래대금':
                    volume_file = job.get('stock_list_path')
            
            # 파일 존재 확인
            if not turnover_file or not os.path.exists(turnover_file):
                logger.error(f"거래율 파일을 찾을 수 없습니다: {turnover_file}")
                return
            
            if not volume_file or not os.path.exists(volume_file):
                logger.error(f"거래대금 파일을 찾을 수 없습니다: {volume_file}")
                return
            
            # 1. 거래율 분석 시작
            logger.info("거래율 상위 50위 분석 시작...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            turnover_batch_id = f"auto_turnover_{timestamp}"
            
            self._record_job(
                job_type='analysis',
                job_status='running',
                trading_type='거래율',
                target_date=datetime.now().strftime('%Y-%m-%d'),
                stock_list_path=turnover_file,
                batch_id=turnover_batch_id,
                error_message=None
            )
            
            # 배치 분석 실행 (동기 방식)
            self.batch_analyzer.start_batch_analysis(
                stock_list_path=turnover_file,
                chart_type='일봉',
                batch_id=turnover_batch_id,
                trading_type='거래율',
                email_enabled=False,
                email_address=''
            )
            
            # 분석 완료 후 파일 삭제
            self._cleanup_files([turnover_file])
            
            # 2. 거래대금 분석 시작
            logger.info("거래대금 상위 50위 분석 시작...")
            volume_batch_id = f"auto_volume_{today}_{timestamp}"
            
            self._record_job(
                job_type='analysis',
                job_status='running',
                trading_type='거래대금',
                target_date=datetime.now().strftime('%Y-%m-%d'),
                stock_list_path=volume_file,
                batch_id=volume_batch_id,
                error_message=None
            )
            
            # 배치 분석 실행 (동기 방식)
            self.batch_analyzer.start_batch_analysis(
                stock_list_path=volume_file,
                chart_type='일봉',
                batch_id=volume_batch_id,
                trading_type='거래대금',
                email_enabled=False,
                email_address=''
            )
            
            # 분석 완료 후 파일 삭제
            self._cleanup_files([volume_file])
            
            # 스케줄 플래그 업데이트
            self._update_schedule_flag(schedule_id, 'analysis_started', True)
            
            logger.info("대량 분석 완료!")
            
        except Exception as e:
            logger.error(f"대량 분석 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _record_job(self, job_type: str, job_status: str, trading_type: Optional[str], 
                   target_date: str, stock_list_path: Optional[str], 
                   batch_id: Optional[str], error_message: Optional[str]):
        """
        작업 기록 (auto_analysis_jobs 테이블)
        
        Args:
            job_type (str): 작업 유형
            job_status (str): 작업 상태
            trading_type (str): 거래 타입
            target_date (str): 대상 날짜
            stock_list_path (str): 파일 경로
            batch_id (str): 배치 ID
            error_message (str): 에러 메시지
        """
        try:
            if not self.db.connect():
                return
            
            insert_query = """
            INSERT INTO auto_analysis_jobs 
            (job_type, job_status, trading_type, target_date, stock_list_path, batch_id, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                job_type,
                job_status,
                trading_type,
                target_date,
                stock_list_path,
                batch_id,
                error_message
            )
            
            self.db.execute_query(insert_query, params)
            logger.info(f"작업 기록 완료: {job_type} - {job_status}")
            
        except Exception as e:
            logger.error(f"작업 기록 중 오류: {e}")
        finally:
            self.db.disconnect()
    
    def _update_schedule_flag(self, schedule_id: int, flag_name: str, value: bool):
        """
        스케줄 플래그 업데이트
        
        Args:
            schedule_id (int): 스케줄 ID
            flag_name (str): 플래그 이름
            value (bool): 플래그 값
        """
        try:
            if not self.db.connect():
                return
            
            # 플래그 이름에 따라 컬럼 선택
            flag_column = flag_name
            timestamp_column = f"{flag_name}_at"
            
            update_query = f"""
            UPDATE batch_schedules 
            SET {flag_column} = %s, {timestamp_column} = %s
            WHERE id = %s
            """
            
            params = (value, datetime.now(), schedule_id)
            
            self.db.execute_query(update_query, params)
            logger.info(f"스케줄 {schedule_id} 플래그 업데이트: {flag_name} = {value}")
            
        except Exception as e:
            logger.error(f"플래그 업데이트 중 오류: {e}")
        finally:
            self.db.disconnect()
    
    def _cleanup_files(self, file_paths: list):
        """
        파일 정리 (분석 완료 후 삭제)
        
        Args:
            file_paths (list): 삭제할 파일 경로 리스트
        """
        try:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"파일 삭제 완료: {file_path}")
                else:
                    logger.warning(f"파일이 존재하지 않습니다: {file_path}")
                    
        except Exception as e:
            logger.error(f"파일 정리 중 오류: {e}")
    
    def cleanup_old_files(self, days: int = 7):
        """
        오래된 파일 정리 (7일 이상 된 파일)
        
        Args:
            days (int): 보관 기간 (일)
        """
        try:
            upload_dir = "uploads/stock_lists"
            if not os.path.exists(upload_dir):
                return
            
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            deleted_count = 0
            
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                
                if os.path.isfile(file_path):
                    # 파일 수정 시간 확인
                    file_mtime = os.path.getmtime(file_path)
                    
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"오래된 파일 삭제: {filename}")
            
            if deleted_count > 0:
                logger.info(f"총 {deleted_count}개의 오래된 파일 삭제 완료")
                
        except Exception as e:
            logger.error(f"오래된 파일 정리 중 오류: {e}")


def main():
    """메인 함수 - 폴링 시작"""
    logger.info("자동 분석 트리거 시작")
    
    trigger = AutoAnalysisTrigger()
    
    try:
        # 오래된 파일 정리 (7일 이상)
        trigger.cleanup_old_files(days=7)
        
        # 폴링 시작
        trigger.start_polling()
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        trigger.stop_polling()


if __name__ == "__main__":
    main()

