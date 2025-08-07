#!/bin/bash

echo "========================================"
echo "   주식 시세 조회 및 AI 분석 프로그램 설치 스크립트"
echo "========================================"
echo

# Python 설치 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되지 않았습니다."
    echo "Python 3.7 이상을 설치해주세요."
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "macOS: brew install python3"
    exit 1
fi

echo "✅ Python3가 설치되어 있습니다."
python3 --version

# pip 설치 확인
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3가 설치되지 않았습니다."
    echo "pip3를 설치해주세요."
    exit 1
fi

echo "✅ pip3가 설치되어 있습니다."
echo

echo "필요한 라이브러리 설치 중..."
echo

echo "📦 requirements.txt에서 모든 라이브러리 설치 중..."
pip3 install -r requirements.txt

echo
echo "========================================"
echo "설치가 완료되었습니다!"
echo "========================================"
echo
echo "다음 단계:"
echo "1. Google AI API 키 발급: https://makersuite.google.com/app/apikey"
echo "2. API 키 설정: python3 setup_api_key.py"
echo
echo "사용 방법:"
echo "1. 기본 차트 생성: python3 day_stock_analysis.py"
echo "2. AI 차트 분석: python3 ai_chart_analysis.py"
echo "3. 통합 실행: python3 integrated_stock_analysis.py"
echo
echo "예시 종목코드:"
echo "- 삼성전자: 005930"
echo "- SK하이닉스: 000660"
echo "- 현대차: 005380"
echo

# 실행 권한 부여
chmod +x day_stock_analysis.py
chmod +x ai_chart_analysis.py
chmod +x integrated_stock_analysis.py
chmod +x setup_api_key.py

echo "실행 권한을 부여했습니다."
echo 