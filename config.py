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
        """환경변수에서만 API 키 로드 (config.txt 파일 제거됨)"""
        return None
    
    def save_api_key(self, api_key: str) -> bool:
        """API 키를 환경변수에 저장 (config.txt 파일 제거됨)"""
        try:
            os.environ['GOOGLE_AI_API_KEY'] = api_key
            print("✅ API 키가 환경변수에 저장되었습니다.")
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