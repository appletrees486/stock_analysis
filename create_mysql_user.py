#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 사용자 생성 스크립트
auth_socket 문제 해결을 위한 대안 사용자 생성
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mysql_user():
    """MySQL 사용자 생성"""
    try:
        # MySQL 명령어들
        commands = [
            "CREATE DATABASE IF NOT EXISTS stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            "CREATE USER IF NOT EXISTS 'stockapp'@'localhost' IDENTIFIED BY '1234';",
            "GRANT ALL PRIVILEGES ON stock_analysis.* TO 'stockapp'@'localhost';",
            "FLUSH PRIVILEGES;"
        ]
        
        # 각 명령어 실행
        for cmd in commands:
            try:
                # mysql 명령어 실행 (비밀번호 없이)
                result = subprocess.run([
                    'mysql', '-u', 'root', '-e', cmd
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"✅ 성공: {cmd[:50]}...")
                else:
                    logger.error(f"❌ 실패: {cmd[:50]}...")
                    logger.error(f"오류: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"⏰ 타임아웃: {cmd[:50]}...")
            except Exception as e:
                logger.error(f"❌ 예외 발생: {e}")
        
        # 연결 테스트
        logger.info("🔍 새 사용자로 연결 테스트...")
        test_result = subprocess.run([
            'mysql', '-u', 'stockapp', '-p1234', '-e', 'SELECT 1;'
        ], capture_output=True, text=True, timeout=10)
        
        if test_result.returncode == 0:
            logger.info("✅ stockapp 사용자 연결 성공!")
            return True
        else:
            logger.error(f"❌ stockapp 사용자 연결 실패: {test_result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ MySQL 사용자 생성 중 오류: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 MySQL 사용자 생성 시작...")
    success = create_mysql_user()
    
    if success:
        logger.info("✅ MySQL 사용자 생성 완료!")
        logger.info("이제 애플리케이션에서 'stockapp' 사용자를 사용합니다.")
    else:
        logger.error("❌ MySQL 사용자 생성 실패")
        sys.exit(1)
