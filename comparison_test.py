#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yahoo Finance 주식 분석 테스트 스크립트
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

def get_stock_data_yahoo(stock_code):
    """Yahoo Finance를 사용한 국내 주식 일봉 데이터 조회 (240일)"""
    print(f"🔍 {stock_code} 240일 일봉 시세 조회 중... (Yahoo Finance)")
    print("   📅 일봉 데이터는 거래일 기준으로 제공되며, 주말/공휴일은 포함되지 않습니다.")
    
    try:
        # Yahoo Finance에서 데이터 조회
        print("   🔄 Yahoo Finance에서 데이터 조회 중...")
        
        # 한국 주식은 .KS 접미사 필요
        ticker_symbol = f"{stock_code}.KS"
        ticker = yf.Ticker(ticker_symbol)
        
        # 1년 데이터 조회 (240일보다 충분)
        hist = ticker.history(period="1y")
        
        if not hist.empty:
            print(f"✅ Yahoo Finance 일봉: 1년 기간 일봉 데이터를 조회했습니다.")
            print(f"📅 총 {len(hist)}일의 일봉 거래 데이터를 가져왔습니다.")
            print(f"🏢 종목명: {ticker.info.get('longName', stock_code)}")
            
            # 240일 데이터로 제한
            if len(hist) > 240:
                hist = hist.tail(240)
            
            # 최근 5일 데이터 출력
            print(f"📊 최근 일봉 데이터 상세:")
            for i, (date, row) in enumerate(hist.tail(5).iterrows()):
                print(f"   {date.strftime('%Y-%m-%d')}: {row['Open']:,.0f} → {row['Close']:,.0f} (거래량: {row['Volume']:,.0f})")
            
            return hist
        else:
            print(f"   ❌ 일봉 데이터 조회 실패: 데이터가 없습니다")
            return None
            
    except Exception as e:
        print(f"   ❌ Yahoo Finance 연결 실패: {str(e)}")
        return None

def calculate_technical_indicators(df):
    """기술적 지표 계산"""
    # 이동평균선
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    # MACD 계산 (표준 공식)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
    
    # RSI 계산 (표준 공식)
    delta = df['Close'].diff()
    
    # 상승폭과 하락폭 분리
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    loss = abs(loss)
    
    # 14일 평균 계산
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    # RS와 RSI 계산
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def analyze_stock_data(hist, stock_code, source_name):
    """주식 일봉 데이터 분석"""
    if hist is None or hist.empty:
        return
    
    print(f"\n" + "="*60)
    print(f"📊 {stock_code} 주식 일봉 분석 결과 ({source_name})")
    print("="*60)
    
    # 기본 통계
    print(f"📅 조회 기간: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}")
    print(f"📈 일봉 거래일 수: {len(hist)}일")
    
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
    
    # 일봉 거래량 정보
    print(f"\n📈 일봉 거래량 정보:")
    print(f"   평균 일봉 거래량: {hist['Volume'].mean():,.0f}주")
    print(f"   최대 일봉 거래량: {hist['Volume'].max():,.0f}주")
    print(f"   최소 일봉 거래량: {hist['Volume'].min():,.0f}주")
    
    # 기술적 지표 계산
    df_with_indicators = calculate_technical_indicators(hist.copy())
    
    # 기술적 지표 정보
    print(f"\n📊 기술적 지표 (최근값):")
    print(f"   5일 이동평균: {df_with_indicators['MA5'].iloc[-1]:,.0f}원")
    print(f"   20일 이동평균: {df_with_indicators['MA20'].iloc[-1]:,.0f}원")
    print(f"   60일 이동평균: {df_with_indicators['MA60'].iloc[-1]:,.0f}원")
    print(f"   120일 이동평균: {df_with_indicators['MA120'].iloc[-1]:,.0f}원")
    
    # RSI 정보
    rsi_value = df_with_indicators['RSI'].iloc[-1]
    print(f"   RSI: {rsi_value:.1f}")
    if rsi_value > 70:
        print("   RSI 신호: 과매수 구간")
    elif rsi_value < 30:
        print("   RSI 신호: 과매도 구간")
    else:
        print("   RSI 신호: 중립 구간")
    
    # MACD 정보
    macd_value = df_with_indicators['MACD'].iloc[-1]
    macd_signal = df_with_indicators['MACD_Signal'].iloc[-1]
    macd_histogram = df_with_indicators['MACD_Histogram'].iloc[-1]
    print(f"   MACD: {macd_value:.2f}")
    print(f"   MACD Signal: {macd_signal:.2f}")
    print(f"   MACD Histogram: {macd_histogram:.2f}")
    if macd_value > macd_signal:
        print("   MACD 신호: 상승 추세")
    else:
        print("   MACD 신호: 하락 추세")

def create_stock_chart(hist, stock_code, source_name):
    """주식 일봉 차트 생성 (캔들차트 + 보조지표)"""
    if hist is None or hist.empty:
        return None
    
    print(f"\n📈 일봉 캔들차트를 생성합니다... ({source_name})")
    
    # 기술적 지표 계산
    df = calculate_technical_indicators(hist.copy())
    df.index.name = 'Date'
    
    # 하나의 큰 차트에 모든 지표 포함
    fig, axes = plt.subplots(4, 1, figsize=(15, 16), height_ratios=[6, 2, 2, 2])
    fig.suptitle(f'{stock_code} Daily Stock Chart (240 Days) - {source_name}', fontsize=16, fontweight='bold')
    
    # 1. 캔들차트 (첫 번째 패널)
    ax1 = axes[0]
    
    # 캔들차트 그리기
    for date, row in df.iterrows():
        color = 'red' if row['Close'] >= row['Open'] else 'blue'
        ax1.plot([date, date], [row['Low'], row['High']], color=color, linewidth=1)
        ax1.plot([date, date], [row['Open'], row['Close']], color=color, linewidth=3)
    
    # 이동평균선 추가
    ax1.plot(df.index, df['MA5'], color='red', linewidth=1, alpha=0.7, label='MA5')
    ax1.plot(df.index, df['MA20'], color='green', linewidth=1, alpha=0.7, label='MA20')
    ax1.plot(df.index, df['MA60'], color='orange', linewidth=1, alpha=0.7, label='MA60')
    ax1.plot(df.index, df['MA120'], color='purple', linewidth=1, alpha=0.7, label='MA120')
    
    ax1.set_title(f'Price Chart with Moving Averages ({source_name})')
    ax1.set_ylabel('Price (KRW)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 일봉 거래량 차트 (두 번째 패널)
    ax2 = axes[1]
    ax2.bar(df.index, df['Volume'], color='green', alpha=0.7)
    ax2.set_title('Daily Volume')
    ax2.set_ylabel('Volume')
    ax2.grid(True, alpha=0.3)
    
    # 3. MACD 차트 (세 번째 패널)
    ax3 = axes[2]
    ax3.plot(df.index, df['MACD'], color='blue', linewidth=1, label='MACD')
    ax3.plot(df.index, df['MACD_Signal'], color='red', linewidth=1, label='Signal')
    ax3.bar(df.index, df['MACD_Histogram'], color='gray', alpha=0.5, width=0.8, label='Histogram')
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.set_title('MACD')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. RSI 차트 (네 번째 패널)
    ax4 = axes[3]
    ax4.plot(df.index, df['RSI'], color='purple', linewidth=1, label='RSI')
    ax4.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Overbought')
    ax4.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Oversold')
    ax4.axhline(y=50, color='black', linestyle='-', alpha=0.3)
    ax4.set_ylim(0, 100)
    ax4.set_title('RSI')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 모든 패널의 x축 날짜 설정
    for ax in axes:
        # 날짜 인덱스에서 적절한 간격으로 날짜 선택
        date_indices = [df.index[0], df.index[len(df)//4], df.index[len(df)//2], 
                       df.index[3*len(df)//4], df.index[-1]]
        ax.set_xticks(date_indices)
        ax.set_xticklabels([date.strftime('%Y-%m-%d') for date in date_indices], 
                          rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 차트를 이미지로 저장
    charts_dir = f"comparison_charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
        print(f"📁 {charts_dir} 폴더를 생성했습니다.")
    
    # 파일명 생성: comparison_종목명_종목번호_데이터소스_생성일.png
    current_date = datetime.now().strftime("%Y%m%d")
    stock_name = stock_code  # 기본값
    
    # Yahoo Finance에서 종목명 가져오기
    try:
        ticker_symbol = f"{stock_code}.KS"
        ticker = yf.Ticker(ticker_symbol)
        ticker_info = ticker.info
        if 'longName' in ticker_info and ticker_info['longName']:
            stock_name = ticker_info['longName']
    except:
        pass
    
    base_filename = f"comparison_{stock_name}_{stock_code}_{source_name.replace(' ', '_')}_{current_date}.png"
    
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
    
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"💾 차트가 저장되었습니다: {filepath}")
    
    # 차트 뷰어를 띄우지 않고 차트 닫기
    plt.close()
    
    return filepath

def analyze_stock_data_source(stock_code):
    """Yahoo Finance 데이터 분석"""
    print(f"\n🔍 {stock_code} Yahoo Finance 데이터 분석")
    print("="*60)
    
    # Yahoo Finance 결과
    print("📊 Yahoo Finance 결과:")
    yahoo_data = get_stock_data_yahoo(stock_code)
    
    if yahoo_data is not None:
        analyze_stock_data(yahoo_data, stock_code, "Yahoo Finance")
        yahoo_chart = create_stock_chart(yahoo_data, stock_code, "Yahoo Finance")
        print(f"✅ Yahoo Finance 차트 생성 완료: {yahoo_chart}")
    else:
        print("❌ Yahoo Finance 데이터 조회 실패")
    
    print("\n" + "="*60)
    print("💡 분석 완료!")
    print("📁 생성된 차트 파일들을 확인해보세요.")
    print("   - comparison_charts/: 분석 차트")
    print("   - daily_charts/: 기존 Yahoo Finance 방식")
    
    if yahoo_data is not None:
        print(f"\n📊 데이터 요약:")
        print(f"   📅 데이터 기간: {yahoo_data.index[0].strftime('%Y-%m-%d')} ~ {yahoo_data.index[-1].strftime('%Y-%m-%d')}")
        print(f"   📈 데이터 수: {len(yahoo_data)}일")
        print(f"   💰 최신 종가: {yahoo_data['Close'].iloc[-1]:,.0f}원")
        print(f"   📊 평균 거래량: {yahoo_data['Volume'].mean():,.0f}주")

def main():
    """메인 함수"""
    print("🚀 Yahoo Finance 주식 분석 테스트 프로그램")
    print("="*60)
    
    # 종목코드 입력
    while True:
        stock_code = input("📈 종목코드를 입력하세요 (예: 005930): ").strip()
        if stock_code.isdigit() and len(stock_code) == 6:
            break
        else:
            print("❌ 올바른 종목코드를 입력해주세요 (6자리 숫자)")
    
    # 분석 실행
    analyze_stock_data_source(stock_code)

if __name__ == "__main__":
    main() 