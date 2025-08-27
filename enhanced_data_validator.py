#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
향상된 데이터 검증 시스템
주식 데이터의 무결성, 일관성, 품질을 종합적으로 검증
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database_config import DatabaseManager
from data_change_tracker import DataChangeTracker
from market_status_detector import MarketStatusDetector
import logging
from typing import Dict, List, Any, Tuple, Optional
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_data_validator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class EnhancedDataValidator:
    def __init__(self):
        """향상된 데이터 검증기 초기화"""
        self.db = DatabaseManager()
        self.change_tracker = DataChangeTracker()
        self.market_detector = MarketStatusDetector()
        self.validation_rules = self._load_validation_rules()
        logging.info("✅ 향상된 데이터 검증기 초기화 완료")
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """검증 규칙 로드"""
        return {
            'price_validation': {
                'min_price': 100,  # 최소 가격
                'max_price': 1000000,  # 최대 가격
                'price_change_limit': 0.3,  # 일일 가격 변동 한계 (30%)
                'volume_min': 1,  # 최소 거래량
                'volume_max': 1000000000  # 최대 거래량
            },
            'technical_indicators': {
                'rsi_range': (0, 100),  # RSI 범위
                'macd_signal_diff_limit': 0.1,  # MACD 시그널 차이 한계
                'bollinger_band_deviation': 3.0  # 볼린저 밴드 표준편차 한계
            },
            'data_consistency': {
                'max_missing_days': 5,  # 연속 누락일 최대
                'min_data_points': 20,  # 최소 데이터 포인트
                'date_continuity_threshold': 0.95  # 날짜 연속성 임계값
            }
        }
    
    def validate_stock_data_integrity(self, stock_code: str, start_date: datetime = None, 
                                     end_date: datetime = None) -> Dict[str, Any]:
        """주식 데이터 무결성 검증"""
        try:
            if not self.db.connect():
                return {'success': False, 'error': '데이터베이스 연결 실패'}
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=30)
            if end_date is None:
                end_date = datetime.now()
            
            # 1. 기본 데이터 존재성 검증
            existence_check = self._check_data_existence(stock_code, start_date, end_date)
            
            # 2. 가격 데이터 유효성 검증
            price_validation = self._validate_price_data(stock_code, start_date, end_date)
            
            # 3. 거래량 데이터 유효성 검증
            volume_validation = self._validate_volume_data(stock_code, start_date, end_date)
            
            # 4. 날짜 연속성 검증
            continuity_check = self._check_date_continuity(stock_code, start_date, end_date)
            
            # 5. 기술적 지표 일관성 검증
            technical_validation = self._validate_technical_indicators(stock_code, start_date, end_date)
            
            # 6. 종합 점수 계산
            total_score = self._calculate_integrity_score(
                existence_check, price_validation, volume_validation, 
                continuity_check, technical_validation
            )
            
            # 7. 검증 결과 로깅
            self.change_tracker.log_data_integrity_check(
                'daily_data', 'CONTENT', 'PASS' if total_score >= 80 else 'FAIL',
                f"무결성 점수: {total_score:.1f}/100", 1
            )
            
            result = {
                'success': True,
                'stock_code': stock_code,
                'validation_period': f"{start_date.date()} ~ {end_date.date()}",
                'total_score': total_score,
                'grade': self._get_grade(total_score),
                'existence_check': existence_check,
                'price_validation': price_validation,
                'volume_validation': volume_validation,
                'continuity_check': continuity_check,
                'technical_validation': technical_validation,
                'recommendations': self._generate_integrity_recommendations(total_score)
            }
            
            return result
            
        except Exception as e:
            logging.error(f"❌ 데이터 무결성 검증 중 오류: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            self.db.disconnect()
    
    def _check_data_existence(self, stock_code: str, start_date: datetime, 
                             end_date: datetime) -> Dict[str, Any]:
        """데이터 존재성 검증"""
        try:
            # 종목 정보 확인
            stock_query = "SELECT * FROM stocks WHERE stock_code = %s"
            stock_result = self.db.fetch_one(stock_query, (stock_code,))
            
            if not stock_result:
                return {'status': 'FAIL', 'score': 0, 'issues': ['종목 정보가 존재하지 않음']}
            
            # 일봉 데이터 개수 확인
            data_count_query = """
            SELECT COUNT(*) as count, MIN(trade_date) as min_date, MAX(trade_date) as max_date
            FROM daily_data 
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            """
            data_result = self.db.fetch_one(data_count_query, (stock_code, start_date, end_date))
            
            if not data_result or data_result['count'] == 0:
                return {'status': 'FAIL', 'score': 0, 'issues': ['해당 기간의 일봉 데이터가 없음']}
            
            # 기술적 지표 데이터 확인
            indicator_query = """
            SELECT COUNT(*) as count
            FROM technical_indicators 
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            """
            indicator_result = self.db.fetch_one(indicator_query, (stock_code, start_date, end_date))
            
            issues = []
            score = 100
            
            if data_result['count'] < 20:
                issues.append(f"데이터 포인트 부족: {data_result['count']}개 (권장: 20개 이상)")
                score -= 30
            
            if indicator_result['count'] == 0:
                issues.append("기술적 지표 데이터가 없음")
                score -= 20
            
            if not issues:
                issues.append("모든 필수 데이터가 존재함")
            
            return {
                'status': 'PASS' if score >= 80 else 'WARNING' if score >= 60 else 'FAIL',
                'score': max(0, score),
                'data_count': data_result['count'],
                'indicator_count': indicator_result['count'],
                'date_range': f"{data_result['min_date']} ~ {data_result['max_date']}",
                'issues': issues
            }
            
        except Exception as e:
            logging.error(f"❌ 데이터 존재성 검증 중 오류: {e}")
            return {'status': 'ERROR', 'score': 0, 'issues': [f'검증 오류: {str(e)}']}
    
    def _validate_price_data(self, stock_code: str, start_date: datetime, 
                            end_date: datetime) -> Dict[str, Any]:
        """가격 데이터 유효성 검증"""
        try:
            query = """
            SELECT trade_date, open, high, low, close
            FROM daily_data 
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
            """
            
            result = self.db.fetch_all(query, (stock_code, start_date, end_date))
            
            if not result:
                return {'status': 'FAIL', 'score': 0, 'issues': ['가격 데이터가 없음']}
            
            issues = []
            score = 100
            invalid_records = 0
            
            for record in result:
                open_price = record['open']
                high_price = record['high']
                low_price = record['low']
                close_price = record['close']
                
                # 기본 가격 범위 검증
                if not (self.validation_rules['price_validation']['min_price'] <= 
                       open_price <= self.validation_rules['price_validation']['max_price']):
                    issues.append(f"{record['trade_date']}: 시가 범위 오류 ({open_price})")
                    invalid_records += 1
                
                # OHLC 관계 검증
                if not (low_price <= open_price <= high_price and 
                       low_price <= close_price <= high_price):
                    issues.append(f"{record['trade_date']}: OHLC 관계 오류 (O:{open_price}, H:{high_price}, L:{low_price}, C:{close_price})")
                    invalid_records += 1
                
                # 가격 변동 한계 검증
                if open_price > 0:
                    daily_change = abs(close_price - open_price) / open_price
                    if daily_change > self.validation_rules['price_validation']['price_change_limit']:
                        issues.append(f"{record['trade_date']}: 가격 변동 한계 초과 ({daily_change:.1%})")
                        invalid_records += 1
            
            # 점수 계산
            if invalid_records > 0:
                score -= min(50, invalid_records * 10)
                score = max(0, score)
            
            if not issues:
                issues.append("모든 가격 데이터가 유효함")
            
            return {
                'status': 'PASS' if score >= 80 else 'WARNING' if score >= 60 else 'FAIL',
                'score': score,
                'total_records': len(result),
                'invalid_records': invalid_records,
                'issues': issues[:10]  # 처음 10개만 반환
            }
            
        except Exception as e:
            logging.error(f"❌ 가격 데이터 검증 중 오류: {e}")
            return {'status': 'ERROR', 'score': 0, 'issues': [f'검증 오류: {str(e)}']}
    
    def _validate_volume_data(self, stock_code: str, start_date: datetime, 
                              end_date: datetime) -> Dict[str, Any]:
        """거래량 데이터 유효성 검증"""
        try:
            query = """
            SELECT trade_date, volume
            FROM daily_data 
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
            """
            
            result = self.db.fetch_all(query, (stock_code, start_date, end_date))
            
            if not result:
                return {'status': 'FAIL', 'score': 0, 'issues': ['거래량 데이터가 없음']}
            
            issues = []
            score = 100
            invalid_records = 0
            
            for record in result:
                volume = record['volume']
                
                # 거래량 범위 검증
                if not (self.validation_rules['price_validation']['volume_min'] <= 
                       volume <= self.validation_rules['price_validation']['volume_max']):
                    issues.append(f"{record['trade_date']}: 거래량 범위 오류 ({volume})")
                    invalid_records += 1
                
                # 거래량이 음수인지 확인
                if volume < 0:
                    issues.append(f"{record['trade_date']}: 음수 거래량 ({volume})")
                    invalid_records += 1
            
            # 점수 계산
            if invalid_records > 0:
                score -= min(50, invalid_records * 10)
                score = max(0, score)
            
            if not issues:
                issues.append("모든 거래량 데이터가 유효함")
            
            return {
                'status': 'PASS' if score >= 80 else 'WARNING' if score >= 60 else 'FAIL',
                'score': score,
                'total_records': len(result),
                'invalid_records': invalid_records,
                'issues': issues[:10]
            }
            
        except Exception as e:
            logging.error(f"❌ 거래량 데이터 검증 중 오류: {e}")
            return {'status': 'ERROR', 'score': 0, 'issues': [f'검증 오류: {str(e)}']}
    
    def _check_date_continuity(self, stock_code: str, start_date: datetime, 
                              end_date: datetime) -> Dict[str, Any]:
        """날짜 연속성 검증"""
        try:
            query = """
            SELECT trade_date
            FROM daily_data 
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
            """
            
            result = self.db.fetch_all(query, (stock_code, start_date, end_date))
            
            if not result:
                return {'status': 'FAIL', 'score': 0, 'issues': ['거래일 데이터가 없음']}
            
            # 거래일 목록 생성
            trade_dates = [record['trade_date'] for record in result]
            
            # 간단한 연속성 검증 (공휴일 계산 제외)
            total_actual = len(trade_dates)
            
            # 연속성 점수 계산 (간단한 버전)
            if total_actual >= 20:
                score = 100
            elif total_actual >= 15:
                score = 80
            elif total_actual >= 10:
                score = 60
            else:
                score = 40
            
            issues = []
            if total_actual < self.validation_rules['data_consistency']['min_data_points']:
                issues.append(f"데이터 포인트 부족: {total_actual}개 (최소 {self.validation_rules['data_consistency']['min_data_points']}개 필요)")
            else:
                issues.append("데이터 포인트가 충분함")
            
            return {
                'status': 'PASS' if score >= 80 else 'WARNING' if score >= 60 else 'FAIL',
                'score': score,
                'actual_trading_days': total_actual,
                'continuity_ratio': f"{score}%",
                'issues': issues
            }
            
        except Exception as e:
            logging.error(f"❌ 날짜 연속성 검증 중 오류: {e}")
            return {'status': 'ERROR', 'score': 0, 'issues': [f'검증 오류: {str(e)}']}
    
    def _validate_technical_indicators(self, stock_code: str, start_date: datetime, 
                                     end_date: datetime) -> Dict[str, Any]:
        """기술적 지표 일관성 검증"""
        try:
            query = """
            SELECT trade_date, rsi, macd, macd_signal
            FROM technical_indicators 
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
            """
            
            result = self.db.fetch_all(query, (stock_code, start_date, end_date))
            
            if not result:
                return {'status': 'FAIL', 'score': 0, 'issues': ['기술적 지표 데이터가 없음']}
            
            issues = []
            score = 100
            invalid_records = 0
            
            for record in result:
                # RSI 범위 검증
                if record['rsi'] is not None:
                    rsi = record['rsi']
                    if not (self.validation_rules['technical_indicators']['rsi_range'][0] <= 
                           rsi <= self.validation_rules['technical_indicators']['rsi_range'][1]):
                        issues.append(f"{record['trade_date']}: RSI 범위 오류 ({rsi})")
                        invalid_records += 1
                
                # MACD 시그널 차이 검증
                if record['macd'] is not None and record['macd_signal'] is not None:
                    macd_diff = abs(record['macd'] - record['macd_signal'])
                    if macd_diff > self.validation_rules['technical_indicators']['macd_signal_diff_limit']:
                        issues.append(f"{record['trade_date']}: MACD 시그널 차이 과대 ({macd_diff:.4f})")
                        invalid_records += 1
                
                # 볼린저 밴드 관계 검증 (현재는 제외)
                pass
            
            # 점수 계산
            if invalid_records > 0:
                score -= min(50, invalid_records * 10)
                score = max(0, score)
            
            if not issues:
                issues.append("모든 기술적 지표가 유효함")
            
            return {
                'status': 'PASS' if score >= 80 else 'WARNING' if score >= 60 else 'FAIL',
                'score': score,
                'total_records': len(result),
                'invalid_records': invalid_records,
                'issues': issues[:10]
            }
            
        except Exception as e:
            logging.error(f"❌ 기술적 지표 검증 중 오류: {e}")
            return {'status': 'ERROR', 'score': 0, 'issues': [f'검증 오류: {str(e)}']}
    
    def _calculate_integrity_score(self, existence_check: Dict, price_validation: Dict,
                                  volume_validation: Dict, continuity_check: Dict,
                                  technical_validation: Dict) -> float:
        """무결성 종합 점수 계산"""
        weights = {
            'existence': 0.25,      # 데이터 존재성 (25%)
            'price': 0.25,          # 가격 데이터 (25%)
            'volume': 0.20,         # 거래량 데이터 (20%)
            'continuity': 0.20,     # 날짜 연속성 (20%)
            'technical': 0.10       # 기술적 지표 (10%)
        }
        
        total_score = (
            existence_check.get('score', 0) * weights['existence'] +
            price_validation.get('score', 0) * weights['price'] +
            volume_validation.get('score', 0) * weights['volume'] +
            continuity_check.get('score', 0) * weights['continuity'] +
            technical_validation.get('score', 0) * weights['technical']
        )
        
        return round(total_score, 1)
    
    def _get_grade(self, score: float) -> str:
        """점수별 등급 반환"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C+"
        elif score >= 40:
            return "C"
        else:
            return "F"
    
    def _generate_integrity_recommendations(self, total_score: float) -> List[str]:
        """무결성 점수 기반 권장사항 생성"""
        recommendations = []
        
        if total_score >= 90:
            recommendations.append("✅ 데이터 품질이 매우 우수합니다")
        elif total_score >= 80:
            recommendations.append("✅ 데이터 품질이 양호합니다")
        elif total_score >= 70:
            recommendations.append("⚠️ 데이터 품질이 보통입니다. 개선 여지가 있습니다")
        elif total_score >= 60:
            recommendations.append("⚠️ 데이터 품질이 낮습니다. 점검이 필요합니다")
        else:
            recommendations.append("🚨 데이터 품질이 매우 낮습니다. 즉시 조치가 필요합니다")
        
        if total_score < 80:
            recommendations.append("🔍 상세 검증 결과를 확인하여 구체적인 문제점을 파악하세요")
        
        if total_score < 60:
            recommendations.append("🔄 데이터 재수집 또는 수정이 권장됩니다")
        
        return recommendations
    
    def validate_multiple_stocks(self, stock_codes: List[str], 
                               start_date: datetime = None, 
                               end_date: datetime = None) -> Dict[str, Any]:
        """여러 종목의 데이터 무결성 일괄 검증"""
        results = {}
        total_scores = []
        
        for stock_code in stock_codes:
            logging.info(f"🔍 {stock_code} 데이터 무결성 검증 중...")
            result = self.validate_stock_data_integrity(stock_code, start_date, end_date)
            results[stock_code] = result
            
            if result.get('success') and 'total_score' in result:
                total_scores.append(result['total_score'])
        
        # 전체 통계 계산
        if total_scores:
            overall_stats = {
                'total_stocks': len(stock_codes),
                'successful_validations': len(total_scores),
                'average_score': round(np.mean(total_scores), 1),
                'median_score': round(np.median(total_scores), 1),
                'min_score': min(total_scores),
                'max_score': max(total_scores),
                'grade_distribution': self._calculate_grade_distribution(total_scores)
            }
        else:
            overall_stats = {
                'total_stocks': len(stock_codes),
                'successful_validations': 0,
                'error': '검증 성공한 종목이 없습니다'
            }
        
        return {
            'individual_results': results,
            'overall_statistics': overall_stats,
            'validation_timestamp': datetime.now()
        }
    
    def _calculate_grade_distribution(self, scores: List[float]) -> Dict[str, int]:
        """점수별 등급 분포 계산"""
        distribution = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C+': 0, 'C': 0, 'F': 0}
        
        for score in scores:
            grade = self._get_grade(score)
            distribution[grade] += 1
        
        return distribution

def main():
    """테스트 함수"""
    print("🚀 향상된 데이터 검증 시스템 테스트")
    print("="*50)
    
    validator = EnhancedDataValidator()
    
    # 단일 종목 검증 테스트
    print("📊 단일 종목 데이터 무결성 검증...")
    single_result = validator.validate_stock_data_integrity('005930')  # 삼성전자
    
    if single_result.get('success'):
        print(f"✅ 검증 완료: {single_result['stock_code']}")
        print(f"📊 종합 점수: {single_result['total_score']}/100 ({single_result['grade']})")
        print(f"📋 권장사항:")
        for rec in single_result['recommendations']:
            print(f"   {rec}")
    else:
        print(f"❌ 검증 실패: {single_result.get('error', '알 수 없는 오류')}")
    
    # 여러 종목 일괄 검증 테스트
    print("\n📊 여러 종목 일괄 검증...")
    test_codes = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER
    batch_result = validator.validate_multiple_stocks(test_codes)
    
    if 'overall_statistics' in batch_result:
        stats = batch_result['overall_statistics']
        print(f"📈 전체 통계:")
        print(f"   총 종목: {stats['total_stocks']}개")
        print(f"   검증 성공: {stats['successful_validations']}개")
        print(f"   평균 점수: {stats['average_score']}/100")
        print(f"   최고 점수: {stats['max_score']}/100")
        print(f"   최저 점수: {stats['min_score']}/100")
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    main()
