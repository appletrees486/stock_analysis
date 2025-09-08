#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
거래량 랭킹 데이터 관리 모듈
일/주/월별 거래량 및 거래률 상위 50개 종목 조회
stock_data_collector.py의 증분 및 검증 방식 적용
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from database_config import DatabaseManager
from market_status_detector import MarketStatusDetector
from korean_holiday_manager import KoreanHolidayManager

logger = logging.getLogger(__name__)

class VolumeRankingDataManager:
    """거래량 랭킹 데이터 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db_manager = DatabaseManager()
        self.market_detector = MarketStatusDetector()
        self.holiday_manager = KoreanHolidayManager()
        
        # 캐시 설정
        self._daily_cache = {}
        self._weekly_cache = {}
        self._monthly_cache = {}
        self._cache_ttl = 3600  # 1시간
        
    def get_daily_volume_ranking(self, date: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """일일 거래량 상위 종목 조회"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
                
            # 캐시 확인
            cache_key = f"daily_volume_{date}"
            if cache_key in self._daily_cache:
                cache_data = self._daily_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # 데이터베이스에서 조회 (거래량만)
            query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    d.volume,
                    d.trade_date
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date = %s
                ORDER BY d.volume DESC
                LIMIT %s
            """
            
            # 데이터베이스 연결 및 쿼리 실행
            if not self.db_manager.connect():
                logger.error("데이터베이스 연결 실패")
                return []
                
            try:
                self.db_manager.execute_query(query, (date, limit))
                results = self.db_manager.cursor.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'stock_code': row['stock_code'],
                        'stock_name': row['stock_name'],
                        'market_type': row['market_type'],
                        'volume': row['volume'],
                        'turnover_rate': 0.0  # 거래률 정보 없음
                    })
                
                # 캐시 저장
                self._daily_cache[cache_key] = {
                    'data': formatted_results,
                    'timestamp': datetime.now().timestamp()
                }
                
                return formatted_results
                
            finally:
                self.db_manager.disconnect()
            
        except Exception as e:
            logger.error(f"일일 거래량 랭킹 조회 실패: {e}")
            return []
    
    def get_daily_turnover_ranking(self, date: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """일일 거래률 상위 종목 조회 (실제 거래률 계산)"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
                
            # 캐시 확인
            cache_key = f"daily_turnover_{date}"
            if cache_key in self._daily_cache:
                cache_data = self._daily_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # 새로운 구조: daily_data의 outstanding_shares 사용
            query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    d.volume,
                    d.trade_date,
                    d.outstanding_shares,
                    CASE 
                        WHEN d.outstanding_shares > 0 
                        THEN ROUND((d.volume / d.outstanding_shares) * 100, 2)
                        ELSE 0 
                    END as turnover_rate
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date = %s
                AND d.outstanding_shares > 0  -- 유통주식수가 있는 데이터만
                ORDER BY turnover_rate DESC
                LIMIT %s
            """
            
            # 데이터베이스 연결 및 쿼리 실행
            if not self.db_manager.connect():
                logger.error("데이터베이스 연결 실패")
                return []
                
            try:
                self.db_manager.execute_query(query, (date, limit))
                results = self.db_manager.cursor.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'stock_code': row['stock_code'],
                        'stock_name': row['stock_name'],
                        'market_type': row['market_type'],
                        'volume': row['volume'],
                        'trade_date': str(row['trade_date']) if row['trade_date'] else None,
                        'outstanding_shares': row['outstanding_shares'],
                        'turnover_rate': float(row['turnover_rate']) if row['turnover_rate'] is not None else 0.0
                    })
                
                # 캐시 저장
                self._daily_cache[cache_key] = {
                    'data': formatted_results,
                    'timestamp': datetime.now().timestamp()
                }
                
                logger.info(f"일일 거래률 랭킹 조회 완료: {date} - {len(formatted_results)}개 종목")
                return formatted_results
                
            finally:
                self.db_manager.disconnect()
            
        except Exception as e:
            logger.error(f"일일 거래률 랭킹 조회 실패: {e}")
            return []
    
    def get_weekly_volume_ranking(self, week_start: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """주간 거래량 상위 종목 조회"""
        try:
            if week_start is None:
                # 현재 주의 월요일 찾기
                today = datetime.now()
                days_since_monday = today.weekday()
                week_start = (today - timedelta(days=days_since_monday)).strftime('%Y-%m-%d')
            
            # 캐시 확인 (주간 데이터는 공유하므로 limit 없이 캐시)
            cache_key = f"weekly_volume_{week_start}"
            if cache_key in self._weekly_cache:
                cache_data = self._weekly_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    # 캐시된 전체 데이터에서 limit만큼 반환
                    return cache_data['data'][:limit]
            
            # 주간 거래량 집계 (월~금)
            week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
            
            # 캐시를 위해 더 많은 데이터를 조회 (최대 1000개)
            cache_limit = max(1000, limit)
            
            query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    SUM(d.volume) as total_volume,
                    COUNT(d.trade_date) as trading_days
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date BETWEEN %s AND %s
                AND WEEKDAY(d.trade_date) < 5
                GROUP BY d.stock_code, s.stock_name, s.market_type
                ORDER BY total_volume DESC
                LIMIT %s
            """
            
            # 데이터베이스 연결 및 쿼리 실행
            if not self.db_manager.connect():
                logger.error("데이터베이스 연결 실패")
                return []
                
            try:
                self.db_manager.execute_query(query, (week_start, week_end, cache_limit))
                results = self.db_manager.cursor.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'stock_code': row['stock_code'],
                        'stock_name': row['stock_name'],
                        'market_type': row['market_type'],
                        'total_volume': row['total_volume'],
                        'volume': row['total_volume'],  # 프론트엔드 호환성을 위해 추가
                        'turnover_rate': 0.0,  # 거래률 계산 불가
                        'trading_days': row['trading_days']
                    })
                
                # 캐시 저장 (전체 데이터)
                self._weekly_cache[cache_key] = {
                    'data': formatted_results,
                    'timestamp': datetime.now().timestamp()
                }
                
                # 요청된 limit만큼 반환
                return formatted_results[:limit]
                
            finally:
                self.db_manager.disconnect()
            
        except Exception as e:
            logger.error(f"주간 거래량 랭킹 조회 실패: {e}")
            return []
    
    def get_weekly_turnover_ranking(self, week_start: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """주간 거래률 상위 종목 조회 (실제 거래률 계산)"""
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
            
            # 주간 거래률 계산 (월~금)
            week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
            
            # 캐시를 위해 더 많은 데이터를 조회 (최대 1000개)
            cache_limit = max(1000, limit)
            
            # 새로운 구조: daily_data의 outstanding_shares 사용
            query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    SUM(d.volume) as total_volume,
                    COUNT(d.trade_date) as trading_days,
                    AVG(d.outstanding_shares) as avg_shares,
                    CASE 
                        WHEN AVG(d.outstanding_shares) > 0 
                        THEN ROUND((SUM(d.volume) / AVG(d.outstanding_shares)) * 100, 2)
                        ELSE 0 
                    END as turnover_rate
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date BETWEEN %s AND %s
                AND d.outstanding_shares > 0  -- 유통주식수가 있는 데이터만
                GROUP BY d.stock_code, s.stock_name, s.market_type
                HAVING COUNT(d.trade_date) >= 3  -- 최소 3일 이상 거래된 종목만
                ORDER BY turnover_rate DESC
                LIMIT %s
            """
            
            # 데이터베이스 연결 및 쿼리 실행
            if not self.db_manager.connect():
                logger.error("데이터베이스 연결 실패")
                return []
                
            try:
                self.db_manager.execute_query(query, (week_start, week_end, cache_limit))
                results = self.db_manager.cursor.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'stock_code': row['stock_code'],
                        'stock_name': row['stock_name'],
                        'market_type': row['market_type'],
                        'total_volume': row['total_volume'],
                        'volume': row['total_volume'],  # 프론트엔드 호환성을 위해 추가
                        'turnover_rate': float(row['turnover_rate']) if row['turnover_rate'] is not None else 0.0,
                        'trading_days': row['trading_days']
                    })
                
                # 캐시 저장 (전체 데이터)
                self._weekly_cache[cache_key] = {
                    'data': formatted_results,
                    'timestamp': datetime.now().timestamp()
                }
                
                logger.info(f"주간 거래률 랭킹 조회 완료: {week_start}~{week_end} - {len(formatted_results)}개 종목")
                # 요청된 limit만큼 반환
                return formatted_results[:limit]
                
            finally:
                self.db_manager.disconnect()
            
        except Exception as e:
            logger.error(f"주간 거래률 랭킹 조회 실패: {e}")
            return []
    
    def get_monthly_volume_ranking(self, year_month: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """월간 거래량 상위 종목 조회"""
        try:
            if year_month is None:
                year_month = datetime.now().strftime('%Y-%m')
            
            # 캐시 확인
            cache_key = f"monthly_volume_{year_month}"
            if cache_key in self._monthly_cache:
                cache_data = self._monthly_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # 월간 거래량 집계 (1일~말일)
            month_start = f"{year_month}-01"
            next_month = datetime.strptime(year_month, '%Y-%m') + timedelta(days=32)
            month_end = (next_month.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    SUM(d.volume) as total_volume,
                    COUNT(d.trade_date) as trading_days
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date BETWEEN %s AND %s
                AND WEEKDAY(d.trade_date) < 5
                GROUP BY d.stock_code, s.stock_name, s.market_type
                ORDER BY total_volume DESC
                LIMIT %s
            """
            
            # 데이터베이스 연결 및 쿼리 실행
            if not self.db_manager.connect():
                logger.error("데이터베이스 연결 실패")
                return []
                
            try:
                self.db_manager.execute_query(query, (month_start, month_end, limit))
                results = self.db_manager.cursor.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'stock_code': row['stock_code'],
                        'stock_name': row['stock_name'],
                        'market_type': row['market_type'],
                        'total_volume': row['total_volume'],
                        'volume': row['total_volume'],  # 프론트엔드 호환성을 위해 추가
                        'turnover_rate': 0.0,  # 거래률 계산 불가
                        'trading_days': row['trading_days']
                    })
                
                # 캐시 저장
                self._monthly_cache[cache_key] = {
                    'data': formatted_results,
                    'timestamp': datetime.now().timestamp()
                }
                
                return formatted_results
                
            finally:
                self.db_manager.disconnect()
            
        except Exception as e:
            logger.error(f"월간 거래량 랭킹 조회 실패: {e}")
            return []
    
    def get_monthly_turnover_ranking(self, year_month: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """월간 거래률 상위 종목 조회 (실제 거래률 계산)"""
        try:
            if year_month is None:
                year_month = datetime.now().strftime('%Y-%m')
            
            # 캐시 확인
            cache_key = f"monthly_turnover_{year_month}"
            if cache_key in self._monthly_cache:
                cache_data = self._monthly_cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # 월간 거래률 계산 (1일~말일)
            month_start = f"{year_month}-01"
            next_month = datetime.strptime(year_month, '%Y-%m') + timedelta(days=32)
            month_end = (next_month.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 새로운 구조: daily_data의 outstanding_shares 사용
            query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    SUM(d.volume) as total_volume,
                    COUNT(d.trade_date) as trading_days,
                    AVG(d.outstanding_shares) as avg_shares,
                    CASE 
                        WHEN AVG(d.outstanding_shares) > 0 
                        THEN ROUND((SUM(d.volume) / AVG(d.outstanding_shares)) * 100, 2)
                        ELSE 0 
                    END as turnover_rate
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date BETWEEN %s AND %s
                AND d.outstanding_shares > 0  -- 유통주식수가 있는 데이터만
                GROUP BY d.stock_code, s.stock_name, s.market_type
                HAVING COUNT(d.trade_date) >= 10  -- 최소 10일 이상 거래된 종목만
                ORDER BY turnover_rate DESC
                LIMIT %s
            """
            
            # 데이터베이스 연결 및 쿼리 실행
            if not self.db_manager.connect():
                logger.error("데이터베이스 연결 실패")
                return []
                
            try:
                self.db_manager.execute_query(query, (month_start, month_end, limit))
                results = self.db_manager.cursor.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'stock_code': row['stock_code'],
                        'stock_name': row['stock_name'],
                        'market_type': row['market_type'],
                        'total_volume': row['total_volume'],
                        'volume': row['total_volume'],  # 프론트엔드 호환성을 위해 추가
                        'turnover_rate': float(row['turnover_rate']) if row['turnover_rate'] is not None else 0.0,
                        'trading_days': row['trading_days']
                    })
                
                # 캐시 저장
                self._monthly_cache[cache_key] = {
                    'data': formatted_results,
                    'timestamp': datetime.now().timestamp()
                }
                
                logger.info(f"월간 거래률 랭킹 조회 완료: {year_month} - {len(formatted_results)}개 종목")
                return formatted_results
                
            finally:
                self.db_manager.disconnect()
            
        except Exception as e:
            logger.error(f"월간 거래률 랭킹 조회 실패: {e}")
            return []
    
    def clear_cache(self):
        """캐시 초기화"""
        self._daily_cache.clear()
        self._weekly_cache.clear()
        self._monthly_cache.clear()
        logger.info("거래량 랭킹 캐시가 초기화되었습니다.")