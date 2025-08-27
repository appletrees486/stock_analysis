#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종목번호 064260의 8월 20일 보조지표 수정
NULL로 되어 있는 보조지표를 다시 계산하고 DB에 업데이트
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import DatabaseManager

def get_stock_data_for_calculation(stock_code, days=240):
    """주식 데이터 조회 (보조지표 계산용) - DB에서 가져오기"""
    try:
        # 데이터베이스 연결
        db = DatabaseManager()
        if not db.connect():
            print("❌ 데이터베이스 연결 실패")
            return None
        
        # 해당 종목의 최신 거래일을 조회
        latest_date_query = "SELECT MAX(trade_date) as latest_date FROM daily_data WHERE stock_code = %s"
        latest_date_result = db.fetch_one(latest_date_query, (stock_code,))
        
        if latest_date_result and latest_date_result['latest_date']:
            end_date = latest_date_result['latest_date']
            start_date = end_date - timedelta(days=days)
            print(f"   📅 DB 최신 거래일: {end_date}")
            print(f"   📅 조회 시작일: {start_date}")
        else:
            print("❌ 해당 종목의 일봉 데이터를 찾을 수 없습니다.")
            db.disconnect()
            return None
        
        # daily_data 테이블에서 일봉 데이터 조회
        query = """
        SELECT trade_date, open, high, low, close, volume
        FROM daily_data 
        WHERE stock_code = %s 
        AND trade_date >= %s 
        AND trade_date <= %s
        ORDER BY trade_date ASC
        """
        
        params = (stock_code, start_date, end_date)
        daily_data = db.fetch_all(query, params)
        
        if daily_data:
            print(f"✅ DB 일봉 데이터 조회 성공: {len(daily_data)}일")
            
            # 데이터프레임으로 변환
            df = pd.DataFrame(daily_data)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            
            # 컬럼명을 Yahoo Finance 형식과 맞춤
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            db.disconnect()
            return df
        else:
            print(f"❌ 일봉 데이터 조회 실패: DB에 데이터가 없습니다")
            db.disconnect()
            return None
            
    except Exception as e:
        print(f"❌ DB 일봉 데이터 조회 실패: {str(e)}")
        try:
            db.disconnect()
        except:
            pass
        return None

def calculate_indicators_from_scratch(df):
    """처음부터 보조지표 계산"""
    print("   🔄 보조지표를 계산합니다...")
    
    # 이동평균선
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    # 볼린저 밴드 계산 (20일 기준)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # MACD 계산 (표준 공식)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
    
    # RSI 계산 (표준 공식)
    delta = df['Close'].diff()
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    loss = abs(loss)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def update_specific_date_indicators(stock_code, target_date, indicators_df):
    """특정 날짜의 보조지표만 업데이트"""
    try:
        db = DatabaseManager()
        if not db.connect():
            return False
        
        print(f"   🔄 {target_date} 보조지표 업데이트 중...")
        
        # 해당 날짜의 데이터만 추출 (날짜 형식 맞춤)
        target_date_str = target_date.strftime('%Y-%m-%d')
        if target_date_str in indicators_df.index.strftime('%Y-%m-%d').values:
            # 해당 날짜의 인덱스 찾기
            date_mask = indicators_df.index.strftime('%Y-%m-%d') == target_date_str
            row = indicators_df[date_mask].iloc[0]
            
            # 업데이트 쿼리
            update_query = """
            UPDATE technical_indicators 
            SET ma5 = %s, ma20 = %s, ma60 = %s, ma120 = %s,
                rsi = %s, bb_upper = %s, bb_middle = %s, bb_lower = %s,
                updated_at = NOW()
            WHERE stock_code = %s AND trade_date = %s
            """
            
            params = (
                float(row['MA5']) if pd.notna(row['MA5']) else None,
                float(row['MA20']) if pd.notna(row['MA20']) else None,
                float(row['MA60']) if pd.notna(row['MA60']) else None,
                float(row['MA120']) if pd.notna(row['MA120']) else None,
                float(row['RSI']) if pd.notna(row['RSI']) else None,
                float(row['BB_Upper']) if pd.notna(row['BB_Upper']) else None,
                float(row['BB_Middle']) if pd.notna(row['BB_Middle']) else None,
                float(row['BB_Lower']) if pd.notna(row['BB_Lower']) else None,
                stock_code,
                target_date.date()
            )
            
            success = db.execute_query(update_query, params)
            if success:
                db.commit()
                print(f"   ✅ {target_date} 보조지표 업데이트 완료")
                
                # 업데이트된 값 출력
                print(f"      MA5: {row['MA5']:.2f}")
                print(f"      MA20: {row['MA20']:.2f}")
                print(f"      MA60: {row['MA60']:.2f}")
                print(f"      MA120: {row['MA120']:.2f}")
                print(f"      RSI: {row['RSI']:.2f}")
                print(f"      BB Upper: {row['BB_Upper']:.2f}")
                print(f"      BB Middle: {row['BB_Middle']:.2f}")
                print(f"      BB Lower: {row['BB_Lower']:.2f}")
                
                return True
            else:
                print(f"   ❌ {target_date} 업데이트 실패")
                return False
        else:
            print(f"   ❌ {target_date} 데이터를 찾을 수 없습니다.")
            return False
        
    except Exception as e:
        print(f"   ❌ 업데이트 오류: {e}")
        return False
    finally:
        try:
            db.disconnect()
        except:
            pass

def main():
    """메인 함수"""
    print("🔧 종목번호 064260 8월 20일 보조지표 수정")
    print("=" * 60)
    
    stock_code = "064260"
    target_date = datetime(2025, 8, 20)
    
    print(f"📈 종목코드: {stock_code}")
    print(f"📅 대상 날짜: {target_date.strftime('%Y-%m-%d')}")
    
    # 1. 주식 데이터 조회
    print("\n1️⃣ 주식 데이터 조회 중...")
    hist = get_stock_data_for_calculation(stock_code)
    
    if hist is None:
        print("❌ 데이터 조회 실패")
        return
    
    # 2. 보조지표 계산
    print("\n2️⃣ 보조지표 계산 중...")
    indicators_df = calculate_indicators_from_scratch(hist.copy())
    
    # 3. 특정 날짜 업데이트
    print("\n3️⃣ DB 업데이트 중...")
    success = update_specific_date_indicators(stock_code, target_date, indicators_df)
    
    if success:
        print(f"\n✅ {stock_code} {target_date.strftime('%Y-%m-%d')} 보조지표 수정 완료!")
        print("이제 다시 확인해보세요.")
    else:
        print(f"\n❌ 보조지표 수정에 실패했습니다.")

if __name__ == "__main__":
    main()
