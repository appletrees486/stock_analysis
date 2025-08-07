#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국내 주식 주봉 시세 조회 스크립트
"""

# matplotlib 백엔드를 Agg로 설정 (tkinter 에러 방지)
import matplotlib
matplotlib.use('Agg')

import yfinance as yf
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
    """국내 주식 주봉 데이터 조회 (5년) - 네이버 금융 우선, Yahoo Finance 보조"""
    print(f"🔍 {stock_code} 5년 주봉 시세 조회 중...")
    print("   📅 주봉 데이터는 거래일 기준으로 제공되며, 주말/공휴일은 포함되지 않습니다.")
    
    # 네이버 금융 데이터 조회 (우선)
    print("   🔄 네이버 금융에서 실시간 데이터 확인 중...")
    from naver_data_module import get_naver_stock_data, get_naver_historical_data
    
    naver_result = get_naver_stock_data(stock_code)
    if naver_result['success']:
        print(f"   ✅ 네이버 금융 실시간 데이터: {naver_result['stock_name']}")
        print(f"   📈 현재가: {naver_result['current_price']:,.0f}원")
        print(f"   📊 변동: {naver_result['change_direction']} {naver_result['change_amount']:+,}원")
        print(f"   ⏰ 조회시간: {naver_result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Yahoo Finance에서 주봉 데이터 조회 (주 데이터)
    yf_weekly_data = None
    tickers_to_try = [
        f"{stock_code}.KS",   # 코스피
        f"{stock_code}.KQ",   # 코스닥 (일부)
        f"{stock_code}.KS",   # 다시 시도
    ]
    
    for i, ticker in enumerate(tickers_to_try):
        try:
            print(f"   시도 {i+1}: {ticker}")
            stock = yf.Ticker(ticker)
            # 5년 주봉 데이터 조회
            hist = stock.history(period="5y", interval="1wk")
            
            if not hist.empty:
                print(f"✅ Yahoo Finance 주봉: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')} 기간 주봉 데이터를 조회했습니다.")
                print(f"📅 총 {len(hist)}주간의 주봉 거래 데이터를 가져왔습니다.")
                print(f"🏢 사용된 티커: {ticker}")
                yf_weekly_data = hist
                break
                
        except Exception as e:
            print(f"   ❌ {ticker} 시도 실패: {str(e)[:50]}...")
            continue
    
    # Yahoo Finance 주봉 데이터가 있는 경우 최신도 확인
    if yf_weekly_data is not None:
        # 최신 데이터 확인 (현재 날짜와 비교)
        latest_weekly_date = yf_weekly_data.index[-1]
        # 타임존 정보 제거
        if hasattr(latest_weekly_date, 'tz_localize'):
            latest_weekly_date = latest_weekly_date.tz_localize(None)
        elif hasattr(latest_weekly_date, 'replace'):
            latest_weekly_date = latest_weekly_date.replace(tzinfo=None)
        
        current_date = datetime.now()
        days_diff = (current_date - latest_weekly_date).days
        
        print(f"   📅 Yahoo Finance 주봉 최신 데이터: {latest_weekly_date.strftime('%Y-%m-%d')}")
        print(f"   📅 현재 날짜: {current_date.strftime('%Y-%m-%d')}")
        print(f"   📅 데이터 차이: {days_diff}일")
        
        # 1일 이상 차이나면 일봉 데이터로 최신 주봉 보완
        if days_diff > 0:
            print(f"   ⚠️ Yahoo Finance 주봉 데이터가 {days_diff}일 전 데이터입니다.")
            print(f"   🔄 Yahoo Finance 일봉 데이터로 최신 주봉을 보완합니다...")
            
            # Yahoo Finance에서 일봉 데이터 조회 (최근 90일 + 오늘까지 확실히 포함)
            try:
                # 먼저 period로 시도
                daily_hist = stock.history(period="90d", interval="1d")
                
                # 만약 오늘 데이터가 없다면 start/end로 다시 시도
                if not daily_hist.empty:
                    latest_date = daily_hist.index[-1]
                    if hasattr(latest_date, 'tz_localize'):
                        latest_date = latest_date.tz_localize(None)
                    elif hasattr(latest_date, 'replace'):
                        latest_date = latest_date.replace(tzinfo=None)
                    
                    # 오늘 데이터가 없으면 start/end로 다시 시도
                    if latest_date.date() < current_date.date():
                        print(f"   🔄 오늘 데이터가 없어 start/end 파라미터로 재시도합니다...")
                        start_date = (current_date - timedelta(days=90)).strftime('%Y-%m-%d')
                        end_date = current_date.strftime('%Y-%m-%d')
                        daily_hist = stock.history(start=start_date, end=end_date, interval="1d")
                if not daily_hist.empty:
                    print(f"   ✅ Yahoo Finance 일봉: {daily_hist.index[0].strftime('%Y-%m-%d')} ~ {daily_hist.index[-1].strftime('%Y-%m-%d')}")
                    
                    # 일봉 데이터의 최신 날짜 확인
                    latest_daily_date = daily_hist.index[-1]
                    if hasattr(latest_daily_date, 'tz_localize'):
                        latest_daily_date = latest_daily_date.tz_localize(None)
                    elif hasattr(latest_daily_date, 'replace'):
                        latest_daily_date = latest_daily_date.replace(tzinfo=None)
                    
                    print(f"   📅 일봉 최신 데이터: {latest_daily_date.strftime('%Y-%m-%d')}")
                    print(f"   📅 현재 날짜: {current_date.strftime('%Y-%m-%d')}")
                    
                    # 일봉 데이터가 현재 날짜보다 최신인지 확인
                    if latest_daily_date.date() >= current_date.date():
                        print(f"   ✅ 일봉 데이터가 오늘까지 포함되어 있습니다!")
                    else:
                        print(f"   ⚠️ 일봉 데이터가 {latest_daily_date.strftime('%Y-%m-%d')}까지만 있습니다.")
                        print(f"   📅 장이 열리지 않았거나 데이터 업데이트가 지연되었을 수 있습니다.")
                    
                    print(f"   📊 일봉 데이터 상세:")
                    for i, (date, row) in enumerate(daily_hist.tail(5).iterrows()):
                        print(f"      {date.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f}")
                    
                    # 일봉을 주봉으로 변환
                    enhanced_weekly_data = convert_daily_to_weekly(daily_hist, yf_weekly_data, stock_code)
                    if enhanced_weekly_data is not None:
                        print(f"   ✅ 일봉 데이터로 주봉을 보완했습니다!")
                        print(f"   📅 최신 주봉 데이터: {enhanced_weekly_data.index[-1].strftime('%Y-%m-%d')}")
                        return enhanced_weekly_data
                    else:
                        print(f"   ⚠️ 일봉 데이터 변환에 실패하여 기존 주봉 데이터를 사용합니다.")
                else:
                    print(f"   ⚠️ Yahoo Finance 일봉 데이터를 가져올 수 없어 기존 주봉 데이터를 사용합니다.")
            except Exception as e:
                print(f"   ❌ Yahoo Finance 일봉 데이터 조회 실패: {str(e)[:50]}...")
        
        return yf_weekly_data
    
    # Yahoo Finance에서 주봉 데이터를 가져올 수 없는 경우
    print("   ⚠️ Yahoo Finance에서 주봉 데이터를 가져올 수 없습니다.")
    print("   🔄 Yahoo Finance 일봉 데이터로 주봉을 생성합니다...")
    
    # Yahoo Finance에서 일봉 데이터로 주봉 생성 시도
    for ticker in tickers_to_try:
        try:
            stock = yf.Ticker(ticker)
            # 5년 일봉 데이터 조회
            daily_hist = stock.history(period="5y", interval="1d")
            if not daily_hist.empty:
                print(f"   ✅ Yahoo Finance 일봉: {daily_hist.index[0].strftime('%Y-%m-%d')} ~ {daily_hist.index[-1].strftime('%Y-%m-%d')}")
                
                # 일봉을 주봉으로 변환
                weekly_from_daily = convert_daily_to_weekly(daily_hist, None, stock_code)
                if weekly_from_daily is not None:
                    print(f"   ✅ 일봉 데이터로 주봉을 생성했습니다!")
                    return weekly_from_daily
                break
        except Exception as e:
            print(f"   ❌ {ticker} 일봉 시도 실패: {str(e)[:50]}...")
            continue
    
    # 모든 소스에서 실패
    print("❌ 주봉 데이터 조회에 실패했습니다.")
    print("💡 가능한 원인:")
    print("   - 종목코드가 잘못되었습니다")
    print("   - 해당 종목이 상장폐지되었습니다")
    print("   - Yahoo Finance에서 지원하지 않는 종목입니다")
    return None

def convert_daily_to_weekly(daily_data, existing_weekly_data=None, stock_code=None):
    """일봉 데이터를 주봉으로 변환 (미완성 주 포함) - 네이버 실시간 데이터 활용"""
    try:
        # 일봉 데이터를 주별로 그룹화
        daily_data_copy = daily_data.copy()
        daily_data_copy.index.name = 'Date'
        
        # 현재 날짜 확인
        current_date = datetime.now().date()
        
        # 네이버 금융 실시간 데이터 가져오기 (현재 주 업데이트용)
        naver_current_price = None
        if stock_code:
            try:
                from naver_data_module import get_naver_stock_data
                naver_result = get_naver_stock_data(stock_code)
                if naver_result['success']:
                    naver_current_price = naver_result['current_price']
                    print(f"   🔄 네이버 실시간 데이터로 현재 주 업데이트: {naver_current_price:,.0f}원")
            except Exception as e:
                print(f"   ⚠️ 네이버 실시간 데이터 조회 실패: {str(e)[:30]}...")
        
        # 주별로 그룹화 (월요일을 주의 시작으로 가정)
        daily_data_copy['Week'] = daily_data_copy.index.to_period('W-MON')
        
        weekly_data = []
        
        for week, group in daily_data_copy.groupby('Week'):
            if len(group) > 0:
                # 주봉 데이터 계산
                week_start = group.index[0]
                
                # 미완성 주인지 확인 (현재 주인 경우)
                is_current_week = False
                if hasattr(week_start, 'date'):
                    week_start_date = week_start.date()
                else:
                    week_start_date = week_start
                
                # 현재 주인지 확인 (월요일부터 현재까지)
                week_end_date = week_start_date + timedelta(days=6)
                if week_start_date <= current_date <= week_end_date:
                    is_current_week = True
                    print(f"   📅 현재 주 감지: {week_start_date} ~ {week_end_date}")
                
                # 현재 주인 경우 실제 마지막 거래일을 날짜로 사용
                if is_current_week:
                    # 현재 주의 실제 마지막 거래일 찾기
                    last_trading_day = group.index[-1]
                    actual_close = group['Close'].iloc[-1]
                    
                    # 네이버 실시간 데이터가 있으면 현재 주 종가 업데이트
                    if naver_current_price is not None:
                        # 오늘 데이터가 있는지 확인
                        today_data = group[group.index.date == current_date]
                        if not today_data.empty:
                            # 오늘 데이터가 있으면 네이버 실시간 가격으로 업데이트
                            actual_close = naver_current_price
                            print(f"      📅 오늘 데이터 포함, 네이버 실시간 가격으로 업데이트: {actual_close:,.0f}원")
                        else:
                            # 오늘 데이터가 없어도 네이버 실시간 가격이 마지막 거래일 종가와 다르면 업데이트
                            if abs(naver_current_price - actual_close) > 0:
                                actual_close = naver_current_price
                                print(f"      📅 네이버 실시간 가격으로 현재 주 종가 업데이트: {actual_close:,.0f}원")
                            else:
                                print(f"      📅 네이버 실시간 가격과 동일, 마지막 거래일 종가 사용: {actual_close:,.0f}원")
                    else:
                        print(f"      📅 현재 주 마지막 거래일: {last_trading_day.strftime('%Y-%m-%d')}, 종가: {actual_close:,.0f}")
                    
                    # 현재 주는 실제 마지막 거래일을 날짜로 사용
                    weekly_data.append({
                        'Date': last_trading_day,       # 실제 마지막 거래일
                        'Open': group['Open'].iloc[0],  # 주 첫날 시가
                        'High': group['High'].max(),    # 주 최고가
                        'Low': group['Low'].min(),      # 주 최저가
                        'Close': actual_close,          # 실제 마지막 거래일 종가 (또는 네이버 실시간)
                        'Volume': group['Volume'].sum(), # 주 총 거래량
                        'IsCurrentWeek': is_current_week # 현재 주 여부
                    })
                else:
                    # 완성된 주는 기존 방식
                    weekly_data.append({
                        'Date': week_start,
                        'Open': group['Open'].iloc[0],      # 주 첫날 시가
                        'High': group['High'].max(),        # 주 최고가
                        'Low': group['Low'].min(),          # 주 최저가
                        'Close': group['Close'].iloc[-1],   # 주 마지막날 종가
                        'Volume': group['Volume'].sum(),    # 주 총 거래량
                        'IsCurrentWeek': is_current_week    # 현재 주 여부
                    })
        
        if not weekly_data:
            print("   ❌ 주봉 데이터 변환에 실패했습니다.")
            return None
        
        # 주봉 DataFrame 생성
        weekly_df = pd.DataFrame(weekly_data)
        weekly_df.set_index('Date', inplace=True)
        weekly_df.sort_index(inplace=True)
        
        # 현재 주가 있는지 확인
        current_weeks = weekly_df[weekly_df['IsCurrentWeek'] == True]
        if not current_weeks.empty:
            print(f"   ✅ 현재 주 포함: {len(current_weeks)}주")
            for idx, row in current_weeks.iterrows():
                print(f"      📅 {idx.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f}")
        
        # IsCurrentWeek 컬럼 제거 (분석에 불필요)
        weekly_df = weekly_df.drop('IsCurrentWeek', axis=1)
        
        # 기존 주봉 데이터가 있는 경우 병합
        if existing_weekly_data is not None:
            # 중복 제거하고 병합
            combined_data = pd.concat([existing_weekly_data, weekly_df])
            combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
            combined_data.sort_index(inplace=True)
            
            print(f"   📅 기존 주봉: {len(existing_weekly_data)}주 + 신규 주봉: {len(weekly_df)}주 = 총 {len(combined_data)}주")
            return combined_data
        else:
            print(f"   📅 일봉에서 생성된 주봉: {len(weekly_df)}주")
            return weekly_df
            
    except Exception as e:
        print(f"   ❌ 일봉을 주봉으로 변환하는 중 오류 발생: {str(e)}")
        return None



def calculate_technical_indicators(df):
    """기술적 지표 계산"""
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
    # Slow %D = Slow %K의 3일 이동평균
    
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
    """주식 주봉 차트 생성 (캔들차트 + 보조지표) - 차트 데이터 반환 추가"""
    if hist is None or hist.empty:
        return None, None
    
    print(f"\n📈 주봉 캔들차트를 생성합니다...")
    
    # 기술적 지표 계산
    df = calculate_technical_indicators(hist.copy())
    df.index.name = 'Date'
    
    # 하나의 큰 차트에 모든 지표 포함
    fig, axes = plt.subplots(5, 1, figsize=(15, 20), height_ratios=[6, 2, 2, 2, 2])
    fig.suptitle(f'{stock_code} Weekly Stock Chart (5 Years) - Technical Indicators', fontsize=16, fontweight='bold')
    
    # 1. 캔들차트 (첫 번째 패널)
    ax1 = axes[0]
    
    # 캔들차트 그리기
    for i, (date, row) in enumerate(df.iterrows()):
        color = 'red' if row['Close'] >= row['Open'] else 'blue'
        ax1.plot([i, i], [row['Low'], row['High']], color=color, linewidth=1)
        ax1.plot([i, i], [row['Open'], row['Close']], color=color, linewidth=3)
    
    # 이동평균선 추가
    ax1.plot(range(len(df)), df['MA5'], color='red', linewidth=1, alpha=0.7, label='MA5')
    ax1.plot(range(len(df)), df['MA20'], color='green', linewidth=1, alpha=0.7, label='MA20')
    ax1.plot(range(len(df)), df['MA60'], color='orange', linewidth=1, alpha=0.7, label='MA60')
    
    # 볼린저 밴드 추가
    ax1.plot(range(len(df)), df['BB_Upper'], color='gray', linewidth=1, alpha=0.5, label='BB Upper')
    ax1.plot(range(len(df)), df['BB_Middle'], color='gray', linewidth=1, alpha=0.5, label='BB Middle')
    ax1.plot(range(len(df)), df['BB_Lower'], color='gray', linewidth=1, alpha=0.5, label='BB Lower')
    
    ax1.set_title('Price Chart with Moving Averages and Bollinger Bands')
    ax1.set_ylabel('Price (KRW)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 주봉 거래량 차트 (두 번째 패널)
    ax2 = axes[1]
    ax2.bar(range(len(df)), df['Volume'], color='green', alpha=0.7)
    ax2.set_title('Weekly Volume')
    ax2.set_ylabel('Volume')
    ax2.grid(True, alpha=0.3)
    
    # 3. 볼린저 밴드 %B 차트 (세 번째 패널)
    ax3 = axes[2]
    # %B = (현재가 - 볼린저 하단) / (볼린저 상단 - 볼린저 하단)
    bb_width = df['BB_Upper'] - df['BB_Lower']
    bb_percent_b = (df['Close'] - df['BB_Lower']) / bb_width
    ax3.plot(range(len(df)), bb_percent_b, color='purple', linewidth=1, label='%B')
    ax3.axhline(y=1, color='red', linestyle='--', alpha=0.5, label='Upper Band')
    ax3.axhline(y=0, color='green', linestyle='--', alpha=0.5, label='Lower Band')
    ax3.axhline(y=0.5, color='gray', linestyle='-', alpha=0.3, label='Middle')
    ax3.set_title('Bollinger Band %B')
    ax3.set_ylabel('%B')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 스토캐스틱 %K 차트 (네 번째 패널)
    ax4 = axes[3]
    ax4.plot(range(len(df)), df['Stoch_K'], color='blue', linewidth=1, label='%K')
    ax4.plot(range(len(df)), df['Stoch_D'], color='red', linewidth=1, label='%D')
    ax4.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='Overbought')
    ax4.axhline(y=20, color='green', linestyle='--', alpha=0.5, label='Oversold')
    ax4.set_ylim(0, 100)
    ax4.set_title('Stochastic Slow')
    ax4.set_ylabel('%K/%D')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. 볼린저 밴드 폭 차트 (다섯 번째 패널)
    ax5 = axes[4]
    bb_width_normalized = bb_width / df['BB_Middle'] * 100  # 중간선 대비 폭을 퍼센트로
    ax5.plot(range(len(df)), bb_width_normalized, color='brown', linewidth=1, label='BB Width %')
    ax5.set_title('Bollinger Band Width')
    ax5.set_ylabel('Width %')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 모든 패널의 x축 날짜 설정
    for ax in axes:
        ax.set_xticks([0, len(df)//4, len(df)//2, 3*len(df)//4, len(df)-1])
        ax.set_xticklabels([
            df.index[0].strftime('%Y-%m-%d'),
            df.index[len(df)//4].strftime('%Y-%m-%d'),
            df.index[len(df)//2].strftime('%Y-%m-%d'),
            df.index[3*len(df)//4].strftime('%Y-%m-%d'),
            df.index[-1].strftime('%Y-%m-%d')
        ], rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 차트를 이미지로 저장
    
    # weekly_charts 폴더 생성
    charts_dir = "weekly_charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
        print(f"📁 {charts_dir} 폴더를 생성했습니다.")
    
    # 종목명 가져오기 (yfinance에서) - 코스피/코스닥 자동 구분
    stock_name = stock_code  # 기본값
    tickers_to_try = [
        f"{stock_code}.KS",   # 코스피
        f"{stock_code}.KQ",   # 코스닥
    ]
    
    for ticker in tickers_to_try:
        try:
            stock = yf.Ticker(ticker)
            stock_info = stock.info
            
            # 종목명 우선순위: longName > shortName > 종목코드
            if 'longName' in stock_info and stock_info['longName'] and stock_info['longName'] != 'N/A':
                stock_name = stock_info['longName']
                break
            elif 'shortName' in stock_info and stock_info['shortName'] and stock_info['shortName'] != 'N/A':
                # shortName이 종목코드와 같은 경우는 제외
                if stock_info['shortName'] != stock_code and not stock_info['shortName'].startswith(stock_code):
                    stock_name = stock_info['shortName']
                    break
        except:
            continue
    
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
    """종목코드로 종목명을 가져오는 함수"""
    try:
        # 코스피/코스닥 자동 구분
        tickers_to_try = [
            f"{stock_code}.KS",   # 코스피
            f"{stock_code}.KQ",   # 코스닥
        ]
        
        for ticker in tickers_to_try:
            try:
                stock = yf.Ticker(ticker)
                stock_info = stock.info
                
                # 종목명 우선순위: longName > shortName > 종목코드
                if 'longName' in stock_info and stock_info['longName'] and stock_info['longName'] != 'N/A':
                    return stock_info['longName']
                elif 'shortName' in stock_info and stock_info['shortName'] and stock_info['shortName'] != 'N/A':
                    # shortName이 종목코드와 같은 경우는 제외
                    if stock_info['shortName'] != stock_code and not stock_info['shortName'].startswith(stock_code):
                        return stock_info['shortName']
            except:
                continue
        
        return stock_code  # 기본값
    except:
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