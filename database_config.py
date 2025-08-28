#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 데이터베이스 연결 설정
"""

import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DatabaseManager:
    def __init__(self):
        """데이터베이스 연결 초기화"""
        self.connection = None
        self.cursor = None
        self.config = self._load_config()
    
    def _load_config(self):
        """데이터베이스 설정 로드"""
        # 환경변수에서 설정 로드
        config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', '1234'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'database': os.getenv('DB_NAME', 'stock_analysis'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
        
        # 환경변수가 없으면 파일에서 로드
        if config['host'] == 'localhost' and config['user'] == 'root':
            file_config = self._load_from_file()
            if file_config:
                config.update(file_config)
        
        # MySQL 8.0 auth_socket 문제 해결: 대안 사용자 생성
        if config['host'] == 'localhost' and config['user'] == 'root':
            # root 사용자 대신 대안 사용자 사용
            logging.warning("⚠️ root 사용자 auth_socket 문제로 인해 대안 설정 적용")
            config['user'] = 'stockapp'
            config['password'] = '1234'
        
        return config
    
    def _load_from_file(self):
        """database_config.txt 파일에서 설정 로드"""
        try:
            config_file = 'database_config.txt'
            if os.path.exists(config_file):
                config = {}
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == 'host':
                                config['host'] = value
                            elif key == 'port':
                                config['port'] = int(value)
                            elif key == 'user':
                                config['user'] = value
                            elif key == 'password':
                                config['password'] = value
                            elif key == 'database':
                                config['database'] = value
                
                logging.info(f"✅ 데이터베이스 설정 파일에서 로드: {config_file}")
                return config
            else:
                logging.warning(f"⚠️ 데이터베이스 설정 파일이 없습니다: {config_file}")
                
        except Exception as e:
            logging.error(f"⚠️ 데이터베이스 설정 파일 로드 오류: {e}")
        
        return None
    
    def connect(self):
        """데이터베이스 연결"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            logging.info("✅ MySQL 데이터베이스 연결 성공")
            return True
        except Error as e:
            logging.error(f"❌ MySQL 연결 실패: {e}")
            logging.warning("⚠️ 데이터베이스 없이 애플리케이션을 계속 실행합니다")
            # DB 연결 실패해도 애플리케이션은 계속 실행
            return False
    
    def disconnect(self):
        """데이터베이스 연결 해제"""
        try:
            if self.cursor:
                # 읽지 않은 결과가 있으면 소비
                try:
                    while self.cursor.nextset():
                        pass
                except:
                    pass
                self.cursor.close()
                self.cursor = None
        except Exception as e:
            logging.debug(f"커서 해제 중 오류: {e}")
        
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
        except Exception as e:
            logging.debug(f"연결 해제 중 오류: {e}")
        
        logging.info("🔌 데이터베이스 연결 해제")
    
    def get_last_insert_id(self):
        """마지막 삽입된 행의 ID 반환"""
        try:
            if not self.cursor:
                logging.error("데이터베이스 커서가 없습니다")
                return None
            
            return self.cursor.lastrowid
        except Error as e:
            logging.error(f"❌ 마지막 삽입 ID 조회 실패: {e}")
            return None
    
    def is_connected(self):
        """데이터베이스 연결 상태 확인"""
        try:
            if self.connection and self.connection.is_connected():
                # ping으로 실제 연결 상태 확인
                self.connection.ping(reconnect=False, attempts=1, delay=0)
                return True
            return False
        except Exception as e:
            logging.debug(f"연결 상태 확인 중 오류: {e}")
            return False
    
    def execute_query(self, query, params=None):
        """쿼리 실행"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return True
        except Error as e:
            logging.error(f"❌ 쿼리 실행 실패: {e}")
            logging.error(f"쿼리: {query}")
            if params:
                logging.error(f"파라미터: {params}")
            return False
    
    def fetch_all(self, query, params=None):
        """모든 결과 조회"""
        if self.execute_query(query, params):
            return self.cursor.fetchall()
        return []
    
    def fetch_one(self, query, params=None):
        """단일 결과 조회"""
        if self.execute_query(query, params):
            return self.cursor.fetchone()
        return None
    
    def execute_many(self, query, params_list):
        """여러 쿼리 실행 (배치 처리) - 연결 상태 확인 및 재연결 포함"""
        try:
            # 연결 상태 확인
            if not self.is_connected():
                logging.warning("⚠️ DB 연결이 끊어졌습니다. 재연결 시도 중...")
                if not self.connect():
                    logging.error("❌ DB 재연결 실패")
                    return False
                logging.info("✅ DB 재연결 성공")
            
            # 커서 상태 확인
            if not self.cursor:
                logging.error("❌ 커서가 초기화되지 않았습니다.")
                return False
            
            # 배치 실행
            self.cursor.executemany(query, params_list)
            self.connection.commit()
            
            affected_rows = self.cursor.rowcount
            logging.info(f"✅ 배치 쿼리 실행 성공: {len(params_list)}개 데이터, 영향받은 행: {affected_rows}개")
            return True
            
        except Error as e:
            logging.error(f"❌ 배치 쿼리 실행 실패: {e}")
            # 연결 오류인 경우 재시도
            if "not connected" in str(e).lower() or "lost connection" in str(e).lower():
                logging.warning("🔄 연결 오류 감지, 재연결 후 재시도...")
                if self.connect():
                    try:
                        self.cursor.executemany(query, params_list)
                        self.connection.commit()
                        logging.info("✅ 재시도 성공")
                        return True
                    except Error as retry_e:
                        logging.error(f"❌ 재시도 실패: {retry_e}")
            return False
    
    def commit(self):
        """변경사항 커밋"""
        if self.connection:
            self.connection.commit()
    
    def rollback(self):
        """변경사항 롤백"""
        if self.connection:
            self.connection.rollback()

# 테스트용 데이터베이스 설정
def create_test_database():
    """테스트용 데이터베이스 생성"""
    config = {
        'host': 'localhost',
        'user': 'root',
        'password': '1234',
        'port': 3306,
        'charset': 'utf8mb4'
    }
    
    try:
        # 데이터베이스 없이 연결
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # 데이터베이스 생성
        cursor.execute("CREATE DATABASE IF NOT EXISTS stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logging.info("✅ stock_analysis 데이터베이스 생성 완료")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        logging.error(f"❌ 테스트 데이터베이스 생성 실패: {e}")
        return False

def get_db_config():
    """데이터베이스 설정 반환"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', '1234'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'database': os.getenv('DB_NAME', 'stock_analysis'),
        'charset': 'utf8mb4',
        'autocommit': True
    }

if __name__ == "__main__":
    # 테스트 데이터베이스 생성
    create_test_database()
    
    # 연결 테스트
    db = DatabaseManager()
    if db.connect():
        print("✅ 데이터베이스 연결 테스트 성공")
        db.disconnect()
    else:
        print("❌ 데이터베이스 연결 테스트 실패")
