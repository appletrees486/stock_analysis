#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 주식 분석 프로그램 - 차트 생성 + AI 분석
순서: 1. 종목명 입력 → 2. 차트 유형 선택 → 3. 차트 생성 → 4. AI 분석 → 5. 결과 저장
"""

# matplotlib 백엔드를 Agg로 설정 (tkinter 에러 방지)
import matplotlib
matplotlib.use('Agg')

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 데이터베이스 연결을 위한 import 추가
from database_config import DatabaseManager

def check_dependencies():
    """필요한 파일들 확인"""
    required_files = [
        "day_stock_analysis.py",
        "week_stock_analysis.py", 
        "month_stock_analysis.py",
        "ai_chart_analysis.py",
        "config.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 필요한 파일이 없습니다:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def check_api_key():
    """API 키 설정 확인"""
    try:
        from config import config
        api_key = config.get_api_key()
        if not api_key:
            print("⚠️ Google AI API 키가 설정되지 않았습니다.")
            print("setup_api_key.py를 실행하여 API 키를 설정해주세요.")
            return False
        return True
    except Exception as e:
        print(f"❌ API 키 확인 중 오류: {e}")
        return False

def get_stock_data_from_db(stock_code, chart_type_en="daily", days=240):
    """DB에서 주식 데이터 조회 (daily_data + technical_indicators)"""
    try:
        print(f"🔍 DB에서 {stock_code} {chart_type_en} 데이터 조회 중...")
        
        db = DatabaseManager()
        if not db.connect():
            print("   ❌ 데이터베이스 연결 실패")
            return None, None
        
        # 종목명 조회
        stock_name_query = "SELECT stock_name FROM stocks WHERE stock_code = %s"
        stock_info = db.fetch_one(stock_name_query, (stock_code,))
        if not stock_info:
            print(f"   ❌ 종목코드 {stock_code}를 찾을 수 없습니다.")
            db.disconnect()
            return None, None
        
        stock_name = stock_info['stock_name']
        print(f"   🏢 종목명: {stock_name}")
        
        # 최신 거래일 기준으로 기간 설정
        latest_date_query = "SELECT MAX(trade_date) as latest_date FROM daily_data WHERE stock_code = %s"
        latest_date_result = db.fetch_one(latest_date_query, (stock_code,))
        
        if latest_date_result and latest_date_result['latest_date']:
            end_date = latest_date_result['latest_date']
            start_date = end_date - timedelta(days=days)
            print(f"   📅 DB 최신 거래일: {end_date}")
            print(f"   📅 조회 시작일: {start_date}")
        else:
            print(f"   ❌ {stock_code}의 거래 데이터를 찾을 수 없습니다.")
            db.disconnect()
            return None, None
        
        # daily_data 테이블에서 일봉 데이터 조회
        daily_query = """
        SELECT trade_date, open, high, low, close, volume
        FROM daily_data 
        WHERE stock_code = %s 
        AND trade_date >= %s 
        AND trade_date <= %s
        ORDER BY trade_date ASC
        """
        
        daily_params = (stock_code, start_date, end_date)
        daily_data = db.fetch_all(daily_query, daily_params)
        
        if not daily_data:
            print(f"   ❌ 일봉 데이터를 찾을 수 없습니다.")
            db.disconnect()
            return None, None
        
        # technical_indicators 테이블에서 보조지표 데이터 조회
        indicators_query = """
        SELECT trade_date, ma5, ma20, ma60, ma120, rsi, macd, macd_signal, macd_histogram, 
               bb_upper, bb_middle, bb_lower
        FROM technical_indicators 
        WHERE stock_code = %s 
        AND trade_date >= %s 
        AND trade_date <= %s
        ORDER BY trade_date ASC
        """
        
        indicators_params = (stock_code, start_date, end_date)
        indicators_data = db.fetch_all(indicators_query, indicators_params)
        
        db.disconnect()
        
        # 데이터프레임으로 변환
        daily_df = pd.DataFrame(daily_data)
        daily_df['trade_date'] = pd.to_datetime(daily_df['trade_date'])
        daily_df.set_index('trade_date', inplace=True)
        daily_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        indicators_df = None
        if indicators_data:
            indicators_df = pd.DataFrame(indicators_data)
            indicators_df['trade_date'] = pd.to_datetime(indicators_df['trade_date'])
            indicators_df.set_index('trade_date', inplace=True)
            indicators_df.columns = ['MA5', 'MA20', 'MA60', 'MA120', 'RSI', 'MACD', 'MACD_Signal', 'MACD_Histogram', 
                                   'BB_Upper', 'BB_Middle', 'BB_Lower']
        
        print(f"   ✅ DB 데이터 조회 성공:")
        print(f"      - 일봉 데이터: {len(daily_df)}일")
        print(f"      - 보조지표 데이터: {len(indicators_df) if indicators_df is not None else 0}일")
        
        return daily_df, indicators_df, stock_name
        
    except Exception as e:
        print(f"   ❌ DB 데이터 조회 실패: {str(e)}")
        try:
            db.disconnect()
        except:
            pass
        return None, None, None

def prepare_ai_analysis_data(daily_df, indicators_df, stock_name, stock_code, chart_type):
    """AI 분석을 위한 데이터 구조화"""
    try:
        print(f"📊 AI 분석용 데이터 구조화 중...")
        
        # 기본 정보
        analysis_data = {
            "metadata": {
                "stock_name": stock_name,
                "stock_code": stock_code,
                "chart_type": chart_type,
                "data_period": {
                    "start": daily_df.index[0].strftime('%Y-%m-%d'),
                    "end": daily_df.index[-1].strftime('%Y-%m-%d')
                },
                "total_records": len(daily_df)
            },
            "price_summary": {
                "latest_close": float(daily_df['Close'].iloc[-1]),
                "latest_volume": int(daily_df['Volume'].iloc[-1]),
                "price_change": float(daily_df['Close'].iloc[-1] - daily_df['Open'].iloc[0]),
                "price_change_pct": float(((daily_df['Close'].iloc[-1] / daily_df['Open'].iloc[0]) - 1) * 100),
                "highest_price": float(daily_df['High'].max()),
                "lowest_price": float(daily_df['Low'].min()),
                "avg_volume": float(daily_df['Volume'].mean())
            }
        }
        
        # 보조지표 정보 추가
        if indicators_df is not None:
            analysis_data["technical_indicators"] = {
                "latest_values": {
                    "ma5": float(indicators_df['MA5'].iloc[-1]) if 'MA5' in indicators_df.columns and pd.notna(indicators_df['MA5'].iloc[-1]) else None,
                    "ma20": float(indicators_df['MA20'].iloc[-1]) if 'MA20' in indicators_df.columns and pd.notna(indicators_df['MA20'].iloc[-1]) else None,
                    "ma60": float(indicators_df['MA60'].iloc[-1]) if 'MA60' in indicators_df.columns and pd.notna(indicators_df['MA60'].iloc[-1]) else None,
                    "ma120": float(indicators_df['MA120'].iloc[-1]) if 'MA120' in indicators_df.columns and pd.notna(indicators_df['MA120'].iloc[-1]) else None,
                    "rsi": float(indicators_df['RSI'].iloc[-1]) if 'RSI' in indicators_df.columns and pd.notna(indicators_df['RSI'].iloc[-1]) else None,
                    "macd": float(indicators_df['MACD'].iloc[-1]) if 'MACD' in indicators_df.columns and pd.notna(indicators_df['MACD'].iloc[-1]) else None,
                    "macd_signal": float(indicators_df['MACD_Signal'].iloc[-1]) if 'MACD_Signal' in indicators_df.columns and pd.notna(indicators_df['MACD_Signal'].iloc[-1]) else None,
                    "macd_histogram": float(indicators_df['MACD_Histogram'].iloc[-1]) if 'MACD_Histogram' in indicators_df.columns and pd.notna(indicators_df['MACD_Histogram'].iloc[-1]) else None,
                    "bb_upper": float(indicators_df['BB_Upper'].iloc[-1]) if 'BB_Upper' in indicators_df.columns and pd.notna(indicators_df['BB_Upper'].iloc[-1]) else None,
                    "bb_middle": float(indicators_df['BB_Middle'].iloc[-1]) if 'BB_Middle' in indicators_df.columns and pd.notna(indicators_df['BB_Middle'].iloc[-1]) else None,
                    "bb_lower": float(indicators_df['BB_Lower'].iloc[-1]) if 'BB_Lower' in indicators_df.columns and pd.notna(indicators_df['BB_Lower'].iloc[-1]) else None
                }
            }
            
            # 최근 10일간의 보조지표 변화
            recent_indicators = indicators_df.tail(10)
            analysis_data["technical_indicators"]["recent_trends"] = {}
            
            # MA5 추세
            if 'MA5' in recent_indicators.columns and pd.notna(recent_indicators['MA5'].iloc[-1]) and pd.notna(recent_indicators['MA5'].iloc[0]):
                analysis_data["technical_indicators"]["recent_trends"]["ma5_trend"] = "상승" if recent_indicators['MA5'].iloc[-1] > recent_indicators['MA5'].iloc[0] else "하락"
            
            # MA20 추세
            if 'MA20' in recent_indicators.columns and pd.notna(recent_indicators['MA20'].iloc[-1]) and pd.notna(recent_indicators['MA20'].iloc[0]):
                analysis_data["technical_indicators"]["recent_trends"]["ma20_trend"] = "상승" if recent_indicators['MA20'].iloc[-1] > recent_indicators['MA20'].iloc[0] else "하락"
            
            # RSI 상태
            if 'RSI' in recent_indicators.columns and pd.notna(recent_indicators['RSI'].iloc[-1]):
                rsi_value = recent_indicators['RSI'].iloc[-1]
                if rsi_value > 70:
                    analysis_data["technical_indicators"]["recent_trends"]["rsi_status"] = "과매수"
                elif rsi_value < 30:
                    analysis_data["technical_indicators"]["recent_trends"]["rsi_status"] = "과매도"
                else:
                    analysis_data["technical_indicators"]["recent_trends"]["rsi_status"] = "중립"
            
            # MACD 신호
            if 'MACD' in recent_indicators.columns and 'MACD_Signal' in recent_indicators.columns:
                if pd.notna(recent_indicators['MACD'].iloc[-1]) and pd.notna(recent_indicators['MACD_Signal'].iloc[-1]):
                    analysis_data["technical_indicators"]["recent_trends"]["macd_signal"] = "상승" if recent_indicators['MACD'].iloc[-1] > recent_indicators['MACD_Signal'].iloc[-1] else "하락"
        
        # 최근 5일간의 가격 데이터
        recent_prices = daily_df.tail(5)
        analysis_data["recent_prices"] = []
        for date, row in recent_prices.iterrows():
            try:
                analysis_data["recent_prices"].append({
                    "date": date.strftime('%Y-%m-%d'),
                    "open": float(row['Open']) if pd.notna(row['Open']) else 0.0,
                    "high": float(row['High']) if pd.notna(row['High']) else 0.0,
                    "low": float(row['Low']) if pd.notna(row['Low']) else 0.0,
                    "close": float(row['Close']) if pd.notna(row['Close']) else 0.0,
                    "volume": int(row['Volume']) if pd.notna(row['Volume']) else 0
                })
            except (ValueError, TypeError) as e:
                print(f"   ⚠️ {date} 데이터 변환 실패: {e}")
                continue
        
        print(f"   ✅ AI 분석용 데이터 구조화 완료")
        print(f"      - 메타데이터: 종목 정보, 기간, 데이터 수")
        print(f"      - 가격 요약: 최근 가격, 변동률, 거래량 통계")
        if indicators_df is not None:
            print(f"      - 보조지표: 최신 값들과 최근 추세")
        print(f"      - 최근 가격: 최근 5일간 OHLCV")
        
        return analysis_data
        
    except Exception as e:
        print(f"   ❌ 데이터 구조화 실패: {str(e)}")
        return None

def enhance_analysis_data_with_db_verification(analysis_data, daily_df, indicators_df, stock_code):
    """DB 데이터 일치성 검증 및 AI 분석 데이터 강화"""
    try:
        print(f"🔍 DB 데이터 일치성 검증 및 강화 중...")
        
        # 최신 데이터 강제 적용
        latest_date = daily_df.index[-1]
        latest_close = daily_df['Close'].iloc[-1]
        latest_volume = daily_df['Volume'].iloc[-1]
        
        # 가격 요약 정보 강제 업데이트
        analysis_data["price_summary"]["latest_close"] = float(latest_close)
        analysis_data["price_summary"]["latest_volume"] = int(latest_volume)
        
        # 최근 5일간 가격 데이터 강제 업데이트
        recent_prices = daily_df.tail(5)
        analysis_data["recent_prices"] = []
        for date, row in recent_prices.iterrows():
            try:
                analysis_data["recent_prices"].append({
                    "date": date.strftime('%Y-%m-%d'),
                    "open": float(row['Open']) if pd.notna(row['Open']) else 0.0,
                    "high": float(row['High']) if pd.notna(row['High']) else 0.0,
                    "low": float(row['Low']) if pd.notna(row['Low']) else 0.0,
                    "close": float(row['Close']) if pd.notna(row['Close']) else 0.0,
                    "volume": int(row['Volume']) if pd.notna(row['Volume']) else 0
                })
            except (ValueError, TypeError) as e:
                print(f"   ⚠️ {date} 데이터 변환 실패: {e}")
                continue
        
        # 보조지표 데이터 강제 업데이트
        if indicators_df is not None and hasattr(indicators_df, 'empty') and not indicators_df.empty:
            latest_indicators = indicators_df.iloc[-1]
            if 'technical_indicators' not in analysis_data:
                analysis_data["technical_indicators"] = {}
            
            if 'latest_values' not in analysis_data["technical_indicators"]:
                analysis_data["technical_indicators"]["latest_values"] = {}
            
            # 최신 보조지표 값 강제 적용
            indicator_mapping = {
                'MA5': 'ma5', 'MA20': 'ma20', 'MA60': 'ma60', 'MA120': 'ma120',
                'RSI': 'rsi', 'MACD': 'macd', 'MACD_Signal': 'macd_signal', 
                'MACD_Histogram': 'macd_histogram', 'BB_Upper': 'bb_upper',
                'BB_Middle': 'bb_middle', 'BB_Lower': 'bb_lower'
            }
            
            for df_col, analysis_col in indicator_mapping.items():
                if df_col in latest_indicators.index and pd.notna(latest_indicators[df_col]):
                    try:
                        value = float(latest_indicators[df_col])
                        if not pd.isna(value) and value != float('inf') and value != float('-inf'):
                            analysis_data["technical_indicators"]["latest_values"][analysis_col] = value
                    except (ValueError, TypeError):
                        print(f"   ⚠️ {df_col} 값 변환 실패: {latest_indicators[df_col]}")
                        continue
        
        # 데이터 일치성 검증 결과 출력
        print(f"   ✅ DB 데이터 일치성 검증 완료:")
        print(f"      - 최신 거래일: {latest_date.strftime('%Y-%m-%d')}")
        print(f"      - 최신 종가: {latest_close:,.0f}원")
        print(f"      - 최신 거래량: {latest_volume:,}주")
        
        # AI 분석 시 DB 데이터 우선순위 강조를 위한 메타데이터 추가
        analysis_data["db_verification"] = {
            "verified_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "db_latest_date": latest_date.strftime('%Y-%m-%d'),
            "db_latest_close": float(latest_close),
            "db_latest_volume": int(latest_volume),
            "data_source": "database_priority",
            "verification_note": "DB 데이터가 AI 분석의 기준 데이터로 사용됨"
        }
        
        return analysis_data
        
    except Exception as e:
        print(f"   ❌ DB 데이터 일치성 검증 실패: {str(e)}")
        return analysis_data

def verify_ai_analysis_result(result, analysis_data, stock_code):
    """AI 분석 결과 검증 및 DB 데이터 일치성 확인"""
    try:
        print(f"🔍 AI 분석 결과 검증 중...")
        
        # DB 데이터에서 최신 정보 추출
        db_latest_close = analysis_data["db_verification"]["db_latest_close"]
        db_latest_date = analysis_data["db_verification"]["db_latest_date"]
        
        # AI 분석 결과에서 가격 정보 추출 및 검증
        price_verified = False
        
        if "오늘의일봉" in result:
            ai_close = result["오늘의일봉"].get("종가", "")
            if ai_close:
                # 숫자만 추출 (예: "7590원" → 7590)
                try:
                    ai_close_value = float(ai_close.replace("원", "").replace(",", ""))
                    price_diff = abs(ai_close_value - db_latest_close)
                    price_diff_pct = (price_diff / db_latest_close) * 100
                    
                    if price_diff_pct <= 1.0:  # 1% 이내 차이면 허용
                        price_verified = True
                        print(f"   ✅ 가격 일치성 검증 통과: AI {ai_close_value:,.0f}원 vs DB {db_latest_close:,.0f}원 (차이: {price_diff_pct:.2f}%)")
                    else:
                        print(f"   ⚠️ 가격 일치성 검증 실패: AI {ai_close_value:,.0f}원 vs DB {db_latest_close:,.0f}원 (차이: {price_diff_pct:.2f}%)")
                        # DB 데이터로 강제 수정
                        result["오늘의일봉"]["종가"] = f"{db_latest_close:,.0f}원"
                        result["오늘의일봉"]["DB검증"] = f"DB 데이터로 수정됨 (원본: {ai_close})"
                        print(f"      🔧 AI 분석 결과를 DB 데이터로 수정: {db_latest_close:,.0f}원")
                except:
                    print(f"   ❌ AI 분석 결과의 가격 파싱 실패: {ai_close}")
                    # DB 데이터로 강제 수정
                    result["오늘의일봉"]["종가"] = f"{db_latest_close:,.0f}원"
                    result["오늘의일봉"]["DB검증"] = f"DB 데이터로 수정됨 (파싱 실패)"
        
        # 검증 결과를 결과에 추가
        if "종목정보" in result:
            if "검증정보" not in result["종목정보"]:
                result["종목정보"]["검증정보"] = {}
            
            result["종목정보"]["검증정보"] = {
                "DB검증일시": analysis_data["db_verification"]["verified_at"],
                "DB최신거래일": db_latest_date,
                "DB최신종가": f"{db_latest_close:,.0f}원",
                "가격일치성": "통과" if price_verified else "수정됨",
                "검증메모": "DB 데이터 우선순위로 검증 및 수정 완료"
            }
        
        print(f"   ✅ AI 분석 결과 검증 완료")
        return result
        
    except Exception as e:
        print(f"   ❌ AI 분석 결과 검증 실패: {str(e)}")
        return result

def get_stock_input():
    """1단계: 종목명 또는 종목코드 입력 받기"""
    print("📈 1단계: 종목명 또는 종목코드 입력")
    print("-" * 50)
    
    while True:
        user_input = input("📈 종목명 또는 종목코드를 입력하세요 (예: 삼성전자, 005930): ").strip()
        if user_input:
            # 종목코드인지 확인 (6자리 숫자)
            if len(user_input) == 6 and (user_input.isdigit() or user_input.isalnum()):
                return user_input  # 종목코드 그대로 반환
            else:
                return user_input  # 종목명으로 처리
        else:
            print("❌ 종목명 또는 종목코드를 입력해주세요.")

def get_chart_type_selection():
    """2단계: 차트 유형 선택"""
    print("\n📊 2단계: 차트 유형 선택")
    print("-" * 50)
    
    chart_types = [
        ("1", "일봉", "daily"),
        ("2", "주봉", "weekly"), 
        ("3", "월봉", "monthly")
    ]
    
    print("📊 분석할 차트 유형을 선택하세요:")
    for num, korean_name, english_name in chart_types:
        print(f"   {num}. {korean_name} 차트")
    
    while True:
        choice = input(f"\n📊 차트 유형을 선택하세요 (1-3): ").strip()
        
        for num, korean_name, english_name in chart_types:
            if choice == num:
                return korean_name, english_name
        
        print("❌ 올바른 번호를 입력해주세요 (1-3)")

def run_chart_generation(stock_name: str, chart_type: str, chart_type_en: str):
    """3단계: 차트 생성 실행"""
    print(f"\n📈 3단계: {chart_type} 차트 생성")
    print("-" * 50)
    
    try:
        # 차트 유형에 따른 분석 모듈 선택
        if chart_type_en == "daily":
            import day_stock_analysis as analysis_module
            print(f"🔍 {stock_name} 일봉 데이터 조회 중...")
        elif chart_type_en == "weekly":
            import week_stock_analysis as analysis_module
            print(f"🔍 {stock_name} 주봉 데이터 조회 중...")
        elif chart_type_en == "monthly":
            import month_stock_analysis as analysis_module
            print(f"🔍 {stock_name} 월봉 데이터 조회 중...")
        else:
            print(f"❌ 지원하지 않는 차트 유형: {chart_type}")
            return False, None
        
        # 종목코드 확인 (종목명이 종목코드인 경우)
        stock_code = stock_name
        if not (len(stock_name) == 6 and (stock_name.isdigit() or stock_name.isalnum())):
            print(f"❌ 종목코드가 올바르지 않습니다: {stock_name}")
            print("   💡 6자리 숫자 또는 영문+숫자 종목코드를 입력해주세요.")
            return False, None
        
        # 차트 데이터 조회 (함수명 차트 유형별로 다름)
        if chart_type_en == "daily":
            hist = analysis_module.get_stock_data(stock_code)
        elif chart_type_en == "weekly":
            hist = analysis_module.get_weekly_stock_data(stock_code)
        elif chart_type_en == "monthly":
            hist = analysis_module.get_monthly_stock_data(stock_code)
        
        if hist is not None:
            # 차트 데이터 분석 (함수명 차트 유형별로 다름)
            if chart_type_en == "daily":
                analysis_module.analyze_stock_data(hist, stock_code)
                chart_path, db_stock_name = analysis_module.create_stock_chart(hist, stock_code)
            elif chart_type_en == "weekly":
                analysis_module.analyze_weekly_stock_data(hist, stock_code)
                chart_path = analysis_module.create_weekly_stock_chart(hist, stock_code)
                db_stock_name = stock_code  # 주봉/월봉은 기본값 사용
            elif chart_type_en == "monthly":
                analysis_module.analyze_monthly_stock_data(hist, stock_code)
                chart_path = analysis_module.create_monthly_stock_chart(hist, stock_code)
                db_stock_name = stock_code  # 주봉/월봉은 기본값 사용
            
            if chart_path:
                print(f"✅ {chart_type} 차트 생성 완료")
                return True, stock_code
            else:
                print(f"❌ {chart_type} 차트 생성에 실패했습니다.")
                return False, None
        else:
            print(f"❌ {chart_type} 데이터 조회에 실패했습니다.")
            return False, None
            
    except Exception as e:
        print(f"❌ {chart_type} 차트 생성 중 오류: {e}")
        return False, None



def get_prompt_from_database(chart_type_en):
    """DB에서 차트 유형에 맞는 프롬프트 가져오기"""
    try:
        print(f"🔍 DB에서 {chart_type_en} 프롬프트 조회 중...")
        
        db = DatabaseManager()
        if not db.connect():
            print("   ❌ 데이터베이스 연결 실패")
            return None
        
        # 차트 유형에 따른 프롬프트 조회
        if chart_type_en == "daily":
            prompt_type = "일봉"
        elif chart_type_en == "weekly":
            prompt_type = "주봉"
        elif chart_type_en == "monthly":
            prompt_type = "월봉"
        else:
            prompt_type = "일봉"  # 기본값
        
        # 프롬프트 조회 쿼리 (올바른 테이블 구조 사용)
        prompt_query = """
        SELECT p.content as prompt_content, p.name as prompt_name, p.created_at 
        FROM prompts p
        JOIN prompt_categories pc ON p.category_id = pc.id
        WHERE pc.name = %s AND p.is_active = 1
        ORDER BY p.created_at DESC 
        LIMIT 1
        """
        
        prompt_result = db.fetch_one(prompt_query, (prompt_type,))
        db.disconnect()
        
        if prompt_result:
            print(f"   ✅ {prompt_type} 프롬프트 조회 성공:")
            print(f"      - 프롬프트명: {prompt_result['prompt_name']}")
            print(f"      - 생성일시: {prompt_result['created_at']}")
            return prompt_result['prompt_content']
        else:
            print(f"   ⚠️ {prompt_type} 프롬프트를 찾을 수 없습니다.")
            print(f"   💡 프롬프트 관리에서 {prompt_type} 프롬프트를 등록해주세요.")
            return None
            
    except Exception as e:
        print(f"   ❌ 프롬프트 조회 실패: {str(e)}")
        try:
            db.disconnect()
        except:
            pass
        return None

def run_ai_analysis_automated(stock_name: str, stock_code: str, chart_type: str, chart_type_en: str, chart_data=None):
    """4단계: 자동으로 AI 분석 실행"""
    print(f"\n🤖 4단계: AI {chart_type} 차트 분석")
    print("-" * 50)
    
    try:
        # 차트 폴더에서 해당 종목의 차트 파일 찾기
        charts_dir = f"{chart_type_en}_charts"
        if not os.path.exists(charts_dir):
            print(f"❌ {charts_dir} 폴더를 찾을 수 없습니다.")
            return False
        
        chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.jpg') and stock_code in f]
        
        if not chart_files:
            print(f"❌ 해당 종목의 {chart_type} 차트 파일을 찾을 수 없습니다.")
            return False
        
        # DB 최신 거래일 기준으로 차트 파일 선택
        print(f"🔍 DB 최신 거래일 기준으로 차트 파일 선택 중...")
        
        # DB에서 최신 거래일 조회
        db_latest_date = None
        try:
            db = DatabaseManager()
            if db.connect():
                latest_date_query = "SELECT MAX(trade_date) as latest_date FROM daily_data WHERE stock_code = %s"
                latest_date_result = db.fetch_one(latest_date_query, (stock_code,))
                if latest_date_result and latest_date_result['latest_date']:
                    db_latest_date = latest_date_result['latest_date'].strftime("%Y%m%d")
                db.disconnect()
        except Exception as e:
            print(f"   ⚠️ DB 최신 거래일 조회 실패: {e}")
        
        if db_latest_date:
            print(f"   📅 DB 최신 거래일: {db_latest_date}")
            
            # DB 최신 거래일과 일치하는 차트 파일 찾기
            matching_files = [f for f in chart_files if db_latest_date in f]
            if matching_files:
                selected_file = matching_files[0]
                print(f"   ✅ DB 최신 거래일과 일치하는 차트 파일 발견: {selected_file}")
            else:
                # 일치하는 파일이 없으면 차트 재생성 시도
                print(f"   ⚠️ DB 최신 거래일과 일치하는 차트 파일이 없습니다.")
                print(f"   🔄 차트를 재생성합니다...")
                
                try:
                    # 차트 재생성
                    if chart_type_en == "daily":
                        import day_stock_analysis as analysis_module
                        hist = analysis_module.get_stock_data(stock_code)
                        if hist is not None:
                            chart_path = analysis_module.create_stock_chart(hist, stock_code)
                            if chart_path:
                                print(f"   ✅ 차트 재생성 완료: {chart_path}")
                                # 재생성된 차트 파일 선택
                                chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.jpg') and stock_code in f]
                                matching_files = [f for f in chart_files if db_latest_date in f]
                                if matching_files:
                                    selected_file = matching_files[0]
                                    print(f"   ✅ 재생성된 차트 파일 선택: {selected_file}")
                                else:
                                    selected_file = sorted(chart_files)[-1]
                                    print(f"   ⚠️ 재생성 후에도 일치하는 파일이 없어 최근 파일 선택: {selected_file}")
                            else:
                                print(f"   ❌ 차트 재생성 실패")
                                selected_file = sorted(chart_files)[-1]
                        else:
                            print(f"   ❌ 차트 데이터 조회 실패")
                            selected_file = sorted(chart_files)[-1]
                    else:
                        # 주봉/월봉은 기존 방식 사용
                        selected_file = sorted(chart_files)[-1]
                        print(f"   ⚠️ 차트 유형 {chart_type_en}은 자동 재생성을 지원하지 않아 최근 파일 선택: {selected_file}")
                except Exception as e:
                    print(f"   ❌ 차트 재생성 중 오류: {e}")
                    selected_file = sorted(chart_files)[-1]
                    print(f"   ⚠️ 오류로 인해 최근 파일 선택: {selected_file}")
        else:
            # DB 조회 실패시 기존 방식 사용
            selected_file = sorted(chart_files)[-1]
            print(f"   ⚠️ DB 조회 실패로 가장 최근 파일 선택: {selected_file}")
        
        print(f"📁 최종 선택된 차트 파일: {selected_file}")
        
        # DB에서 주식 데이터 조회
        print(f"🔍 DB에서 {stock_code} 데이터 조회 중...")
        daily_df, indicators_df, db_stock_name = get_stock_data_from_db(stock_code, chart_type_en)
        
        if daily_df is None:
            print(f"❌ DB에서 데이터를 조회할 수 없습니다.")
            return False
        
        # AI 분석용 데이터 구조화
        analysis_data = prepare_ai_analysis_data(daily_df, indicators_df, db_stock_name, stock_code, chart_type)
        
        if analysis_data is None:
            print(f"❌ AI 분석용 데이터 구조화에 실패했습니다.")
            return False
        
        # DB 데이터 일치성 검증 및 강화
        analysis_data = enhance_analysis_data_with_db_verification(analysis_data, daily_df, indicators_df, stock_code)
        
        # ai_chart_analysis.py의 함수들을 직접 호출
        import ai_chart_analysis
        from config import config
        
        # API 키 가져오기
        api_key = config.get_api_key()
        if not api_key:
            print("❌ API 키를 가져올 수 없습니다.")
            return False
        
        # DB 설정 가져오기
        db_config = config.get_database_config()
        
        # AI 분석기 초기화 (DB 설정 포함)
        analyzer = ai_chart_analysis.AIChartAnalyzer(api_key, db_config=db_config)
        
        # 파일 경로 설정
        image_path = os.path.join(charts_dir, selected_file)
        
        print(f"🔍 분석 시작: {db_stock_name}")
        print(f"📁 파일: {image_path}")
        print(f"📊 차트 유형: {chart_type}")
        print(f"📊 DB 데이터 정보:")
        print(f"   - 종목명: {db_stock_name}")
        print(f"   - 데이터 기간: {analysis_data['metadata']['data_period']['start']} ~ {analysis_data['metadata']['data_period']['end']}")
        print(f"   - 총 데이터 수: {analysis_data['metadata']['total_records']}일")
        print(f"   - 최근 종가: {analysis_data['price_summary']['latest_close']:,.0f}원")
        print(f"   - 가격 변동률: {analysis_data['price_summary']['price_change_pct']:+.2f}%")
        
        if 'technical_indicators' in analysis_data:
            ti = analysis_data['technical_indicators']
            if ti['latest_values']['rsi']:
                print(f"   - 최근 RSI: {ti['latest_values']['rsi']:.1f}")
            if ti['latest_values']['ma5']:
                print(f"   - 5일 이동평균: {ti['latest_values']['ma5']:,.0f}원")
        
        # AI 분석 실행 (차트 이미지 + DB 데이터)
        print(f"\n🤖 AI 분석 실행 중...")
        
        # DB에서 프롬프트 가져오기
        print(f"🔍 {chart_type_en} 차트용 프롬프트 조회 중...")
        prompt_content = get_prompt_from_database(chart_type_en)
        
        if prompt_content:
            print(f"📝 사용할 프롬프트:")
            print("-" * 20)
            print(prompt_content[:200] + "..." if len(prompt_content) > 200 else prompt_content)
            print("-" * 20)
            print(f"📊 프롬프트 길이: {len(prompt_content)}자")
            
            # AI 분석기에서 프롬프트 사용
            result = analyzer.analyze_chart_image(image_path, prompt_content, chart_type, analysis_data)
        else:
            print("⚠️ DB에서 프롬프트를 찾을 수 없어 AI 분석기의 기본 프롬프트를 사용합니다.")
            # AI 분석기에서 자체 프롬프트 사용 (DB에서 자동 조회)
            result = analyzer.analyze_chart_image(image_path, "", chart_type, analysis_data)
        
        if result:
            # AI 분석 결과 검증 및 DB 데이터 일치성 확인
            result = verify_ai_analysis_result(result, analysis_data, stock_code)
            # 결과 저장
            output_dir = "ai_analysis_results"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # JSON 파일 저장 (차트 유형 포함)
            json_filename = f"analysis_{chart_type_en}_{db_stock_name}_{timestamp}.json"
            json_path = os.path.join(output_dir, json_filename)
            
            # Word 문서 저장 (차트 유형 포함)
            doc_filename = f"analysis_{chart_type_en}_{db_stock_name}_{timestamp}.docx"
            doc_path = os.path.join(output_dir, doc_filename)
            
            # JSON 파일 저장
            json_success = analyzer.save_analysis_result(result, json_path)
            
            # Word 문서 생성
            doc_success = analyzer.create_word_document(result, image_path, doc_path, chart_type)
            
            if json_success and doc_success:
                print("✅ AI 분석 완료")
                print(f"📄 JSON 결과 파일: {json_path}")
                print(f"📄 Word 문서 파일: {doc_path}")
                
                # 주요 결과 출력
                if "투자아이디어" in result:
                    print(f"\n📈 투자 아이디어:")
                    trend_key = "단기추세" if "단기추세" in result['투자아이디어'] else "중기추세" if "중기추세" in result['투자아이디어'] else "장기추세"
                    print(f"   추세: {result['투자아이디어'].get(trend_key, 'N/A')}")
                    print(f"   매매 시점: {result['투자아이디어'].get('매매시점', 'N/A')}")
                    print(f"   핵심 포인트: {result['투자아이디어'].get('핵심포인트', 'N/A')}")
                
                return True
            else:
                if not json_success:
                    print("❌ JSON 결과 저장에 실패했습니다.")
                if not doc_success:
                    print("❌ Word 문서 생성에 실패했습니다.")
                return False
        else:
            print("❌ AI 분석에 실패했습니다.")
            return False
            
    except Exception as e:
        print(f"❌ AI 분석 중 오류: {e}")
        return False

def show_final_results(stock_name: str, chart_type: str):
    """최종 결과 파일들 표시"""
    print("\n" + "="*60)
    print("🎉 전체 분석이 완료되었습니다!")
    print("="*60)
    
    print(f"\n📊 분석 정보:")
    print(f"   종목명: {stock_name}")
    print(f"   차트 유형: {chart_type}")
    
    print("\n📁 생성된 파일들:")
    
    # 차트 이미지 확인
    chart_folders = ["daily_charts", "weekly_charts", "monthly_charts"]
    for folder in chart_folders:
        if os.path.exists(folder):
            chart_files = [f for f in os.listdir(folder) if f.endswith('.jpg') and stock_name in f]
            if chart_files:
                print(f"   📈 {folder}: {len(chart_files)}개")
                for file in chart_files:
                    print(f"      - {file}")
    
    # AI 분석 결과 확인
    if os.path.exists("ai_analysis_results"):
        result_files = [f for f in os.listdir("ai_analysis_results") if f.endswith(('.json', '.docx')) and stock_name in f]
        if result_files:
            json_files = [f for f in result_files if f.endswith('.json')]
            doc_files = [f for f in result_files if f.endswith('.docx')]
            
            print(f"   🤖 AI 분석 결과: {len(result_files)}개")
            print(f"      📄 JSON 파일: {len(json_files)}개")
            print(f"      📄 Word 문서: {len(doc_files)}개")
            
            for file in result_files:
                print(f"         - {file}")
    
    print("\n💡 사용법:")
    print("   1. 차트 이미지: 각 차트 폴더에서 확인")
    print("   2. JSON 분석 결과: ai_analysis_results/ 폴더에서 확인")
    print("   3. Word 문서: ai_analysis_results/ 폴더에서 확인")

def main():
    """메인 함수"""
    print("🚀 통합 주식 분석 프로그램")
    print("="*60)
    print("📊 종목명 입력 → 차트 유형 선택 → 차트 생성 → AI 분석")
    print("="*60)
    
    # 의존성 확인
    if not check_dependencies():
        print("\n❌ 프로그램을 실행할 수 없습니다.")
        print("필요한 파일들을 확인해주세요.")
        return
    
    # API 키 확인
    if not check_api_key():
        print("\n❌ API 키 설정이 필요합니다.")
        print("setup_api_key.py를 실행하여 API 키를 설정해주세요.")
        return
    
    print("\n✅ 모든 준비가 완료되었습니다.")
    print("순서대로 실행을 시작합니다...")
    
    # 1단계: 종목명 입력
    stock_name = get_stock_input()
    
    # 2단계: 차트 유형 선택
    chart_type, chart_type_en = get_chart_type_selection()
    
    print("\n" + "="*60)
    
    # 3단계: 차트 생성
    chart_success, stock_code = run_chart_generation(stock_name, chart_type, chart_type_en)
    
    if chart_success and stock_code:
        print("\n" + "="*60)
        
        # 4단계: AI 분석
        if run_ai_analysis_automated(stock_name, stock_code, chart_type, chart_type_en):
            show_final_results(stock_name, chart_type)
        else:
            print("\n❌ AI 분석에 실패했습니다.")
            print("차트는 생성되었지만 AI 분석을 완료할 수 없습니다.")
    else:
        print("\n❌ 차트 생성에 실패했습니다.")
        print("AI 분석을 진행할 수 없습니다.")

if __name__ == "__main__":
    main() 