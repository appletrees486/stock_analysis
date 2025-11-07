#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주봉 자동 분석 및 블로그 작성 모듈
랭킹 추출 → 주봉 분석 → 블로그 작성
"""

# UTF-8 인코딩 설정 (Windows 환경 대응)
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
import sys
import threading
import glob
import zipfile
import shutil
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weekly_auto_blog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 필요한 모듈 임포트
from week_calculator import get_week_number
from ranking_data_extractor import RankingDataExtractor
from database_config import DatabaseManager

# week_stock_analysis.py 함수들
from week_stock_analysis import (
    get_weekly_stock_data,
    create_weekly_stock_chart,
    save_chart_data_to_json,
    get_stock_name
)

# week_calculator 추가 import
from week_calculator import (
    get_week_number,
    get_week_start_date,
    get_week_end_date
)

# week_stock_analysis 추가 import
from week_stock_analysis import is_complete_week
from korean_holiday_manager import KoreanHolidayManager

# ai_chart_analysis.py
import ai_chart_analysis

# config, database_config
from config import config
from database_config import get_db_config


class WeeklyAutoBlog:
    """주봉 자동 분석 및 블로그 작성 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        
    def extract_weekly_rankings(self, year: int, week: int, limit: int = 50) -> Optional[Dict]:
        """
        주봉 랭킹 추출
        
        Args:
            year: 연도
            week: 주차
            limit: 추출할 랭킹 수 (기본 50개)
            
        Returns:
            Dict: 추출 결과 (turnover_file, volume_file)
        """
        try:
            logger.info(f"📊 주봉 랭킹 추출 시작: {year}년 {week}주차 (limit={limit})")
            
            # RankingDataExtractor 초기화
            extractor = RankingDataExtractor()
            
            # batch_id 생성
            batch_id = f"weekly_{year}_{week}"
            
            # 주봉 랭킹 추출 - limit 지원을 위해 직접 RankingCalculator 호출
            from ranking_calculator import RankingCalculator
            ranking_calculator = RankingCalculator()
            
            # DB 최신 거래일 조회 (주봉 기준 날짜)
            if not self.db.connect():
                logger.error("DB 연결 실패")
                return None
            
            query = "SELECT MAX(trade_date) as latest_date FROM daily_data"
            date_result = self.db.fetch_one(query)
            self.db.disconnect()
            
            if not date_result or not date_result.get('latest_date'):
                logger.error("최신 거래일을 찾을 수 없습니다")
                return None
            
            target_date = date_result['latest_date'].strftime('%Y-%m-%d')
            
            # ✅ 주차 완성도 확인
            from korean_holiday_manager import KoreanHolidayManager
            from datetime import date as date_type
            
            holiday_manager = KoreanHolidayManager()
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            target_year, target_week = get_week_number(target_date_obj)
            
            # 해당 주차의 시작일/종료일 확인
            from week_calculator import WeekCalculator
            week_start = WeekCalculator.get_week_start_date(target_year, target_week)
            week_end = WeekCalculator.get_week_end_date(target_year, target_week)
            
            # DB 최신 거래일이 해당 주차의 며칠째인지 확인
            current_date_obj = date_result['latest_date']
            if isinstance(current_date_obj, str):
                current_date_obj = datetime.strptime(current_date_obj, '%Y-%m-%d').date()
            
            days_into_week = (current_date_obj - week_start).days
            total_days_in_week = (week_end - week_start).days + 1
            
            # 주차 진행률 계산
            week_progress = (days_into_week / total_days_in_week) * 100 if total_days_in_week > 0 else 0
            
            logger.info(f"랭킹 추출 대상 날짜: {target_date}")
            logger.info(f"주차 정보: {target_year}년 {target_week}주차")
            logger.info(f"주차 기간: {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")
            logger.info(f"현재 진행률: {week_progress:.1f}% ({days_into_week}/{total_days_in_week}일)")
            
            # 주차 완성도 경고
            if days_into_week < total_days_in_week:
                logger.warning(f"⚠️ 해당 주차는 아직 완성되지 않았습니다.")
                logger.warning(f"💡 주차 완료 후 다시 실행하시면 더 정확한 랭킹을 얻을 수 있습니다.")
            else:
                logger.info(f"✅ 해당 주차가 완성되었습니다.")
            
            # 1. 거래율 상위 limit 개 추출
            turnover_ranking = ranking_calculator.get_turnover_ranking(
                target_date=target_date,
                chart_type="주봉",
                limit=limit
            )
            
            # 2. 거래대금 상위 limit 개 추출
            volume_ranking = ranking_calculator.get_volume_ranking(
                target_date=target_date,
                chart_type="주봉",
                limit=limit
            )
            
            # 파일 저장
            results = {
                'target_date': target_date,
                'chart_type': '주봉',
                'turnover_file': None,
                'volume_file': None,
                'turnover_count': 0,
                'volume_count': 0,
                'success': False,
                'error': None
            }
            
            if turnover_ranking:
                turnover_file = self._save_ranking_to_txt(
                    turnover_ranking,
                    target_date,
                    '주봉',
                    '거래율',
                    batch_id
                )
                results['turnover_file'] = turnover_file
                results['turnover_count'] = len(turnover_ranking)
                logger.info(f"거래율 상위 {limit}위 추출 완료: {len(turnover_ranking)}개")
            
            if volume_ranking:
                volume_file = self._save_ranking_to_txt(
                    volume_ranking,
                    target_date,
                    '주봉',
                    '거래대금',
                    batch_id
                )
                results['volume_file'] = volume_file
                results['volume_count'] = len(volume_ranking)
                logger.info(f"거래대금 상위 {limit}위 추출 완료: {len(volume_ranking)}개")
            
            results['success'] = bool(results['turnover_file'] and results['volume_file'])
            
            result = results
            
            if not result.get('success'):
                logger.error(f"❌ 주봉 랭킹 추출 실패: {result.get('error')}")
                return None
            
            logger.info(f"✅ 주봉 랭킹 추출 완료")
            logger.info(f"   - 거래율 파일: {result.get('turnover_file')}")
            logger.info(f"   - 거래대금 파일: {result.get('volume_file')}")
            logger.info(f"   - 거래율 종목 수: {result.get('turnover_count')}")
            logger.info(f"   - 거래대금 종목 수: {result.get('volume_count')}")
            
            return result
            
        except Exception as e:
            logger.error(f"주봉 랭킹 추출 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _save_ranking_to_txt(self, ranking_data: List[Dict], target_date: str, chart_type: str, trading_type: str, batch_id: str) -> str:
        """
        랭킹 데이터를 txt 파일로 저장 (종목코드만)
        
        Args:
            ranking_data: 랭킹 데이터 리스트
            target_date: 대상 날짜
            chart_type: 차트 타입
            trading_type: 거래 타입
            batch_id: 배치 ID
            
        Returns:
            str: 저장된 파일 경로
        """
        try:
            # 출력 디렉토리 생성
            output_dir = "uploads/stock_lists"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 파일명 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            if batch_id:
                filename = f"{chart_type}_{trading_type}_랭킹_{batch_id}_{timestamp}.txt"
            else:
                filename = f"{chart_type}_{trading_type}_랭킹_{timestamp}.txt"
            
            filepath = os.path.join(output_dir, filename)
            
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
    
    def read_stock_codes_from_file(self, file_path: str) -> List[str]:
        """
        txt 파일에서 종목코드 리스트 읽기
        
        Args:
            file_path: 파일 경로
            
        Returns:
            List[str]: 종목코드 리스트
        """
        try:
            stock_codes = []
            
            if not os.path.exists(file_path):
                logger.error(f"파일이 존재하지 않습니다: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stock_code = line.strip()
                    if stock_code:  # 빈 줄 제외
                        stock_codes.append(stock_code)
            
            logger.info(f"종목코드 {len(stock_codes)}개 로드: {file_path}")
            return stock_codes
            
        except Exception as e:
            logger.error(f"파일 읽기 실패: {file_path}, 오류: {e}")
            return []
    
    def analyze_weekly_stocks_from_file(self, file_path: str, trading_type: str, year: int, week: int) -> bool:
        """
        파일에서 종목 리스트를 읽어서 각각 주봉 분석
        
        Args:
            file_path: 종목 리스트 파일 경로
            trading_type: 거래 타입 ("거래율" 또는 "거래대금")
            year: 연도
            week: 주차
            
        Returns:
            bool: 성공 여부
        """
        try:
            logger.info(f"📈 주봉 분석 시작: {trading_type}")
            
            # 종목 리스트 읽기
            stock_codes = self.read_stock_codes_from_file(file_path)
            
            if not stock_codes:
                logger.warning(f"종목 리스트가 비어있습니다: {file_path}")
                return False
            
            logger.info(f"총 {len(stock_codes)}개 종목 분석 예정")
            
            # 각 종목별 주봉 분석
            success_count = 0
            failed_count = 0
            
            for i, stock_code in enumerate(stock_codes, 1):
                try:
                    logger.info(f"[{i}/{len(stock_codes)}] {stock_code} 분석 중...")
                    
                    # 1. 주봉 데이터 조회
                    weekly_data = get_weekly_stock_data(stock_code)
                    
                    if weekly_data is None or weekly_data.empty:
                        logger.error(f"주봉 데이터 조회 실패: {stock_code}")
                        failed_count += 1
                        continue
                    
                    # 2. 주봉 차트 생성
                    chart_result = create_weekly_stock_chart(weekly_data, stock_code)
                    
                    if not chart_result or len(chart_result) != 3:
                        logger.error(f"주봉 차트 생성 실패: {stock_code}")
                        failed_count += 1
                        continue
                    
                    chart_path, stock_name, chart_data = chart_result
                    
                    # 3. JSON 데이터 저장
                    json_path = save_chart_data_to_json(
                        chart_data, 
                        stock_code, 
                        stock_name, 
                        trading_type=trading_type
                    )
                    
                    if not json_path:
                        logger.error(f"JSON 데이터 저장 실패: {stock_code}")
                        failed_count += 1
                        continue
                    
                    # 4. AI 분석
                    api_key = config.get_api_key()
                    if not api_key:
                        logger.error(f"API 키를 가져올 수 없습니다")
                        failed_count += 1
                        continue
                    
                    db_config = get_db_config()
                    analyzer = ai_chart_analysis.AIChartAnalyzer(api_key, db_config)
                    
                    analysis_result = analyzer.analyze_chart_image(
                        image_path=chart_path,
                        stock_name=stock_name,
                        chart_type="주봉",
                        chart_data=chart_data,
                        json_data_path=json_path,
                        trading_type=trading_type
                    )
                    
                    if analysis_result:
                        # ✅ 결과 파일 저장 추가 (batch_stock_analyzer_optimized.py 로직 재사용)
                        from datetime import datetime as dt
                        output_dir = "ai_analysis_results"
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)
                        
                        timestamp = dt.now().strftime('%Y%m%d_%H%M%S')
                        batch_id = f"weekly_{year}_{week}"
                        
                        # 파일명 생성 (batch_stock_analyzer_optimized.py와 동일한 형식)
                        chart_type_en = "weekly"  # 주봉은 항상 weekly
                        base_filename = f"analysis_{chart_type_en}_{stock_code}_{timestamp}_{batch_id}"
                        result_json_path = os.path.join(output_dir, f"{base_filename}.json")
                        result_doc_path = os.path.join(output_dir, f"{base_filename}.docx")
                        
                        # JSON 저장
                        try:
                            json_success = analyzer.save_analysis_result(analysis_result, result_json_path)
                            if json_success:
                                logger.info(f"✅ {stock_code} 결과 JSON 저장: {result_json_path}")
                            else:
                                logger.error(f"❌ {stock_code} JSON 저장 실패")
                        except Exception as e:
                            logger.error(f"❌ {stock_code} JSON 저장 실패: {e}")
                            json_success = False
                        
                        # DOCX 저장 (항상 생성 - 비즈니스 로직 유지)
                        try:
                            doc_success = analyzer.create_word_document_hybrid(analysis_result, chart_path, result_doc_path, "주봉")
                            if doc_success:
                                logger.info(f"✅ {stock_code} 결과 DOCX 저장: {result_doc_path}")
                            else:
                                logger.error(f"❌ {stock_code} DOCX 저장 실패")
                        except Exception as e:
                            logger.error(f"❌ {stock_code} DOCX 저장 실패: {e}")
                            doc_success = False
                        
                        # 성공 여부 판단 (batch_stock_analyzer_optimized.py와 동일한 로직)
                        if json_success and doc_success:
                            logger.info(f"✅ {stock_code} ({stock_name}) AI 분석 및 저장 완료")
                            success_count += 1
                        else:
                            logger.error(f"❌ {stock_code} 파일 저장 실패 - JSON: {json_success}, DOCX: {doc_success}")
                            failed_count += 1
                    else:
                        logger.error(f"❌ {stock_code} AI 분석 실패")
                        failed_count += 1
                    
                except Exception as e:
                    logger.error(f"종목 {stock_code} 분석 중 오류: {e}")
                    failed_count += 1
                    continue
            
            logger.info(f"📊 주봉 분석 완료: {trading_type}")
            logger.info(f"   성공: {success_count}개, 실패: {failed_count}개")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"주봉 분석 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def analyze_weekly_charts(self, ranking_result: Dict, year: int, week: int) -> bool:
        """
        주봉 차트 분석 - 거래율/거래대금 분리 처리
        
        Args:
            ranking_result: 랭킹 추출 결과
            year: 연도
            week: 주차
            
        Returns:
            bool: 성공 여부
        """
        try:
            logger.info(f"📊 주봉 차트 분석 시작: {year}년 {week}주차")
            
            turnover_file = ranking_result.get('turnover_file')
            volume_file = ranking_result.get('volume_file')
            
            if not turnover_file or not os.path.exists(turnover_file):
                logger.error(f"거래율 파일을 찾을 수 없습니다: {turnover_file}")
                return False
            
            if not volume_file or not os.path.exists(volume_file):
                logger.error(f"거래대금 파일을 찾을 수 없습니다: {volume_file}")
                return False
            
            # 1. 거래율 상위 50위 주봉 분석
            logger.info(f"📈 거래율 상위 50위 주봉 분석 시작...")
            turnover_success = self.analyze_weekly_stocks_from_file(
                file_path=turnover_file,
                trading_type="거래율",
                year=year,
                week=week
            )
            
            if not turnover_success:
                logger.error("거래율 주봉 분석 실패")
            
            # 2. 거래대금 상위 50위 주봉 분석
            logger.info(f"💰 거래대금 상위 50위 주봉 분석 시작...")
            volume_success = self.analyze_weekly_stocks_from_file(
                file_path=volume_file,
                trading_type="거래대금",
                year=year,
                week=week
            )
            
            if not volume_success:
                logger.error("거래대금 주봉 분석 실패")
            
            # 전체 성공 여부
            overall_success = turnover_success and volume_success
            
            logger.info(f"📊 주봉 차트 분석 완료: {year}년 {week}주차")
            logger.info(f"   거래율 분석: {'성공' if turnover_success else '실패'}")
            logger.info(f"   거래대금 분석: {'성공' if volume_success else '실패'}")
            
            # ✅ Summary/Tag 파일 생성 및 ZIP 파일 생성 추가
            if overall_success:
                self.create_summary_and_zip(year, week)
            
            return overall_success
            
        except Exception as e:
            logger.error(f"주봉 차트 분석 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def create_summary_and_zip(self, year: int, week: int) -> bool:
        """
        Summary/Tag 파일 생성 및 ZIP 파일 생성
        
        Args:
            year: 연도
            week: 주차
            
        Returns:
            bool: 성공 여부
        """
        try:
            logger.info(f"📊 Summary/Tag 파일 및 ZIP 파일 생성 시작: {year}년 {week}주차")
            
            # 1. ai_analysis_results 폴더에서 주봉 관련 JSON 파일들 찾기
            batch_id = f"weekly_{year}_{week}"
            
            # 배치 ID가 포함된 파일만 찾기
            pattern = f"ai_analysis_results/analysis_weekly_*_{batch_id}.json"
            json_files = glob.glob(pattern)
            
            if not json_files:
                logger.warning(f"Summary 생성할 JSON 파일이 없습니다: {pattern}")
                return False
            
            logger.info(f"📄 발견된 분석 결과 파일: {len(json_files)}개")
            
            # 2. Summary 파일 생성 (batch_analyzer의 _create_summary_analysis 로직 재사용)
            from api.batch_analyzer import BatchAnalyzer
            batch_analyzer = BatchAnalyzer()
            
            summary_files = batch_analyzer._create_summary_analysis(
                chart_type='주봉',
                specific_files=json_files,
                batch_id=batch_id
            )
            
            if not summary_files:
                logger.warning(f"Summary 파일 생성 실패")
            else:
                logger.info(f"✅ Summary 파일 생성 완료: {summary_files}")
            
            # 3. ZIP 파일 생성 (batch_analyzer의 _save_batch_results 로직 재사용)
            try:
                # results 폴더 생성
                results_dir = "results"
                if not os.path.exists(results_dir):
                    os.makedirs(results_dir)
                
                # ZIP 파일명 생성
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                zip_filename = f"주봉_{year}년{week}주차_{batch_id}.zip"
                zip_path = os.path.join(results_dir, zip_filename)
                
                logger.info(f"📦 ZIP 파일 생성: {zip_path}")
                
                # ZIP 파일에 summary/tag 파일 추가
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Summary 파일들 추가 (batch_analyzer.py 구조 따라하기)
                    if summary_files:
                        # DOCX 파일 추가 - summary_analysis 폴더 안에
                        if summary_files.get('docx_path') and os.path.exists(summary_files['docx_path']):
                            # 파일명 추출
                            basename = os.path.basename(summary_files['docx_path'])
                            # summary_analysis 폴더 안에 저장 (batch_analyzer.py 구조)
                            zipf.write(summary_files['docx_path'], f"summary_analysis/{basename}")
                            logger.info(f"✅ Summary DOCX 추가: summary_analysis/{basename}")
                        
                        # JSON 파일 추가 - summary_analysis 폴더 안에
                        if summary_files.get('json_path') and os.path.exists(summary_files['json_path']):
                            basename = os.path.basename(summary_files['json_path'])
                            zipf.write(summary_files['json_path'], f"summary_analysis/{basename}")
                            logger.info(f"✅ Summary JSON 추가: summary_analysis/{basename}")
                    
                    # Tag 파일 찾아서 추가 (최상위에 tag.docx로 저장 - batch_analyzer.py 구조)
                    tag_pattern = f"ai_analysis_results/tag_{batch_id}_*.docx"
                    tag_files = glob.glob(tag_pattern)
                    tag_path = None
                    
                    if tag_files:
                        latest_tag = max(tag_files, key=os.path.getctime)
                        tag_path = latest_tag
                        logger.info(f"✅ Tag 파일 발견: {tag_path}")
                    else:
                        # 태그 파일이 없을 경우 기본 태그 파일 생성 (AI 생성 실패 시 대체)
                        logger.warning(f"⚠️ Tag 파일을 찾을 수 없습니다. 기본 태그 파일을 생성합니다.")
                        tag_path = self._create_default_tag_file(batch_id, year, week)
                    
                    if tag_path and os.path.exists(tag_path):
                        zipf.write(tag_path, "tag.docx")
                        logger.info(f"✅ Tag DOCX 추가: tag.docx")
                    else:
                        logger.error(f"❌ Tag DOCX 파일을 추가할 수 없습니다: {tag_path}")
                    
                    # Total Analysis 파일 추가 (batch_analyzer.py 구조)
                    try:
                        import tempfile
                        
                        # JSON 파일들에서 데이터 읽어오기
                        analysis_data_list = []
                        for json_file in json_files:
                            try:
                                with open(json_file, 'r', encoding='utf-8') as f:
                                    analysis_data = json.load(f)
                                    analysis_data_list.append(analysis_data)
                            except Exception as e:
                                logger.warning(f"JSON 파일 읽기 실패: {json_file}, {e}")
                                continue
                        
                        if analysis_data_list:
                            # Total Analysis JSON 생성
                            total_analysis_json = self._create_total_analysis_from_files(analysis_data_list, "주봉")
                            
                            if total_analysis_json:
                                # Total Analysis DOCX 생성 (임시 파일)
                                with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                                    temp_path = temp_file.name
                                
                                # batch_analyzer의 메서드 재사용
                                from api.batch_analyzer import BatchAnalyzer
                                batch_analyzer = BatchAnalyzer()
                                doc_success = batch_analyzer._create_total_analysis_docx(
                                    total_analysis_json, "주봉", temp_path, batch_id
                                )
                                
                                if doc_success:
                                    total_analysis_filename = f"total_analysis/통합요약_분석_weekly_{timestamp}.docx"
                                    zipf.write(temp_path, total_analysis_filename)
                                    logger.info(f"✅ Total Analysis DOCX 추가: {total_analysis_filename}")
                                    
                                    # 임시 파일 삭제
                                    os.unlink(temp_path)
                                else:
                                    logger.warning(f"Total Analysis DOCX 생성 실패")
                                    if os.path.exists(temp_path):
                                        os.unlink(temp_path)
                            else:
                                logger.warning(f"Total Analysis JSON 생성 실패")
                    except Exception as e:
                        logger.error(f"Total Analysis ZIP 추가 실패: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                logger.info(f"✅ ZIP 파일 생성 완료: {zip_path}")
                logger.info(f"📊 ZIP 파일 크기: {os.path.getsize(zip_path) if os.path.exists(zip_path) else 0} bytes")
                
                # 4. blog_auto/docs 폴더에 복사
                docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog_auto", "docs")
                if not os.path.exists(docs_dir):
                    os.makedirs(docs_dir)
                
                docs_zip_path = os.path.join(docs_dir, os.path.basename(zip_path))
                shutil.copy2(zip_path, docs_zip_path)
                logger.info(f"✅ ZIP 파일을 blog_auto/docs 폴더에 복사: {docs_zip_path}")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ ZIP 파일 생성 실패: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
            
        except Exception as e:
            logger.error(f"Summary/ZIP 파일 생성 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _create_total_analysis_from_files(self, analysis_data_list: List[Dict], chart_type: str) -> Dict:
        """
        JSON 파일들로부터 Total Analysis 생성
        
        Args:
            analysis_data_list: JSON 파일에서 로드한 분석 데이터 리스트
            chart_type: 차트 유형
            
        Returns:
            dict: Total Analysis JSON 데이터
        """
        try:
            logger.info(f"Total Analysis 생성 시작: {len(analysis_data_list)}개 파일")
            
            # 거래정보 통계 수집
            trading_stats = {
                "거래대금_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "원"},
                "거래률_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "%"},
                "순위_통계": {"1위": 0, "10위이내": 0, "50위이내": 0, "100위이내": 0},
                "거래타입_분포": {"거래대금": 0, "거래율": 0},
                "유통주식수_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "주"},
                "거래량_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "주"}
            }
            
            valid_trading_data = 0
            
            # 메타데이터
            total_analysis = {
                "metadata": {
                    "chart_type": chart_type,
                    "total_stocks": len(analysis_data_list),
                    "created_at": datetime.now().isoformat(),
                    "analysis_version": "1.0",
                    "file_type": "total_analysis"
                },
                "consolidated_analysis": {},
                "trading_statistics": trading_stats
            }
            
            # 각 종목별 분석 결과 추가
            for analysis_data in analysis_data_list:
                try:
                    stock_code = analysis_data.get("종목정보", {}).get("종목번호", "000000")
                    stock_name = analysis_data.get("종목정보", {}).get("종목명", "알수없음")
                    
                    # 거래정보 통계 수집
                    if "종목정보" in analysis_data:
                        trading_info = analysis_data["종목정보"]
                        
                        # 거래대금 파싱 및 통계 수집
                        trading_amount_str = trading_info.get("거래대금", "0")
                        trading_amount = self._parse_trading_amount(trading_amount_str)
                        if trading_amount > 0:
                            trading_stats["거래대금_통계"]["총합"] += trading_amount
                            trading_stats["거래대금_통계"]["최대"] = max(trading_stats["거래대금_통계"]["최대"], trading_amount)
                            trading_stats["거래대금_통계"]["최소"] = min(trading_stats["거래대금_통계"]["최소"], trading_amount)
                        
                        # 거래율 파싱 및 통계 수집
                        turnover_rate_str = trading_info.get("거래율", "0%")
                        turnover_rate = self._parse_percentage(turnover_rate_str)
                        if turnover_rate > 0:
                            trading_stats["거래률_통계"]["총합"] += turnover_rate
                            trading_stats["거래률_통계"]["최대"] = max(trading_stats["거래률_통계"]["최대"], turnover_rate)
                            trading_stats["거래률_통계"]["최소"] = min(trading_stats["거래률_통계"]["최소"], turnover_rate)
                        
                        # 순위 통계 수집
                        ranking_str = trading_info.get("순위", "999위")
                        ranking = self._parse_ranking(ranking_str)
                        if ranking == 1:
                            trading_stats["순위_통계"]["1위"] += 1
                        elif ranking <= 10:
                            trading_stats["순위_통계"]["10위이내"] += 1
                        elif ranking <= 50:
                            trading_stats["순위_통계"]["50위이내"] += 1
                        elif ranking <= 100:
                            trading_stats["순위_통계"]["100위이내"] += 1
                        
                        # 거래타입 분포 수집
                        trading_type = trading_info.get("거래타입", "거래대금")
                        if trading_type in trading_stats["거래타입_분포"]:
                            trading_stats["거래타입_분포"][trading_type] += 1
                        
                        valid_trading_data += 1
                    
                    # 개별 종목의 전체 구조를 그대로 유지하면서 키-값 형태로 저장
                    total_analysis["consolidated_analysis"][stock_code] = analysis_data
                    
                    logger.info(f"종목 {stock_code} ({stock_name}) 분석 데이터 추가 완료")
                    
                except Exception as e:
                    logger.warning(f"JSON 데이터 처리 실패: {e}")
                    continue
            
            # 통계 계산
            if valid_trading_data > 0:
                # 평균 계산
                trading_stats["거래대금_통계"]["평균"] = trading_stats["거래대금_통계"]["총합"] / valid_trading_data
                trading_stats["거래률_통계"]["평균"] = trading_stats["거래률_통계"]["총합"] / valid_trading_data
                
                # 최소값이 무한대인 경우 0으로 설정
                if trading_stats["거래대금_통계"]["최소"] == float('inf'):
                    trading_stats["거래대금_통계"]["최소"] = 0
                if trading_stats["거래률_통계"]["최소"] == float('inf'):
                    trading_stats["거래률_통계"]["최소"] = 0
            
            # 통계 정보를 메타데이터에 추가
            total_analysis["metadata"]["trading_data_count"] = valid_trading_data
            total_analysis["metadata"]["trading_statistics"] = trading_stats
            
            logger.info(f"Total Analysis JSON 생성 완료: {len(total_analysis['consolidated_analysis'])}개 종목 (거래정보: {valid_trading_data}개)")
            
            return total_analysis
            
        except Exception as e:
            logger.error(f"Total Analysis 생성 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_trading_amount(self, amount_str: str) -> float:
        """거래대금 문자열을 숫자로 변환 (예: '5263억원' -> 526300000000)"""
        try:
            if not amount_str or amount_str == "N/A":
                return 0
            
            import re
            clean_str = amount_str.replace(',', '')
            match = re.search(r'([\d.]+)(억원|만원|원)?', clean_str)
            if not match:
                return 0
            
            number = float(match.group(1))
            unit = match.group(2) or "원"
            
            if unit == "억원":
                return number * 100000000
            elif unit == "만원":
                return number * 10000
            else:
                return number
        except:
            return 0
    
    def _parse_percentage(self, percent_str: str) -> float:
        """퍼센트 문자열을 숫자로 변환 (예: '1250.18%' -> 1250.18)"""
        try:
            if not percent_str or percent_str == "N/A":
                return 0
            
            import re
            match = re.search(r'([\d.]+)%', percent_str)
            if match:
                return float(match.group(1))
            return 0
        except:
            return 0
    
    def _parse_ranking(self, ranking_str: str) -> int:
        """순위 문자열을 숫자로 변환 (예: '1위' -> 1)"""
        try:
            if not ranking_str or ranking_str == "N/A":
                return 999
            
            import re
            match = re.search(r'(\d+)위', ranking_str)
            if match:
                return int(match.group(1))
            return 999
        except:
            return 999
    
    def _create_default_tag_file(self, batch_id: str, year: int, week: int) -> str:
        """
        기본 태그 파일 생성 (AI 태그 생성 실패 시 대체)
        
        Args:
            batch_id: 배치 ID
            year: 연도
            week: 주차
            
        Returns:
            str: 생성된 태그 파일 경로 또는 None
        """
        try:
            logger.info(f"🏷️ 기본 태그 파일 생성 시작: {year}년 {week}주차")
            
            output_dir = "ai_analysis_results"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            tag_filename = f"tag_{batch_id}_{timestamp}.docx"
            tag_path = os.path.join(output_dir, tag_filename)
            
            # 기본 태그 텍스트 생성 (차트 타입, 연도, 주차 정보 포함)
            default_tag_text = f"주봉, {year}년 {week}주차, 주식분석, 기술적분석, 투자분석, 차트분석"
            
            # DOCX 파일 생성
            from docx import Document
            from docx.oxml.ns import qn
            
            doc = Document()
            
            # 태그 텍스트를 문단으로 추가
            para = doc.add_paragraph(default_tag_text)
            
            # 한글 폰트 적용
            for run in para.runs:
                run.font.name = '맑은 고딕'
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            # 문서 저장
            doc.save(tag_path)
            logger.info(f"✅ 기본 태그 파일 생성 완료: {tag_path}")
            
            return tag_path
            
        except Exception as e:
            logger.error(f"❌ 기본 태그 파일 생성 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def write_blog_posts(self, year: int, week: int) -> bool:
        """
        블로그 자동 작성
        
        Args:
            year: 연도
            week: 주차
            
        Returns:
            bool: 성공 여부
        """
        try:
            logger.info(f"📝 블로그 자동 작성 시작: {year}년 {week}주차")
            
            # batch_scheduler.py의 _run_blog_writing_async() 로직 재사용
            import sys
            import os
            
            # 프로젝트 루트 및 blog_auto 디렉토리 경로 설정
            project_root = os.path.dirname(os.path.abspath(__file__))
            blog_auto_path = os.path.join(project_root, 'blog_auto')
            docs_path = os.path.join(blog_auto_path, 'docs')
            
            logger.info(f"[DEBUG] 프로젝트 루트: {project_root}")
            logger.info(f"[DEBUG] blog_auto 경로: {blog_auto_path}")
            logger.info(f"[DEBUG] docs 경로: {docs_path}")
            
            # blog_auto 디렉토리를 경로에 추가
            if blog_auto_path not in sys.path:
                sys.path.insert(0, blog_auto_path)
            
            # docs 디렉토리 존재 확인
            if not os.path.exists(docs_path):
                logger.warning(f"⚠️ docs 디렉토리가 존재하지 않습니다: {docs_path}")
                logger.info(f"📁 docs 디렉토리를 생성합니다...")
                os.makedirs(docs_path, exist_ok=True)
            
            from auto_blog import NaverBlogBot
            
            # 블로그 봇 인스턴스 생성 (일반 모드 - 캡챠 처리 가능)
            bot = NaverBlogBot(headless=False, debug_mode=True)
            
            try:
                # 로그인
                if not bot.run_login():
                    logger.error(f"❌ 블로그 로그인 실패: {year}년 {week}주차")
                    return False
                
                logger.info(f"✅ 블로그 로그인 성공: {year}년 {week}주차")
                
                # docs 경로 확인
                if not os.path.exists(docs_path):
                    logger.error(f"❌ docs 디렉토리를 찾을 수 없습니다: {docs_path}")
                    return False
                
                # docs 디렉토리의 zip 파일 확인
                zip_files = [f for f in os.listdir(docs_path) if f.endswith('.zip')]
                logger.info(f"📂 docs 디렉토리: {docs_path}")
                logger.info(f"📦 발견된 zip 파일: {len(zip_files)}개")
                
                if zip_files:
                    for zip_file in zip_files:
                        logger.info(f"   - {zip_file}")
                
                # docs 폴더의 zip 파일 처리 및 블로그 작성
                if bot.docs_zip_processor:
                    # 미처리 zip 파일 확인
                    unprocessed_zips = bot.get_unprocessed_zips()
                    
                    if not unprocessed_zips:
                        logger.info(f"📭 처리할 zip 파일이 없습니다: {year}년 {week}주차")
                        logger.info(f"   (총 {len(zip_files)}개 zip 파일이 있지만 모두 처리됨)")
                        return True
                    
                    logger.info(f"📦 총 {len(unprocessed_zips)}개의 zip 파일 처리 시작")
                    
                    # 각 zip 파일 처리
                    success_count = 0
                    for zip_path in unprocessed_zips:
                        zip_filename = os.path.basename(zip_path)
                        logger.info(f"📝 블로그 작성 중: {zip_filename}")
                        
                        try:
                            # 단일 zip 파일 처리
                            blog_post = bot.docs_zip_processor.process_single_zip_file(zip_path)
                            
                            if not blog_post:
                                logger.error(f"❌ ZIP 파일 처리 실패: {zip_filename}")
                                continue
                            
                            # 블로그 글쓰기 페이지로 이동
                            if not bot.navigate_to_blog_write():
                                logger.error(f"❌ 블로그 글쓰기 페이지 이동 실패")
                                continue
                            
                            # iframe으로 전환
                            if not bot.switch_to_blog_frame():
                                logger.error(f"❌ iframe 전환 실패")
                                continue
                            
                            # 팝업 닫기
                            bot.close_popups_and_help()
                            
                            # 제목 입력
                            if not bot.enter_blog_title(blog_post['title']):
                                logger.error(f"❌ 제목 입력 실패")
                                continue
                            
                            # 내용과 표 입력
                            if not bot.write_content_with_structured_tables(blog_post['content'], blog_post['tables']):
                                logger.error(f"❌ 내용 입력 실패")
                                continue
                            
                            # 첨부파일 추가
                            if blog_post.get('attachment_file'):
                                if not bot.add_file_to_blog(blog_post['attachment_file']):
                                    logger.warning(f"⚠️ 첨부파일 추가 실패")
                            
                            # 분석월 추출 (ZIP 파일명에서)
                            analysis_month = None
                            try:
                                from zip_analyzer import ZipAnalyzer
                                zip_analyzer = ZipAnalyzer()
                                zip_result = zip_analyzer.parse_zip_filename(zip_filename)
                                if zip_result:
                                    analysis_month = zip_result['analysis_month']
                            except Exception as e:
                                logger.warning(f"⚠️ 분석월 추출 실패: {e}")
                            
                            # 태그 정보
                            tags = blog_post.get('tags', '')
                            
                            # 발행
                            if not bot.click_save_button(analysis_month, tags):
                                logger.error(f"❌ 발행 실패")
                                continue
                            
                            logger.info(f"✅ 블로그 작성 완료: {zip_filename}")
                            success_count += 1
                            
                            # 처리 완료 표시
                            bot.mark_zip_as_processed(zip_filename)
                            
                            # 작성 페이지로 돌아가기
                            bot.return_to_write_page()
                            
                            # extracted 폴더만 정리 (ZIP 파일은 유지)
                            if bot.docs_zip_processor:
                                bot.docs_zip_processor.cleanup_extracted_files()
                                logger.info(f"✅ extracted 폴더 정리 완료")
                            
                        except Exception as e:
                            logger.error(f"❌ 블로그 작성 중 오류: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            continue
                    
                    # 블로그 작성 상태 업데이트
                    if success_count > 0:
                        logger.info(f"✅ 블로그 자동 작성 완료: {success_count}개 포스트")
                        return True
                    else:
                        logger.error(f"❌ 블로그 자동 작성 실패: 모든 포스트 작성 실패")
                        return False
                else:
                    logger.error(f"❌ docs zip 처리기를 사용할 수 없습니다.")
                    return False
                
            finally:
                # 드라이버 정리
                bot.close_driver()
                
        except Exception as e:
            logger.error(f"블로그 자동 작성 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run(self):
        """전체 실행"""
        try:
            logger.info("🚀 주봉 자동 분석 및 블로그 작성 시작")
            logger.info("="*60)
            
            # 1. 주차 계산 (완성된 주로 조정)
            current_date = datetime.now()
            year, week = get_week_number(current_date)
            logger.info(f"📅 현재 주차: {year}년 {week}주차")
            
            # 주 완성도 확인
            week_start = get_week_start_date(year, week)
            week_end = get_week_end_date(year, week)
            is_complete = is_complete_week(week_start, current_date)
            
            if not is_complete:
                logger.warning(f"⚠️ {year}년 {week}주차는 아직 완성되지 않았습니다.")
                logger.info(f"   주 기간: {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")
                logger.info(f"   현재 일자: {current_date.strftime('%Y-%m-%d')}")
                
                # 이전 주차로 조정
                if week > 1:
                    week -= 1
                    week_start = get_week_start_date(year, week)
                    week_end = get_week_end_date(year, week)
                    logger.info(f"   이전 주차로 조정: {year}년 {week}주차")
                    logger.info(f"   조정된 주 기간: {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")
                else:
                    # 작년 마지막 주로 조정
                    year -= 1
                    week = 52
                    week_start = get_week_start_date(year, week)
                    week_end = get_week_end_date(year, week)
                    logger.info(f"   작년 마지막 주로 조정: {year}년 {week}주차")
                    logger.info(f"   조정된 주 기간: {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")
            else:
                logger.info(f"✅ {year}년 {week}주차는 완성된 주입니다.")
                logger.info(f"   주 기간: {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}")
            
            # 2. 랭킹 추출 (기본값 50개 사용)
            logger.info("\n📊 1단계: 주봉 랭킹 추출")
            ranking_result = self.extract_weekly_rankings(year, week)  # 기본값 50 사용
            
            if not ranking_result:
                logger.error("랭킹 추출 실패로 종료")
                return False
            
            # 3. 주봉 분석
            logger.info("\n📈 2단계: 주봉 차트 분석")
            analysis_success = self.analyze_weekly_charts(ranking_result, year, week)
            
            if not analysis_success:
                logger.error("주봉 분석 실패로 종료")
                return False
            
            # 4. 블로그 작성
            logger.info("\n📝 3단계: 블로그 자동 작성")
            blog_success = self.write_blog_posts(year, week)
            
            if not blog_success:
                logger.error("블로그 작성 실패")
                return False
            
            logger.info("\n" + "="*60)
            logger.info("✅ 주봉 자동 분석 및 블로그 작성 완료!")
            logger.info(f"📅 {year}년 {week}주차")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"전체 실행 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


def main():
    """메인 함수"""
    try:
        logger.info("🎯 주봉 자동 분석 및 블로그 작성 프로그램")
        logger.info("="*60)
        logger.info("📌 기능:")
        logger.info("   1. 주봉 랭킹 추출 (거래율/거래대금 상위 50위)")
        logger.info("   2. 주봉 차트 분석")
        logger.info("   3. 블로그 자동 작성")
        logger.info("="*60)
        
        # WeeklyAutoBlog 인스턴스 생성
        app = WeeklyAutoBlog()
        
        # 전체 실행
        success = app.run()
        
        if success:
            logger.info("\n✅ 프로그램이 성공적으로 완료되었습니다!")
            return 0
        else:
            logger.error("\n❌ 프로그램 실행 중 오류가 발생했습니다.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n\n👋 사용자가 중단했습니다.")
        return 1
    except Exception as e:
        logger.error(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
