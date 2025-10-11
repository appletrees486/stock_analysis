#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프롬프트 관리 클래스들
2단계: 프롬프트 관리 클래스 구현
"""

import os
import json
import base64
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import mysql.connector
from mysql.connector import Error
from cryptography.fernet import Fernet

class SecureConfigManager:
    """암호화된 설정 관리 클래스"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.cipher_suite = self._get_or_create_cipher()
    
    def _get_or_create_cipher(self) -> Fernet:
        """암호화 키 생성 또는 로드"""
        key_file = ".secret_key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            # 새로운 암호화 키 생성
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            print("🔐 새로운 암호화 키가 생성되었습니다.")
        
        return Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """값을 암호화"""
        return self.cipher_suite.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """암호화된 값을 복호화"""
        return self.cipher_suite.decrypt(encrypted_value.encode()).decode()
    
    def _get_connection(self):
        """DB 연결 반환"""
        return mysql.connector.connect(**self.db_config)
    
    def save_api_key(self, api_key: str, key_name: str = "gemini_api_key") -> bool:
        """API 키를 암호화하여 DB에 저장"""
        try:
            encrypted_key = self.encrypt_value(api_key)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 기존 키가 있으면 업데이트, 없으면 삽입
            upsert_query = """
                INSERT INTO secure_configs (config_key, encrypted_value, description, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE 
                encrypted_value = %s,
                description = %s,
                updated_at = NOW()
            """
            
            description = f"Google AI Gemini API 키 - {key_name}"
            cursor.execute(upsert_query, (key_name, encrypted_key, description, encrypted_key, description))
            conn.commit()
            
            print(f"✅ {key_name}이 암호화되어 저장되었습니다.")
            return True
            
        except Error as e:
            print(f"❌ API 키 저장 중 오류: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_api_key(self, key_name: str = "gemini_api_key") -> Optional[str]:
        """암호화된 API 키를 복호화하여 반환"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = "SELECT encrypted_value FROM secure_configs WHERE config_key = %s AND is_active = TRUE"
            cursor.execute(query, (key_name,))
            result = cursor.fetchone()
            
            if result:
                encrypted_value = result['encrypted_value']
                return self.decrypt_value(encrypted_value)
            else:
                return None
                
        except Error as e:
            print(f"❌ API 키 조회 중 오류: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def test_api_key(self, api_key: str) -> bool:
        """API 키 유효성 테스트"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("테스트")
            return True
        except Exception as e:
            print(f"❌ API 키 유효성 검증 실패: {e}")
            return False

class PromptManager:
    """DB에서 프롬프트를 관리하는 클래스"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
    
    def _get_connection(self):
        """DB 연결 반환"""
        return mysql.connector.connect(**self.db_config)
    
    def get_prompt(self, chart_type: str, version: str = None) -> str:
        """차트 유형에 따른 프롬프트 반환"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 차트 유형을 카테고리명으로 매핑
            category_mapping = {
                'daily': '일봉', '일봉': '일봉', 'day': '일봉',
                'weekly': '주봉', '주봉': '주봉', 'week': '주봉',
                'monthly': '월봉', '월봉': '월봉', 'month': '월봉',
                'daily-summary': '일봉 요약', '일봉 요약': '일봉 요약',
                'weekly-summary': '주봉 요약', '주봉 요약': '주봉 요약',
                'monthly-summary': '월봉 요약', '월봉 요약': '월봉 요약',
                'tag': '태그', '태그': '태그'
            }
            
            # chart_type이 이미 한글이면 그대로 사용, 영어면 매핑
            if chart_type in ['일봉', '주봉', '월봉', '일봉 요약', '주봉 요약', '월봉 요약', '태그']:
                category_name = chart_type
            else:
                category_name = category_mapping.get(chart_type.lower(), '일봉')
            
            # 먼저 prompt_categories에서 category_id 조회
            category_query = "SELECT id FROM prompt_categories WHERE name = %s LIMIT 1"
            cursor.execute(category_query, (category_name,))
            category_result = cursor.fetchone()
            
            if not category_result:
                print(f"⚠️ 프롬프트 카테고리 '{category_name}'을 찾을 수 없습니다.")
                return self._get_fallback_prompt(chart_type)
            
            category_id = category_result['id']
            
            # 기본 프롬프트 조회
            if version:
                query = """
                    SELECT content 
                    FROM prompts 
                    WHERE category_id = %s AND version = %s AND is_active = TRUE
                    LIMIT 1
                """
                cursor.execute(query, (category_id, version))
            else:
                query = """
                    SELECT content 
                    FROM prompts 
                    WHERE category_id = %s AND is_active = TRUE
                    ORDER BY is_default DESC, version DESC
                    LIMIT 1
                """
                cursor.execute(query, (category_id,))
            
            result = cursor.fetchone()
            
            if result:
                print(f"✅ DB에서 {category_name} 프롬프트 조회 성공")
                return result['content']
            else:
                print(f"⚠️ DB에서 {category_name} 프롬프트를 찾을 수 없습니다.")
                # 기본값이 없으면 하드코딩된 프롬프트 반환
                return self._get_fallback_prompt(chart_type)
                
        except Error as e:
            print(f"❌ 프롬프트 조회 중 오류: {e}")
            return self._get_fallback_prompt(chart_type)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def _get_fallback_prompt(self, chart_type: str) -> str:
        """DB 조회 실패 시 하드코딩된 기본 프롬프트 반환"""
        # 기존 코드의 프롬프트들을 여기에 유지
        if chart_type.lower() in ['daily', '일봉', 'day']:
            return """
일봉 차트 분석 프롬프트 (fallback)
역할: 당신은 전문 주식 트레이더이자 차트 분석 전문가입니다.
[기존 일봉 프롬프트 내용...]
"""
        elif chart_type.lower() in ['weekly', '주봉', 'week']:
            return """
주봉 차트 분석 프롬프트 (fallback)
역할: 당신은 전문 주식 트레이더이자 차트 분석 전문가입니다.
[기존 주봉 프롬프트 내용...]
"""
        elif chart_type.lower() in ['monthly', '월봉', 'month']:
            return """
월봉 차트 분석 프롬프트 (fallback)
역할: 당신은 전문 주식 트레이더이자 차트 분석 전문가입니다.
[기존 월봉 프롬프트 내용...]
"""
        else:
            return """
일봉 차트 분석 프롬프트 (fallback)
역할: 당신은 전문 주식 트레이더이자 차트 분석 전문가입니다.
[기본 프롬프트 내용...]
"""
    
    def update_prompt(self, chart_type: str, content: str, version: str = None, created_by: str = "system") -> bool:
        """프롬프트 업데이트"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            category_mapping = {
                'daily': '일봉', '일봉': '일봉', 'day': '일봉',
                'weekly': '주봉', '주봉': '주봉', 'week': '주봉',
                'monthly': '월봉', '월봉': '월봉', 'month': '월봉',
                'daily-summary': '일봉 요약', '일봉 요약': '일봉 요약',
                'weekly-summary': '주봉 요약', '주봉 요약': '주봉 요약',
                'monthly-summary': '월봉 요약', '월봉 요약': '월봉 요약',
                'tag': '태그', '태그': '태그'
            }
            
            # chart_type이 이미 한글이면 그대로 사용, 영어면 매핑
            if chart_type in ['일봉', '주봉', '월봉', '일봉 요약', '주봉 요약', '월봉 요약', '태그']:
                category_name = chart_type
            else:
                category_name = category_mapping.get(chart_type.lower(), '일봉')
            
            # 카테고리 ID 조회
            cursor.execute("SELECT id FROM prompt_categories WHERE name = %s", (category_name,))
            category_result = cursor.fetchone()
            
            if not category_result:
                print(f"❌ 카테고리를 찾을 수 없습니다: {category_name}")
                return False
            
            category_id = category_result[0]
            
            # 기존 프롬프트 비활성화
            update_query = """
                UPDATE prompts 
                SET is_active = FALSE, is_default = FALSE
                WHERE category_id = %s
            """
            cursor.execute(update_query, (category_id,))
            
            # 새 프롬프트 추가
            version = version or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            prompt_name = f"{category_name} 프롬프트 v{version}"
            
            insert_query = """
                INSERT INTO prompts (category_id, name, content, version, is_active, is_default, created_by, change_log)
                VALUES (%s, %s, %s, %s, TRUE, TRUE, %s, %s)
            """
            
            change_log = f"프롬프트 업데이트 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by {created_by}"
            cursor.execute(insert_query, (category_id, prompt_name, content, version, created_by, change_log))
            
            conn.commit()
            print(f"✅ {category_name} 프롬프트 업데이트 완료 (v{version})")
            return True
            
        except Error as e:
            print(f"❌ 프롬프트 업데이트 중 오류: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_prompt_versions(self, chart_type: str) -> List[Dict[str, Any]]:
        """프롬프트 버전 목록 조회"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            category_mapping = {
                'daily': '일봉', '일봉': '일봉', 'day': '일봉',
                'weekly': '주봉', '주봉': '주봉', 'week': '주봉',
                'monthly': '월봉', '월봉': '월봉', 'month': '월봉',
                'daily-summary': '일봉 요약', '일봉 요약': '일봉 요약',
                'weekly-summary': '주봉 요약', '주봉 요약': '주봉 요약',
                'monthly-summary': '월봉 요약', '월봉 요약': '월봉 요약',
                'tag': '태그', '태그': '태그'
            }
            
            # chart_type이 이미 한글이면 그대로 사용, 영어면 매핑
            if chart_type in ['일봉', '주봉', '월봉', '일봉 요약', '주봉 요약', '월봉 요약', '태그']:
                category_name = chart_type
            else:
                category_name = category_mapping.get(chart_type.lower(), '일봉')
            
            query = """
                SELECT p.id, p.name, p.version, p.is_active, p.is_default, p.created_by, p.created_at, p.updated_at
                FROM prompts p
                JOIN prompt_categories pc ON p.category_id = pc.id
                WHERE pc.name = %s
                ORDER BY p.created_at DESC
            """
            
            cursor.execute(query, (category_name,))
            results = cursor.fetchall()
            
            return results
            
        except Error as e:
            print(f"❌ 프롬프트 버전 조회 중 오류: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def delete_prompt_version(self, prompt_id: int) -> bool:
        """프롬프트 버전 삭제 (실제 삭제하지 않고 비활성화)"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            update_query = """
                UPDATE prompts 
                SET is_active = FALSE, is_default = FALSE
                WHERE id = %s
            """
            
            cursor.execute(update_query, (prompt_id,))
            conn.commit()
            
            print(f"✅ 프롬프트 버전 비활성화 완료 (ID: {prompt_id})")
            return True
            
        except Error as e:
            print(f"❌ 프롬프트 버전 비활성화 중 오류: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

class UnifiedConfigManager:
    """통합 설정 관리 클래스 (API 키 + 프롬프트 + 시스템 설정)"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.secure_manager = SecureConfigManager(db_config)
        self.prompt_manager = PromptManager(db_config)
    
    def get_system_config(self, key: str, default_value=None):
        """시스템 설정 조회 (기본값 반환)"""
        # 기본 설정값 반환
        default_configs = {
            'max_retry_count': 3,
            'analysis_timeout': 300,
            'chart_image_max_size': 2000
        }
        return default_configs.get(key, default_value)
    
    def update_system_config(self, key: str, value: Any, description: str = None) -> bool:
        """시스템 설정 업데이트 (기본값만 지원)"""
        print(f"⚠️ 시스템 설정 업데이트는 지원되지 않습니다: {key}")
        return False

def test_prompt_manager():
    """프롬프트 매니저 테스트"""
    print("🧪 프롬프트 매니저 테스트 시작")
    
    # 데이터베이스 설정 로드
    from config import config
    db_config = config.get_database_config()
    
    # 통합 설정 관리자 초기화
    config_manager = UnifiedConfigManager(db_config)
    

    
    # 프롬프트 조회 테스트
    chart_types = ['일봉', '주봉', '월봉']
    
    for chart_type in chart_types:
        print(f"\n📊 {chart_type} 프롬프트 테스트:")
        prompt = config_manager.prompt_manager.get_prompt(chart_type)
        print(f"  길이: {len(prompt)} 문자")
        print(f"  시작: {prompt[:100]}...")
        
        # 버전 목록 조회
        versions = config_manager.prompt_manager.get_prompt_versions(chart_type)
        print(f"  버전 수: {len(versions)}개")
    
    print("\n✅ 프롬프트 매니저 테스트 완료")

if __name__ == "__main__":
    test_prompt_manager()
