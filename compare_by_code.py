#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def compare_by_stock_code():
    """주식 코드로 비교"""
    
    # 웹에서 받은 파일 읽기 (주식 코드만)
    web_file = r"d:\Downloads\월간_거래대금_랭킹_20250917_18023.txt"
    fixed_file = "ranking_2025_08_after_fix.txt"
    
    print("🔍 주식 코드로 비교 중...")
    
    try:
        with open(web_file, 'r', encoding='utf-8') as f:
            web_codes = [line.strip() for line in f.readlines() if line.strip()]
        
        with open(fixed_file, 'r', encoding='utf-8') as f:
            fixed_content = f.read()
        
        # 수정된 파일에서 주식 코드 추출
        fixed_codes = []
        for line in fixed_content.split('\n'):
            if '위.' in line and '(' in line and ')' in line:
                # " 1위. 삼성전자 (005930)" 형식에서 코드 추출
                code = line.split('(')[1].split(')')[0]
                fixed_codes.append(code)
        
        print(f"\n📊 웹 파일: {len(web_codes)}개, 수정 후: {len(fixed_codes)}개")
        
        # 상위 50개 비교
        print("\n📊 상위 50개 주식 코드 비교:")
        print("-" * 80)
        print(f"{'순위':<4} {'웹 파일':<10} {'수정 후':<10} {'일치여부'}")
        print("-" * 80)
        
        matches = 0
        for i in range(min(50, len(web_codes), len(fixed_codes))):
            web_code = web_codes[i] if i < len(web_codes) else ""
            fixed_code = fixed_codes[i] if i < len(fixed_codes) else ""
            
            is_match = web_code == fixed_code
            if is_match:
                matches += 1
            
            print(f"{i+1:2d}위  {web_code:<10} {fixed_code:<10} {'✅' if is_match else '❌'}")
        
        print("-" * 80)
        print(f"일치율: {matches}/{min(50, len(web_codes), len(fixed_codes))} ({matches*100//min(50, len(web_codes), len(fixed_codes))}%)")
        
        if matches == min(50, len(web_codes), len(fixed_codes)):
            print("🎉 완벽히 일치합니다! 이중 정렬 문제가 해결되었습니다!")
        else:
            print("⚠️  여전히 차이가 있습니다. 추가 분석이 필요합니다.")
            
            # 차이가 나는 부분 분석
            print("\n🔍 차이 분석:")
            for i in range(min(10, len(web_codes), len(fixed_codes))):
                if web_codes[i] != fixed_codes[i]:
                    print(f"  {i+1}위: 웹={web_codes[i]}, 수정후={fixed_codes[i]}")
            
    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없습니다: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    compare_by_stock_code()
