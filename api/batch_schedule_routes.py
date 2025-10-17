#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 스케줄 관리 API 라우트
자동 수집 스케줄 관리를 위한 REST API 엔드포인트 제공
"""

from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime

from database_config import DatabaseManager

# 배치 스케줄러 import (선택적)
try:
    from batch_scheduler import get_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"BatchScheduler import 실패: {e}")
    SCHEDULER_AVAILABLE = False

# 로깅 설정
logger = logging.getLogger(__name__)

# 블루프린트 생성
batch_schedule_bp = Blueprint('batch_schedule', __name__)

@batch_schedule_bp.route('/api/batch-schedule/list', methods=['GET'])
def get_schedule_list():
    """배치 스케줄 목록 조회"""
    try:
        db = DatabaseManager()
        
        if not db.connect():
            return jsonify({
                'success': False,
                'error': '데이터베이스 연결 실패'
            }), 500
        
        query = """
        SELECT s.id, s.schedule_name, s.job_type, s.cron_expression, s.is_active,
               s.last_run, s.next_run, s.description, s.job_config,
               s.collection_completed, s.ranking_extracted, s.analysis_started,
               s.blog_written, s.blog_written_at, s.blog_post_url, s.blog_error_message,
               j.status as last_job_status, j.success_count, j.failed_count
        FROM batch_schedules s
        LEFT JOIN collection_jobs j ON s.last_job_id = j.id
        ORDER BY s.created_at DESC
        """
        
        schedules = db.fetch_all(query)
        
        result = []
        for schedule in schedules:
            job_config = {}
            if schedule.get('job_config'):
                try:
                    job_config = json.loads(schedule['job_config'])
                except:
                    job_config = {}
            
            result.append({
                'id': schedule['id'],
                'schedule_name': schedule['schedule_name'],
                'job_type': schedule['job_type'],
                'cron_expression': schedule['cron_expression'],
                'is_active': bool(schedule['is_active']),
                'last_run': schedule['last_run'].isoformat() if schedule['last_run'] else None,
                'next_run': schedule['next_run'].isoformat() if schedule['next_run'] else None,
                'description': schedule['description'],
                'job_config': job_config,
                'last_job_status': schedule['last_job_status'],
                'last_success_count': schedule['success_count'] or 0,
                'last_failed_count': schedule['failed_count'] or 0,
                'collection_completed': bool(schedule.get('collection_completed', False)),
                'ranking_extracted': bool(schedule.get('ranking_extracted', False)),
                'analysis_started': bool(schedule.get('analysis_started', False)),
                'blog_written': bool(schedule.get('blog_written', False)),
                'blog_written_at': schedule['blog_written_at'].isoformat() if schedule.get('blog_written_at') else None,
                'blog_post_url': schedule.get('blog_post_url'),
                'blog_error_message': schedule.get('blog_error_message')
            })
        
        return jsonify({
            'success': True,
            'schedules': result,
            'total': len(result)
        })
        
    except Exception as e:
        logger.error(f"스케줄 목록 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄 목록 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500
    finally:
        db.disconnect()

@batch_schedule_bp.route('/api/batch-schedule/toggle/<int:schedule_id>', methods=['POST'])
def toggle_schedule(schedule_id):
    """스케줄 활성화/비활성화 토글"""
    try:
        db = DatabaseManager()
        
        if not db.connect():
            return jsonify({
                'success': False,
                'error': '데이터베이스 연결 실패'
            }), 500
        
        # 현재 상태 조회
        query = "SELECT is_active, schedule_name FROM batch_schedules WHERE id = %s"
        result = db.fetch_one(query, (schedule_id,))
        
        if not result:
            return jsonify({
                'success': False,
                'error': f'스케줄 {schedule_id}를 찾을 수 없습니다.'
            }), 404
        
        current_status = result['is_active']
        schedule_name = result['schedule_name']
        new_status = not current_status
        
        # 상태 업데이트
        update_query = """
        UPDATE batch_schedules 
        SET is_active = %s, updated_at = %s
        WHERE id = %s
        """
        
        params = (new_status, datetime.now(), schedule_id)
        
        if db.execute_query(update_query, params):
            # 스케줄러 재로드 (가능한 경우)
            if SCHEDULER_AVAILABLE:
                try:
                    scheduler = get_scheduler()
                    scheduler.reload_schedules()
                    logger.info(f"스케줄러 재로드 완료")
                except Exception as e:
                    logger.warning(f"스케줄러 재로드 실패: {e}")
            
            status_text = "활성화" if new_status else "비활성화"
            logger.info(f"스케줄 {status_text}: {schedule_name} (ID: {schedule_id})")
            
            return jsonify({
                'success': True,
                'message': f'스케줄이 {status_text}되었습니다.',
                'schedule_id': schedule_id,
                'is_active': new_status
            })
        else:
            return jsonify({
                'success': False,
                'error': '스케줄 상태 업데이트에 실패했습니다.'
            }), 500
        
    except Exception as e:
        logger.error(f"스케줄 토글 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄 토글 중 오류가 발생했습니다: {str(e)}'
        }), 500
    finally:
        db.disconnect()

@batch_schedule_bp.route('/api/batch-schedule/create', methods=['POST'])
def create_schedule():
    """새로운 배치 스케줄 생성"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '요청 데이터가 없습니다.'
            }), 400
        
        # 필수 필드 검증
        required_fields = ['schedule_name', 'job_type', 'cron_expression']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'필수 필드가 누락되었습니다: {field}'
                }), 400
        
        # 크론 표현식 검증
        cron_expression = data['cron_expression'].strip()
        cron_parts = cron_expression.split()
        if len(cron_parts) != 5:
            return jsonify({
                'success': False,
                'error': '잘못된 크론 표현식입니다. (예: "0 16 * * 1-5")'
            }), 400
        
        db = DatabaseManager()
        
        if not db.connect():
            return jsonify({
                'success': False,
                'error': '데이터베이스 연결 실패'
            }), 500
        
        # 중복 이름 확인
        check_query = "SELECT id FROM batch_schedules WHERE schedule_name = %s"
        existing = db.fetch_one(check_query, (data['schedule_name'],))
        
        if existing:
            return jsonify({
                'success': False,
                'error': '동일한 이름의 스케줄이 이미 존재합니다.'
            }), 400
        
        # 스케줄 생성
        insert_query = """
        INSERT INTO batch_schedules 
        (schedule_name, job_type, cron_expression, description, job_config, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        job_config = data.get('job_config', {})
        job_config_json = json.dumps(job_config) if job_config else None
        
        params = (
            data['schedule_name'],
            data['job_type'],
            cron_expression,
            data.get('description', ''),
            job_config_json,
            data.get('is_active', False)
        )
        
        if db.execute_query(insert_query, params):
            schedule_id = db.get_last_insert_id()
            
            # 스케줄러 재로드 (가능한 경우)
            if SCHEDULER_AVAILABLE and data.get('is_active', False):
                try:
                    scheduler = get_scheduler()
                    scheduler.reload_schedules()
                    logger.info(f"스케줄러 재로드 완료")
                except Exception as e:
                    logger.warning(f"스케줄러 재로드 실패: {e}")
            
            logger.info(f"새로운 스케줄 생성: {data['schedule_name']} (ID: {schedule_id})")
            
            return jsonify({
                'success': True,
                'message': '스케줄이 생성되었습니다.',
                'schedule_id': schedule_id
            })
        else:
            return jsonify({
                'success': False,
                'error': '스케줄 생성에 실패했습니다.'
            }), 500
        
    except Exception as e:
        logger.error(f"스케줄 생성 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500
    finally:
        if 'db' in locals():
            db.disconnect()

@batch_schedule_bp.route('/api/batch-schedule/delete/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """배치 스케줄 삭제"""
    try:
        db = DatabaseManager()
        
        if not db.connect():
            return jsonify({
                'success': False,
                'error': '데이터베이스 연결 실패'
            }), 500
        
        # 스케줄 존재 확인
        query = "SELECT schedule_name FROM batch_schedules WHERE id = %s"
        result = db.fetch_one(query, (schedule_id,))
        
        if not result:
            return jsonify({
                'success': False,
                'error': f'스케줄 {schedule_id}를 찾을 수 없습니다.'
            }), 404
        
        schedule_name = result['schedule_name']
        
        # 스케줄 삭제
        delete_query = "DELETE FROM batch_schedules WHERE id = %s"
        
        if db.execute_query(delete_query, (schedule_id,)):
            # 스케줄러 재로드 (가능한 경우)
            if SCHEDULER_AVAILABLE:
                try:
                    scheduler = get_scheduler()
                    scheduler.reload_schedules()
                    logger.info(f"스케줄러 재로드 완료")
                except Exception as e:
                    logger.warning(f"스케줄러 재로드 실패: {e}")
            
            logger.info(f"스케줄 삭제: {schedule_name} (ID: {schedule_id})")
            
            return jsonify({
                'success': True,
                'message': f'스케줄 "{schedule_name}"이 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': '스케줄 삭제에 실패했습니다.'
            }), 500
        
    except Exception as e:
        logger.error(f"스케줄 삭제 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500
    finally:
        db.disconnect()

@batch_schedule_bp.route('/api/batch-schedule/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """스케줄러 상태 조회"""
    try:
        if not SCHEDULER_AVAILABLE:
            return jsonify({
                'success': True,
                'scheduler_available': False,
                'status': 'unavailable',
                'message': 'APScheduler를 사용할 수 없습니다.'
            })
        
        scheduler = get_scheduler()
        
        return jsonify({
            'success': True,
            'scheduler_available': True,
            'status': 'running' if scheduler.is_running else 'stopped',
            'scheduled_jobs': scheduler.get_scheduled_jobs()
        })
        
    except Exception as e:
        logger.error(f"스케줄러 상태 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄러 상태 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_schedule_bp.route('/api/batch-schedule/scheduler/start', methods=['POST'])
def start_scheduler():
    """스케줄러 시작"""
    try:
        if not SCHEDULER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'APScheduler를 사용할 수 없습니다.'
            }), 503
        
        scheduler = get_scheduler()
        
        if scheduler.start():
            return jsonify({
                'success': True,
                'message': '스케줄러가 시작되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': '스케줄러 시작에 실패했습니다.'
            }), 500
        
    except Exception as e:
        logger.error(f"스케줄러 시작 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄러 시작 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_schedule_bp.route('/api/batch-schedule/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """스케줄러 중지"""
    try:
        if not SCHEDULER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'APScheduler를 사용할 수 없습니다.'
            }), 503
        
        scheduler = get_scheduler()
        
        if scheduler.stop():
            return jsonify({
                'success': True,
                'message': '스케줄러가 중지되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': '스케줄러 중지에 실패했습니다.'
            }), 500
        
    except Exception as e:
        logger.error(f"스케줄러 중지 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄러 중지 중 오류가 발생했습니다: {str(e)}'
        }), 500

@batch_schedule_bp.route('/api/batch-schedule/scheduler/reload', methods=['POST'])
def reload_scheduler():
    """스케줄러 재로드"""
    try:
        if not SCHEDULER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'APScheduler를 사용할 수 없습니다.'
            }), 503
        
        scheduler = get_scheduler()
        
        if scheduler.reload_schedules():
            return jsonify({
                'success': True,
                'message': '스케줄러가 재로드되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': '스케줄러 재로드에 실패했습니다.'
            }), 500
        
    except Exception as e:
        logger.error(f"스케줄러 재로드 중 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'스케줄러 재로드 중 오류가 발생했습니다: {str(e)}'
        }), 500
