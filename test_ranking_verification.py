#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from api.volume_ranking_utils import VolumeRankingDataManager
from datetime import datetime

def test_ranking_verification():
    volume_manager = VolumeRankingDataManager()
    
    # 2025년 35주차 (2025-08-25 ~ 2025-08-31) 데이터 조회
    week_start = '2025-08-25'
    
    print('=== 2025년 35주차 랭킹 검증 ===')
    print(f'주차: {week_start} ~ 2025-08-31')
    print()
    
    # 1. 거래량 랭킹 조회
    print('--- 거래량 랭킹 (상위 10개) ---')
    volume_ranking = volume_manager.get_weekly_volume_ranking(week_start, 10)
    for i, item in enumerate(volume_ranking):
        print(f"{i+1:2d}위: {item['stock_code']} {item['stock_name']} - {item['volume']:,}")
        if item['stock_code'] == '044180':
            print(f"    → 044180 종목 발견: 거래량 랭킹 {i+1}위")
    
    print()
    
    # 2. 거래률 랭킹 조회
    print('--- 거래률 랭킹 (상위 10개) ---')
    turnover_ranking = volume_manager.get_weekly_turnover_ranking(week_start, 10)
    for i, item in enumerate(turnover_ranking):
        print(f"{i+1:2d}위: {item['stock_code']} {item['stock_name']} - {item['turnover_rate']:.2f}%")
        if item['stock_code'] == '044180':
            print(f"    → 044180 종목 발견: 거래률 랭킹 {i+1}위")
    
    print()
    
    # 3. 044180 종목 상세 정보
    print('--- 044180 종목 상세 정보 ---')
    for item in volume_ranking:
        if item['stock_code'] == '044180':
            print(f"거래량 랭킹: {volume_ranking.index(item) + 1}위")
            print(f"거래량: {item['volume']:,}")
            break
    
    for item in turnover_ranking:
        if item['stock_code'] == '044180':
            print(f"거래률 랭킹: {turnover_ranking.index(item) + 1}위")
            print(f"거래률: {item['turnover_rate']:.2f}%")
            break

if __name__ == "__main__":
    test_ranking_verification()
