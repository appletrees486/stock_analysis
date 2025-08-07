#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 금융 데이터 조회 공통 모듈
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time

def get_naver_stock_data(stock_code):
    """네이버 금융에서 실시간 주식 데이터 조회"""
    try:
        # 네이버 금융 URL
        url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'euc-kr'  # 네이버 금융 인코딩
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 현재가 추출
            current_price_elem = soup.select_one('#chart_area > div.rate_info > div > p.no_today > em > span.blind')
            if current_price_elem:
                current_price = current_price_elem.get_text().strip()
                # 쉼표 제거하고 숫자만 추출
                current_price = re.sub(r'[^\d]', '', current_price)
                current_price = int(current_price) if current_price else 0
            else:
                current_price = 0
            
            # 전일대비 변동 추출
            change_elem = soup.select_one('#chart_area > div.rate_info > div > p.no_exday > em:nth-child(1) > span.blind')
            if change_elem:
                change_text = change_elem.get_text().strip()
                # 상승/하락 여부 확인
                if '상승' in change_text:
                    change_direction = '상승'
                elif '하락' in change_text:
                    change_direction = '하락'
                else:
                    change_direction = '보합'
                
                # 변동폭 추출
                change_amount = re.sub(r'[^\d]', '', change_text)
                change_amount = int(change_amount) if change_amount else 0
            else:
                change_direction = '보합'
                change_amount = 0
            
            # 거래량 추출
            volume_elem = soup.select_one('#chart_area > div.rate_info > table > tbody > tr:nth-child(3) > td:nth-child(2) > span')
            if volume_elem:
                volume_text = volume_elem.get_text().strip()
                volume = re.sub(r'[^\d]', '', volume_text)
                volume = int(volume) if volume else 0
            else:
                volume = 0
            
            # 종목명 추출
            stock_name_elem = soup.select_one('#middle > div.h_company > div.wrap_company > h2 > a')
            if stock_name_elem:
                stock_name = stock_name_elem.get_text().strip()
            else:
                stock_name = f"종목{stock_code}"
            
            return {
                'success': True,
                'stock_name': stock_name,
                'current_price': current_price,
                'change_direction': change_direction,
                'change_amount': change_amount,
                'volume': volume,
                'timestamp': datetime.now(),
                'source': '네이버 금융'
            }
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_naver_historical_data(stock_code, period_days=30):
    """네이버 금융에서 과거 데이터 조회 (일봉 기준)"""
    try:
        # 네이버 금융 일봉 차트 URL
        url = f"https://finance.naver.com/item/sise_day.naver?code={stock_code}&page=1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'euc-kr'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 일봉 데이터 테이블 찾기
            table = soup.select_one('table.type5')
            if not table:
                return {'success': False, 'error': '일봉 데이터 테이블을 찾을 수 없습니다'}
            
            # 데이터 추출
            rows = table.select('tr')[1:]  # 헤더 제외
            data = []
            
            for row in rows:
                cols = row.select('td')
                if len(cols) >= 7:
                    try:
                        date_str = cols[0].get_text().strip()
                        if date_str and date_str != '':
                            # 날짜 파싱
                            date = datetime.strptime(date_str, '%Y.%m.%d')
                            
                            # 가격 데이터 파싱
                            close_price = int(cols[1].get_text().strip().replace(',', ''))
                            change_amount = int(cols[2].get_text().strip().replace(',', ''))
                            open_price = int(cols[3].get_text().strip().replace(',', ''))
                            high_price = int(cols[4].get_text().strip().replace(',', ''))
                            low_price = int(cols[5].get_text().strip().replace(',', ''))
                            volume = int(cols[6].get_text().strip().replace(',', ''))
                            
                            data.append({
                                'Date': date,
                                'Close': close_price,
                                'Change': change_amount,
                                'Open': open_price,
                                'High': high_price,
                                'Low': low_price,
                                'Volume': volume
                            })
                    except (ValueError, IndexError):
                        continue
            
            if data:
                return {
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'source': '네이버 금융'
                }
            else:
                return {'success': False, 'error': '유효한 데이터가 없습니다'}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def compare_data_sources(stock_code):
    """네이버 금융과 Yahoo Finance 데이터 비교"""
    import yfinance as yf
    
    print(f"🔍 {stock_code} 데이터 소스 비교")
    print(f"📅 현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 네이버 금융 데이터 조회
    print("📊 네이버 금융 데이터 조회 중...")
    naver_result = get_naver_stock_data(stock_code)
    
    if naver_result['success']:
        print(f"✅ 네이버 금융:")
        print(f"   🏢 종목명: {naver_result['stock_name']}")
        print(f"   📈 현재가: {naver_result['current_price']:,.0f}원")
        print(f"   📊 변동: {naver_result['change_direction']} {naver_result['change_amount']:+,}원")
        print(f"   📈 거래량: {naver_result['volume']:,.0f}주")
        print(f"   ⏰ 조회시간: {naver_result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"❌ 네이버 금융: {naver_result['error']}")
    
    print()
    
    # Yahoo Finance 데이터 조회
    print("📊 Yahoo Finance 데이터 조회 중...")
    try:
        ticker = f"{stock_code}.KS"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d", interval="1d")
        
        if not hist.empty:
            latest_date = hist.index[-1]
            if hasattr(latest_date, 'tz_localize'):
                latest_date = latest_date.tz_localize(None)
            elif hasattr(latest_date, 'replace'):
                latest_date = latest_date.replace(tzinfo=None)
            
            current_date = datetime.now()
            days_diff = (current_date - latest_date).days
            
            print(f"✅ Yahoo Finance:")
            print(f"   📅 최신 데이터: {latest_date.strftime('%Y-%m-%d')}")
            print(f"   📈 최신 가격: {hist['Close'].iloc[-1]:,.0f}원")
            print(f"   📅 데이터 차이: {days_diff}일")
            print(f"   📊 데이터 수: {len(hist)}일")
            
            # 가격 비교
            if naver_result['success']:
                price_diff = naver_result['current_price'] - hist['Close'].iloc[-1]
                print(f"   💰 가격 차이: {price_diff:+,.0f}원")
                
                if abs(price_diff) < 100:
                    print("   ✅ 가격이 거의 동일합니다 (정상)")
                else:
                    print("   ⚠️ 가격 차이가 있습니다 (업데이트 시점 차이)")
        else:
            print("❌ Yahoo Finance: 데이터 없음")
            
    except Exception as e:
        print(f"❌ Yahoo Finance: {str(e)}")
    
    print()
    print("=" * 80)
    
    # 결론
    print("📋 결론:")
    print("1. 네이버 금융: 실시간에 가까운 데이터 (장 중 실시간 업데이트)")
    print("2. Yahoo Finance: 장 마감 후 업데이트 (2-4시간 지연)")
    print("3. 네이버 금융이 더 최신 데이터를 제공합니다")
    
    return naver_result, hist if 'hist' in locals() else None 