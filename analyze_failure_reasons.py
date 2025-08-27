#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유통주식수 수집 실패 사유 분석 모듈
향후 재활용을 위한 상세 분석 및 해결 방안 제시
"""

from database_config import DatabaseManager
import json
from datetime import datetime

class FailureAnalyzer:
    """실패 사유 분석 클래스"""
    
    def __init__(self):
        """초기화"""
        self.db = DatabaseManager()
        self.analysis_results = {}
        
    def analyze_failure_reasons(self, date='2025-08-22', limit=50):
        """유통주식수 수집 실패 사유 분석"""
        try:
            if not self.db.connect():
                print("❌ 데이터베이스 연결 실패")
                return None
            
            print(f"=== {date} 기준 유통주식수 수집 실패 사유 분석 ===")
            print("="*70)
            
            # 실패한 종목들 조회
            failed_query = """
            SELECT 
                d.stock_code,
                s.stock_name,
                s.market_type,
                d.volume,
                d.shares_at_date,
                d.market_cap_at_date,
                d.trade_date
            FROM daily_data d
            JOIN stocks s ON d.stock_code = s.stock_code
            WHERE d.trade_date = %s 
            AND d.shares_at_date = 0
            ORDER BY d.volume DESC
            LIMIT %s
            """
            
            failed_result = self.db.fetch_all(failed_query, (date, limit))
            
            print(f"📊 분석 대상: {date} 기준 유통주식수가 없는 종목들")
            print(f"🔍 상위 {len(failed_result)}개 종목 분석 결과:")
            print()
            
            # 실패 패턴 분석
            failure_patterns = self._analyze_failure_patterns(failed_result)
            
            # 상세 분석 결과 저장
            self.analysis_results = {
                'analysis_date': datetime.now().isoformat(),
                'target_date': date,
                'total_analyzed': len(failed_result),
                'failure_patterns': failure_patterns,
                'detailed_results': self._format_detailed_results(failed_result, failure_patterns)
            }
            
            # 결과 출력
            self._print_analysis_results(failure_patterns)
            self._print_solutions(failure_patterns)
            
            print("\n🎉 분석 완료!")
            return self.analysis_results
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def _analyze_failure_patterns(self, failed_result):
        """실패 패턴 분석"""
        patterns = {
            'KOSDAQ_404': {'count': 0, 'stocks': []},      # KOSDAQ 종목 HTTP 404 오류
            'KOSDAQ_ZERO': {'count': 0, 'stocks': []},     # KOSDAQ 종목 유통주식수 0
            'KOSPI_ZERO': {'count': 0, 'stocks': []},      # KOSPI 종목 유통주식수 0
            'SPECIAL_CODES': {'count': 0, 'stocks': []},   # 특수 종목코드
            'LOW_VOLUME': {'count': 0, 'stocks': []},      # 거래량이 매우 낮은 종목
            'UNKNOWN': {'count': 0, 'stocks': []}          # 기타 원인
        }
        
        for row in failed_result:
            stock_code = row['stock_code']
            stock_name = row['stock_name']
            market_type = row['market_type']
            volume = row['volume']
            
            # 실패 패턴 분석
            pattern = self._classify_failure_pattern(stock_code, stock_name, market_type, volume)
            
            # 패턴별 카운트 및 종목 정보 저장
            patterns[pattern]['count'] += 1
            patterns[pattern]['stocks'].append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'market_type': market_type,
                'volume': volume,
                'pattern': pattern
            })
        
        return patterns
    
    def _classify_failure_pattern(self, stock_code, stock_name, market_type, volume):
        """개별 종목의 실패 패턴 분류"""
        
        # 특수 종목코드 체크
        if any(c.isalpha() for c in stock_code) or len(stock_code) > 6:
            return 'SPECIAL_CODES'
        
        # 거래량이 매우 낮은 종목 (비활성 의심)
        if volume < 1000:
            return 'LOW_VOLUME'
        
        # KOSDAQ 종목 실패 패턴
        if market_type == 'KOSDAQ':
            # 9로 시작하는 6자리 종목코드 (Yahoo Finance에서 404 오류 발생 가능성 높음)
            if stock_code.startswith('9') and len(stock_code) == 6:
                return 'KOSDAQ_404'
            else:
                return 'KOSDAQ_ZERO'
        
        # KOSPI 종목 실패 패턴
        elif market_type == 'KOSPI':
            return 'KOSPI_ZERO'
        
        return 'UNKNOWN'
    
    def _format_detailed_results(self, failed_result, failure_patterns):
        """상세 분석 결과 포맷팅"""
        detailed = []
        
        for row in failed_result:
            stock_code = row['stock_code']
            stock_name = row['stock_name']
            market_type = row['market_type']
            volume = row['volume']
            shares = row['shares_at_date']
            market_cap = row['market_cap_at_date']
            
            pattern = self._classify_failure_pattern(stock_code, stock_name, market_type, volume)
            
            detailed.append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'market_type': market_type,
                'volume': volume,
                'shares_at_date': shares,
                'market_cap_at_date': market_cap,
                'failure_pattern': pattern,
                'pattern_description': self._get_pattern_description(pattern),
                'suggested_solution': self._get_suggested_solution(pattern)
            })
        
        return detailed
    
    def _print_analysis_results(self, failure_patterns):
        """분석 결과 출력"""
        total_failed = sum(pattern['count'] for pattern in failure_patterns.values())
        
        for pattern, data in failure_patterns.items():
            if data['count'] > 0:
                percentage = (data['count'] / total_failed) * 100
                print(f"🔍 {self._get_pattern_description(pattern)}: {data['count']}개 ({percentage:.1f}%)")
                
                # 상위 5개 종목 예시
                if data['stocks']:
                    print("   📋 예시 종목:")
                    for i, stock in enumerate(data['stocks'][:5], 1):
                        print(f"      {i}. {stock['stock_code']} ({stock['stock_name']}) - 거래량: {stock['volume']:,}주")
                    if len(data['stocks']) > 5:
                        print(f"      ... 외 {len(data['stocks']) - 5}개")
                    print()
    
    def _print_solutions(self, failure_patterns):
        """해결 방안 출력"""
        print("=== 해결 방안 ===")
        
        solutions = {
            'KOSDAQ_404': [
                "💡 Yahoo Finance 티커 매핑 개선",
                "   - KOSDAQ 종목의 경우 .KQ 접미사 우선 시도",
                "   - 대체 티커 형식 (.KR, 원본 코드) 순차 시도",
                "   - API 응답 확인 및 재시도 로직 강화"
            ],
            'KOSDAQ_ZERO': [
                "💡 상장폐지/비활성 종목 확인",
                "   - KRX 상장폐지 정보와 대조",
                "   - 거래량 기준 비활성 종목 필터링",
                "   - 주기적 상태 재확인"
            ],
            'KOSPI_ZERO': [
                "💡 데이터 수집 로직 개선",
                "   - Yahoo Finance API 응답 상태 확인",
                "   - 재시도 횟수 및 간격 조정",
                "   - 대체 데이터 소스 고려"
            ],
            'SPECIAL_CODES': [
                "💡 특수 종목코드 처리 로직",
                "   - 우선주, SPAC 등 특별 매핑 테이블 구축",
                "   - 종목코드별 맞춤형 처리 로직",
                "   - 수동 검증 및 업데이트"
            ],
            'LOW_VOLUME': [
                "💡 비활성 종목 필터링",
                "   - 거래량 기준 임계값 설정",
                "   - 주기적 활성 상태 확인",
                "   - 우선순위 조정"
            ]
        }
        
        for pattern, data in failure_patterns.items():
            if data['count'] > 0 and pattern in solutions:
                for solution in solutions[pattern]:
                    print(solution)
                print()
    
    def _get_pattern_description(self, pattern):
        """패턴에 대한 설명 반환"""
        descriptions = {
            'KOSDAQ_404': 'KOSDAQ 404 오류 (Yahoo Finance 티커 매핑 실패)',
            'KOSDAQ_ZERO': 'KOSDAQ 유통주식수 0 (상장폐지/비활성 의심)',
            'KOSPI_ZERO': 'KOSPI 유통주식수 0 (데이터 수집 실패)',
            'SPECIAL_CODES': '특수 종목코드 (우선주, SPAC 등)',
            'LOW_VOLUME': '거래량 낮음 (비활성 종목 의심)',
            'UNKNOWN': '기타 원인'
        }
        return descriptions.get(pattern, '알 수 없는 패턴')
    
    def _get_suggested_solution(self, pattern):
        """패턴별 제안 해결책 반환"""
        solutions = {
            'KOSDAQ_404': 'Yahoo Finance 티커 매핑 개선 및 재시도 로직 강화',
            'KOSDAQ_ZERO': '상장폐지/비활성 종목 확인 및 상태 재검증',
            'KOSPI_ZERO': '데이터 수집 로직 개선 및 대체 소스 고려',
            'SPECIAL_CODES': '특수 종목코드별 맞춤형 처리 로직 구축',
            'LOW_VOLUME': '거래량 기준 비활성 종목 필터링',
            'UNKNOWN': '추가 분석 및 수동 검증 필요'
        }
        return solutions.get(pattern, '분석 필요')
    
    def save_analysis_results(self, filename=None):
        """분석 결과를 JSON 파일로 저장"""
        if not self.analysis_results:
            print("❌ 저장할 분석 결과가 없습니다.")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"failure_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 분석 결과가 {filename}에 저장되었습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")
            return False
    
    def get_failure_summary(self):
        """실패 요약 정보 반환"""
        if not self.analysis_results:
            return None
        
        total = self.analysis_results['total_analyzed']
        patterns = self.analysis_results['failure_patterns']
        
        summary = {
            'total_failed': total,
            'pattern_counts': {k: v['count'] for k, v in patterns.items()},
            'top_issues': []
        }
        
        # 상위 이슈 식별
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1]['count'], reverse=True)
        for pattern, data in sorted_patterns[:3]:
            if data['count'] > 0:
                summary['top_issues'].append({
                    'pattern': pattern,
                    'count': data['count'],
                    'percentage': (data['count'] / total) * 100,
                    'description': self._get_pattern_description(pattern)
                })
        
        return summary

def main():
    """메인 함수 - 향후 활용을 위한 예시"""
    analyzer = FailureAnalyzer()
    
    # 기본 분석 실행
    results = analyzer.analyze_failure_reasons()
    
    if results:
        # 분석 결과 저장
        analyzer.save_analysis_results()
        
        # 요약 정보 출력
        summary = analyzer.get_failure_summary()
        if summary:
            print(f"\n📊 실패 요약:")
            print(f"   총 실패 종목: {summary['total_failed']}개")
            print(f"   주요 이슈:")
            for issue in summary['top_issues']:
                print(f"     - {issue['description']}: {issue['count']}개 ({issue['percentage']:.1f}%)")

if __name__ == "__main__":
    main()
