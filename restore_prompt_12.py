#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프롬프트 ID 12번 복구 스크립트
prompts 테이블에서 id 12번 row의 일봉 차트 분석 프롬프트를 복구합니다.
"""

import mysql.connector
from mysql.connector import Error
from config import config

def restore_prompt_12():
    """ID 12번 프롬프트 복구"""
    try:
        # 데이터베이스 설정 로드
        db_config = config.get_database_config()
        
        # 데이터베이스 연결
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        print("🔗 데이터베이스에 연결되었습니다.")
        
        # ID 12번 프롬프트 현재 상태 확인
        cursor.execute("SELECT * FROM prompts WHERE id = 12")
        prompt_12 = cursor.fetchone()
        
        if not prompt_12:
            print("❌ ID 12번 프롬프트를 찾을 수 없습니다.")
            return False
        
        print(f"📋 ID 12번 프롬프트 현재 상태:")
        print(f"  ID: {prompt_12['id']}")
        print(f"  카테고리 ID: {prompt_12['category_id']}")
        print(f"  이름: {prompt_12['name']}")
        print(f"  버전: {prompt_12['version']}")
        print(f"  활성화: {prompt_12['is_active']}")
        print(f"  기본값: {prompt_12['is_default']}")
        print(f"  생성자: {prompt_12['created_by']}")
        print(f"  내용 길이: {len(prompt_12['content']) if prompt_12['content'] else 0} 문자")
        
        # 카테고리 정보 확인
        cursor.execute("SELECT name FROM prompt_categories WHERE id = %s", (prompt_12['category_id'],))
        category_result = cursor.fetchone()
        category_name = category_result['name'] if category_result else "알 수 없음"
        print(f"  카테고리: {category_name}")
        
        # 복구 작업 수행
        print("\n🔧 프롬프트 복구 작업 시작...")
        
        # 1. 프롬프트를 활성화 상태로 복구
        update_query = """
            UPDATE prompts 
            SET is_active = TRUE, is_default = TRUE, updated_at = NOW()
            WHERE id = 12
        """
        cursor.execute(update_query)
        
        # 2. 같은 카테고리의 다른 프롬프트들은 기본값 해제
        if prompt_12['category_id']:
            reset_default_query = """
                UPDATE prompts 
                SET is_default = FALSE, updated_at = NOW()
                WHERE category_id = %s AND id != 12
            """
            cursor.execute(reset_default_query, (prompt_12['category_id'],))
            print(f"✅ 같은 카테고리의 다른 프롬프트들의 기본값 해제 완료")
        
        # 변경사항 커밋
        conn.commit()
        print("✅ 프롬프트 복구 완료")
        
        # 복구 후 상태 확인
        cursor.execute("SELECT * FROM prompts WHERE id = 12")
        restored_prompt = cursor.fetchone()
        
        print(f"\n📋 복구 후 ID 12번 프롬프트 상태:")
        print(f"  활성화: {restored_prompt['is_active']}")
        print(f"  기본값: {restored_prompt['is_default']}")
        print(f"  업데이트 시간: {restored_prompt['updated_at']}")
        
        # 해당 카테고리의 활성 프롬프트 목록 확인
        if prompt_12['category_id']:
            cursor.execute("""
                SELECT id, name, version, is_active, is_default 
                FROM prompts 
                WHERE category_id = %s 
                ORDER BY is_default DESC, created_at DESC
            """, (prompt_12['category_id'],))
            
            category_prompts = cursor.fetchall()
            print(f"\n📋 카테고리 '{category_name}'의 프롬프트 목록:")
            for prompt in category_prompts:
                status = "🟢 활성+기본" if prompt['is_active'] and prompt['is_default'] else \
                        "🟡 활성" if prompt['is_active'] else "🔴 비활성"
                print(f"  {prompt['id']}. {prompt['name']} (v{prompt['version']}) - {status}")
        
        return True
        
    except Error as e:
        print(f"❌ 오류 발생: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("\n🔌 데이터베이스 연결이 종료되었습니다.")

if __name__ == "__main__":
    print("🚀 프롬프트 ID 12번 복구 시작")
    success = restore_prompt_12()
    
    if success:
        print("\n✅ 프롬프트 복구가 성공적으로 완료되었습니다!")
        print("이제 ID 12번 프롬프트가 활성화되고 기본값으로 설정되었습니다.")
    else:
        print("\n❌ 프롬프트 복구 중 오류가 발생했습니다.")
        print("데이터베이스 연결과 권한을 확인해주세요.")
