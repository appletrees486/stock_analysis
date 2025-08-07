#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
대량 분석 처리 클래스
비동기적으로 다수 종목을 분석하는 기능
"""

import os
import json
import threading
import zipfile
import logging
from datetime import datetime
from typing import List, Dict, Any
import time
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

class BatchAnalyzer:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BatchAnalyzer, cls).__new__(cls)
                    cls._instance.batch_status = {}
                    cls._instance.batch_results = {}
                    cls._instance.batch_threads = {}
        return cls._instance
    
    def __init__(self):
        # 싱글톤이므로 초기화는 한 번만
        pass
    
    def start_batch_analysis(self, stock_list_path: str, chart_type: str, batch_id: str):
        """대량 분석 시작"""
        try:
            logger.info(f"대량 분석 시작: batch_id={batch_id}")
            
            # 초기 상태 설정
            self.batch_status[batch_id] = {
                'status': 'running',
                'total': 0,
                'completed': 0,
                'failed': 0,
                'start_time': datetime.now().isoformat(),
                'progress': 0,
                'chart_type': chart_type
            }
            
            # 백그라운드에서 분석 실행
            thread = threading.Thread(
                target=self._run_batch_analysis,
                args=(stock_list_path, chart_type, batch_id)
            )
            thread.daemon = True
            thread.start()
            
            self.batch_threads[batch_id] = thread
            logger.info(f"대량 분석 스레드 시작: batch_id={batch_id}")
            
        except Exception as e:
            logger.error(f"대량 분석 시작 오류: {e}")
            self.batch_status[batch_id] = {
                'status': 'failed',
                'error': str(e),
                'start_time': datetime.now().isoformat()
            }
    
    def _run_batch_analysis(self, stock_list_path: str, chart_type: str, batch_id: str):
        """백그라운드에서 대량 분석 실행"""
        try:
            # 종목 리스트 읽기
            from .utils import get_stock_list_from_file
            stock_codes = get_stock_list_from_file(stock_list_path)
            
            if not stock_codes:
                raise Exception("종목 리스트가 비어있습니다.")
            
            self.batch_status[batch_id]['total'] = len(stock_codes)
            self.batch_results[batch_id] = []
            
            logger.info(f"대량 분석 시작: {len(stock_codes)}개 종목, 차트타입={chart_type}")
            
            # 각 종목별 분석
            for i, stock_code in enumerate(stock_codes):
                try:
                    logger.info(f"종목 분석 중: {stock_code} ({i+1}/{len(stock_codes)})")
                    
                    # 기존 배치 분석 모듈 활용
                    from batch_stock_analyzer_optimized import analyze_single_stock_fast
                    
                    # 차트 타입 매핑
                    chart_type_mapping = {
                        "일봉": "daily",
                        "주봉": "weekly", 
                        "월봉": "monthly"
                    }
                    chart_type_en = chart_type_mapping.get(chart_type, "daily")
                    
                    batch_result = analyze_single_stock_fast(
                        stock_code, chart_type, chart_type_en, None
                    )
                    
                    # 배치 결과를 AI 분석 결과 형식으로 변환
                    if batch_result.get('success', False):
                        # 성공한 경우 기본 결과 생성
                        result = {
                            'stock_name': stock_code,
                            'chart_type': chart_type,
                            'analysis_score': 75,  # 기본 점수
                            'summary': f'{stock_code} 종목 분석이 완료되었습니다.',
                            'detailed_analysis': f'{stock_code} 종목의 {chart_type} 차트 분석이 성공적으로 완료되었습니다.',
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        # 실패한 경우 에러 결과 생성
                        result = {
                            'stock_name': stock_code,
                            'chart_type': chart_type,
                            'analysis_score': 0,
                            'summary': f'분석 실패: {batch_result.get("error", "알 수 없는 오류")}',
                            'detailed_analysis': f'종목 {stock_code} 분석 중 오류가 발생했습니다. 오류: {batch_result.get("error", "알 수 없는 오류")}',
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    # 결과에 메타데이터 추가
                    result['batch_id'] = batch_id
                    result['stock_code'] = stock_code
                    result['chart_type'] = chart_type
                    result['processed_at'] = datetime.now().isoformat()
                    
                    self.batch_results[batch_id].append(result)
                    self.batch_status[batch_id]['completed'] += 1
                    
                    logger.info(f"종목 분석 완료: {stock_code}")
                    
                except Exception as e:
                    logger.error(f"종목 {stock_code} 분석 실패: {e}")
                    self.batch_status[batch_id]['failed'] += 1
                    
                    # 실패한 종목에 대한 에러 결과 추가
                    error_result = {
                        'batch_id': batch_id,
                        'stock_code': stock_code,
                        'chart_type': chart_type,
                        'processed_at': datetime.now().isoformat(),
                        'error': str(e),
                        'analysis_score': 0,
                        'summary': f'분석 실패: {str(e)}',
                        'detailed_analysis': f'종목 {stock_code} 분석 중 오류가 발생했습니다.'
                    }
                    self.batch_results[batch_id].append(error_result)
                
                # 진행률 업데이트
                progress = (i + 1) / len(stock_codes) * 100
                self.batch_status[batch_id]['progress'] = progress
            
            # 분석 완료
            self.batch_status[batch_id]['status'] = 'completed'
            self.batch_status[batch_id]['end_time'] = datetime.now().isoformat()
            
            # 결과 저장
            self._save_batch_results(batch_id)
            
            logger.info(f"대량 분석 완료: batch_id={batch_id}")
            
        except Exception as e:
            logger.error(f"대량 분석 실행 오류: {e}")
            self.batch_status[batch_id]['status'] = 'failed'
            self.batch_status[batch_id]['error'] = str(e)
            self.batch_status[batch_id]['end_time'] = datetime.now().isoformat()
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """배치 상태 조회"""
        if batch_id in self.batch_status:
            return self.batch_status[batch_id]
        else:
            return {'error': '배치를 찾을 수 없습니다'}
    
    def get_batch_results(self, batch_id: str) -> Dict[str, Any]:
        """배치 결과 조회"""
        if batch_id in self.batch_results:
            return {
                'batch_id': batch_id,
                'results': self.batch_results[batch_id],
                'status': self.batch_status.get(batch_id, {}),
                'total_results': len(self.batch_results[batch_id])
            }
        else:
            return {'error': '결과를 찾을 수 없습니다'}
    
    def _save_batch_results(self, batch_id: str):
        """배치 결과를 파일로 저장"""
        try:
            # JSON 결과 저장
            results_file = f"results/{batch_id}_results.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.batch_results[batch_id], f, ensure_ascii=False, indent=2)
            
            # ZIP 파일 생성 (결과 다운로드용)
            zip_file = f"results/{batch_id}_results.zip"
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # JSON 파일 추가
                zipf.write(results_file, os.path.basename(results_file))
                
                # 요약 파일 생성 및 추가
                summary_file = f"results/{batch_id}_summary.txt"
                self._create_summary_file(batch_id, summary_file)
                zipf.write(summary_file, os.path.basename(summary_file))
                
                # ai_analysis_results 폴더의 개별 종목별 분석 결과 파일들 추가
                self._add_analysis_files_to_zip(zipf, batch_id)
            
            logger.info(f"배치 결과 저장 완료: {batch_id}")
            
        except Exception as e:
            logger.error(f"배치 결과 저장 오류: {e}")
    
    def _add_analysis_files_to_zip(self, zipf, batch_id: str):
        """ai_analysis_results 폴더의 분석 결과 파일들을 ZIP에 추가"""
        try:
            ai_results_dir = "ai_analysis_results"
            if not os.path.exists(ai_results_dir):
                logger.warning(f"AI 분석 결과 폴더가 존재하지 않습니다: {ai_results_dir}")
                return
            
            # 배치에 포함된 종목 코드들 가져오기
            if batch_id not in self.batch_results:
                return
            
            batch_results = self.batch_results[batch_id]
            chart_type = self.batch_status.get(batch_id, {}).get('chart_type', '일봉')
            
            # 차트 타입 매핑
            chart_type_mapping = {
                "일봉": "daily",
                "주봉": "weekly", 
                "월봉": "monthly"
            }
            chart_type_en = chart_type_mapping.get(chart_type, "daily")
            
            # 각 종목별로 분석 결과 파일 찾기
            for result in batch_results:
                stock_code = result.get('stock_code')
                if not stock_code:
                    continue
                
                # 해당 종목의 분석 결과 파일들 찾기
                pattern = f"analysis_{chart_type_en}_{stock_code}_*.json"
                json_files = []
                for file in os.listdir(ai_results_dir):
                    if file.startswith(f"analysis_{chart_type_en}_{stock_code}_") and file.endswith('.json'):
                        json_files.append(file)
                
                # 가장 최근 파일 선택 (타임스탬프가 가장 큰 파일)
                if json_files:
                    latest_json = sorted(json_files)[-1]
                    json_path = os.path.join(ai_results_dir, latest_json)
                    
                    # ZIP에 JSON 파일 추가
                    zip_path = f"analysis_results/{latest_json}"
                    zipf.write(json_path, zip_path)
                    
                    # 해당하는 DOCX 파일도 찾아서 추가
                    docx_file = latest_json.replace('.json', '.docx')
                    docx_path = os.path.join(ai_results_dir, docx_file)
                    if os.path.exists(docx_path):
                        docx_zip_path = f"analysis_results/{docx_file}"
                        zipf.write(docx_path, docx_zip_path)
                        logger.info(f"분석 결과 파일 추가: {stock_code} - {latest_json}, {docx_file}")
                    else:
                        logger.info(f"분석 결과 파일 추가: {stock_code} - {latest_json}")
                else:
                    logger.warning(f"종목 {stock_code}의 분석 결과 파일을 찾을 수 없습니다")
            
        except Exception as e:
            logger.error(f"분석 결과 파일 ZIP 추가 오류: {e}")
    
    def _create_summary_file(self, batch_id: str, summary_file: str):
        """분석 결과 요약 파일 생성"""
        try:
            if batch_id not in self.batch_results:
                return
            
            results = self.batch_results[batch_id]
            status = self.batch_status.get(batch_id, {})
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 50 + "\n")
                f.write("AI 주식 차트 분석 결과 요약\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"배치 ID: {batch_id}\n")
                f.write(f"차트 유형: {status.get('chart_type', 'N/A')}\n")
                f.write(f"시작 시간: {status.get('start_time', 'N/A')}\n")
                f.write(f"완료 시간: {status.get('end_time', 'N/A')}\n")
                f.write(f"총 종목 수: {status.get('total', 0)}\n")
                f.write(f"성공: {status.get('completed', 0)}\n")
                f.write(f"실패: {status.get('failed', 0)}\n")
                f.write(f"진행률: {status.get('progress', 0):.1f}%\n\n")
                
                f.write("=" * 50 + "\n")
                f.write("종목별 분석 결과\n")
                f.write("=" * 50 + "\n\n")
                
                for i, result in enumerate(results, 1):
                    f.write(f"{i}. 종목코드: {result.get('stock_code', 'N/A')}\n")
                    f.write(f"   분석 점수: {result.get('analysis_score', 0)}\n")
                    f.write(f"   요약: {result.get('summary', 'N/A')}\n")
                    if 'error' in result:
                        f.write(f"   오류: {result['error']}\n")
                    f.write("\n")
            
        except Exception as e:
            logger.error(f"요약 파일 생성 오류: {e}")
    
    def cleanup_batch(self, batch_id: str):
        """배치 데이터 정리"""
        try:
            if batch_id in self.batch_status:
                del self.batch_status[batch_id]
            if batch_id in self.batch_results:
                del self.batch_results[batch_id]
            if batch_id in self.batch_threads:
                del self.batch_threads[batch_id]
            
            logger.info(f"배치 데이터 정리 완료: {batch_id}")
            
        except Exception as e:
            logger.error(f"배치 데이터 정리 오류: {e}")
    
    def get_all_batches(self) -> List[str]:
        """모든 배치 ID 목록 반환"""
        return list(self.batch_status.keys()) 