#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최적화된 배치 주식 분석 프로그램 - 대화형 인터페이스
기능: 사용자 플로우에 맞는 단계별 분석 시스템
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict
import threading

# matplotlib 백엔드를 Agg로 설정 (안정성 확보)
import matplotlib
matplotlib.use('Agg')

# 전역 변수로 모듈 캐싱
_analysis_modules = {}

def get_analysis_module(chart_type_en: str):
    """분석 모듈 캐싱으로 성능 향상"""
    if chart_type_en not in _analysis_modules:
        if chart_type_en == "daily":
            import day_stock_analysis
            _analysis_modules[chart_type_en] = day_stock_analysis
        elif chart_type_en == "weekly":
            import week_stock_analysis
            _analysis_modules[chart_type_en] = week_stock_analysis
        elif chart_type_en == "monthly":
            import month_stock_analysis
            _analysis_modules[chart_type_en] = month_stock_analysis
    return _analysis_modules[chart_type_en]

def check_dependencies():
    """필요한 파일들 확인 (간소화)"""
    required_files = ["day_stock_analysis.py", "week_stock_analysis.py", "month_stock_analysis.py", "ai_chart_analysis.py", "config.py"]
    return all(os.path.exists(f) for f in required_files)

def check_api_key():
    """API 키 설정 확인 (간소화)"""
    try:
        from config import config
        return bool(config.get_api_key())
    except:
        return False

def get_stock_list_from_file():
    """파일에서 종목 목록 가져오기"""
    if os.path.exists("stock_list.txt"):
        with open("stock_list.txt", 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        # 종목코드만 추출 (6자리 숫자인 경우만)
        stocks = []
        for line in lines:
            if line.isdigit() and len(line) == 6:
                stocks.append(line)
        
        return stocks
    return []



def get_chart_type_options():
    """차트 유형 옵션 반환"""
    return [
        ("일봉", "daily"),
        ("주봉", "weekly"), 
        ("월봉", "monthly")
    ]

def extract_stock_code(stock_name: str) -> str:
    """종목코드 추출 (단순화)"""
    # 이미 6자리 숫자면 종목코드로 인식
    if stock_name.isdigit() and len(stock_name) == 6:
        return stock_name
    # 종목명이면 그대로 반환 (stock_list.txt에서 처리)
    return stock_name

def get_user_input_stocks():
    """사용자로부터 종목 입력 받기"""
    print("\n📊 1단계: 종목 입력 방법 선택")
    print("="*50)
    print("1. 종목명 직접 입력")
    print("2. 파일에서 읽기 (stock_list.txt)")
    
    while True:
        try:
            choice = input("\n선택하세요 (1-2): ").strip()
            if choice == "1":
                return get_manual_stock_input()
            elif choice == "2":
                return get_file_stock_input()
            else:
                print("❌ 1, 2 중에서 선택해주세요.")
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            sys.exit(0)

def get_manual_stock_input():
    """수동으로 종목 입력 받기"""
    print("\n📝 종목명을 입력하세요 (종료하려면 '완료' 입력)")
    print("예시: 삼성전자, 005930, SK하이닉스")
    
    stocks = []
    while True:
        try:
            stock_input = input(f"종목 {len(stocks)+1}: ").strip()
            if stock_input.lower() in ['완료', 'done', '']:
                break
            if stock_input:
                stocks.append(stock_input)
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            sys.exit(0)
    
    if not stocks:
        print("⚠️ 종목이 입력되지 않았습니다. 프로그램을 종료합니다.")
        sys.exit(0)
    
    return stocks

def get_file_stock_input():
    """파일에서 종목 읽기"""
    stocks = get_stock_list_from_file()
    if stocks:
        print(f"✅ 파일에서 {len(stocks)}개 종목을 읽었습니다.")
        return stocks
    else:
        print("❌ stock_list.txt 파일이 없거나 비어있습니다.")
        print("⚠️ 프로그램을 종료합니다.")
        sys.exit(0)



def get_user_chart_type():
    """사용자로부터 차트 유형 선택 받기"""
    print("\n📈 2단계: 차트 유형 선택")
    print("="*50)
    
    chart_options = get_chart_type_options()
    for i, (name, _) in enumerate(chart_options, 1):
        print(f"{i}. {name}")
    
    while True:
        try:
            choice = input("\n선택하세요 (1-3): ").strip()
            if choice in ['1', '2', '3']:
                idx = int(choice) - 1
                chart_type, chart_type_en = chart_options[idx]
                print(f"✅ 선택된 차트 유형: {chart_type}")
                return chart_type, chart_type_en
            else:
                print("❌ 1, 2, 3 중에서 선택해주세요.")
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            sys.exit(0)

def confirm_analysis(stock_list: List[str], chart_type: str):
    """분석 시작 전 확인"""
    print("\n🔍 3단계: 분석 설정 확인")
    print("="*50)
    print(f"📊 분석할 종목 수: {len(stock_list)}개")
    print(f"📈 차트 유형: {chart_type}")
    
    if len(stock_list) <= 10:
        print(f"📋 종목 목록: {', '.join(stock_list)}")
    else:
        print(f"📋 종목 목록: {', '.join(stock_list[:10])} ... 외 {len(stock_list)-10}개")
    
    while True:
        try:
            confirm = input("\n분석을 시작하시겠습니까? (y/n): ").strip().lower()
            if confirm in ['y', 'yes', '예', 'ㅇ']:
                return True
            elif confirm in ['n', 'no', '아니오', 'ㄴ']:
                return False
            else:
                print("❌ y 또는 n을 입력해주세요.")
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            sys.exit(0)

class FastProgressTracker:
    """고속 진행률 추적기"""
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.failed = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def update(self, success: bool = True):
        with self.lock:
            self.completed += 1
            if not success:
                self.failed += 1
            
            if self.completed % 5 == 0 or self.completed == self.total:  # 5개마다 출력
                progress = (self.completed / self.total) * 100
                elapsed = time.time() - self.start_time
                avg_time = elapsed / self.completed if self.completed > 0 else 0
                remaining = avg_time * (self.total - self.completed)
                
                print(f"\r📊 {progress:.1f}% ({self.completed}/{self.total}) | "
                      f"성공: {self.completed - self.failed} | 실패: {self.failed} | "
                      f"남은시간: {remaining/60:.1f}분", end="", flush=True)

def create_chart_fast(stock_code: str, chart_type_en: str) -> tuple[bool, object]:
    """고속 차트 생성"""
    try:
        module = get_analysis_module(chart_type_en)
        
        if chart_type_en == "daily":
            hist = module.get_stock_data(stock_code)
            if hist is not None and not hist.empty:
                module.analyze_stock_data(hist, stock_code)
                module.create_stock_chart(hist, stock_code)
                return True, hist
            else:
                print(f"   ❌ {stock_code}: 데이터가 없거나 비어있습니다.")
                return False, None
        elif chart_type_en == "weekly":
            hist = module.get_weekly_stock_data(stock_code)
            if hist is not None and not hist.empty:
                module.analyze_weekly_stock_data(hist, stock_code)
                module.create_weekly_stock_chart(hist, stock_code)
                return True, hist
            else:
                print(f"   ❌ {stock_code}: 주봉 데이터가 없거나 비어있습니다.")
                return False, None
        elif chart_type_en == "monthly":
            hist = module.get_monthly_stock_data(stock_code)
            if hist is not None and not hist.empty:
                module.analyze_monthly_stock_data(hist, stock_code)
                module.create_monthly_stock_chart(hist, stock_code)
                return True, hist
            else:
                print(f"   ❌ {stock_code}: 월봉 데이터가 없거나 비어있습니다.")
                return False, None
        
        return False, None
    except Exception as e:
        print(f"   ❌ {stock_code} 차트 생성 오류: {str(e)}")
        return False, None

def run_ai_analysis_fast(stock_name: str, stock_code: str, chart_type: str, chart_type_en: str, chart_data=None) -> bool:
    """고속 AI 분석"""
    try:
        charts_dir = f"{chart_type_en}_charts"
        if not os.path.exists(charts_dir):
            return False
        
        # 차트 파일 찾기 (최적화)
        chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.png') and stock_code in f]
        if not chart_files:
            return False
        
        selected_file = sorted(chart_files)[-1]
        
        # AI 분석 실행
        import ai_chart_analysis
        from config import config
        
        api_key = config.get_api_key()
        if not api_key:
            return False
        
        analyzer = ai_chart_analysis.AIChartAnalyzer(api_key)
        image_path = os.path.join(charts_dir, selected_file)
        
        # 차트 데이터가 있는 경우 AI 분석에 전달
        if chart_data is not None:
            result = analyzer.analyze_chart_image(image_path, "", chart_type, chart_data)
        else:
            result = analyzer.analyze_chart_image(image_path, "", chart_type)
        
        if result:
            # 결과 저장 (간소화)
            output_dir = "ai_analysis_results"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            json_path = os.path.join(output_dir, f"analysis_{chart_type_en}_{stock_name}_{timestamp}.json")
            doc_path = os.path.join(output_dir, f"analysis_{chart_type_en}_{stock_name}_{timestamp}.docx")
            
            json_success = analyzer.save_analysis_result(result, json_path)
            doc_success = analyzer.create_word_document(result, image_path, doc_path, chart_type)
            
            return json_success and doc_success
        
        return False
    except:
        return False

def analyze_single_stock_fast(stock_input: str, chart_type: str, chart_type_en: str, tracker: FastProgressTracker) -> Dict:
    """고속 단일 종목 분석"""
    result = {
        "stock_input": stock_input,
        "stock_code": None,
        "success": False,
        "error": None,
        "chart_created": False,
        "ai_analysis_done": False
    }
    
    try:
        # 종목코드 추출
        stock_code = extract_stock_code(stock_input)
        result["stock_code"] = stock_code
        
        # 차트 생성
        chart_success, chart_data = create_chart_fast(stock_code, chart_type_en)
        if chart_success:
            result["chart_created"] = True
            
            # AI 분석 (차트 데이터 포함)
            ai_success = run_ai_analysis_fast(stock_input, stock_code, chart_type, chart_type_en, chart_data)
            if ai_success:
                result["ai_analysis_done"] = True
                result["success"] = True
            else:
                result["error"] = "AI 분석 실패"
        else:
            result["error"] = "차트 생성 실패"
        
        if tracker:
            tracker.update(result["success"])
        return result
        
    except Exception as e:
        result["error"] = str(e)
        if tracker:
            tracker.update(False)
        return result

def run_batch_analysis_fast(stock_list: List[str], chart_type: str, chart_type_en: str):
    """고속 배치 분석"""
    print(f"\n🚀 4단계: 차트 생성 및 분석 시작")
    print(f"📊 총 {len(stock_list)}개 종목 | 차트 유형: {chart_type}")
    print("-" * 60)
    
    tracker = FastProgressTracker(len(stock_list))
    results = []
    
    # 순차 처리 (안정성 우선)
    for stock in stock_list:
        try:
            result = analyze_single_stock_fast(stock, chart_type, chart_type_en, tracker)
            results.append(result)
        except Exception as e:
            results.append({
                "stock_input": stock,
                "stock_code": None,
                "success": False,
                "error": str(e),
                "chart_created": False,
                "ai_analysis_done": False
            })
            tracker.update(False)
    
    print("\n")  # 진행률 출력 후 줄바꿈
    return results



def display_results_fast(results: List[Dict], chart_type: str):
    """고속 결과 표시"""
    print("\n" + "="*80)
    print("🎉 분석 완료!")
    print("="*80)
    
    total_stocks = len(results)
    successful_stocks = sum(1 for r in results if r["success"])
    failed_stocks = total_stocks - successful_stocks
    
    print(f"\n📊 분석 통계:")
    print(f"   📈 총 종목 수: {total_stocks}개")
    print(f"   ✅ 성공: {successful_stocks}개 ({successful_stocks/total_stocks*100:.1f}%)")
    print(f"   ❌ 실패: {failed_stocks}개 ({failed_stocks/total_stocks*100:.1f}%)")
    print(f"   📊 차트 유형: {chart_type}")
    
    # 성공한 종목들 (상위 10개만 표시)
    if successful_stocks > 0:
        print(f"\n✅ 성공한 종목들 (상위 10개):")
        for i, result in enumerate(results):
            if result["success"] and i < 10:
                print(f"   - {result['stock_input']} ({result['stock_code']})")
        if successful_stocks > 10:
            print(f"   ... 외 {successful_stocks - 10}개")
    
    print(f"\n📁 생성된 파일들:")
    print(f"   📈 차트 이미지: {chart_type.lower()}_charts/ 폴더")
    print(f"   🤖 AI 분석 결과: ai_analysis_results/ 폴더")

def main():
    """메인 함수 (대화형 인터페이스)"""
    print("🚀 최적화된 배치 주식 분석 프로그램")
    print("="*60)
    print("📊 대화형 다중 종목 분석 시스템")
    print("="*60)
    
    # 빠른 의존성 확인
    if not check_dependencies():
        print("❌ 필요한 파일이 없습니다.")
        return
    
    if not check_api_key():
        print("❌ API 키 설정이 필요합니다.")
        return
    
    print("✅ 모든 준비 완료")
    
    try:
        # 1단계: 종목 입력
        stock_list = get_user_input_stocks()
        
        # 2단계: 차트 유형 선택
        chart_type, chart_type_en = get_user_chart_type()
        
        # 3단계: 분석 확인
        if not confirm_analysis(stock_list, chart_type):
            print("👋 분석을 취소했습니다.")
            return
        
        # 4단계: 분석 실행
        start_time = time.time()
        results = run_batch_analysis_fast(stock_list, chart_type, chart_type_en)
        end_time = time.time()
        
        # 5단계: 결과 표시
        display_results_fast(results, chart_type)
        
        # 성능 통계
        total_time = end_time - start_time
        print(f"\n⏱️ 총 소요 시간: {total_time/60:.1f}분 ({total_time:.0f}초)")
        print(f"📊 평균 처리 시간: {total_time/len(stock_list):.1f}초/종목")
        print(f"🚀 처리 속도: {len(stock_list)/total_time:.1f}종목/초")
        
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
        sys.exit(0)

if __name__ == "__main__":
    main() 