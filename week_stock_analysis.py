#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국내 주식 주봉 시세 조회 스크립트 (DB 기반)
"""

# matplotlib 백엔드를 Agg로 설정 (tkinter 에러 방지)
import matplotlib
matplotlib.use('Agg')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import mplfinance as mpf
import platform
import os
# openpyxl import 추가
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
import json
# 데이터베이스 연결을 위한 import 추가
from database_config import DatabaseManager
# 한국 공휴일 관리자 import 추가
from korean_holiday_manager import KoreanHolidayManager

# 운영체제별 한글 폰트 설정
system = platform.system()
if system == 'Windows':
    # Windows 환경
    font_list = ['Malgun Gothic', '맑은 고딕', 'NanumGothic', '나눔고딕']
elif system == 'Darwin':  # macOS
    font_list = ['AppleGothic', 'NanumGothic', '나눔고딕']
else:  # Linux
    font_list = ['NanumGothic', '나눔고딕', 'DejaVu Sans']

# 사용 가능한 폰트 찾기
available_font = None
for font in font_list:
    try:
        fm.findfont(font)
        available_font = font
        break
    except:
        continue

if available_font:
    plt.rcParams['font.family'] = available_font
    print(f"✅ 사용 폰트: {available_font}")
else:
    # 기본 폰트 사용
    plt.rcParams['font.family'] = 'DejaVu Sans'
    print("⚠️ 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")

plt.rcParams['axes.unicode_minus'] = False

# 폰트 캐시 재설정
try:
    fm._rebuild()
except AttributeError:
    # 최신 matplotlib 버전에서는 _rebuild가 제거됨
    fm.findfont('DejaVu Sans', rebuild_if_missing=True)

def get_weekly_stock_data(stock_code):
    """국내 주식 주봉 데이터 조회 (5년) - DB daily_data에서 조회하여 주봉 변환"""
    print(f"🔍 {stock_code} 5년 주봉 시세 조회 중...")
    print("   📅 주봉 데이터는 거래일 기준으로 제공되며, 주말/공휴일은 포함되지 않습니다.")
    
    try:
        # 데이터베이스 연결
        print("   🔄 데이터베이스에서 일봉 데이터 조회 중...")
        db = DatabaseManager()
        
        if not db.connect():
            print("   ❌ 데이터베이스 연결 실패")
            return None
        
        # 5년(260주) 전 날짜 계산 - 실제 최신 거래일 기준으로 설정
        # 먼저 해당 종목의 최신 거래일을 조회
        latest_date_query = "SELECT MAX(trade_date) as latest_date FROM daily_data WHERE stock_code = %s"
        latest_date_result = db.fetch_one(latest_date_query, (stock_code,))
        
        if latest_date_result and latest_date_result['latest_date']:
            end_date = latest_date_result['latest_date']
            start_date = end_date - timedelta(days=260*7)  # 5년 = 260주 * 7일
            print(f"   📅 DB 최신 거래일: {end_date}")
            print(f"   📅 조회 시작일: {start_date}")
        else:
            # 최신 거래일이 없으면 현재 날짜 기준으로 설정
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=260*7)
            print(f"   ⚠️ 최신 거래일을 찾을 수 없어 현재 날짜 기준으로 설정")
            print(f"   📅 현재 날짜: {end_date}")
            print(f"   📅 조회 시작일: {start_date}")
        
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
            print(f"✅ DB 일봉 데이터 조회 성공: {len(daily_data)}일의 일봉 거래 데이터를 가져왔습니다.")
            
            # 종목명 조회
            stock_name_query = "SELECT stock_name FROM stocks WHERE stock_code = %s"
            stock_info = db.fetch_one(stock_name_query, (stock_code,))
            stock_name = stock_info['stock_name'] if stock_info else stock_code
            print(f"🏢 종목명: {stock_name}")
            
            # 데이터프레임으로 변환
            df = pd.DataFrame(daily_data)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            
            # 컬럼명을 Yahoo Finance 형식과 맞춤
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            # Decimal 타입을 float로 변환 (pandas 연산 호환성을 위해)
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = df[col].astype(float)
            
            # 디버깅: 데이터 기간 확인
            print(f"🔍 데이터 기간 디버깅:")
            print(f"   요청 기간: 5년 (260주)")
            print(f"   실제 시작일: {df.index[0].strftime('%Y-%m-%d')}")
            print(f"   실제 종료일: {df.index[-1].strftime('%Y-%m-%d')}")
            print(f"   실제 데이터 수: {len(df)}일")
            
            # 최신 데이터 신뢰성 검증
            holiday_manager = KoreanHolidayManager()
            latest_date = df.index[-1]
            is_reliable, reliability_reason = validate_weekly_data_reliability(stock_code, latest_date, holiday_manager)
            
            if not is_reliable:
                print(f"   ⚠️ 주봉 데이터 신뢰성 문제: {reliability_reason}")
                print(f"   💡 보다 정확한 주봉 분석을 위해 장마감 후 재실행을 권장합니다.")
            else:
                print(f"   ✅ 주봉 데이터 신뢰성 확인: {reliability_reason}")
            
            # 일봉을 주봉으로 변환
            weekly_data = convert_daily_to_weekly(df, stock_code)
            
            if weekly_data is not None:
                # ✅ 주봉 데이터에 보조지표 계산 추가
                weekly_data_with_indicators = calculate_technical_indicators(weekly_data.copy())
                
                # 주봉 데이터를 weekly_data 테이블에 저장 (보조지표 포함)
                save_weekly_data_to_db(db, stock_code, weekly_data_with_indicators)
                print(f"✅ 주봉 데이터(보조지표 포함)를 weekly_data 테이블에 저장했습니다.")
            
            db.disconnect()
            return weekly_data_with_indicators  # ✅ 보조지표가 포함된 데이터 반환
        else:
            print(f"   ❌ 일봉 데이터 조회 실패: DB에 데이터가 없습니다")
            print(f"   💡 {stock_code} 종목의 일봉 데이터를 먼저 수집해주세요.")
            db.disconnect()
            return None
            
    except Exception as e:
        print(f"   ❌ DB 일봉 데이터 조회 실패: {str(e)}")
        try:
            db.disconnect()
        except:
            pass
        return None

def convert_daily_to_weekly(daily_data, stock_code):
    """일봉 데이터를 주봉으로 변환 (5년 = 260주) - 한국 공휴일 및 장마감 시간 고려"""
    try:
        print(f"   🔄 일봉 데이터를 주봉으로 변환 중...")
        
        # 한국 공휴일 관리자 초기화
        holiday_manager = KoreanHolidayManager()
        
        # 현재 시간 및 장 상태 확인
        current_time = datetime.now()
        market_status = holiday_manager.get_market_status(current_time)
        market_status_desc = holiday_manager.get_market_status_description(market_status)
        
        print(f"   📅 현재 시간: {current_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   🏢 장 상태: {market_status_desc}")
        
        # 장중이거나 거래일이 아닌 경우 경고
        if market_status in ["during_market", "near_market_close"]:
            print(f"   ⚠️ 현재 장중입니다. 주봉 데이터가 완전하지 않을 수 있습니다.")
            print(f"   💡 정확한 주봉 데이터를 위해서는 장마감 후(15:30 이후) 분석을 권장합니다.")
        elif market_status == "non_trading_day":
            print(f"   📅 오늘은 거래일이 아닙니다. 이전 거래일까지의 데이터로 주봉을 생성합니다.")
        
        # 일봉 데이터를 주별로 그룹화 (실제 거래일 기준)
        daily_data_copy = daily_data.copy()
        daily_data_copy.index.name = 'Date'
        
        # 날짜를 정렬
        daily_data_copy = daily_data_copy.sort_index()
        
        # 실제 거래일 기준 주봉 그룹화
        weekly_data = []
        current_week_data = []
        current_week_start = None
        
        for date, row in daily_data_copy.iterrows():
            # 날짜를 date 객체로 변환
            if hasattr(date, 'date'):
                trade_date = date.date()
            else:
                trade_date = date
            
            # 거래일 확인 (이미 daily_data에는 거래일만 있지만 추가 검증)
            if not holiday_manager.is_trading_day(trade_date):
                print(f"   ⚠️ {trade_date}는 거래일이 아닙니다. 건너뜁니다.")
                continue
            
            # 주의 시작일 결정
            if current_week_start is None:
                current_week_start = date
                print(f"   📅 첫 번째 주 시작: {current_week_start.strftime('%Y-%m-%d')}")
            
            # 현재 주에 데이터 추가
            current_week_data.append({
                'date': date,
                'trade_date': trade_date,
                'open': row['Open'],
                'high': row['High'],
                'low': row['Low'],
                'close': row['Close'],
                'volume': row['Volume']
            })
            
            # 주의 마지막 거래일인지 확인
            # 다음 거래일이 다음 주에 속하는지 확인
            next_date = daily_data_copy.index[daily_data_copy.index.get_loc(date) + 1] if daily_data_copy.index.get_loc(date) + 1 < len(daily_data_copy) else None
            
            if next_date is None or _is_new_trading_week(current_week_start, next_date, holiday_manager):
                # ✅ 완성된 주인지 확인 - 미완성 주는 제외
                if current_week_data and not is_complete_week(current_week_start, current_time):
                    print(f"   ⚠️ 미완성 주 제외: {current_week_start.strftime('%Y-%m-%d')} 주")
                    break  # 미완성 주는 생성하지 않고 루프 종료
                
                # 현재 주 완성 - 주봉 데이터 생성 (완성된 주만)
                if current_week_data:
                    week_open = current_week_data[0]['open']      # 주 첫 거래일 시가
                    week_high = max([d['high'] for d in current_week_data])    # 주 최고가
                    week_low = min([d['low'] for d in current_week_data])      # 주 최저가
                    week_close = current_week_data[-1]['close']   # 주 마지막 거래일 종가
                    week_volume = sum([d['volume'] for d in current_week_data]) # 주 총 거래량
                    
                    weekly_data.append({
                        'Date': current_week_start,
                        'Open': week_open,
                        'High': week_high,
                        'Low': week_low,
                        'Close': week_close,
                        'Volume': week_volume,
                        'TradingDays': len(current_week_data)  # 해당 주의 거래일 수
                    })
                    
                    print(f"   📊 완성된 주봉 생성: {current_week_data[0]['trade_date']} ~ {current_week_data[-1]['trade_date']} ({len(current_week_data)}일)")
                
                # 다음 주 시작
                current_week_start = next_date
                current_week_data = []
        
        if not weekly_data:
            print("   ❌ 주봉 데이터 변환에 실패했습니다.")
            return None
        
        # 주봉 DataFrame 생성
        weekly_df = pd.DataFrame(weekly_data)
        weekly_df.set_index('Date', inplace=True)
        weekly_df.sort_index(inplace=True)
        
        print(f"   ✅ 완성된 주봉만 변환 완료: {len(weekly_df)}주")
        print(f"   📅 변환된 주봉 기간: {weekly_df.index[0].strftime('%Y-%m-%d')} ~ {weekly_df.index[-1].strftime('%Y-%m-%d')}")
        
        # 거래일 수 통계 출력
        avg_trading_days = weekly_df['TradingDays'].mean()
        print(f"   📊 평균 거래일 수: {avg_trading_days:.1f}일/주")
        print(f"   📊 거래일 수 범위: {weekly_df['TradingDays'].min()}일 ~ {weekly_df['TradingDays'].max()}일")
        
        # TradingDays 컬럼 제거 (분석에 불필요)
        weekly_df = weekly_df.drop('TradingDays', axis=1)
        
        return weekly_df
            
    except Exception as e:
        print(f"   ❌ 일봉을 주봉으로 변환하는 중 오류 발생: {str(e)}")
        return None

def is_complete_week(week_start_date, current_date):
    """해당 주가 완성되었는지 확인 (주의 마지막 거래일이 지났는지 확인)"""
    try:
        # week_start_date를 date 객체로 변환
        if hasattr(week_start_date, 'date'):
            week_start = week_start_date.date()
        else:
            week_start = week_start_date
        
        # 현재 날짜를 date 객체로 변환
        if hasattr(current_date, 'date'):
            current = current_date.date()
        else:
            current = current_date
        
        # 주의 마지막 날 계산 (주 시작일로부터 6일 후)
        week_end = week_start + timedelta(days=6)
        
        # 현재 날짜가 주의 마지막 날을 지났는지 확인
        is_complete = current > week_end
        
        if not is_complete:
            print(f"   ⚠️ 미완성 주 감지: {week_start} ~ {week_end} (현재: {current})")
        
        return is_complete
        
    except Exception as e:
        print(f"   ❌ 주 완성도 확인 중 오류: {e}")
        return False

def _is_new_trading_week(week_start, current_date, holiday_manager):
    """현재 날짜가 새로운 거래 주에 속하는지 확인 (한국 공휴일 고려)"""
    try:
        # week_start와 current_date 사이의 일수 계산
        if hasattr(week_start, 'date'):
            start_date = week_start.date()
        else:
            start_date = week_start
        
        if hasattr(current_date, 'date'):
            current_date_obj = current_date.date()
        else:
            current_date_obj = current_date
        
        days_diff = (current_date_obj - start_date).days
        
        # 7일 이상 차이나면 새로운 주
        if days_diff >= 7:
            return True
        
        # 월요일이면서 거래일인 경우 새로운 주로 간주 (단, 최소 1일 이상 차이)
        is_monday = current_date_obj.weekday() == 0  # 월요일 = 0
        is_trading_day = holiday_manager.is_trading_day(current_date_obj)
        
        if is_monday and is_trading_day and days_diff >= 1:
            return True
        
        return False
        
    except Exception as e:
        print(f"   ⚠️ 거래 주 구분 확인 중 오류: {e}")
        return False

def _is_new_week(week_start, current_date):
    """현재 날짜가 새로운 주에 속하는지 확인"""
    try:
        # week_start와 current_date 사이의 일수 계산
        days_diff = (current_date - week_start).days
        
        # 7일 이상 차이나면 새로운 주
        if days_diff >= 7:
            return True
        
        # 또는 월요일을 기준으로 새로운 주인지 확인
        week_start_weekday = week_start.weekday()  # 0=월요일, 6=일요일
        current_weekday = current_date.weekday()
        
        # 월요일(0)부터 시작해서 다음 월요일(0)이 오면 새로운 주
        if current_weekday == 0 and week_start_weekday != 0:
            return True
        
        return False
        
    except Exception as e:
        print(f"   ⚠️ 주 구분 확인 중 오류: {str(e)}")
        # 기본적으로 7일 기준으로 처리
        days_diff = (current_date - week_start).days
        return days_diff >= 7

def validate_weekly_data_reliability(stock_code, latest_date, holiday_manager):
    """주봉 데이터 신뢰성 검증 - 장마감 시간 및 최신 데이터 고려"""
    try:
        # 현재 시간 기준 장 상태 확인
        current_time = datetime.now()
        market_status = holiday_manager.get_market_status(current_time)
        
        # 최신 데이터가 오늘인 경우 장마감 여부 확인
        if isinstance(latest_date, str):
            latest_date = datetime.strptime(latest_date, '%Y-%m-%d').date()
        elif hasattr(latest_date, 'date'):
            latest_date = latest_date.date()
        
        today = current_time.date()
        
        if latest_date == today:
            # 오늘 데이터인 경우 장마감 시간 체크
            if market_status in ["during_market", "near_market_close"]:
                print(f"   ⚠️ 최신 데이터가 오늘({latest_date})이지만 아직 장중입니다.")
                print(f"   💡 주봉 데이터의 정확성을 위해 장마감 후(15:30 이후) 분석을 권장합니다.")
                return False, "장중 데이터 - 주봉 완성되지 않음"
            elif market_status == "non_trading_day":
                print(f"   📅 오늘은 거래일이 아닙니다. 이전 거래일 데이터로 주봉을 생성합니다.")
                return True, "비거래일 - 이전 거래일 데이터 사용"
            else:
                print(f"   ✅ 장마감 후 데이터로 주봉 신뢰성이 높습니다.")
                return True, "장마감 후 데이터 - 높은 신뢰성"
        else:
            # 과거 데이터인 경우 신뢰성 높음
            days_ago = (today - latest_date).days
            print(f"   📅 최신 데이터가 {days_ago}일 전 데이터입니다. 신뢰성이 높습니다.")
            return True, f"{days_ago}일 전 데이터 - 높은 신뢰성"
            
    except Exception as e:
        print(f"   ❌ 주봉 데이터 신뢰성 검증 실패: {e}")
        return False, f"검증 오류: {e}"

def save_weekly_data_to_db(db, stock_code, weekly_data):
    """주봉 데이터를 weekly_data 테이블에 저장 (보조지표 포함)"""
    try:
        print(f"   💾 주봉 데이터(보조지표 포함)를 DB에 저장 중...")
        
        # 기존 주봉 데이터 삭제 (해당 종목)
        delete_query = "DELETE FROM weekly_data WHERE stock_code = %s"
        db.execute_query(delete_query, (stock_code,))
        
        # ✅ 새로운 주봉 데이터 삽입 (보조지표 포함)
        insert_query = """
        INSERT INTO weekly_data 
        (stock_code, week_start, open, high, low, close, volume,
         ma5, ma20, ma60, rsi, stoch_k, stoch_d, bb_upper, bb_middle, bb_lower)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params_list = []
        for date, row in weekly_data.iterrows():
            params = (
                stock_code,
                date.strftime('%Y-%m-%d'),
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume']),
                # ✅ 보조지표 추가
                float(row.get('MA5', 0)) if pd.notna(row.get('MA5')) else None,
                float(row.get('MA20', 0)) if pd.notna(row.get('MA20')) else None,
                float(row.get('MA60', 0)) if pd.notna(row.get('MA60')) else None,
                float(row.get('RSI', 0)) if pd.notna(row.get('RSI')) else None,
                float(row.get('Stoch_K', 0)) if pd.notna(row.get('Stoch_K')) else None,
                float(row.get('Stoch_D', 0)) if pd.notna(row.get('Stoch_D')) else None,
                float(row.get('BB_Upper', 0)) if pd.notna(row.get('BB_Upper')) else None,
                float(row.get('BB_Middle', 0)) if pd.notna(row.get('BB_Middle')) else None,
                float(row.get('BB_Lower', 0)) if pd.notna(row.get('BB_Lower')) else None
            )
            params_list.append(params)
        
        # 배치 삽입
        success_count = 0
        for params in params_list:
            if db.execute_query(insert_query, params):
                success_count += 1
            else:
                print(f"   ❌ 주봉 데이터 저장 실패: {params[1]}")
        
        print(f"   ✅ {success_count}주 주봉 데이터(보조지표 포함) 저장 완료")
        return success_count > 0
            
    except Exception as e:
        print(f"   ❌ 주봉 데이터 저장 중 오류: {str(e)}")
        return False

def calculate_technical_indicators(df):
    """기술적 지표 계산 - 주봉 기준"""
    print(f"   🔧 주봉 기술적 지표 계산 시작 (데이터 수: {len(df)}주)")
    
    # 이동평균선 (주간 기준)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 볼린저 밴드 계산 (20주 기준)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # 스토캐스틱 슬로우 계산
    # %K = (현재가 - 최저가) / (최고가 - 최저가) * 100
    # %D = %K의 3일 이동평균
    # Slow %K = %D
    # Slow %D = Slow %K의 3주 이동평균
    
    # 14주 기준으로 계산
    period = 14
    
    # 최고가와 최저가 계산
    high_14 = df['High'].rolling(window=period).max()
    low_14 = df['Low'].rolling(window=period).min()
    
    # %K 계산
    k_fast = ((df['Close'] - low_14) / (high_14 - low_14)) * 100
    
    # %D 계산 (3주 이동평균)
    d_fast = k_fast.rolling(window=3).mean()
    
    # Slow %K = %D
    df['Stoch_K'] = d_fast
    
    # Slow %D = Slow %K의 3주 이동평균
    df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()
    
    # ✅ RSI (Relative Strength Index) 계산 추가
    try:
        # RSI 계산 (14주 기준)
        rsi_period = 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        
        # 0으로 나누기 방지
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50)  # NaN 값은 중립값 50으로 설정
        
        print(f"   ✅ RSI 계산 완료")
    except Exception as e:
        print(f"   ⚠️ RSI 계산 실패: {e}")
        df['RSI'] = 50.0  # 기본값으로 중립값 설정
    
    print(f"   ✅ 주봉 기술적 지표 계산 완료")
    print(f"   📊 계산된 지표: MA5, MA20, MA60, 볼린저밴드, 스토캐스틱, RSI")
    
    return df

def analyze_weekly_stock_data(hist, stock_code):
    """주식 주봉 데이터 분석"""
    if hist is None or hist.empty:
        return
    
    print("\n" + "="*60)
    print(f"📊 {stock_code} 주식 주봉 분석 결과")
    print("="*60)
    
    # 기본 통계
    print(f"📅 조회 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
    print(f"📈 주봉 거래주 수: {len(hist)}주")
    
    # 가격 정보
    print(f"\n💰 가격 정보:")
    print(f"   시작가: {hist['Open'].iloc[0]:,.0f}원")
    print(f"   종가: {hist['Close'].iloc[-1]:,.0f}원")
    print(f"   최고가: {hist['High'].max():,.0f}원")
    print(f"   최저가: {hist['Low'].min():,.0f}원")
    
    # 변동 정보
    price_change = hist['Close'].iloc[-1] - hist['Open'].iloc[0]
    price_change_pct = (price_change / hist['Open'].iloc[0]) * 100
    
    print(f"\n📊 변동 정보:")
    print(f"   가격 변동: {price_change:+,.0f}원")
    print(f"   변동률: {price_change_pct:+.2f}%")
    
    # 주봉 거래량 정보
    print(f"\n📈 주봉 거래량 정보:")
    print(f"   평균 주봉 거래량: {hist['Volume'].mean():,.0f}주")
    print(f"   최대 주봉 거래량: {hist['Volume'].max():,.0f}주")
    print(f"   최소 주봉 거래량: {hist['Volume'].min():,.0f}주")
    
    # 기술적 지표 계산
    df_with_indicators = calculate_technical_indicators(hist.copy())
    
    # 기술적 지표 정보
    print(f"\n📊 기술적 지표 (최근값):")
    print(f"   5주 이동평균: {df_with_indicators['MA5'].iloc[-1]:,.0f}원")
    print(f"   20주 이동평균: {df_with_indicators['MA20'].iloc[-1]:,.0f}원")
    print(f"   60주 이동평균: {df_with_indicators['MA60'].iloc[-1]:,.0f}원")
    
    # 볼린저 밴드 정보
    current_price = hist['Close'].iloc[-1]
    bb_upper = df_with_indicators['BB_Upper'].iloc[-1]
    bb_lower = df_with_indicators['BB_Lower'].iloc[-1]
    bb_middle = df_with_indicators['BB_Middle'].iloc[-1]
    
    print(f"   볼린저 밴드 상단: {bb_upper:,.0f}원")
    print(f"   볼린저 밴드 중간: {bb_middle:,.0f}원")
    print(f"   볼린저 밴드 하단: {bb_lower:,.0f}원")
    
    # 볼린저 밴드 신호
    if current_price > bb_upper:
        print("   볼린저 밴드 신호: 과매수 구간")
    elif current_price < bb_lower:
        print("   볼린저 밴드 신호: 과매도 구간")
    else:
        print("   볼린저 밴드 신호: 중립 구간")
    
    # 스토캐스틱 정보
    stoch_k = df_with_indicators['Stoch_K'].iloc[-1]
    stoch_d = df_with_indicators['Stoch_D'].iloc[-1]
    print(f"   스토캐스틱 %K: {stoch_k:.1f}")
    print(f"   스토캐스틱 %D: {stoch_d:.1f}")
    
    # 스토캐스틱 신호
    if stoch_k > 80 and stoch_d > 80:
        print("   스토캐스틱 신호: 과매수 구간")
    elif stoch_k < 20 and stoch_d < 20:
        print("   스토캐스틱 신호: 과매도 구간")
    else:
        print("   스토캐스틱 신호: 중립 구간")

def create_weekly_stock_chart(hist, stock_code):
    """주식 주봉 차트 생성 (캔들차트 + 보조지표) - test_overlay_chart.py 스타일 적용"""
    if hist is None or hist.empty:
        return None, None
    
    print(f"\n📈 주봉 캔들차트를 생성합니다...")
    
    # 기술적 지표 계산
    df = calculate_technical_indicators(hist.copy())
    df.index.name = 'Date'
    
    # 차트 생성 (3개 패널: 메인차트, 거래량, 스토캐스틱)
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), height_ratios=[8, 2, 2])
    fig.suptitle(f'{stock_code} Weekly Stock Chart (5 Years) - Image Reference Style', fontsize=16, fontweight='bold')
    
    # 1. 메인 차트 (캔들차트 + 보조지표 오버레이)
    ax1 = axes[0]
    
    # 볼린저 밴드 영역 채우기 (이미지 참고 - 오렌지/베이지 스타일)
    ax1.fill_between(df.index, df['BB_Upper'], df['BB_Lower'], 
                     alpha=0.15, color='#FFE4B5', label='Bollinger Bands')
    
    # 볼린저 밴드 상단과 하단을 오렌지/베이지 색으로 표시 (범례에 표시하지 않음)
    ax1.plot(df.index, df['BB_Upper'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    ax1.plot(df.index, df['BB_Lower'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    
    # 캔들차트 그리기 (이미지 참고 - 빨간색/파란색)
    for i, (date, row) in enumerate(df.iterrows()):
        if row['Close'] >= row['Open']:  # 상승
            color = '#FF4444'  # 빨간색
        else:  # 하락
            color = '#4444FF'  # 파란색
        
        ax1.plot([date, date], [row['Low'], row['High']], color=color, linewidth=1.0)
        ax1.plot([date, date], [row['Open'], row['Close']], color=color, linewidth=3.0)
    
    # 이동평균선 추가 (웹 트레이딩 스타일 유지)
    ax1.plot(df.index, df['MA5'], color='#F59E0B', linewidth=2.0, alpha=0.9, label='MA5')
    ax1.plot(df.index, df['MA20'], color='#8B5CF6', linewidth=2.0, alpha=0.9, label='MA20')
    ax1.plot(df.index, df['MA60'], color='#06B6D4', linewidth=2.0, alpha=0.9, label='MA60')
    
    # 메인 차트 설정
    ax1.set_title('Price Chart with Bollinger Bands and Moving Averages', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price (KRW)', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax1.yaxis.set_label_position('right')
    ax1.yaxis.tick_right()
    
    # 2. 거래량 차트 (두 번째 패널) - 웹 트레이딩 스타일 유지
    ax2 = axes[1]
    
    # 상승/하락에 따른 거래량 색상 (이미지 참고 - 빨간색/파란색)
    colors = ['#FF4444' if close >= open else '#4444FF' 
              for close, open in zip(df['Close'], df['Open'])]
    
    ax2.bar(df.index, df['Volume'], color=colors, alpha=0.7, width=0.8)
    ax2.set_title('Volume', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Volume', fontsize=10, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax2.yaxis.set_label_position('right')
    ax2.yaxis.tick_right()
    
    # 3. 스토캐스틱 차트 (세 번째 패널) - 웹 트레이딩 스타일 유지
    ax3 = axes[2]
    ax3.plot(df.index, df['Stoch_K'], color='#3B82F6', linewidth=2.0, label='%K')
    ax3.plot(df.index, df['Stoch_D'], color='#F59E0B', linewidth=2.0, label='%D')
    ax3.axhline(y=80, color='#EF4444', linestyle='--', alpha=0.8, linewidth=1.5, label='Overbought')
    ax3.axhline(y=20, color='#10B981', linestyle='--', alpha=0.8, linewidth=1.5, label='Oversold')
    ax3.set_ylim(0, 100)
    ax3.set_title('Stochastic Slow', fontsize=12, fontweight='bold')
    ax3.set_ylabel('%K/%D', fontsize=10, fontweight='bold')
    ax3.legend(fontsize=10, framealpha=0.9)
    ax3.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax3.yaxis.set_label_position('right')
    ax3.yaxis.tick_right()
    
    # X축 날짜 설정 - 하단에만 표시
    for i, ax in enumerate(axes):
        if i == len(axes) - 1:  # 마지막 패널에만 날짜 표시
            # 주간 차트이므로 적절한 간격으로 날짜 선택
            date_indices = [df.index[0], df.index[len(df)//4], df.index[len(df)//2], 
                           df.index[3*len(df)//4], df.index[-1]]
            ax.set_xticks(date_indices)
            ax.set_xticklabels([date.strftime('%Y-%m-%d') for date in date_indices], 
                              rotation=45, ha='right', fontweight='bold')
        else:
            ax.set_xticks([])  # 다른 패널은 X축 눈금 숨김
    
    plt.tight_layout()
    
    # 차트를 이미지로 저장
    
    # weekly_charts 폴더 생성
    charts_dir = "weekly_charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
        print(f"📁 {charts_dir} 폴더를 생성했습니다.")
    
    # 종목명 가져오기 (DB에서)
    stock_name = get_stock_name(stock_code)
    
    # 파일명 생성: weekly_종목명_종목번호_생성일.png
    current_date = datetime.now().strftime("%Y%m%d")
    base_filename = f"weekly_{stock_name}_{stock_code}_{current_date}.png"
    
    # 파일명에서 특수문자 제거 및 공백을 언더스코어로 변경
    base_filename = base_filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
    
    # 파일 중복 확인 및 버전 추가
    version = 1
    filename = base_filename
    filepath = os.path.join(charts_dir, filename)
    
    while os.path.exists(filepath):
        # 파일명에서 확장자 분리
        name_without_ext = base_filename.rsplit('.', 1)[0]
        ext = base_filename.rsplit('.', 1)[1]
        filename = f"{name_without_ext}_v{version}.{ext}"
        filepath = os.path.join(charts_dir, filename)
        version += 1
    
    # 차트 저장
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"💾 차트가 저장되었습니다: {filepath}")
    
    # 차트 뷰어를 띄우지 않고 차트 닫기
    plt.close()
    
    # 차트 데이터 반환 (보조지표 포함)
    return filepath, df

def get_stock_name(stock_code):
    """종목코드로 종목명을 가져오는 함수 - DB에서 조회"""
    try:
        # 데이터베이스 연결
        db = DatabaseManager()
        
        if not db.connect():
            print(f"   ⚠️ DB 연결 실패로 종목코드를 종목명으로 사용: {stock_code}")
            return stock_code
        
        # stocks 테이블에서 종목명 조회
        stock_name_query = "SELECT stock_name FROM stocks WHERE stock_code = %s"
        stock_info = db.fetch_one(stock_name_query, (stock_code,))
        
        db.disconnect()
        
        if stock_info and stock_info['stock_name']:
            return stock_info['stock_name']
        else:
            print(f"   ⚠️ 종목명을 찾을 수 없어 종목코드를 사용: {stock_code}")
            return stock_code
            
    except Exception as e:
        print(f"   ⚠️ 종목명 조회 실패: {str(e)}")
        return stock_code

def save_chart_data_to_json(chart_data, stock_code, stock_name):
    """차트 데이터를 JSON으로 저장 - Gemini AI 최적화"""
    if chart_data is None or chart_data.empty:
        print("❌ 저장할 차트 데이터가 없습니다.")
        return None
    
    try:
        print(f"\n📊 차트 데이터를 JSON으로 저장합니다...")
        
        # 시간대 정보 제거
        chart_data_clean = chart_data.copy()
        if chart_data_clean.index.tz is not None:
            chart_data_clean.index = chart_data_clean.index.tz_localize(None)
            print("   🔧 시간대 정보를 제거했습니다.")
        
        # JSON 저장 디렉토리 생성
        json_dir = "chart_data_json"
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)
            print(f"📁 {json_dir} 폴더를 생성했습니다.")
        
        # 파일명 생성
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"weekly_{stock_name}_{stock_code}_{current_date}.json"
        filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        filepath = os.path.join(json_dir, filename)
        
        # 중복 확인
        version = 1
        while os.path.exists(filepath):
            name_without_ext = filename.rsplit('.', 1)[0]
            ext = filename.rsplit('.', 1)[1]
            filename = f"{name_without_ext}_v{version}.{ext}"
            filepath = os.path.join(json_dir, filename)
            version += 1
        
        # JSON 데이터 구조화
        json_data = {
            "metadata": {
                "stock_name": stock_name,
                "stock_code": stock_code,
                "created_at": datetime.now().isoformat(),
                "data_period": {
                    "start": chart_data_clean.index[0].strftime('%Y-%m-%d'),
                    "end": chart_data_clean.index[-1].strftime('%Y-%m-%d')
                },
                "total_records": len(chart_data_clean),
                "chart_type": "weekly"
            },
            "summary": {
                "latest_close": float(chart_data_clean['Close'].iloc[-1]),
                "latest_volume": int(chart_data_clean['Volume'].iloc[-1]),
                "price_change": float(chart_data_clean['Close'].iloc[-1] - chart_data_clean['Open'].iloc[0]),
                "price_change_pct": float(((chart_data_clean['Close'].iloc[-1] / chart_data_clean['Open'].iloc[0]) - 1) * 100),
                "highest_price": float(chart_data_clean['High'].max()),
                "lowest_price": float(chart_data_clean['Low'].min()),
                "avg_volume": float(chart_data_clean['Volume'].mean())
            },
            "technical_indicators": {
                "latest_values": {
                    "ma5": float(chart_data_clean['MA5'].iloc[-1]) if 'MA5' in chart_data_clean else None,
                    "ma20": float(chart_data_clean['MA20'].iloc[-1]) if 'MA20' in chart_data_clean else None,
                    "ma60": float(chart_data_clean['MA60'].iloc[-1]) if 'MA60' in chart_data_clean else None,
                    "stoch_k": float(chart_data_clean['Stoch_K'].iloc[-1]) if 'Stoch_K' in chart_data_clean else None,
                    "stoch_d": float(chart_data_clean['Stoch_D'].iloc[-1]) if 'Stoch_D' in chart_data_clean else None,
                    "bb_upper": float(chart_data_clean['BB_Upper'].iloc[-1]) if 'BB_Upper' in chart_data_clean else None,
                    "bb_lower": float(chart_data_clean['BB_Lower'].iloc[-1]) if 'BB_Lower' in chart_data_clean else None,
                    "bb_middle": float(chart_data_clean['BB_Middle'].iloc[-1]) if 'BB_Middle' in chart_data_clean else None
                }
            },
            "chart_data": []
        }
        
        # 차트 데이터 추가 (최근 30개 데이터만 - AI 분석에 충분)
        recent_data = chart_data_clean.tail(30)
        for date, row in recent_data.iterrows():
            data_point = {
                "date": date.strftime('%Y-%m-%d'),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            }
            
            # 기술적 지표 추가
            if 'MA5' in row:
                data_point["ma5"] = float(row['MA5'])
            if 'MA20' in row:
                data_point["ma20"] = float(row['MA20'])
            if 'MA60' in row:
                data_point["ma60"] = float(row['MA60'])
            if 'Stoch_K' in row:
                data_point["stoch_k"] = float(row['Stoch_K'])
            if 'Stoch_D' in row:
                data_point["stoch_d"] = float(row['Stoch_D'])
            if 'BB_Upper' in row:
                data_point["bb_upper"] = float(row['BB_Upper'])
            if 'BB_Lower' in row:
                data_point["bb_lower"] = float(row['BB_Lower'])
            if 'BB_Middle' in row:
                data_point["bb_middle"] = float(row['BB_Middle'])
            
            json_data["chart_data"].append(data_point)
        
        # JSON 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 JSON 파일이 저장되었습니다: {filepath}")
        print(f"📊 데이터 구조:")
        print(f"   - 메타데이터: 종목 정보, 생성일시, 데이터 기간")
        print(f"   - 요약 정보: 최근 가격, 변동률, 거래량 통계")
        print(f"   - 기술적 지표: 최신 보조지표 값들")
        print(f"   - 차트 데이터: 최근 30개 거래주 OHLCV + 지표")
        
        return filepath
        
    except Exception as e:
        print(f"❌ JSON 파일 저장 중 오류: {e}")
        return None

def save_chart_data_to_csv(chart_data, stock_code, stock_name):
    """차트 데이터를 CSV로 저장 - 간단하고 읽기 쉬움"""
    if chart_data is None or chart_data.empty:
        print("❌ 저장할 차트 데이터가 없습니다.")
        return None
    
    try:
        print(f"\n📊 차트 데이터를 CSV로 저장합니다...")
        
        # 시간대 정보 제거
        chart_data_clean = chart_data.copy()
        if chart_data_clean.index.tz is not None:
            chart_data_clean.index = chart_data_clean.index.tz_localize(None)
            print("   🔧 시간대 정보를 제거했습니다.")
        
        # CSV 저장 디렉토리 생성
        csv_dir = "chart_data_csv"
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
            print(f"📁 {csv_dir} 폴더를 생성했습니다.")
        
        # 파일명 생성
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"weekly_{stock_name}_{stock_code}_{current_date}.csv"
        filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        filepath = os.path.join(csv_dir, filename)
        
        # 중복 확인
        version = 1
        while os.path.exists(filepath):
            name_without_ext = filename.rsplit('.', 1)[0]
            ext = filename.rsplit('.', 1)[1]
            filename = f"{name_without_ext}_v{version}.{ext}"
            filepath = os.path.join(csv_dir, filename)
            version += 1
        
        # CSV 저장 (최근 50개 데이터만)
        recent_data = chart_data_clean.tail(50)
        recent_data.to_csv(filepath, encoding='utf-8-sig')
        
        print(f"💾 CSV 파일이 저장되었습니다: {filepath}")
        print(f"📊 데이터: 최근 50개 거래주 OHLCV + 기술적 지표")
        
        return filepath
        
    except Exception as e:
        print(f"❌ CSV 파일 저장 중 오류: {e}")
        return None

def save_chart_summary_to_text(chart_data, stock_code, stock_name):
    """차트 데이터 요약을 텍스트로 저장 - AI 분석 최적화"""
    if chart_data is None or chart_data.empty:
        print("❌ 저장할 차트 데이터가 없습니다.")
        return None
    
    try:
        print(f"\n📊 차트 데이터 요약을 텍스트로 저장합니다...")
        
        # 텍스트 저장 디렉토리 생성
        text_dir = "chart_data_text"
        if not os.path.exists(text_dir):
            os.makedirs(text_dir)
            print(f"📁 {text_dir} 폴더를 생성했습니다.")
        
        # 파일명 생성
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"weekly_{stock_name}_{stock_code}_{current_date}_summary.txt"
        filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        filepath = os.path.join(text_dir, filename)
        
        # 중복 확인
        version = 1
        while os.path.exists(filepath):
            name_without_ext = filename.rsplit('.', 1)[0]
            ext = filename.rsplit('.', 1)[1]
            filename = f"{name_without_ext}_v{version}.{ext}"
            filepath = os.path.join(text_dir, filename)
            version += 1
        
        # 요약 텍스트 생성
        summary_text = f"""주식 주봉 차트 데이터 요약
========================

종목 정보:
- 종목명: {stock_name}
- 종목코드: {stock_code}
- 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 데이터 기간: {chart_data.index[0].strftime('%Y-%m-%d')} ~ {chart_data.index[-1].strftime('%Y-%m-%d')}
- 총 데이터 수: {len(chart_data)}주

가격 정보:
- 시작가: {chart_data['Open'].iloc[0]:,.0f}원
- 최근 종가: {chart_data['Close'].iloc[-1]:,.0f}원
- 최고가: {chart_data['High'].max():,.0f}원
- 최저가: {chart_data['Low'].min():,.0f}원
- 가격 변동: {chart_data['Close'].iloc[-1] - chart_data['Open'].iloc[0]:+,.0f}원
- 변동률: {((chart_data['Close'].iloc[-1] / chart_data['Open'].iloc[0]) - 1) * 100:+.2f}%

거래량 정보:
- 평균 거래량: {chart_data['Volume'].mean():,.0f}주
- 최대 거래량: {chart_data['Volume'].max():,.0f}주
- 최근 거래량: {chart_data['Volume'].iloc[-1]:,.0f}주

기술적 지표 (최근값):
"""
        
        # 기술적 지표 추가
        if 'MA5' in chart_data:
            summary_text += f"- 5주 이동평균: {chart_data['MA5'].iloc[-1]:,.0f}원\n"
        if 'MA20' in chart_data:
            summary_text += f"- 20주 이동평균: {chart_data['MA20'].iloc[-1]:,.0f}원\n"
        if 'MA60' in chart_data:
            summary_text += f"- 60주 이동평균: {chart_data['MA60'].iloc[-1]:,.0f}원\n"
        if 'Stoch_K' in chart_data:
            summary_text += f"- 스토캐스틱 %K: {chart_data['Stoch_K'].iloc[-1]:.1f}\n"
        if 'Stoch_D' in chart_data:
            summary_text += f"- 스토캐스틱 %D: {chart_data['Stoch_D'].iloc[-1]:.1f}\n"
        if 'BB_Upper' in chart_data:
            summary_text += f"- 볼린저 밴드 상단: {chart_data['BB_Upper'].iloc[-1]:,.0f}원\n"
        if 'BB_Lower' in chart_data:
            summary_text += f"- 볼린저 밴드 하단: {chart_data['BB_Lower'].iloc[-1]:,.0f}원\n"
        if 'BB_Middle' in chart_data:
            summary_text += f"- 볼린저 밴드 중간: {chart_data['BB_Middle'].iloc[-1]:,.0f}원\n"
        
        summary_text += f"""
최근 10개 거래주 데이터:
"""
        
        # 최근 10개 데이터 추가
        recent_data = chart_data.tail(10)
        for date, row in recent_data.iterrows():
            summary_text += f"{date.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f} (거래량: {row['Volume']:,.0f})\n"
        
        # 텍스트 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        
        print(f"💾 텍스트 요약 파일이 저장되었습니다: {filepath}")
        
        return filepath
        
    except Exception as e:
        print(f"❌ 텍스트 파일 저장 중 오류: {e}")
        return None

# 엑셀 저장 기능 주석 처리 (나중에 검토용으로 사용)
'''
def save_chart_data_to_excel(chart_data, stock_code, stock_name):
    """차트 데이터를 엑셀로 저장 (보조지표 포함)"""
    if chart_data is None or chart_data.empty:
        print("❌ 저장할 차트 데이터가 없습니다.")
        return None
    
    try:
        print(f"\n📊 차트 데이터를 엑셀로 저장합니다...")
        
        # 시간대 정보 제거 (Excel 호환성을 위해)
        chart_data_clean = chart_data.copy()
        if chart_data_clean.index.tz is not None:
            chart_data_clean.index = chart_data_clean.index.tz_localize(None)
            print("   🔧 시간대 정보를 제거했습니다.")
        
        # 엑셀 파일 저장 디렉토리 생성
        excel_dir = "chart_data_excel"
        if not os.path.exists(excel_dir):
            os.makedirs(excel_dir)
            print(f"📁 {excel_dir} 폴더를 생성했습니다.")
        
        # 파일명 생성
        current_date = datetime.now().strftime("%Y%m%d")
        base_filename = f"weekly_chart_data_{stock_name}_{stock_code}_{current_date}.xlsx"
        base_filename = base_filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        
        # 파일 중복 확인 및 버전 추가
        version = 1
        filename = base_filename
        filepath = os.path.join(excel_dir, filename)
        
        while os.path.exists(filepath):
            name_without_ext = base_filename.rsplit('.', 1)[0]
            ext = base_filename.rsplit('.', 1)[1]
            filename = f"{name_without_ext}_v{version}.{ext}"
            filepath = os.path.join(excel_dir, filename)
            version += 1
        
        # 워크북 생성
        wb = openpyxl.Workbook()
        
        # 기본 시트 제거
        wb.remove(wb.active)
        
        # 1. 종합 데이터 시트 (모든 지표 포함)
        ws_summary = wb.create_sheet("종합데이터")
        
        # 모든 컬럼 선택
        summary_data = chart_data_clean.copy()
        summary_data.index.name = 'Date'
        summary_data.insert(0, 'Date', summary_data.index.strftime('%Y-%m-%d'))
        
        for r in dataframe_to_rows(summary_data, index=False, header=True):
            ws_summary.append(r)
        
        # 헤더 스타일링
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for cell in ws_summary[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 컬럼 너비 조정
        for col in ws_summary.columns:
            ws_summary.column_dimensions[col[0].column_letter].width = 12
        
        # 2. 요약 정보 시트
        ws_info = wb.create_sheet("요약정보")
        
        # 기본 정보
        info_data = [
            ["종목명", stock_name],
            ["종목코드", stock_code],
            ["생성일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["데이터 기간", f"{chart_data_clean.index[0].strftime('%Y-%m-%d')} ~ {chart_data_clean.index[-1].strftime('%Y-%m-%d')}"],
            ["총 데이터 수", len(chart_data_clean)],
            ["", ""],
            ["최근 데이터 요약", ""],
            ["최근 종가", f"{chart_data_clean['Close'].iloc[-1]:,.0f}원"],
            ["최근 스토캐스틱 %K", f"{chart_data_clean['Stoch_K'].iloc[-1]:.1f}"],
            ["최근 스토캐스틱 %D", f"{chart_data_clean['Stoch_D'].iloc[-1]:.1f}"],
            ["5주 이동평균", f"{chart_data_clean['MA5'].iloc[-1]:,.0f}원"],
            ["20주 이동평균", f"{chart_data_clean['MA20'].iloc[-1]:,.0f}원"],
            ["60주 이동평균", f"{chart_data_clean['MA60'].iloc[-1]:,.0f}원"],
            ["볼린저 밴드 상단", f"{chart_data_clean['BB_Upper'].iloc[-1]:,.0f}원"],
            ["볼린저 밴드 하단", f"{chart_data_clean['BB_Lower'].iloc[-1]:,.0f}원"],
        ]
        
        for row in info_data:
            ws_info.append(row)
        
        # 헤더 스타일링
        for row in ws_info.iter_rows(min_row=1, max_row=len(info_data)):
            for cell in row:
                if cell.value and cell.value in ["종목명", "종목코드", "생성일시", "데이터 기간", "총 데이터 수", "최근 데이터 요약"]:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # 컬럼 너비 조정
        ws_info.column_dimensions['A'].width = 20
        ws_info.column_dimensions['B'].width = 30
        
        # 파일 저장
        wb.save(filepath)
        print(f"💾 엑셀 파일이 저장되었습니다: {filepath}")
        
        # 시트 정보 출력
        print(f"📊 생성된 시트:")
        print(f"   - 종합데이터: 모든 지표 통합 (OHLCV + 기술적 지표)")
        print(f"   - 요약정보: 종목 및 데이터 요약")
        
        return filepath
        
    except Exception as e:
        print(f"❌ 엑셀 파일 저장 중 오류: {e}")
        return None
'''

def main():
    """메인 함수"""
    print("🚀 국내 주식 주봉 시세 조회 프로그램 (5년)")
    print("="*60)
    
    # 종목코드 입력
    while True:
        stock_code = input("📈 종목코드를 입력하세요 (예: 005930): ").strip()
        if stock_code.isdigit() and len(stock_code) == 6:
            break
        else:
            print("❌ 올바른 종목코드를 입력해주세요 (6자리 숫자)")
    
    # 주봉 데이터 조회
    hist = get_weekly_stock_data(stock_code)
    
    if hist is not None:
        # 주봉 데이터 분석
        analyze_weekly_stock_data(hist, stock_code)
        
        # 주봉 차트 생성 (차트 데이터 반환)
        chart_path, chart_data = create_weekly_stock_chart(hist, stock_code)
        
        if chart_path and chart_data is not None:
            # 종목명 가져오기
            stock_name = get_stock_name(stock_code)
            
            # JSON 저장 (추천)
            json_path = save_chart_data_to_json(chart_data, stock_code, stock_name)
            
            # CSV 저장 (보조)
            csv_path = save_chart_data_to_csv(chart_data, stock_code, stock_name)
            
            # 텍스트 요약 저장 (보조)
            text_path = save_chart_summary_to_text(chart_data, stock_code, stock_name)
            
            if json_path:
                print(f"\n✅ 주봉 분석이 완료되었습니다!")
                print(f"📈 차트 이미지: {chart_path}")
                print(f"📊 JSON 데이터: {json_path}")
                if csv_path:
                    print(f"📋 CSV 데이터: {csv_path}")
                if text_path:
                    print(f"📝 텍스트 요약: {text_path}")
                print(f"\n💡 이제 AI 분석에 차트 이미지와 JSON 데이터를 함께 전달할 수 있습니다!")
            else:
                print(f"\n✅ 주봉 분석이 완료되었습니다!")
                print(f"📈 차트 이미지: {chart_path}")
                print(f"❌ 데이터 파일 저장에 실패했습니다.")
        else:
            print(f"\n❌ 차트 생성에 실패했습니다.")
    else:
        print("\n❌ 주봉 데이터 조회에 실패했습니다.")

if __name__ == "__main__":
    main() 