#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄 시간 계산 유틸리티
크론 표현식의 다음 실행 시간을 정확히 계산하는 도구
"""

from datetime import datetime, timedelta
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

def validate_cron_expression(cron_expression):
    """크론 표현식 유효성 검사"""
    try:
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return False, "크론 표현식은 5개 부분으로 구성되어야 합니다 (분 시 일 월 요일)"
        
        # 각 부분 검증
        minute, hour, day, month, day_of_week = parts
        
        # 분 (0-59)
        if not _validate_time_part(minute, 0, 59):
            return False, "분은 0-59 범위여야 합니다"
        
        # 시 (0-23)
        if not _validate_time_part(hour, 0, 23):
            return False, "시는 0-23 범위여야 합니다"
        
        # 일 (1-31)
        if not _validate_time_part(day, 1, 31):
            return False, "일은 1-31 범위여야 합니다"
        
        # 월 (1-12)
        if not _validate_time_part(month, 1, 12):
            return False, "월은 1-12 범위여야 합니다"
        
        # 요일 (0-6, 0=일요일)
        if not _validate_time_part(day_of_week, 0, 6):
            return False, "요일은 0-6 범위여야 합니다 (0=일요일)"
        
        return True, "유효한 크론 표현식입니다"
        
    except Exception as e:
        return False, f"크론 표현식 검증 중 오류: {e}"

def _validate_time_part(part, min_val, max_val):
    """시간 부분 유효성 검사"""
    if part == '*':
        return True
    
    # 범위 처리 (예: 1-5)
    if '-' in part:
        try:
            start, end = part.split('-')
            return min_val <= int(start) <= max_val and min_val <= int(end) <= max_val
        except:
            return False
    
    # 쉼표 처리 (예: 1,3,5)
    if ',' in part:
        try:
            values = [int(x) for x in part.split(',')]
            return all(min_val <= val <= max_val for val in values)
        except:
            return False
    
    # 단일 값
    try:
        val = int(part)
        return min_val <= val <= max_val
    except:
        return False

def get_next_run_time(cron_expression, from_time=None):
    """다음 실행 시간 계산"""
    try:
        if from_time is None:
            from_time = datetime.now()
        
        # 크론 트리거 생성
        parts = cron_expression.strip().split()
        minute, hour, day, month, day_of_week = parts
        
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone='Asia/Seoul'
        )
        
        # 다음 실행 시간 계산
        next_run = trigger.get_next_fire_time(from_time, from_time)
        
        return next_run
        
    except Exception as e:
        logger.error(f"다음 실행 시간 계산 중 오류: {e}")
        return None

def is_schedule_in_future(cron_expression, check_time=None):
    """스케줄이 미래 시간인지 확인"""
    try:
        if check_time is None:
            check_time = datetime.now()
        
        next_run = get_next_run_time(cron_expression, check_time)
        
        if next_run is None:
            return False
        
        # 시간대 통일 (naive datetime로 변환)
        if next_run.tzinfo is not None:
            next_run = next_run.replace(tzinfo=None)
        if check_time.tzinfo is not None:
            check_time = check_time.replace(tzinfo=None)
        
        # 다음 실행 시간이 현재 시간보다 미래인지 확인
        return next_run > check_time
        
    except Exception as e:
        logger.error(f"스케줄 미래 시간 확인 중 오류: {e}")
        return False

def suggest_future_schedule(base_hour, base_minute, days_ahead=0):
    """미래 시간 스케줄 제안"""
    try:
        now = datetime.now()
        
        # 기본 시간 설정
        target_time = now.replace(hour=base_hour, minute=base_minute, second=0, microsecond=0)
        
        # 오늘 시간이 이미 지났으면 내일로 설정
        if target_time <= now:
            target_time += timedelta(days=1)
        
        # 추가 일수 적용
        if days_ahead > 0:
            target_time += timedelta(days=days_ahead)
        
        # 크론 표현식 생성
        cron_expression = f"{target_time.minute} {target_time.hour} * * *"
        
        return cron_expression, target_time
        
    except Exception as e:
        logger.error(f"미래 스케줄 제안 중 오류: {e}")
        return None, None

if __name__ == '__main__':
    # 테스트
    test_cron = "02 18 * * 1-5"
    print(f"크론 표현식: {test_cron}")
    
    valid, message = validate_cron_expression(test_cron)
    print(f"유효성: {valid}, 메시지: {message}")
    
    next_run = get_next_run_time(test_cron)
    print(f"다음 실행 시간: {next_run}")
    
    is_future = is_schedule_in_future(test_cron)
    print(f"미래 시간 여부: {is_future}")
