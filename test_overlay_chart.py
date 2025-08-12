#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오버레이 차트 테스트 스크립트 - 종목코드 019210 (YG-1) 테스트
"""

# matplotlib 백엔드를 Agg로 설정 (tkinter 에러 방지)
import matplotlib
matplotlib.use('Agg')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import os
import yfinance as yf

# 운영체제별 한글 폰트 설정
system = platform.system()
if system == 'Windows':
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
    plt.rcParams['font.family'] = 'DejaVu Sans'
    print("⚠️ 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")

plt.rcParams['axes.unicode_minus'] = False

def get_stock_data_019210():
    """종목코드 019210 (YG-1) 실제 데이터 조회"""
    print("🔍 종목코드 019210 (YG-1) 데이터를 조회합니다...")
    
    try:
        # Yahoo Finance에서 데이터 조회
        ticker_symbol = "019210.KS"
        ticker = yf.Ticker(ticker_symbol)
        
        # 1년 데이터 조회 (240일보다 충분)
        hist = ticker.history(period="1y")
        
        if not hist.empty:
            print(f"✅ Yahoo Finance 데이터 조회 성공")
            print(f"📅 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
            print(f"📊 데이터 수: {len(hist)}일")
            print(f"🏢 종목명: {ticker.info.get('longName', 'YG-1')}")
            
            # 최근 5일 데이터 출력
            print(f"📊 최근 일봉 데이터:")
            for i, (date, row) in enumerate(hist.tail(5).iterrows()):
                print(f"   {date.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f} (거래량: {row['Volume']:,.0f})")
            
            return hist
        else:
            print("❌ 데이터 조회 실패")
            return None
            
    except Exception as e:
        print(f"❌ 데이터 조회 중 오류: {str(e)}")
        return None

def calculate_technical_indicators(df):
    """기술적 지표 계산 (볼린저 밴드 추가)"""
    print("🔧 기술적 지표를 계산합니다...")
    
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
    
    # RSI 계산
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
    
    # MACD 계산
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
    
    print("✅ 기술적 지표 계산 완료")
    return df

def create_overlay_chart(df, stock_code="019210", stock_name="YG-1"):
    """일봉 오버레이 차트 생성 - 이미지 참고하여 볼린저 밴드 색상 복원"""
    print(f"\n📈 일봉 오버레이 차트를 생성합니다...")
    
    # 기술적 지표 계산
    df = calculate_technical_indicators(df.copy())
    
    # 차트 생성 (4개 패널: 메인차트, 거래량, RSI, MACD)
    fig, axes = plt.subplots(4, 1, figsize=(15, 16), height_ratios=[8, 2, 2, 2])
    fig.suptitle(f'{stock_name} ({stock_code}) Daily Stock Chart - Image Reference Style', fontsize=16, fontweight='bold')
    
    # 1. 메인 차트 (캔들차트 + 보조지표 오버레이)
    ax1 = axes[0]
    
    # 볼린저 밴드 영역 채우기 (이미지 참고 - 오렌지/베이지 스타일)
    ax1.fill_between(df.index, df['BB_Upper'], df['BB_Lower'], 
                     alpha=0.15, color='#FFE4B5', label='Bollinger Bands')
    
    # 볼린저 밴드 상단과 하단을 오렌지/베이지 색으로 표시 (범례에 표시하지 않음)
    ax1.plot(df.index, df['BB_Upper'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    ax1.plot(df.index, df['BB_Lower'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    
    # 캔들차트 그리기 (이미지 참고 - 빨간색/파란색)
    for date, row in df.iterrows():
        if row['Close'] >= row['Open']:  # 상승
            color = '#FF4444'  # 빨간색
        else:  # 하락
            color = '#4444FF'  # 파란색
        
        ax1.plot([date, date], [row['Low'], row['High']], color=color, linewidth=1.0)
        ax1.plot([date, date], [row['Open'], row['Close']], color=color, linewidth=3.0)
    
    # 이동평균선 추가 (웹 트레이딩 스타일 유지)
    ax1.plot(df.index, df['MA5'], color='#F59E0B', linewidth=2.0, alpha=0.9, label='MA5')      # 주황색
    ax1.plot(df.index, df['MA20'], color='#8B5CF6', linewidth=2.0, alpha=0.9, label='MA20')    # 보라색
    ax1.plot(df.index, df['MA60'], color='#06B6D4', linewidth=2.0, alpha=0.9, label='MA60')    # 청록색
    ax1.plot(df.index, df['MA120'], color='#84CC16', linewidth=2.0, alpha=0.9, label='MA120')  # 연두색
    
    # 메인 차트 설정
    ax1.set_title('Price Chart with Bollinger Bands and Moving Averages', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price (KRW)', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    
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
    
    # 3. RSI 차트 (세 번째 패널) - 웹 트레이딩 스타일 유지
    ax3 = axes[2]
    ax3.plot(df.index, df['RSI'], color='#8B5CF6', alpha=0.9, linewidth=2.0, label='RSI')
    ax3.axhline(y=80, color='#EF4444', linestyle='--', alpha=0.8, linewidth=1.5, label='Overbought')
    ax3.axhline(y=40, color='#10B981', linestyle='--', alpha=0.8, linewidth=1.5, label='Oversold')
    ax3.axhline(y=60, color='#6B7280', linestyle='-', alpha=0.6, linewidth=1.0)
    ax3.set_title('RSI (Relative Strength Index)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('RSI', fontsize=10, fontweight='bold')
    ax3.set_ylim(0, 100)
    ax3.legend(fontsize=10, framealpha=0.9)
    ax3.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax3.yaxis.set_label_position('right')
    ax3.yaxis.tick_right()
    
    # 4. MACD 차트 (네 번째 패널) - 웹 트레이딩 스타일 유지
    ax4 = axes[3]
    ax4.plot(df.index, df['MACD'], color='#3B82F6', linewidth=2.0, label='MACD')
    ax4.plot(df.index, df['MACD_Signal'], color='#F59E0B', linewidth=2.0, label='Signal')
    ax4.bar(df.index, df['MACD_Histogram'], color='#6B7280', alpha=0.6, width=0.8, label='Histogram')
    ax4.axhline(y=0, color='#374151', linestyle='-', alpha=0.7, linewidth=1.0)
    ax4.set_title('MACD (12,26,9)', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=10, framealpha=0.9)
    ax4.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax4.yaxis.set_label_position('right')
    ax4.yaxis.tick_right()
    
    # X축 날짜 설정 - 하단에만 표시
    for i, ax in enumerate(axes):
        if i == len(axes) - 1:  # 마지막 패널에만 날짜 표시
            # 날짜 인덱스에서 적절한 간격으로 날짜 선택
            date_indices = [df.index[0], df.index[len(df)//4], df.index[len(df)//2], 
                           df.index[3*len(df)//4], df.index[-1]]
            ax.set_xticks(date_indices)
            ax.set_xticklabels([date.strftime('%Y-%m') for date in date_indices], 
                              rotation=45, ha='right', fontweight='bold')
        else:
            ax.set_xticks([])  # 다른 패널은 X축 눈금 숨김
    
    plt.tight_layout()
    
    # 차트를 이미지로 저장
    charts_dir = "test_charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
        print(f"📁 {charts_dir} 폴더를 생성했습니다.")
    
    # 파일명 생성 (버전 관리)
    current_date = datetime.now().strftime("%Y%m%d")
    current_time = datetime.now().strftime("%H%M%S")
    base_filename = f"daily_overlay_{stock_name}_{stock_code}_{current_date}"
    
    # 버전 확인 및 파일명 생성
    version = 1
    while True:
        if version == 1:
            filename = f"{base_filename}.png"
        else:
            filename = f"{base_filename}_v{version}.png"
        
        filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        filepath = os.path.join(charts_dir, filename)
        
        if not os.path.exists(filepath):
            break
        version += 1
    
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"💾 일봉 오버레이 차트가 저장되었습니다: {filepath}")
    
    # 차트 뷰어를 띄우지 않고 차트 닫기
    plt.close()
    
    return filepath

def get_weekly_stock_data(stock_code):
    """주봉 데이터 조회 (5년)"""
    print(f"🔍 {stock_code} 5년 주봉 데이터를 조회합니다...")
    
    try:
        ticker_symbol = f"{stock_code}.KS"
        ticker = yf.Ticker(ticker_symbol)
        
        # 5년 주봉 데이터 조회
        hist = ticker.history(period="5y", interval="1wk")
        
        if not hist.empty:
            print(f"✅ 주봉 데이터 조회 성공")
            print(f"📅 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
            print(f"📊 데이터 수: {len(hist)}주")
            
            # 최근 5주 데이터 출력
            print(f"📊 최근 주봉 데이터:")
            for i, (date, row) in enumerate(hist.tail(5).iterrows()):
                print(f"   {date.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f} (거래량: {row['Volume']:,.0f})")
            
            return hist
        else:
            print("❌ 주봉 데이터 조회 실패")
            return None
            
    except Exception as e:
        print(f"❌ 주봉 데이터 조회 중 오류: {str(e)}")
        return None

def calculate_weekly_indicators(df):
    """주봉용 기술적 지표 계산"""
    print("🔧 주봉 기술적 지표를 계산합니다...")
    
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
    period = 14
    high_14 = df['High'].rolling(window=period).max()
    low_14 = df['Low'].rolling(window=period).min()
    
    k_fast = ((df['Close'] - low_14) / (high_14 - low_14)) * 100
    d_fast = k_fast.rolling(window=3).mean()
    
    df['Stoch_K'] = d_fast
    df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()
    
    print("✅ 주봉 기술적 지표 계산 완료")
    return df

def create_weekly_overlay_chart(df, stock_code="019210", stock_name="YG-1"):
    """주봉 오버레이 차트 생성 - 이미지 참고하여 볼린저 밴드 색상 복원"""
    print(f"\n📈 주봉 오버레이 차트를 생성합니다...")
    
    # 기술적 지표 계산
    df = calculate_weekly_indicators(df.copy())
    
    # 차트 생성 (3개 패널: 메인차트, 거래량, 스토캐스틱)
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), height_ratios=[8, 2, 2])
    fig.suptitle(f'{stock_name} ({stock_code}) Weekly Stock Chart - Image Reference Style', fontsize=16, fontweight='bold')
    
    # 1. 메인 차트 (캔들차트 + 보조지표 오버레이)
    ax1 = axes[0]
    
    # 볼린저 밴드 영역 채우기 (이미지 참고 - 오렌지/베이지 스타일)
    ax1.fill_between(df.index, df['BB_Upper'], df['BB_Lower'], 
                     alpha=0.15, color='#FFE4B5', label='Bollinger Bands')
    
    # 볼린저 밴드 상단과 하단을 오렌지/베이지 색으로 표시 (범례에 표시하지 않음)
    ax1.plot(df.index, df['BB_Upper'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    ax1.plot(df.index, df['BB_Lower'], color='#FFCE89', alpha=0.8, linewidth=1.5, label='_nolegend_')
    
    # 캔들차트 그리기 (이미지 참고 - 빨간색/파란색)
    for date, row in df.iterrows():
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
    ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    
    # Y축을 오른쪽으로 이동
    ax1.yaxis.set_label_position('right')
    ax1.yaxis.tick_right()
    
    # 2. 거래량 차트
    ax2 = axes[1]
    colors = ['#FF4444' if close >= open else '#4444FF' 
              for close, open in zip(df['Close'], df['Open'])]
    
    ax2.bar(df.index, df['Volume'], color=colors, alpha=0.7, width=0.8)
    ax2.set_title('Volume', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Volume', fontsize=10, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax2.yaxis.set_label_position('right')
    ax2.yaxis.tick_right()
    
    # 3. 스토캐스틱 차트
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
        if i == len(axes) - 1:
            date_indices = [df.index[0], df.index[len(df)//4], df.index[len(df)//2], 
                           df.index[3*len(df)//4], df.index[-1]]
            ax.set_xticks(date_indices)
            ax.set_xticklabels([date.strftime('%Y-%m-%d') for date in date_indices], 
                              rotation=45, ha='right', fontweight='bold')
        else:
            ax.set_xticks([])
    
    plt.tight_layout()
    
    # 차트 저장
    charts_dir = "test_charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
    
    current_date = datetime.now().strftime("%Y%m%d")
    filename = f"weekly_overlay_{stock_name}_{stock_code}_{current_date}.png"
    filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
    filepath = os.path.join(charts_dir, filename)
    
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"💾 주봉 오버레이 차트가 저장되었습니다: {filepath}")
    
    plt.close()
    return filepath

def get_monthly_stock_data(stock_code):
    """월봉 데이터 조회 (10년)"""
    print(f"🔍 {stock_code} 10년 월봉 데이터를 조회합니다...")
    
    try:
        ticker_symbol = f"{stock_code}.KS"
        ticker = yf.Ticker(ticker_symbol)
        
        # 10년 월봉 데이터 조회
        hist = ticker.history(period="10y", interval="1mo")
        
        if not hist.empty:
            print(f"✅ 월봉 데이터 조회 성공")
            print(f"📅 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
            print(f"📊 데이터 수: {len(hist)}개월")
            
            # 최근 5개월 데이터 출력
            print(f"📊 최근 월봉 데이터:")
            for i, (date, row) in enumerate(hist.tail(5).iterrows()):
                print(f"   {date.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f} (거래량: {row['Volume']:,.0f})")
            
            return hist
        else:
            print("❌ 월봉 데이터 조회 실패")
            return None
            
    except Exception as e:
        print(f"❌ 월봉 데이터 조회 중 오류: {str(e)}")
        return None

def calculate_monthly_indicators(df):
    """월봉용 기술적 지표 계산"""
    print("🔧 월봉 기술적 지표를 계산합니다...")
    
    # 이동평균선 (월간 기준)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # CCI (Commodity Channel Index) 계산
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    sma_tp = typical_price.rolling(window=20).mean()
    mean_deviation = typical_price.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
    df['CCI'] = (typical_price - sma_tp) / (0.015 * mean_deviation)
    
    # ADX (Average Directional Index) 계산
    high_diff = df['High'].diff()
    low_diff = df['Low'].diff()
    
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), -low_diff, 0)
    
    tr1 = df['High'] - df['Low']
    tr2 = np.abs(df['High'] - df['Close'].shift(1))
    tr3 = np.abs(df['Low'] - df['Close'].shift(1))
    true_range = np.maximum(tr1, np.maximum(tr2, tr3))
    
    period = min(14, len(df) // 2)
    if period < 5:
        period = 5
    
    atr = true_range.rolling(window=period).mean()
    atr = atr.replace(0, np.nan)
    
    plus_dm_avg = pd.Series(plus_dm).rolling(window=period).mean()
    minus_dm_avg = pd.Series(minus_dm).rolling(window=period).mean()
    
    plus_di = pd.Series(index=df.index, dtype=float)
    minus_di = pd.Series(index=df.index, dtype=float)
    
    for i in range(len(df)):
        if pd.notna(atr.iloc[i]) and atr.iloc[i] > 0:
            plus_di.iloc[i] = (plus_dm_avg.iloc[i] / atr.iloc[i]) * 100
            minus_di.iloc[i] = (minus_dm_avg.iloc[i] / atr.iloc[i]) * 100
        else:
            plus_di.iloc[i] = 0
            minus_di.iloc[i] = 0
    
    dx = pd.Series(index=df.index, dtype=float)
    
    for i in range(len(df)):
        di_sum = plus_di.iloc[i] + minus_di.iloc[i]
        if di_sum > 0:
            dx.iloc[i] = abs(plus_di.iloc[i] - minus_di.iloc[i]) / di_sum * 100
        else:
            dx.iloc[i] = 0
    
    df['ADX'] = pd.Series(dx).rolling(window=period).mean()
    df['Plus_DI'] = plus_di
    df['Minus_DI'] = minus_di
    
    df['ADX'] = df['ADX'].fillna(0)
    df['Plus_DI'] = df['Plus_DI'].fillna(0)
    df['Minus_DI'] = df['Minus_DI'].fillna(0)
    
    print("✅ 월봉 기술적 지표 계산 완료")
    return df

def create_monthly_overlay_chart(df, stock_code="019210", stock_name="YG-1"):
    """월봉 오버레이 차트 생성 - 이미지 참고하여 캔들 색상 복원"""
    print(f"\n📈 월봉 오버레이 차트를 생성합니다...")
    
    # 기술적 지표 계산
    df = calculate_monthly_indicators(df.copy())
    
    # 차트 생성 (4개 패널: 메인차트, 거래량, CCI, ADX)
    fig, axes = plt.subplots(4, 1, figsize=(15, 16), height_ratios=[8, 2, 2, 2])
    fig.suptitle(f'{stock_name} ({stock_code}) Monthly Stock Chart - Image Reference Style', fontsize=16, fontweight='bold')
    
    # 1. 메인 차트 (캔들차트 + 이동평균선)
    ax1 = axes[0]
    
    # 캔들차트 그리기 (이미지 참고 - 빨간색/파란색)
    for date, row in df.iterrows():
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
    ax1.set_title('Price Chart with Moving Averages', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price (KRW)', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    
    # Y축을 오른쪽으로 이동
    ax1.yaxis.set_label_position('right')
    ax1.yaxis.tick_right()
    
    # 2. 거래량 차트
    ax2 = axes[1]
    colors = ['#FF4444' if close >= open else '#4444FF' 
              for close, open in zip(df['Close'], df['Open'])]
    
    ax2.bar(df.index, df['Volume'], color=colors, alpha=0.7, width=0.8)
    ax2.set_title('Volume', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Volume', fontsize=10, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax2.yaxis.set_label_position('right')
    ax2.yaxis.tick_right()
    
    # 3. CCI 차트
    ax3 = axes[2]
    ax3.plot(df.index, df['CCI'], color='#3B82F6', linewidth=2.0, label='CCI')
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
    
    # 4. ADX 차트
    ax4 = axes[3]
    ax4.plot(df.index, df['ADX'], color='#8B5CF6', linewidth=2.5, label='ADX')
    ax4.plot(df.index, df['Plus_DI'], color='#10B981', linewidth=2.0, alpha=0.8, label='+DI')
    ax4.plot(df.index, df['Minus_DI'], color='#EF4444', linewidth=2.0, alpha=0.8, label='-DI')
    ax4.axhline(y=25, color='#6B7280', linestyle='--', alpha=0.8, linewidth=1.5, label='Trend Threshold')
    ax4.set_title('ADX (Average Directional Index)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('ADX/+DI/-DI', fontsize=10, fontweight='bold')
    ax4.legend(fontsize=10, framealpha=0.9)
    ax4.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax4.yaxis.set_label_position('right')
    ax4.yaxis.tick_right()
    
    # X축 날짜 설정 - 하단에만 표시
    for i, ax in enumerate(axes):
        if i == len(axes) - 1:
            date_indices = [df.index[0], df.index[len(df)//4], df.index[len(df)//2], 
                           df.index[3*len(df)//4], df.index[-1]]
            ax.set_xticks(date_indices)
            ax.set_xticklabels([date.strftime('%Y-%m') for date in date_indices], 
                              rotation=45, ha='right', fontweight='bold')
        else:
            ax.set_xticks([])
    
    plt.tight_layout()
    
    # 차트 저장
    charts_dir = "test_charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
    
    # 파일명 생성 (버전 관리)
    current_date = datetime.now().strftime("%Y%m%d")
    current_time = datetime.now().strftime("%H%M%S")
    base_filename = f"monthly_overlay_{stock_name}_{stock_code}_{current_date}"
    
    # 버전 확인 및 파일명 생성
    version = 1
    while True:
        if version == 1:
            filename = f"{base_filename}.png"
        else:
            filename = f"{base_filename}_v{version}.png"
        
        filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        filepath = os.path.join(charts_dir, filename)
        
        if not os.path.exists(filepath):
            break
        version += 1
    
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"💾 월봉 오버레이 차트가 저장되었습니다: {filepath}")
    
    plt.close()
    return filepath

def main():
    """메인 함수"""
    print("🚀 종목코드 019210 (YG-1) 일봉/주봉/월봉 오버레이 차트 테스트")
    print("="*60)
    
    # 1. 일봉 차트 생성
    print("\n" + "="*50)
    print("📈 1단계: 일봉 차트 생성")
    print("="*50)
    
    daily_df = get_stock_data_019210()
    if daily_df is not None:
        daily_chart_path = create_overlay_chart(daily_df, "019210", "YG-1")
        if daily_chart_path:
            print(f"✅ 일봉 차트 생성 완료: {daily_chart_path}")
        else:
            print("❌ 일봉 차트 생성 실패")
    else:
        print("❌ 일봉 데이터 조회 실패")
    
    # 2. 주봉 차트 생성
    print("\n" + "="*50)
    print("📈 2단계: 주봉 차트 생성")
    print("="*50)
    
    weekly_df = get_weekly_stock_data("019210")
    if weekly_df is not None:
        weekly_chart_path = create_weekly_overlay_chart(weekly_df, "019210", "YG-1")
        if weekly_chart_path:
            print(f"✅ 주봉 차트 생성 완료: {weekly_chart_path}")
        else:
            print("❌ 주봉 차트 생성 실패")
    else:
        print("❌ 주봉 데이터 조회 실패")
    
    # 3. 월봉 차트 생성
    print("\n" + "="*50)
    print("📈 3단계: 월봉 차트 생성")
    print("="*50)
    
    monthly_df = get_monthly_stock_data("019210")
    if monthly_df is not None:
        monthly_chart_path = create_monthly_overlay_chart(monthly_df, "019210", "YG-1")
        if monthly_chart_path:
            print(f"✅ 월봉 차트 생성 완료: {monthly_chart_path}")
        else:
            print("❌ 월봉 차트 생성 실패")
    else:
        print("❌ 월봉 데이터 조회 실패")
    
    # 최종 결과 요약
    print("\n" + "="*60)
    print("🎯 최종 결과 요약")
    print("="*60)
    
    success_count = 0
    if 'daily_chart_path' in locals() and daily_chart_path:
        print(f"✅ 일봉 차트: {daily_chart_path}")
        success_count += 1
    if 'weekly_chart_path' in locals() and weekly_chart_path:
        print(f"✅ 주봉 차트: {weekly_chart_path}")
        success_count += 1
    if 'monthly_chart_path' in locals() and monthly_chart_path:
        print(f"✅ 월봉 차트: {monthly_chart_path}")
        success_count += 1
    
    print(f"\n📊 총 {success_count}/3개 차트 생성 완료")
    
    if success_count == 3:
        print("\n🎉 모든 차트가 성공적으로 생성되었습니다!")
        print("\n💡 차트 특징:")
        print("   📅 일봉: 볼린저 밴드 + RSI + MACD 오버레이")
        print("   📅 주봉: 볼린저 밴드 + 스토캐스틱 + %B 오버레이")
        print("   📅 월봉: 이동평균선 + CCI + ADX 오버레이")
        print("   🎨 모든 차트: Y축 가격이 오른쪽, X축 날짜는 하단에만 표시")
        print("   🎯 실제 YG-1 주식 데이터 사용")
    else:
        print(f"\n⚠️ {3-success_count}개 차트 생성에 실패했습니다.")
        print("   네트워크 연결이나 데이터 가용성을 확인해주세요.")

if __name__ == "__main__":
    main()
