#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
일일 시세 수집 API 라우트
주식 데이터 수집을 위한 REST API 엔드포인트 제공
DB 기반 상태 관리로 개선 (기존 메모리 기반 로직 병행 유지)
"""

from flask import Blueprint, request, jsonify
import logging
import threading
import time
from datetime import datetime
import traceback

# 새로운 DB 기반 작업 관리자 import
try:
    from collection_job_manager import CollectionJobManager
    JOB_MANAGER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"CollectionJobManager import 실패: {e}")
    JOB_MANAGER_AVAILABLE = False

# 로깅 설정
logger = logging.getLogger(__name__)

# 블루프린트 생성
daily_collection_bp = Blueprint('daily_collection', __name__)

# 기존 전역 변수로 수집 상태 관리 (하위 호환성 유지)
collection_status = {
    'status': 'idle',  # idle, running, completed, error
    'start_time': None,
    'end_time': None,
    'progress': {
        'total': 0,
        'processed': 0,
        'current_batch': 0,
        'total_batches': 0
    },
    'stats': {
        'total': 0,
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0
    },
    'current_task': None,
    'error_message': None,
    'job_id': None  # DB 작업 ID 추가
}

# DB 기반 작업 관리자 인스턴스
job_manager = CollectionJobManager() if JOB_MANAGER_AVAILABLE else None

@daily_collection_bp.route('/api/daily-collection/start', methods=['POST'])
def start_collection():
    """일일 시세 수집 시작 (DB 기반 상태 관리 + 기존 로직 병행)"""
    try:
        global collection_status
        
        # DB 기반 작업 관리자를 사용할 수 있으면 우선 사용
        if job_manager:
            # 이미 실행 중인 작업이 있는지 DB에서 확인
            running_job = job_manager.get_running_job('DAILY_COLLECTION')
            if running_job:
                return jsonify({
                    'success': False,
                    'error': '이미 수집이 진행 중입니다.',
                    'job_id': running_job['id']
                }), 400
            
            # 새로운 작업 생성
            job_config = {
                'batch_size': 100,
                'max_workers': 5,
                'trigger_source': 'web_ui'
            }
            job_id = job_manager.create_job('DAILY_COLLECTION', 'MANUAL', job_config)
            
            if not job_id:
                logger.error("DB 작업 생성 실패")
                # DB 실패 시 기존 방식으로 fallback
            else:
                # DB 작업 시작
                if job_manager.start_job(job_id):
                    collection_status['job_id'] = job_id
                    logger.info(f"DB 기반 작업 시작: Job ID={job_id}")
                else:
                    logger.error(f"DB 작업 시작 실패: Job ID={job_id}")
        
        # 기존 메모리 기반 상태 관리도 병행 유지 (하위 호환성)
        if collection_status['status'] == 'running':
            return jsonify({
                'success': False,
                'error': '이미 수집이 진행 중입니다.',
                'job_id': collection_status.get('job_id')
            }), 400
        
        # 상태 초기화
        collection_status.update({
            'status': 'running',
            'start_time': datetime.now(),
            'end_time': None,
            'progress': {
                'total': 0,
                'processed': 0,
                'current_batch': 0,
                'total_batches': 0
            },
            'stats': {
                'total': 0,
                'processed': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0
            },
            'error_message': None
        })
        
        # 백그라운드에서 수집 작업 시작
        collection_thread = threading.Thread(
            target=run_collection_task,
            daemon=True
        )
        collection_thread.start()
        
        collection_status['current_task'] = collection_thread
        
        logger.info("일일 시세 수집 시작: 전체 종목을 100개씩 배치로 수집")
        
        return jsonify({
            'success': True,
            'message': '수집이 시작되었습니다.',
            'job_id': collection_status.get('job_id', int(time.time())),
            'collection_id': int(time.time())  # 하위 호환성
        })
        
    except Exception as e:
        logger.error(f"수집 시작 중 오류: {e}")
        logger.error(traceback.format_exc())
        
        collection_status.update({
            'status': 'error',
            'error_message': str(e)
        })
        
        return jsonify({
            'success': False,
            'error': f'수집 시작 중 오류가 발생했습니다: {str(e)}'
        }), 500

@daily_collection_bp.route('/api/daily-collection/stop', methods=['POST'])
def stop_collection():
    """일일 시세 수집 중지"""
    try:
        global collection_status
        
        if collection_status['status'] != 'running':
            return jsonify({
                'success': False,
                'error': '현재 실행 중인 수집 작업이 없습니다.'
            }), 400
        
        # 상태 업데이트
        collection_status.update({
            'status': 'idle',
            'end_time': datetime.now()
        })
        
        logger.info("일일 시세 수집이 중지되었습니다.")
        
        return jsonify({
            'success': True,
            'message': '수집이 중지되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"수집 중지 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'수집 중지 중 오류가 발생했습니다: {str(e)}'
        }), 500

@daily_collection_bp.route('/api/daily-collection/status', methods=['GET'])
@daily_collection_bp.route('/api/daily-collection/status/<int:job_id>', methods=['GET'])
def get_collection_status(job_id=None):
    """일일 시세 수집 상태 조회 (DB 기반 + 기존 로직 병행)"""
    try:
        global collection_status
        
        # DB 기반 상태 조회 우선 시도
        if job_manager and job_id:
            db_status = job_manager.get_job_status(job_id)
            if db_status:
                return jsonify(db_status)
        
        # 현재 실행 중인 작업이 있으면 DB에서 조회
        if job_manager and collection_status.get('job_id'):
            db_status = job_manager.get_job_status(collection_status['job_id'])
            if db_status:
                # 메모리 상태와 DB 상태 동기화
                collection_status['status'] = db_status['status'].lower()
                return jsonify(db_status)
        
        # 기존 메모리 기반 상태 조회 (하위 호환성)
        progress_percentage = 0
        if collection_status['progress']['total'] > 0:
            progress_percentage = (collection_status['progress']['processed'] / collection_status['progress']['total']) * 100
        
        # 실행 시간 계산
        duration = None
        if collection_status['start_time']:
            if collection_status['end_time']:
                duration = (collection_status['end_time'] - collection_status['start_time']).total_seconds()
            else:
                duration = (datetime.now() - collection_status['start_time']).total_seconds()
        
        return jsonify({
            'status': collection_status['status'],
            'job_id': collection_status.get('job_id'),
            'progress': {
                'total': collection_status['progress']['total'],
                'processed': collection_status['progress']['processed'],
                'current_batch': collection_status['progress']['current_batch'],
                'total_batches': collection_status['progress']['total_batches'],
                'percentage': round(progress_percentage, 2)
            },
            'stats': collection_status['stats'],
            'start_time': collection_status['start_time'].isoformat() if collection_status['start_time'] else None,
            'end_time': collection_status['end_time'].isoformat() if collection_status['end_time'] else None,
            'duration': round(duration, 2) if duration else None,
            'error_message': collection_status['error_message']
        })
        
    except Exception as e:
        logger.error(f"상태 조회 중 오류: {e}")
        return jsonify({
            'status': 'error',
            'error': f'상태 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

def run_collection_task():
    """백그라운드에서 수집 작업 실행"""
    try:
        global collection_status
        
        logger.info("수집 작업 시작: 전체 종목을 100개씩 배치로 수집")
        
        # StockDataCollector 임포트 및 초기화
        try:
            from stock_data_collector import StockDataCollector
            collector = StockDataCollector()
            
            # 콜백 함수 설정
            collector.set_progress_callback(update_progress)
            collector.set_stats_callback(update_stats)
            
        except ImportError as e:
            logger.error(f"StockDataCollector 임포트 실패: {e}")
            collection_status.update({
                'status': 'error',
                'error_message': f'StockDataCollector 모듈을 찾을 수 없습니다: {e}'
            })
            return
        
        # 전체 종목 수집 (자동으로 초기/증분 판단)
        logger.info("전체 종목 수집 시작")
        success, failed = collector.collect_all_stocks()
        
        # 결과 처리
        total = success + failed
        collection_status.update({
            'status': 'completed',
            'end_time': datetime.now(),
            'progress': {
                'total': total,
                'processed': total,
                'current_batch': 0,
                'total_batches': 0
            },
            'stats': {
                'total': total,
                'processed': total,
                'success': success,
                'failed': failed,
                'skipped': 0
            }
        })
        
        logger.info(f"수집 작업 완료: 성공={success}, 실패={failed}, 총={total}")
        
    except Exception as e:
        logger.error(f"수집 작업 실행 중 오류: {e}")
        logger.error(traceback.format_exc())
        
        collection_status.update({
            'status': 'error',
            'end_time': datetime.now(),
            'error_message': str(e)
        })
    
    finally:
        # 작업 완료 후 정리
        collection_status['current_task'] = None

def update_progress(total, processed, current_batch, total_batches):
    """진행률 업데이트 (DB + 메모리 병행)"""
    global collection_status
    
    # 메모리 기반 업데이트 (기존 로직)
    collection_status['progress'].update({
        'total': total,
        'processed': processed,
        'current_batch': current_batch,
        'total_batches': total_batches
    })
    
    # DB 기반 업데이트 (새로운 기능)
    if job_manager and collection_status.get('job_id'):
        job_manager.update_progress(
            collection_status['job_id'],
            total, processed, current_batch, total_batches
        )

def update_stats(success_count, failed_count, skipped_count=0):
    """통계 업데이트 (누적) - DB + 메모리 병행"""
    global collection_status
    
    # 메모리 기반 업데이트 (기존 로직)
    current_stats = collection_status['stats']
    current_stats['success'] += success_count
    current_stats['failed'] += failed_count
    current_stats['skipped'] += skipped_count
    current_stats['processed'] = current_stats['success'] + current_stats['failed'] + current_stats['skipped']
    
    # 전체 종목 수 업데이트 (처음 호출 시에만)
    if current_stats['total'] == 0:
        current_stats['total'] = current_stats['processed']
    
    # DB 기반 업데이트 (새로운 기능)
    if job_manager and collection_status.get('job_id'):
        job_manager.update_stats(
            collection_status['job_id'],
            current_stats['success'], 
            current_stats['failed'], 
            current_stats['skipped']
        )

# 새로운 API 엔드포인트들 (DB 기반 기능)

@daily_collection_bp.route('/api/daily-collection/history', methods=['GET'])
def get_collection_history():
    """수집 작업 히스토리 조회"""
    try:
        if not job_manager:
            return jsonify({
                'success': False,
                'error': 'DB 기반 작업 관리자를 사용할 수 없습니다.'
            }), 503
        
        limit = request.args.get('limit', 10, type=int)
        job_type = request.args.get('job_type', 'DAILY_COLLECTION')
        
        jobs = job_manager.get_recent_jobs(limit, job_type)
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'total': len(jobs)
        })
        
    except Exception as e:
        logger.error(f"작업 히스토리 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'작업 히스토리 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@daily_collection_bp.route('/api/daily-collection/running', methods=['GET'])
def get_running_collection():
    """현재 실행 중인 수집 작업 조회"""
    try:
        if not job_manager:
            # DB 기반 관리자가 없으면 메모리 기반 상태 반환
            if collection_status['status'] == 'running':
                return jsonify({
                    'success': True,
                    'running_job': {
                        'id': collection_status.get('job_id', 'memory_based'),
                        'job_type': 'DAILY_COLLECTION',
                        'status': 'RUNNING',
                        'start_time': collection_status['start_time'].isoformat() if collection_status['start_time'] else None,
                        'progress_total': collection_status['progress']['total'],
                        'progress_processed': collection_status['progress']['processed']
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'running_job': None
                })
        
        running_job = job_manager.get_running_job('DAILY_COLLECTION')
        
        return jsonify({
            'success': True,
            'running_job': running_job
        })
        
    except Exception as e:
        logger.error(f"실행 중인 작업 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'실행 중인 작업 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@daily_collection_bp.route('/api/daily-collection/cancel/<int:job_id>', methods=['POST'])
def cancel_collection(job_id):
    """특정 수집 작업 취소"""
    try:
        if not job_manager:
            return jsonify({
                'success': False,
                'error': 'DB 기반 작업 관리자를 사용할 수 없습니다.'
            }), 503
        
        if job_manager.cancel_job(job_id):
            # 현재 메모리 상태와 동기화
            if collection_status.get('job_id') == job_id:
                collection_status['status'] = 'idle'
                collection_status['end_time'] = datetime.now()
            
            return jsonify({
                'success': True,
                'message': f'작업 {job_id}가 취소되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'작업 {job_id} 취소에 실패했습니다.'
            }), 400
        
    except Exception as e:
        logger.error(f"작업 취소 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'작업 취소 중 오류가 발생했습니다: {str(e)}'
        }), 500
