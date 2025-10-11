#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프롬프트 관리를 위한 데이터베이스 테이블 생성 스크립트
"""

from database_config import DatabaseManager
import logging

def create_prompt_tables(db):
    """프롬프트 관련 테이블 생성"""
    
    # 1. 프롬프트 카테고리 테이블
    prompt_categories_table = """
    CREATE TABLE IF NOT EXISTS prompt_categories (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(50) NOT NULL UNIQUE,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_name (name),
        INDEX idx_is_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 2. 프롬프트 테이블
    prompts_table = """
    CREATE TABLE IF NOT EXISTS prompts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        category_id INT NOT NULL,
        name VARCHAR(200) NOT NULL,
        content TEXT NOT NULL,
        version VARCHAR(50),
        is_active BOOLEAN DEFAULT TRUE,
        is_default BOOLEAN DEFAULT FALSE,
        created_by VARCHAR(100) DEFAULT 'system',
        change_log TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES prompt_categories(id) ON DELETE CASCADE,
        INDEX idx_category_id (category_id),
        INDEX idx_is_active (is_active),
        INDEX idx_is_default (is_default),
        INDEX idx_version (version)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 3. 보안 설정 테이블 (API 키 등)
    secure_configs_table = """
    CREATE TABLE IF NOT EXISTS secure_configs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        config_key VARCHAR(100) NOT NULL UNIQUE,
        encrypted_value TEXT NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_config_key (config_key),
        INDEX idx_is_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # 테이블 생성 실행
    tables = [
        ("prompt_categories", prompt_categories_table),
        ("prompts", prompts_table),
        ("secure_configs", secure_configs_table)
    ]
    
    for table_name, table_sql in tables:
        try:
            if db.execute_query(table_sql):
                logging.info(f"✅ {table_name} 테이블 생성 완료")
            else:
                logging.error(f"❌ {table_name} 테이블 생성 실패")
                return False
        except Exception as e:
            logging.error(f"❌ {table_name} 테이블 생성 중 오류: {e}")
            return False
    
    return True

def insert_prompt_categories(db):
    """프롬프트 카테고리 데이터 삽입"""
    categories = [
        ('일봉', '일봉 차트 분석을 위한 프롬프트', 1),
        ('주봉', '주봉 차트 분석을 위한 프롬프트', 2),
        ('월봉', '월봉 차트 분석을 위한 프롬프트', 3),
        ('일봉 요약', '일봉 분석 결과 요약을 위한 프롬프트', 4),
        ('주봉 요약', '주봉 분석 결과 요약을 위한 프롬프트', 5),
        ('월봉 요약', '월봉 분석 결과 요약을 위한 프롬프트', 6),
        ('태그', '태그 분석을 위한 프롬프트', 7)
    ]
    
    insert_sql = """
    INSERT IGNORE INTO prompt_categories (name, description, sort_order)
    VALUES (%s, %s, %s)
    """
    
    try:
        if db.execute_many(insert_sql, categories):
            logging.info(f"✅ 프롬프트 카테고리 {len(categories)}개 삽입 완료")
            return True
        else:
            logging.error("❌ 프롬프트 카테고리 삽입 실패")
            return False
    except Exception as e:
        logging.error(f"❌ 프롬프트 카테고리 삽입 중 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 프롬프트 관리 테이블 생성 시작")
    print("="*50)
    
    # 데이터베이스 연결
    db = DatabaseManager()
    if not db.connect():
        print("❌ 데이터베이스 연결 실패")
        return
    
    try:
        # 프롬프트 테이블 생성
        print("📋 프롬프트 관련 테이블 생성 중...")
        if create_prompt_tables(db):
            print("✅ 모든 프롬프트 테이블 생성 완료")
        else:
            print("❌ 프롬프트 테이블 생성 실패")
            return
        
        # 프롬프트 카테고리 데이터 삽입
        print("\n📊 프롬프트 카테고리 데이터 삽입 중...")
        if insert_prompt_categories(db):
            print("✅ 프롬프트 카테고리 데이터 삽입 완료")
        else:
            print("❌ 프롬프트 카테고리 데이터 삽입 실패")
            return
        
        print("\n🎉 프롬프트 관리 테이블 생성 완료!")
        print("📊 생성된 테이블:")
        print("   - prompt_categories: 프롬프트 카테고리")
        print("   - prompts: 프롬프트 내용")
        print("   - secure_configs: 보안 설정 (API 키 등)")
        
    except Exception as e:
        logging.error(f"❌ 프롬프트 테이블 생성 중 오류: {e}")
        print(f"❌ 오류 발생: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    main()
