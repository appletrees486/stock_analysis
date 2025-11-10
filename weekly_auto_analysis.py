#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주봉 자동 분석 및 블로그 작성 스크립트

기존 batch_scheduler.py의 랭킹 → 분석 → 블로그 작성 흐름을
주봉 전용으로 재구성한 독립 실행 모듈입니다.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import List, Optional

# Windows 콘솔 환경에서 UTF-8 출력이 깨지는 문제 방지
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("WeeklyAutoAnalysis")

# ----------------------------------------------------------------------
# 상수 정의 (유니코드 이스케이프 사용으로 CP949 환경 문제 방지)
# ----------------------------------------------------------------------
CHART_TYPE_WEEKLY = "\uc8fc\ubd09"         # "주봉"
TRADING_TYPE_TURNOVER = "\uac70\ub798\uc728"  # "거래율"
TRADING_TYPE_VOLUME = "\uac70\ub798\ub300\uae08"  # "거래대금"
TEST_TOP_LIMIT = 5

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# blog_auto 모듈 경로 추가
BLOG_AUTO_PATH = os.path.join(PROJECT_ROOT, "blog_auto")
if BLOG_AUTO_PATH not in sys.path:
    sys.path.insert(0, BLOG_AUTO_PATH)

try:
    from auto_blog import NaverBlogBot, check_dependencies as check_blog_dependencies
except ImportError:
    NaverBlogBot = None  # type: ignore
    check_blog_dependencies = None  # type: ignore
    logger.warning("blog_auto 모듈을 불러올 수 없습니다. 블로그 자동 작성이 비활성화됩니다.")

# 주봉 관련 유틸
from week_calculator import WeekCalculator, get_week_number_string
from week_stock_analysis import (
    get_weekly_stock_data,
    create_weekly_stock_chart,
    save_chart_data_to_json,
    save_chart_data_to_csv,
    save_chart_summary_to_text,
)

# 기존 랭킹/분석 모듈
from ranking_data_extractor import RankingDataExtractor
from api.batch_analyzer import BatchAnalyzer


class WeeklyAutoAnalysis:
    """주봉 자동 분석 및 블로그 작성 오케스트레이터"""

    def __init__(self, target_date: Optional[str] = None):
        self.target_date = target_date
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.base_batch_id = f"weekly_auto_{self.timestamp}"

        self.extractor = RankingDataExtractor()
        self.batch_analyzer = BatchAnalyzer()

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def run(self) -> None:
        """전체 파이프라인 실행"""
        logger.info("%s 자동 분석을 시작합니다.", CHART_TYPE_WEEKLY)

        ranking_result = self._extract_weekly_rankings()
        if not ranking_result or not ranking_result.get("success"):
            logger.error("랭킹 추출에 실패하여 작업을 종료합니다.")
            return

        target_date = ranking_result.get("target_date")
        if target_date:
            self._log_week_info(target_date)

        turnover_file = ranking_result.get("turnover_file")
        volume_file = ranking_result.get("volume_file")

        if not turnover_file and not volume_file:
            logger.error("랭킹 파일이 생성되지 않아 작업을 종료합니다.")
            return

        # 거래율/거래대금 순으로 처리
        self._process_ranking_file(
            stock_list_path=turnover_file,
            trading_type=TRADING_TYPE_TURNOVER,
            batch_suffix="turnover"
        )

        self._process_ranking_file(
            stock_list_path=volume_file,
            trading_type=TRADING_TYPE_VOLUME,
            batch_suffix="volume"
        )

        # 배치 캐시 정리 (이미지 꼬임 방지)
        cache_id = f"{self.base_batch_id}_cache"
        logger.info("캐시 정리를 진행합니다. (ID: %s)", cache_id)
        self.batch_analyzer.clear_batch_cache(cache_id)
        logger.info("캐시 정리가 완료되었습니다.")

        # 블로그 자동 작성
        self._run_blog_posting()

        logger.info("주봉 자동 분석 프로세스가 완료되었습니다.")
        logger.info("필요 시 캐시 디렉터리를 한 번 더 점검하고, 추가 블로그 게시물 작성 여부를 확인해주세요.")

    # ------------------------------------------------------------------
    # 랭킹 처리
    # ------------------------------------------------------------------
    def _extract_weekly_rankings(self) -> Optional[dict]:
        """주봉 기준 랭킹 데이터 추출"""
        try:
            logger.info("%s 랭킹 데이터를 추출합니다. 대상 날짜: %s", CHART_TYPE_WEEKLY, self.target_date or "최신 거래일")
            result = self.extractor.extract_rankings(
                target_date=self.target_date,
                chart_type=CHART_TYPE_WEEKLY,
                batch_id=self.base_batch_id
            )
            if result.get("success"):
                logger.info(
                    "랭킹 추출 성공 - 거래율 파일: %s, 거래대금 파일: %s",
                    result.get("turnover_file"),
                    result.get("volume_file")
                )
                self._limit_ranking_files(result, TEST_TOP_LIMIT)
            else:
                logger.error("랭킹 추출 실패: %s", result.get("error"))
            return result
        except Exception as exc:
            logger.exception("랭킹 추출 중 오류가 발생했습니다: %s", exc)
            return None

    @staticmethod
    def _create_limited_ranking_file(original_path: Optional[str], limit: int) -> Optional[str]:
        """랭킹 파일을 상위 N개로 제한한 새 파일을 생성"""
        if not original_path or not os.path.exists(original_path):
            return None

        try:
            with open(original_path, "r", encoding="utf-8") as src:
                lines = [line.strip() for line in src.readlines() if line.strip()]

            limited_lines = lines[:limit]
            if not limited_lines:
                return None

            base, ext = os.path.splitext(original_path)
            limited_path = f"{base}_top{limit}{ext}"

            with open(limited_path, "w", encoding="utf-8") as dst:
                dst.write("\n".join(limited_lines) + "\n")

            return limited_path
        except Exception as exc:
            logger.warning("랭킹 파일 제한 생성 중 오류 (%s): %s", original_path, exc)
            return None

    def _limit_ranking_files(self, result: dict, limit: int) -> None:
        """랭킹 결과에 포함된 파일을 상위 N개로 제한"""
        if not result.get("success"):
            return

        for key in ("turnover_file", "volume_file"):
            original_path = result.get(key)
            limited_path = self._create_limited_ranking_file(original_path, limit)
            if limited_path:
                # 원본 경로는 보관
                backup_key = f"{key}_full"
                result[backup_key] = original_path
                result[key] = limited_path
                logger.info("테스트용 상위 %d개 랭킹 파일 생성: %s", limit, limited_path)

    def _process_ranking_file(self, stock_list_path: Optional[str], trading_type: str, batch_suffix: str) -> None:
        """랭킹 파일을 이용해 주봉 데이터를 준비하고 BatchAnalyzer 실행"""
        if not stock_list_path or not os.path.exists(stock_list_path):
            logger.warning("%s 랭킹 파일이 존재하지 않습니다: %s", trading_type, stock_list_path)
            return

        logger.info("%s 랭킹 파일 처리 시작: %s", trading_type, stock_list_path)
        stock_codes = self._load_stock_codes(stock_list_path)
        if not stock_codes:
            logger.warning("%s 랭킹 파일에서 종목을 찾을 수 없습니다.", trading_type)
            return

        logger.info("총 %d개 종목에 대해 주봉 데이터 준비를 진행합니다.", len(stock_codes))

        prepared_count = 0
        for stock_code in stock_codes:
            if self._prepare_weekly_resources(stock_code, trading_type):
                prepared_count += 1

        logger.info(
            "%s 랭킹 주봉 데이터 준비 완료: 총 %d개 중 %d개 성공",
            trading_type,
            len(stock_codes),
            prepared_count
        )

        batch_id = f"{self.base_batch_id}_{batch_suffix}"
        try:
            logger.info("%s 배치 분석을 시작합니다. Batch ID: %s", trading_type, batch_id)
            self.batch_analyzer.start_batch_analysis(
                stock_list_path=stock_list_path,
                chart_type=CHART_TYPE_WEEKLY,
                batch_id=batch_id,
                trading_type=trading_type,
                email_enabled=False,
                email_address=""
            )
            logger.info("%s 배치 분석이 완료되었습니다.", trading_type)
        except Exception as exc:
            logger.exception("%s 배치 분석 중 오류가 발생했습니다: %s", trading_type, exc)

    # ------------------------------------------------------------------
    # 개별 종목 주봉 리소스 준비
    # ------------------------------------------------------------------
    def _prepare_weekly_resources(self, stock_code: str, trading_type: str) -> bool:
        """주봉 데이터/차트/파일을 사전 생성"""
        try:
            logger.info("[%s 준비] %s 종목 처리 시작", CHART_TYPE_WEEKLY, stock_code)
            hist = get_weekly_stock_data(stock_code)
            if hist is None or hist.empty:
                logger.warning("[%s 준비] %s 종목의 %s 데이터를 가져오지 못했습니다.", CHART_TYPE_WEEKLY, stock_code, CHART_TYPE_WEEKLY)
                return False

            chart_path, stock_name, chart_df = create_weekly_stock_chart(hist, stock_code)
            if chart_df is None or chart_df.empty:
                logger.warning("[%s 준비] %s 종목의 차트 데이터를 생성하지 못했습니다.", CHART_TYPE_WEEKLY, stock_code)
                return False

            json_path = save_chart_data_to_json(chart_df, stock_code, stock_name, trading_type=trading_type)
            csv_path = save_chart_data_to_csv(chart_df, stock_code, stock_name)
            text_path = save_chart_summary_to_text(chart_df, stock_code, stock_name)

            logger.info(
                "[%s 준비] %s 종목 완료 - 차트: %s | JSON: %s | CSV: %s | TEXT: %s",
                CHART_TYPE_WEEKLY,
                stock_code,
                chart_path,
                json_path,
                csv_path,
                text_path
            )
            return True

        except Exception as exc:
            logger.exception("[%s 준비] %s 종목 처리 중 오류: %s", CHART_TYPE_WEEKLY, stock_code, exc)
            return False

    # ------------------------------------------------------------------
    # 블로그 자동 작성
    # ------------------------------------------------------------------
    def _run_blog_posting(self) -> None:
        """blog_auto 모듈을 이용한 블로그 자동 작성"""
        if NaverBlogBot is None or check_blog_dependencies is None:
            logger.warning("blog_auto 모듈을 사용할 수 없어 블로그 자동 작성을 건너뜁니다.")
            return

            logger.info("블로그 자동 작성을 시작합니다.")
        try:
            if not check_blog_dependencies():
                logger.warning("블로그 자동 작성에 필요한 의존성이 누락되어 작업을 건너뜁니다.")
                return

            bot = NaverBlogBot(headless=False, debug_mode=True)
            try:
                success = bot.process_multiple_zips()
                if success:
                    logger.info("블로그 자동 작성이 완료되었습니다.")
                else:
                    logger.warning("블로그 자동 작성이 일부 실패했습니다. 상세 로그를 확인하세요.")
            finally:
                bot.close_driver()

        except Exception as exc:
            logger.exception("블로그 자동 작성 중 오류가 발생했습니다: %s", exc)

    # ------------------------------------------------------------------
    # 보조 메서드
    # ------------------------------------------------------------------
    @staticmethod
    def _load_stock_codes(stock_list_path: str) -> List[str]:
        """txt 파일에서 종목코드를 로드"""
        try:
            with open(stock_list_path, "r", encoding="utf-8") as file:
                codes = [line.strip() for line in file.readlines() if line.strip()]
            return codes
        except Exception as exc:
            logger.error("종목코드 파일을 읽는 중 오류가 발생했습니다 (%s): %s", stock_list_path, exc)
            return []

    @staticmethod
    def _log_week_info(date_str: str) -> None:
        """대상 날짜의 주차 정보를 로깅"""
        try:
            analysis_date = datetime.strptime(date_str, "%Y-%m-%d")
            week_str = get_week_number_string(analysis_date, "YYYY년 W주차")
            week_start = WeekCalculator.get_week_start_date(*WeekCalculator.get_week_number(analysis_date))
            week_end = WeekCalculator.get_week_end_date(*WeekCalculator.get_week_number(analysis_date))
            logger.info(
                "대상 거래일: %s (%s, 기간: %s ~ %s)",
                date_str,
                week_str,
                week_start.strftime("%Y-%m-%d"),
                week_end.strftime("%Y-%m-%d")
            )
        except Exception as exc:
            logger.warning("주차 정보를 계산하는 중 문제가 발생했습니다: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="주봉 랭킹 기반 자동 분석 및 블로그 작성 실행기")
    parser.add_argument(
        "--target-date",
        help="분석 대상 거래일 (YYYY-MM-DD). 지정하지 않으면 latest trade_date 사용."
    )
    args = parser.parse_args()

    runner = WeeklyAutoAnalysis(target_date=args.target_date)
    runner.run()


if __name__ == "__main__":
    main()

