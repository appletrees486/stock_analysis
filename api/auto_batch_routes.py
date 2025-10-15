#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 배치 상태 모니터링 API
"""

from flask import Blueprint, jsonify, render_template, request
import logging
from datetime import datetime
from database_config import DatabaseManager

# 로깅 설정
logger = logging.getLogger(__name__)

# 블루프린트 생성
auto_batch_bp = Blueprint('auto_batch', __name__)

@auto_batch_bp.route('/auto-batch-status')
def auto_batch_status_page():
    """자동 배치 상태 모니터링 페이지"""
    logger.info("자동 배치 상태 모니터링 페이지 접속")
    return render_template('auto_batch_status.html')

@auto_batch_bp.route('/api/auto-batch/status', methods=['GET'])
def get_auto_batch_status():
    """자동 배치 현재 상태 조회"""
    try:
        db = DatabaseManager()
        
        if not db.connect():
            return jsonify({'error': 'DB 연결 실패'}), 500
        
        # 활성 스케줄 조회
        query = """
        SELECT 
            id,
            schedule_name,
            job_type,
            is_active,
            collection_completed,
            collection_completed_at,
            ranking_extracted,
            ranking_extracted_at,
            analysis_started,
            analysis_started_at,
            created_at,
            updated_at
        FROM batch_schedules 
        WHERE is_active = TRUE 
        AND job_type = 'DAILY_COLLECTION'
        ORDER BY id DESC
        LIMIT 1
        """
        
        schedule = db.fetch_one(query)
        
        if not schedule:
            return jsonify({
                'has_active_schedule': False,
                'message': '활성 스케줄이 없습니다'
            })
        
        # 최근 작업 이력 조회
        jobs_query = """
        SELECT 
            id,
            job_type,
            job_status,
            trading_type,
            target_date,
            batch_id,
            error_message,
            created_at
        FROM auto_analysis_jobs
        WHERE target_date = %s
        ORDER BY created_at DESC
        LIMIT 20
        """
        
        today = datetime.now().strftime('%Y-%m-%d')
        jobs = db.fetch_all(jobs_query, (today,))
        
        # 진행 상황 계산
        progress = {
            'collection': schedule.get('collection_completed', False),
            'ranking': schedule.get('ranking_extracted', False),
            'analysis': schedule.get('analysis_started', False)
        }
        
        # 전체 진행률 계산
        completed_steps = sum(progress.values())
        total_progress = int((completed_steps / 3) * 100)
        
        result = {
            'has_active_schedule': True,
            'schedule': {
                'id': schedule['id'],
                'name': schedule['schedule_name'],
                'job_type': schedule['job_type'],
                'created_at': schedule['created_at'].isoformat() if schedule['created_at'] else None,
                'updated_at': schedule['updated_at'].isoformat() if schedule['updated_at'] else None
            },
            'progress': progress,
            'timestamps': {
                'collection_completed_at': schedule['collection_completed_at'].isoformat() if schedule['collection_completed_at'] else None,
                'ranking_extracted_at': schedule['ranking_extracted_at'].isoformat() if schedule['ranking_extracted_at'] else None,
                'analysis_started_at': schedule['analysis_started_at'].isoformat() if schedule['analysis_started_at'] else None
            },
            'total_progress': total_progress,
            'jobs': [
                {
                    'id': job['id'],
                    'job_type': job['job_type'],
                    'job_status': job['job_status'],
                    'trading_type': job['trading_type'],
                    'target_date': job['target_date'],
                    'batch_id': job['batch_id'],
                    'error_message': job['error_message'],
                    'created_at': job['created_at'].isoformat() if job['created_at'] else None
                }
                for job in jobs
            ]
        }
        
        db.disconnect()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"자동 배치 상태 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@auto_batch_bp.route('/api/auto-batch/jobs', methods=['GET'])
def get_auto_batch_jobs():
    """자동 배치 작업 이력 조회"""
    try:
        db = DatabaseManager()
        
        if not db.connect():
            return jsonify({'error': 'DB 연결 실패'}), 500
        
        # 날짜 파라미터 (기본값: 오늘)
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # 작업 이력 조회
        query = """
        SELECT 
            id,
            job_type,
            job_status,
            trading_type,
            target_date,
            stock_list_path,
            batch_id,
            error_message,
            created_at,
            updated_at
        FROM auto_analysis_jobs
        WHERE target_date = %s
        ORDER BY created_at DESC
        """
        
        jobs = db.fetch_all(query, (date_str,))
        
        result = {
            'date': date_str,
            'total_count': len(jobs),
            'jobs': [
                {
                    'id': job['id'],
                    'job_type': job['job_type'],
                    'job_status': job['job_status'],
                    'trading_type': job['trading_type'],
                    'target_date': job['target_date'],
                    'stock_list_path': job['stock_list_path'],
                    'batch_id': job['batch_id'],
                    'error_message': job['error_message'],
                    'created_at': job['created_at'].isoformat() if job['created_at'] else None,
                    'updated_at': job['updated_at'].isoformat() if job['updated_at'] else None
                }
                for job in jobs
            ]
        }
        
        db.disconnect()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"자동 배치 작업 이력 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@auto_batch_bp.route('/api/auto-batch/history', methods=['GET'])
def get_auto_batch_history():
    """자동 배치 전체 이력 조회"""
    try:
        db = DatabaseManager()
        
        if not db.connect():
            return jsonify({'error': 'DB 연결 실패'}), 500
        
        # 스케줄 이력 조회
        query = """
        SELECT 
            id,
            schedule_name,
            job_type,
            is_active,
            collection_completed,
            ranking_extracted,
            analysis_started,
            created_at,
            updated_at
        FROM batch_schedules 
        WHERE job_type = 'DAILY_COLLECTION'
        ORDER BY id DESC
        LIMIT 30
        """
        
        schedules = db.fetch_all(query)
        
        result = {
            'total_count': len(schedules),
            'schedules': [
                {
                    'id': schedule['id'],
                    'name': schedule['schedule_name'],
                    'job_type': schedule['job_type'],
                    'is_active': schedule['is_active'],
                    'collection_completed': schedule['collection_completed'],
                    'ranking_extracted': schedule['ranking_extracted'],
                    'analysis_started': schedule['analysis_started'],
                    'created_at': schedule['created_at'].isoformat() if schedule['created_at'] else None,
                    'updated_at': schedule['updated_at'].isoformat() if schedule['updated_at'] else None
                }
                for schedule in schedules
            ]
        }
        
        db.disconnect()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"자동 배치 이력 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

