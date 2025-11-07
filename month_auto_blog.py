#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
월봉 자동 분석 및 블로그 작성 모듈
랭킹 추출 → 월봉 분석 → 블로그 작성
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
import sys
import glob
import zipfile
import shutil
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('month_auto_blog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from ranking_data_extractor import RankingDataExtractor
from database_config import DatabaseManager

from month_stock_analysis import (
    get_monthly_stock_data,
    create_monthly_stock_chart,
    save_chart_data_to_json,
    get_stock_name,
    is_complete_month
)

import ai_chart_analysis
from config import config
from database_config import get_db_config


class MonthAutoBlog:
    """월봉 자동 분석 및 블로그 작성 클래스"""

    def __init__(self):
        self.db = DatabaseManager()

    def _get_latest_trade_date(self, year: int = None, month: int = None) -> Optional[date]:
        """특정 월의 최신 거래일 조회 (year/month가 없으면 전체 최신 거래일)"""
        db = DatabaseManager()
        try:
            if not db.connect():
                logger.error("DB 연결 실패")
                return None

            if year is not None and month is not None:
                query = """
                    SELECT MAX(trade_date) AS latest_date
                    FROM daily_data
                    WHERE YEAR(trade_date) = %s AND MONTH(trade_date) = %s
                """
                result = db.fetch_one(query, (year, month))
            else:
                query = "SELECT MAX(trade_date) AS latest_date FROM daily_data"
                result = db.fetch_one(query)

            if result and result.get('latest_date'):
                latest = result['latest_date']
                return latest.date() if hasattr(latest, 'date') else latest
            return None
        except Exception as e:
            logger.error(f"최신 거래일 조회 실패: {e}")
            return None
        finally:
            try:
                db.disconnect()
            except:
                pass

    def extract_monthly_rankings(self, year: int, month: int, limit: int = 50) -> Optional[Dict]:
        """월봉 랭킹 추출"""
        try:
            logger.info(f"📊 월봉 랭킹 추출 시작: {year}년 {month}월 (limit={limit})")

            RankingDataExtractor()
            batch_id = f"monthly_{year}_{month:02d}"

            from ranking_calculator import RankingCalculator
            ranking_calculator = RankingCalculator()

            target_date = f"{year}-{month:02d}"

            turnover_ranking = ranking_calculator.get_turnover_ranking(
                target_date=target_date,
                chart_type="월봉",
                limit=limit
            )
            volume_ranking = ranking_calculator.get_volume_ranking(
                target_date=target_date,
                chart_type="월봉",
                limit=limit
            )

            results = {
                "target_date": target_date,
                "chart_type": "월봉",
                "turnover_file": None,
                "volume_file": None,
                "turnover_count": 0,
                "volume_count": 0,
                "success": False,
                "error": None
            }

            if turnover_ranking:
                turnover_file = self._save_ranking_to_txt(
                    turnover_ranking,
                    target_date,
                    "월봉",
                    "거래율",
                    batch_id
                )
                results["turnover_file"] = turnover_file
                results["turnover_count"] = len(turnover_ranking)
                logger.info(f"거래율 상위 {limit}위 추출 완료: {len(turnover_ranking)}개")

            if volume_ranking:
                volume_file = self._save_ranking_to_txt(
                    volume_ranking,
                    target_date,
                    "월봉",
                    "거래대금",
                    batch_id
                )
                results["volume_file"] = volume_file
                results["volume_count"] = len(volume_ranking)
                logger.info(f"거래대금 상위 {limit}위 추출 완료: {len(volume_ranking)}개")

            results["success"] = bool(results["turnover_file"] and results["volume_file"])
            if not results["success"]:
                logger.error("❌ 월봉 랭킹 추출 실패: 결과 파일이 생성되지 않았습니다.")
                return None

            logger.info("✅ 월봉 랭킹 추출 완료")
            logger.info(f"   - 거래율 파일: {results.get('turnover_file')}")
            logger.info(f"   - 거래대금 파일: {results.get('volume_file')}")
            logger.info(f"   - 거래율 종목 수: {results.get('turnover_count')}")
            logger.info(f"   - 거래대금 종목 수: {results.get('volume_count')}")

            return results
        except Exception as e:
            logger.error(f"월봉 랭킹 추출 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _save_ranking_to_txt(self, ranking_data: List[Dict], target_date: str,
                             chart_type: str, trading_type: str, batch_id: str) -> str:
        """랭킹 데이터를 txt 파일로 저장 (종목코드 리스트)"""
        output_dir = "uploads/stock_lists"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        if batch_id:
            filename = f"{chart_type}_{trading_type}_랭킹_{batch_id}_{timestamp}.txt"
        else:
            filename = f"{chart_type}_{trading_type}_랭킹_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            for item in ranking_data:
                f.write(f"{item['stock_code']}\n")

        logger.info(f"파일 저장 완료: {filepath} ({len(ranking_data)}개)")
        return filepath

    def read_stock_codes_from_file(self, file_path: str) -> List[str]:
        """txt 파일에서 종목코드 리스트 읽기"""
        if not os.path.exists(file_path):
            logger.error(f"파일이 존재하지 않습니다: {file_path}")
            return []

        stock_codes: List[str] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stock_code = line.strip()
                if stock_code:
                    stock_codes.append(stock_code)

        logger.info(f"종목코드 {len(stock_codes)}개 로드: {file_path}")
        return stock_codes

    def analyze_monthly_stocks_from_file(self, file_path: str, trading_type: str,
                                         year: int, month: int) -> bool:
        """파일에서 종목 리스트를 읽어서 각각 월봉 분석"""
        try:
            logger.info(f"📈 월봉 분석 시작: {trading_type}")

            stock_codes = self.read_stock_codes_from_file(file_path)
            if not stock_codes:
                logger.warning(f"종목 리스트가 비어있습니다: {file_path}")
                return False

            logger.info(f"총 {len(stock_codes)}개 종목 분석 예정")
            success_count = 0
            failed_count = 0

            for idx, stock_code in enumerate(stock_codes, 1):
                try:
                    logger.info(f"[{idx}/{len(stock_codes)}] {stock_code} 분석 중...")

                    monthly_data = get_monthly_stock_data(stock_code)
                    if monthly_data is None or monthly_data.empty:
                        logger.error(f"월봉 데이터 조회 실패: {stock_code}")
                        failed_count += 1
                        continue

                    chart_result = create_monthly_stock_chart(monthly_data, stock_code)
                    if not chart_result or len(chart_result) != 3:
                        logger.error(f"월봉 차트 생성 실패: {stock_code}")
                        failed_count += 1
                        continue

                    chart_path, stock_name, chart_data = chart_result
                    if chart_path:
                        chart_path = os.path.abspath(chart_path)

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

                    api_key = config.get_api_key()
                    if not api_key:
                        logger.error("API 키를 가져올 수 없습니다")
                        failed_count += 1
                        continue

                    analyzer = ai_chart_analysis.AIChartAnalyzer(api_key, get_db_config())
                    analysis_result = analyzer.analyze_chart_image(
                        image_path=chart_path,
                        stock_name=stock_name,
                        chart_type="월봉",
                        chart_data=chart_data,
                        json_data_path=json_path,
                        trading_type=trading_type
                    )

                    if not analysis_result:
                        logger.error(f"❌ {stock_code} AI 분석 실패")
                        failed_count += 1
                        continue

                    output_dir = "ai_analysis_results"
                    os.makedirs(output_dir, exist_ok=True)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    batch_id = f"monthly_{year}_{month:02d}"
                    chart_type_en = "monthly"

                    base_filename = f"analysis_{chart_type_en}_{stock_code}_{timestamp}_{batch_id}"
                    result_json_path = os.path.join(output_dir, f"{base_filename}.json")
                    result_doc_path = os.path.join(output_dir, f"{base_filename}.docx")

                    try:
                        json_success = analyzer.save_analysis_result(analysis_result, result_json_path)
                        if json_success:
                            logger.info(f"✅ {stock_code} 결과 JSON 저장: {result_json_path}")
                        else:
                            logger.error(f"❌ {stock_code} JSON 저장 실패")
                    except Exception as e:
                        logger.error(f"❌ {stock_code} JSON 저장 실패: {e}")
                        json_success = False

                    try:
                        doc_success = analyzer.create_word_document_hybrid(
                            analysis_result,
                            chart_path,
                            result_doc_path,
                            "월봉"
                        )
                        if doc_success:
                            logger.info(f"✅ {stock_code} 결과 DOCX 저장: {result_doc_path}")
                        else:
                            logger.error(f"❌ {stock_code} DOCX 저장 실패")
                    except Exception as e:
                        logger.error(f"❌ {stock_code} DOCX 저장 실패: {e}")
                        doc_success = False

                    if json_success and doc_success:
                        logger.info(f"✅ {stock_code} ({stock_name}) AI 분석 및 저장 완료")
                        success_count += 1
                    else:
                        logger.error(f"❌ {stock_code} 파일 저장 실패 - JSON: {json_success}, DOCX: {doc_success}")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"종목 {stock_code} 분석 중 오류: {e}")
                    failed_count += 1

            logger.info(f"📊 월봉 분석 완료: {trading_type}")
            logger.info(f"   성공: {success_count}개, 실패: {failed_count}개")
            return success_count > 0
        except Exception as e:
            logger.error(f"월봉 분석 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def analyze_monthly_charts(self, ranking_result: Dict, year: int, month: int) -> bool:
        """월봉 차트 분석 - 거래율/거래대금 분리"""
        try:
            logger.info(f"📊 월봉 차트 분석 시작: {year}년 {month}월")

            turnover_file = ranking_result.get("turnover_file")
            volume_file = ranking_result.get("volume_file")

            if not turnover_file or not os.path.exists(turnover_file):
                logger.error(f"거래율 파일을 찾을 수 없습니다: {turnover_file}")
                return False
            if not volume_file or not os.path.exists(volume_file):
                logger.error(f"거래대금 파일을 찾을 수 없습니다: {volume_file}")
                return False

            logger.info("📈 거래율 상위 50위 월봉 분석 시작...")
            turnover_success = self.analyze_monthly_stocks_from_file(
                turnover_file, "거래율", year, month
            )
            if not turnover_success:
                logger.error("거래율 월봉 분석 실패")

            logger.info("💰 거래대금 상위 50위 월봉 분석 시작...")
            volume_success = self.analyze_monthly_stocks_from_file(
                volume_file, "거래대금", year, month
            )
            if not volume_success:
                logger.error("거래대금 월봉 분석 실패")

            overall_success = turnover_success and volume_success
            logger.info(f"📊 월봉 차트 분석 완료: {year}년 {month}월")
            logger.info(f"   거래율 분석: {'성공' if turnover_success else '실패'}")
            logger.info(f"   거래대금 분석: {'성공' if volume_success else '실패'}")

            if overall_success:
                self.create_summary_and_zip(year, month)

            return overall_success
        except Exception as e:
            logger.error(f"월봉 차트 분석 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def create_summary_and_zip(self, year: int, month: int) -> bool:
        """Summary/Tag 및 ZIP 파일 생성"""
        try:
            logger.info(f"📊 Summary/Tag 파일 및 ZIP 파일 생성 시작: {year}년 {month}월")

            batch_id = f"monthly_{year}_{month:02d}"
            pattern = f"ai_analysis_results/analysis_monthly_*_{batch_id}.json"
            json_files = glob.glob(pattern)

            if not json_files:
                logger.warning(f"Summary 생성할 JSON 파일이 없습니다: {pattern}")
                return False

            logger.info(f"📄 발견된 분석 결과 파일: {len(json_files)}개")

            from api.batch_analyzer import BatchAnalyzer
            batch_analyzer = BatchAnalyzer()

            summary_files = batch_analyzer._create_summary_analysis(
                chart_type="월봉",
                specific_files=json_files,
                batch_id=batch_id
            )

            if summary_files:
                logger.info(f"✅ Summary 파일 생성 완료: {summary_files}")
            else:
                logger.warning("Summary 파일 생성 실패")

            results_dir = "results"
            os.makedirs(results_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f"월봉_{year}년{month:02d}월_{batch_id}.zip"
            zip_path = os.path.join(results_dir, zip_filename)

            logger.info(f"📦 ZIP 파일 생성: {zip_path}")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                if summary_files:
                        if summary_files.get("docx_path") and os.path.exists(summary_files["docx_path"]):
                            basename = os.path.basename(summary_files["docx_path"])
                            zipf.write(summary_files["docx_path"], f"summary_analysis/{basename}")
                            logger.info(f"✅ Summary DOCX 추가: summary_analysis/{basename}")

                        if summary_files.get("json_path") and os.path.exists(summary_files["json_path"]):
                            basename = os.path.basename(summary_files["json_path"])
                            zipf.write(summary_files["json_path"], f"summary_analysis/{basename}")
                            logger.info(f"✅ Summary JSON 추가: summary_analysis/{basename}")

                tag_pattern = f"ai_analysis_results/tag_{batch_id}_*.docx"
                tag_files = glob.glob(tag_pattern)
                if tag_files:
                    tag_path = max(tag_files, key=os.path.getctime)
                    logger.info(f"✅ Tag 파일 발견: {tag_path}")
                else:
                    logger.warning("⚠️ Tag 파일을 찾을 수 없습니다. 기본 태그 파일을 생성합니다.")
                    tag_path = self._create_default_tag_file(batch_id, year, month)

                if tag_path and os.path.exists(tag_path):
                    zipf.write(tag_path, "tag.docx")
                    logger.info("✅ Tag DOCX 추가: tag.docx")
                else:
                    logger.error(f"❌ Tag DOCX 파일을 추가할 수 없습니다: {tag_path}")

                try:
                    import tempfile
                    analysis_data_list = []
                    for json_file in json_files:
                        try:
                            with open(json_file, "r", encoding="utf-8") as f:
                                analysis_data_list.append(json.load(f))
                        except Exception as e:
                            logger.warning(f"JSON 파일 읽기 실패: {json_file}, {e}")

                    if analysis_data_list:
                        total_analysis_json = self._create_total_analysis_from_files(analysis_data_list, "월봉")
                        if total_analysis_json:
                            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
                                temp_path = temp_file.name

                            doc_success = batch_analyzer._create_total_analysis_docx(
                                total_analysis_json, "월봉", temp_path, batch_id
                            )

                            if doc_success:
                                total_analysis_filename = f"total_analysis/통합요약_분석_monthly_{timestamp}.docx"
                                zipf.write(temp_path, total_analysis_filename)
                                logger.info(f"✅ Total Analysis DOCX 추가: {total_analysis_filename}")
                            else:
                                logger.warning("Total Analysis DOCX 생성 실패")

                            if os.path.exists(temp_path):
                                os.unlink(temp_path)
                        else:
                            logger.warning("Total Analysis JSON 생성 실패")
                except Exception as e:
                    logger.error(f"Total Analysis ZIP 추가 실패: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            logger.info(f"✅ ZIP 파일 생성 완료: {zip_path}")
            logger.info(f"📊 ZIP 파일 크기: {os.path.getsize(zip_path) if os.path.exists(zip_path) else 0} bytes")

            docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog_auto", "docs")
            os.makedirs(docs_dir, exist_ok=True)
            docs_zip_path = os.path.join(docs_dir, os.path.basename(zip_path))
            shutil.copy2(zip_path, docs_zip_path)
            logger.info(f"✅ ZIP 파일을 blog_auto/docs 폴더에 복사: {docs_zip_path}")

            return True
        except Exception as e:
            logger.error(f"Summary/ZIP 파일 생성 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _create_total_analysis_from_files(self, analysis_data_list: List[Dict], chart_type: str) -> Dict:
        """JSON 파일들로부터 Total Analysis 생성"""
        try:
            logger.info(f"Total Analysis 생성 시작: {len(analysis_data_list)}개 파일")

            trading_stats = {
                "거래대금_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "원"},
                "거래률_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "%"},
                "순위_통계": {"1위": 0, "10위이내": 0, "50위이내": 0, "100위이내": 0},
                "거래타입_분포": {"거래대금": 0, "거래율": 0},
                "유통주식수_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "주"},
                "거래량_통계": {"총합": 0, "평균": 0, "최대": 0, "최소": float('inf'), "단위": "주"}
            }

            valid_trading_data = 0

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

            for analysis_data in analysis_data_list:
                try:
                    stock_code = analysis_data.get("종목정보", {}).get("종목번호", "000000")
                    stock_name = analysis_data.get("종목정보", {}).get("종목명", "알수없음")

                    if "종목정보" in analysis_data:
                        trading_info = analysis_data["종목정보"]

                        amount = self._parse_trading_amount(trading_info.get("거래대금", "0"))
                        if amount > 0:
                            trading_stats["거래대금_통계"]["총합"] += amount
                            trading_stats["거래대금_통계"]["최대"] = max(trading_stats["거래대금_통계"]["최대"], amount)
                            trading_stats["거래대금_통계"]["최소"] = min(trading_stats["거래대금_통계"]["최소"], amount)

                        turnover_rate = self._parse_percentage(trading_info.get("거래율", "0%"))
                        if turnover_rate > 0:
                            trading_stats["거래률_통계"]["총합"] += turnover_rate
                            trading_stats["거래률_통계"]["최대"] = max(trading_stats["거래률_통계"]["최대"], turnover_rate)
                            trading_stats["거래률_통계"]["최소"] = min(trading_stats["거래률_통계"]["최소"], turnover_rate)

                        ranking = self._parse_ranking(trading_info.get("순위", "999위"))
                        if ranking == 1:
                            trading_stats["순위_통계"]["1위"] += 1
                        elif ranking <= 10:
                            trading_stats["순위_통계"]["10위이내"] += 1
                        elif ranking <= 50:
                            trading_stats["순위_통계"]["50위이내"] += 1
                        elif ranking <= 100:
                            trading_stats["순위_통계"]["100위이내"] += 1

                        trading_type = trading_info.get("거래타입", "거래대금")
                        if trading_type in trading_stats["거래타입_분포"]:
                            trading_stats["거래타입_분포"][trading_type] += 1

                        valid_trading_data += 1

                    total_analysis["consolidated_analysis"][stock_code] = analysis_data
                    logger.info(f"종목 {stock_code} ({stock_name}) 분석 데이터 추가 완료")

                except Exception as e:
                    logger.warning(f"JSON 데이터 처리 실패: {e}")

            if valid_trading_data > 0:
                trading_stats["거래대금_통계"]["평균"] = trading_stats["거래대금_통계"]["총합"] / valid_trading_data
                trading_stats["거래률_통계"]["평균"] = trading_stats["거래률_통계"]["총합"] / valid_trading_data

                if trading_stats["거래대금_통계"]["최소"] == float('inf'):
                    trading_stats["거래대금_통계"]["최소"] = 0
                if trading_stats["거래률_통계"]["최소"] == float('inf'):
                    trading_stats["거래률_통계"]["최소"] = 0

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
        """거래대금 문자열을 숫자로 변환"""
        try:
            if not amount_str or amount_str == "N/A":
                return 0.0

            import re
            clean_str = amount_str.replace(",", "")
            match = re.search(r"([\d.]+)(억원|만원|원)?", clean_str)
            if not match:
                return 0.0

            number = float(match.group(1))
            unit = match.group(2) or "원"

            if unit == "억원":
                return number * 100_000_000
            if unit == "만원":
                return number * 10_000
            return number
        except Exception:
            return 0.0

    def _parse_percentage(self, percent_str: str) -> float:
        """퍼센트 문자열을 숫자로 변환"""
        try:
            if not percent_str or percent_str == "N/A":
                return 0.0

            import re
            match = re.search(r"([\d.]+)%", percent_str)
            if match:
                return float(match.group(1))
            return 0.0
        except Exception:
            return 0.0

    def _parse_ranking(self, ranking_str: str) -> int:
        """순위 문자열을 숫자로 변환"""
        try:
            if not ranking_str or ranking_str == "N/A":
                return 999

            import re
            match = re.search(r"(\d+)위", ranking_str)
            if match:
                return int(match.group(1))
            return 999
        except Exception:
            return 999

    def _create_default_tag_file(self, batch_id: str, year: int, month: int) -> Optional[str]:
        """기본 태그 파일 생성 (AI 태그 생성 실패 시 사용)"""
        try:
            logger.info(f"🏷️ 기본 태그 파일 생성 시작: {year}년 {month}월")

            output_dir = "ai_analysis_results"
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            tag_filename = f"tag_{batch_id}_{timestamp}.docx"
            tag_path = os.path.join(output_dir, tag_filename)

            default_tag_text = f"월봉, {year}년 {month}월, 주식분석, 기술적분석, 투자분석, 차트분석"

            from docx import Document
            from docx.oxml.ns import qn

            doc = Document()
            para = doc.add_paragraph(default_tag_text)
            for run in para.runs:
                run.font.name = "맑은 고딕"
                run._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")

            doc.save(tag_path)
            logger.info(f"✅ 기본 태그 파일 생성 완료: {tag_path}")
            return tag_path
        except Exception as e:
            logger.error(f"❌ 기본 태그 파일 생성 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def write_blog_posts(self, year: int, month: int) -> bool:
        """블로그 자동 작성"""
        try:
            logger.info(f"📝 블로그 자동 작성 시작: {year}년 {month}월")

            project_root = os.path.dirname(os.path.abspath(__file__))
            blog_auto_path = os.path.join(project_root, "blog_auto")
            docs_path = os.path.join(blog_auto_path, "docs")

            logger.info(f"[DEBUG] 프로젝트 루트: {project_root}")
            logger.info(f"[DEBUG] blog_auto 경로: {blog_auto_path}")
            logger.info(f"[DEBUG] docs 경로: {docs_path}")

            if blog_auto_path not in sys.path:
                sys.path.insert(0, blog_auto_path)

            if not os.path.exists(docs_path):
                logger.warning(f"⚠️ docs 디렉토리가 존재하지 않습니다: {docs_path}")
                logger.info("📁 docs 디렉토리를 생성합니다...")
                os.makedirs(docs_path, exist_ok=True)

            from auto_blog import NaverBlogBot

            bot = NaverBlogBot(headless=False, debug_mode=True)

            try:
                if not bot.run_login():
                    logger.error(f"❌ 블로그 로그인 실패: {year}년 {month}월")
                    return False

                logger.info(f"✅ 블로그 로그인 성공: {year}년 {month}월")

                if not os.path.exists(docs_path):
                    logger.error(f"❌ docs 디렉토리를 찾을 수 없습니다: {docs_path}")
                    return False

                zip_files = [f for f in os.listdir(docs_path) if f.endswith(".zip")]
                logger.info(f"📂 docs 디렉토리: {docs_path}")
                logger.info(f"📦 발견된 zip 파일: {len(zip_files)}개")
                for zip_file in zip_files:
                    logger.info(f"   - {zip_file}")

                if not bot.docs_zip_processor:
                    logger.error("❌ docs zip 처리기를 사용할 수 없습니다.")
                    return False

                unprocessed_zips = bot.get_unprocessed_zips()
                if not unprocessed_zips:
                    logger.info(f"📭 처리할 zip 파일이 없습니다: {year}년 {month}월")
                    logger.info(f"   (총 {len(zip_files)}개 zip 파일이 있지만 모두 처리됨)")
                    return True

                logger.info(f"📦 총 {len(unprocessed_zips)}개의 zip 파일 처리 시작")
                success_count = 0

                for zip_path in unprocessed_zips:
                    zip_filename = os.path.basename(zip_path)
                    logger.info(f"📝 블로그 작성 중: {zip_filename}")

                    try:
                        blog_post = bot.docs_zip_processor.process_single_zip_file(zip_path)
                        if not blog_post:
                            logger.error(f"❌ ZIP 파일 처리 실패: {zip_filename}")
                            continue

                        if not bot.navigate_to_blog_write():
                            logger.error("❌ 블로그 글쓰기 페이지 이동 실패")
                            continue

                        if not bot.switch_to_blog_frame():
                            logger.error("❌ iframe 전환 실패")
                            continue

                        bot.close_popups_and_help()

                        if not bot.enter_blog_title(blog_post["title"]):
                            logger.error("❌ 제목 입력 실패")
                            continue

                        if not bot.write_content_with_structured_tables(blog_post["content"], blog_post["tables"]):
                            logger.error("❌ 내용 입력 실패")
                            continue

                        if blog_post.get("attachment_file"):
                            if not bot.add_file_to_blog(blog_post["attachment_file"]):
                                logger.warning("⚠️ 첨부파일 추가 실패")

                        analysis_month = None
                        try:
                            from zip_analyzer import ZipAnalyzer
                            zip_analyzer = ZipAnalyzer()
                            zip_result = zip_analyzer.parse_zip_filename(zip_filename)
                            if zip_result:
                                analysis_month = zip_result["analysis_month"]
                        except Exception as e:
                            logger.warning(f"⚠️ 분석월 추출 실패: {e}")

                        tags = blog_post.get("tags", "")
                        if not bot.click_save_button(analysis_month, tags):
                            logger.error("❌ 발행 실패")
                            continue

                        logger.info(f"✅ 블로그 작성 완료: {zip_filename}")
                        success_count += 1

                        bot.mark_zip_as_processed(zip_filename)
                        bot.return_to_write_page()

                        if bot.docs_zip_processor:
                            bot.docs_zip_processor.cleanup_extracted_files()
                            logger.info("✅ extracted 폴더 정리 완료")

                    except Exception as e:
                        logger.error(f"❌ 블로그 작성 중 오류: {e}")
                        import traceback
                        logger.error(traceback.format_exc())

                if success_count > 0:
                    logger.info(f"✅ 블로그 자동 작성 완료: {success_count}개 포스트")
                    return True

                logger.error("❌ 블로그 자동 작성 실패: 모든 포스트 작성 실패")
                return False
            finally:
                bot.close_driver()
        except Exception as e:
            logger.error(f"블로그 자동 작성 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def run(self) -> bool:
        """전체 실행"""
        try:
            logger.info("🚀 월봉 자동 분석 및 블로그 작성 시작")
            logger.info("=" * 60)

            current_datetime = datetime.now()
            latest_trade_date = self._get_latest_trade_date()
            if not latest_trade_date:
                logger.error("최신 거래일을 찾을 수 없어 작업을 종료합니다.")
                return False

            target_trade_date = latest_trade_date
            attempts = 0

            while not is_complete_month(target_trade_date, current_datetime, target_trade_date):
                attempts += 1
                if attempts > 12:
                    logger.error("1년 이내에 완성된 월을 찾지 못했습니다.")
                    return False

                target_year = target_trade_date.year
                target_month = target_trade_date.month
                logger.warning(f"⚠️ {target_year}년 {target_month}월은 아직 완성되지 않았습니다.")

                if target_month == 1:
                    prev_year = target_year - 1
                    prev_month = 12
                else:
                    prev_year = target_year
                    prev_month = target_month - 1

                prev_trade_date = self._get_latest_trade_date(prev_year, prev_month)
                if not prev_trade_date:
                    logger.error(f"{prev_year}년 {prev_month}월의 거래일을 찾을 수 없습니다.")
                    return False

                target_trade_date = prev_trade_date

            target_year = target_trade_date.year
            target_month = target_trade_date.month

            logger.info(f"📅 분석 대상 월: {target_year}년 {target_month}월")
            logger.info("=" * 60)

            logger.info("\n📊 1단계: 월봉 랭킹 추출 (테스트용 상위 3개)")
            ranking_result = self.extract_monthly_rankings(target_year, target_month, limit=3)
            if not ranking_result:
                logger.error("랭킹 추출 실패로 종료")
                return False

            logger.info("\n📈 2단계: 월봉 차트 분석")
            analysis_success = self.analyze_monthly_charts(ranking_result, target_year, target_month)
            if not analysis_success:
                logger.error("월봉 분석 실패로 종료")
                return False

            logger.info("\n📝 3단계: 블로그 자동 작성")
            blog_success = self.write_blog_posts(target_year, target_month)
            if not blog_success:
                logger.error("블로그 작성 실패")
                return False

            logger.info("\n" + "=" * 60)
            logger.info("✅ 월봉 자동 분석 및 블로그 작성 완료!")
            logger.info(f"📅 {target_year}년 {target_month}월")
            logger.info("=" * 60)
            return True
        except Exception as e:
            logger.error(f"전체 실행 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


def main() -> int:
    """메인 함수"""
    try:
        logger.info("🎯 월봉 자동 분석 및 블로그 작성 프로그램")
        logger.info("=" * 60)
        logger.info("📌 기능:")
        logger.info("   1. 월봉 랭킹 추출 (거래율/거래대금 상위 50위)")
        logger.info("   2. 월봉 차트 분석")
        logger.info("   3. 블로그 자동 작성")
        logger.info("=" * 60)

        app = MonthAutoBlog()
        success = app.run()

        if success:
            logger.info("\n✅ 프로그램이 성공적으로 완료되었습니다!")
            return 0

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
    sys.exit(main())

