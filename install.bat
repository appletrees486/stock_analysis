@echo off
chcp 65001 >nul
echo ========================================
echo    주식 시세 조회 및 AI 분석 프로그램 설치 스크립트
echo ========================================
echo.

echo Python 설치 확인 중...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았습니다.
    echo Python 3.7 이상을 설치해주세요: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python이 설치되어 있습니다.
python --version

echo.
echo 필요한 라이브러리 설치 중...
echo.

echo 📦 requirements.txt에서 모든 라이브러리 설치 중...
pip install -r requirements.txt

echo.
echo ========================================
echo 설치가 완료되었습니다!
echo ========================================
echo.
echo 다음 단계:
echo 1. Google AI API 키 발급: https://makersuite.google.com/app/apikey
echo 2. API 키 설정: python setup_api_key.py
echo.
echo 사용 방법:
echo 1. 기본 차트 생성: python day_stock_analysis.py
echo 2. AI 차트 분석: python ai_chart_analysis.py
echo 3. 통합 실행: python integrated_stock_analysis.py
echo.
echo 예시 종목코드:
echo - 삼성전자: 005930
echo - SK하이닉스: 000660
echo - 현대차: 005380
echo.
pause 