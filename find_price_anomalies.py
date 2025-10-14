#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB에서 직접 10월 1일, 2일 데이터 이상 패턴 찾기
"""

from database_config import DatabaseManager
import pandas as pd

def find_price_anomalies():
    """DB에서 직접 이상 패턴 찾기"""
    
    db = DatabaseManager()
    
    if not db.connect():
        print("DB 연결 실패")
        return
    
    print("="*80)
    print("10월 1일, 2일 데이터 이상 패턴 분석")
    print("="*80)
    
    try:
        # 1. 10월 1일, 2일 종가가 평소(9월 평균)보다 2배 이상 높은 종목
        print("\n[1] 10월 1일, 2일 종가가 9월 평균보다 2배 이상 높은 종목")
        print("-"*80)
        
        query1 = """
            SELECT 
                d.stock_code,
                s.stock_name,
                d.trade_date,
                d.close as oct_close,
                AVG(d_prev.close) as sep_avg_close,
                d.close / AVG(d_prev.close) as price_ratio,
                ((d.close - AVG(d_prev.close)) / AVG(d_prev.close)) * 100 as increase_percent
            FROM daily_data d
            JOIN stocks s ON d.stock_code = s.stock_code
            LEFT JOIN daily_data d_prev 
                ON d.stock_code = d_prev.stock_code 
                AND d_prev.trade_date >= '2025-09-01' 
                AND d_prev.trade_date < '2025-10-01'
            WHERE d.trade_date IN ('2025-10-01', '2025-10-02')
            GROUP BY d.stock_code, s.stock_name, d.trade_date, d.close
            HAVING d.close / AVG(d_prev.close) > 2.0
            ORDER BY price_ratio DESC
            LIMIT 50
        """
        
        result1 = db.fetch_all(query1)
        if result1:
            df1 = pd.DataFrame(result1)
            print(f"발견된 종목 수: {len(df1)}")
            print("\n상위 10개:")
            print(df1.head(10).to_string(index=False))
            
            # CSV 저장
            df1.to_csv('anomalies_2x_increase.csv', index=False, encoding='utf-8-sig')
            print(f"\n전체 결과가 'anomalies_2x_increase.csv' 파일로 저장되었습니다.")
        else:
            print("발견된 종목 없음")
        
        # 2. 10월 1일, 2일 종가가 50,000원 이상인 종목 중 평소보다 높은 종목
        print("\n\n[2] 10월 1일, 2일 종가가 50,000원 이상이면서 9월 평균보다 1.5배 이상 높은 종목")
        print("-"*80)
        
        query2 = """
            SELECT 
                d.stock_code,
                s.stock_name,
                d.trade_date,
                d.close as oct_close,
                AVG(d_prev.close) as sep_avg_close,
                d.close / AVG(d_prev.close) as price_ratio
            FROM daily_data d
            JOIN stocks s ON d.stock_code = s.stock_code
            LEFT JOIN daily_data d_prev 
                ON d.stock_code = d_prev.stock_code 
                AND d_prev.trade_date >= '2025-09-01' 
                AND d_prev.trade_date < '2025-10-01'
            WHERE d.trade_date IN ('2025-10-01', '2025-10-02')
                AND d.close > 50000
            GROUP BY d.stock_code, s.stock_name, d.trade_date, d.close
            HAVING d.close / AVG(d_prev.close) > 1.5
            ORDER BY d.close DESC
            LIMIT 50
        """
        
        result2 = db.fetch_all(query2)
        if result2:
            df2 = pd.DataFrame(result2)
            print(f"발견된 종목 수: {len(df2)}")
            print("\n상위 10개:")
            print(df2.head(10).to_string(index=False))
            
            # CSV 저장
            df2.to_csv('anomalies_50k_high.csv', index=False, encoding='utf-8-sig')
            print(f"\n전체 결과가 'anomalies_50k_high.csv' 파일로 저장되었습니다.")
        else:
            print("발견된 종목 없음")
        
        # 3. 10월 1일, 2일 종가가 100,000원 이상인 종목
        print("\n\n[3] 10월 1일, 2일 종가가 100,000원 이상인 종목")
        print("-"*80)
        
        query3 = """
            SELECT 
                d.stock_code,
                s.stock_name,
                d.trade_date,
                d.close,
                d.high,
                d.low,
                d.volume
            FROM daily_data d
            JOIN stocks s ON d.stock_code = s.stock_code
            WHERE d.trade_date IN ('2025-10-01', '2025-10-02')
                AND d.close > 100000
            ORDER BY d.close DESC
        """
        
        result3 = db.fetch_all(query3)
        if result3:
            df3 = pd.DataFrame(result3)
            print(f"발견된 종목 수: {len(df3)}")
            print("\n전체 목록:")
            print(df3.to_string(index=False))
            
            # CSV 저장
            df3.to_csv('anomalies_100k_above.csv', index=False, encoding='utf-8-sig')
            print(f"\n전체 결과가 'anomalies_100k_above.csv' 파일로 저장되었습니다.")
        else:
            print("발견된 종목 없음")
        
        print("\n" + "="*80)
        print("분석 완료!")
        print("="*80)
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_price_anomalies()

