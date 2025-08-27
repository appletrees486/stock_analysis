#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터 변경 이력 추적 및 감사 로그 시스템
주식 데이터의 모든 변경사항을 추적하고 감사 로그를 생성
"""

import json
import hashlib
from datetime import datetime, timedelta
from database_config import DatabaseManager
import logging
from typing import Dict, List, Any, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_change_tracker.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DataChangeTracker:
    def __init__(self):
        """데이터 변경 추적기 초기화"""
        self.db = DatabaseManager()
        self._ensure_tracking_tables()
        logging.info("✅ 데이터 변경 추적기 초기화 완료")
    
    def _ensure_tracking_tables(self):
        """추적 테이블들이 존재하는지 확인하고 없으면 생성"""
        try:
            if not self.db.connect():
                logging.error("❌ 데이터베이스 연결 실패")
                return False
            
            # 데이터 변경 이력 테이블
            change_history_table = """
            CREATE TABLE IF NOT EXISTS data_change_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                table_name VARCHAR(100) NOT NULL,
                record_id VARCHAR(100) NOT NULL,
                change_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
                old_values JSON,
                new_values JSON,
                changed_fields JSON,
                change_reason VARCHAR(500),
                user_id VARCHAR(100),
                ip_address VARCHAR(45),
                change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_table_record (table_name, record_id),
                INDEX idx_change_type (change_type),
                INDEX idx_timestamp (change_timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            # 데이터 무결성 검증 테이블
            data_integrity_log = """
            CREATE TABLE IF NOT EXISTS data_integrity_log (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                table_name VARCHAR(100) NOT NULL,
                check_type ENUM('STRUCTURE', 'CONTENT', 'RELATIONSHIP') NOT NULL,
                check_result ENUM('PASS', 'FAIL', 'WARNING') NOT NULL,
                error_message TEXT,
                affected_records INT,
                check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_table_type (table_name, check_type),
                INDEX idx_result (check_result),
                INDEX idx_timestamp (check_timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            # 데이터 백업 이력 테이블
            backup_history = """
            CREATE TABLE IF NOT EXISTS backup_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                backup_type ENUM('FULL', 'INCREMENTAL', 'DIFFERENTIAL') NOT NULL,
                backup_name VARCHAR(200) NOT NULL,
                backup_path VARCHAR(500) NOT NULL,
                backup_size BIGINT,
                table_count INT,
                record_count BIGINT,
                backup_status ENUM('SUCCESS', 'FAILED', 'IN_PROGRESS') NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_backup_type (backup_type),
                INDEX idx_status (backup_status),
                INDEX idx_start_time (start_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            tables = [
                ("data_change_history", change_history_table),
                ("data_integrity_log", data_integrity_log),
                ("backup_history", backup_history)
            ]
            
            for table_name, table_sql in tables:
                if self.db.execute_query(table_sql):
                    logging.info(f"✅ {table_name} 테이블 확인/생성 완료")
                else:
                    logging.error(f"❌ {table_name} 테이블 생성 실패")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ 추적 테이블 확인/생성 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def track_insert(self, table_name: str, record_id: str, new_values: Dict[str, Any], 
                    change_reason: str = None, user_id: str = None, ip_address: str = None):
        """INSERT 작업 추적"""
        try:
            if not self.db.connect():
                return False
            
            insert_sql = """
            INSERT INTO data_change_history 
            (table_name, record_id, change_type, new_values, change_reason, user_id, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                table_name,
                record_id,
                'INSERT',
                json.dumps(new_values, ensure_ascii=False, default=str),
                change_reason,
                user_id,
                ip_address
            )
            
            if self.db.execute_query(insert_sql, params):
                logging.info(f"✅ INSERT 추적 완료: {table_name}.{record_id}")
                return True
            else:
                logging.error(f"❌ INSERT 추적 실패: {table_name}.{record_id}")
                return False
                
        except Exception as e:
            logging.error(f"❌ INSERT 추적 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def track_update(self, table_name: str, record_id: str, old_values: Dict[str, Any], 
                    new_values: Dict[str, Any], change_reason: str = None, 
                    user_id: str = None, ip_address: str = None):
        """UPDATE 작업 추적"""
        try:
            if not self.db.connect():
                return False
            
            # 변경된 필드 식별
            changed_fields = {}
            for key in new_values:
                if key in old_values and old_values[key] != new_values[key]:
                    changed_fields[key] = {
                        'old': old_values[key],
                        'new': new_values[key]
                    }
            
            if not changed_fields:
                logging.info(f"ℹ️ 변경된 필드가 없음: {table_name}.{record_id}")
                return True
            
            insert_sql = """
            INSERT INTO data_change_history 
            (table_name, record_id, change_type, old_values, new_values, changed_fields, 
             change_reason, user_id, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                table_name,
                record_id,
                'UPDATE',
                json.dumps(old_values, ensure_ascii=False, default=str),
                json.dumps(new_values, ensure_ascii=False, default=str),
                json.dumps(changed_fields, ensure_ascii=False, default=str),
                change_reason,
                user_id,
                ip_address
            )
            
            if self.db.execute_query(insert_sql, params):
                logging.info(f"✅ UPDATE 추적 완료: {table_name}.{record_id} ({len(changed_fields)}개 필드)")
                return True
            else:
                logging.error(f"❌ UPDATE 추적 실패: {table_name}.{record_id}")
                return False
                
        except Exception as e:
            logging.error(f"❌ UPDATE 추적 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def track_delete(self, table_name: str, record_id: str, old_values: Dict[str, Any], 
                    change_reason: str = None, user_id: str = None, ip_address: str = None):
        """DELETE 작업 추적"""
        try:
            if not self.db.connect():
                return False
            
            insert_sql = """
            INSERT INTO data_change_history 
            (table_name, record_id, change_type, old_values, change_reason, user_id, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                table_name,
                record_id,
                'DELETE',
                json.dumps(old_values, ensure_ascii=False, default=str),
                change_reason,
                user_id,
                ip_address
            )
            
            if self.db.execute_query(insert_sql, params):
                logging.info(f"✅ DELETE 추적 완료: {table_name}.{record_id}")
                return True
            else:
                logging.error(f"❌ DELETE 추적 실패: {table_name}.{record_id}")
                return False
                
        except Exception as e:
            logging.error(f"❌ DELETE 추적 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def get_change_history(self, table_name: str = None, record_id: str = None, 
                          change_type: str = None, start_date: datetime = None, 
                          end_date: datetime = None, limit: int = 100):
        """변경 이력 조회"""
        try:
            if not self.db.connect():
                return []
            
            where_conditions = []
            params = []
            
            if table_name:
                where_conditions.append("table_name = %s")
                params.append(table_name)
            
            if record_id:
                where_conditions.append("record_id = %s")
                params.append(record_id)
            
            if change_type:
                where_conditions.append("change_type = %s")
                params.append(change_type)
            
            if start_date:
                where_conditions.append("change_timestamp >= %s")
                params.append(start_date)
            
            if end_date:
                where_conditions.append("change_timestamp <= %s")
                params.append(end_date)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            query = f"""
            SELECT * FROM data_change_history 
            WHERE {where_clause}
            ORDER BY change_timestamp DESC
            LIMIT %s
            """
            params.append(limit)
            
            result = self.db.fetch_all(query, params)
            
            # JSON 필드 파싱
            for row in result:
                if row.get('old_values'):
                    row['old_values'] = json.loads(row['old_values'])
                if row.get('new_values'):
                    row['new_values'] = json.loads(row['new_values'])
                if row.get('changed_fields'):
                    row['changed_fields'] = json.loads(row['changed_fields'])
            
            return result
            
        except Exception as e:
            logging.error(f"❌ 변경 이력 조회 중 오류: {e}")
            return []
        finally:
            self.db.disconnect()
    
    def log_data_integrity_check(self, table_name: str, check_type: str, check_result: str, 
                                error_message: str = None, affected_records: int = 0):
        """데이터 무결성 검증 결과 로깅"""
        try:
            if not self.db.connect():
                return False
            
            insert_sql = """
            INSERT INTO data_integrity_log 
            (table_name, check_type, check_result, error_message, affected_records)
            VALUES (%s, %s, %s, %s, %s)
            """
            
            params = (table_name, check_type, check_result, error_message, affected_records)
            
            if self.db.execute_query(insert_sql, params):
                logging.info(f"✅ 무결성 검증 로그 저장 완료: {table_name}.{check_type}")
                return True
            else:
                logging.error(f"❌ 무결성 검증 로그 저장 실패: {table_name}.{check_type}")
                return False
                
        except Exception as e:
            logging.error(f"❌ 무결성 검증 로그 저장 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def log_backup_operation(self, backup_type: str, backup_name: str, backup_path: str,
                           backup_size: int = None, table_count: int = None, 
                           record_count: int = None, backup_status: str = 'IN_PROGRESS'):
        """백업 작업 로깅"""
        try:
            if not self.db.connect():
                return False
            
            insert_sql = """
            INSERT INTO backup_history 
            (backup_type, backup_name, backup_path, backup_size, table_count, 
             record_count, backup_status, start_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                backup_type, backup_name, backup_path, backup_size,
                table_count, record_count, backup_status, datetime.now()
            )
            
            if self.db.execute_query(insert_sql, params):
                backup_id = self.db.cursor.lastrowid
                logging.info(f"✅ 백업 작업 로그 저장 완료: {backup_name} (ID: {backup_id})")
                return backup_id
            else:
                logging.error(f"❌ 백업 작업 로그 저장 실패: {backup_name}")
                return None
                
        except Exception as e:
            logging.error(f"❌ 백업 작업 로그 저장 중 오류: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def update_backup_status(self, backup_id: int, backup_status: str, 
                           end_time: datetime = None, error_message: str = None):
        """백업 상태 업데이트"""
        try:
            if not self.db.connect():
                return False
            
            update_sql = """
            UPDATE backup_history 
            SET backup_status = %s, end_time = %s, error_message = %s
            WHERE id = %s
            """
            
            params = (backup_status, end_time, error_message, backup_id)
            
            if self.db.execute_query(update_sql, params):
                logging.info(f"✅ 백업 상태 업데이트 완료: ID {backup_id} -> {backup_status}")
                return True
            else:
                logging.error(f"❌ 백업 상태 업데이트 실패: ID {backup_id}")
                return False
                
        except Exception as e:
            logging.error(f"❌ 백업 상태 업데이트 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def get_data_integrity_summary(self, days: int = 30):
        """데이터 무결성 검증 결과 요약"""
        try:
            if not self.db.connect():
                return {}
            
            query = """
            SELECT 
                check_type,
                check_result,
                COUNT(*) as count
            FROM data_integrity_log 
            WHERE check_timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY check_type, check_result
            ORDER BY check_type, check_result
            """
            
            result = self.db.fetch_all(query, (days,))
            
            summary = {}
            for row in result:
                check_type = row['check_type']
                check_result = row['check_result']
                count = row['count']
                
                if check_type not in summary:
                    summary[check_type] = {}
                
                summary[check_type][check_result] = count
            
            return summary
            
        except Exception as e:
            logging.error(f"❌ 무결성 검증 요약 조회 중 오류: {e}")
            return {}
        finally:
            self.db.disconnect()
    
    def cleanup_old_logs(self, days: int = 90):
        """오래된 로그 정리"""
        try:
            if not self.db.connect():
                return False
            
            # 변경 이력 정리
            change_history_cleanup = """
            DELETE FROM data_change_history 
            WHERE change_timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
            """
            
            # 무결성 검증 로그 정리
            integrity_log_cleanup = """
            DELETE FROM data_integrity_log 
            WHERE check_timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
            """
            
            # 백업 이력 정리 (1년 이상)
            backup_history_cleanup = """
            DELETE FROM backup_history 
            WHERE created_at < DATE_SUB(NOW(), INTERVAL 365 DAY)
            """
            
            cleanup_queries = [
                ("변경 이력", change_history_cleanup, days),
                ("무결성 검증 로그", integrity_log_cleanup, days),
                ("백업 이력", backup_history_cleanup, 365)
            ]
            
            total_deleted = 0
            for name, query, param in cleanup_queries:
                if self.db.execute_query(query, (param,)):
                    deleted_count = self.db.cursor.rowcount
                    total_deleted += deleted_count
                    logging.info(f"✅ {name} 정리 완료: {deleted_count}개 레코드 삭제")
                else:
                    logging.error(f"❌ {name} 정리 실패")
            
            logging.info(f"✅ 로그 정리 완료: 총 {total_deleted}개 레코드 삭제")
            return True
            
        except Exception as e:
            logging.error(f"❌ 로그 정리 중 오류: {e}")
            return False
        finally:
            self.db.disconnect()

def main():
    """테스트 함수"""
    print("🚀 데이터 변경 추적기 테스트")
    print("="*50)
    
    tracker = DataChangeTracker()
    
    # 테스트 데이터 변경 추적
    print("📊 테스트 데이터 변경 추적...")
    
    # INSERT 추적 테스트
    test_new_values = {
        'stock_code': '005930',
        'stock_name': '삼성전자',
        'price': 71000,
        'volume': 1000000
    }
    
    if tracker.track_insert('stocks', '005930', test_new_values, 
                           change_reason='테스트 데이터 삽입', user_id='test_user'):
        print("✅ INSERT 추적 테스트 성공")
    
    # UPDATE 추적 테스트
    old_values = test_new_values.copy()
    new_values = old_values.copy()
    new_values['price'] = 72000
    
    if tracker.track_update('stocks', '005930', old_values, new_values,
                           change_reason='가격 업데이트', user_id='test_user'):
        print("✅ UPDATE 추적 테스트 성공")
    
    # DELETE 추적 테스트
    if tracker.track_delete('stocks', '005930', old_values,
                           change_reason='테스트 데이터 삭제', user_id='test_user'):
        print("✅ DELETE 추적 테스트 성공")
    
    # 변경 이력 조회 테스트
    print("\n📋 최근 변경 이력 조회...")
    recent_changes = tracker.get_change_history(limit=10)
    print(f"   총 {len(recent_changes)}개의 변경 이력 발견")
    
    for change in recent_changes[:3]:  # 처음 3개만 출력
        print(f"   {change['change_timestamp']}: {change['table_name']}.{change['record_id']} "
              f"({change['change_type']}) - {change['change_reason']}")
    
    # 무결성 검증 로그 테스트
    print("\n🔍 데이터 무결성 검증 로그 테스트...")
    if tracker.log_data_integrity_check('stocks', 'STRUCTURE', 'PASS', affected_records=100):
        print("✅ 무결성 검증 로그 테스트 성공")
    
    # 백업 작업 로그 테스트
    print("\n💾 백업 작업 로그 테스트...")
    backup_id = tracker.log_backup_operation('FULL', 'test_backup_001', '/backup/test.db')
    if backup_id:
        print(f"✅ 백업 작업 로그 테스트 성공 (ID: {backup_id})")
        tracker.update_backup_status(backup_id, 'SUCCESS', datetime.now())
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    main()
