#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 주식 분석 프로그램 - 차트 생성 + AI 분석
순서: 1. 종목명 입력 → 2. 차트 유형 선택 → 3. 차트 생성 → 4. AI 분석 → 5. 결과 저장
"""

# matplotlib 백엔드를 Agg로 설정 (tkinter 에러 방지)
import matplotlib
matplotlib.use('Agg')

import os
import sys
from datetime import datetime

def check_dependencies():
    """필요한 파일들 확인"""
    required_files = [
        "day_stock_analysis.py",
        "week_stock_analysis.py", 
        "month_stock_analysis.py",
        "ai_chart_analysis.py",
        "config.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 필요한 파일이 없습니다:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def check_api_key():
    """API 키 설정 확인"""
    try:
        from config import config
        api_key = config.get_api_key()
        if not api_key:
            print("⚠️ Google AI API 키가 설정되지 않았습니다.")
            print("setup_api_key.py를 실행하여 API 키를 설정해주세요.")
            return False
        return True
    except Exception as e:
        print(f"❌ API 키 확인 중 오류: {e}")
        return False

def get_stock_input():
    """1단계: 종목명 또는 종목코드 입력 받기"""
    print("📈 1단계: 종목명 또는 종목코드 입력")
    print("-" * 50)
    
    while True:
        user_input = input("📈 종목명 또는 종목코드를 입력하세요 (예: 삼성전자, 005930): ").strip()
        if user_input:
            # 종목코드인지 확인 (6자리 숫자)
            if user_input.isdigit() and len(user_input) == 6:
                return user_input  # 종목코드 그대로 반환
            else:
                return user_input  # 종목명으로 처리
        else:
            print("❌ 종목명 또는 종목코드를 입력해주세요.")

def get_chart_type_selection():
    """2단계: 차트 유형 선택"""
    print("\n📊 2단계: 차트 유형 선택")
    print("-" * 50)
    
    chart_types = [
        ("1", "일봉", "daily"),
        ("2", "주봉", "weekly"), 
        ("3", "월봉", "monthly")
    ]
    
    print("📊 분석할 차트 유형을 선택하세요:")
    for num, korean_name, english_name in chart_types:
        print(f"   {num}. {korean_name} 차트")
    
    while True:
        choice = input(f"\n📊 차트 유형을 선택하세요 (1-3): ").strip()
        
        for num, korean_name, english_name in chart_types:
            if choice == num:
                return korean_name, english_name
        
        print("❌ 올바른 번호를 입력해주세요 (1-3)")

def run_chart_generation(stock_name: str, chart_type: str, chart_type_en: str):
    """3단계: 차트 생성 실행"""
    print(f"\n📈 3단계: {chart_type} 차트 생성")
    print("-" * 50)
    
    try:
        # 차트 유형에 따른 분석 모듈 선택
        if chart_type_en == "daily":
            import day_stock_analysis as analysis_module
            print(f"🔍 {stock_name} 일봉 데이터 조회 중...")
        elif chart_type_en == "weekly":
            import week_stock_analysis as analysis_module
            print(f"🔍 {stock_name} 주봉 데이터 조회 중...")
        elif chart_type_en == "monthly":
            import month_stock_analysis as analysis_module
            print(f"🔍 {stock_name} 월봉 데이터 조회 중...")
        else:
            print(f"❌ 지원하지 않는 차트 유형: {chart_type}")
            return False, None, None
        
        # 종목코드 추출 (종목명에서)
        stock_code = extract_stock_code_from_name(stock_name)
        if not stock_code:
            print(f"❌ 종목코드를 찾을 수 없습니다: {stock_name}")
            return False, None, None
        
        # 차트 데이터 조회 (함수명 차트 유형별로 다름)
        if chart_type_en == "daily":
            hist = analysis_module.get_stock_data(stock_code)
        elif chart_type_en == "weekly":
            hist = analysis_module.get_weekly_stock_data(stock_code)
        elif chart_type_en == "monthly":
            hist = analysis_module.get_monthly_stock_data(stock_code)
        
        if hist is not None:
            # 차트 데이터 분석 (함수명 차트 유형별로 다름)
            if chart_type_en == "daily":
                analysis_module.analyze_stock_data(hist, stock_code)
                analysis_module.create_stock_chart(hist, stock_code)
            elif chart_type_en == "weekly":
                analysis_module.analyze_weekly_stock_data(hist, stock_code)
                analysis_module.create_weekly_stock_chart(hist, stock_code)
            elif chart_type_en == "monthly":
                analysis_module.analyze_monthly_stock_data(hist, stock_code)
                analysis_module.create_monthly_stock_chart(hist, stock_code)
            
            print(f"✅ {chart_type} 차트 생성 완료")
            return True, stock_code, hist
        else:
            print(f"❌ {chart_type} 데이터 조회에 실패했습니다.")
            return False, None, None
            
    except Exception as e:
        print(f"❌ {chart_type} 차트 생성 중 오류: {e}")
        return False, None, None

def extract_stock_code_from_name(stock_name: str) -> str:
    """종목명에서 종목코드 추출 또는 종목코드 직접 반환"""
    # 이미 종목코드인 경우 (6자리 숫자)
    if stock_name.isdigit() and len(stock_name) == 6:
        return stock_name
    
    # 사용자 입력으로 종목코드 직접 입력 받기
    print(f"⚠️ '{stock_name}'의 종목코드를 찾을 수 없습니다.")
    while True:
        stock_code = input(f"📈 '{stock_name}'의 종목코드를 직접 입력하세요 (6자리 숫자): ").strip()
        if stock_code.isdigit() and len(stock_code) == 6:
            return stock_code
        else:
            print("❌ 올바른 종목코드를 입력해주세요 (6자리 숫자)")

def run_ai_analysis_automated(stock_name: str, stock_code: str, chart_type: str, chart_type_en: str, chart_data=None):
    """4단계: 자동으로 AI 분석 실행"""
    print(f"\n🤖 4단계: AI {chart_type} 차트 분석")
    print("-" * 50)
    
    try:
        # 차트 폴더에서 해당 종목의 차트 파일 찾기
        charts_dir = f"{chart_type_en}_charts"
        if not os.path.exists(charts_dir):
            print(f"❌ {charts_dir} 폴더를 찾을 수 없습니다.")
            return False
        
        chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.png') and stock_code in f]
        
        if not chart_files:
            print(f"❌ 해당 종목의 {chart_type} 차트 파일을 찾을 수 없습니다.")
            return False
        
        # 가장 최근 파일 선택 (파일명에 날짜가 포함되어 있음)
        selected_file = sorted(chart_files)[-1]
        print(f"📁 선택된 차트 파일: {selected_file}")
        
        # ai_chart_analysis.py의 함수들을 직접 호출
        import ai_chart_analysis
        from config import config
        
        # API 키 가져오기
        api_key = config.get_api_key()
        if not api_key:
            print("❌ API 키를 가져올 수 없습니다.")
            return False
        
        # AI 분석기 초기화
        analyzer = ai_chart_analysis.AIChartAnalyzer(api_key)
        
        # 파일 경로 설정
        image_path = os.path.join(charts_dir, selected_file)
        
        print(f"🔍 분석 시작: {stock_name}")
        print(f"📁 파일: {image_path}")
        print(f"📊 차트 유형: {chart_type}")
        
        # 차트 데이터가 있는 경우 AI 분석에 전달
        if chart_data is not None:
            print(f"📊 차트 데이터 정보: {len(chart_data)}개 데이터 포인트")
            # AI 분석 실행 (차트 데이터 포함)
            result = analyzer.analyze_chart_image(image_path, "", chart_type, chart_data)
        else:
            print(f"⚠️ 차트 데이터가 없어 이미지만으로 분석을 진행합니다.")
            # AI 분석 실행 (이미지만)
            result = analyzer.analyze_chart_image(image_path, "", chart_type)
        
        if result:
            # 결과 저장
            output_dir = "ai_analysis_results"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # JSON 파일 저장 (차트 유형 포함)
            json_filename = f"analysis_{chart_type_en}_{stock_name}_{timestamp}.json"
            json_path = os.path.join(output_dir, json_filename)
            
            # Word 문서 저장 (차트 유형 포함)
            doc_filename = f"analysis_{chart_type_en}_{stock_name}_{timestamp}.docx"
            doc_path = os.path.join(output_dir, doc_filename)
            
            # JSON 파일 저장
            json_success = analyzer.save_analysis_result(result, json_path)
            
            # Word 문서 생성
            doc_success = analyzer.create_word_document(result, image_path, doc_path, chart_type)
            
            if json_success and doc_success:
                print("✅ AI 분석 완료")
                print(f"📄 JSON 결과 파일: {json_path}")
                print(f"📄 Word 문서 파일: {doc_path}")
                
                # 주요 결과 출력
                if "투자아이디어" in result:
                    print(f"\n📈 투자 아이디어:")
                    trend_key = "단기추세" if "단기추세" in result['투자아이디어'] else "중기추세" if "중기추세" in result['투자아이디어'] else "장기추세"
                    print(f"   추세: {result['투자아이디어'].get(trend_key, 'N/A')}")
                    print(f"   매매 시점: {result['투자아이디어'].get('매매시점', 'N/A')}")
                    print(f"   핵심 포인트: {result['투자아이디어'].get('핵심포인트', 'N/A')}")
                
                return True
            else:
                if not json_success:
                    print("❌ JSON 결과 저장에 실패했습니다.")
                if not doc_success:
                    print("❌ Word 문서 생성에 실패했습니다.")
                return False
        else:
            print("❌ AI 분석에 실패했습니다.")
            return False
            
    except Exception as e:
        print(f"❌ AI 분석 중 오류: {e}")
        return False

def show_final_results(stock_name: str, chart_type: str):
    """최종 결과 파일들 표시"""
    print("\n" + "="*60)
    print("🎉 전체 분석이 완료되었습니다!")
    print("="*60)
    
    print(f"\n📊 분석 정보:")
    print(f"   종목명: {stock_name}")
    print(f"   차트 유형: {chart_type}")
    
    print("\n📁 생성된 파일들:")
    
    # 차트 이미지 확인
    chart_folders = ["daily_charts", "weekly_charts", "monthly_charts"]
    for folder in chart_folders:
        if os.path.exists(folder):
            chart_files = [f for f in os.listdir(folder) if f.endswith('.png') and stock_name in f]
            if chart_files:
                print(f"   📈 {folder}: {len(chart_files)}개")
                for file in chart_files:
                    print(f"      - {file}")
    
    # AI 분석 결과 확인
    if os.path.exists("ai_analysis_results"):
        result_files = [f for f in os.listdir("ai_analysis_results") if f.endswith(('.json', '.docx')) and stock_name in f]
        if result_files:
            json_files = [f for f in result_files if f.endswith('.json')]
            doc_files = [f for f in result_files if f.endswith('.docx')]
            
            print(f"   🤖 AI 분석 결과: {len(result_files)}개")
            print(f"      📄 JSON 파일: {len(json_files)}개")
            print(f"      📄 Word 문서: {len(doc_files)}개")
            
            for file in result_files:
                print(f"         - {file}")
    
    print("\n💡 사용법:")
    print("   1. 차트 이미지: 각 차트 폴더에서 확인")
    print("   2. JSON 분석 결과: ai_analysis_results/ 폴더에서 확인")
    print("   3. Word 문서: ai_analysis_results/ 폴더에서 확인")

def main():
    """메인 함수"""
    print("🚀 통합 주식 분석 프로그램")
    print("="*60)
    print("📊 종목명 입력 → 차트 유형 선택 → 차트 생성 → AI 분석")
    print("="*60)
    
    # 의존성 확인
    if not check_dependencies():
        print("\n❌ 프로그램을 실행할 수 없습니다.")
        print("필요한 파일들을 확인해주세요.")
        return
    
    # API 키 확인
    if not check_api_key():
        print("\n❌ API 키 설정이 필요합니다.")
        print("setup_api_key.py를 실행하여 API 키를 설정해주세요.")
        return
    
    print("\n✅ 모든 준비가 완료되었습니다.")
    print("순서대로 실행을 시작합니다...")
    
    # 1단계: 종목명 입력
    stock_name = get_stock_input()
    
    # 2단계: 차트 유형 선택
    chart_type, chart_type_en = get_chart_type_selection()
    
    print("\n" + "="*60)
    
    # 3단계: 차트 생성
    chart_success, stock_code, chart_data = run_chart_generation(stock_name, chart_type, chart_type_en)
    
    if chart_success and stock_code:
        print("\n" + "="*60)
        
        # 4단계: AI 분석
        if run_ai_analysis_automated(stock_name, stock_code, chart_type, chart_type_en, chart_data):
            show_final_results(stock_name, chart_type)
        else:
            print("\n❌ AI 분석에 실패했습니다.")
            print("차트는 생성되었지만 AI 분석을 완료할 수 없습니다.")
    else:
        print("\n❌ 차트 생성에 실패했습니다.")
        print("AI 분석을 진행할 수 없습니다.")

if __name__ == "__main__":
    main() 