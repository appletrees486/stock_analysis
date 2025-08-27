#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stocks_data.json 파일을 읽어서 DB의 stocks 테이블에 중복 없이 업데이트하는 스크립트
"""

import json
import mysql.connector
from mysql.connector import Error
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def connect_to_database():
    """데이터베이스에 연결"""
    try:
        # 데이터베이스 설정
        db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '1234',
            'database': 'stock_analysis',
            'charset': 'utf8mb4',
            'autocommit': False,
            'raise_on_warnings': True
        }
        
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("MySQL 데이터베이스에 성공적으로 연결되었습니다.")
            return connection
    except Error as e:
        print(f"데이터베이스 연결 오류: {e}")
        return None

def load_stocks_data(json_file_path):
    """JSON 파일에서 주식 데이터 로드"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        print(f"JSON 파일에서 {len(data)}개의 주식 데이터를 로드했습니다.")
        return data
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return None

def get_existing_stocks(connection):
    """기존 stocks 테이블의 주식 코드 조회"""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT stock_code FROM stocks")
        existing_codes = {row[0] for row in cursor.fetchall()}
        cursor.close()
        print(f"기존 stocks 테이블에서 {len(existing_codes)}개의 주식 코드를 조회했습니다.")
        return existing_codes
    except Error as e:
        print(f"기존 주식 조회 오류: {e}")
        return set()

def insert_new_stocks(connection, stocks_data, existing_codes):
    """새로운 주식 데이터를 stocks 테이블에 삽입"""
    try:
        cursor = connection.cursor()
        
        # 중복되지 않는 새로운 주식만 필터링
        new_stocks = []
        for stock in stocks_data:
            if stock['stock_code'] not in existing_codes:
                new_stocks.append(stock)
        
        if not new_stocks:
            print("새로 추가할 주식이 없습니다.")
            return 0
        
        print(f"새로 추가할 주식: {len(new_stocks)}개")
        
        # INSERT 쿼리 실행
        insert_query = """
        INSERT INTO stocks (stock_code, stock_name, market_type, created_at, updated_at) 
        VALUES (%s, %s, %s, NOW(), NOW())
        """
        
        inserted_count = 0
        for stock in new_stocks:
            try:
                cursor.execute(insert_query, (
                    stock['stock_code'],
                    stock['stock_name'],
                    stock['market_type']
                ))
                inserted_count += 1
                
                if inserted_count % 100 == 0:
                    print(f"진행률: {inserted_count}/{len(new_stocks)}")
                    
            except Error as e:
                print(f"주식 {stock['stock_code']} 삽입 오류: {e}")
                continue
        
        # 변경사항 커밋
        connection.commit()
        cursor.close()
        
        print(f"성공적으로 {inserted_count}개의 새로운 주식을 추가했습니다.")
        return inserted_count
        
    except Error as e:
        print(f"주식 삽입 오류: {e}")
        connection.rollback()
        return 0

def update_existing_stocks(connection, stocks_data, existing_codes):
    """기존 주식 정보 업데이트 (이름이나 시장 구분이 변경된 경우)"""
    try:
        cursor = connection.cursor()
        
        # 기존 주식 정보를 배치로 조회 (IN 절의 파라미터 제한 문제 해결)
        batch_size = 1000
        existing_stocks = {}
        
        for i in range(0, len(existing_codes), batch_size):
            batch_codes = list(existing_codes)[i:i + batch_size]
            placeholders = ','.join(['%s'] * len(batch_codes))
            
            cursor.execute(f"SELECT stock_code, stock_name, market_type FROM stocks WHERE stock_code IN ({placeholders})", batch_codes)
            batch_results = cursor.fetchall()
            
            for row in batch_results:
                existing_stocks[row[0]] = {'stock_name': row[1], 'market_type': row[2]}
        
        # 업데이트가 필요한 주식 찾기
        stocks_to_update = []
        for stock in stocks_data:
            if stock['stock_code'] in existing_codes:
                existing = existing_stocks[stock['stock_code']]
                if (existing['stock_name'] != stock['stock_name'] or 
                    existing['market_type'] != stock['market_type']):
                    stocks_to_update.append(stock)
        
        if not stocks_to_update:
            print("업데이트할 주식이 없습니다.")
            return 0
        
        print(f"업데이트할 주식: {len(stocks_to_update)}개")
        
        # UPDATE 쿼리 실행
        update_query = """
        UPDATE stocks 
        SET stock_name = %s, market_type = %s, updated_at = NOW() 
        WHERE stock_code = %s
        """
        
        updated_count = 0
        for stock in stocks_to_update:
            try:
                cursor.execute(update_query, (
                    stock['stock_name'],
                    stock['market_type'],
                    stock['stock_code']
                ))
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"업데이트 진행률: {updated_count}/{len(stocks_to_update)}")
                    
            except Error as e:
                print(f"주식 {stock['stock_code']} 업데이트 오류: {e}")
                continue
        
        # 변경사항 커밋
        connection.commit()
        cursor.close()
        
        print(f"성공적으로 {updated_count}개의 주식을 업데이트했습니다.")
        return updated_count
        
    except Error as e:
        print(f"주식 업데이트 오류: {e}")
        connection.rollback()
        return 0

def main():
    """메인 함수"""
    json_file_path = "etc/stocks_data.json"
    
    print("=== stocks_data.json을 DB에 업데이트 시작 ===")
    
    # JSON 파일 로드
    stocks_data = load_stocks_data(json_file_path)
    if not stocks_data:
        print("JSON 파일 로드 실패. 프로그램을 종료합니다.")
        return
    
    # 데이터베이스 연결
    connection = connect_to_database()
    if not connection:
        print("데이터베이스 연결 실패. 프로그램을 종료합니다.")
        return
    
    try:
        # 기존 주식 코드 조회
        existing_codes = get_existing_stocks(connection)
        
        # 새로운 주식 추가
        inserted_count = insert_new_stocks(connection, stocks_data, existing_codes)
        
        # 기존 주식 업데이트
        updated_count = update_existing_stocks(connection, stocks_data, existing_codes)
        
        print(f"\n=== 업데이트 완료 ===")
        print(f"새로 추가된 주식: {inserted_count}개")
        print(f"업데이트된 주식: {updated_count}개")
        print(f"총 처리된 주식: {inserted_count + updated_count}개")
        
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")
    
    finally:
        if connection.is_connected():
            connection.close()
            print("데이터베이스 연결이 종료되었습니다.")

if __name__ == "__main__":
    main()
