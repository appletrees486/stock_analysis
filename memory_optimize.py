#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1GB 메모리 환경을 위한 Flask 애플리케이션 메모리 최적화 설정
"""

import gc
import os
import sys

def optimize_memory_usage():
    """메모리 사용량 최적화 설정"""
    
    # 1. 가비지 컬렉션 최적화
    gc.set_threshold(700, 10, 10)  # 더 자주 가비지 컬렉션 실행
    gc.enable()
    
    # 2. Python 최적화 설정
    os.environ['PYTHONHASHSEED'] = '0'  # 해시 시드 고정
    os.environ['PYTHONUNBUFFERED'] = '1'  # 버퍼링 비활성화
    os.environ['PYTHONOPTIMIZE'] = '1'  # 최적화 모드
    
    # 3. 메모리 사용량 모니터링 함수
    import psutil
    
    def get_memory_usage():
        """현재 프로세스의 메모리 사용량 반환 (MB)"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def memory_warning_check():
        """메모리 사용량이 300MB를 초과하면 경고"""
        usage = get_memory_usage()
        if usage > 300:
            print(f"⚠️ 메모리 사용량 경고: {usage:.1f}MB")
            gc.collect()  # 강제 가비지 컬렉션
            return True
        return False
    
    return get_memory_usage, memory_warning_check

def setup_flask_memory_optimization(app):
    """Flask 앱에 메모리 최적화 설정 적용"""
    
    # 1. Flask 설정 최적화
    app.config.update(
        # 세션 설정 최적화
        PERMANENT_SESSION_LIFETIME=1800,  # 30분
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        
        # 캐시 비활성화 (메모리 절약)
        SEND_FILE_MAX_AGE_DEFAULT=0,
        
        # JSON 설정 최적화
        JSON_SORT_KEYS=False,
        JSONIFY_PRETTYPRINT_REGULAR=False,
    )
    
    # 2. 요청 후 메모리 정리
    @app.after_request
    def cleanup_memory(response):
        """요청 처리 후 메모리 정리"""
        gc.collect()
        return response
    
    # 3. 메모리 모니터링 엔드포인트
    @app.route('/memory-status')
    def memory_status():
        """메모리 사용량 확인 엔드포인트"""
        import psutil
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        return {
            'memory_usage_mb': round(memory_mb, 1),
            'memory_percent': round(process.memory_percent(), 1),
            'status': 'warning' if memory_mb > 300 else 'ok'
        }
    
    return app

# 시스템 시작 시 메모리 최적화 적용
if __name__ == "__main__":
    get_memory_usage, memory_warning_check = optimize_memory_usage()
    print(f"🛡️ 메모리 최적화 모드 활성화")
    print(f"💾 현재 메모리 사용량: {get_memory_usage():.1f}MB")
