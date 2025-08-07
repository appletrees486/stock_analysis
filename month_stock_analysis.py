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
# openpyxl 관련 import 제거됨 (검토용)

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
    # 이동평균선 (월간 기준)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # CCI (Commodity Channel Index) 계산
    # CCI = (Typical Price - SMA of Typical Price) / (0.015 * Mean Deviation)
    # Typical Price = (High + Low + Close) / 3
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    sma_tp = typical_price.rolling(window=20).mean()
    
    # Mean Deviation 계산
    mean_deviation = typical_price.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
    df['CCI'] = (typical_price - sma_tp) / (0.015 * mean_deviation)
    
    # ADX (Average Directional Index) 계산
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
    
    # 14기간 평균 계산
    period = 14
    atr = true_range.rolling(window=period).mean()
    plus_di = (pd.Series(plus_dm).rolling(window=period).mean() / atr) * 100
    minus_di = (pd.Series(minus_dm).rolling(window=period).mean() / atr) * 100
    
    # DX 계산
    dx = np.abs(plus_di - minus_di) / (plus_di + minus_di) * 100
    
    # ADX 계산 (DX의 14기간 평균)
    df['ADX'] = pd.Series(dx).rolling(window=period).mean()
    df['Plus_DI'] = plus_di
    df['Minus_DI'] = minus_di
    
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
    
    # ADX 정보
    adx_value = df_with_indicators['ADX'].iloc[-1]
    plus_di = df_with_indicators['Plus_DI'].iloc[-1]
    minus_di = df_with_indicators['Minus_DI'].iloc[-1]
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
    """주식 월봉 차트 생성 (캔들차트 + 보조지표)"""
    if hist is None or hist.empty:
        return None
    
    print(f"\n📈 월봉 캔들차트를 생성합니다...")
    
    # 기술적 지표 계산
    df = calculate_technical_indicators(hist.copy())
    df.index.name = 'Date'
    
    # 하나의 큰 차트에 모든 지표 포함
    fig, axes = plt.subplots(5, 1, figsize=(15, 20), height_ratios=[6, 2, 2, 2, 2])
    fig.suptitle(f'{stock_code} Monthly Stock Chart (10 Years) - Technical Indicators', fontsize=16, fontweight='bold')
    
    # 1. 캔들차트 (첫 번째 패널)
    ax1 = axes[0]
    
    # 캔들차트 그리기
    for i, (date, row) in enumerate(df.iterrows()):
        color = 'red' if row['Close'] >= row['Open'] else 'blue'
        ax1.plot([i, i], [row['Low'], row['High']], color=color, linewidth=1)
        ax1.plot([i, i], [row['Open'], row['Close']], color=color, linewidth=3)
    
    # 이동평균선 추가
    ax1.plot(range(len(df)), df['MA5'], color='red', linewidth=1, alpha=0.7, label='MA5')
    ax1.plot(range(len(df)), df['MA10'], color='orange', linewidth=1, alpha=0.7, label='MA10')
    ax1.plot(range(len(df)), df['MA20'], color='green', linewidth=1, alpha=0.7, label='MA20')
    ax1.plot(range(len(df)), df['MA60'], color='purple', linewidth=1, alpha=0.7, label='MA60')
    
    ax1.set_title('Price Chart with Moving Averages')
    ax1.set_ylabel('Price (KRW)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 월봉 거래량 차트 (두 번째 패널)
    ax2 = axes[1]
    ax2.bar(range(len(df)), df['Volume'], color='green', alpha=0.7)
    ax2.set_title('Monthly Volume')
    ax2.set_ylabel('Volume')
    ax2.grid(True, alpha=0.3)
    
    # 3. CCI 차트 (세 번째 패널)
    ax3 = axes[2]
    ax3.plot(range(len(df)), df['CCI'], color='blue', linewidth=1, label='CCI')
    ax3.axhline(y=100, color='red', linestyle='--', alpha=0.5, label='Overbought')
    ax3.axhline(y=-100, color='green', linestyle='--', alpha=0.5, label='Oversold')
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.set_title('CCI (Commodity Channel Index)')
    ax3.set_ylabel('CCI')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. ADX 차트 (네 번째 패널)
    ax4 = axes[3]
    ax4.plot(range(len(df)), df['ADX'], color='purple', linewidth=2, label='ADX')
    ax4.plot(range(len(df)), df['Plus_DI'], color='green', linewidth=1, alpha=0.7, label='+DI')
    ax4.plot(range(len(df)), df['Minus_DI'], color='red', linewidth=1, alpha=0.7, label='-DI')
    ax4.axhline(y=25, color='gray', linestyle='--', alpha=0.5, label='Trend Threshold')
    ax4.set_title('ADX (Average Directional Index)')
    ax4.set_ylabel('ADX/+DI/-DI')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. 이동평균 비교 차트 (다섯 번째 패널)
    ax5 = axes[4]
    ax5.plot(range(len(df)), df['MA5'], color='red', linewidth=1, label='MA5')
    ax5.plot(range(len(df)), df['MA10'], color='orange', linewidth=1, label='MA10')
    ax5.plot(range(len(df)), df['MA20'], color='green', linewidth=1, label='MA20')
    ax5.plot(range(len(df)), df['MA60'], color='purple', linewidth=1, label='MA60')
    ax5.set_title('Moving Averages Comparison')
    ax5.set_ylabel('Price (KRW)')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 모든 패널의 x축 날짜 설정
    for ax in axes:
        ax.set_xticks([0, len(df)//4, len(df)//2, 3*len(df)//4, len(df)-1])
        ax.set_xticklabels([
            df.index[0].strftime('%Y-%m'),
            df.index[len(df)//4].strftime('%Y-%m'),
            df.index[len(df)//2].strftime('%Y-%m'),
            df.index[3*len(df)//4].strftime('%Y-%m'),
            df.index[-1].strftime('%Y-%m')
        ], rotation=45, ha='right')
    
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
    
    return filepath
    
    # 이동평균 신호 분석
    current_price = hist['Close'].iloc[-1]
    print(f"\n📈 이동평균 신호 분석:")
    print("-" * 50)
    
    if 'MA5' in df.columns and 'MA10' in df.columns and 'MA20' in df.columns and 'MA60' in df.columns:
        ma5 = df['MA5'].iloc[-1]
        ma10 = df['MA10'].iloc[-1]
        ma20 = df['MA20'].iloc[-1]
        ma60 = df['MA60'].iloc[-1]
        
        if current_price > ma5 and ma5 > ma10 and ma10 > ma20 and ma20 > ma60:
            print("✅ 강한 상승 추세: 현재가 > 5개월선 > 10개월선 > 20개월선 > 60개월선")
        elif current_price > ma5 and ma5 > ma10 and ma10 > ma20:
            print("📈 상승 추세: 현재가 > 5개월선 > 10개월선 > 20개월선")
        elif current_price < ma5 and ma5 < ma10 and ma10 < ma20 and ma20 < ma60:
            print("🔻 강한 하락 추세: 현재가 < 5개월선 < 10개월선 < 20개월선 < 60개월선")
        elif current_price < ma5 and ma5 < ma10 and ma10 < ma20:
            print("📉 하락 추세: 현재가 < 5개월선 < 10개월선 < 20개월선")
        else:
            print("🔄 혼조세: 이동평균선이 교차하는 구간")
    
    # 월봉 캔들차트 패턴 분석
    print(f"\n🕯️ 월봉 캔들차트 패턴 분석:")
    print("-" * 50)
    
    # 최근 3개월간의 월봉 캔들 패턴 분석
    recent_data = hist.tail(3)
    for i, (date, row) in enumerate(recent_data.iterrows()):
        body_size = abs(row['Close'] - row['Open'])
        total_range = row['High'] - row['Low']
        body_ratio = body_size / total_range if total_range > 0 else 0
        
        if row['Close'] > row['Open']:
            candle_type = "양봉"
            if body_ratio > 0.7:
                pattern = "강한 상승"
            elif body_ratio > 0.4:
                pattern = "일반 상승"
            else:
                pattern = "약한 상승"
        else:
            candle_type = "음봉"
            if body_ratio > 0.7:
                pattern = "강한 하락"
            elif body_ratio > 0.4:
                pattern = "일반 하락"
            else:
                pattern = "약한 하락"
        
        print(f"{date.strftime('%Y-%m')}: {candle_type} ({pattern}) - 시가: {row['Open']:,.0f}, 종가: {row['Close']:,.0f}")

# 엑셀 저장 기능 제거됨 (검토용)

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
        
        # 월봉 차트 생성
        create_monthly_stock_chart(hist, stock_code)
        
        # 월봉 데이터를 엑셀로 저장
        # 엑셀 저장 기능 제거됨 (검토용)
        
        print("\n✅ 월봉 분석이 완료되었습니다!")
    else:
        print("\n❌ 월봉 데이터 조회에 실패했습니다.")

if __name__ == "__main__":
    main() 