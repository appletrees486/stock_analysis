#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 차트 생성기 - 랭킹 종목들의 월봉 차트를 일괄 생성
"""

import subprocess
import sys
import time
from datetime import datetime

def generate_charts_from_file(file_path, ranking_type):
    """파일에서 종목코드를 읽어 차트를 생성"""
    print(f"🚀 {ranking_type} 랭킹 종목 차트 생성 시작")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    error_stocks = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            stock_code = line.strip()
            if not stock_code:
                continue
                
            print(f"\n📊 [{i:2d}/50] {stock_code} 차트 생성 중...")
            
            try:
                # month_stock_analysis.py 실행
                result = subprocess.run(
                    [sys.executable, 'month_stock_analysis.py'],
                    input=stock_code + '\n',
                    text=True,
                    capture_output=True,
                    timeout=60  # 60초 타임아웃
                )
                
                if result.returncode == 0:
                    print(f"   ✅ {stock_code} 차트 생성 완료")
                    success_count += 1
                else:
                    print(f"   ❌ {stock_code} 차트 생성 실패")
                    print(f"   오류: {result.stderr}")
                    error_count += 1
                    error_stocks.append(stock_code)
                
                # 1초 대기 (DB 부하 방지)
                time.sleep(1)
                
            except subprocess.TimeoutExpired:
                print(f"   ⏰ {stock_code} 타임아웃 (60초 초과)")
                error_count += 1
                error_stocks.append(stock_code)
            except Exception as e:
                print(f"   ❌ {stock_code} 오류: {str(e)}")
                error_count += 1
                error_stocks.append(stock_code)
    
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return
    
    # 결과 요약
    print("\n" + "=" * 60)
    print(f"📊 {ranking_type} 랭킹 차트 생성 완료")
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {error_count}개")
    
    if error_stocks:
        print(f"❌ 실패한 종목: {', '.join(error_stocks)}")
    
    return success_count, error_count, error_stocks

def main():
    """메인 함수"""
    print("🚀 랭킹 종목 배치 차트 생성기")
    print("=" * 60)
    
    # 파일 경로 설정
    trading_amount_file = r"D:\Downloads\월간_거래대금_랭킹_20250918_2029.txt"
    trading_rate_file = r"D:\Downloads\월간_거래율_랭킹_20250918_0947.txt"
    
    total_success = 0
    total_error = 0
    
    # 1. 월간 거래대금 랭킹 차트 생성
    print("\n🔥 1단계: 월간 거래대금 랭킹 차트 생성")
    success1, error1, errors1 = generate_charts_from_file(trading_amount_file, "월간 거래대금")
    total_success += success1
    total_error += error1
    
    # 2. 월간 거래율 랭킹 차트 생성
    print("\n🔥 2단계: 월간 거래율 랭킹 차트 생성")
    success2, error2, errors2 = generate_charts_from_file(trading_rate_file, "월간 거래율")
    total_success += success2
    total_error += error2
    
    # 전체 결과
    print("\n" + "=" * 60)
    print("🎯 전체 결과 요약")
    print("=" * 60)
    print(f"✅ 총 성공: {total_success}개")
    print(f"❌ 총 실패: {total_error}개")
    print(f"📊 성공률: {total_success/(total_success+total_error)*100:.1f}%")
    
    if errors1 or errors2:
        print(f"\n❌ 실패한 종목 목록:")
        if errors1:
            print(f"   거래대금 랭킹: {', '.join(errors1)}")
        if errors2:
            print(f"   거래율 랭킹: {', '.join(errors2)}")
    
    print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
