#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주차 계산 전용 모듈 (ISO 8601 표준 기반)
모든 파일에서 통일된 주차 계산 방식을 제공합니다.
"""

from datetime import datetime, date, timedelta
from typing import Tuple, Optional, Union
import re


class WeekCalculator:
    """ISO 8601 표준을 기반으로 한 주차 계산 클래스"""
    
    @staticmethod
    def get_week_number(date_obj: Union[datetime, date]) -> Tuple[int, int]:
        """
        주어진 날짜의 ISO 8601 주차 번호를 반환
        
        Args:
            date_obj: 계산할 날짜 (datetime 또는 date 객체)
            
        Returns:
            Tuple[int, int]: (연도, 주차번호)
            
        Example:
            >>> WeekCalculator.get_week_number(datetime(2025, 1, 1))
            (2025, 1)
        """
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        year, week, _ = date_obj.isocalendar()
        return year, week
    
    @staticmethod
    def get_week_number_string(date_obj: Union[datetime, date], format_str: str = "YYYY년 W주차") -> str:
        """
        주어진 날짜의 주차를 문자열로 반환
        
        Args:
            date_obj: 계산할 날짜
            format_str: 출력 형식 ("YYYY년 W주차", "YYYY-WW" 등)
            
        Returns:
            str: 포맷된 주차 문자열
            
        Example:
            >>> WeekCalculator.get_week_number_string(datetime(2025, 1, 1))
            "2025년 1주차"
        """
        year, week = WeekCalculator.get_week_number(date_obj)
        
        if format_str == "YYYY년 W주차":
            return f"{year}년 {week}주차"
        elif format_str == "YYYY-WW":
            return f"{year}-W{week:02d}"
        elif format_str == "YYYY년 WW주차":
            return f"{year}년 {week:02d}주차"
        else:
            return format_str.replace("YYYY", str(year)).replace("W", str(week))
    
    @staticmethod
    def get_week_start_date(year: int, week: int) -> date:
        """
        주어진 연도와 주차의 주 시작일(월요일)을 반환
        
        Args:
            year: 연도
            week: 주차 번호
            
        Returns:
            date: 해당 주의 월요일 날짜
            
        Example:
            >>> WeekCalculator.get_week_start_date(2025, 1)
            datetime.date(2024, 12, 30)
        """
        # ISO 8601: 1월 4일이 속한 주의 월요일을 1주차로 계산
        jan_4 = date(year, 1, 4)
        jan_4_weekday = jan_4.weekday()  # 0=월요일, 6=일요일
        
        # 1월 4일이 속한 주의 월요일 계산
        week_start = jan_4 - timedelta(days=jan_4_weekday)
        
        # 요청된 주차의 월요일 계산
        target_week_start = week_start + timedelta(weeks=week - 1)
        
        return target_week_start
    
    @staticmethod
    def get_week_end_date(year: int, week: int) -> date:
        """
        주어진 연도와 주차의 주 종료일(일요일)을 반환
        
        Args:
            year: 연도
            week: 주차 번호
            
        Returns:
            date: 해당 주의 일요일 날짜
        """
        week_start = WeekCalculator.get_week_start_date(year, week)
        return week_start + timedelta(days=6)
    
    @staticmethod
    def get_week_period(year: int, week: int, format_str: str = "YYYY-MM-DD ~ YYYY-MM-DD") -> str:
        """
        주어진 연도와 주차의 주 기간을 문자열로 반환
        
        Args:
            year: 연도
            week: 주차 번호
            format_str: 출력 형식
            
        Returns:
            str: 포맷된 주 기간 문자열
            
        Example:
            >>> WeekCalculator.get_week_period(2025, 1)
            "2024-12-30 ~ 2025-01-05"
        """
        week_start = WeekCalculator.get_week_start_date(year, week)
        week_end = WeekCalculator.get_week_end_date(year, week)
        
        if format_str == "YYYY-MM-DD ~ YYYY-MM-DD":
            return f"{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}"
        elif format_str == "M월 D일 ~ M월 D일":
            return f"{week_start.month}월 {week_start.day}일 ~ {week_end.month}월 {week_end.day}일"
        else:
            return format_str.replace("START", week_start.strftime('%Y-%m-%d')).replace("END", week_end.strftime('%Y-%m-%d'))
    
    @staticmethod
    def parse_week_string(week_string: str) -> Optional[Tuple[int, int]]:
        """
        주차 문자열을 파싱하여 연도와 주차 번호를 반환
        
        Args:
            week_string: 주차 문자열 ("2025년 1주차", "2025-W01" 등)
            
        Returns:
            Optional[Tuple[int, int]]: (연도, 주차번호) 또는 None
            
        Example:
            >>> WeekCalculator.parse_week_string("2025년 1주차")
            (2025, 1)
        """
        # 패턴 1: "2025년 1주차" 또는 "2025년 01주차"
        pattern1 = r'(\d{4})년\s*(\d{1,2})주차'
        match1 = re.search(pattern1, week_string)
        if match1:
            year = int(match1.group(1))
            week = int(match1.group(2))
            return year, week
        
        # 패턴 2: "2025-W01" 또는 "2025-W1"
        pattern2 = r'(\d{4})-W(\d{1,2})'
        match2 = re.search(pattern2, week_string)
        if match2:
            year = int(match2.group(1))
            week = int(match2.group(2))
            return year, week
        
        # 패턴 3: "2025년 1월 1주차" (월+주차)
        pattern3 = r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})주차'
        match3 = re.search(pattern3, week_string)
        if match3:
            year = int(match3.group(1))
            month = int(match3.group(2))
            week_in_month = int(match3.group(3))
            
            # 해당 월의 첫 번째 날짜로 주차 계산
            first_day = date(year, month, 1)
            _, first_week = WeekCalculator.get_week_number(first_day)
            week = first_week + week_in_month - 1
            return year, week
        
        return None
    
    @staticmethod
    def get_current_week() -> Tuple[int, int]:
        """
        현재 주차를 반환
        
        Returns:
            Tuple[int, int]: (연도, 주차번호)
        """
        return WeekCalculator.get_week_number(date.today())
    
    @staticmethod
    def get_current_week_string(format_str: str = "YYYY년 W주차") -> str:
        """
        현재 주차를 문자열로 반환
        
        Args:
            format_str: 출력 형식
            
        Returns:
            str: 현재 주차 문자열
        """
        return WeekCalculator.get_week_number_string(date.today(), format_str)
    
    @staticmethod
    def is_valid_week(year: int, week: int) -> bool:
        """
        주어진 연도와 주차가 유효한지 확인
        
        Args:
            year: 연도
            week: 주차 번호
            
        Returns:
            bool: 유효한 주차인지 여부
        """
        try:
            # 해당 연도의 최대 주차 수 계산
            dec_28 = date(year, 12, 28)  # 12월 28일은 항상 해당 연도의 마지막 주에 속함
            _, max_week = WeekCalculator.get_week_number(dec_28)
            
            return 1 <= week <= max_week
        except:
            return False
    
    @staticmethod
    def get_weeks_in_year(year: int) -> int:
        """
        주어진 연도의 총 주차 수를 반환
        
        Args:
            year: 연도
            
        Returns:
            int: 해당 연도의 총 주차 수
        """
        dec_28 = date(year, 12, 28)
        _, max_week = WeekCalculator.get_week_number(dec_28)
        return max_week
    
    @staticmethod
    def get_week_range(year: int, week: int) -> Tuple[date, date]:
        """
        주어진 연도와 주차의 주 범위를 반환
        
        Args:
            year: 연도
            week: 주차 번호
            
        Returns:
            Tuple[date, date]: (주 시작일, 주 종료일)
        """
        week_start = WeekCalculator.get_week_start_date(year, week)
        week_end = WeekCalculator.get_week_end_date(year, week)
        return week_start, week_end


# 편의 함수들
def get_week_number(date_obj: Union[datetime, date]) -> Tuple[int, int]:
    """주어진 날짜의 주차 번호를 반환 (편의 함수)"""
    return WeekCalculator.get_week_number(date_obj)


def get_week_number_string(date_obj: Union[datetime, date], format_str: str = "YYYY년 W주차") -> str:
    """주어진 날짜의 주차를 문자열로 반환 (편의 함수)"""
    return WeekCalculator.get_week_number_string(date_obj, format_str)


def get_week_start_date(year: int, week: int) -> date:
    """주어진 연도와 주차의 주 시작일을 반환 (편의 함수)"""
    return WeekCalculator.get_week_start_date(year, week)


def get_week_end_date(year: int, week: int) -> date:
    """주어진 연도와 주차의 주 종료일을 반환 (편의 함수)"""
    return WeekCalculator.get_week_end_date(year, week)


def parse_week_string(week_string: str) -> Optional[Tuple[int, int]]:
    """주차 문자열을 파싱하여 연도와 주차 번호를 반환 (편의 함수)"""
    return WeekCalculator.parse_week_string(week_string)


def get_current_week() -> Tuple[int, int]:
    """현재 주차를 반환 (편의 함수)"""
    return WeekCalculator.get_current_week()


def get_current_week_string(format_str: str = "YYYY년 W주차") -> str:
    """현재 주차를 문자열로 반환 (편의 함수)"""
    return WeekCalculator.get_current_week_string(format_str)


# 테스트 함수
def test_week_calculator():
    """주차 계산기 테스트"""
    print("📅 주차 계산기 테스트")
    print("=" * 50)
    
    # 현재 주차
    current_year, current_week = get_current_week()
    print(f"현재 주차: {current_year}년 {current_week}주차")
    
    # 특정 날짜 테스트
    test_dates = [
        datetime(2025, 1, 1),   # 2025년 1월 1일
        datetime(2025, 1, 6),   # 2025년 1월 6일
        datetime(2025, 8, 25),  # 2025년 8월 25일 (35주차)
        datetime(2025, 12, 31), # 2025년 12월 31일
    ]
    
    print(f"\n📊 특정 날짜 주차 테스트:")
    for test_date in test_dates:
        year, week = get_week_number(test_date)
        week_str = get_week_number_string(test_date)
        week_start = get_week_start_date(year, week)
        week_end = get_week_end_date(year, week)
        print(f"  {test_date.strftime('%Y-%m-%d')} → {week_str} ({week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')})")
    
    # 주차 문자열 파싱 테스트
    test_strings = [
        "2025년 1주차",
        "2025년 35주차",
        "2025-W01",
        "2025-W35",
        "2025년 8월 1주차",
    ]
    
    print(f"\n🔍 주차 문자열 파싱 테스트:")
    for test_str in test_strings:
        result = parse_week_string(test_str)
        if result:
            year, week = result
            week_start = get_week_start_date(year, week)
            week_end = get_week_end_date(year, week)
            print(f"  '{test_str}' → {year}년 {week}주차 ({week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')})")
        else:
            print(f"  '{test_str}' → 파싱 실패")
    
    # 주차 유효성 검사
    print(f"\n✅ 주차 유효성 검사:")
    test_weeks = [(2025, 1), (2025, 35), (2025, 53), (2025, 0), (2025, 54)]
    for year, week in test_weeks:
        is_valid = WeekCalculator.is_valid_week(year, week)
        print(f"  {year}년 {week}주차: {'유효' if is_valid else '무효'}")
    
    # 연도별 총 주차 수
    print(f"\n📊 연도별 총 주차 수:")
    for year in [2024, 2025, 2026]:
        total_weeks = WeekCalculator.get_weeks_in_year(year)
        print(f"  {year}년: {total_weeks}주차")


if __name__ == "__main__":
    test_week_calculator()
