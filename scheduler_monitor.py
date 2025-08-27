#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 스케줄러 모니터링 도구
실시간으로 스케줄러 상태와 작업 진행 상황을 모니터링
"""

import time
import os
import sys
from datetime import datetime
from database_config import DatabaseManager
from batch_scheduler import get_scheduler
from collection_job_manager import CollectionJobManager

def clear_screen():
    """화면 지우기"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_scheduler_status():
    """스케줄러 상태 조회"""
    try:
        scheduler = get_scheduler()
        return {
            'is_running': scheduler.is_running,
            'scheduled_jobs': scheduler.get_scheduled_jobs() if scheduler.is_running else []
        }
    except Exception as e:
        return {
            'is_running': False,
            'scheduled_jobs': [],
            'error': str(e)
        }

def get_running_jobs():
    """실행 중인 작업 조회"""
    try:
        job_manager = CollectionJobManager()
        running_job = job_manager.get_running_job()
        return running_job
    except Exception as e:
        return None

def get_recent_jobs():
    """최근 작업 이력 조회"""
    try:
        job_manager = CollectionJobManager()
        return job_manager.get_recent_jobs(limit=5)
    except Exception as e:
        return []

def get_schedule_info():
    """스케줄 정보 조회"""
    try:
        db = DatabaseManager()
        if not db.connect():
            return []
        
        query = """
        SELECT id, schedule_name, job_type, cron_expression, is_active, 
               last_run, next_run
        FROM batch_schedules 
        WHERE is_active = TRUE
        ORDER BY created_at DESC
        """
        
        schedules = db.fetch_all(query)
        db.disconnect()
        return schedules
    except Exception as e:
        return []

def format_time(dt):
    """시간 포맷팅"""
    if dt is None:
        return "없음"
    if isinstance(dt, str):
        return dt
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def display_status():
    """상태 표시"""
    clear_screen()
    
    print("🔍 자동 스케줄러 모니터링 대시보드")
    print("=" * 80)
    print(f"⏰ 현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 스케줄러 상태
    scheduler_status = get_scheduler_status()
    status_icon = "🟢" if scheduler_status['is_running'] else "🔴"
    print(f"📡 스케줄러 상태: {status_icon} {'실행 중' if scheduler_status['is_running'] else '중지됨'}")
    
    if 'error' in scheduler_status:
        print(f"❌ 오류: {scheduler_status['error']}")
    
    print()
    
    # 활성 스케줄 목록
    print("📅 활성 스케줄 목록")
    print("-" * 50)
    
    schedules = get_schedule_info()
    if schedules:
        for schedule in schedules:
            print(f"🔹 {schedule['schedule_name']} ({schedule['job_type']})")
            print(f"   크론: {schedule['cron_expression']}")
            print(f"   마지막 실행: {format_time(schedule['last_run'])}")
            print()
    else:
        print("   ℹ️ 활성 스케줄이 없습니다")
    
    # 등록된 APScheduler 작업
    if scheduler_status['is_running'] and scheduler_status['scheduled_jobs']:
        print("⏰ 등록된 스케줄 작업")
        print("-" * 50)
        
        for job in scheduler_status['scheduled_jobs']:
            next_run = job.get('next_run', 'None')
            if next_run and next_run != 'None':
                try:
                    next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                    next_run = next_run_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            print(f"🔸 {job.get('name', 'Unknown')}")
            print(f"   다음 실행: {next_run}")
            print()
    
    # 실행 중인 작업
    print("🚀 실행 중인 작업")
    print("-" * 50)
    
    running_job = get_running_jobs()
    if running_job:
        print(f"🔄 Job ID: {running_job['id']}")
        print(f"   유형: {running_job['job_type']}")
        print(f"   시작 시간: {format_time(running_job['start_time'])}")
        
        if running_job.get('progress_total') and running_job.get('progress_processed'):
            progress = (running_job['progress_processed'] / running_job['progress_total']) * 100
            print(f"   진행률: {running_job['progress_processed']}/{running_job['progress_total']} ({progress:.1f}%)")
    else:
        print("   ℹ️ 실행 중인 작업이 없습니다")
    
    print()
    
    # 최근 작업 이력
    print("📋 최근 작업 이력 (최근 5개)")
    print("-" * 50)
    
    recent_jobs = get_recent_jobs()
    if recent_jobs:
        for job in recent_jobs:
            status_icon = {
                'COMPLETED': '✅',
                'FAILED': '❌',
                'RUNNING': '🔄',
                'PENDING': '⏳',
                'CANCELLED': '🚫'
            }.get(job['status'], '❓')
            
            duration = f"{job['duration']}초" if job['duration'] else "측정 안됨"
            
            print(f"{status_icon} Job ID: {job['id']} ({job['job_type']})")
            print(f"   상태: {job['status']}, 실행 시간: {duration}")
            
            if job['stats']['success'] or job['stats']['failed']:
                print(f"   결과: 성공 {job['stats']['success']}, 실패 {job['stats']['failed']}")
            
            print()
    else:
        print("   ℹ️ 최근 작업 이력이 없습니다")
    
    print("-" * 80)
    print("💡 Ctrl+C를 눌러 모니터링을 종료하세요")
    print("🔄 5초마다 자동 업데이트됩니다")

def main():
    """메인 함수"""
    print("🚀 자동 스케줄러 모니터링 시작")
    print("몇 초 후 대시보드가 표시됩니다...")
    
    try:
        while True:
            display_status()
            time.sleep(5)  # 5초마다 업데이트
            
    except KeyboardInterrupt:
        print("\n\n👋 모니터링을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 모니터링 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
