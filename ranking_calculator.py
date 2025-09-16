#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 순위 계산 모듈
모든 모듈에서 사용하는 순위 계산 로직을 통합 관리합니다.
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# week_calculator 모듈 import
from week_calculator import WeekCalculator, get_week_number

logger = logging.getLogger(__name__)


class RankingCalculator:
    """통합 순위 계산 클래스"""
    
    def __init__(self, db_config: dict = None):
        """
        RankingCalculator 초기화
        
        Args:
            db_config (dict): 데이터베이스 설정
        """
        self.db_config = db_config
        self._cache = {}  # 간단한 메모리 캐시
        self._cache_ttl = 3600  # 1시간 TTL
        
    def calculate_transaction_amount(self, volume: float, close_price: float, 
                                   high_price: float = None, low_price: float = None, 
                                   method: str = "close_price") -> float:
        """
        거래대금 계산 (첨부 이미지 참고)
        
        Args:
            volume (float): 거래량
            close_price (float): 종가
            high_price (float): 고가 (Typical Price 방식용)
            low_price (float): 저가 (Typical Price 방식용)
            method (str): "close_price" (기본) 또는 "typical_price"
            
        Returns:
            float: 계산된 거래대금
        """
        try:
            if method == "typical_price" and high_price and low_price:
                # (H + L + C) / 3 × V - 조금 더 균형 잡힌 근사
                typical_price = (high_price + low_price + close_price) / 3
                return typical_price * volume
            else:
                # C × V - 가장 널리 쓰이는 대용치 (간단한 근사)
                return close_price * volume
        except Exception as e:
            logger.error(f"거래대금 계산 오류: {e}")
            return 0.0
    
    def calculate_turnover_rate(self, volume: float, outstanding_shares: float) -> float:
        """
        거래율 계산
        
        Args:
            volume (float): 거래량
            outstanding_shares (float): 유통주식수
            
        Returns:
            float: 거래율 (%)
        """
        try:
            if outstanding_shares > 0:
                return (volume / outstanding_shares) * 100
            else:
                return 0.0
        except Exception as e:
            logger.error(f"거래율 계산 오류: {e}")
            return 0.0
    
    def calculate_individual_ranking(self, stock_code: str, target_date: str, 
                                   chart_type: str, trading_type: str = "거래대금") -> Dict[str, Any]:
        """
        개별 종목 순위 계산
        
        Args:
            stock_code (str): 종목코드
            target_date (str): 대상 날짜/기간
            chart_type (str): 차트 타입 (일봉, 주봉, 월봉)
            trading_type (str): 거래 타입 (거래대금, 거래율)
            
        Returns:
            Dict[str, Any]: 순위 정보
        """
        try:
            from database_config import DatabaseManager
            db = DatabaseManager()
            
            if not db.connect():
                logger.error("DB 연결 실패")
                return self._get_default_ranking_info()
            
            # 해당 종목의 거래 데이터 조회
            stock_query, stock_params = self._build_stock_data_query_with_params(stock_code, target_date, chart_type)
            stock_data = db.fetch_one(stock_query, stock_params)
            
            if not stock_data:
                db.disconnect()
                return self._get_default_ranking_info()
            
            # 거래대금/거래율 계산
            volume = stock_data.get('volume', 0)
            close_price = stock_data.get('close_price', 0)
            outstanding_shares = stock_data.get('outstanding_shares', 0)
            
            transaction_amount = self.calculate_transaction_amount(volume, close_price)
            turnover_rate = self.calculate_turnover_rate(volume, outstanding_shares)
            
            # 순위 계산을 위한 기준값
            ranking_value = transaction_amount if trading_type == "거래대금" else turnover_rate
            
            # 순위 계산 쿼리 실행
            ranking_query, ranking_params = self._build_ranking_calculation_query_with_params(target_date, chart_type, trading_type, ranking_value)
            ranking_result = db.fetch_one(ranking_query, ranking_params)
            
            db.disconnect()
            
            return {
                'ranking': ranking_result.get('ranking', 1) if ranking_result else 1,
                'transaction_amount': transaction_amount,
                'turnover_rate': turnover_rate,
                'total_stocks': ranking_result.get('total_stocks', 1) if ranking_result else 1,
                'volume': volume,
                'close_price': close_price,
                'outstanding_shares': outstanding_shares
            }
            
        except Exception as e:
            logger.error(f"개별 순위 계산 오류: {e}")
            return self._get_default_ranking_info()
    
    def get_volume_ranking(self, target_date: str, chart_type: str, 
                          limit: int = 50, trading_type: str = "거래대금") -> List[Dict[str, Any]]:
        """
        전체 순위 리스트 조회 (거래대금 기준)
        
        Args:
            target_date (str): 대상 날짜/기간
            chart_type (str): 차트 타입 (일봉, 주봉, 월봉)
            limit (int): 조회할 개수 (기본 50개)
            trading_type (str): 거래 타입 (거래대금, 거래율)
            
        Returns:
            List[Dict[str, Any]]: 순위 리스트
        """
        try:
            from database_config import DatabaseManager
            db = DatabaseManager()
            
            if not db.connect():
                logger.error("DB 연결 실패")
                return []
            
            # 캐시 확인
            cache_key = f"{chart_type}_{trading_type}_{target_date}_{limit}"
            if cache_key in self._cache:
                cache_data = self._cache[cache_key]
                if datetime.now().timestamp() - cache_data['timestamp'] < self._cache_ttl:
                    return cache_data['data']
            
            # 시점별 쿼리 생성
            query, params = self._build_ranking_list_query(target_date, chart_type, trading_type, limit)
            
            # 순위 리스트 조회
            results = db.fetch_all(query, params)
            db.disconnect()
            
            # 결과 포맷팅
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'stock_code': row['stock_code'],
                    'stock_name': row['stock_name'],
                    'market_type': row['market_type'],
                    'volume': row['volume'],
                    'transaction_amount': row.get('transaction_amount', 0),
                    'turnover_rate': row.get('turnover_rate', 0),
                    'outstanding_shares': row.get('outstanding_shares', 0),
                    'ranking': row.get('ranking', 0)
                })
            
            # 캐시 저장
            self._cache[cache_key] = {
                'data': formatted_results,
                'timestamp': datetime.now().timestamp()
            }
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"순위 리스트 조회 오류: {e}")
            return []
    
    def get_turnover_ranking(self, target_date: str, chart_type: str, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """
        전체 순위 리스트 조회 (거래율 기준)
        
        Args:
            target_date (str): 대상 날짜/기간
            chart_type (str): 차트 타입 (일봉, 주봉, 월봉)
            limit (int): 조회할 개수 (기본 50개)
            
        Returns:
            List[Dict[str, Any]]: 순위 리스트
        """
        return self.get_volume_ranking(target_date, chart_type, limit, "거래율")
    
    def _build_ranking_query(self, target_date: str, chart_type: str, trading_type: str) -> Tuple[str, tuple]:
        """순위 계산용 쿼리 생성"""
        if chart_type == "일봉":
            if trading_type == "거래율":
                query = """
                SELECT COUNT(*) + 1 as ranking
                FROM daily_data 
                WHERE trade_date = %s 
                AND outstanding_shares > 0
                AND (volume / outstanding_shares) * 100 > %s
                """
            else:
                query = """
                SELECT COUNT(*) + 1 as ranking
                FROM daily_data 
                WHERE trade_date = %s 
                AND volume > %s
                """
            return query, (target_date,)
            
        elif chart_type == "주봉":
            # week_calculator.py 활용하여 주간 기간 계산
            try:
                target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
                year, week = get_week_number(target_datetime)
                week_start = WeekCalculator.get_week_start_date(year, week)
                week_end = WeekCalculator.get_week_end_date(year, week)
                
                if trading_type == "거래율":
                    query = """
                    SELECT COUNT(*) + 1 as ranking
                    FROM (
                        SELECT stock_code, AVG((volume / outstanding_shares) * 100) as avg_turnover_rate
                        FROM daily_data 
                        WHERE trade_date BETWEEN %s AND %s
                        AND WEEKDAY(trade_date) < 5
                        AND outstanding_shares > 0
                        GROUP BY stock_code
                        HAVING avg_turnover_rate > %s
                    ) as weekly_turnover_rates
                    """
                else:
                    query = """
                    SELECT COUNT(*) + 1 as ranking
                    FROM (
                        SELECT stock_code, SUM(volume) as total_volume
                        FROM daily_data 
                        WHERE trade_date BETWEEN %s AND %s
                        AND WEEKDAY(trade_date) < 5
                        GROUP BY stock_code
                        HAVING total_volume > %s
                    ) as weekly_volumes
                    """
                return query, (week_start, week_end)
            except Exception as e:
                logger.error(f"주차 계산 실패: {e}")
                return "SELECT 1 as ranking", (1,)
                
        elif chart_type == "월봉":
            year, month = target_date.split('-')
            if trading_type == "거래율":
                query = """
                SELECT COUNT(*) + 1 as ranking
                FROM (
                    SELECT stock_code, AVG((volume / outstanding_shares) * 100) as avg_turnover_rate
                    FROM daily_data 
                    WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s
                    AND WEEKDAY(trade_date) < 5
                    AND outstanding_shares > 0
                    GROUP BY stock_code
                    HAVING avg_turnover_rate > %s
                ) as monthly_turnover_rates
                """
            else:
                query = """
                SELECT COUNT(*) + 1 as ranking
                FROM (
                    SELECT stock_code, SUM(volume) as total_volume
                    FROM daily_data 
                    WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s
                    AND WEEKDAY(trade_date) < 5
                    GROUP BY stock_code
                    HAVING total_volume > %s
                ) as monthly_volumes
                """
            return query, (year, month)
        
        return "SELECT 1 as ranking", (1,)
    
    def _build_stock_data_query_with_params(self, stock_code: str, target_date: str, chart_type: str) -> Tuple[str, tuple]:
        """개별 종목 데이터 조회 쿼리 및 매개변수 생성"""
        if chart_type == "일봉":
            query = """
            SELECT volume, close as close_price, outstanding_shares
            FROM daily_data 
            WHERE stock_code = %s AND trade_date = %s
            """
            return query, (stock_code, target_date)
        elif chart_type == "주봉":
            try:
                target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
                year, week = get_week_number(target_datetime)
                week_start = WeekCalculator.get_week_start_date(year, week)
                week_end = WeekCalculator.get_week_end_date(year, week)
                
                query = """
                SELECT SUM(volume) as volume, AVG(close) as close_price, AVG(outstanding_shares) as outstanding_shares
                FROM daily_data 
                WHERE stock_code = %s 
                AND trade_date BETWEEN %s AND %s
                AND WEEKDAY(trade_date) < 5
                """
                return query, (stock_code, week_start, week_end)
            except Exception as e:
                logger.error(f"주차 계산 실패: {e}")
                return "SELECT 0 as volume, 0 as close_price, 0 as outstanding_shares", (stock_code,)
        elif chart_type == "월봉":
            year, month = target_date.split('-')
            query = """
            SELECT SUM(volume) as volume, AVG(close) as close_price, AVG(outstanding_shares) as outstanding_shares
            FROM daily_data 
            WHERE stock_code = %s 
            AND YEAR(trade_date) = %s AND MONTH(trade_date) = %s
            AND WEEKDAY(trade_date) < 5
            """
            return query, (stock_code, year, month)
        return "SELECT 0 as volume, 0 as close_price, 0 as outstanding_shares", (stock_code,)
    
    def _build_ranking_calculation_query_with_params(self, target_date: str, chart_type: str, 
                                                   trading_type: str, ranking_value: float) -> Tuple[str, tuple]:
        """순위 계산 쿼리 및 매개변수 생성"""
        if chart_type == "일봉":
            if trading_type == "거래율":
                query = """
                SELECT COUNT(*) + 1 as ranking, 
                       (SELECT COUNT(*) FROM daily_data WHERE trade_date = %s AND outstanding_shares > 0) as total_stocks
                FROM daily_data 
                WHERE trade_date = %s 
                AND outstanding_shares > 0
                AND (volume / outstanding_shares) * 100 > %s
                """
                return query, (target_date, target_date, ranking_value)
            else:
                query = """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(*) FROM daily_data WHERE trade_date = %s) as total_stocks
                FROM daily_data 
                WHERE trade_date = %s 
                AND volume > %s
                """
                return query, (target_date, target_date, ranking_value)
        elif chart_type == "주봉":
            try:
                target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
                year, week = get_week_number(target_datetime)
                week_start = WeekCalculator.get_week_start_date(year, week)
                week_end = WeekCalculator.get_week_end_date(year, week)
                
                if trading_type == "거래율":
                    query = """
                    SELECT COUNT(*) + 1 as ranking,
                           (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                            WHERE trade_date BETWEEN %s AND %s 
                            AND WEEKDAY(trade_date) < 5 
                            AND outstanding_shares > 0) as total_stocks
                    FROM (
                        SELECT stock_code, AVG((volume / outstanding_shares) * 100) as avg_turnover_rate
                        FROM daily_data 
                        WHERE trade_date BETWEEN %s AND %s
                        AND WEEKDAY(trade_date) < 5
                        AND outstanding_shares > 0
                        GROUP BY stock_code
                        HAVING avg_turnover_rate > %s
                    ) as weekly_turnover_rates
                    """
                    return query, (week_start, week_end, week_start, week_end, ranking_value)
                else:
                    query = """
                    SELECT COUNT(*) + 1 as ranking,
                           (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                            WHERE trade_date BETWEEN %s AND %s 
                            AND WEEKDAY(trade_date) < 5) as total_stocks
                    FROM (
                        SELECT stock_code, SUM(volume) as total_volume
                        FROM daily_data 
                        WHERE trade_date BETWEEN %s AND %s
                        AND WEEKDAY(trade_date) < 5
                        GROUP BY stock_code
                        HAVING total_volume > %s
                    ) as weekly_volumes
                    """
                    return query, (week_start, week_end, week_start, week_end, ranking_value)
            except Exception as e:
                logger.error(f"주차 계산 실패: {e}")
                return "SELECT 1 as ranking, 1 as total_stocks", (1,)
        elif chart_type == "월봉":
            year, month = target_date.split('-')
            if trading_type == "거래율":
                query = """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                        WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s 
                        AND WEEKDAY(trade_date) < 5 
                        AND outstanding_shares > 0) as total_stocks
                FROM (
                    SELECT stock_code, AVG((volume / outstanding_shares) * 100) as avg_turnover_rate
                    FROM daily_data 
                    WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s
                    AND WEEKDAY(trade_date) < 5
                    AND outstanding_shares > 0
                    GROUP BY stock_code
                    HAVING avg_turnover_rate > %s
                ) as monthly_turnover_rates
                """
                return query, (year, month, year, month, ranking_value)
            else:
                query = """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                        WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s 
                        AND WEEKDAY(trade_date) < 5) as total_stocks
                FROM (
                    SELECT stock_code, SUM(volume) as total_volume
                    FROM daily_data 
                    WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s
                    AND WEEKDAY(trade_date) < 5
                    GROUP BY stock_code
                    HAVING total_volume > %s
                ) as monthly_volumes
                """
                return query, (year, month, year, month, ranking_value)
        return "SELECT 1 as ranking, 1 as total_stocks", (1,)
    
    def _build_ranking_calculation_query(self, target_date: str, chart_type: str, 
                                       trading_type: str, ranking_value: float) -> str:
        """순위 계산 쿼리 생성"""
        if chart_type == "일봉":
            if trading_type == "거래율":
                return """
                SELECT COUNT(*) + 1 as ranking, 
                       (SELECT COUNT(*) FROM daily_data WHERE trade_date = %s AND outstanding_shares > 0) as total_stocks
                FROM daily_data 
                WHERE trade_date = %s 
                AND outstanding_shares > 0
                AND (volume / outstanding_shares) * 100 > %s
                """
            else:
                return """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(*) FROM daily_data WHERE trade_date = %s) as total_stocks
                FROM daily_data 
                WHERE trade_date = %s 
                AND volume > %s
                """
        elif chart_type == "주봉":
            if trading_type == "거래율":
                return """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                        WHERE trade_date BETWEEN %s AND %s 
                        AND WEEKDAY(trade_date) < 5 
                        AND outstanding_shares > 0) as total_stocks
                FROM (
                    SELECT stock_code, AVG((volume / outstanding_shares) * 100) as avg_turnover_rate
                    FROM daily_data 
                    WHERE trade_date BETWEEN %s AND %s
                    AND WEEKDAY(trade_date) < 5
                    AND outstanding_shares > 0
                    GROUP BY stock_code
                    HAVING avg_turnover_rate > %s
                ) as weekly_turnover_rates
                """
            else:
                return """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                        WHERE trade_date BETWEEN %s AND %s 
                        AND WEEKDAY(trade_date) < 5) as total_stocks
                FROM (
                    SELECT stock_code, SUM(volume) as total_volume
                    FROM daily_data 
                    WHERE trade_date BETWEEN %s AND %s
                    AND WEEKDAY(trade_date) < 5
                    GROUP BY stock_code
                    HAVING total_volume > %s
                ) as weekly_volumes
                """
        elif chart_type == "월봉":
            if trading_type == "거래율":
                return """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                        WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s 
                        AND WEEKDAY(trade_date) < 5 
                        AND outstanding_shares > 0) as total_stocks
                FROM (
                    SELECT stock_code, AVG((volume / outstanding_shares) * 100) as avg_turnover_rate
                    FROM daily_data 
                    WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s
                    AND WEEKDAY(trade_date) < 5
                    AND outstanding_shares > 0
                    GROUP BY stock_code
                    HAVING avg_turnover_rate > %s
                ) as monthly_turnover_rates
                """
            else:
                return """
                SELECT COUNT(*) + 1 as ranking,
                       (SELECT COUNT(DISTINCT stock_code) FROM daily_data 
                        WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s 
                        AND WEEKDAY(trade_date) < 5) as total_stocks
                FROM (
                    SELECT stock_code, SUM(volume) as total_volume
                    FROM daily_data 
                    WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s
                    AND WEEKDAY(trade_date) < 5
                    GROUP BY stock_code
                    HAVING total_volume > %s
                ) as monthly_volumes
                """
        return "SELECT 1 as ranking, 1 as total_stocks"
    
    def _build_ranking_list_query(self, target_date: str, chart_type: str, 
                                trading_type: str, limit: int) -> Tuple[str, tuple]:
        """순위 리스트 조회 쿼리 생성"""
        if chart_type == "일봉":
            if trading_type == "거래율":
                query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    d.volume,
                    d.close * d.volume as transaction_amount,
                    (d.volume / d.outstanding_shares) * 100 as turnover_rate,
                    d.outstanding_shares,
                    ROW_NUMBER() OVER (ORDER BY (d.volume / d.outstanding_shares) * 100 DESC) as ranking
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date = %s
                AND d.outstanding_shares > 0
                ORDER BY turnover_rate DESC
                LIMIT %s
                """
            else:
                query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    d.volume,
                    d.close * d.volume as transaction_amount,
                    (d.volume / d.outstanding_shares) * 100 as turnover_rate,
                    d.outstanding_shares,
                    ROW_NUMBER() OVER (ORDER BY d.volume DESC) as ranking
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE d.trade_date = %s
                ORDER BY d.volume DESC
                LIMIT %s
                """
            return query, (target_date, limit)
        
        elif chart_type == "주봉":
            # week_calculator.py 활용하여 주간 기간 계산
            try:
                target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
                year, week = get_week_number(target_datetime)
                week_start = WeekCalculator.get_week_start_date(year, week)
                week_end = WeekCalculator.get_week_end_date(year, week)
                
                if trading_type == "거래율":
                    query = """
                    SELECT 
                        d.stock_code,
                        s.stock_name,
                        s.market_type,
                        SUM(d.volume) as volume,
                        SUM(d.close * d.volume) as transaction_amount,
                        (SUM(d.volume) / AVG(d.outstanding_shares)) * 100 as turnover_rate,
                        AVG(d.outstanding_shares) as outstanding_shares,
                        ROW_NUMBER() OVER (ORDER BY (SUM(d.volume) / AVG(d.outstanding_shares)) * 100 DESC) as ranking
                    FROM daily_data d
                    JOIN stocks s ON d.stock_code = s.stock_code
                    WHERE d.trade_date BETWEEN %s AND %s
                    AND WEEKDAY(d.trade_date) < 5
                    AND d.outstanding_shares > 0
                    GROUP BY d.stock_code, s.stock_name, s.market_type
                    HAVING SUM(d.volume) > 0 AND AVG(d.outstanding_shares) > 0
                    ORDER BY turnover_rate DESC
                    LIMIT %s
                    """
                else:
                    query = """
                    SELECT 
                        d.stock_code,
                        s.stock_name,
                        s.market_type,
                        SUM(d.volume) as volume,
                        SUM(d.close * d.volume) as transaction_amount,
                        (SUM(d.volume) / AVG(d.outstanding_shares)) * 100 as turnover_rate,
                        AVG(d.outstanding_shares) as outstanding_shares,
                        ROW_NUMBER() OVER (ORDER BY SUM(d.volume) DESC) as ranking
                    FROM daily_data d
                    JOIN stocks s ON d.stock_code = s.stock_code
                    WHERE d.trade_date BETWEEN %s AND %s
                    AND WEEKDAY(d.trade_date) < 5
                    GROUP BY d.stock_code, s.stock_name, s.market_type
                    HAVING SUM(d.volume) > 0
                    ORDER BY volume DESC
                    LIMIT %s
                    """
                return query, (week_start, week_end, limit)
            except Exception as e:
                logger.error(f"주차 계산 실패: {e}")
                return "SELECT 1 as ranking", (1,)
        
        elif chart_type == "월봉":
            year, month = target_date.split('-')
            if trading_type == "거래율":
                query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    SUM(d.volume) as volume,
                    SUM(d.close * d.volume) as transaction_amount,
                    (SUM(d.volume) / AVG(d.outstanding_shares)) * 100 as turnover_rate,
                    AVG(d.outstanding_shares) as outstanding_shares,
                    ROW_NUMBER() OVER (ORDER BY (SUM(d.volume) / AVG(d.outstanding_shares)) * 100 DESC) as ranking
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE YEAR(d.trade_date) = %s AND MONTH(d.trade_date) = %s
                AND WEEKDAY(d.trade_date) < 5
                AND d.outstanding_shares > 0
                GROUP BY d.stock_code, s.stock_name, s.market_type
                HAVING SUM(d.volume) > 0 AND AVG(d.outstanding_shares) > 0
                ORDER BY turnover_rate DESC
                LIMIT %s
                """
            else:
                query = """
                SELECT 
                    d.stock_code,
                    s.stock_name,
                    s.market_type,
                    SUM(d.volume) as volume,
                    SUM(d.close * d.volume) as transaction_amount,
                    (SUM(d.volume) / AVG(d.outstanding_shares)) * 100 as turnover_rate,
                    AVG(d.outstanding_shares) as outstanding_shares,
                    ROW_NUMBER() OVER (ORDER BY SUM(d.volume) DESC) as ranking
                FROM daily_data d
                JOIN stocks s ON d.stock_code = s.stock_code
                WHERE YEAR(d.trade_date) = %s AND MONTH(d.trade_date) = %s
                AND WEEKDAY(d.trade_date) < 5
                GROUP BY d.stock_code, s.stock_name, s.market_type
                HAVING SUM(d.volume) > 0
                ORDER BY volume DESC
                LIMIT %s
                """
            return query, (year, month, limit)
        
        return "SELECT 1 as ranking", (1,)
    
    def _get_default_ranking_info(self) -> Dict[str, Any]:
        """기본 순위 정보 반환"""
        return {
            'ranking': 1,
            'transaction_amount': 0.0,
            'turnover_rate': 0.0,
            'total_stocks': 1,
            'volume': 0,
            'close_price': 0,
            'outstanding_shares': 0
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        logger.info("순위 계산 캐시가 초기화되었습니다.")


# 편의 함수들
def calculate_individual_ranking(stock_code: str, target_date: str, 
                               chart_type: str, trading_type: str = "거래대금") -> Dict[str, Any]:
    """개별 종목 순위 계산 (편의 함수)"""
    calculator = RankingCalculator()
    return calculator.calculate_individual_ranking(stock_code, target_date, chart_type, trading_type)


def get_volume_ranking(target_date: str, chart_type: str, 
                      limit: int = 50, trading_type: str = "거래대금") -> List[Dict[str, Any]]:
    """전체 순위 리스트 조회 (편의 함수)"""
    calculator = RankingCalculator()
    return calculator.get_volume_ranking(target_date, chart_type, limit, trading_type)


def get_turnover_ranking(target_date: str, chart_type: str, 
                        limit: int = 50) -> List[Dict[str, Any]]:
    """전체 순위 리스트 조회 - 거래율 기준 (편의 함수)"""
    calculator = RankingCalculator()
    return calculator.get_turnover_ranking(target_date, chart_type, limit)


# 테스트 함수
def test_ranking_calculator():
    """순위 계산기 테스트"""
    print("📊 순위 계산기 테스트")
    print("=" * 50)
    
    calculator = RankingCalculator()
    
    # 거래대금 계산 테스트
    print("💰 거래대금 계산 테스트:")
    print(f"  종가 × 거래량: {calculator.calculate_transaction_amount(1000, 50000):,.0f}원")
    print(f"  Typical Price: {calculator.calculate_transaction_amount(1000, 50000, 52000, 48000, 'typical_price'):,.0f}원")
    
    # 거래율 계산 테스트
    print(f"\n📈 거래율 계산 테스트:")
    print(f"  거래율: {calculator.calculate_turnover_rate(1000, 1000000):.2f}%")
    
    print(f"\n✅ 테스트 완료!")


if __name__ == "__main__":
    test_ranking_calculator()
