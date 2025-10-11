#!/usr/bin/env python
# -*- coding: utf-8 -*-

from database_config import DatabaseManager

db = DatabaseManager()
db.connect()

print("=" * 80)
print("데이터 수집 품질 검증")
print("=" * 80)

# 1. 전체 종목 vs 수집된 종목
total_stocks = db.fetch_one("SELECT COUNT(*) as cnt FROM stocks WHERE is_active = TRUE")
collected_daily = db.fetch_one("SELECT COUNT(DISTINCT stock_code) as cnt FROM daily_data")
collected_tech = db.fetch_one("SELECT COUNT(DISTINCT stock_code) as cnt FROM technical_indicators")

print(f"\n[종목 수집률]")
print(f"  전체 활성 종목:       {total_stocks['cnt']:,}개")
print(f"  일봉 수집 종목:       {collected_daily['cnt']:,}개")
print(f"  기술지표 수집 종목:   {collected_tech['cnt']:,}개")

daily_rate = (collected_daily['cnt'] / total_stocks['cnt'] * 100) if total_stocks['cnt'] > 0 else 0
tech_rate = (collected_tech['cnt'] / total_stocks['cnt'] * 100) if total_stocks['cnt'] > 0 else 0

print(f"\n  일봉 수집률:   {daily_rate:.2f}%")
print(f"  기술지표 수집률: {tech_rate:.2f}%")

# 2. 데이터 품질 확인 (NULL 값)
daily_quality = db.fetch_one("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN open IS NULL THEN 1 ELSE 0 END) as null_open,
        SUM(CASE WHEN high IS NULL THEN 1 ELSE 0 END) as null_high,
        SUM(CASE WHEN low IS NULL THEN 1 ELSE 0 END) as null_low,
        SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) as null_close,
        SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) as null_volume,
        SUM(CASE WHEN trading_value IS NULL THEN 1 ELSE 0 END) as null_trading
    FROM daily_data
""")

print(f"\n[일봉 데이터 품질]")
print(f"  총 레코드: {daily_quality['total']:,}개")
print(f"  NULL 비율:")
print(f"    - Open:   {daily_quality['null_open']:,}개 ({daily_quality['null_open']/daily_quality['total']*100:.3f}%)")
print(f"    - High:   {daily_quality['null_high']:,}개 ({daily_quality['null_high']/daily_quality['total']*100:.3f}%)")
print(f"    - Low:    {daily_quality['null_low']:,}개 ({daily_quality['null_low']/daily_quality['total']*100:.3f}%)")
print(f"    - Close:  {daily_quality['null_close']:,}개 ({daily_quality['null_close']/daily_quality['total']*100:.3f}%)")
print(f"    - Volume: {daily_quality['null_volume']:,}개 ({daily_quality['null_volume']/daily_quality['total']*100:.3f}%)")
print(f"    - Trading:{daily_quality['null_trading']:,}개 ({daily_quality['null_trading']/daily_quality['total']*100:.3f}%)")

ohlcv_quality = 100 - (daily_quality['null_close'] / daily_quality['total'] * 100)
print(f"\n  OHLCV 데이터 품질: {ohlcv_quality:.2f}%")

# 3. 기술지표 품질
tech_quality = db.fetch_one("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN ma5 IS NULL THEN 1 ELSE 0 END) as null_ma5,
        SUM(CASE WHEN ma20 IS NULL THEN 1 ELSE 0 END) as null_ma20,
        SUM(CASE WHEN ma60 IS NULL THEN 1 ELSE 0 END) as null_ma60,
        SUM(CASE WHEN ma120 IS NULL THEN 1 ELSE 0 END) as null_ma120,
        SUM(CASE WHEN rsi IS NULL THEN 1 ELSE 0 END) as null_rsi,
        SUM(CASE WHEN macd IS NULL THEN 1 ELSE 0 END) as null_macd
    FROM technical_indicators
""")

print(f"\n[기술지표 데이터 품질]")
print(f"  총 레코드: {tech_quality['total']:,}개")
print(f"  NULL 비율:")
print(f"    - MA5:   {tech_quality['null_ma5']:,}개 ({tech_quality['null_ma5']/tech_quality['total']*100:.2f}%)")
print(f"    - MA20:  {tech_quality['null_ma20']:,}개 ({tech_quality['null_ma20']/tech_quality['total']*100:.2f}%)")
print(f"    - MA60:  {tech_quality['null_ma60']:,}개 ({tech_quality['null_ma60']/tech_quality['total']*100:.2f}%)")
print(f"    - MA120: {tech_quality['null_ma120']:,}개 ({tech_quality['null_ma120']/tech_quality['total']*100:.2f}%)")
print(f"    - RSI:   {tech_quality['null_rsi']:,}개 ({tech_quality['null_rsi']/tech_quality['total']*100:.2f}%)")
print(f"    - MACD:  {tech_quality['null_macd']:,}개 ({tech_quality['null_macd']/tech_quality['total']*100:.2f}%)")

# 가장 긴 이동평균인 MA120 기준으로 품질 계산
tech_quality_rate = 100 - (tech_quality['null_ma120'] / tech_quality['total'] * 100)
print(f"\n  기술지표 품질: {tech_quality_rate:.2f}%")

# 4. 일봉 vs 기술지표 레코드 수 비교
print(f"\n[데이터 일치성]")
print(f"  일봉 레코드:     {daily_quality['total']:,}개")
print(f"  기술지표 레코드: {tech_quality['total']:,}개")
diff = tech_quality['total'] - daily_quality['total']
print(f"  차이: {diff:+,}개")

if abs(diff) / daily_quality['total'] < 0.01:  # 1% 이내
    print(f"  [OK] 일치 (차이 {abs(diff)/daily_quality['total']*100:.2f}%)")
else:
    print(f"  [주의] 불일치 (차이 {abs(diff)/daily_quality['total']*100:.2f}%)")

# 5. 최종 점수
print(f"\n" + "=" * 80)
print(f"[최종 수집 품질]")
print(f"  종목 수집률:    {daily_rate:.2f}%")
print(f"  OHLCV 품질:     {ohlcv_quality:.2f}%")
print(f"  기술지표 품질:  {tech_quality_rate:.2f}%")

overall = (daily_rate + ohlcv_quality + tech_quality_rate) / 3
print(f"\n  종합 품질 점수: {overall:.2f}%")

if overall >= 99.9:
    print(f"\n  [완벽!] 99.9% 이상 달성!")
elif overall >= 99.0:
    print(f"\n  [우수] 99% 이상 달성!")
elif overall >= 95.0:
    print(f"\n  [양호] 95% 이상")
else:
    print(f"\n  [개선 필요]")

print("=" * 80)

db.disconnect()

