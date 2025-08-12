#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국내 주식 월봉 시세 조회 스크립트
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

def get_monthly_stock_data(stock_code):
    """국내 주식 월봉 데이터 조회 (10년) - 네이버 금융 우선, Yahoo Finance 보조"""
    print(f"🔍 {stock_code} 10년 월봉 시세 조회 중...")
    print("   📅 월봉 데이터는 거래일 기준으로 제공되며, 월말 기준으로 집계됩니다.")
    
    # 네이버 금융 데이터 조회 (우선)
    print("   🔄 네이버 금융에서 실시간 데이터 확인 중...")
    from naver_data_module import get_naver_stock_data, get_naver_historical_data
    
    naver_result = get_naver_stock_data(stock_code)
    if naver_result['success']:
        print(f"   ✅ 네이버 금융 실시간 데이터: {naver_result['stock_name']}")
        print(f"   📈 현재가: {naver_result['current_price']:,.0f}원")
        print(f"   📊 변동: {naver_result['change_direction']} {naver_result['change_amount']:+,}원")
        print(f"   ⏰ 조회시간: {naver_result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Yahoo Finance에서 월봉 데이터 조회 (주 데이터)
    yf_monthly_data = None
    tickers_to_try = [
        f"{stock_code}.KS",   # 코스피
        f"{stock_code}.KQ",   # 코스닥 (일부)
        f"{stock_code}.KS",   # 다시 시도
    ]
    
    for i, ticker in enumerate(tickers_to_try):
        try:
            print(f"   시도 {i+1}: {ticker}")
            stock = yf.Ticker(ticker)
            # 10년 월봉 데이터 조회
            hist = stock.history(period="10y", interval="1mo")
            
            if not hist.empty:
                print(f"✅ Yahoo Finance 월봉: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')} 기간 월봉 데이터를 조회했습니다.")
                print(f"📅 총 {len(hist)}개월의 월봉 거래 데이터를 가져왔습니다.")
                print(f"🏢 사용된 티커: {ticker}")
                yf_monthly_data = hist
                break
                
        except Exception as e:
            print(f"   ❌ {ticker} 시도 실패: {str(e)[:50]}...")
            continue
    
    # Yahoo Finance 월봉 데이터가 있는 경우 최신도 확인
    if yf_monthly_data is not None:
        # 최신 데이터 확인 (현재 날짜와 비교)
        latest_monthly_date = yf_monthly_data.index[-1]
        # 타임존 정보 제거
        if hasattr(latest_monthly_date, 'tz_localize'):
            latest_monthly_date = latest_monthly_date.tz_localize(None)
        elif hasattr(latest_monthly_date, 'replace'):
            latest_monthly_date = latest_monthly_date.replace(tzinfo=None)
        
        current_date = datetime.now()
        days_diff = (current_date - latest_monthly_date).days
        
        print(f"   📅 Yahoo Finance 월봉 최신 데이터: {latest_monthly_date.strftime('%Y-%m-%d')}")
        print(f"   📅 현재 날짜: {current_date.strftime('%Y-%m-%d')}")
        print(f"   📅 데이터 차이: {days_diff}일")
        
        # 7일 이상 차이나면 일봉 데이터로 최신 월봉 보완
        if days_diff > 7:
            print(f"   ⚠️ Yahoo Finance 월봉 데이터가 {days_diff}일 전 데이터입니다.")
            print(f"   🔄 Yahoo Finance 일봉 데이터로 최신 월봉을 보완합니다...")
            
            # Yahoo Finance에서 일봉 데이터 조회 (최근 90일)
            try:
                daily_hist = stock.history(period="90d", interval="1d")
                if not daily_hist.empty:
                    print(f"   ✅ Yahoo Finance 일봉: {daily_hist.index[0].strftime('%Y-%m-%d')} ~ {daily_hist.index[-1].strftime('%Y-%m-%d')}")
                    print(f"   📊 일봉 데이터 상세:")
                    for i, (date, row) in enumerate(daily_hist.tail(5).iterrows()):
                        print(f"      {date.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f}")
                    
                    # 일봉을 월봉으로 변환
                    enhanced_monthly_data = convert_daily_to_monthly(daily_hist, yf_monthly_data)
                    if enhanced_monthly_data is not None:
                        print(f"   ✅ 일봉 데이터로 월봉을 보완했습니다!")
                        print(f"   📅 최신 월봉 데이터: {enhanced_monthly_data.index[-1].strftime('%Y-%m-%d')}")
                        return enhanced_monthly_data
                    else:
                        print(f"   ⚠️ 일봉 데이터 변환에 실패하여 기존 월봉 데이터를 사용합니다.")
                else:
                    print(f"   ⚠️ Yahoo Finance 일봉 데이터를 가져올 수 없어 기존 월봉 데이터를 사용합니다.")
            except Exception as e:
                print(f"   ❌ Yahoo Finance 일봉 데이터 조회 실패: {str(e)[:50]}...")
        
        return yf_monthly_data
    
    # Yahoo Finance에서 월봉 데이터를 가져올 수 없는 경우
    print("   ⚠️ Yahoo Finance에서 월봉 데이터를 가져올 수 없습니다.")
    print("   🔄 Yahoo Finance 일봉 데이터로 월봉을 생성합니다...")
    
    # Yahoo Finance에서 일봉 데이터로 월봉 생성 시도
    for ticker in tickers_to_try:
        try:
            stock = yf.Ticker(ticker)
            # 10년 일봉 데이터 조회
            daily_hist = stock.history(period="10y", interval="1d")
            if not daily_hist.empty:
                print(f"   ✅ Yahoo Finance 일봉: {daily_hist.index[0].strftime('%Y-%m-%d')} ~ {daily_hist.index[-1].strftime('%Y-%m-%d')}")
                
                # 일봉을 월봉으로 변환
                monthly_from_daily = convert_daily_to_monthly(daily_hist, None)
                if monthly_from_daily is not None:
                    print(f"   ✅ 일봉 데이터로 월봉을 생성했습니다!")
                    return monthly_from_daily
                break
        except Exception as e:
            print(f"   ❌ {ticker} 일봉 시도 실패: {str(e)[:50]}...")
            continue
    
    # 모든 소스에서 실패
    print("❌ 월봉 데이터 조회에 실패했습니다.")
    print("💡 가능한 원인:")
    print("   - 종목코드가 잘못되었습니다")
    print("   - 해당 종목이 상장폐지되었습니다")
    print("   - Yahoo Finance에서 지원하지 않는 종목입니다")
    return None

def convert_daily_to_monthly(daily_data, existing_monthly_data=None):
    """일봉 데이터를 월봉으로 변환 (미완성 월 포함)"""
    try:
        # 일봉 데이터를 월별로 그룹화
        daily_data_copy = daily_data.copy()
        daily_data_copy.index.name = 'Date'
        
        # 현재 날짜 확인
        current_date = datetime.now().date()
        
        # 월별로 그룹화
        daily_data_copy['Month'] = daily_data_copy.index.to_period('M')
        
        monthly_data = []
        
        for month, group in daily_data_copy.groupby('Month'):
            if len(group) > 0:
                # 월봉 데이터 계산
                month_start = group.index[0]
                
                # 미완성 월인지 확인 (현재 월인 경우)
                is_current_month = False
                if hasattr(month_start, 'date'):
                    month_start_date = month_start.date()
                else:
                    month_start_date = month_start
                
                # 현재 월인지 확인
                current_month_start = current_date.replace(day=1)
                if month_start_date.month == current_date.month and month_start_date.year == current_date.year:
                    is_current_month = True
                    print(f"   📅 현재 월 감지: {month_start_date.strftime('%Y-%m')}")
                
                # 현재 월인 경우 실제 마지막 거래일을 날짜로 사용
                if is_current_month:
                    # 현재 월의 실제 마지막 거래일 찾기
                    last_trading_day = group.index[-1]
                    actual_close = group['Close'].iloc[-1]
                    print(f"      📅 현재 월 마지막 거래일: {last_trading_day.strftime('%Y-%m-%d')}, 종가: {actual_close:,.0f}")
                    
                    # 현재 월은 실제 마지막 거래일을 날짜로 사용
                    monthly_data.append({
                        'Date': last_trading_day,       # 실제 마지막 거래일
                        'Open': group['Open'].iloc[0],  # 월 첫날 시가
                        'High': group['High'].max(),    # 월 최고가
                        'Low': group['Low'].min(),      # 월 최저가
                        'Close': actual_close,          # 실제 마지막 거래일 종가
                        'Volume': group['Volume'].sum(), # 월 총 거래량
                        'IsCurrentMonth': is_current_month # 현재 월 여부
                    })
                else:
                    # 완성된 월은 기존 방식
                    monthly_data.append({
                        'Date': month_start,
                        'Open': group['Open'].iloc[0],      # 월 첫날 시가
                        'High': group['High'].max(),        # 월 최고가
                        'Low': group['Low'].min(),          # 월 최저가
                        'Close': group['Close'].iloc[-1],   # 월 마지막날 종가
                        'Volume': group['Volume'].sum(),    # 월 총 거래량
                        'IsCurrentMonth': is_current_month  # 현재 월 여부
                    })
        
        if not monthly_data:
            print("   ❌ 월봉 데이터 변환에 실패했습니다.")
            return None
        
        # 월봉 DataFrame 생성
        monthly_df = pd.DataFrame(monthly_data)
        monthly_df.set_index('Date', inplace=True)
        monthly_df.sort_index(inplace=True)
        
        # 현재 월이 있는지 확인
        current_months = monthly_df[monthly_df['IsCurrentMonth'] == True]
        if not current_months.empty:
            print(f"   ✅ 현재 월 포함: {len(current_months)}개월")
            for idx, row in current_months.iterrows():
                print(f"      📅 {idx.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f}")
        
        # IsCurrentMonth 컬럼 제거 (분석에 불필요)
        monthly_df = monthly_df.drop('IsCurrentMonth', axis=1)
        
        # 기존 월봉 데이터가 있는 경우 병합
        if existing_monthly_data is not None:
            # 중복 제거하고 병합
            combined_data = pd.concat([existing_monthly_data, monthly_df])
            combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
            combined_data.sort_index(inplace=True)
            
            print(f"   📅 기존 월봉: {len(existing_monthly_data)}개월 + 신규 월봉: {len(monthly_df)}개월 = 총 {len(combined_data)}개월")
            return combined_data
        else:
            print(f"   📅 일봉에서 생성된 월봉: {len(monthly_df)}개월")
            return monthly_df
            
    except Exception as e:
        print(f"   ❌ 일봉을 월봉으로 변환하는 중 오류 발생: {str(e)}")
        return None

def calculate_technical_indicators(df):
    """기술적 지표 계산"""
    print(f"   🔧 기술적 지표 계산 시작 (데이터 수: {len(df)}개월)")
    
    # 이동평균선 (월간 기준)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 볼린저 밴드 계산 (20개월 기준)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # CCI (Commodity Channel Index) 계산
    # CCI = (Typical Price - SMA of Typical Price) / (0.015 * Mean Deviation)
    # Typical Price = (High + Low + Close) / 3
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    sma_tp = typical_price.rolling(window=20).mean()
    
    # Mean Deviation 계산
    mean_deviation = typical_price.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
    df['CCI'] = (typical_price - sma_tp) / (0.015 * mean_deviation)
    
    # ADX (Average Directional Index) 계산
    print(f"   📊 ADX 계산 시작 (기간: {min(14, len(df) // 2)}개월)")
    
    # +DM, -DM 계산
    high_diff = df['High'].diff()
    low_diff = df['Low'].diff()
    
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), -low_diff, 0)
    
    # True Range 계산
    tr1 = df['High'] - df['Low']
    tr2 = np.abs(df['High'] - df['Close'].shift(1))
    tr3 = np.abs(df['Low'] - df['Close'].shift(1))
    true_range = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # 14기간 평균 계산 (월봉 데이터 특성을 고려하여 조정)
    period = min(14, len(df) // 2)  # 데이터가 적은 경우 기간 조정
    if period < 5:
        period = 5  # 최소 5기간 보장
    
    print(f"   📊 ADX 계산 기간: {period}개월")
    
    # ATR 계산 (0으로 나누기 방지)
    atr = true_range.rolling(window=period).mean()
    atr = atr.replace(0, np.nan)  # 0값을 NaN으로 변경
    
    # +DI, -DI 계산 (0으로 나누기 방지)
    plus_dm_avg = pd.Series(plus_dm).rolling(window=period).mean()
    minus_dm_avg = pd.Series(minus_dm).rolling(window=period).mean()
    
    # pandas Series로 변환하여 계산
    plus_di = pd.Series(index=df.index, dtype=float)
    minus_di = pd.Series(index=df.index, dtype=float)
    
    # 0으로 나누기 방지하면서 계산
    for i in range(len(df)):
        if pd.notna(atr.iloc[i]) and atr.iloc[i] > 0:
            plus_di.iloc[i] = (plus_dm_avg.iloc[i] / atr.iloc[i]) * 100
            minus_di.iloc[i] = (minus_dm_avg.iloc[i] / atr.iloc[i]) * 100
        else:
            plus_di.iloc[i] = 0
            minus_di.iloc[i] = 0
    
    # DX 계산 (0으로 나누기 방지)
    dx = pd.Series(index=df.index, dtype=float)
    
    for i in range(len(df)):
        di_sum = plus_di.iloc[i] + minus_di.iloc[i]
        if di_sum > 0:
            dx.iloc[i] = abs(plus_di.iloc[i] - minus_di.iloc[i]) / di_sum * 100
        else:
            dx.iloc[i] = 0
    
    # ADX 계산 (DX의 평균)
    df['ADX'] = pd.Series(dx).rolling(window=period).mean()
    df['Plus_DI'] = plus_di
    df['Minus_DI'] = minus_di
    
    # NaN 값 처리
    df['ADX'] = df['ADX'].fillna(0)
    df['Plus_DI'] = df['Plus_DI'].fillna(0)
    df['Minus_DI'] = df['Minus_DI'].fillna(0)
    
    # ADX 계산 결과 확인
    valid_adx_count = df['ADX'].notna().sum()
    print(f"   ✅ ADX 계산 완료: {valid_adx_count}/{len(df)}개월 유효한 값")
    if valid_adx_count > 0:
        print(f"   📊 최근 ADX 값: {df['ADX'].iloc[-1]:.1f}")
        print(f"   📊 최근 +DI 값: {df['Plus_DI'].iloc[-1]:.1f}")
        print(f"   📊 최근 -DI 값: {df['Minus_DI'].iloc[-1]:.1f}")
    else:
        print(f"   ⚠️ ADX 계산 실패: 모든 값이 NaN입니다")
    
    return df

def analyze_monthly_stock_data(hist, stock_code):
    """주식 월봉 데이터 분석"""
    if hist is None or hist.empty:
        return
    
    print("\n" + "="*60)
    print(f"📊 {stock_code} 주식 월봉 분석 결과")
    print("="*60)
    
    # 기본 통계
    print(f"📅 조회 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
    print(f"📈 월봉 거래월 수: {len(hist)}개월")
    
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
    
    # 월봉 거래량 정보
    print(f"\n📈 월봉 거래량 정보:")
    print(f"   평균 월봉 거래량: {hist['Volume'].mean():,.0f}주")
    print(f"   최대 월봉 거래량: {hist['Volume'].max():,.0f}주")
    print(f"   최소 월봉 거래량: {hist['Volume'].min():,.0f}주")
    
    # 기술적 지표 계산
    df_with_indicators = calculate_technical_indicators(hist.copy())
    
    # 기술적 지표 정보
    print(f"\n📊 기술적 지표 (최근값):")
    print(f"   5개월 이동평균: {df_with_indicators['MA5'].iloc[-1]:,.0f}원")
    print(f"   10개월 이동평균: {df_with_indicators['MA10'].iloc[-1]:,.0f}원")
    print(f"   20개월 이동평균: {df_with_indicators['MA20'].iloc[-1]:,.0f}원")
    print(f"   60개월 이동평균: {df_with_indicators['MA60'].iloc[-1]:,.0f}원")
    
    # CCI 정보
    cci_value = df_with_indicators['CCI'].iloc[-1]
    print(f"   CCI: {cci_value:.1f}")
    if cci_value > 100:
        print("   CCI 신호: 과매수 구간")
    elif cci_value < -100:
        print("   CCI 신호: 과매도 구간")
    else:
        print("   CCI 신호: 중립 구간")
    
    # ADX 정보 (NaN 체크 추가)
    adx_value = df_with_indicators['ADX'].iloc[-1]
    plus_di = df_with_indicators['Plus_DI'].iloc[-1]
    minus_di = df_with_indicators['Minus_DI'].iloc[-1]
    
    # ADX 값이 유효한지 확인
    if pd.isna(adx_value) or pd.isna(plus_di) or pd.isna(minus_di):
        print("   ⚠️ ADX 계산 중 일부 값이 NaN입니다. 데이터를 확인해주세요.")
        print(f"   ADX: {adx_value}")
        print(f"   +DI: {plus_di}")
        print(f"   -DI: {minus_di}")
    else:
        print(f"   ADX: {adx_value:.1f}")
        print(f"   +DI: {plus_di:.1f}")
        print(f"   -DI: {minus_di:.1f}")
        
        if adx_value > 25:
            if plus_di > minus_di:
                print("   ADX 신호: 강한 상승 추세")
            else:
                print("   ADX 신호: 강한 하락 추세")
        else:
            print("   ADX 신호: 약한 추세 (추세 없음)")

def create_monthly_stock_chart(hist, stock_code):
    """주식 월봉 차트 생성 (캔들차트 + 보조지표) - test_overlay_chart.py 스타일 적용"""
    if hist is None or hist.empty:
        return None, None
    
    print(f"\n📈 월봉 캔들차트를 생성합니다...")
    
    # 기술적 지표 계산
    df = calculate_technical_indicators(hist.copy())
    df.index.name = 'Date'
    
    # 차트 생성 (4개 패널: 메인차트, 거래량, CCI, ADX)
    fig, axes = plt.subplots(4, 1, figsize=(15, 16), height_ratios=[8, 2, 2, 2])
    fig.suptitle(f'{stock_code} Monthly Stock Chart (10 Years) - Image Reference Style', fontsize=16, fontweight='bold')
    
    # 1. 메인 차트 (캔들차트 + 보조지표 오버레이)
    ax1 = axes[0]
    
    # 볼린저 밴드 영역 채우기 (이미지 참고 - 오렌지/베이지 스타일)
    ax1.fill_between(range(len(df)), df['BB_Upper'], df['BB_Lower'], 
                     alpha=0.15, color='#FFE4B5', label='Bollinger Bands')
    
    # 볼린저 밴드 상단과 하단을 오렌지/베이지 색으로 표시 (범례에 표시하지 않음)
    ax1.plot(range(len(df)), df['BB_Upper'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    ax1.plot(range(len(df)), df['BB_Lower'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    
    # 캔들차트 그리기 (이미지 참고 - 빨간색/파란색)
    for i, (date, row) in enumerate(df.iterrows()):
        if row['Close'] >= row['Open']:  # 상승
            color = '#FF4444'  # 빨간색
        else:  # 하락
            color = '#4444FF'  # 파란색
        
        ax1.plot([i, i], [row['Low'], row['High']], color=color, linewidth=1.0)
        ax1.plot([i, i], [row['Open'], row['Close']], color=color, linewidth=3.0)
    
    # 이동평균선 추가 (웹 트레이딩 스타일 유지)
    ax1.plot(range(len(df)), df['MA5'], color='#F59E0B', linewidth=2.0, alpha=0.9, label='MA5')
    ax1.plot(range(len(df)), df['MA20'], color='#8B5CF6', linewidth=2.0, alpha=0.9, label='MA20')
    ax1.plot(range(len(df)), df['MA60'], color='#06B6D4', linewidth=2.0, alpha=0.9, label='MA60')
    
    # 메인 차트 설정
    ax1.set_title('Price Chart with Moving Averages', fontsize=14, fontweight='bold')
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
    
    ax2.bar(range(len(df)), df['Volume'], color=colors, alpha=0.7, width=0.8)
    ax2.set_title('Volume', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Volume', fontsize=10, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax2.yaxis.set_label_position('right')
    ax2.yaxis.tick_right()
    
    # 3. CCI 차트 (세 번째 패널) - 웹 트레이딩 스타일 유지
    ax3 = axes[2]
    ax3.plot(range(len(df)), df['CCI'], color='#3B82F6', linewidth=2.0, label='CCI')
    ax3.axhline(y=100, color='#EF4444', linestyle='--', alpha=0.8, linewidth=1.5, label='Overbought')
    ax3.axhline(y=-100, color='#10B981', linestyle='--', alpha=0.8, linewidth=1.5, label='Oversold')
    ax3.axhline(y=0, color='#6B7280', linestyle='-', alpha=0.6, linewidth=1.0, label='Neutral')
    ax3.set_title('CCI (Commodity Channel Index)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('CCI', fontsize=10, fontweight='bold')
    ax3.legend(fontsize=10, framealpha=0.9)
    ax3.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax3.yaxis.set_label_position('right')
    ax3.yaxis.tick_right()
    
    # 4. ADX 차트 (네 번째 패널) - 웹 트레이딩 스타일 유지
    ax4 = axes[3]
    
    # ADX 값이 유효한지 확인하고 플롯
    if not df['ADX'].isna().all() and not df['Plus_DI'].isna().all() and not df['Minus_DI'].isna().all():
        ax4.plot(range(len(df)), df['ADX'], color='#8B5CF6', linewidth=2.5, label='ADX')
        ax4.plot(range(len(df)), df['Plus_DI'], color='#10B981', linewidth=2.0, alpha=0.8, label='+DI')
        ax4.plot(range(len(df)), df['Minus_DI'], color='#EF4444', linewidth=2.0, alpha=0.8, label='-DI')
        ax4.axhline(y=25, color='#6B7280', linestyle='--', alpha=0.8, linewidth=1.5, label='Trend Threshold')
        ax4.set_title('ADX (Average Directional Index)', fontsize=12, fontweight='bold')
        ax4.set_ylabel('ADX/+DI/-DI', fontsize=10, fontweight='bold')
        ax4.legend(fontsize=10, framealpha=0.9)
        ax4.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    else:
        # ADX 데이터가 유효하지 않은 경우 메시지 표시
        ax4.text(0.5, 0.5, 'ADX 데이터를 계산할 수 없습니다\n(데이터가 부족하거나 오류가 발생했습니다)', 
                transform=ax4.transAxes, ha='center', va='center', fontsize=12)
        ax4.set_title('ADX (Average Directional Index) - 데이터 오류', fontsize=12, fontweight='bold')
        ax4.set_ylabel('ADX/+DI/-DI', fontsize=10, fontweight='bold')
        ax4.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax4.yaxis.set_label_position('right')
    ax4.yaxis.tick_right()
    
    # X축 날짜 설정 - 하단에만 표시
    for i, ax in enumerate(axes):
        if i == len(axes) - 1:  # 마지막 패널에만 날짜 표시
            ax.set_xticks([0, len(df)//4, len(df)//2, 3*len(df)//4, len(df)-1])
            ax.set_xticklabels([
                df.index[0].strftime('%Y-%m'),
                df.index[len(df)//4].strftime('%Y-%m'),
                df.index[len(df)//2].strftime('%Y-%m'),
                df.index[3*len(df)//4].strftime('%Y-%m'),
                df.index[-1].strftime('%Y-%m')
            ], rotation=45, ha='right', fontweight='bold')
        else:
            ax.set_xticks([])  # 다른 패널은 X축 눈금 숨김
    
    plt.tight_layout()
    
    # 차트를 이미지로 저장
    
    # monthly_charts 폴더 생성
    charts_dir = "monthly_charts"
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
    
    # 파일명 생성: monthly_종목명_종목번호_생성일.png
    current_date = datetime.now().strftime("%Y%m%d")
    base_filename = f"monthly_{stock_name}_{stock_code}_{current_date}.png"
    
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
        filename = f"monthly_{stock_name}_{stock_code}_{current_date}.json"
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
                "chart_type": "monthly"
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
                    "ma10": float(chart_data_clean['MA10'].iloc[-1]) if 'MA10' in chart_data_clean else None,
                    "ma20": float(chart_data_clean['MA20'].iloc[-1]) if 'MA20' in chart_data_clean else None,
                    "ma60": float(chart_data_clean['MA60'].iloc[-1]) if 'MA60' in chart_data_clean else None,
                    "cci": float(chart_data_clean['CCI'].iloc[-1]) if 'CCI' in chart_data_clean else None,
                    "adx": float(chart_data_clean['ADX'].iloc[-1]) if 'ADX' in chart_data_clean else None,
                    "plus_di": float(chart_data_clean['Plus_DI'].iloc[-1]) if 'Plus_DI' in chart_data_clean else None,
                    "minus_di": float(chart_data_clean['Minus_DI'].iloc[-1]) if 'Minus_DI' in chart_data_clean else None
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
            if 'MA10' in row:
                data_point["ma10"] = float(row['MA10'])
            if 'MA20' in row:
                data_point["ma20"] = float(row['MA20'])
            if 'MA60' in row:
                data_point["ma60"] = float(row['MA60'])
            if 'CCI' in row:
                data_point["cci"] = float(row['CCI'])
            if 'ADX' in row:
                data_point["adx"] = float(row['ADX'])
            if 'Plus_DI' in row:
                data_point["plus_di"] = float(row['Plus_DI'])
            if 'Minus_DI' in row:
                data_point["minus_di"] = float(row['Minus_DI'])
            
            json_data["chart_data"].append(data_point)
        
        # JSON 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 JSON 파일이 저장되었습니다: {filepath}")
        print(f"📊 데이터 구조:")
        print(f"   - 메타데이터: 종목 정보, 생성일시, 데이터 기간")
        print(f"   - 요약 정보: 최근 가격, 변동률, 거래량 통계")
        print(f"   - 기술적 지표: 최신 보조지표 값들")
        print(f"   - 차트 데이터: 최근 30개 거래월 OHLCV + 지표")
        
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
        filename = f"monthly_{stock_name}_{stock_code}_{current_date}.csv"
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
        print(f"📊 데이터: 최근 50개 거래월 OHLCV + 기술적 지표")
        
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
        filename = f"monthly_{stock_name}_{stock_code}_{current_date}_summary.txt"
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
        summary_text = f"""주식 월봉 차트 데이터 요약
========================

종목 정보:
- 종목명: {stock_name}
- 종목코드: {stock_code}
- 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 데이터 기간: {chart_data.index[0].strftime('%Y-%m-%d')} ~ {chart_data.index[-1].strftime('%Y-%m-%d')}
- 총 데이터 수: {len(chart_data)}개월

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
            summary_text += f"- 5개월 이동평균: {chart_data['MA5'].iloc[-1]:,.0f}원\n"
        if 'MA10' in chart_data:
            summary_text += f"- 10개월 이동평균: {chart_data['MA10'].iloc[-1]:,.0f}원\n"
        if 'MA20' in chart_data:
            summary_text += f"- 20개월 이동평균: {chart_data['MA20'].iloc[-1]:,.0f}원\n"
        if 'MA60' in chart_data:
            summary_text += f"- 60개월 이동평균: {chart_data['MA60'].iloc[-1]:,.0f}원\n"
        if 'CCI' in chart_data:
            summary_text += f"- CCI: {chart_data['CCI'].iloc[-1]:.1f}\n"
        if 'ADX' in chart_data:
            summary_text += f"- ADX: {chart_data['ADX'].iloc[-1]:.1f}\n"
        if 'Plus_DI' in chart_data:
            summary_text += f"- +DI: {chart_data['Plus_DI'].iloc[-1]:.1f}\n"
        if 'Minus_DI' in chart_data:
            summary_text += f"- -DI: {chart_data['Minus_DI'].iloc[-1]:.1f}\n"
        
        summary_text += f"""
최근 10개 거래월 데이터:
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
        base_filename = f"monthly_chart_data_{stock_name}_{stock_code}_{current_date}.xlsx"
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
            ["최근 CCI", f"{chart_data_clean['CCI'].iloc[-1]:.1f}"],
            ["최근 ADX", f"{chart_data_clean['ADX'].iloc[-1]:.1f}"],
            ["5개월 이동평균", f"{chart_data_clean['MA5'].iloc[-1]:,.0f}원"],
            ["10개월 이동평균", f"{chart_data_clean['MA10'].iloc[-1]:,.0f}원"],
            ["20개월 이동평균", f"{chart_data_clean['MA20'].iloc[-1]:,.0f}원"],
            ["60개월 이동평균", f"{chart_data_clean['MA60'].iloc[-1]:,.0f}원"],
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
    print("🚀 국내 주식 월봉 시세 조회 프로그램 (10년)")
    print("="*60)
    
    # 종목코드 입력
    while True:
        stock_code = input("📈 종목코드를 입력하세요 (예: 005930): ").strip()
        if stock_code.isdigit() and len(stock_code) == 6:
            break
        else:
            print("❌ 올바른 종목코드를 입력해주세요 (6자리 숫자)")
    
    # 월봉 데이터 조회
    hist = get_monthly_stock_data(stock_code)
    
    if hist is not None:
        # 월봉 데이터 분석
        analyze_monthly_stock_data(hist, stock_code)
        
        # 월봉 차트 생성 (차트 데이터 반환)
        chart_path, chart_data = create_monthly_stock_chart(hist, stock_code)
        
        if chart_path and chart_data is not None:
            # 종목명 가져오기
            stock_name = stock_code
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
            
            # JSON 저장 (추천)
            json_path = save_chart_data_to_json(chart_data, stock_code, stock_name)
            
            # CSV 저장 (보조)
            csv_path = save_chart_data_to_csv(chart_data, stock_code, stock_name)
            
            # 텍스트 요약 저장 (보조)
            text_path = save_chart_summary_to_text(chart_data, stock_code, stock_name)
            
            if json_path:
                print(f"\n✅ 월봉 분석이 완료되었습니다!")
                print(f"📈 차트 이미지: {chart_path}")
                print(f"📊 JSON 데이터: {json_path}")
                if csv_path:
                    print(f"📋 CSV 데이터: {csv_path}")
                if text_path:
                    print(f"📝 텍스트 요약: {text_path}")
                print(f"\n💡 이제 AI 분석에 차트 이미지와 JSON 데이터를 함께 전달할 수 있습니다!")
            else:
                print(f"\n✅ 월봉 분석이 완료되었습니다!")
                print(f"📈 차트 이미지: {chart_path}")
                print(f"❌ 데이터 파일 저장에 실패했습니다.")
        else:
            print(f"\n❌ 차트 생성에 실패했습니다.")
    else:
        print("\n❌ 월봉 데이터 조회에 실패했습니다.")

if __name__ == "__main__":
    main() 