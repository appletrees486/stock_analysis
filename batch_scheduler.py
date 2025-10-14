#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 스케줄러 (Batch Scheduler)
APScheduler를 사용한 자동 수집 작업 스케줄링
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
import threading
import time

from database_config import DatabaseManager
from collection_job_manager import CollectionJobManager

# 로깅 설정
logger = logging.getLogger(__name__)

class BatchScheduler:
    """배치 스케줄러 - 자동 수집 작업 관리"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        self.job_manager = CollectionJobManager()
        self.scheduler = None
        self.is_running = False
        self._lock = threading.Lock()
        
        # APScheduler 설정
        self.jobstores = {
            'default': MemoryJobStore()
        }
        self.executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }
        self.job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5분
        }
    
    def start(self):
        """스케줄러 시작"""
        try:
            with self._lock:
                if self.is_running:
                    logger.warning("스케줄러가 이미 실행 중입니다.")
                    return True
                
                # APScheduler 초기화
                self.scheduler = BackgroundScheduler(
                    jobstores=self.jobstores,
                    executors=self.executors,
                    job_defaults=self.job_defaults,
                    timezone='Asia/Seoul'
                )
                
                # DB에서 활성 스케줄 로드
                self._load_schedules_from_db()
                
                # 스케줄러 시작
                self.scheduler.start()
                self.is_running = True
                
                logger.info("✅ 배치 스케줄러 시작 완료")
                return True
                
        except Exception as e:
            logger.error(f"스케줄러 시작 실패: {e}")
            return False
    
    def stop(self):
        """스케줄러 중지"""
        try:
            with self._lock:
                if not self.is_running:
                    logger.warning("스케줄러가 실행 중이 아닙니다.")
                    return True
                
                if self.scheduler:
                    self.scheduler.shutdown(wait=False)
                    self.scheduler = None
                
                self.is_running = False
                logger.info("✅ 배치 스케줄러 중지 완료")
                return True
                
        except Exception as e:
            logger.error(f"스케줄러 중지 실패: {e}")
            return False
    
    def _load_schedules_from_db(self):
        """DB에서 활성 스케줄 로드"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return
            
            query = """
            SELECT id, schedule_name, job_type, cron_expression, job_config
            FROM batch_schedules 
            WHERE is_active = TRUE
            """
            
            schedules = self.db.fetch_all(query)
            
            if not schedules:
                logger.info("활성 스케줄이 없습니다.")
                return
            
            for schedule in schedules:
                try:
                    # 크론 표현식 파싱
                    cron_parts = schedule['cron_expression'].split()
                    if len(cron_parts) != 5:
                        logger.error(f"잘못된 크론 표현식: {schedule['cron_expression']}")
                        continue
                    
                    minute, hour, day, month, day_of_week = cron_parts
                    
                    # APScheduler 작업 추가
                    job_id = f"schedule_{schedule['id']}"
                    
                    self.scheduler.add_job(
                        func=self._execute_scheduled_job,
                        trigger=CronTrigger(
                            minute=minute,
                            hour=hour,
                            day=day,
                            month=month,
                            day_of_week=day_of_week
                        ),
                        id=job_id,
                        name=schedule['schedule_name'],
                        args=[schedule['id']],
                        replace_existing=True
                    )
                    
                    logger.info(f"✅ 스케줄 로드: {schedule['schedule_name']} ({schedule['cron_expression']})")
                    
                except Exception as e:
                    logger.error(f"스케줄 로드 실패: {schedule['schedule_name']} - {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"스케줄 로드 중 오류: {e}")
        finally:
            self.db.disconnect()
    
    def _execute_scheduled_job(self, schedule_id: int):
        """스케줄된 작업 실행"""
        try:
            logger.info(f"🚀 스케줄 작업 실행 시작: Schedule ID={schedule_id}")
            
            # 스케줄 정보 조회
            schedule_info = self._get_schedule_info(schedule_id)
            if not schedule_info:
                logger.error(f"스케줄 정보를 찾을 수 없습니다: Schedule ID={schedule_id}")
                return
            
            job_type = schedule_info['job_type']
            job_config = schedule_info.get('job_config', {})
            
            # 이미 실행 중인 동일한 작업이 있는지 확인
            running_job = self.job_manager.get_running_job(job_type)
            if running_job:
                logger.warning(f"이미 실행 중인 {job_type} 작업이 있습니다. 스케줄 실행 건너뜀")
                return
            
            # 새로운 작업 생성 및 시작
            job_id = self.job_manager.create_job(job_type, 'SCHEDULED', job_config)
            
            if not job_id:
                logger.error(f"스케줄 작업 생성 실패: {job_type}")
                return
            
            if not self.job_manager.start_job(job_id):
                logger.error(f"스케줄 작업 시작 실패: Job ID={job_id}")
                return
            
            # 스케줄 테이블의 last_run, last_job_id 업데이트
            self._update_schedule_last_run(schedule_id, job_id)
            
            # 실제 수집 작업 실행
            if job_type == 'DAILY_COLLECTION':
                self._run_daily_collection(job_id, job_config)
            elif job_type == 'BATCH_ANALYSIS':
                self._run_batch_analysis(job_id, job_config)
            elif job_type == 'DATA_VALIDATION':
                self._run_data_validation(job_id, job_config)
            else:
                logger.error(f"알 수 없는 작업 유형: {job_type}")
                self.job_manager.complete_job(job_id, False, f"알 수 없는 작업 유형: {job_type}")
            
        except Exception as e:
            logger.error(f"스케줄 작업 실행 중 오류: {e}")
            if 'job_id' in locals():
                self.job_manager.complete_job(job_id, False, str(e))
    
    def _get_schedule_info(self, schedule_id: int) -> Optional[Dict]:
        """스케줄 정보 조회"""
        try:
            if not self.db.connect():
                return None
            
            query = """
            SELECT id, schedule_name, job_type, cron_expression, job_config
            FROM batch_schedules 
            WHERE id = %s AND is_active = TRUE
            """
            
            result = self.db.fetch_one(query, (schedule_id,))
            
            if result:
                job_config = {}
                if result.get('job_config'):
                    try:
                        job_config = json.loads(result['job_config'])
                    except:
                        job_config = {}
                
                return {
                    'id': result['id'],
                    'schedule_name': result['schedule_name'],
                    'job_type': result['job_type'],
                    'cron_expression': result['cron_expression'],
                    'job_config': job_config
                }
            
            return None
            
        except Exception as e:
            logger.error(f"스케줄 정보 조회 실패: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def _update_schedule_last_run(self, schedule_id: int, job_id: int):
        """스케줄 마지막 실행 정보 업데이트"""
        try:
            if not self.db.connect():
                return
            
            update_query = """
            UPDATE batch_schedules 
            SET last_run = %s, last_job_id = %s, updated_at = %s
            WHERE id = %s
            """
            
            params = (datetime.now(), job_id, datetime.now(), schedule_id)
            
            if self.db.execute_query(update_query, params):
                logger.info(f"스케줄 마지막 실행 정보 업데이트: Schedule ID={schedule_id}, Job ID={job_id}")
            
        except Exception as e:
            logger.error(f"스케줄 마지막 실행 정보 업데이트 실패: {e}")
        finally:
            self.db.disconnect()
    
    def _update_collection_completed_flag(self, job_id: int):
        """수집 완료 플래그 업데이트 (자동 분석 트리거용)"""
        try:
            if not self.db.connect():
                logger.error("DB 연결 실패")
                return
            
            # job_id로 스케줄 찾기
            find_schedule_query = """
            SELECT id FROM batch_schedules 
            WHERE last_job_id = %s 
            AND is_active = TRUE
            AND job_type = 'DAILY_COLLECTION'
            ORDER BY id DESC
            LIMIT 1
            """
            
            schedule = self.db.fetch_one(find_schedule_query, (job_id,))
            
            if not schedule:
                logger.warning(f"Job ID {job_id}에 해당하는 활성 스케줄을 찾을 수 없습니다.")
                return
            
            schedule_id = schedule['id']
            
            # 수집 완료 플래그 업데이트
            update_query = """
            UPDATE batch_schedules 
            SET collection_completed = TRUE, 
                collection_completed_at = %s,
                updated_at = %s
            WHERE id = %s
            """
            
            params = (datetime.now(), datetime.now(), schedule_id)
            
            if self.db.execute_query(update_query, params):
                logger.info(f"✅ 수집 완료 플래그 업데이트: Schedule ID={schedule_id}, Job ID={job_id}")
                logger.info(f"   → auto_analysis_trigger가 랭킹 추출을 시작합니다.")
            else:
                logger.error(f"수집 완료 플래그 업데이트 실패: Schedule ID={schedule_id}")
            
        except Exception as e:
            logger.error(f"수집 완료 플래그 업데이트 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.db.disconnect()
    
    def _run_daily_collection(self, job_id: int, job_config: Dict):
        """일일 시세 수집 실행"""
        try:
            logger.info(f"📊 일일 시세 수집 시작: Job ID={job_id}")
            
            # StockDataCollector 임포트 및 실행
            from stock_data_collector import StockDataCollector
            
            collector = StockDataCollector()
            
            # 진행률 및 통계 콜백 설정
            def progress_callback(total, processed, current_batch, total_batches):
                self.job_manager.update_progress(job_id, total, processed, current_batch, total_batches)
            
            def stats_callback(success_count, failed_count, skipped_count=0):
                self.job_manager.update_stats(job_id, success_count, failed_count, skipped_count)
            
            collector.set_progress_callback(progress_callback)
            collector.set_stats_callback(stats_callback)
            
            # 배치 크기 및 워커 수 설정
            batch_size = job_config.get('batch_size', 100)
            max_workers = job_config.get('max_workers', 5)
            
            if hasattr(collector, 'batch_size'):
                collector.batch_size = batch_size
            if hasattr(collector, 'max_workers'):
                collector.max_workers = max_workers
            
            # 전체 종목 수집 실행
            success_count, failed_count = collector.collect_all_stocks()
            
            # 작업 완료 처리
            if success_count > 0:
                self.job_manager.complete_job(job_id, True)
                logger.info(f"✅ 일일 시세 수집 완료: Job ID={job_id}, 성공={success_count}, 실패={failed_count}")
                
                # 수집 완료 플래그 업데이트 (자동 분석 트리거용)
                self._update_collection_completed_flag(job_id)
                
            else:
                self.job_manager.complete_job(job_id, False, "모든 종목 수집 실패")
                logger.error(f"❌ 일일 시세 수집 실패: Job ID={job_id}")
            
        except Exception as e:
            logger.error(f"일일 시세 수집 실행 중 오류: {e}")
            self.job_manager.complete_job(job_id, False, str(e))
    
    def _run_batch_analysis(self, job_id: int, job_config: Dict):
        """배치 분석 실행 (향후 확장용)"""
        try:
            logger.info(f"📈 배치 분석 시작: Job ID={job_id}")
            
            # 향후 배치 분석 로직 구현
            time.sleep(5)  # 임시 처리
            
            self.job_manager.complete_job(job_id, True)
            logger.info(f"✅ 배치 분석 완료: Job ID={job_id}")
            
        except Exception as e:
            logger.error(f"배치 분석 실행 중 오류: {e}")
            self.job_manager.complete_job(job_id, False, str(e))
    
    def _run_data_validation(self, job_id: int, job_config: Dict):
        """데이터 검증 실행 (향후 확장용)"""
        try:
            logger.info(f"🔍 데이터 검증 시작: Job ID={job_id}")
            
            # 향후 데이터 검증 로직 구현
            time.sleep(3)  # 임시 처리
            
            self.job_manager.complete_job(job_id, True)
            logger.info(f"✅ 데이터 검증 완료: Job ID={job_id}")
            
        except Exception as e:
            logger.error(f"데이터 검증 실행 중 오류: {e}")
            self.job_manager.complete_job(job_id, False, str(e))
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """현재 스케줄된 작업 목록 조회"""
        try:
            if not self.is_running or not self.scheduler:
                return []
            
            jobs = []
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': next_run.isoformat() if next_run else None,
                    'trigger': str(job.trigger)
                })
            
            return jobs
            
        except Exception as e:
            logger.error(f"스케줄된 작업 목록 조회 실패: {e}")
            return []
    
    def reload_schedules(self):
        """스케줄 재로드"""
        try:
            if not self.is_running or not self.scheduler:
                logger.warning("스케줄러가 실행 중이 아닙니다.")
                return False
            
            # 기존 작업 제거
            self.scheduler.remove_all_jobs()
            
            # 새로운 스케줄 로드
            self._load_schedules_from_db()
            
            logger.info("✅ 스케줄 재로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"스케줄 재로드 실패: {e}")
            return False

# 전역 스케줄러 인스턴스
_scheduler_instance = None
_scheduler_lock = threading.Lock()

def get_scheduler() -> BatchScheduler:
    """전역 스케줄러 인스턴스 반환 (싱글톤)"""
    global _scheduler_instance
    
    with _scheduler_lock:
        if _scheduler_instance is None:
            _scheduler_instance = BatchScheduler()
        
        return _scheduler_instance

def start_scheduler():
    """스케줄러 시작"""
    scheduler = get_scheduler()
    return scheduler.start()

def stop_scheduler():
    """스케줄러 중지"""
    scheduler = get_scheduler()
    return scheduler.stop()
