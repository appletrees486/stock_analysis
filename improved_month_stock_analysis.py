#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 국내 주식 월봉 시세 조회 스크립트 (Y축 자동 조정 + 로그 스케일 적용)
기존 month_stock_analysis.py의 개선된 버전
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
import json

# 데이터베이스 연결을 위한 import 추가
from database_config import DatabaseManager

# 운영체제별 한글 폰트 설정 (한글 깨짐 방지 강화)
system = platform.system()
if system == 'Windows':
    # Windows 환경 - 한글 폰트 우선순위
    font_list = ['Malgun Gothic', '맑은 고딕', 'NanumGothic', '나눔고딕', 'Noto Sans CJK KR', 'Noto Sans KR']
elif system == 'Darwin':  # macOS
    font_list = ['AppleGothic', 'NanumGothic', '나눔고딕', 'Noto Sans CJK KR', 'Noto Sans KR']
else:  # Linux
    font_list = ['NanumGothic', '나눔고딕', 'Noto Sans CJK KR', 'Noto Sans KR', 'DejaVu Sans']

# 사용 가능한 폰트 찾기 (한글 지원 폰트 우선)
available_font = None
for font in font_list:
    try:
        # 폰트 파일 경로 확인
        font_path = fm.findfont(font)
        if font_path and 'DejaVu' not in font_path:  # DejaVu는 한글 미지원
            available_font = font
            print(f"✅ 한글 지원 폰트 발견: {font} ({font_path})")
            break
    except Exception as e:
        print(f"⚠️ 폰트 {font} 확인 실패: {e}")
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

def get_monthly_stock_data_from_db(stock_code):
    """DB에서 월봉 데이터 조회 (보조지표 포함)"""
    print(f"🔍 DB에서 {stock_code} 월봉 데이터 조회 중...")
    
    try:
        db = DatabaseManager()
        if not db.connect():
            print("   ❌ 데이터베이스 연결 실패")
            return None
        
        # 종목명 조회
        stock_name_query = "SELECT stock_name FROM stocks WHERE stock_code = %s"
        stock_info = db.fetch_one(stock_name_query, (stock_code,))
        if not stock_info:
            print(f"   ❌ 종목코드 {stock_code}를 찾을 수 없습니다.")
            db.disconnect()
            return None
        
        stock_name = stock_info['stock_name']
        print(f"   🏢 종목명: {stock_name}")
        
        # 최신 월봉 데이터 기준으로 기간 설정
        latest_date_query = "SELECT MAX(month_start) as latest_date FROM monthly_data WHERE stock_code = %s"
        latest_date_result = db.fetch_one(latest_date_query, (stock_code,))
        
        if latest_date_result and latest_date_result['latest_date']:
            end_date = latest_date_result['latest_date']
            start_date = end_date - timedelta(days=3650)  # 10년 전
            print(f"   📅 DB 최신 월봉: {end_date}")
            print(f"   📅 조회 시작일: {start_date}")
        else:
            print(f"   ⚠️ DB에 월봉 데이터가 없습니다.")
            db.disconnect()
            return None
        
        # 월봉 데이터 조회 (보조지표 포함, month_end 포함)
        monthly_query = """
        SELECT month_start, month_end, open, high, low, close, volume,
               ma5, ma20, ma60, ma6, ma12, ma24, cci, adx, plus_di, minus_di,
               bb_upper, bb_middle, bb_lower, macd, macd_signal, macd_histogram, rsi
        FROM monthly_data 
        WHERE stock_code = %s 
        AND month_start >= %s 
        AND month_start <= %s
        ORDER BY month_start ASC
        """
        
        params = (stock_code, start_date, end_date)
        monthly_data = db.fetch_all(monthly_query, params)
        
        db.disconnect()
        
        if monthly_data:
            # DataFrame으로 변환
            df = pd.DataFrame(monthly_data)
            df['month_start'] = pd.to_datetime(df['month_start'])
            df['month_end'] = pd.to_datetime(df['month_end'])
            df.set_index('month_start', inplace=True)
            
            # 컬럼명을 기존 형식과 맞춤 (month_end 제외)
            df.columns = ['Month_End', 'Open', 'High', 'Low', 'Close', 'Volume', 
                         'MA5', 'MA20', 'MA60', 'MA6', 'MA12', 'MA24', 'CCI', 'ADX', 'Plus_DI', 'Minus_DI',
                         'BB_Upper', 'BB_Middle', 'BB_Lower', 'MACD', 'MACD_Signal', 'MACD_Histogram', 'RSI']
            
            print(f"   ✅ DB에서 월봉 데이터 {len(df)}개월 조회 완료")
            print(f"   📅 데이터 기간: {df.index[0].strftime('%Y-%m')} ~ {df.index[-1].strftime('%Y-%m')}")
            
            return df
        else:
            print(f"   ⚠️ DB에 월봉 데이터가 없습니다.")
            return None
            
    except Exception as e:
        print(f"   ❌ DB에서 월봉 데이터 조회 실패: {str(e)}")
        try:
            db.disconnect()
        except:
            pass
        return None

def calculate_technical_indicators(df, stock_code=None):
    """기술적 지표 계산 - 월봉 기준 (10년/120개월+ 설정)"""
    
    try:
        print(f"   🔧 월봉 기술적 지표 계산 시작 (데이터 수: {len(df)}개월)")
        
        # 데이터 타입을 float로 변환 (decimal 타입 문제 해결)
        try:
            numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
            print(f"   ✅ 데이터 타입 변환 완료: float64")
        except Exception as e:
            print(f"   ⚠️ 데이터 타입 변환 중 오류: {e}")
        
        # 이동평균선 (월간 기준) - 6/12/24개월만 사용 (차트 표시용)
        df['MA6'] = df['Close'].rolling(window=6).mean()   # DB 저장용
        df['MA12'] = df['Close'].rolling(window=12).mean() # DB 저장용
        df['MA24'] = df['Close'].rolling(window=24).mean() # DB 저장용
        
        # 기존 호환성을 위한 이동평균선 (DB 저장용)
        df['MA3'] = df['Close'].rolling(window=3).mean()
        df['MA5'] = df['Close'].rolling(window=5).mean()   # DB 저장용
        df['MA20'] = df['Close'].rolling(window=20).mean() # DB 저장용
        df['MA60'] = df['Close'].rolling(window=60).mean() # DB 저장용 장기 추세
        
        # 🔥 개선된 볼린저 밴드 계산 (20개월,2) - 로그 스케일 최적화
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        
        # 기본 볼린저 밴드 계산
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # 🔥 로그 스케일용 볼린저 밴드 하한선 개선 (간단하고 효율적인 방법)
        # 1. 최소값을 1원으로 설정
        df['BB_Lower'] = df['BB_Lower'].clip(lower=1.0)
        
        # 2. 중간선의 40% 이하로는 내려가지 않도록 제한
        df['BB_Lower'] = df['BB_Lower'].clip(lower=df['BB_Middle'] * 0.4)
        
        # 3. 전체 데이터의 최저가의 60% 이하로는 절대 내려가지 않도록 제한
        global_min_price = df[['High', 'Low', 'Close', 'Open']].min().min()
        if global_min_price > 0:
            df['BB_Lower'] = df['BB_Lower'].clip(lower=global_min_price * 0.6)
        
        # 4. 볼린저 밴드 폭이 너무 넓어지지 않도록 제한 (중간선의 150% 이하)
        max_band_width = df['BB_Middle'] * 1.5
        band_width = df['BB_Upper'] - df['BB_Lower']
        
        # 밴드 폭이 너무 넓으면 하한선을 조정
        mask = band_width > max_band_width
        df.loc[mask, 'BB_Lower'] = df.loc[mask, 'BB_Upper'] - max_band_width[mask]
        df['BB_Lower'] = df['BB_Lower'].clip(lower=1.0)  # 최소 1원 보장
        
        # 볼린저 밴드 데이터 검증
        print(f"   📊 볼린저 밴드 계산 완료:")
        print(f"   📊 BB_Upper 범위: {df['BB_Upper'].min():.0f} ~ {df['BB_Upper'].max():.0f}")
        print(f"   📊 BB_Lower 범위: {df['BB_Lower'].min():.0f} ~ {df['BB_Lower'].max():.0f}")
        print(f"   📊 BB_Middle 범위: {df['BB_Middle'].min():.0f} ~ {df['BB_Middle'].max():.0f}")
        
        # 거래량 + 12개월 이동평균 거래량
        df['Volume_MA12'] = df['Volume'].rolling(window=12).mean()
        
        # MACD 계산 (12,26,9) - 표준 공식
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # RSI 계산 (14) - 표준 공식 (DB 저장용)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50)  # NaN 값은 중립값 50으로 설정
        print(f"   ✅ RSI 계산 완료")
        
        # CCI (Commodity Channel Index) 계산
        try:
            # CCI = (Typical Price - SMA of Typical Price) / (0.015 * Mean Deviation)
            # Typical Price = (High + Low + Close) / 3
            typical_price = (df['High'] + df['Low'] + df['Close']) / 3
            sma_tp = typical_price.rolling(window=20).mean()
            
            # Mean Deviation 계산
            mean_deviation = typical_price.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
            df['CCI'] = (typical_price - sma_tp) / (0.015 * mean_deviation)
            print(f"   ✅ CCI 계산 완료")
        except Exception as e:
            print(f"   ⚠️ CCI 계산 실패: {e}")
            df['CCI'] = 0.0
        
        # ADX (Average Directional Index) 계산
        print(f"   📊 ADX 계산 시작 (기간: {min(14, len(df) // 2)}개월)")
        
        # +DM, -DM 계산
        high_diff = df['High'].diff()
        low_diff = df['Low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), -low_diff, 0)
        
        # True Range 계산 (오류 처리 강화)
        try:
            tr1 = df['High'] - df['Low']
            tr2 = np.abs(df['High'] - df['Close'].shift(1))
            tr3 = np.abs(df['Low'] - df['Close'].shift(1))
            # pandas의 maximum 함수 사용 (numpy 대신) - NaN 값 처리
            true_range_df = pd.concat([tr1, tr2, tr3], axis=1)
            true_range_df = true_range_df.fillna(0)  # NaN 값을 0으로 채움
            true_range = true_range_df.max(axis=1)
            print(f"   ✅ True Range 계산 완료")
        except Exception as e:
            print(f"   ❌ True Range 계산 실패: {e}")
            # 기본값으로 설정
            true_range = pd.Series(0.0, index=df.index)
        
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
        
        # 피봇 지지·저항 계산 (연간 기준)
        try:
            # 연간 고점/저점 계산
            df['Year'] = df.index.year
            yearly_high = df.groupby('Year')['High'].max()
            yearly_low = df.groupby('Year')['Low'].min()
            
            # 최근 3년간의 고점/저점 평균
            recent_years = sorted(yearly_high.index)[-3:]
            pivot_resistance = yearly_high[recent_years].mean()
            pivot_support = yearly_low[recent_years].mean()
            
            # 피봇 포인트 계산
            df['Pivot_Point'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['Pivot_Resistance'] = pivot_resistance
            df['Pivot_Support'] = pivot_support
            
            print(f"   ✅ 피봇 지지·저항 계산 완료")
            print(f"   📊 피봇 저항선: {pivot_resistance:,.0f}원")
            print(f"   📊 피봇 지지선: {pivot_support:,.0f}원")
        except Exception as e:
            print(f"   ⚠️ 피봇 지지·저항 계산 실패: {e}")
            df['Pivot_Point'] = df['Close']
            df['Pivot_Resistance'] = df['High'].rolling(window=12).max()
            df['Pivot_Support'] = df['Low'].rolling(window=12).min()
        
        print(f"   ✅ 월봉 기술적 지표 계산 완료")
        print(f"   📊 계산된 지표: MA3/6/12/24, 볼린저밴드, MACD, RSI, CCI, ADX, 피봇 지지·저항")
        return df
    
    except Exception as e:
        print(f"   ❌ calculate_technical_indicators 함수에서 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        # 오류 발생 시 기본 DataFrame 반환
        return df

def detect_trading_suspension(row, df):
    """거래정지 기간 감지 함수 - 월봉용 (정확한 조건)"""
    # 월봉 데이터의 특성을 고려한 조건들 (정확한 거래정지만 감지)
    
    # 1. 가격이 0 이하인 경우 (상장폐지 등)
    if row['Close'] <= 0 or row['Open'] <= 0 or row['High'] <= 0 or row['Low'] <= 0:
        return True
    
    # 2. OHLC가 모두 동일하고 거래량이 0인 경우 (명확한 거래정지)
    if (row['Open'] == row['High'] == row['Low'] == row['Close'] and 
        row['Volume'] == 0):
        return True
    
    # 3. 거래량이 0이지만 가격 변동이 있는 경우는 거래정지로 간주하지 않음
    # (데이터 수집 문제일 수 있음)
    
    return False

def create_improved_monthly_stock_chart(hist, stock_code):
    """개선된 주식 월봉 차트 생성 (Y축 자동 조정 + 로그 스케일 적용)"""
    if hist is None or hist.empty:
        return None, None
    
    print(f"\n📈 개선된 월봉 캔들차트를 생성합니다...")
    
    # 중복 데이터 제거 (같은 월의 여러 데이터가 있으면 최신 데이터만 유지)
    print(f"   🔍 중복 데이터 확인 중...")
    original_count = len(hist)
    
    # 월별로 그룹화하여 중복 제거
    hist_clean = hist.copy()
    hist_clean['Month'] = hist_clean.index.to_period('M')
    
    # 월별로 최신 데이터만 유지
    hist_clean = hist_clean.groupby('Month').last()
    
    # Month 컬럼이 있으면 제거
    if 'Month' in hist_clean.columns:
        hist_clean = hist_clean.drop('Month', axis=1)
    
    removed_count = original_count - len(hist_clean)
    if removed_count > 0:
        print(f"   ✅ 중복 데이터 {removed_count}개 제거 완료 (원본: {original_count}개 → 정리: {len(hist_clean)}개)")
    else:
        print(f"   ✅ 중복 데이터 없음 (총 {len(hist_clean)}개)")
    
    # 기술적 지표 계산
    try:
        df = calculate_technical_indicators(hist_clean.copy(), stock_code)
        df.index.name = 'Date'
    except Exception as e:
        print(f"   ❌ 기술적 지표 계산 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    
    # 차트 생성 (4개 패널: 메인차트, 거래량, MACD, RSI)
    fig, axes = plt.subplots(4, 1, figsize=(12, 12), height_ratios=[6, 2, 2, 2])
    
    # 종목명 가져오기 (DB에서) - 차트 제목용
    chart_stock_name = stock_code  # 기본값
    try:
        db = DatabaseManager()
        if db.connect():
            stock_name_query = "SELECT stock_name FROM stocks WHERE stock_code = %s"
            stock_info = db.fetch_one(stock_name_query, (stock_code,))
            if stock_info and stock_info.get('stock_name'):
                chart_stock_name = stock_info['stock_name']
                print(f"✅ DB에서 종목명 조회 성공: {stock_code} -> {chart_stock_name}")
            else:
                print(f"⚠️ DB에서 종목명을 찾을 수 없음: {stock_code}")
            db.disconnect()
    except Exception as e:
        print(f"⚠️ DB 조회 중 오류: {e}, 종목코드를 종목명으로 사용: {stock_code}")
        # 실패시 기본값 사용
        pass
    
    fig.suptitle(f'{chart_stock_name} ({stock_code}) 개선된 월봉 차트 분석(10Years)', fontsize=16, fontweight='bold')
    
    # 1. 메인 차트 (캔들차트 + 보조지표 오버레이) - 개선된 Y축 설정
    ax1 = axes[0]
    
    # 볼린저 밴드 영역 채우기 (기존 차트와 동일한 스타일 - 옅은 주황색)
    ax1.fill_between(range(len(df)), df['BB_Upper'], df['BB_Lower'], 
                     alpha=0.1, color='#FFA500', label='Bollinger Bands')
    
    # 볼린저 밴드 상단과 하단을 옅은 주황색으로 표시 (기존 차트와 동일)
    ax1.plot(range(len(df)), df['BB_Upper'], color='#FF8C00', alpha=0.6, linewidth=1.0, label='_nolegend_', marker='None', linestyle='-')
    ax1.plot(range(len(df)), df['BB_Lower'], color='#FF8C00', alpha=0.6, linewidth=1.0, label='_nolegend_', marker='None', linestyle='-')
    
    # 캔들차트 그리기 (기존 차트와 동일한 스타일)
    print(f"   📊 캔들차트 그리기 시작: {len(df)}개월 데이터")
    drawn_candles = 0
    
    for i, (date, row) in enumerate(df.iterrows()):
        # 거래정지 기간 감지 (정확한 조건으로 수정)
        is_trading_suspension = detect_trading_suspension(row, df)
        
        if is_trading_suspension:
            # 거래정지 기간: 캔들을 완전히 숨김 (크기 0)
            # 아무것도 그리지 않음 - 거래정지 기간은 시각적으로 표시하지 않음
            pass
        else:
            # 일반 거래일: 기존 차트와 동일한 캔들 스타일
            if row['Close'] >= row['Open']:  # 상승
                color = '#FF4444'  # 빨간색
                # 상승 캔들: 몸통을 더 두껍게, 꼬리를 얇게
                ax1.plot([i, i], [row['Low'], row['High']], color=color, linewidth=0.8, marker='None', linestyle='-')
                ax1.plot([i, i], [row['Open'], row['Close']], color=color, linewidth=4.0, marker='None', linestyle='-')
            else:  # 하락
                color = '#4444FF'  # 파란색
                # 하락 캔들: 몸통을 더 두껍게, 꼬리를 얇게
                ax1.plot([i, i], [row['Low'], row['High']], color=color, linewidth=0.8, marker='None', linestyle='-')
                ax1.plot([i, i], [row['Open'], row['Close']], color=color, linewidth=4.0, marker='None', linestyle='-')
            drawn_candles += 1
    
    print(f"   ✅ 캔들차트 그리기 완료: {drawn_candles}개 캔들 표시")
    
    # 이동평균선 추가 (6, 12, 24개월선만 표시) - 기존 차트와 동일한 색상
    ax1.plot(range(len(df)), df['MA6'], color='#8B5CF6', linewidth=2.0, alpha=0.9, label='6개월선', marker='None', linestyle='-')
    ax1.plot(range(len(df)), df['MA12'], color='#F59E0B', linewidth=2.0, alpha=0.9, label='12개월선', marker='None', linestyle='-')
    ax1.plot(range(len(df)), df['MA24'], color='#06B6D4', linewidth=2.0, alpha=0.9, label='24개월선', marker='None', linestyle='-')
    
    # 🔥 개선된 Y축 설정 - 기존 차트와 동일한 스타일
    # 데이터의 실제 최고가/최저가를 반영 (볼린저 밴드 포함)
    price_data = df[['High', 'Low', 'Close', 'Open']].values.flatten()
    bb_data = df[['BB_Upper', 'BB_Lower']].values.flatten()
    
    # 모든 가격 데이터와 볼린저 밴드 데이터 결합
    all_price_data = np.concatenate([price_data, bb_data])
    all_price_data = all_price_data[~np.isnan(all_price_data)]  # NaN 값 제거
    all_price_data = all_price_data[all_price_data > 0]  # 0 이하 값 제거 (로그 스케일용)
    
    if len(all_price_data) > 0:
        min_price = np.min(all_price_data)
        max_price = np.max(all_price_data)
        
        # 🔥 Y축 동적 눈금 개수 조정 (가격 범위에 따라 5~20개 눈금 자동 선택)
        y_min = 0  # 0부터 시작
        
        # 가격 범위 계산
        price_range = max_price - min_price
        
        # 가격 범위에 따라 적절한 눈금 개수 결정
        if price_range >= 500000:  # 50만원 이상 차이: 20개 눈금
            tick_count = 20
        elif price_range >= 200000:  # 20만원 이상 차이: 15개 눈금
            tick_count = 15
        elif price_range >= 100000:  # 10만원 이상 차이: 12개 눈금
            tick_count = 12
        elif price_range >= 50000:   # 5만원 이상 차이: 10개 눈금
            tick_count = 10
        elif price_range >= 20000:   # 2만원 이상 차이: 8개 눈금
            tick_count = 8
        elif price_range >= 10000:   # 1만원 이상 차이: 6개 눈금
            tick_count = 6
        else:  # 1만원 미만 차이: 5개 눈금
            tick_count = 5
        
        # Y축 최대값을 적절히 설정 (10% 여유분)
        y_max = int(max_price * 1.1)
        
        print(f"   📊 가격 범위: {min_price:,.0f}원 ~ {max_price:,.0f}원 (차이: {price_range:,.0f}원)")
        print(f"   📊 Y축 범위: {y_min:,.0f}원 ~ {y_max:,.0f}원 ({tick_count}개 눈금)")
        
        # 선형 스케일 적용 (균등한 간격)
        ax1.set_yscale('linear')
        ax1.set_ylim(y_min, y_max)
        
        # Y축 눈금을 균등한 간격으로 설정 (개수 기반)
        y_ticks = np.linspace(y_min, y_max, tick_count)  # 균등한 간격으로 tick_count개 생성
        ax1.set_yticks(y_ticks)
        ax1.set_yticklabels([f'{int(tick):,}' for tick in y_ticks])
        
        # Y축 레이블 스타일 개선 (천 단위 구분자 강조)
        ax1.tick_params(axis='y', labelsize=10)
        for label in ax1.get_yticklabels():
            label.set_fontweight('bold')
        
        print(f"   ✅ 선형 스케일 적용 완료 (균등한 간격)")
    else:
        print(f"   ⚠️ 가격 데이터가 없어 기본 설정을 사용합니다.")
    
    # 메인 차트 설정
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax1.yaxis.set_label_position('right')
    ax1.yaxis.tick_right()
    
    # 2. 거래량 차트 (두 번째 패널) - 웹 트레이딩 스타일 유지
    ax2 = axes[1]
    
    # 거래량 차트 그리기 (거래정지 기간 처리)
    colors = []
    volumes = []
    for i, (date, row) in enumerate(df.iterrows()):
        # 거래정지 기간 감지
        is_trading_suspension = detect_trading_suspension(row, df)
        
        if is_trading_suspension:
            # 거래정지 기간: 완전히 숨김 (크기 0)
            colors.append('#FFFFFF')  # 투명하게 (흰색)
            volumes.append(0)  # 크기 0
        else:
            # 일반 거래일: 상승/하락에 따른 색상
            if row['Close'] >= row['Open']:
                colors.append('#FF4444')  # 빨간색
            else:
                colors.append('#4444FF')  # 파란색
            volumes.append(row['Volume'])
    
    ax2.bar(range(len(df)), volumes, color=colors, alpha=0.7, width=0.8)
    # 거래량 이동평균선 추가
    ax2.plot(range(len(df)), df['Volume_MA12'], color='#F59E0B', linewidth=2.0, alpha=0.9, label='거래량 MA12', marker='None', linestyle='-')
    ax2.set_title('12개월 이동평균이 포함된 거래량', fontsize=12, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=9, framealpha=0.9)
    ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax2.yaxis.set_label_position('right')
    ax2.yaxis.tick_right()
    
    # 3. MACD 차트 (세 번째 패널) - 웹 트레이딩 스타일 유지
    ax3 = axes[2]
    ax3.plot(range(len(df)), df['MACD'], color='#3B82F6', linewidth=2.0, label='MACD', marker='None', linestyle='-')
    ax3.plot(range(len(df)), df['MACD_Signal'], color='#EF4444', linewidth=2.0, alpha=0.8, label='Signal', marker='None', linestyle='-')
    ax3.bar(range(len(df)), df['MACD_Histogram'], color='#10B981', alpha=0.6, width=0.8, label='Histogram')
    ax3.axhline(y=0, color='#6B7280', linestyle='-', alpha=0.6, linewidth=1.0, label='제로선')
    ax3.set_title('MACD (이동평균수렴확산)', fontsize=12, fontweight='bold')
    ax3.legend(loc='upper left', fontsize=10, framealpha=0.9)  # 왼쪽 정렬로 변경
    ax3.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Y축을 오른쪽으로 이동
    ax3.yaxis.set_label_position('right')
    ax3.yaxis.tick_right()
    
    # 4. RSI 차트 (네 번째 패널) - 웹 트레이딩 스타일 유지
    ax4 = axes[3]
    ax4.plot(range(len(df)), df['RSI'], color='#8B5CF6', linewidth=2.0, label='RSI', marker='None', linestyle='-')
    ax4.axhline(y=70, color='#EF4444', linestyle='--', alpha=0.8, linewidth=1.5, label='과매수')
    ax4.axhline(y=30, color='#10B981', linestyle='--', alpha=0.8, linewidth=1.5, label='과매도')
    ax4.axhline(y=50, color='#6B7280', linestyle='-', alpha=0.6, linewidth=1.0, label='중립')
    ax4.fill_between(range(len(df)), 70, 100, alpha=0.1, color='#EF4444', label='과매수 구간')
    ax4.fill_between(range(len(df)), 0, 30, alpha=0.1, color='#10B981', label='과매도 구간')
    ax4.set_title('RSI (상대강도지수)', fontsize=12, fontweight='bold')
    ax4.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax4.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax4.set_ylim(0, 100)  # RSI는 0-100 범위
    
    # Y축을 오른쪽으로 이동
    ax4.yaxis.set_label_position('right')
    ax4.yaxis.tick_right()
    
    # X축 날짜 설정 - 하단에만 표시 (스타일 변경: 글자 크기 50% 증가, 가로 표시)
    for i, ax in enumerate(axes):
        if i == len(axes) - 1:  # 마지막 패널에만 날짜 표시
            ax.set_xticks([0, len(df)//4, len(df)//2, 3*len(df)//4, len(df)-1])
            # 글자 크기 50% 증가 (기본 10에서 15로), 대각선에서 가로로 변경 (rotation=0)
            ax.set_xticklabels([
                df.index[0].strftime('%Y-%m'),
                df.index[len(df)//4].strftime('%Y-%m'),
                df.index[len(df)//2].strftime('%Y-%m'),
                df.index[3*len(df)//4].strftime('%Y-%m'),
                df.index[-1].strftime('%Y-%m')
            ], rotation=0, ha='center', fontweight='bold', fontsize=15)
        else:
            ax.set_xticks([])  # 다른 패널은 X축 눈금 숨김
    
    plt.tight_layout()
    
    # 차트를 이미지로 저장
    
    # improved_monthly_charts 폴더 생성
    charts_dir = "improved_monthly_charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
        print(f"📁 {charts_dir} 폴더를 생성했습니다.")
    
    # 파일명 생성: improved_monthly_종목명_종목코드_생성일.png (차트 제목에서 가져온 종목명 사용)
    current_date = datetime.now().strftime("%Y%m%d")
    # 종목명에서 띄어쓰기 제거하여 파일명 생성
    base_filename = f"improved_monthly_{chart_stock_name.replace(' ', '')}_{stock_code}_{current_date}.png"
    
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
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    print(f"💾 개선된 차트가 저장되었습니다: {filepath}")
    
    # 차트 뷰어를 띄우지 않고 차트 닫기
    plt.close(fig)  # 특정 figure 닫기
    plt.close('all')  # 모든 figure 닫기
    
    # 메모리 정리
    import gc
    gc.collect()
    
    # 차트 데이터 반환 (보조지표 포함) - 일봉 분석과 동일한 패턴
    return filepath, chart_stock_name, df

def get_improved_monthly_stock_data(stock_code):
    """개선된 국내 주식 월봉 데이터 조회 (10년/120개월+) - DB에서 조회"""
    print(f"🔍 {stock_code} 10년(120개월+) 월봉 시세 조회 중...")
    print("   📅 월봉 데이터는 거래일 기준으로 제공되며, 월말 기준으로 집계됩니다.")
    
    # DB에서 월봉 데이터 조회 시도
    db_monthly_data = get_monthly_stock_data_from_db(stock_code)
    if db_monthly_data is not None and not db_monthly_data.empty:
        print(f"   ✅ DB에서 월봉 데이터 조회 완료")
        return db_monthly_data
    
    # DB에서 실패한 경우 오류 메시지 출력
    print(f"   ⚠️ DB에서 월봉 데이터 조회 실패")
    print("❌ 월봉 데이터 조회에 실패했습니다.")
    print("💡 가능한 원인:")
    print("   - 종목코드가 잘못되었습니다")
    print("   - 해당 종목이 상장폐지되었습니다")
    print("   - DB에 월봉 데이터가 수집되지 않았습니다")
    print("   - 데이터베이스 연결에 문제가 있습니다")
    return None

def main():
    """메인 함수"""
    print("🚀 개선된 국내 주식 월봉 시세 조회 프로그램 (Y축 자동 조정 + 로그 스케일)")
    print("="*80)
    
    # 종목코드 입력
    while True:
        stock_code = input("📈 종목코드를 입력하세요 (예: 210120): ").strip()
        if len(stock_code) == 6 and (stock_code.isdigit() or stock_code.isalnum()):
            break
        else:
            print("❌ 올바른 종목코드를 입력해주세요 (6자리 숫자 또는 영문+숫자)")
    
    # 월봉 데이터 조회
    hist = get_improved_monthly_stock_data(stock_code)
    
    if hist is not None:
        # 개선된 월봉 차트 생성
        chart_result = create_improved_monthly_stock_chart(hist, stock_code)
        
        if chart_result and len(chart_result) == 3:
            chart_path, stock_name, chart_data = chart_result
            print(f"🏢 종목명: {stock_name}")
            print(f"\n✅ 개선된 월봉 분석이 완료되었습니다!")
            print(f"📈 개선된 차트 이미지: {chart_path}")
            print(f"\n🔍 개선 사항:")
            print(f"   - Y축 범위 자동 조정 (데이터 기반)")
            print(f"   - 로그 스케일 적용 (네이버 차트와 동일)")
            print(f"   - 최고가/최저가 완전 표시")
        else:
            print(f"\n❌ 개선된 차트 생성에 실패했습니다.")
    else:
        print("\n❌ 월봉 데이터 조회에 실패했습니다.")

if __name__ == "__main__":
    main()
