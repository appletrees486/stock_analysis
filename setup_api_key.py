#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 키 설정 스크립트
"""

from config import config

def main():
    """API 키 설정"""
    print("🔑 Google AI API 키 설정")
    print("="*50)
    print("Google AI API 키를 발급받는 방법:")
    print("1. https://makersuite.google.com/app/apikey 접속")
    print("2. Google 계정으로 로그인")
    print("3. 'Create API Key' 클릭")
    print("4. 생성된 API 키를 복사")
    print("="*50)
    
    # 현재 설정된 API 키 확인
    current_key = config.get_api_key()
    if current_key:
        print(f"현재 설정된 API 키: {current_key[:10]}...{current_key[-4:]}")
        change = input("API 키를 변경하시겠습니까? (y/N): ").strip().lower()
        if change != 'y':
            print("✅ 설정을 유지합니다.")
            return
    
    # 새 API 키 입력
    while True:
        api_key = input("\n🔑 Google AI API 키를 입력하세요: ").strip()
        
        if not api_key:
            print("❌ API 키를 입력해주세요.")
            continue
        
        if len(api_key) < 20:
            print("❌ 올바른 API 키 형식이 아닙니다.")
            continue
        
        # API 키 저장
        if config.set_api_key(api_key):
            print("✅ API 키가 성공적으로 저장되었습니다!")
            print(f"저장된 키: {api_key[:10]}...{api_key[-4:]}")
            break
        else:
            print("❌ API 키 저장에 실패했습니다.")
            retry = input("다시 시도하시겠습니까? (y/N): ").strip().lower()
            if retry != 'y':
                break

if __name__ == "__main__":
    main() 