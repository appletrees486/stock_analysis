#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
두 종목 자동 분석 스크립트
"""

from week_stock_analysis import (
    get_weekly_stock_data, 
    analyze_weekly_stock_data, 
    create_weekly_stock_chart,
    save_chart_data_to_json,
    save_chart_data_to_csv,
    save_chart_summary_to_text
)

def analyze_stock(stock_code):
    """단일 종목 분석"""
    print(f"\n{'='*60}")
    print(f"📊 {stock_code} 종목 분석 시작")
    print(f"{'='*60}")
    
    # 주봉 데이터 조회
    hist = get_weekly_stock_data(stock_code)
    
    if hist is not None:
        # 주봉 데이터 분석
        analyze_weekly_stock_data(hist, stock_code)
        
        # 주봉 차트 생성
        chart_result = create_weekly_stock_chart(hist, stock_code)
        
        if chart_result and len(chart_result) == 3:
            chart_path, stock_name, chart_data = chart_result
            print(f"🏢 종목명: {stock_name}")
            
            # JSON 저장
            json_path = save_chart_data_to_json(chart_data, stock_code, stock_name)
            
            # CSV 저장
            csv_path = save_chart_data_to_csv(chart_data, stock_code, stock_name)
            
            # 텍스트 요약 저장
            text_path = save_chart_summary_to_text(chart_data, stock_code, stock_name)
            
            if json_path:
                print(f"\n✅ {stock_code} 주봉 분석이 완료되었습니다!")
                print(f"📈 차트 이미지: {chart_path}")
                print(f"📊 JSON 데이터: {json_path}")
                if csv_path:
                    print(f"📋 CSV 데이터: {csv_path}")
                if text_path:
                    print(f"📝 텍스트 요약: {text_path}")
                return chart_path, json_path, stock_name
            else:
                print(f"\n❌ {stock_code} 데이터 파일 저장에 실패했습니다.")
                return None, None, None
        else:
            print(f"\n❌ {stock_code} 차트 생성에 실패했습니다.")
            return None, None, None
    else:
        print(f"\n❌ {stock_code} 주봉 데이터 조회에 실패했습니다.")
        return None, None, None

def main():
    """메인 함수"""
    print("🚀 두 종목 자동 주봉 분석 프로그램")
    print("="*60)
    
    # 분석할 종목 리스트
    stock_codes = ["005930", "097230"]
    
    results = {}
    
    for stock_code in stock_codes:
        chart_path, json_path, stock_name = analyze_stock(stock_code)
        results[stock_code] = {
            'chart_path': chart_path,
            'json_path': json_path,
            'stock_name': stock_name
        }
    
    # 결과 요약
    print(f"\n{'='*60}")
    print("📊 분석 결과 요약")
    print(f"{'='*60}")
    
    for stock_code, result in results.items():
        if result['chart_path'] and result['json_path']:
            print(f"✅ {stock_code} ({result['stock_name']}): 성공")
            print(f"   📈 차트: {result['chart_path']}")
            print(f"   📊 JSON: {result['json_path']}")
        else:
            print(f"❌ {stock_code}: 실패")
    
    print(f"\n💡 이제 AI 분석에 차트 이미지와 JSON 데이터를 전달할 수 있습니다!")

if __name__ == "__main__":
    main()
