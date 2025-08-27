#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
설정 파일 - API 키 및 기타 설정 관리
"""

import os
from typing import Optional, Dict, Any

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
    
    def get_database_config(self) -> Dict[str, Any]:
        """데이터베이스 설정 반환"""
        # 환경변수에서 데이터베이스 설정 로드
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'stock_analysis'),
            'charset': 'utf8mb4',
            'autocommit': True,
            'raise_on_warnings': True
        }
        
        # 환경변수가 없으면 기본 설정 파일에서 로드 시도
        if db_config['password'] == '' and db_config['user'] == 'root':
            db_config = self._load_database_config_from_file(db_config)
        
        return db_config
    
    def _load_database_config_from_file(self, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """파일에서 데이터베이스 설정 로드"""
        try:
            db_config_file = 'database_config.txt'
            if os.path.exists(db_config_file):
                with open(db_config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip().lower()
                                value = value.strip()
                                
                                if key == 'host':
                                    default_config['host'] = value
                                elif key == 'port':
                                    default_config['port'] = int(value)
                                elif key == 'user':
                                    default_config['user'] = value
                                elif key == 'password':
                                    default_config['password'] = value
                                elif key == 'database':
                                    default_config['database'] = value
                
                print(f"✅ 데이터베이스 설정 파일에서 로드: {db_config_file}")
            else:
                print(f"⚠️ 데이터베이스 설정 파일이 없습니다: {db_config_file}")
                print("기본 설정을 사용합니다.")
                
        except Exception as e:
            print(f"⚠️ 데이터베이스 설정 파일 로드 오류: {e}")
            print("기본 설정을 사용합니다.")
        
        return default_config
    
    def save_database_config(self, db_config: Dict[str, Any]) -> bool:
        """데이터베이스 설정을 파일에 저장"""
        try:
            db_config_file = 'database_config.txt'
            with open(db_config_file, 'w', encoding='utf-8') as f:
                f.write(f"# 데이터베이스 설정 파일\n")
                f.write(f"# 생성일시: {os.popen('date').read().strip()}\n\n")
                f.write(f"host={db_config['host']}\n")
                f.write(f"port={db_config['port']}\n")
                f.write(f"user={db_config['user']}\n")
                f.write(f"password={db_config['password']}\n")
                f.write(f"database={db_config['database']}\n")
            
            print(f"✅ 데이터베이스 설정이 저장되었습니다: {db_config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 데이터베이스 설정 저장 오류: {e}")
            return False

# 전역 설정 인스턴스
config = Config() 