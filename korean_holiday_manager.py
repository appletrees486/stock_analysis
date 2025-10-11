#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국 공휴일 관리 시스템 - 단순화 버전
복잡한 대체공휴일 로직 제거, 명시적 데이터만 사용
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional

class KoreanHolidayManager:
    """단순화된 한국 공휴일 관리 - 명시적 데이터만"""
    
    def __init__(self):
        self.holidays = self._load_holidays()
    
    def _load_holidays(self) -> Dict[int, List[Tuple[int, int, str]]]:
        """명시적 공휴일 데이터만 로드 (2024-2026년)"""
        holidays = {}
        
        # 2024년
        holidays[2024] = [
            # 고정 공휴일
            (1, 1, "신정"),
            (3, 1, "삼일절"),
            (5, 5, "어린이날"),
            (6, 6, "현충일"),
            (8, 15, "광복절"),
            (10, 3, "개천절"),
            (10, 9, "한글날"),
            (12, 25, "크리스마스"),
            # 음력 공휴일
            (2, 9, "설날"),
            (2, 10, "설날"),
            (2, 11, "설날"),
            (2, 12, "대체공휴일"),  # 설날 대체
            (4, 10, "국회의원선거일"),
            (5, 15, "부처님오신날"),
            (9, 16, "추석"),
            (9, 17, "추석"),
            (9, 18, "추석"),
        ]
        
        # 2025년
        holidays[2025] = [
            # 고정 공휴일
            (1, 1, "신정"),
            (3, 1, "삼일절"),
            (5, 5, "어린이날"),
            (6, 6, "현충일"),
            (8, 15, "광복절"),
            (10, 3, "개천절"),
            (10, 9, "한글날"),
            (12, 25, "크리스마스"),
            # 음력 공휴일
            (1, 28, "설날"),
            (1, 29, "설날"),
            (1, 30, "설날"),
            (5, 5, "부처님오신날"),  # 어린이날과 겹침
            (10, 5, "추석"),
            (10, 6, "추석"),
            (10, 7, "추석"),
            (10, 8, "대체공휴일"),  # 추석 대체 (명시적 추가!)
        ]
        
        # 2026년 (미래 계획)
        holidays[2026] = [
            # 고정 공휴일
            (1, 1, "신정"),
            (3, 1, "삼일절"),
            (5, 5, "어린이날"),
            (6, 6, "현충일"),
            (8, 15, "광복절"),
            (10, 3, "개천절"),
            (10, 9, "한글날"),
            (12, 25, "크리스마스"),
            # 음력 공휴일 (예상)
            (2, 16, "설날"),
            (2, 17, "설날"),
            (2, 18, "설날"),
            (5, 23, "부처님오신날"),
            (9, 24, "추석"),
            (9, 25, "추석"),
            (9, 26, "추석"),
        ]
        
        return holidays
    
    def is_holiday(self, check_date: date) -> bool:
        """특정 날짜가 공휴일인지 확인"""
        # 1. 주말 체크 (빠른 경로)
        if check_date.weekday() >= 5:  # 토요일(5) 또는 일요일(6)
            return True
        
        # 2. 명시적 공휴일 체크
        year = check_date.year
        month = check_date.month
        day = check_date.day
        
        if year in self.holidays:
            for h_month, h_day, h_name in self.holidays[year]:
                if h_month == month and h_day == day:
                    return True
        
        return False
    
    def is_trading_day(self, check_date: date) -> bool:
        """특정 날짜가 거래일인지 확인"""
        return not self.is_holiday(check_date)
    
    def get_holiday_info(self, check_date: date) -> Optional[str]:
        """특정 날짜의 공휴일 정보 반환"""
        # 주말 체크
        if check_date.weekday() >= 5:
            return "주말"
        
        # 명시적 공휴일 체크
        year = check_date.year
        month = check_date.month
        day = check_date.day
        
        if year in self.holidays:
            for h_month, h_day, h_name in self.holidays[year]:
                if h_month == month and h_day == day:
                    return h_name
        
        return None
    
    def get_next_trading_day(self, from_date: date) -> date:
        """다음 거래일 반환"""
        next_date = from_date + timedelta(days=1)
        while not self.is_trading_day(next_date):
            next_date += timedelta(days=1)
        return next_date
    
    def get_previous_trading_day(self, from_date: date) -> date:
        """이전 거래일 반환"""
        prev_date = from_date - timedelta(days=1)
        while not self.is_trading_day(prev_date):
            prev_date -= timedelta(days=1)
        return prev_date
    
    def get_market_status(self, collection_time: datetime) -> str:
        """수집 시점 기준으로 장 상태 판단"""
        # 거래일 여부 확인
        if not self.is_trading_day(collection_time.date()):
            return "non_trading_day"
        
        # 시간대별 판단
        hour = collection_time.hour
        minute = collection_time.minute
        
        if hour < 9:
            return "before_market_open"
        elif 9 <= hour < 15:
            return "during_market"
        elif hour == 15 and minute < 30:
            return "near_market_close"
        else:
            return "after_market_close"


# 테스트 함수
def test_simple_manager():
    """단순화된 매니저 테스트"""
    print("\n" + "="*60)
    print("단순화 버전 - 2025년 10월 테스트")
    print("="*60)
    
    manager = KoreanHolidayManager()
    
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    
    print("\n2025년 10월 3일~10일:")
    print("-"*60)
    
    for day in range(3, 11):
        test_date = date(2025, 10, day)
        weekday_name = weekdays[test_date.weekday()]
        is_trading = manager.is_trading_day(test_date)
        holiday_info = manager.get_holiday_info(test_date)
        
        status = "[거래일]" if is_trading else "[휴장일]"
        info = holiday_info if holiday_info else "정상거래일"
        
        print(f"{test_date.strftime('%Y-%m-%d')} ({weekday_name}): {status} - {info}")
    
    print("\n" + "="*60)
    print("결과: 10월 8일 대체공휴일이 명시적으로 처리됨!")
    print("="*60)


if __name__ == "__main__":
    test_simple_manager()

