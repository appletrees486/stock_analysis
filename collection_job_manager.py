#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수집 작업 관리자 (Collection Job Manager)
DB 기반 상태 관리 및 진행률 추적을 담당
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from database_config import DatabaseManager

# 로깅 설정
logger = logging.getLogger(__name__)

class CollectionJobManager:
    """수집 작업 관리자 - DB 기반 상태 관리"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
    
    def create_job(self, job_type: str, trigger_type: str = 'MANUAL', job_config: Dict = None) -> Optional[int]:
        """새로운 수집 작업 생성"""
        db = DatabaseManager()  # 독립적인 DB 연결 사용
        try:
            if not db.connect():
                logger.error("데이터베이스 연결 실패")
                return None
            
            # 이미 실행 중인 동일한 작업이 있는지 확인 (독립적인 쿼리)
            check_query = """
            SELECT id FROM collection_jobs 
            WHERE job_type = %s AND status = 'RUNNING'
            ORDER BY start_time DESC LIMIT 1
            """
            existing_job = db.fetch_one(check_query, (job_type,))
            
            if existing_job:
                logger.warning(f"이미 실행 중인 {job_type} 작업이 있습니다. (Job ID: {existing_job['id']})")
                return None
            
            insert_query = """
            INSERT INTO collection_jobs 
            (job_type, trigger_type, status, job_config, created_at)
            VALUES (%s, %s, 'PENDING', %s, %s)
            """
            
            config_json = json.dumps(job_config) if job_config else None
            params = (job_type, trigger_type, config_json, datetime.now())
            
            if db.execute_query(insert_query, params):
                # 생성된 작업 ID 조회
                job_id = db.get_last_insert_id()
                if job_id:
                    logger.info(f"✅ 새로운 수집 작업 생성: ID={job_id}, Type={job_type}, Trigger={trigger_type}")
                    return job_id
                else:
                    logger.error("작업 ID 조회 실패")
                    return None
            else:
                logger.error("수집 작업 생성 실패")
                return None
                
        except Exception as e:
            logger.error(f"수집 작업 생성 중 오류: {e}")
            return None
        finally:
            db.disconnect()
    
    def start_job(self, job_id: int) -> bool:
        """작업 시작"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return False
            
            update_query = """
            UPDATE collection_jobs 
            SET status = 'RUNNING', start_time = %s, updated_at = %s
            WHERE id = %s AND status = 'PENDING'
            """
            
            params = (datetime.now(), datetime.now(), job_id)
            
            if self.db.execute_query(update_query, params):
                logger.info(f"✅ 작업 시작: Job ID={job_id}")
                return True
            else:
                logger.error(f"작업 시작 실패: Job ID={job_id}")
                return False
                
        except Exception as e:
            logger.error(f"작업 시작 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def update_progress(self, job_id: int, total: int, processed: int, 
                       current_batch: int = 0, total_batches: int = 0) -> bool:
        """진행률 업데이트"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return False
            
            update_query = """
            UPDATE collection_jobs 
            SET progress_total = %s, progress_processed = %s, 
                progress_current_batch = %s, progress_total_batches = %s,
                updated_at = %s
            WHERE id = %s AND status = 'RUNNING'
            """
            
            params = (total, processed, current_batch, total_batches, datetime.now(), job_id)
            
            result = self.db.execute_query(update_query, params)
            if result:
                logger.debug(f"진행률 업데이트: Job ID={job_id}, {processed}/{total}")
            
            return result
                
        except Exception as e:
            logger.error(f"진행률 업데이트 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def update_stats(self, job_id: int, success_count: int, failed_count: int, skipped_count: int = 0) -> bool:
        """통계 업데이트"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return False
            
            update_query = """
            UPDATE collection_jobs 
            SET success_count = %s, failed_count = %s, skipped_count = %s, updated_at = %s
            WHERE id = %s AND status = 'RUNNING'
            """
            
            params = (success_count, failed_count, skipped_count, datetime.now(), job_id)
            
            result = self.db.execute_query(update_query, params)
            if result:
                logger.debug(f"통계 업데이트: Job ID={job_id}, 성공={success_count}, 실패={failed_count}, 건너뜀={skipped_count}")
            
            return result
                
        except Exception as e:
            logger.error(f"통계 업데이트 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def complete_job(self, job_id: int, success: bool = True, error_message: str = None) -> bool:
        """작업 완료"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return False
            
            status = 'COMPLETED' if success else 'FAILED'
            
            update_query = """
            UPDATE collection_jobs 
            SET status = %s, end_time = %s, error_message = %s, updated_at = %s
            WHERE id = %s AND status = 'RUNNING'
            """
            
            params = (status, datetime.now(), error_message, datetime.now(), job_id)
            
            if self.db.execute_query(update_query, params):
                logger.info(f"✅ 작업 완료: Job ID={job_id}, Status={status}")
                return True
            else:
                logger.error(f"작업 완료 처리 실패: Job ID={job_id}")
                return False
                
        except Exception as e:
            logger.error(f"작업 완료 처리 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def cancel_job(self, job_id: int) -> bool:
        """작업 취소"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return False
            
            update_query = """
            UPDATE collection_jobs 
            SET status = 'CANCELLED', end_time = %s, updated_at = %s
            WHERE id = %s AND status IN ('PENDING', 'RUNNING')
            """
            
            params = (datetime.now(), datetime.now(), job_id)
            
            if self.db.execute_query(update_query, params):
                logger.info(f"✅ 작업 취소: Job ID={job_id}")
                return True
            else:
                logger.error(f"작업 취소 실패: Job ID={job_id}")
                return False
                
        except Exception as e:
            logger.error(f"작업 취소 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return None
            
            query = """
            SELECT id, job_type, status, trigger_type, start_time, end_time,
                   progress_total, progress_processed, progress_current_batch, progress_total_batches,
                   success_count, failed_count, skipped_count, error_message,
                   job_config, created_at, updated_at
            FROM collection_jobs 
            WHERE id = %s
            """
            
            result = self.db.fetch_one(query, (job_id,))
            
            if result:
                # JSON 컬럼 파싱
                job_config = None
                if result.get('job_config'):
                    try:
                        job_config = json.loads(result['job_config'])
                    except:
                        job_config = {}
                
                # 진행률 계산
                progress_percentage = 0
                if result['progress_total'] and result['progress_total'] > 0:
                    progress_percentage = (result['progress_processed'] / result['progress_total']) * 100
                
                # 실행 시간 계산
                duration = None
                if result['start_time']:
                    end_time = result['end_time'] or datetime.now()
                    duration = (end_time - result['start_time']).total_seconds()
                
                return {
                    'id': result['id'],
                    'job_type': result['job_type'],
                    'status': result['status'],
                    'trigger_type': result['trigger_type'],
                    'start_time': result['start_time'].isoformat() if result['start_time'] else None,
                    'end_time': result['end_time'].isoformat() if result['end_time'] else None,
                    'progress': {
                        'total': result['progress_total'],
                        'processed': result['progress_processed'],
                        'current_batch': result['progress_current_batch'],
                        'total_batches': result['progress_total_batches'],
                        'percentage': round(progress_percentage, 2)
                    },
                    'stats': {
                        'success': result['success_count'],
                        'failed': result['failed_count'],
                        'skipped': result['skipped_count']
                    },
                    'duration': round(duration, 2) if duration else None,
                    'error_message': result['error_message'],
                    'job_config': job_config,
                    'created_at': result['created_at'].isoformat() if result['created_at'] else None,
                    'updated_at': result['updated_at'].isoformat() if result['updated_at'] else None
                }
            else:
                logger.warning(f"작업을 찾을 수 없습니다: Job ID={job_id}")
                return None
                
        except Exception as e:
            logger.error(f"작업 상태 조회 중 오류: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def get_running_job(self, job_type: str = None) -> Optional[Dict[str, Any]]:
        """실행 중인 작업 조회"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return None
            
            if job_type:
                query = """
                SELECT id, job_type, status, start_time, progress_total, progress_processed
                FROM collection_jobs 
                WHERE job_type = %s AND status = 'RUNNING'
                ORDER BY start_time DESC LIMIT 1
                """
                params = (job_type,)
            else:
                query = """
                SELECT id, job_type, status, start_time, progress_total, progress_processed
                FROM collection_jobs 
                WHERE status = 'RUNNING'
                ORDER BY start_time DESC LIMIT 1
                """
                params = ()
            
            result = self.db.fetch_one(query, params)
            
            if result:
                return {
                    'id': result['id'],
                    'job_type': result['job_type'],
                    'status': result['status'],
                    'start_time': result['start_time'].isoformat() if result['start_time'] else None,
                    'progress_total': result['progress_total'],
                    'progress_processed': result['progress_processed']
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"실행 중인 작업 조회 중 오류: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def get_recent_jobs(self, limit: int = 10, job_type: str = None) -> List[Dict[str, Any]]:
        """최근 작업 목록 조회"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return []
            
            if job_type:
                query = """
                SELECT id, job_type, status, trigger_type, start_time, end_time,
                       progress_total, progress_processed, success_count, failed_count, skipped_count,
                       created_at
                FROM collection_jobs 
                WHERE job_type = %s
                ORDER BY created_at DESC LIMIT %s
                """
                params = (job_type, limit)
            else:
                query = """
                SELECT id, job_type, status, trigger_type, start_time, end_time,
                       progress_total, progress_processed, success_count, failed_count, skipped_count,
                       created_at
                FROM collection_jobs 
                ORDER BY created_at DESC LIMIT %s
                """
                params = (limit,)
            
            results = self.db.fetch_all(query, params)
            
            jobs = []
            for result in results:
                # 진행률 계산
                progress_percentage = 0
                if result['progress_total'] and result['progress_total'] > 0:
                    progress_percentage = (result['progress_processed'] / result['progress_total']) * 100
                
                # 실행 시간 계산
                duration = None
                if result['start_time']:
                    end_time = result['end_time'] or datetime.now()
                    duration = (end_time - result['start_time']).total_seconds()
                
                jobs.append({
                    'id': result['id'],
                    'job_type': result['job_type'],
                    'status': result['status'],
                    'trigger_type': result['trigger_type'],
                    'start_time': result['start_time'].isoformat() if result['start_time'] else None,
                    'end_time': result['end_time'].isoformat() if result['end_time'] else None,
                    'progress': {
                        'total': result['progress_total'],
                        'processed': result['progress_processed'],
                        'percentage': round(progress_percentage, 2)
                    },
                    'stats': {
                        'success': result['success_count'],
                        'failed': result['failed_count'],
                        'skipped': result['skipped_count']
                    },
                    'duration': round(duration, 2) if duration else None,
                    'created_at': result['created_at'].isoformat() if result['created_at'] else None
                })
            
            return jobs
                
        except Exception as e:
            logger.error(f"최근 작업 목록 조회 중 오류: {e}")
            return []
        finally:
            self.db.disconnect()
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """오래된 작업 정리"""
        try:
            if not self.db.connect():
                logger.error("데이터베이스 연결 실패")
                return 0
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            delete_query = """
            DELETE FROM collection_jobs 
            WHERE created_at < %s AND status IN ('COMPLETED', 'FAILED', 'CANCELLED')
            """
            
            if self.db.execute_query(delete_query, (cutoff_date,)):
                deleted_count = self.db.cursor.rowcount if hasattr(self.db, 'cursor') else 0
                logger.info(f"✅ {days}일 이전 완료된 작업 {deleted_count}개 정리 완료")
                return deleted_count
            else:
                logger.error("오래된 작업 정리 실패")
                return 0
                
        except Exception as e:
            logger.error(f"오래된 작업 정리 중 오류: {e}")
            return 0
        finally:
            self.db.disconnect()
