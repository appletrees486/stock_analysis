#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
랭킹 데이터 추출 모듈
거래율/거래대금 상위 50위를 추출하여 txt 파일로 저장
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ranking_calculator import RankingCalculator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ranking_extractor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class RankingDataExtractor:
    """랭킹 데이터 추출 클래스"""
    
    def __init__(self):
        """초기화"""
        self.ranking_calculator = RankingCalculator()
        self.output_dir = "uploads/stock_lists"
        
        # 출력 디렉토리 생성
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"출력 디렉토리 생성: {self.output_dir}")
    
    def extract_rankings(self, target_date: str = None, chart_type: str = "일봉", batch_id: str = None) -> Dict[str, Any]:
        """
        거래율/거래대금 상위 50위 추출 및 txt 파일 저장
        
        Args:
            target_date (str): 대상 날짜 (None이면 daily_data의 최신 trade_date)
            chart_type (str): 차트 타입 (일봉, 주봉, 월봉)
            batch_id (str): 배치 ID (파일명에 포함)
            
        Returns:
            Dict[str, Any]: 추출 결과
        """
        try:
            # 대상 날짜 설정
            if target_date is None:
                # daily_data에서 가장 최신 trade_date 조회
                from database_config import DatabaseManager
                db = DatabaseManager()
                
                if db.connect():
                    query = "SELECT MAX(trade_date) as latest_date FROM daily_data"
                    result = db.fetch_one(query)
                    db.disconnect()
                    
                    if result and result.get('latest_date'):
                        target_date = result['latest_date'].strftime('%Y-%m-%d') if hasattr(result['latest_date'], 'strftime') else str(result['latest_date'])
                        logger.info(f"daily_data 최신 날짜 사용: {target_date}")
                    else:
                        # 데이터가 없으면 오늘 날짜 사용 (fallback)
                        target_date = datetime.now().strftime('%Y-%m-%d')
                        logger.warning(f"daily_data가 비어있어 오늘 날짜 사용: {target_date}")
                else:
                    # DB 연결 실패 시 오늘 날짜 사용 (fallback)
                    target_date = datetime.now().strftime('%Y-%m-%d')
                    logger.warning(f"DB 연결 실패로 오늘 날짜 사용: {target_date}")
            
            logger.info(f"랭킹 데이터 추출 시작: {target_date} ({chart_type})")
            
            results = {
                'target_date': target_date,
                'chart_type': chart_type,
                'turnover_file': None,
                'volume_file': None,
                'turnover_count': 0,
                'volume_count': 0,
                'success': False,
                'error': None
            }
            
            # 1. 거래율 상위 50위 추출
            try:
                logger.info("거래율 상위 50위 추출 중...")
                turnover_ranking = self.ranking_calculator.get_turnover_ranking(
                    target_date=target_date,
                    chart_type=chart_type,
                    limit=50
                )
                
                if turnover_ranking:
                    # txt 파일 저장
                    turnover_file = self._save_to_txt(
                        turnover_ranking, 
                        target_date, 
                        chart_type, 
                        "거래율",
                        batch_id
                    )
                    results['turnover_file'] = turnover_file
                    results['turnover_count'] = len(turnover_ranking)
                    logger.info(f"거래율 상위 50위 추출 완료: {len(turnover_ranking)}개 종목")
                else:
                    logger.warning("거래율 랭킹 데이터가 없습니다.")
                    
            except Exception as e:
                logger.error(f"거래율 랭킹 추출 실패: {e}")
                results['error'] = f"거래율 랭킹 추출 실패: {str(e)}"
            
            # 2. 거래대금 상위 50위 추출
            try:
                logger.info("거래대금 상위 50위 추출 중...")
                volume_ranking = self.ranking_calculator.get_volume_ranking(
                    target_date=target_date,
                    chart_type=chart_type,
                    limit=50,
                    trading_type="거래대금"
                )
                
                if volume_ranking:
                    # txt 파일 저장
                    volume_file = self._save_to_txt(
                        volume_ranking, 
                        target_date, 
                        chart_type, 
                        "거래대금",
                        batch_id
                    )
                    results['volume_file'] = volume_file
                    results['volume_count'] = len(volume_ranking)
                    logger.info(f"거래대금 상위 50위 추출 완료: {len(volume_ranking)}개 종목")
                else:
                    logger.warning("거래대금 랭킹 데이터가 없습니다.")
                    
            except Exception as e:
                logger.error(f"거래대금 랭킹 추출 실패: {e}")
                results['error'] = f"거래대금 랭킹 추출 실패: {str(e)}"
            
            # 결과 검증
            if results['turnover_file'] and results['volume_file']:
                results['success'] = True
                logger.info("랭킹 데이터 추출 완료!")
            else:
                logger.warning("일부 랭킹 데이터 추출에 실패했습니다.")
            
            return results
            
        except Exception as e:
            logger.error(f"랭킹 데이터 추출 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_to_txt(self, ranking_data: List[Dict[str, Any]], 
                    target_date: str, chart_type: str, trading_type: str, batch_id: str = None) -> str:
        """
        랭킹 데이터를 txt 파일로 저장 (종목코드만)
        
        Args:
            ranking_data (List[Dict]): 랭킹 데이터
            target_date (str): 대상 날짜
            chart_type (str): 차트 타입
            trading_type (str): 거래 타입
            batch_id (str): 배치 ID (파일명에 포함)
            
        Returns:
            str: 저장된 파일 경로
        """
        try:
            # 파일명 생성
            chart_type_kr = chart_type  # 일봉, 주봉, 월봉
            trading_type_kr = trading_type  # 거래율, 거래대금
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            # 배치 ID가 있으면 파일명에 포함
            if batch_id:
                filename = f"{chart_type_kr}_{trading_type_kr}_랭킹_{batch_id}_{timestamp}.txt"
            else:
                filename = f"{chart_type_kr}_{trading_type_kr}_랭킹_{timestamp}.txt"
            
            filepath = os.path.join(self.output_dir, filename)
            
            # 종목코드만 추출
            stock_codes = [item['stock_code'] for item in ranking_data]
            
            # txt 파일 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                for stock_code in stock_codes:
                    f.write(f"{stock_code}\n")
            
            logger.info(f"파일 저장 완료: {filepath} ({len(stock_codes)}개 종목)")
            
            return filepath
            
        except Exception as e:
            logger.error(f"파일 저장 실패: {e}")
            raise
    
    def extract_rankings_for_auto_analysis(self, target_date: str = None, batch_id: str = None) -> Dict[str, Any]:
        """
        자동 분석을 위한 랭킹 추출 (일봉만)
        
        Args:
            target_date (str): 대상 날짜 (None이면 오늘)
            batch_id (str): 배치 ID (파일명에 포함)
            
        Returns:
            Dict[str, Any]: 추출 결과
        """
        return self.extract_rankings(target_date=target_date, chart_type="일봉", batch_id=batch_id)


def main():
    """테스트 함수"""
    logger.info("랭킹 데이터 추출기 테스트 시작")
    
    extractor = RankingDataExtractor()
    
    # 최신 거래일로 테스트 (2025-10-13)
    result = extractor.extract_rankings_for_auto_analysis(target_date='2025-10-13')
    
    if result.get('success'):
        logger.info("테스트 성공!")
        logger.info(f"거래율 파일: {result.get('turnover_file')}")
        logger.info(f"거래대금 파일: {result.get('volume_file')}")
        logger.info(f"거래율 종목 수: {result.get('turnover_count')}")
        logger.info(f"거래대금 종목 수: {result.get('volume_count')}")
    else:
        logger.error("테스트 실패!")
        logger.error(f"오류: {result.get('error')}")


if __name__ == "__main__":
    main()

