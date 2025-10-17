#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 스케줄러 (Batch Scheduler)
APScheduler를 사용한 자동 수집 작업 스케줄링
"""

# UTF-8 인코딩 설정 (Windows 환경 대응)
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

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
from cleanup_running_jobs import cleanup_running_jobs

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
            
            # 🧹 스케줄 실행 전 실행 중인 작업 정리 (우선순위 보장)
            logger.info("🧹 실행 중인 작업 정리 중...")
            cleanup_running_jobs()
            
            # 스케줄 정보 조회
            schedule_info = self._get_schedule_info(schedule_id)
            if not schedule_info:
                logger.error(f"스케줄 정보를 찾을 수 없습니다: Schedule ID={schedule_id}")
                return
            
            job_type = schedule_info['job_type']
            job_config = schedule_info.get('job_config', {})
            
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
        """수집 완료 플래그 업데이트 및 랭킹 추출 시작"""
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
                logger.info(f"   → 랭킹 추출을 시작합니다.")
                
                # 비동기로 랭킹 추출 및 분석 시작
                import threading
                thread = threading.Thread(
                    target=self._start_ranking_extraction_and_analysis,
                    args=(schedule_id,),
                    daemon=True
                )
                thread.start()
                logger.info(f"   → 랭킹 추출 스레드 시작됨")
            else:
                logger.error(f"수집 완료 플래그 업데이트 실패: Schedule ID={schedule_id}")
            
        except Exception as e:
            logger.error(f"수집 완료 플래그 업데이트 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.db.disconnect()
    
    def _start_ranking_extraction_and_analysis(self, schedule_id: int):
        """랭킹 추출 및 분석 실행 (비동기)"""
        try:
            logger.info(f"[INFO] 랭킹 추출 및 분석 시작: Schedule ID={schedule_id}")
            
            # 1. 랭킹 추출
            from ranking_data_extractor import RankingDataExtractor
            
            extractor = RankingDataExtractor()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            batch_id = f"schedule_{schedule_id}_{timestamp}"
            
            # target_date=None으로 전달하면 daily_data의 최신 trade_date 자동 조회
            result = extractor.extract_rankings_for_auto_analysis(
                target_date=None,  # None으로 전달하면 daily_data의 최신 trade_date 사용
                batch_id=batch_id
            )
            
            if not result.get('success'):
                logger.error(f"❌ 랭킹 추출 실패: {result.get('error')}")
                return
            
            logger.info(f"✅ 랭킹 추출 완료")
            logger.info(f"   - 거래율 파일: {result.get('turnover_file')}")
            logger.info(f"   - 거래대금 파일: {result.get('volume_file')}")
            
            # 랭킹 추출 완료 플래그 업데이트
            if not self.db.connect():
                logger.error("DB 연결 실패")
                return
            
            update_query = """
            UPDATE batch_schedules 
            SET ranking_extracted = TRUE, 
                ranking_extracted_at = %s,
                updated_at = %s
            WHERE id = %s
            """
            
            params = (datetime.now(), datetime.now(), schedule_id)
            self.db.execute_query(update_query, params)
            self.db.disconnect()
            
            # 2. 분석 시작
            self._run_analysis_async(result, schedule_id)
            
        except Exception as e:
            logger.error(f"랭킹 추출 및 분석 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _run_analysis_async(self, ranking_result: Dict, schedule_id: int):
        """분석 실행 (비동기)"""
        try:
            logger.info(f"📊 분석 시작: Schedule ID={schedule_id}")
            
            turnover_file = ranking_result.get('turnover_file')
            volume_file = ranking_result.get('volume_file')
            
            # 파일 존재 확인
            import os
            if not turnover_file or not os.path.exists(turnover_file):
                logger.error(f"거래율 파일을 찾을 수 없습니다: {turnover_file}")
                return
            
            if not volume_file or not os.path.exists(volume_file):
                logger.error(f"거래대금 파일을 찾을 수 없습니다: {volume_file}")
                return
            
            # BatchAnalyzer 임포트
            from api.batch_analyzer import BatchAnalyzer
            batch_analyzer = BatchAnalyzer()
            
            today = datetime.now().strftime('%Y-%m-%d')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            # 1. 거래율 분석
            logger.info(f"📈 거래율 상위 50위 분석 시작...")
            turnover_batch_id = f"auto_turnover_{timestamp}"
            
            batch_analyzer.start_batch_analysis(
                stock_list_path=turnover_file,
                chart_type='일봉',
                batch_id=turnover_batch_id,
                trading_type='거래율',
                email_enabled=False,
                email_address=''
            )
            
            # 2. 거래대금 분석
            logger.info(f"💰 거래대금 상위 50위 분석 시작...")
            volume_batch_id = f"auto_volume_{timestamp}"
            
            batch_analyzer.start_batch_analysis(
                stock_list_path=volume_file,
                chart_type='일봉',
                batch_id=volume_batch_id,
                trading_type='거래대금',
                email_enabled=False,
                email_address=''
            )
            
            # 🆕 모든 분석이 완료된 후 캐시 정리 (차트 이미지 꼬임 방지)
            logger.info(f"🧹 모든 분석 완료 후 캐시 정리 시작...")
            batch_analyzer.clear_batch_cache(f"auto_analysis_{timestamp}")
            logger.info(f"✅ 캐시 정리 완료!")
            
            # 분석 시작 플래그 업데이트
            if not self.db.connect():
                logger.error("DB 연결 실패")
                return
            
            update_query = """
            UPDATE batch_schedules 
            SET analysis_started = TRUE, 
                analysis_started_at = %s,
                updated_at = %s
            WHERE id = %s
            """
            
            params = (datetime.now(), datetime.now(), schedule_id)
            self.db.execute_query(update_query, params)
            self.db.disconnect()
            
            logger.info(f"✅ 분석 완료: Schedule ID={schedule_id}")
            
            # 🆕 분석 완료 후 블로그 작성 시작
            logger.info(f"📝 블로그 자동 작성 시작: Schedule ID={schedule_id}")
            self._run_blog_writing_async(schedule_id)
            
        except Exception as e:
            logger.error(f"분석 실행 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _run_blog_writing_async(self, schedule_id: int):
        """블로그 작성 실행 (비동기)"""
        try:
            logger.info(f"📝 블로그 자동 작성 시작: Schedule ID={schedule_id}")
            
            # auto_blog.py 임포트
            import sys
            import os
            
            # 프로젝트 루트 및 blog_auto 디렉토리 경로 설정
            project_root = os.path.dirname(os.path.abspath(__file__))
            blog_auto_path = os.path.join(project_root, 'blog_auto')
            docs_path = os.path.join(blog_auto_path, 'docs')
            
            logger.info(f"[DEBUG] 프로젝트 루트: {project_root}")
            logger.info(f"[DEBUG] blog_auto 경로: {blog_auto_path}")
            logger.info(f"[DEBUG] docs 경로: {docs_path}")
            
            # blog_auto 디렉토리를 경로에 추가
            if blog_auto_path not in sys.path:
                sys.path.insert(0, blog_auto_path)
            
            # docs 디렉토리 존재 확인
            if not os.path.exists(docs_path):
                logger.warning(f"⚠️ docs 디렉토리가 존재하지 않습니다: {docs_path}")
                logger.info(f"📁 docs 디렉토리를 생성합니다...")
                os.makedirs(docs_path, exist_ok=True)
            
            from auto_blog import NaverBlogBot
            
            # 블로그 봇 인스턴스 생성 (일반 모드 - 캡챠 처리 가능)
            bot = NaverBlogBot(headless=False, debug_mode=True)
            
            try:
                # 로그인
                if not bot.run_login():
                    logger.error(f"❌ 블로그 로그인 실패: Schedule ID={schedule_id}")
                    self._update_blog_writing_status(schedule_id, False, "로그인 실패")
                    return
                
                logger.info(f"✅ 블로그 로그인 성공: Schedule ID={schedule_id}")
                
                # docs 경로 확인
                if not os.path.exists(docs_path):
                    logger.error(f"❌ docs 디렉토리를 찾을 수 없습니다: {docs_path}")
                    self._update_blog_writing_status(schedule_id, False, "docs 디렉토리 없음")
                    return
                
                # docs 디렉토리의 zip 파일 확인
                zip_files = [f for f in os.listdir(docs_path) if f.endswith('.zip')]
                logger.info(f"📂 docs 디렉토리: {docs_path}")
                logger.info(f"📦 발견된 zip 파일: {len(zip_files)}개")
                
                if zip_files:
                    for zip_file in zip_files:
                        logger.info(f"   - {zip_file}")
                
                # docs 폴더의 zip 파일 처리 및 블로그 작성
                if bot.docs_zip_processor:
                    # 미처리 zip 파일 확인
                    unprocessed_zips = bot.get_unprocessed_zips()
                    
                    if not unprocessed_zips:
                        logger.info(f"📭 처리할 zip 파일이 없습니다: Schedule ID={schedule_id}")
                        logger.info(f"   (총 {len(zip_files)}개 zip 파일이 있지만 모두 처리됨)")
                        self._update_blog_writing_status(schedule_id, True, "처리할 파일 없음")
                        return
                    
                    logger.info(f"📦 총 {len(unprocessed_zips)}개의 zip 파일 처리 시작")
                    
                    # 각 zip 파일 처리
                    success_count = 0
                    for zip_path in unprocessed_zips:
                        zip_filename = os.path.basename(zip_path)
                        logger.info(f"📝 블로그 작성 중: {zip_filename}")
                        
                        try:
                            # 단일 zip 파일 처리
                            blog_post = bot.docs_zip_processor.process_single_zip_file(zip_path)
                            
                            if not blog_post:
                                logger.error(f"❌ ZIP 파일 처리 실패: {zip_filename}")
                                continue
                            
                            # 블로그 글쓰기 페이지로 이동
                            if not bot.navigate_to_blog_write():
                                logger.error(f"❌ 블로그 글쓰기 페이지 이동 실패")
                                continue
                            
                            # iframe으로 전환
                            if not bot.switch_to_blog_frame():
                                logger.error(f"❌ iframe 전환 실패")
                                continue
                            
                            # 팝업 닫기
                            bot.close_popups_and_help()
                            
                            # 제목 입력
                            if not bot.enter_blog_title(blog_post['title']):
                                logger.error(f"❌ 제목 입력 실패")
                                continue
                            
                            # 내용과 표 입력
                            if not bot.write_content_with_structured_tables(blog_post['content'], blog_post['tables']):
                                logger.error(f"❌ 내용 입력 실패")
                                continue
                            
                            # 첨부파일 추가
                            if blog_post.get('attachment_file'):
                                if not bot.add_file_to_blog(blog_post['attachment_file']):
                                    logger.warning(f"⚠️ 첨부파일 추가 실패")
                            
                            # 분석월 추출 (ZIP 파일명에서)
                            analysis_month = None
                            try:
                                from zip_analyzer import ZipAnalyzer
                                zip_analyzer = ZipAnalyzer()
                                zip_result = zip_analyzer.parse_zip_filename(zip_filename)
                                if zip_result:
                                    analysis_month = zip_result['analysis_month']
                            except Exception as e:
                                logger.warning(f"⚠️ 분석월 추출 실패: {e}")
                            
                            # 태그 정보
                            tags = blog_post.get('tags', '')
                            
                            # 발행
                            if not bot.click_save_button(analysis_month, tags):
                                logger.error(f"❌ 발행 실패")
                                continue
                            
                            logger.info(f"✅ 블로그 작성 완료: {zip_filename}")
                            success_count += 1
                            
                            # 처리 완료 표시
                            bot.mark_zip_as_processed(zip_filename)
                            
                            # 작성 페이지로 돌아가기
                            bot.return_to_write_page()
                            
                            # extracted 폴더만 정리 (ZIP 파일은 유지)
                            if bot.docs_zip_processor:
                                bot.docs_zip_processor.cleanup_extracted_files()
                                logger.info(f"✅ extracted 폴더 정리 완료")
                            
                        except Exception as e:
                            logger.error(f"❌ 블로그 작성 중 오류: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            continue
                    
                    # 블로그 작성 상태 업데이트
                    if success_count > 0:
                        self._update_blog_writing_status(schedule_id, True, f"{success_count}개 포스트 작성 완료")
                        logger.info(f"✅ 블로그 자동 작성 완료: {success_count}개 포스트")
                    else:
                        self._update_blog_writing_status(schedule_id, False, "모든 포스트 작성 실패")
                        logger.error(f"❌ 블로그 자동 작성 실패: 모든 포스트 작성 실패")
                else:
                    logger.error(f"❌ docs zip 처리기를 사용할 수 없습니다.")
                    self._update_blog_writing_status(schedule_id, False, "docs zip 처리기 없음")
                
            finally:
                # 드라이버 정리
                bot.close_driver()
                
        except Exception as e:
            logger.error(f"블로그 자동 작성 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._update_blog_writing_status(schedule_id, False, str(e))
    
    def _update_blog_writing_status(self, schedule_id: int, success: bool, message: str = ""):
        """블로그 작성 상태 업데이트"""
        try:
            if not self.db.connect():
                logger.error("DB 연결 실패")
                return
            
            if success:
                update_query = """
                UPDATE batch_schedules 
                SET blog_written = TRUE, 
                    blog_written_at = %s,
                    updated_at = %s
                WHERE id = %s
                """
                params = (datetime.now(), datetime.now(), schedule_id)
            else:
                update_query = """
                UPDATE batch_schedules 
                SET blog_error_message = %s,
                    updated_at = %s
                WHERE id = %s
                """
                params = (message, datetime.now(), schedule_id)
            
            if self.db.execute_query(update_query, params):
                logger.info(f"블로그 작성 상태 업데이트: Schedule ID={schedule_id}, Success={success}")
            
        except Exception as e:
            logger.error(f"블로그 작성 상태 업데이트 실패: {e}")
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
