#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
거래대금 랭킹 데이터 관리 모듈
일/주/월별 거래대금 및 거래율 상위 50개 종목 조회
stock_data_collector.py의 증분 및 검증 방식 적용
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from database_config import DatabaseManager
from market_status_detector import MarketStatusDetector
from korean_holiday_manager import KoreanHolidayManager
from ranking_calculator import RankingCalculator

logger = logging.getLogger(__name__)

class VolumeRankingDataManager:
    """거래대금 랭킹 데이터 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db_manager = DatabaseManager()
        self.market_detector = MarketStatusDetector()
        self.holiday_manager = KoreanHolidayManager()
        self.ranking_calculator = RankingCalculator()
        
        # 캐시 설정
        self._daily_cache = {}
        self._weekly_cache = {}
        self._monthly_cache = {}
        self._cache_ttl = 3600  # 1시간
        
    def get_daily_volume_ranking(self, date: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """일일 거래대금 상위 종목 조회"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
                
            # 캐시 확인
            cache_key = f"daily_volume_{date}"
            if cache_key in self._daily_cache:
                cache_data = self._daily_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # RankingCalculator를 사용하여 거래대금 순위 조회
            results = self.ranking_calculator.get_volume_ranking(date, "일봉", limit=limit, trading_type="거래대금")
            
            # 캐시에 저장
            self._daily_cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now().timestamp()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"일일 거래대금 랭킹 조회 실패: {e}")
            return []
    
    def get_daily_turnover_ranking(self, date: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """일일 거래율 상위 종목 조회 (실제 거래율 계산)"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
                
            # 캐시 확인
            cache_key = f"daily_turnover_{date}"
            if cache_key in self._daily_cache:
                cache_data = self._daily_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # RankingCalculator를 사용하여 거래율 순위 조회
            results = self.ranking_calculator.get_turnover_ranking(date, "일봉", limit=limit)
            
            # 캐시에 저장
            self._daily_cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now().timestamp()
            }
            
            logger.info(f"일일 거래율 랭킹 조회 완료: {date} - {len(results)}개 종목")
            return results
            
        except Exception as e:
            logger.error(f"일일 거래율 랭킹 조회 실패: {e}")
            return []
    
    def get_weekly_volume_ranking(self, week_start: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """주간 거래대금 상위 종목 조회"""
        try:
            logger.info(f"🔍 get_weekly_volume_ranking 호출: week_start='{week_start}', limit={limit}")
            
            if week_start is None:
                # 현재 주의 월요일 찾기
                today = datetime.now()
                days_since_monday = today.weekday()
                week_start = (today - timedelta(days=days_since_monday)).strftime('%Y-%m-%d')
                logger.info(f"🔍 week_start가 None이어서 현재 주로 설정: {week_start}")
            else:
                # week_start 값 검증 및 수정
                try:
                    # 날짜 파싱
                    week_start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
                    logger.info(f"🔍 파싱된 week_start: {week_start_date}")
                    
                    # 해당 날짜가 월요일인지 확인
                    if week_start_date.weekday() != 0:  # 0 = 월요일
                        logger.warning(f"⚠️ week_start가 월요일이 아닙니다: {week_start_date} (요일: {week_start_date.weekday()})")
                        
                        # 가장 가까운 월요일로 수정
                        days_to_monday = week_start_date.weekday()
                        corrected_week_start = week_start_date - timedelta(days=days_to_monday)
                        logger.info(f"🔧 week_start를 월요일로 수정: {week_start} → {corrected_week_start}")
                        week_start = corrected_week_start.strftime('%Y-%m-%d')
                    else:
                        logger.info(f"✅ week_start가 올바른 월요일입니다: {week_start_date}")
                        
                except ValueError as e:
                    logger.error(f"❌ week_start 날짜 형식 오류: {week_start} - {e}")
                    # 현재 주의 월요일로 fallback
                    today = datetime.now()
                    days_since_monday = today.weekday()
                    week_start = (today - timedelta(days=days_since_monday)).strftime('%Y-%m-%d')
                    logger.info(f"🔧 week_start를 현재 주 월요일로 설정: {week_start}")
            
            # 캐시 확인 (주간 데이터는 공유하므로 limit 없이 캐시)
            cache_key = f"weekly_volume_{week_start}"
            
            # 기존 캐시 삭제 (필드명 변경으로 인해)
            if cache_key in self._weekly_cache:
                del self._weekly_cache[cache_key]
            
            # ranking_calculator의 캐시도 초기화
            self.ranking_calculator._cache.clear()
            
            # 캐시 완전 무시
            print(f"🔍 VolumeRankingDataManager 캐시 무시")
            
            # 캐시 확인 (새로 생성된 데이터만 사용)
            # if cache_key in self._weekly_cache:
            #     cache_data = self._weekly_cache[cache_key]
            #     if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
            #         # 캐시된 데이터 반환
            #         return cache_data['data'][:limit]
            
            # RankingCalculator를 사용하여 주간 거래대금 순위 조회
            results = self.ranking_calculator.get_volume_ranking(week_start, "주봉", limit=limit, trading_type="거래대금")
            
            # 캐시에 저장
            self._weekly_cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now().timestamp()
            }
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"주간 거래대금 랭킹 조회 실패: {e}")
            return []
    
    def get_weekly_turnover_ranking(self, week_start: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """주간 거래율 상위 종목 조회 (실제 거래율 계산)"""
        try:
            if week_start is None:
                # 현재 주의 월요일 찾기
                today = datetime.now()
                days_since_monday = today.weekday()
                week_start = (today - timedelta(days=days_since_monday)).strftime('%Y-%m-%d')
            
            # 캐시 확인 (주간 데이터는 공유하므로 limit 없이 캐시)
            cache_key = f"weekly_turnover_{week_start}"
            if cache_key in self._weekly_cache:
                cache_data = self._weekly_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    # 캐시된 전체 데이터에서 limit만큼 반환
                    return cache_data['data'][:limit]
            
            # RankingCalculator를 사용하여 주간 거래율 순위 조회
            results = self.ranking_calculator.get_turnover_ranking(week_start, "주봉", limit=limit)
            
            # 캐시에 저장
            self._weekly_cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now().timestamp()
            }
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"주간 거래율 랭킹 조회 실패: {e}")
            return []
    
    def get_monthly_volume_ranking(self, year_month: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """월간 거래대금 상위 종목 조회"""
        try:
            if year_month is None:
                year_month = datetime.now().strftime('%Y-%m')
            
            # 캐시 확인
            cache_key = f"monthly_volume_{year_month}"
            if cache_key in self._monthly_cache:
                cache_data = self._monthly_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # RankingCalculator를 사용하여 월간 거래대금 순위 조회
            results = self.ranking_calculator.get_volume_ranking(year_month, "월봉", limit=limit, trading_type="거래대금")
            
            # 캐시에 저장
            self._monthly_cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now().timestamp()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"월간 거래대금 랭킹 조회 실패: {e}")
            return []
    
    def get_monthly_turnover_ranking(self, year_month: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """월간 거래율 상위 종목 조회 (실제 거래율 계산)"""
        try:
            if year_month is None:
                year_month = datetime.now().strftime('%Y-%m')
            
            # 캐시 확인
            cache_key = f"monthly_turnover_{year_month}"
            if cache_key in self._monthly_cache:
                cache_data = self._monthly_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # RankingCalculator를 사용하여 월간 거래율 순위 조회
            results = self.ranking_calculator.get_turnover_ranking(year_month, "월봉", limit=limit)
            
            # 캐시에 저장
            self._monthly_cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now().timestamp()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"월간 거래율 랭킹 조회 실패: {e}")
            return []
    
    def clear_cache(self):
        """캐시 초기화"""
        self._daily_cache.clear()
        self._weekly_cache.clear()
        self._monthly_cache.clear()
        logger.info("거래대금 랭킹 캐시가 초기화되었습니다.")