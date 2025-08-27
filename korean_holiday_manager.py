#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국 공휴일 관리 시스템 (API key 불필요)
"""

from datetime import datetime, date, timedelta
import calendar
import json
import os
from typing import Dict, List, Tuple, Optional

class KoreanHolidayManager:
    """API key 없이 한국 공휴일 관리"""
    
    def __init__(self):
        self.holidays = self._load_comprehensive_holidays()
        self.cache_file = "korean_holidays_cache.json"
        self._load_cache()
    
    def _load_comprehensive_holidays(self) -> Dict[int, List[Tuple[int, int, str]]]:
        """종합 공휴일 정보 로드 (2020-2030년)"""
        holidays = {}
        
        # 2020-2030년 고정 공휴일
        for year in range(2020, 2031):
            year_holidays = []
            
            # 1. 고정 공휴일 (월, 일, 이름)
            fixed_holidays = [
                (1, 1, "신정"),
                (3, 1, "삼일절"),
                (5, 5, "어린이날"),
                (6, 6, "현충일"),
                (8, 15, "광복절"),
                (10, 3, "개천절"),
                (10, 9, "한글날"),
                (12, 25, "크리스마스")
            ]
            
            # 2. 음력 공휴일 (대략적인 날짜)
            lunar_holidays = self._get_lunar_holidays(year)
            
            # 3. 대체공휴일 규칙 적용
            substitute_holidays = self._get_substitute_holidays(year)
            
            # 4. 임시공휴일 (대통령 선거 등)
            temporary_holidays = self._get_temporary_holidays(year)
            
            # 모든 공휴일 통합
            all_holidays = fixed_holidays + lunar_holidays + substitute_holidays + temporary_holidays
            
            # 중복 제거 및 정렬
            unique_holidays = list(set(all_holidays))
            unique_holidays.sort(key=lambda x: (x[0], x[1]))
            
            holidays[year] = unique_holidays
        
        return holidays
    
    def _get_lunar_holidays(self, year: int) -> List[Tuple[int, int, str]]:
        """음력 공휴일 (대략적인 날짜)"""
        lunar_holidays = []
        
        # 설날 (음력 1월 1일 전후)
        # 대략적인 양력 날짜 계산 (정확하지 않음)
        if year == 2020:
            lunar_holidays.extend([(1, 24, "설날"), (1, 25, "설날"), (1, 26, "설날")])
        elif year == 2021:
            lunar_holidays.extend([(2, 11, "설날"), (2, 12, "설날"), (2, 13, "설날")])
        elif year == 2022:
            lunar_holidays.extend([(1, 31, "설날"), (2, 1, "설날"), (2, 2, "설날")])
        elif year == 2023:
            lunar_holidays.extend([(1, 21, "설날"), (1, 22, "설날"), (1, 23, "설날")])
        elif year == 2024:
            lunar_holidays.extend([(2, 9, "설날"), (2, 10, "설날"), (2, 11, "설날")])
        elif year == 2025:
            lunar_holidays.extend([(1, 28, "설날"), (1, 29, "설날"), (1, 30, "설날")])
        elif year == 2026:
            lunar_holidays.extend([(2, 16, "설날"), (2, 17, "설날"), (2, 18, "설날")])
        elif year == 2027:
            lunar_holidays.extend([(2, 5, "설날"), (2, 6, "설날"), (2, 7, "설날")])
        elif year == 2028:
            lunar_holidays.extend([(1, 25, "설날"), (1, 26, "설날"), (1, 27, "설날")])
        elif year == 2029:
            lunar_holidays.extend([(2, 12, "설날"), (2, 13, "설날"), (2, 14, "설날")])
        elif year == 2030:
            lunar_holidays.extend([(2, 2, "설날"), (2, 3, "설날"), (2, 4, "설날")])
        
        # 부처님 오신 날 (음력 4월 8일)
        if year == 2020:
            lunar_holidays.append((4, 30, "부처님오신날"))
        elif year == 2021:
            lunar_holidays.append((5, 19, "부처님오신날"))
        elif year == 2022:
            lunar_holidays.append((5, 8, "부처님오신날"))
        elif year == 2023:
            lunar_holidays.append((5, 27, "부처님오신날"))
        elif year == 2024:
            lunar_holidays.append((5, 15, "부처님오신날"))
        elif year == 2025:
            lunar_holidays.append((5, 4, "부처님오신날"))
        elif year == 2026:
            lunar_holidays.append((5, 23, "부처님오신날"))
        elif year == 2027:
            lunar_holidays.append((5, 12, "부처님오신날"))
        elif year == 2028:
            lunar_holidays.append((5, 1, "부처님오신날"))
        elif year == 2029:
            lunar_holidays.append((5, 20, "부처님오신날"))
        elif year == 2030:
            lunar_holidays.append((5, 9, "부처님오신날"))
        
        # 추석 (음력 8월 15일 전후)
        if year == 2020:
            lunar_holidays.extend([(9, 30, "추석"), (10, 1, "추석"), (10, 2, "추석")])
        elif year == 2021:
            lunar_holidays.extend([(9, 20, "추석"), (9, 21, "추석"), (9, 22, "추석")])
        elif year == 2022:
            lunar_holidays.extend([(9, 9, "추석"), (9, 10, "추석"), (9, 11, "추석")])
        elif year == 2023:
            lunar_holidays.extend([(9, 28, "추석"), (9, 29, "추석"), (9, 30, "추석")])
        elif year == 2024:
            lunar_holidays.extend([(10, 16, "추석"), (10, 17, "추석"), (10, 18, "추석")])
        elif year == 2025:
            lunar_holidays.extend([(10, 5, "추석"), (10, 6, "추석"), (10, 7, "추석")])
        elif year == 2026:
            lunar_holidays.extend([(9, 24, "추석"), (9, 25, "추석"), (9, 26, "추석")])
        elif year == 2027:
            lunar_holidays.extend([(10, 13, "추석"), (10, 14, "추석"), (10, 15, "추석")])
        elif year == 2028:
            lunar_holidays.extend([(10, 2, "추석"), (10, 3, "추석"), (10, 4, "추석")])
        elif year == 2029:
            lunar_holidays.extend([(9, 21, "추석"), (9, 22, "추석"), (9, 23, "추석")])
        elif year == 2030:
            lunar_holidays.extend([(10, 10, "추석"), (10, 11, "추석"), (10, 12, "추석")])
        
        return lunar_holidays
    
    def _get_substitute_holidays(self, year: int) -> List[Tuple[int, int, str]]:
        """대체공휴일 규칙 적용"""
        substitute_holidays = []
        
        # 대체공휴일 규칙: 공휴일이 주말이나 다른 공휴일과 겹치면 다음 평일을 공휴일로 지정
        # 실제로는 매년 다르지만, 주요 공휴일에 대해서만 적용
        
        # 어린이날이 주말인 경우
        children_day = date(year, 5, 5)
        if children_day.weekday() >= 5:  # 토요일(5) 또는 일요일(6)
            # 다음 평일 찾기
            next_weekday = children_day + timedelta(days=1)
            while next_weekday.weekday() >= 5:
                next_weekday += timedelta(days=1)
            substitute_holidays.append((next_weekday.month, next_weekday.day, "대체공휴일"))
        
        return substitute_holidays
    
    def _get_temporary_holidays(self, year: int) -> List[Tuple[int, int, str]]:
        """임시공휴일 (대통령 선거 등)"""
        temporary_holidays = []
        
        # 대통령 선거일 (4년마다)
        if year in [2022, 2026, 2030]:
            temporary_holidays.append((3, 9, "대통령선거일"))
        
        # 국회의원 선거일 (4년마다)
        if year in [2024, 2028]:
            temporary_holidays.append((4, 10, "국회의원선거일"))
        
        # 지방선거일 (4년마다)
        if year in [2022, 2026, 2030]:
            temporary_holidays.append((6, 1, "지방선거일"))
        
        return temporary_holidays
    
    def _load_cache(self):
        """캐시 파일에서 공휴일 정보 로드"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    # 캐시된 데이터가 현재 연도와 일치하는지 확인
                    current_year = datetime.now().year
                    if str(current_year) in cached_data:
                        self.holidays.update(cached_data)
            except Exception as e:
                print(f"캐시 로드 실패: {e}")
    
    def _save_cache(self):
        """공휴일 정보를 캐시 파일에 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.holidays, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
    
    def is_holiday(self, check_date: date) -> bool:
        """특정 날짜가 공휴일인지 확인"""
        year = check_date.year
        month = check_date.month
        day = check_date.day
        
        # 해당 연도의 공휴일 목록 확인
        if year in self.holidays:
            for h_month, h_day, h_name in self.holidays[year]:
                if h_month == month and h_day == day:
                    return True
        
        # 주말 확인
        if check_date.weekday() >= 5:  # 토요일(5) 또는 일요일(6)
            return True
        
        return False
    
    def is_trading_day(self, check_date: date) -> bool:
        """특정 날짜가 거래일인지 확인 (공휴일이 아닌 평일)"""
        return not self.is_holiday(check_date)
    
    def get_next_trading_day(self, from_date: date) -> date:
        """특정 날짜 이후의 다음 거래일 반환"""
        next_date = from_date + timedelta(days=1)
        while not self.is_trading_day(next_date):
            next_date += timedelta(days=1)
        return next_date
    
    def get_previous_trading_day(self, from_date: date) -> date:
        """특정 날짜 이전의 이전 거래일 반환"""
        prev_date = from_date - timedelta(days=1)
        while not self.is_trading_day(prev_date):
            prev_date -= timedelta(days=1)
        return prev_date
    
    def get_trading_days_in_month(self, year: int, month: int) -> List[date]:
        """특정 월의 모든 거래일 반환"""
        trading_days = []
        current_date = date(year, month, 1)
        
        while current_date.month == month:
            if self.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days
    
    def get_trading_days_in_year(self, year: int) -> List[date]:
        """특정 연도의 모든 거래일 반환"""
        trading_days = []
        current_date = date(year, 1, 1)
        
        while current_date.year == year:
            if self.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days
    
    def get_holiday_info(self, check_date: date) -> Optional[str]:
        """특정 날짜의 공휴일 정보 반환"""
        year = check_date.year
        month = check_date.month
        day = check_date.day
        
        if year in self.holidays:
            for h_month, h_day, h_name in self.holidays[year]:
                if h_month == month and h_day == day:
                    return h_name
        
        # 주말인 경우
        if check_date.weekday() >= 5:
            return "주말"
        
        return None
    
    def update_holidays(self, year: int, additional_holidays: List[Tuple[int, int, str]]):
        """특정 연도에 추가 공휴일 정보 업데이트"""
        if year not in self.holidays:
            self.holidays[year] = []
        
        self.holidays[year].extend(additional_holidays)
        self.holidays[year] = list(set(self.holidays[year]))  # 중복 제거
        self.holidays[year].sort(key=lambda x: (x[0], x[1]))  # 정렬
        
        self._save_cache()  # 캐시 업데이트
    
    def get_market_status(self, collection_time: datetime) -> str:
        """수집 시점 기준으로 장 상태 판단"""
        # 한국 시간으로 변환 (UTC+9)
        korea_time = collection_time
        
        # 거래일 여부 확인
        if not self.is_trading_day(korea_time.date()):
            return "non_trading_day"
        
        # 시간대별 판단
        hour = korea_time.hour
        minute = korea_time.minute
        
        if hour < 9:
            return "before_market_open"
        elif 9 <= hour < 15:
            return "during_market"
        elif hour == 15 and minute < 30:
            return "near_market_close"
        elif hour == 15 and minute >= 30:
            return "after_market_close"
        else:
            return "after_market_close"
    
    def get_market_status_description(self, status: str) -> str:
        """장 상태에 대한 설명 반환"""
        status_descriptions = {
            "non_trading_day": "거래일 아님 (주말/공휴일)",
            "before_market_open": "장 시작 전",
            "during_market": "장중",
            "near_market_close": "장 마감 직전",
            "after_market_close": "장 마감 후"
        }
        return status_descriptions.get(status, "알 수 없음")


# 테스트 함수
def test_holiday_manager():
    """공휴일 관리자 테스트"""
    print("🇰🇷 한국 공휴일 관리자 테스트")
    print("="*50)
    
    manager = KoreanHolidayManager()
    
    # 오늘 날짜 확인
    today = date.today()
    print(f"📅 오늘: {today.strftime('%Y-%m-%d')} ({today.strftime('%A')})")
    print(f"   공휴일 여부: {'예' if manager.is_holiday(today) else '아니오'}")
    print(f"   거래일 여부: {'예' if manager.is_trading_day(today) else '아니오'}")
    
    holiday_info = manager.get_holiday_info(today)
    if holiday_info:
        print(f"   공휴일 정보: {holiday_info}")
    
    # 다음 거래일 확인
    next_trading = manager.get_next_trading_day(today)
    print(f"📈 다음 거래일: {next_trading.strftime('%Y-%m-%d')} ({next_trading.strftime('%A')})")
    
    # 이전 거래일 확인
    prev_trading = manager.get_previous_trading_day(today)
    print(f"📉 이전 거래일: {prev_trading.strftime('%Y-%m-%d')} ({prev_trading.strftime('%A')})")
    
    # 이번 달 거래일 수
    current_month_trading = manager.get_trading_days_in_month(today.year, today.month)
    print(f"📊 이번 달 거래일 수: {len(current_month_trading)}일")
    
    # 이번 해 거래일 수
    current_year_trading = manager.get_trading_days_in_year(today.year)
    print(f"📊 이번 해 거래일 수: {len(current_year_trading)}일")
    
    # 특정 날짜 테스트
    test_dates = [
        date(2025, 1, 1),   # 신정
        date(2025, 5, 5),   # 어린이날
        date(2025, 8, 15),  # 광복절
        date(2025, 12, 25), # 크리스마스
    ]
    
    print(f"\n🔍 특정 날짜 공휴일 테스트:")
    for test_date in test_dates:
        is_holiday = manager.is_holiday(test_date)
        holiday_name = manager.get_holiday_info(test_date)
        print(f"   {test_date.strftime('%Y-%m-%d')}: {'공휴일' if is_holiday else '거래일'} - {holiday_name}")


if __name__ == "__main__":
    test_holiday_manager()
