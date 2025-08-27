#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국 주식시장 개장/폐장 상태 판단 시스템
공휴일, 장 시간, 특별한 시장 상황을 고려하여 현재 시장 상태를 판단
"""

import datetime
from datetime import time, datetime, date
import pytz
from korean_holiday_manager import KoreanHolidayManager
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('market_status.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MarketStatusDetector:
    def __init__(self):
        """시장 상태 감지기 초기화"""
        self.holiday_manager = KoreanHolidayManager()
        self.korea_tz = pytz.timezone('Asia/Seoul')
        
        # 한국 주식시장 시간 설정
        self.market_open_time = time(9, 0)      # 09:00
        self.market_close_time = time(15, 30)   # 15:30
        self.break_start_time = time(11, 20)    # 11:20
        self.break_end_time = time(13, 0)       # 13:00
        
        # 특별한 시장 상황 (예: 코로나19, 긴급 상황 등)
        self.special_market_closures = [
            # 예시: 코로나19 관련 특별 휴장
            # date(2020, 3, 23),  # 2020년 3월 23일 특별 휴장
        ]
        
        logging.info("✅ 시장 상태 감지기 초기화 완료")
    
    def is_holiday(self, check_date=None):
        """공휴일 여부 확인"""
        if check_date is None:
            check_date = datetime.now(self.korea_tz).date()
        
        return self.holiday_manager.is_holiday(check_date)
    
    def is_weekend(self, check_date=None):
        """주말 여부 확인"""
        if check_date is None:
            check_date = datetime.now(self.korea_tz).date()
        
        return check_date.weekday() >= 5  # 5=토요일, 6=일요일
    
    def is_special_closure(self, check_date=None):
        """특별 휴장 여부 확인"""
        if check_date is None:
            check_date = datetime.now(self.korea_tz).date()
        
        return check_date in self.special_market_closures
    
    def is_market_open(self, check_datetime=None):
        """현재 시장이 열려있는지 확인"""
        if check_datetime is None:
            check_datetime = datetime.now(self.korea_tz)
        
        current_date = check_datetime.date()
        current_time = check_datetime.time()
        
        # 공휴일, 주말, 특별 휴장 확인
        if (self.is_holiday(current_date) or 
            self.is_weekend(current_date) or 
            self.is_special_closure(current_date)):
            return False, "휴장일"
        
        # 장 시간 확인
        if current_time < self.market_open_time:
            return False, "장 시작 전"
        elif current_time > self.market_close_time:
            return False, "장 마감 후"
        elif self.break_start_time <= current_time < self.break_end_time:
            return False, "점심시간"
        else:
            return True, "정상 거래시간"
    
    def get_market_status(self, check_datetime=None):
        """현재 시장 상태 상세 정보 반환"""
        if check_datetime is None:
            check_datetime = datetime.now(self.korea_tz)
        
        current_date = check_datetime.date()
        current_time = check_datetime.time()
        
        # 기본 정보
        status_info = {
            'datetime': check_datetime,
            'date': current_date,
            'time': current_time,
            'is_open': False,
            'status': '',
            'next_open': None,
            'next_close': None,
            'time_until_open': None,
            'time_until_close': None
        }
        
        # 현재 상태 확인
        is_open, status = self.is_market_open(check_datetime)
        status_info['is_open'] = is_open
        status_info['status'] = status
        
        # 다음 개장/폐장 시간 계산
        if not is_open:
            if current_time < self.market_open_time:
                # 오늘 장 시작 전
                next_open = datetime.combine(current_date, self.market_open_time)
                next_open = self.korea_tz.localize(next_open)
                status_info['next_open'] = next_open
                status_info['time_until_open'] = next_open - check_datetime
            elif current_time > self.market_close_time:
                # 오늘 장 마감 후
                next_open = self._get_next_trading_day_open(current_date)
                status_info['next_open'] = next_open
                status_info['time_until_open'] = next_open - check_datetime
            elif self.break_start_time <= current_time < self.break_end_time:
                # 점심시간
                next_open = datetime.combine(current_date, self.break_end_time)
                next_open = self.korea_tz.localize(next_open)
                status_info['next_open'] = next_open
                status_info['time_until_open'] = next_open - check_datetime
        else:
            # 현재 거래시간
            next_close = datetime.combine(current_date, self.market_close_time)
            next_close = self.korea_tz.localize(next_close)
            status_info['next_close'] = next_close
            status_info['time_until_close'] = next_close - check_datetime
        
        return status_info
    
    def _get_next_trading_day_open(self, from_date):
        """다음 거래일 개장 시간 계산"""
        next_date = from_date + datetime.timedelta(days=1)
        
        # 최대 30일까지 확인
        for _ in range(30):
            if (not self.is_holiday(next_date) and 
                not self.is_weekend(next_date) and 
                not self.is_special_closure(next_date)):
                next_datetime = datetime.combine(next_date, self.market_open_time)
                return self.korea_tz.localize(next_datetime)
            next_date += datetime.timedelta(days=1)
        
        # 30일 내에 거래일이 없으면 None 반환
        return None
    
    def get_trading_days_in_month(self, year, month):
        """특정 월의 거래일 목록 반환"""
        trading_days = []
        current_date = date(year, month, 1)
        
        while current_date.month == month:
            if (not self.is_holiday(current_date) and 
                not self.is_weekend(current_date) and 
                not self.is_special_closure(current_date)):
                trading_days.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        return trading_days
    
    def get_trading_days_in_range(self, start_date, end_date):
        """특정 기간의 거래일 목록 반환"""
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if (not self.is_holiday(current_date) and 
                not self.is_weekend(current_date) and 
                not self.is_special_closure(current_date)):
                trading_days.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        return trading_days
    
    def is_data_collection_time(self, check_datetime=None):
        """데이터 수집이 적절한 시간인지 확인"""
        if check_datetime is None:
            check_datetime = datetime.now(self.korea_tz)
        
        current_date = check_datetime.date()
        current_time = check_datetime.time()
        
        # 공휴일, 주말, 특별 휴장 확인
        if (self.is_holiday(current_date) or 
            self.is_weekend(current_date) or 
            self.is_special_closure(current_date)):
            return False, "휴장일"
        
        # 데이터 수집 권장 시간: 장 마감 후 1시간 ~ 다음날 장 시작 전
        if current_time >= time(15, 40) or current_time < time(8, 0):
            return True, "데이터 수집 권장 시간"
        elif current_time >= time(9, 0) and current_time <= time(15, 30):
            return False, "장 거래시간 (실시간 데이터 수집 가능)"
        else:
            return False, "비권장 시간"
    
    def get_market_hours_info(self):
        """시장 운영 시간 정보 반환"""
        return {
            'regular_open': self.market_open_time,
            'regular_close': self.market_close_time,
            'break_start': self.break_start_time,
            'break_end': self.break_end_time,
            'trading_hours': '09:00-15:30',
            'break_hours': '11:20-13:00',
            'total_trading_hours': '6시간 30분'
        }

def main():
    """테스트 함수"""
    print("🚀 시장 상태 감지기 테스트")
    print("="*50)
    
    detector = MarketStatusDetector()
    
    # 현재 시장 상태 확인
    current_status = detector.get_market_status()
    
    print(f"📅 현재 시간: {current_status['datetime']}")
    print(f"🔍 시장 상태: {'🟢 열림' if current_status['is_open'] else '🔴 닫힘'}")
    print(f"📊 상태 설명: {current_status['status']}")
    
    if current_status['next_open']:
        print(f"⏰ 다음 개장: {current_status['next_open']}")
        if current_status['time_until_open']:
            hours = current_status['time_until_open'].total_seconds() / 3600
            print(f"⏳ 개장까지: {hours:.1f}시간")
    
    if current_status['next_close']:
        print(f"⏰ 다음 폐장: {current_status['next_close']}")
        if current_status['time_until_close']:
            hours = current_status['time_until_close'].total_seconds() / 3600
            print(f"⏳ 폐장까지: {hours:.1f}시간")
    
    # 시장 운영 시간 정보
    hours_info = detector.get_market_hours_info()
    print(f"\n📋 시장 운영 시간:")
    print(f"   정규 거래: {hours_info['trading_hours']}")
    print(f"   점심시간: {hours_info['break_hours']}")
    print(f"   총 거래시간: {hours_info['total_trading_hours']}")
    
    # 데이터 수집 시간 확인
    is_collection_time, collection_status = detector.is_data_collection_time()
    print(f"\n📊 데이터 수집 시간: {'✅ 권장' if is_collection_time else '❌ 비권장'}")
    print(f"   상태: {collection_status}")

if __name__ == "__main__":
    main()
