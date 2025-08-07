#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공공데이터 API 연결 테스트 스크립트
"""

import requests
import json
from datetime import datetime

# 공공데이터 API 설정
API_KEY = "1A4ObzoWfk8XusMwdYIzhsp4F/vPMPCPtuRvV+VJnKsI1YrCzEmwOByBy/Vw1MMbEkNUxVQrZr63qd21UM0sYw=="
BASE_URL = "http://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService"

def test_api_connection():
    """API 연결 테스트"""
    print("🔍 공공데이터 API 연결 테스트")
    print("="*50)
    
    # 현재 날짜
    current_date = datetime.now().strftime("%Y%m%d")
    
    # 테스트할 엔드포인트들
    endpoints = [
        "/getStockPriceInfo",
        "/getStockSecuritiesInfo",
        "/getStockPriceInfoService"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔄 엔드포인트 테스트: {endpoint}")
        
        # 기본 파라미터
        params = {
            'serviceKey': API_KEY,
            'pageNo': '1',
            'numOfRows': '10',
            'resultType': 'json',
            'basDt': current_date
        }
        
        try:
            # HTTP 요청
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                params=params,
                timeout=10
            )
            
            print(f"   📊 상태 코드: {response.status_code}")
            print(f"   📋 응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ JSON 파싱 성공")
                    print(f"   📋 응답 키: {list(data.keys())}")
                    
                    if 'response' in data:
                        print(f"   📋 response 키: {list(data['response'].keys())}")
                        
                        if 'body' in data['response']:
                            body = data['response']['body']
                            print(f"   📋 body 키: {list(body.keys())}")
                            
                            if 'items' in body:
                                items = body['items']
                                if isinstance(items, dict) and 'item' in items:
                                    print(f"   📊 데이터 항목 수: {len(items['item'])}")
                                elif isinstance(items, list):
                                    print(f"   📊 데이터 항목 수: {len(items)}")
                                else:
                                    print(f"   📊 items 타입: {type(items)}")
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON 파싱 실패: {e}")
                    print(f"   📋 응답 내용: {response.text[:200]}...")
            else:
                print(f"   ❌ HTTP 오류: {response.status_code}")
                print(f"   📋 응답 내용: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 요청 오류: {e}")

def test_simple_request():
    """간단한 요청 테스트"""
    print("\n🔍 간단한 요청 테스트")
    print("="*50)
    
    try:
        # 가장 기본적인 요청
        url = "http://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
        params = {
            'serviceKey': API_KEY,
            'pageNo': '1',
            'numOfRows': '1',
            'resultType': 'json'
        }
        
        print(f"🔄 URL: {url}")
        print(f"📋 파라미터: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"📊 상태 코드: {response.status_code}")
        print(f"📋 응답 내용: {response.text[:500]}...")
        
    except Exception as e:
        print(f"❌ 오류: {e}")

def test_stock_data():
    """주식 데이터 테스트"""
    print("\n🔍 주식 데이터 테스트")
    print("="*50)
    
    # 삼성전자 종목코드
    stock_code = "005930"
    
    # 여러 날짜로 테스트
    test_dates = [
        "20250805",  # 어제
        "20250804",  # 그제
        "20250801",  # 지난주 금요일
        "20250731",  # 지난주 목요일
    ]
    
    for test_date in test_dates:
        print(f"\n�� 날짜 테스트: {test_date} (종목코드: {stock_code})")
        
        url = "http://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
        params = {
            'serviceKey': API_KEY,
            'pageNo': '1',
            'numOfRows': '10',
            'resultType': 'json',
            'basDt': test_date,
            'srtnCd': stock_code
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            print(f"   📊 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if 'response' in data and 'body' in data['response']:
                        items = data['response']['body'].get('items', {})
                        
                        if isinstance(items, dict) and 'item' in items:
                            items = items['item']
                        
                        if items and len(items) > 0:
                            print(f"   ✅ 데이터 발견: {len(items)}개 항목")
                            print(f"   📋 첫 번째 항목: {items[0]}")
                            
                            # 삼성전자 데이터인지 확인
                            if items[0].get('srtnCd') == stock_code:
                                print(f"   🎯 삼성전자 데이터 확인!")
                                print(f"   📊 종목명: {items[0].get('itmsNm')}")
                                print(f"   💰 종가: {items[0].get('clpr')}원")
                                print(f"   📈 거래량: {items[0].get('trqu')}주")
                                return True
                            else:
                                print(f"   ⚠️ 다른 종목 데이터: {items[0].get('srtnCd')} - {items[0].get('itmsNm')}")
                        else:
                            print(f"   ⚠️ 데이터 없음")
                    else:
                        print(f"   ❌ 응답 형식 오류")
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON 파싱 실패: {e}")
            else:
                print(f"   ❌ HTTP 오류: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 요청 오류: {e}")
    
    return False

if __name__ == "__main__":
    test_api_connection()
    test_simple_request()
    test_stock_data() 