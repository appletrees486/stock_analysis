#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로컬서버 캐시 리셋 및 재시작 도구
"""

import os
import sys
import shutil
import subprocess
import time
import glob
from pathlib import Path

# requests 라이브러리 확인 및 설치
try:
    import requests
except ImportError:
    print("❌ requests 라이브러리가 설치되지 않았습니다.")
    print("💡 다음 명령어로 설치해주세요: pip install requests")
    sys.exit(1)

class CacheReset:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.server_url = "http://localhost:5000"
        self.cache_dirs = [
            '__pycache__',
            'api/__pycache__',
            'static/css/__pycache__',
            'static/js/__pycache__'
        ]
        self.log_files = [
            '*.log',
            'stock_collector.log',
            'database.log',
            'market_status.log',
            'csv_insert.log',
            'stocks_dump.log',
            'data_change_tracker.log',
            'database_cleanup.log',
            'database_full_cleanup.log',
            'enhanced_data_validator.log',
            'null_data_updater.log'
        ]
        self.temp_files = [
            '*.tmp',
            '*.temp',
            '*.cache'
        ]

    def clear_pycache(self):
        """Python 캐시 파일들 삭제"""
        print("🗑️  Python 캐시 파일 삭제 중...")
        removed_count = 0
        
        for cache_dir in self.cache_dirs:
            cache_path = self.project_root / cache_dir
            if cache_path.exists():
                try:
                    shutil.rmtree(cache_path)
                    print(f"   ✅ {cache_dir} 삭제됨")
                    removed_count += 1
                except Exception as e:
                    print(f"   ❌ {cache_dir} 삭제 실패: {e}")
        
        # 모든 __pycache__ 디렉토리 재귀적으로 삭제
        for pycache in self.project_root.rglob('__pycache__'):
            try:
                shutil.rmtree(pycache)
                print(f"   ✅ {pycache.relative_to(self.project_root)} 삭제됨")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ {pycache} 삭제 실패: {e}")
        
        print(f"   📊 총 {removed_count}개의 캐시 디렉토리 삭제됨")

    def clear_log_files(self):
        """로그 파일들 삭제"""
        print("📝 로그 파일 삭제 중...")
        removed_count = 0
        
        for log_pattern in self.log_files:
            log_files = list(self.project_root.glob(log_pattern))
            for log_file in log_files:
                try:
                    log_file.unlink()
                    print(f"   ✅ {log_file.name} 삭제됨")
                    removed_count += 1
                except Exception as e:
                    print(f"   ❌ {log_file.name} 삭제 실패: {e}")
        
        print(f"   📊 총 {removed_count}개의 로그 파일 삭제됨")

    def clear_temp_files(self):
        """임시 파일들 삭제"""
        print("🗂️  임시 파일 삭제 중...")
        removed_count = 0
        
        for temp_pattern in self.temp_files:
            temp_files = list(self.project_root.glob(temp_pattern))
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                    print(f"   ✅ {temp_file.name} 삭제됨")
                    removed_count += 1
                except Exception as e:
                    print(f"   ❌ {temp_file.name} 삭제 실패: {e}")
        
        print(f"   📊 총 {removed_count}개의 임시 파일 삭제됨")

    def clear_upload_cache(self):
        """업로드 캐시 삭제"""
        print("📤 업로드 캐시 삭제 중...")
        upload_dirs = ['uploads/charts', 'uploads/stock_lists']
        removed_count = 0
        
        for upload_dir in upload_dirs:
            upload_path = self.project_root / upload_dir
            if upload_path.exists():
                try:
                    # 디렉토리 내용만 삭제하고 디렉토리는 유지
                    for item in upload_path.iterdir():
                        if item.is_file():
                            item.unlink()
                            print(f"   ✅ {item.name} 삭제됨")
                            removed_count += 1
                        elif item.is_dir():
                            shutil.rmtree(item)
                            print(f"   ✅ {item.name}/ 디렉토리 삭제됨")
                            removed_count += 1
                except Exception as e:
                    print(f"   ❌ {upload_dir} 정리 실패: {e}")
        
        print(f"   📊 총 {removed_count}개의 업로드 파일 삭제됨")

    def clear_chart_cache(self):
        """차트 캐시 삭제"""
        print("📊 차트 캐시 삭제 중...")
        chart_dirs = ['daily_charts', 'weekly_charts', 'monthly_charts']
        removed_count = 0
        
        for chart_dir in chart_dirs:
            chart_path = self.project_root / chart_dir
            if chart_path.exists():
                try:
                    # PNG 파일들만 삭제
                    for png_file in chart_path.glob('*.png'):
                        png_file.unlink()
                        print(f"   ✅ {png_file.name} 삭제됨")
                        removed_count += 1
                except Exception as e:
                    print(f"   ❌ {chart_dir} 정리 실패: {e}")
        
        print(f"   📊 총 {removed_count}개의 차트 파일 삭제됨")

    def clear_web_cache(self):
        """웹 API 캐시 초기화"""
        print("🌐 웹 API 캐시 초기화 중...")
        
        try:
            # 거래량 랭킹 캐시 초기화
            response = requests.post(f"{self.server_url}/api/volume-ranking/cache/clear", timeout=10)
            if response.status_code == 200:
                print("   ✅ 거래량 랭킹 캐시 초기화됨")
            else:
                print(f"   ⚠️  거래량 랭킹 캐시 초기화 실패: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️  서버가 실행 중이지 않습니다. 서버를 먼저 시작해주세요.")
        except requests.exceptions.Timeout:
            print("   ⚠️  서버 응답 시간 초과")
        except Exception as e:
            print(f"   ❌ 웹 캐시 초기화 오류: {e}")

    def clear_browser_cache(self):
        """브라우저 캐시 초기화 안내"""
        print("🌐 브라우저 캐시 초기화 안내:")
        print("   💡 브라우저에서 다음을 수행하세요:")
        print("      - Ctrl + Shift + R (강력 새로고침)")
        print("      - 또는 F12 → Network 탭 → 'Disable cache' 체크")
        print("      - 또는 Ctrl + Shift + Delete → 캐시 삭제")

    def check_server_status(self):
        """서버 상태 확인"""
        print("🔍 서버 상태 확인 중...")
        
        try:
            response = requests.get(f"{self.server_url}/", timeout=5)
            if response.status_code == 200:
                print("   ✅ 서버가 정상적으로 실행 중입니다")
                return True
            else:
                print(f"   ⚠️  서버 응답 오류: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("   ❌ 서버에 연결할 수 없습니다")
            return False
        except requests.exceptions.Timeout:
            print("   ⚠️  서버 응답 시간 초과")
            return False
        except Exception as e:
            print(f"   ❌ 서버 상태 확인 오류: {e}")
            return False

    def restart_server(self):
        """서버 재시작"""
        print("🔄 서버 재시작 중...")
        
        # 현재 실행 중인 Flask 서버 프로세스 찾기 및 종료
        try:
            if sys.platform == "win32":
                # Windows에서 Python 프로세스 종료
                subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                             capture_output=True, text=True)
                subprocess.run(['taskkill', '/f', '/im', 'pythonw.exe'], 
                             capture_output=True, text=True)
            else:
                # Linux/Mac에서 Python 프로세스 종료
                subprocess.run(['pkill', '-f', 'python.*app.py'], 
                             capture_output=True, text=True)
            
            print("   ✅ 기존 서버 프로세스 종료됨")
            time.sleep(2)
            
        except Exception as e:
            print(f"   ⚠️  기존 프로세스 종료 중 오류: {e}")
        
        # 새 서버 시작
        try:
            print("   🚀 새 서버 시작 중...")
            if sys.platform == "win32":
                # Windows에서 백그라운드 실행
                subprocess.Popen([sys.executable, 'app.py'], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # Linux/Mac에서 백그라운드 실행
                subprocess.Popen([sys.executable, 'app.py'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            
            print("   ✅ 서버가 백그라운드에서 시작됨")
            print("   🌐 브라우저에서 http://localhost:5000 접속 가능")
            
        except Exception as e:
            print(f"   ❌ 서버 시작 실패: {e}")
            print("   💡 수동으로 'python app.py' 실행해주세요")

    def show_status(self):
        """현재 상태 표시"""
        print("📋 현재 프로젝트 상태:")
        print(f"   📁 프로젝트 경로: {self.project_root}")
        
        # 캐시 디렉토리 개수
        cache_count = len(list(self.project_root.rglob('__pycache__')))
        print(f"   🗂️  캐시 디렉토리: {cache_count}개")
        
        # 로그 파일 개수
        log_count = 0
        for log_pattern in self.log_files:
            log_count += len(list(self.project_root.glob(log_pattern)))
        print(f"   📝 로그 파일: {log_count}개")
        
        # 차트 파일 개수
        chart_count = 0
        for chart_dir in ['daily_charts', 'weekly_charts', 'monthly_charts']:
            chart_path = self.project_root / chart_dir
            if chart_path.exists():
                chart_count += len(list(chart_path.glob('*.png')))
        print(f"   📊 차트 파일: {chart_count}개")
        
        # 서버 상태 확인
        print(f"\n🌐 웹 서버 상태:")
        server_running = self.check_server_status()
        if server_running:
            print(f"   ✅ 서버 URL: {self.server_url}")
        else:
            print(f"   ❌ 서버가 실행 중이지 않습니다")

    def run_full_reset(self):
        """전체 캐시 리셋 실행 (서버 + 웹)"""
        print("🧹 전체 캐시 리셋 시작 (서버 + 웹)")
        print("=" * 50)
        
        self.show_status()
        print("\n" + "=" * 50)
        
        # 1. 서버 캐시 정리
        print("📁 1단계: 서버 캐시 정리")
        self.clear_pycache()
        print()
        self.clear_log_files()
        print()
        self.clear_temp_files()
        print()
        self.clear_upload_cache()
        print()
        self.clear_chart_cache()
        
        print("\n" + "=" * 30)
        print("📁 서버 캐시 정리 완료!")
        print("=" * 30)
        
        # 2. 서버 재시작
        print("\n🔄 2단계: 서버 재시작")
        self.restart_server()
        
        # 서버 시작 대기
        print("\n⏳ 서버 시작 대기 중... (5초)")
        time.sleep(5)
        
        # 3. 웹 캐시 초기화
        print("\n🌐 3단계: 웹 캐시 초기화")
        self.clear_web_cache()
        print()
        self.clear_browser_cache()
        
        print("\n" + "=" * 50)
        print("✅ 전체 캐시 리셋 완료!")
        print("🌐 브라우저에서 http://localhost:5000 접속하여 확인하세요")
        print("=" * 50)

    def run_web_cache_reset(self):
        """웹 캐시만 초기화"""
        print("🌐 웹 캐시 초기화 시작")
        print("=" * 30)
        
        # 서버 상태 확인
        if not self.check_server_status():
            print("\n❌ 서버가 실행 중이지 않습니다.")
            start_server = input("서버를 시작하시겠습니까? (y/N): ").strip().lower()
            if start_server in ['y', 'yes', '예']:
                self.restart_server()
                time.sleep(5)
            else:
                print("💡 먼저 'python app.py'로 서버를 시작해주세요")
                return
        
        # 웹 캐시 초기화
        self.clear_web_cache()
        print()
        self.clear_browser_cache()
        
        print("\n" + "=" * 30)
        print("✅ 웹 캐시 초기화 완료!")
        print("=" * 30)

def main():
    """메인 함수"""
    reset_tool = CacheReset()
    
    print("🛠️  로컬서버 캐시 리셋 도구")
    print("=" * 50)
    print("1. 전체 캐시 리셋 (서버 + 웹) - 권장")
    print("2. 서버 캐시만 정리 (서버 재시작 안함)")
    print("3. 웹 캐시만 초기화")
    print("4. 서버만 재시작")
    print("5. 서버 상태 확인")
    print("6. 현재 상태 확인")
    print("7. 종료")
    
    while True:
        try:
            choice = input("\n선택하세요 (1-7): ").strip()
            
            if choice == '1':
                reset_tool.run_full_reset()
                break
            elif choice == '2':
                print("🧹 서버 캐시 정리만 실행")
                reset_tool.clear_pycache()
                reset_tool.clear_log_files()
                reset_tool.clear_temp_files()
                reset_tool.clear_upload_cache()
                reset_tool.clear_chart_cache()
                print("\n✅ 서버 캐시 정리 완료!")
                break
            elif choice == '3':
                reset_tool.run_web_cache_reset()
                break
            elif choice == '4':
                reset_tool.restart_server()
                break
            elif choice == '5':
                reset_tool.check_server_status()
            elif choice == '6':
                reset_tool.show_status()
            elif choice == '7':
                print("👋 종료합니다.")
                break
            else:
                print("❌ 잘못된 선택입니다. 1-7 중에서 선택해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n👋 사용자가 중단했습니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
