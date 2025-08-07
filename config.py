#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
설정 파일 - API 키 및 기타 설정 관리
"""

import os
from typing import Optional

class Config:
    """설정 관리 클래스"""
    
    def __init__(self):
        self.api_key = None
        self.load_api_key()
    
    def load_api_key(self) -> None:
        """API 키 로드"""
        # 1. 환경변수에서 로드
        self.api_key = os.getenv('GOOGLE_AI_API_KEY')
        
        # 2. 환경변수가 없으면 config.txt에서 로드
        if not self.api_key:
            self.api_key = self.load_from_file()
    
    def load_from_file(self) -> Optional[str]:
        """config.txt 파일에서 API 키 로드"""
        try:
            config_file = 'config.txt'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    api_key = f.read().strip()
                    if api_key:
                        return api_key
        except Exception as e:
            print(f"⚠️ 설정 파일 로드 오류: {e}")
        return None
    
    def save_api_key(self, api_key: str) -> bool:
        """API 키를 환경변수와 파일에 저장"""
        try:
            # 환경변수에 저장
            os.environ['GOOGLE_AI_API_KEY'] = api_key
            
            # 파일에 저장 (영구 보관)
            config_file = 'config.txt'
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(api_key)
            
            print("✅ API 키가 환경변수와 설정 파일에 저장되었습니다.")
            return True
        except Exception as e:
            print(f"❌ API 키 저장 오류: {e}")
            return False
    
    def get_api_key(self) -> Optional[str]:
        """API 키 반환"""
        return self.api_key
    
    def set_api_key(self, api_key: str) -> bool:
        """API 키 설정"""
        self.api_key = api_key
        return self.save_api_key(api_key)

# 전역 설정 인스턴스
config = Config() 