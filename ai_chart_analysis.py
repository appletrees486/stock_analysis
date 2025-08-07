#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 제미나이를 활용한 주식 차트 분석 스크립트 (일봉/주봉/월봉 지원)
"""

import os
import json
import base64
import time
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import requests
from typing import Dict, Any, Optional
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.shared import OxmlElement, qn
import pandas as pd

class StockNameMapper:
    """종목번호와 종목명 매핑 클래스"""
    
    def __init__(self, stock_list_file: str = "sotck_list.txt"):
        """
        종목명 매퍼 초기화
        
        Args:
            stock_list_file (str): 종목 리스트 파일 경로
        """
        self.stock_list_file = stock_list_file
        self.stock_mapping = {}
        self.load_stock_mapping()
    
    def load_stock_mapping(self):
        """종목 리스트 파일에서 종목번호와 종목명 매핑 로드"""
        try:
            if os.path.exists(self.stock_list_file):
                with open(self.stock_list_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and '\t' in line:
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                stock_code = parts[0].strip()
                                stock_name = parts[1].strip()
                                self.stock_mapping[stock_code] = stock_name
                
                print(f"✅ 종목 매핑 로드 완료: {len(self.stock_mapping)}개 종목")
            else:
                print(f"⚠️ 종목 리스트 파일을 찾을 수 없습니다: {self.stock_list_file}")
        except Exception as e:
            print(f"❌ 종목 매핑 로드 중 오류: {e}")
    
    def get_stock_name(self, stock_code: str) -> str:
        """
        종목번호로 종목명 조회
        
        Args:
            stock_code (str): 종목번호
            
        Returns:
            str: 종목명 (찾지 못한 경우 종목번호 반환)
        """
        # 종목번호 정리 (앞의 0 제거)
        clean_code = stock_code.lstrip('0')
        if not clean_code:
            clean_code = '0'
        
        # 6자리로 패딩
        padded_code = clean_code.zfill(6)
        
        # 매핑에서 찾기
        if padded_code in self.stock_mapping:
            return self.stock_mapping[padded_code]
        
        # 원본 코드로도 시도
        if stock_code in self.stock_mapping:
            return self.stock_mapping[stock_code]
        
        # 찾지 못한 경우 종목번호 반환
        return stock_code
    
    def extract_stock_info_from_filename(self, filename: str) -> tuple:
        """
        파일명에서 종목정보 추출
        
        Args:
            filename (str): 파일명
            
        Returns:
            tuple: (종목명, 종목번호)
        """
        try:
            # 파일명에서 확장자 제거
            name_without_ext = os.path.splitext(filename)[0]
            
            # 언더스코어로 분리
            parts = name_without_ext.split('_')
            
            stock_name = ""
            stock_code = ""
            
            # 파일명 패턴 분석
            if len(parts) >= 3:
                # weekly_Samsung_Electronics_Co.,_Ltd._005930_20250804 형태
                # 또는 daily_380550_380550_20250804 형태
                
                # 마지막에서 두 번째 부분이 종목번호일 가능성이 높음
                for i, part in enumerate(parts):
                    # 6자리 숫자인 경우 종목번호로 간주
                    if len(part) == 6 and part.isdigit():
                        stock_code = part
                        # 종목번호 앞의 부분들을 종목명으로 조합
                        stock_name_parts = parts[1:i] if i > 1 else parts[1:]
                        stock_name = "_".join(stock_name_parts)
                        break
                
                # 종목번호를 찾지 못한 경우, 파일명에서 직접 추출 시도
                if not stock_code:
                    for part in parts:
                        if len(part) == 6 and part.isdigit():
                            stock_code = part
                            break
            
            # 종목명이 비어있거나 종목번호가 없는 경우
            if not stock_name or not stock_code:
                # 파일명에서 6자리 숫자 찾기
                import re
                code_match = re.search(r'(\d{6})', filename)
                if code_match:
                    stock_code = code_match.group(1)
                    # 종목번호로 종목명 조회
                    stock_name = self.get_stock_name(stock_code)
                else:
                    # 파일명 그대로 사용
                    stock_name = name_without_ext
                    stock_code = "000000"
            
            return stock_name, stock_code
            
        except Exception as e:
            print(f"❌ 파일명에서 종목정보 추출 중 오류: {e}")
            return filename, "000000"

class ChartAnalysisPrompts:
    """차트 분석 프롬프트 관리 클래스"""
    
    @staticmethod
    def get_daily_prompt() -> str:
        """일봉 차트 분석 프롬프트"""
        return """
역할: 당신은 전문 주식 트레이더이자 차트 분석 전문가입니다. 아래에 제시된 [종목명]의 일봉 차트 이미지를 종합적으로 분석하여, 핵심적인 분석 결과와 단기 투자 아이디어를 A4 용지 1장 분량으로 간결하게 작성해 주세요.

분석 순서 및 출력 형식:

종합 분석 점수:

일봉 차트의 주요 분석 요소(추세, 모멘텀, 수급 등)를 종합하여 현재의 단기 투자 매력도를 100점 만점으로 환산하고, 그 점수와 함께 한 줄 요약을 가장 먼저 제시해 주세요.

오늘의 일봉(Daily Candle) 요약:

오늘의 종가 [숫자]원, 등락률 [숫자]%, 거래량 [숫자]주를 먼저 명시해 주세요.

이 수치를 바탕으로 오늘 하루 동안의 가격 움직임과 시장의 주요 특징(예: 갭 상승/하락, 특정 가격대 돌파 실패 등)을 요약해 주세요.

핵심 기술적 분석 지표 요약:

아래 용어에 대한 간결한 설명을 포함하여, 각 지표의 현재 상태를 구체적인 수치와 함께 요약해 주세요.

이동평균선 정배열 여부: [예/아니오]. (정배열: 단기 이동평균선이 장기 이동평균선 위에 위치하여 상승 추세를 나타내는 강력한 신호.)

골든 크로스/데드 크로스 발생 여부: [예/아니오]. (골든 크로스: 단기 이동평균선이 장기 이동평균선을 상향 돌파하는 현상으로, 매수 시그널로 해석됨.)

MACD 지표 상태: [MACD 수치] vs [시그널 수치]. (MACD: 모멘텀과 추세를 파악하는 지표. MACD 선이 시그널 선 위에 있으면 상승 모멘텀이 강하다는 의미.)

RSI 지표 상태: [RSI 수치]. (RSI: 상대강도지수. 0-100 사이의 값으로 주가 과매수(70 이상) 또는 과매도(30 이하) 상태를 나타냄.)

볼린저밴드: [밴드 폭 변화] (볼린저밴드: 주가의 변동성을 나타내는 지표. 밴드가 좁아지면 변동성 확대를, 넓어지면 추세의 지속을 암시.)

세부 분석 및 종합 판단:

가격 및 거래량:

최근 5일간 평균 거래량 [숫자]주 대비 오늘 거래량은 [숫자]주로, [평균 대비 %] 수준입니다.

특정 가격대([가격])를 중심으로 발생한 장대 양/음봉 또는 대량 거래 봉([거래량]주)의 의미를 구체적으로 분석해 주세요.

이동평균선:

현재 주가([가격])가 5일선([가격]), 20일선([가격]), 60일선([가격]) 대비 어떤 위치에 있는지(위/아래) 정확히 기술해 주세요.

이동평균선이 현재 [밀집/확산] 상태이며, 이는 향후 [변동성 확대/축소] 중 무엇을 시사하는지 판단해 주세요.

모멘텀 및 강도 (MACD, RSI):

MACD 선([수치])과 시그널 선([수치])의 관계를 바탕으로 현재 모멘텀의 강도가 [강함/약함]을 판단하고, MACD 오실레이터의 양/음 전환 여부와 변화를 통해 추세의 방향성을 설명해 주세요.

**RSI 수치([수치])**가 과매수/과매도 구간에 진입했는지 여부를 판단하고, 가격과 지표 간의 다이버전스가 관찰되는 경우 그 의미를 설명해 주세요.

단기 투자 아이디어 (핵심 요약):

위의 종합 분석을 바탕으로, [종목명]의 단기적인 추세 및 모멘텀을 한 문장으로 요약해 주세요.

잠재적인 매수/매도 시점에 대한 핵심적인 투자 아이디어를 '매수/매도 시그널' 같은 표현을 사용하여 구체적으로 제시해 주세요.

**종목명 변환 규칙:**
파일명에서 종목명과 종목코드를 자동으로 추출하여 분석해주세요:

1. **영문 회사명 → 한국어 회사명 변환:**
   - SK_hynix_Inc._000660 → SK하이닉스
   - Samsung_Electronics_Co.,_Ltd._005930 → 삼성전자
   - Hyundai_Motor_Company_005380 → 현대차
   - Kiwoom_Securities_Co.,_Ltd._039490 → 키움증권
   - Aurora_World_Corp_039830 → 오로라월드
   - Heng_Sheng_Holding_Group_Limited_900270 → 항성홀딩그룹
   - 기타 영문명은 한국어 회사명으로 변환

2. **종목코드 → 한국어 회사명 변환:**
   - 380550 → 뉴로펫 (Neurophet)
   - 328130 → 루닛 (Lunit)
   - 338220 → Vuno
   - 종목코드만 있는 경우 해당 종목의 실제 한국어 회사명을 찾아서 사용

3. **파일명 패턴 분석:**
   - weekly_Samsung_Electronics_Co.,_Ltd._005930_20250804.png → 삼성전자 (005930)
   - daily_380550_380550_20250804.png → 뉴로펫 (380550)
   - 파일명에서 언더스코어(_)로 구분된 부분들을 분석하여 종목명과 종목코드 추출

4. **알 수 없는 종목의 경우:**
   - 종목코드는 파일명에서 추출
   - 종목명은 "알 수 없음" 대신 종목코드 그대로 사용하거나, 가능한 경우 영문명을 한국어로 변환

**응답 형식:**
JSON 형태로 응답해주세요. 일봉 차트에 필요한 지표만 포함하여 작성해주세요:

{
  "종목정보": {
    "종목명": "한국어 회사명",
    "종목번호": "6자리 종목코드",
    "분석일시": "YYYY-MM-DD HH:MM:SS",
    "차트유형": "일봉"
  },
  "종합분석점수": {
    "점수": 85,
    "요약": "단기 상승 모멘텀 강함, 매수 시그널"
  },
  "오늘의일봉": {
    "종가": "가격",
    "등락률": "등락률",
    "거래량": "거래량",
    "주요특징": "오늘의 주요 특징"
  },
  "핵심기술적지표": {
    "이동평균선정배열": "예/아니오",
    "골든데드크로스": "예/아니오",
    "MACD상태": "MACD vs 시그널",
    "RSI상태": "RSI 수치",
    "볼린저밴드": "밴드 폭 변화"
  },
  "세부분석": {
    "가격및거래량": {
      "거래량비교": "평균 대비 거래량",
      "주요가격대": "특정 가격대 분석"
    },
    "이동평균선": {
      "현재가위치": "이동평균선 대비 위치",
      "밀집도": "밀집/확산 상태"
    },
    "모멘텀": {
      "MACD분석": "모멘텀 강도 분석",
      "RSI분석": "RSI 구간 및 다이버전스"
    }
  },
  "단기투자아이디어": {
    "추세요약": "단기 추세 요약",
    "매매시그널": "매수/매도 시그널"
  }
}
"""

    @staticmethod
    def get_weekly_prompt() -> str:
        """주봉 차트 분석 프롬프트"""
        return """
역할: 당신은 전문 주식 트레이더이자 차트 분석 전문가입니다. 아래에 제시된 [종목명]의 주봉 차트 이미지를 종합적으로 분석하여, 중기적인 투자 아이디어를 A4 용지 1장 분량으로 간결하게 작성해 주세요.

분석 순서 및 출력 형식:

종합 분석 점수:

주봉 차트의 주요 분석 요소들을 종합하여 현재의 중기 투자 매력도를 100점 만점으로 환산하고, 그 점수와 함께 한 줄 요약을 가장 먼저 제시해 주세요.

이번 주 봉(Weekly Candle) 요약:

이번 주의 종가 [숫자]원, 등락률 [숫자]%, 거래량 [숫자]주를 먼저 명시해 주세요.

이 수치를 바탕으로 지난 한 주 동안의 가격 움직임과 시장의 주요 특징(예: 주요 지지/저항선 터치, 박스권 돌파 시도 등)을 요약해 주세요.

핵심 기술적 분석 지표 요약:

아래 용어에 대한 간결한 설명을 포함하여, 각 지표의 현재 상태를 구체적인 수치와 함께 요약해 주세요.

이동평균선 정배열 여부: [예/아니오]. (정배열: 단기 이동평균선이 장기 이동평균선 위에 위치하여 중기 상승 추세를 나타내는 신호.)

골든 크로스/데드 크로스 발생 여부: [예/아니오]. (골든 크로스: 단기 이평선이 장기 이평선을 상향 돌파하는 현상으로, 중기적인 매수 시그널로 해석됨.)

Stochastic Slow 상태: %K: [수치], %D: [수치]. (Stochastic Slow: 주가 움직임의 속도를 파악하는 지표. 과매수(80 이상) 또는 과매도(20 이하) 구간 진입 여부로 매매 시점을 판단.)

볼린저밴드: [밴드 폭 변화] (볼린저밴드: 주가의 변동성을 나타내는 지표. 밴드 폭이 좁아지면 변동성 확대를, 넓어지면 추세의 지속을 암시.)

세부 분석 및 종합 판단:

가격 및 거래량:

최근 1개월(4주) 평균 거래량 [숫자]주 대비 이번 주 거래량은 [숫자]주로, [평균 대비 %] 수준입니다.

[종목명]은 최근 [N]주간 [하단 가격]원에서 [상단 가격]원 사이의 박스권을 형성하고 있는지, 또는 이탈했는지 구체적으로 분석해 주세요.

이동평균선:

현재 주가([가격])가 5주선([가격]), 20주선([가격]), 60주선([가격]) 대비 어떤 위치에 있는지(위/아래) 정확히 기술해 주세요.

특히 20주선이 중기 추세의 방향성을 결정하는 중요한 [지지선/저항선] 역할을 하는지 분석해 주세요.

모멘텀 및 변동성 (Stochastic, Bollinger Bands):

Stochastic %K 선([수치])과 %D 선([수치])의 교차를 바탕으로 현재 모멘텀의 강도가 [강함/약함]을 판단해 주세요.

볼린저밴드의 폭이 현재 [좁아짐/넓어짐] 상태이며, 이는 향후 [변동성 확대/축소] 가능성을 시사한다고 판단해 주세요.

종합적인 중기 투자 아이디어 (핵심 요약):

위의 종합 분석을 바탕으로, [종목명]의 중기적인 추세 방향성과 주요 움직임을 한 문장으로 요약해 주세요.

잠재적인 매수/매도 시점에 대한 핵심적인 투자 아이디어를 '매수/매도 시그널' 같은 표현을 사용하여 구체적으로 제시해 주세요.

**종목명 변환 규칙:**
파일명에서 종목명과 종목코드를 자동으로 추출하여 분석해주세요:

1. **영문 회사명 → 한국어 회사명 변환:**
   - SK_hynix_Inc._000660 → SK하이닉스
   - Samsung_Electronics_Co.,_Ltd._005930 → 삼성전자
   - Hyundai_Motor_Company_005380 → 현대차
   - Kiwoom_Securities_Co.,_Ltd._039490 → 키움증권
   - Aurora_World_Corp_039830 → 오로라월드
   - Heng_Sheng_Holding_Group_Limited_900270 → 항성홀딩그룹
   - 기타 영문명은 한국어 회사명으로 변환

2. **종목코드 → 한국어 회사명 변환:**
   - 380550 → 뉴로펫 (Neurophet)
   - 328130 → 루닛 (Lunit)
   - 338220 → Vuno
   - 종목코드만 있는 경우 해당 종목의 실제 한국어 회사명을 찾아서 사용

3. **파일명 패턴 분석:**
   - weekly_Samsung_Electronics_Co.,_Ltd._005930_20250804.png → 삼성전자 (005930)
   - daily_380550_380550_20250804.png → 뉴로펫 (380550)
   - 파일명에서 언더스코어(_)로 구분된 부분들을 분석하여 종목명과 종목코드 추출

4. **알 수 없는 종목의 경우:**
   - 종목코드는 파일명에서 추출
   - 종목명은 "알 수 없음" 대신 종목코드 그대로 사용하거나, 가능한 경우 영문명을 한국어로 변환

**응답 형식:**
JSON 형태로 응답해주세요. 주봉 차트에 필요한 지표만 포함하여 작성해주세요:

{
  "종목정보": {
    "종목명": "한국어 회사명",
    "종목번호": "6자리 종목코드",
    "분석일시": "YYYY-MM-DD HH:MM:SS",
    "차트유형": "주봉"
  },
  "종합분석점수": {
    "점수": 75,
    "요약": "중기 상승 추세 유지, 박스권 돌파 시도"
  },
  "이번주봉": {
    "종가": "가격",
    "등락률": "등락률",
    "거래량": "거래량",
    "주요특징": "이번 주의 주요 특징"
  },
  "핵심기술적지표": {
    "이동평균선정배열": "예/아니오",
    "골든데드크로스": "예/아니오",
    "Stochastic상태": "%K vs %D",
    "볼린저밴드": "밴드 폭 변화"
  },
  "세부분석": {
    "가격및거래량": {
      "거래량비교": "평균 대비 거래량",
      "박스권분석": "박스권 형성 및 이탈 여부"
    },
    "이동평균선": {
      "현재가위치": "이동평균선 대비 위치",
      "20주선역할": "지지선/저항선 역할"
    },
    "모멘텀": {
      "Stochastic분석": "모멘텀 강도 분석",
      "볼린저밴드분석": "변동성 확대/축소 분석"
    }
  },
  "중기투자아이디어": {
    "추세요약": "중기 추세 요약",
    "매매시그널": "매수/매도 시그널"
  }
}
"""

    @staticmethod
    def get_monthly_prompt() -> str:
        """월봉 차트 분석 프롬프트"""
        return """
역할: 당신은 전문 주식 트레이더이자 차트 분석 전문가입니다. 아래에 제시된 [종목명]의 월봉 차트 이미지를 종합적으로 분석하여, 장기적인 투자 아이디어를 A4 용지 1장 분량으로 간결하게 작성해 주세요.

분석 순서 및 출력 형식:

종합 분석 점수:

월봉 차트의 주요 분석 요소들을 종합하여 현재의 장기 투자 매력도를 100점 만점으로 환산하고, 그 점수와 함께 한 줄 요약을 가장 먼저 제시해 주세요.

이번 월봉(Monthly Candle) 요약:

이번 달의 종가 [숫자]원, 등락률 [숫자]%, 거래량 [숫자]주를 먼저 명시해 주세요.

이 수치를 바탕으로 지난 한 달 동안의 가격 움직임과 시장의 주요 특징(예: 사상 최고가/최저가 경신, 중요한 가격대 터치 등)을 요약해 주세요.

핵심 기술적 분석 지표 요약:

아래 용어에 대한 간결한 설명을 포함하여, 각 지표의 현재 상태를 구체적인 수치와 함께 요약해 주세요.

장기 정배열 여부: [예/아니오]. (장기 정배열: 장기 이동평균선이 안정적인 상승 추세를 유지하는 상태로, 장기 투자 관점에서 긍정적인 신호.)

CCI 지표 상태: [CCI 수치]. (CCI: 추세의 시작과 전환을 파악하는 지표. 과매수(+100 이상) 또는 과매도(-100 이하) 구간 진입 여부로 추세의 극단을 판단.)

ADX 지표 상태: [ADX 수치]. (ADX: 추세의 강도를 측정하는 지표. 20 이상이면 추세가 존재하며, 수치가 높을수록 추세가 강하다는 의미.)

주요 이동평균선 위치: [5개월선/10개월선/20개월선]. (이동평균선: 특정 기간의 평균 가격을 나타내는 선. 장기 차트에서는 중요한 지지선/저항선 역할을 함.)

세부 분석 및 종합 판단:

가격 및 거래량:

지난 6개월간 평균 거래량 [숫자]주 대비 이번 달 거래량은 [숫자]주로, [평균 대비 %] 수준입니다.

차트 상의 **역사적인 고점([가격])과 저점([가격])**을 언급하며, 현재 가격([가격])이 장기 주가 사이클 상 어느 위치에 있는지 분석해 주세요.

이동평균선:

현재 주가([가격])가 5개월선([가격]), 10개월선([가격]), 20개월선([가격]) 대비 어떤 위치에 있는지(위/아래) 정확히 기술해 주세요.

특히 20개월선이 장기 추세의 방향성을 나타내는 중요한 [지지선/저항선] 역할을 하는지 분석해 주세요.

모멘텀 및 추세 강도 (CCI, ADX):

**CCI 수치([수치])**가 과매수/과매도 구간에 진입했는지 여부를 판단하고, 0선을 [상향/하향] 돌파했는지 여부와 그 의미를 설명해 주세요.

**ADX 수치([수치])**를 통해 현재 [추세의 강도가 강화/약화]되고 있다고 판단하고, 추세가 [상승/하락/횡보] 중 어느 방향으로 나아가고 있는지 설명해 주세요.

종합적인 장기 투자 아이디어 (핵심 요약):

위의 종합 분석을 바탕으로, [종목명]의 장기적인 주가 사이클 및 거시적인 추세를 한 문장으로 요약해 주세요.

장기 투자 관점에서의 핵심적인 아이디어를 '장기 보유', '분할 매수', '관망' 등의 표현을 사용하여 구체적으로 제시해 주세요.

**종목명 변환 규칙:**
파일명에서 종목명과 종목코드를 자동으로 추출하여 분석해주세요:

1. **영문 회사명 → 한국어 회사명 변환:**
   - SK_hynix_Inc._000660 → SK하이닉스
   - Samsung_Electronics_Co.,_Ltd._005930 → 삼성전자
   - Hyundai_Motor_Company_005380 → 현대차
   - Kiwoom_Securities_Co.,_Ltd._039490 → 키움증권
   - Aurora_World_Corp_039830 → 오로라월드
   - Heng_Sheng_Holding_Group_Limited_900270 → 항성홀딩그룹
   - 기타 영문명은 한국어 회사명으로 변환

2. **종목코드 → 한국어 회사명 변환:**
   - 380550 → 뉴로펫 (Neurophet)
   - 328130 → 루닛 (Lunit)
   - 338220 → Vuno
   - 종목코드만 있는 경우 해당 종목의 실제 한국어 회사명을 찾아서 사용

3. **파일명 패턴 분석:**
   - weekly_Samsung_Electronics_Co.,_Ltd._005930_20250804.png → 삼성전자 (005930)
   - daily_380550_380550_20250804.png → 뉴로펫 (380550)
   - 파일명에서 언더스코어(_)로 구분된 부분들을 분석하여 종목명과 종목코드 추출

4. **알 수 없는 종목의 경우:**
   - 종목코드는 파일명에서 추출
   - 종목명은 "알 수 없음" 대신 종목코드 그대로 사용하거나, 가능한 경우 영문명을 한국어로 변환

**응답 형식:**
JSON 형태로 응답해주세요. 월봉 차트에 필요한 지표만 포함하여 작성해주세요:

{
  "종목정보": {
    "종목명": "한국어 회사명",
    "종목번호": "6자리 종목코드",
    "분석일시": "YYYY-MM-DD HH:MM:SS",
    "차트유형": "월봉"
  },
  "종합분석점수": {
    "점수": 65,
    "요약": "장기 상승 추세 유지, 분할 매수 적기"
  },
  "이번월봉": {
    "종가": "가격",
    "등락률": "등락률",
    "거래량": "거래량",
    "주요특징": "이번 달의 주요 특징"
  },
  "핵심기술적지표": {
    "장기정배열": "예/아니오",
    "CCI상태": "CCI 수치",
    "ADX상태": "ADX 수치",
    "주요이동평균선": "5개월선/10개월선/20개월선"
  },
  "세부분석": {
    "가격및거래량": {
      "거래량비교": "평균 대비 거래량",
      "역사적고점저점": "역사적 고점/저점 분석"
    },
    "이동평균선": {
      "현재가위치": "이동평균선 대비 위치",
      "20개월선역할": "지지선/저항선 역할"
    },
    "모멘텀": {
      "CCI분석": "CCI 구간 및 0선 돌파 분석",
      "ADX분석": "추세 강도 및 방향성 분석"
    }
  },
  "장기투자아이디어": {
    "사이클요약": "장기 주가 사이클 요약",
    "투자전략": "장기 투자 전략"
  }
}
"""

    @staticmethod
    def get_prompt(chart_type: str) -> str:
        """차트 유형에 따른 프롬프트 반환"""
        chart_type = chart_type.lower()
        if chart_type in ['daily', '일봉', 'day']:
            return ChartAnalysisPrompts.get_daily_prompt()
        elif chart_type in ['weekly', '주봉', 'week']:
            return ChartAnalysisPrompts.get_weekly_prompt()
        elif chart_type in ['monthly', '월봉', 'month']:
            return ChartAnalysisPrompts.get_monthly_prompt()
        else:
            # 기본값은 일봉
            return ChartAnalysisPrompts.get_daily_prompt()

class AIChartAnalyzer:
    def __init__(self, api_key: str, stock_list_file: str = "sotck_list.txt"):
        """
        AI 차트 분석기 초기화
        
        Args:
            api_key (str): Google AI API 키
            stock_list_file (str): 종목 리스트 파일 경로
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # 제미나이 모델 설정
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 종목명 매퍼 초기화
        self.stock_mapper = StockNameMapper(stock_list_file)

    def encode_image_to_base64(self, image_path: str) -> str:
        """
        이미지를 base64로 인코딩
        
        Args:
            image_path (str): 이미지 파일 경로
            
        Returns:
            str: base64 인코딩된 이미지
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"❌ 이미지 인코딩 오류: {e}")
            return ""

    def analyze_chart_image(self, image_path: str, stock_name: str = "", chart_type: str = "일봉", chart_data: Optional[pd.DataFrame] = None, 
                           json_data_path: str = "", csv_data_path: str = "", text_summary_path: str = "") -> Optional[Dict[str, Any]]:
        """
        차트 이미지를 AI로 분석 (개선된 버전 - JSON/CSV/텍스트 데이터 지원)
        
        Args:
            image_path (str): 차트 이미지 파일 경로
            stock_name (str): 종목명
            chart_type (str): 차트 유형 (일봉/주봉/월봉)
            chart_data (pd.DataFrame): 차트 데이터 (Open, High, Low, Close, Volume)
            json_data_path (str): JSON 데이터 파일 경로
            csv_data_path (str): CSV 데이터 파일 경로
            text_summary_path (str): 텍스트 요약 파일 경로
            
        Returns:
            Dict[str, Any]: 분석 결과 JSON
        """
        try:
            print(f"🔍 AI 차트 분석 시작: {image_path}")
            print(f"📊 차트 유형: {chart_type}")
            
            # 파일명에서 종목정보 추출
            filename = os.path.basename(image_path)
            extracted_stock_name, extracted_stock_code = self.stock_mapper.extract_stock_info_from_filename(filename)
            
            # 종목명이 제공되지 않은 경우 추출된 정보 사용
            if not stock_name:
                stock_name = extracted_stock_name
                # 종목번호로 정확한 종목명 조회
                if extracted_stock_code and extracted_stock_code != "000000":
                    stock_name = self.stock_mapper.get_stock_name(extracted_stock_code)
            
            print(f"📈 종목명: {stock_name}")
            print(f"📈 종목번호: {extracted_stock_code}")
            
            # 1. 이미지 파일 존재 및 무결성 검증
            if not os.path.exists(image_path):
                print(f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
                return None
            
            # 이미지 파일 크기 확인
            file_size = os.path.getsize(image_path)
            print(f"📊 이미지 파일 크기: {file_size:,} bytes")
            
            if file_size == 0:
                print(f"❌ 이미지 파일이 비어있습니다: {image_path}")
                return None
            
            # 2. 이미지 형식 및 크기 검증
            try:
                with Image.open(image_path) as img:
                    print(f"📊 이미지 크기: {img.size}")
                    print(f"📊 이미지 형식: {img.format}")
                    print(f"📊 이미지 모드: {img.mode}")
                    
                    # 이미지 크기가 너무 작으면 경고
                    if img.size[0] < 100 or img.size[1] < 100:
                        print(f"⚠️ 이미지 크기가 너무 작습니다: {img.size}")
                    
                    # 이미지가 너무 크면 리사이즈 고려
                    if img.size[0] > 4000 or img.size[1] > 4000:
                        print(f"⚠️ 이미지 크기가 너무 큽니다: {img.size}")
                        print(f"🔄 이미지를 2000x2000으로 리사이즈합니다...")
                        
                        # 이미지 리사이즈
                        max_size = 2000
                        if img.size[0] > img.size[1]:
                            new_width = max_size
                            new_height = int(img.size[1] * max_size / img.size[0])
                        else:
                            new_height = max_size
                            new_width = int(img.size[0] * max_size / img.size[1])
                        
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        print(f"✅ 이미지 리사이즈 완료: {img.size}")
                        
            except Exception as e:
                print(f"❌ 이미지 파일 검증 실패: {e}")
                return None
            
            # 3. 차트 유형에 따른 프롬프트 선택
            prompt = ChartAnalysisPrompts.get_prompt(chart_type)
            
            # 4. 추가 데이터 파일들 로드 및 프롬프트에 추가
            additional_data_info = self._load_additional_data_files(json_data_path, csv_data_path, text_summary_path)
            if additional_data_info:
                prompt += f"\n\n{additional_data_info}"
                print(f"✅ 추가 데이터 파일 정보가 프롬프트에 추가되었습니다.")
            
            # 5. 차트 데이터 정보를 프롬프트에 추가 (기존 방식)
            if chart_data is not None and not chart_data.empty:
                print(f"📊 차트 데이터 정보 추가: {len(chart_data)}개 데이터 포인트")
                
                # 최근 데이터 요약 정보 생성
                recent_data = chart_data.tail(10)  # 최근 10개 데이터
                
                data_summary = f"""
**차트 데이터 정보:**
- 데이터 기간: {chart_data.index[0].strftime('%Y-%m-%d')} ~ {chart_data.index[-1].strftime('%Y-%m-%d')}
- 총 데이터 수: {len(chart_data)}개
- 최근 10개 데이터:
"""
                
                for i, (date, row) in enumerate(recent_data.iterrows()):
                    data_summary += f"- {date.strftime('%Y-%m-%d')}: 시가 {row['Open']:,.0f}, 고가 {row['High']:,.0f}, 저가 {row['Low']:,.0f}, 종가 {row['Close']:,.0f}, 거래량 {row['Volume']:,.0f}\n"
                
                # 기술적 지표 정보 추가 (있는 경우)
                if 'MA5' in chart_data.columns:
                    data_summary += f"- 5기간 이동평균: {chart_data['MA5'].iloc[-1]:,.0f}\n"
                if 'MA20' in chart_data.columns:
                    data_summary += f"- 20기간 이동평균: {chart_data['MA20'].iloc[-1]:,.0f}\n"
                if 'RSI' in chart_data.columns:
                    data_summary += f"- RSI: {chart_data['RSI'].iloc[-1]:.1f}\n"
                if 'MACD' in chart_data.columns:
                    data_summary += f"- MACD: {chart_data['MACD'].iloc[-1]:.2f}\n"
                
                # 가격 변동 정보
                price_change = chart_data['Close'].iloc[-1] - chart_data['Open'].iloc[0]
                price_change_pct = (price_change / chart_data['Open'].iloc[0]) * 100
                data_summary += f"- 전체 기간 가격 변동: {price_change:+,.0f}원 ({price_change_pct:+.2f}%)\n"
                
                # 최근 변동 정보
                recent_change = chart_data['Close'].iloc[-1] - chart_data['Close'].iloc[-2] if len(chart_data) > 1 else 0
                recent_change_pct = (recent_change / chart_data['Close'].iloc[-2]) * 100 if len(chart_data) > 1 else 0
                data_summary += f"- 최근 변동: {recent_change:+,.0f}원 ({recent_change_pct:+.2f}%)\n"
                
                prompt += data_summary
                
                print(f"✅ 차트 데이터 정보가 프롬프트에 추가되었습니다.")
            else:
                print(f"⚠️ 차트 데이터가 제공되지 않았습니다. 이미지와 추가 데이터 파일만으로 분석을 진행합니다.")
            
            # 종목명 정보를 프롬프트에 추가
            prompt += f"\n\n**중요: 분석할 종목은 '{stock_name}' (종목번호: {extracted_stock_code})입니다.**"
            prompt = prompt.replace("[종목명]", stock_name)
            
            # 6. AI 분석 재시도 메커니즘
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"🔄 AI 분석 시도 {attempt + 1}/{max_retries}")
                    
                    # 이미지 로드 및 리사이즈
                    image = Image.open(image_path)
                    
                    # 이미지가 너무 크면 리사이즈
                    if image.size[0] > 2000 or image.size[1] > 2000:
                        max_size = 2000
                        if image.size[0] > image.size[1]:
                            new_width = max_size
                            new_height = int(image.size[1] * max_size / image.size[0])
                        else:
                            new_height = max_size
                            new_width = int(image.size[0] * max_size / image.size[1])
                        
                        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        print(f"🔄 AI 분석용 이미지 리사이즈: {image.size}")
                    
                    # AI 분석 요청 (이미지를 base64로 인코딩하여 전송)
                    try:
                        # 이미지를 base64로 인코딩
                        import base64
                        import io
                        
                        # 이미지를 메모리에 저장
                        img_buffer = io.BytesIO()
                        image.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        
                        # base64로 인코딩
                        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                        print(f"📊 이미지 base64 인코딩 완료: {len(img_base64)} 문자")
                        
                        # AI 분석 요청 (base64 이미지 포함)
                        response = self.model.generate_content([
                            prompt,
                            {
                                "mime_type": "image/png",
                                "data": img_base64
                            }
                        ])
                        
                        # 응답이 이미지를 인식하지 못하는 경우, 다른 방식 시도
                        if "이미지가 제공되지 않았으므로" in response.text or "이미지가 없으므로" in response.text:
                            print("⚠️ AI가 이미지를 인식하지 못함. 다른 방식으로 시도...")
                            
                            # 파일 경로를 직접 전달하는 방식 시도
                            response = self.model.generate_content([
                                prompt + "\n\n이미지 파일 경로: " + image_path,
                                image
                            ])
                        
                    except Exception as e:
                        print(f"⚠️ base64 인코딩 실패, 기본 방식으로 시도: {e}")
                        # 기본 방식으로 시도
                        response = self.model.generate_content([
                            prompt,
                            image
                        ])
                    
                    if response.text:
                        print(f"✅ AI 분석 완료 (시도 {attempt + 1})")
                        print(f"📝 AI 응답 길이: {len(response.text)}")
                        print(f"📝 AI 응답 시작: {response.text[:100]}...")
                        
                        # 7. 응답 검증 및 JSON 파싱
                        if self._is_valid_json_response(response.text):
                            try:
                                analysis_result = self._parse_json_response(response.text)
                                
                                # 분석 일시 및 차트 유형 추가
                                if "종목정보" in analysis_result:
                                    analysis_result["종목정보"]["분석일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    analysis_result["종목정보"]["차트유형"] = chart_type
                                    # 종목정보가 없는 경우 추가
                                    if "종목명" not in analysis_result["종목정보"]:
                                        analysis_result["종목정보"]["종목명"] = stock_name
                                    if "종목번호" not in analysis_result["종목정보"]:
                                        analysis_result["종목정보"]["종목번호"] = extracted_stock_code
                                else:
                                    # 종목정보 섹션이 없는 경우 생성
                                    analysis_result["종목정보"] = {
                                        "종목명": stock_name,
                                        "종목번호": extracted_stock_code,
                                        "분석일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "차트유형": chart_type
                                    }
                                
                                print(f"✅ JSON 파싱 성공 (시도 {attempt + 1})")
                                return analysis_result
                                
                            except json.JSONDecodeError as e:
                                print(f"⚠️ JSON 파싱 오류 (시도 {attempt + 1}): {e}")
                                if attempt < max_retries - 1:
                                    print(f"🔄 재시도 중... ({attempt + 2}/{max_retries})")
                                    time.sleep(2)
                                    continue
                                else:
                                    print(f"❌ 모든 시도 실패. 마지막 응답: {response.text}")
                                    return self._create_fallback_result(stock_name, chart_type, response.text, "JSON 파싱 실패", extracted_stock_code)
                        else:
                            print(f"⚠️ AI 응답이 JSON 형식이 아닙니다 (시도 {attempt + 1})")
                            if attempt < max_retries - 1:
                                print(f"🔄 재시도 중... ({attempt + 2}/{max_retries})")
                                time.sleep(2)
                                continue
                            else:
                                print(f"❌ 모든 시도 실패. 마지막 응답: {response.text}")
                                return self._create_fallback_result(stock_name, chart_type, response.text, "JSON 형식 아님", extracted_stock_code)
                    else:
                        print(f"❌ AI 분석 응답이 없습니다 (시도 {attempt + 1})")
                        if attempt < max_retries - 1:
                            print(f"🔄 재시도 중... ({attempt + 2}/{max_retries})")
                            time.sleep(2)
                            continue
                        else:
                            return None
                            
                except Exception as e:
                    print(f"❌ AI 분석 중 오류 발생 (시도 {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        print(f"🔄 재시도 중... ({attempt + 2}/{max_retries})")
                        time.sleep(2)
                        continue
                    else:
                        return None
            
            return None
                
        except Exception as e:
            print(f"❌ AI 분석 중 예상치 못한 오류 발생: {e}")
            return None
    
    def _is_valid_json_response(self, response_text: str) -> bool:
        """AI 응답이 유효한 JSON 형식인지 확인"""
        text = response_text.strip()
        
        # JSON 코드 블록 제거 (더 강력한 방식)
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        # JSON 형식인지 확인
        is_json = text.startswith('{') and text.endswith('}')
        
        # 디버깅을 위한 로그 추가
        print(f"🔍 JSON 검증: {is_json}")
        print(f"🔍 응답 시작: {text[:50]}...")
        print(f"🔍 응답 끝: ...{text[-50:]}")
        
        return is_json
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """AI 응답에서 JSON 파싱"""
        json_text = response_text.strip()
        
        # JSON 코드 블록 제거 (더 강력한 방식)
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        elif json_text.startswith('```'):
            json_text = json_text[3:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
        
        # 앞뒤 공백 제거
        json_text = json_text.strip()
        
        return json.loads(json_text)
    
    def _create_fallback_result(self, stock_name: str, chart_type: str, ai_response: str, error_type: str, stock_code: str = "000000") -> Dict[str, Any]:
        """JSON 파싱 실패 시 대체 결과 생성"""
        return {
            "종목정보": {
                "종목명": stock_name,
                "종목번호": stock_code,
                "분석일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "차트유형": chart_type,
                "파싱상태": error_type
            },
            "AI분석결과": ai_response
        }

    def save_analysis_result(self, result: Dict[str, Any], output_path: str) -> bool:
        """
        분석 결과를 JSON 파일로 저장
        
        Args:
            result (Dict[str, Any]): 분석 결과
            output_path (str): 저장할 파일 경로
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 출력 디렉토리 생성
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # JSON 파일로 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"💾 JSON 분석 결과 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ JSON 결과 저장 중 오류: {e}")
            return False

    def create_word_document(self, result: Dict[str, Any], chart_image_path: str, output_path: str, chart_type: str = "일봉") -> bool:
        """
        분석 결과를 Word 문서로 생성
        
        Args:
            result (Dict[str, Any]): 분석 결과
            chart_image_path (str): 차트 이미지 경로
            output_path (str): 저장할 Word 파일 경로
            chart_type (str): 차트 유형 (일봉/주봉/월봉)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 출력 디렉토리 생성
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Word 문서 생성
            doc = Document()
            
            # 한글 폰트 설정을 위한 스타일 설정
            from docx.oxml.ns import qn
            
            # 제목 설정
            title = doc.add_heading('AI 주식 차트 분석 리포트', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # 제목에 한글 폰트 적용
            for run in title.runs:
                run.font.name = '맑은 고딕'
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            # 종목 정보
            heading1 = doc.add_heading('종목 정보', level=1)
            for run in heading1.runs:
                run.font.name = '맑은 고딕'
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            if "종목정보" in result:
                info = result["종목정보"]
                p1 = doc.add_paragraph(f"종목명: {info.get('종목명', 'N/A')}")
                p2 = doc.add_paragraph(f"종목번호: {info.get('종목번호', 'N/A')}")
                p3 = doc.add_paragraph(f"분석일시: {info.get('분석일시', 'N/A')}")
                p4 = doc.add_paragraph(f"차트유형: {info.get('차트유형', 'N/A')}")
                # 한글 폰트 적용
                for p in [p1, p2, p3, p4]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            # 종합 분석 점수
            if "종합분석점수" in result:
                heading_score = doc.add_heading('종합 분석 점수', level=1)
                for run in heading_score.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                score = result["종합분석점수"]
                p_score1 = doc.add_paragraph(f"점수: {score.get('점수', 'N/A')}/100")
                p_score2 = doc.add_paragraph(f"요약: {score.get('요약', 'N/A')}")
                
                # 점수 강조
                p_score1.runs[0].bold = True
                p_score1.runs[0].font.size = Pt(14)
                
                for p in [p_score1, p_score2]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            # 차트 이미지 추가
            heading2 = doc.add_heading('차트 이미지', level=1)
            for run in heading2.runs:
                run.font.name = '맑은 고딕'
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            if os.path.exists(chart_image_path):
                doc.add_picture(chart_image_path, width=Inches(6))
                doc.add_paragraph()
            
            # 오늘의 봉 요약 (일봉/주봉/월봉)
            if chart_type == "일봉" and "오늘의일봉" in result:
                heading_candle = doc.add_heading('오늘의 일봉 요약', level=1)
                for run in heading_candle.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                candle = result["오늘의일봉"]
                p_candle1 = doc.add_paragraph(f"종가: {candle.get('종가', 'N/A')}원")
                p_candle2 = doc.add_paragraph(f"등락률: {candle.get('등락률', 'N/A')}%")
                p_candle3 = doc.add_paragraph(f"거래량: {candle.get('거래량', 'N/A')}주")
                p_candle4 = doc.add_paragraph(f"주요 특징: {candle.get('주요특징', 'N/A')}")
                
                for p in [p_candle1, p_candle2, p_candle3, p_candle4]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            elif chart_type == "주봉" and "이번주봉" in result:
                heading_candle = doc.add_heading('이번 주 봉 요약', level=1)
                for run in heading_candle.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                candle = result["이번주봉"]
                p_candle1 = doc.add_paragraph(f"종가: {candle.get('종가', 'N/A')}원")
                p_candle2 = doc.add_paragraph(f"등락률: {candle.get('등락률', 'N/A')}%")
                p_candle3 = doc.add_paragraph(f"거래량: {candle.get('거래량', 'N/A')}주")
                p_candle4 = doc.add_paragraph(f"주요 특징: {candle.get('주요특징', 'N/A')}")
                
                for p in [p_candle1, p_candle2, p_candle3, p_candle4]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            elif chart_type == "월봉" and "이번월봉" in result:
                heading_candle = doc.add_heading('이번 월봉 요약', level=1)
                for run in heading_candle.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                candle = result["이번월봉"]
                p_candle1 = doc.add_paragraph(f"종가: {candle.get('종가', 'N/A')}원")
                p_candle2 = doc.add_paragraph(f"등락률: {candle.get('등락률', 'N/A')}%")
                p_candle3 = doc.add_paragraph(f"거래량: {candle.get('거래량', 'N/A')}주")
                p_candle4 = doc.add_paragraph(f"주요 특징: {candle.get('주요특징', 'N/A')}")
                
                for p in [p_candle1, p_candle2, p_candle3, p_candle4]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            # 핵심 기술적 분석 지표
            if "핵심기술적지표" in result:
                heading_tech = doc.add_heading('핵심 기술적 분석 지표', level=1)
                for run in heading_tech.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                tech = result["핵심기술적지표"]
                
                # 일봉 차트 지표들
                if chart_type == "일봉":
                    if "이동평균선정배열" in tech:
                        p_tech1 = doc.add_paragraph(f"이동평균선 정배열: {tech.get('이동평균선정배열', 'N/A')}")
                    if "골든데드크로스" in tech:
                        p_tech2 = doc.add_paragraph(f"골든/데드 크로스: {tech.get('골든데드크로스', 'N/A')}")
                    if "MACD상태" in tech:
                        p_tech3 = doc.add_paragraph(f"MACD 상태: {tech.get('MACD상태', 'N/A')}")
                    if "RSI상태" in tech:
                        p_tech4 = doc.add_paragraph(f"RSI 상태: {tech.get('RSI상태', 'N/A')}")
                    if "볼린저밴드" in tech:
                        p_tech5 = doc.add_paragraph(f"볼린저밴드: {tech.get('볼린저밴드', 'N/A')}")
                
                # 주봉 차트 지표들
                elif chart_type == "주봉":
                    if "이동평균선정배열" in tech:
                        p_tech1 = doc.add_paragraph(f"이동평균선 정배열: {tech.get('이동평균선정배열', 'N/A')}")
                    if "골든데드크로스" in tech:
                        p_tech2 = doc.add_paragraph(f"골든/데드 크로스: {tech.get('골든데드크로스', 'N/A')}")
                    if "Stochastic상태" in tech:
                        p_tech3 = doc.add_paragraph(f"Stochastic 상태: {tech.get('Stochastic상태', 'N/A')}")
                    if "볼린저밴드" in tech:
                        p_tech4 = doc.add_paragraph(f"볼린저밴드: {tech.get('볼린저밴드', 'N/A')}")
                
                # 월봉 차트 지표들
                elif chart_type == "월봉":
                    if "장기정배열" in tech:
                        p_tech1 = doc.add_paragraph(f"장기 정배열: {tech.get('장기정배열', 'N/A')}")
                    if "CCI상태" in tech:
                        p_tech2 = doc.add_paragraph(f"CCI 상태: {tech.get('CCI상태', 'N/A')}")
                    if "ADX상태" in tech:
                        p_tech3 = doc.add_paragraph(f"ADX 상태: {tech.get('ADX상태', 'N/A')}")
                    if "주요이동평균선" in tech:
                        p_tech4 = doc.add_paragraph(f"주요 이동평균선: {tech.get('주요이동평균선', 'N/A')}")
                
                # 한글 폰트 적용
                tech_paragraphs = []
                for i in range(1, 6):
                    if f'p_tech{i}' in locals():
                        tech_paragraphs.append(locals()[f'p_tech{i}'])
                
                for p in tech_paragraphs:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            # 세부 분석
            if "세부분석" in result:
                heading_detail = doc.add_heading('세부 분석', level=1)
                for run in heading_detail.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                detail = result["세부분석"]
                
                # 가격 및 거래량 분석
                if "가격및거래량" in detail:
                    sub_heading1 = doc.add_heading('가격 및 거래량', level=2)
                    for run in sub_heading1.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                    
                    price_vol = detail["가격및거래량"]
                    if "거래량비교" in price_vol:
                        p_detail1 = doc.add_paragraph(f"거래량 비교: {price_vol.get('거래량비교', 'N/A')}")
                    if "주요가격대" in price_vol:
                        p_detail2 = doc.add_paragraph(f"주요 가격대: {price_vol.get('주요가격대', 'N/A')}")
                    if "박스권분석" in price_vol:
                        p_detail3 = doc.add_paragraph(f"박스권 분석: {price_vol.get('박스권분석', 'N/A')}")
                    if "역사적고점저점" in price_vol:
                        p_detail4 = doc.add_paragraph(f"역사적 고점/저점: {price_vol.get('역사적고점저점', 'N/A')}")
                
                # 이동평균선 분석
                if "이동평균선" in detail:
                    sub_heading2 = doc.add_heading('이동평균선', level=2)
                    for run in sub_heading2.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                    
                    ma = detail["이동평균선"]
                    if "현재가위치" in ma:
                        p_detail5 = doc.add_paragraph(f"현재가 위치: {ma.get('현재가위치', 'N/A')}")
                    if "밀집도" in ma:
                        p_detail6 = doc.add_paragraph(f"밀집도: {ma.get('밀집도', 'N/A')}")
                    if "20주선역할" in ma:
                        p_detail7 = doc.add_paragraph(f"20주선 역할: {ma.get('20주선역할', 'N/A')}")
                    if "20개월선역할" in ma:
                        p_detail8 = doc.add_paragraph(f"20개월선 역할: {ma.get('20개월선역할', 'N/A')}")
                
                # 모멘텀 분석
                if "모멘텀" in detail:
                    sub_heading3 = doc.add_heading('모멘텀 및 강도', level=2)
                    for run in sub_heading3.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                    
                    momentum = detail["모멘텀"]
                    if "MACD분석" in momentum:
                        p_detail9 = doc.add_paragraph(f"MACD 분석: {momentum.get('MACD분석', 'N/A')}")
                    if "RSI분석" in momentum:
                        p_detail10 = doc.add_paragraph(f"RSI 분석: {momentum.get('RSI분석', 'N/A')}")
                    if "Stochastic분석" in momentum:
                        p_detail11 = doc.add_paragraph(f"Stochastic 분석: {momentum.get('Stochastic분석', 'N/A')}")
                    if "볼린저밴드분석" in momentum:
                        p_detail12 = doc.add_paragraph(f"볼린저밴드 분석: {momentum.get('볼린저밴드분석', 'N/A')}")
                    if "CCI분석" in momentum:
                        p_detail13 = doc.add_paragraph(f"CCI 분석: {momentum.get('CCI분석', 'N/A')}")
                    if "ADX분석" in momentum:
                        p_detail14 = doc.add_paragraph(f"ADX 분석: {momentum.get('ADX분석', 'N/A')}")
                
                # 세부 분석 한글 폰트 적용
                detail_paragraphs = []
                for i in range(1, 15):
                    if f'p_detail{i}' in locals():
                        detail_paragraphs.append(locals()[f'p_detail{i}'])
                
                for p in detail_paragraphs:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            # 투자 아이디어
            if chart_type == "일봉" and "단기투자아이디어" in result:
                heading_idea = doc.add_heading('단기 투자 아이디어', level=1)
                for run in heading_idea.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                idea = result["단기투자아이디어"]
                if "추세요약" in idea:
                    p_idea1 = doc.add_paragraph(f"추세 요약: {idea.get('추세요약', 'N/A')}")
                if "매매시그널" in idea:
                    p_idea2 = doc.add_paragraph(f"매매 시그널: {idea.get('매매시그널', 'N/A')}")
                    p_idea2.runs[0].bold = True
                    p_idea2.runs[0].font.size = Pt(14)
                
                for p in [p_idea1, p_idea2]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            elif chart_type == "주봉" and "중기투자아이디어" in result:
                heading_idea = doc.add_heading('중기 투자 아이디어', level=1)
                for run in heading_idea.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                idea = result["중기투자아이디어"]
                if "추세요약" in idea:
                    p_idea1 = doc.add_paragraph(f"추세 요약: {idea.get('추세요약', 'N/A')}")
                if "매매시그널" in idea:
                    p_idea2 = doc.add_paragraph(f"매매 시그널: {idea.get('매매시그널', 'N/A')}")
                    p_idea2.runs[0].bold = True
                    p_idea2.runs[0].font.size = Pt(14)
                
                for p in [p_idea1, p_idea2]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            
            elif chart_type == "월봉" and "장기투자아이디어" in result:
                heading_idea = doc.add_heading('장기 투자 아이디어', level=1)
                for run in heading_idea.runs:
                    run.font.name = '맑은 고딕'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
                
                idea = result["장기투자아이디어"]
                if "사이클요약" in idea:
                    p_idea1 = doc.add_paragraph(f"사이클 요약: {idea.get('사이클요약', 'N/A')}")
                if "투자전략" in idea:
                    p_idea2 = doc.add_paragraph(f"투자 전략: {idea.get('투자전략', 'N/A')}")
                    p_idea2.runs[0].bold = True
                    p_idea2.runs[0].font.size = Pt(14)
                
                for p in [p_idea1, p_idea2]:
                    for run in p.runs:
                        run.font.name = '맑은 고딕'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
            

            
            # 문서 저장
            doc.save(output_path)
            print(f"📄 Word 문서 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Word 문서 생성 중 오류: {e}")
            return False

    def _load_additional_data_files(self, json_data_path: str, csv_data_path: str, text_summary_path: str) -> str:
        """
        추가 데이터 파일들을 로드하고 프롬프트용 텍스트로 변환
        
        Args:
            json_data_path (str): JSON 데이터 파일 경로
            csv_data_path (str): CSV 데이터 파일 경로
            text_summary_path (str): 텍스트 요약 파일 경로
            
        Returns:
            str: 프롬프트에 추가할 데이터 정보 텍스트
        """
        additional_info = ""
        
        # 1. JSON 데이터 파일 로드
        if json_data_path and os.path.exists(json_data_path):
            try:
                print(f"📊 JSON 데이터 파일 로드 중: {json_data_path}")
                with open(json_data_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # JSON 데이터를 구조화된 텍스트로 변환
                json_info = f"""
**JSON 구조화 데이터 정보:**
- 종목명: {json_data.get('metadata', {}).get('stock_name', 'N/A')}
- 종목코드: {json_data.get('metadata', {}).get('stock_code', 'N/A')}
- 데이터 기간: {json_data.get('metadata', {}).get('data_period', {}).get('start', 'N/A')} ~ {json_data.get('metadata', {}).get('data_period', {}).get('end', 'N/A')}
- 총 데이터 수: {json_data.get('metadata', {}).get('total_records', 'N/A')}개

**요약 정보:**
- 최근 종가: {json_data.get('summary', {}).get('latest_close', 'N/A'):,.0f}원
- 최근 거래량: {json_data.get('summary', {}).get('latest_volume', 'N/A'):,}주
- 가격 변동: {json_data.get('summary', {}).get('price_change', 'N/A'):+,.0f}원
- 변동률: {json_data.get('summary', {}).get('price_change_pct', 'N/A'):+.2f}%
- 최고가: {json_data.get('summary', {}).get('highest_price', 'N/A'):,.0f}원
- 최저가: {json_data.get('summary', {}).get('lowest_price', 'N/A'):,.0f}원
- 평균 거래량: {json_data.get('summary', {}).get('avg_volume', 'N/A'):,.0f}주

**기술적 지표 (최근값):**
"""
                
                # 기술적 지표 정보 추가
                tech_indicators = json_data.get('technical_indicators', {}).get('latest_values', {})
                for indicator, value in tech_indicators.items():
                    if value is not None:
                        if 'ma' in indicator.lower():
                            json_info += f"- {indicator.upper()}: {value:,.0f}원\n"
                        else:
                            json_info += f"- {indicator.upper()}: {value:.2f}\n"
                
                # 최근 차트 데이터 (최대 5개)
                chart_data = json_data.get('chart_data', [])
                if chart_data:
                    json_info += f"\n**최근 5개 거래일 데이터:**\n"
                    for i, data_point in enumerate(chart_data[-5:]):
                        json_info += f"- {data_point['date']}: 시가 {data_point['open']:,.0f}, 고가 {data_point['high']:,.0f}, 저가 {data_point['low']:,.0f}, 종가 {data_point['close']:,.0f}, 거래량 {data_point['volume']:,}\n"
                
                additional_info += json_info
                print(f"✅ JSON 데이터 로드 완료")
                
            except Exception as e:
                print(f"❌ JSON 데이터 파일 로드 실패: {e}")
        
        # 2. CSV 데이터 파일 로드
        if csv_data_path and os.path.exists(csv_data_path):
            try:
                print(f"📊 CSV 데이터 파일 로드 중: {csv_data_path}")
                import pandas as pd
                csv_data = pd.read_csv(csv_data_path, encoding='utf-8-sig')
                
                csv_info = f"""
**CSV 데이터 정보:**
- 파일 경로: {csv_data_path}
- 데이터 수: {len(csv_data)}개
- 컬럼: {', '.join(csv_data.columns.tolist())}

**최근 5개 데이터:**
"""
                
                # 최근 5개 데이터 추가
                for i, row in csv_data.tail(5).iterrows():
                    csv_info += f"- {row.iloc[0]}: 시가 {row['Open']:,.0f}, 고가 {row['High']:,.0f}, 저가 {row['Low']:,.0f}, 종가 {row['Close']:,.0f}, 거래량 {row['Volume']:,}\n"
                
                additional_info += csv_info
                print(f"✅ CSV 데이터 로드 완료")
                
            except Exception as e:
                print(f"❌ CSV 데이터 파일 로드 실패: {e}")
        
        # 3. 텍스트 요약 파일 로드
        if text_summary_path and os.path.exists(text_summary_path):
            try:
                print(f"📊 텍스트 요약 파일 로드 중: {text_summary_path}")
                with open(text_summary_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                text_info = f"""
**텍스트 요약 정보:**
{text_content}
"""
                
                additional_info += text_info
                print(f"✅ 텍스트 요약 로드 완료")
                
            except Exception as e:
                print(f"❌ 텍스트 요약 파일 로드 실패: {e}")
        
        return additional_info

    def analyze_chart_with_data_files(self, image_path: str, json_data_path: str = "", csv_data_path: str = "", 
                                     text_summary_path: str = "", stock_name: str = "", chart_type: str = "일봉") -> Optional[Dict[str, Any]]:
        """
        차트 이미지와 데이터 파일들을 함께 AI로 분석하는 편의 메서드
        
        Args:
            image_path (str): 차트 이미지 파일 경로
            json_data_path (str): JSON 데이터 파일 경로
            csv_data_path (str): CSV 데이터 파일 경로
            text_summary_path (str): 텍스트 요약 파일 경로
            stock_name (str): 종목명
            chart_type (str): 차트 유형 (일봉/주봉/월봉)
            
        Returns:
            Dict[str, Any]: 분석 결과 JSON
        """
        print(f"🚀 차트 이미지와 데이터 파일들을 함께 분석합니다...")
        print(f"📈 차트 이미지: {image_path}")
        print(f"📊 JSON 데이터: {json_data_path if json_data_path else '없음'}")
        print(f"📋 CSV 데이터: {csv_data_path if csv_data_path else '없음'}")
        print(f"📝 텍스트 요약: {text_summary_path if text_summary_path else '없음'}")
        
        return self.analyze_chart_image(
            image_path=image_path,
            stock_name=stock_name,
            chart_type=chart_type,
            json_data_path=json_data_path,
            csv_data_path=csv_data_path,
            text_summary_path=text_summary_path
        )

    def find_related_data_files(self, image_path: str) -> tuple:
        """
        차트 이미지 파일과 관련된 데이터 파일들을 자동으로 찾기
        
        Args:
            image_path (str): 차트 이미지 파일 경로
            
        Returns:
            tuple: (json_path, csv_path, text_path)
        """
        print(f"🔍 관련 데이터 파일들을 찾는 중: {image_path}")
        
        # 이미지 파일명에서 기본 정보 추출
        image_filename = os.path.basename(image_path)
        image_name_without_ext = os.path.splitext(image_filename)[0]
        
        # 파일명에서 종목명과 종목코드 추출
        parts = image_name_without_ext.split('_')
        if len(parts) >= 3:
            chart_type = parts[0]  # daily, weekly, monthly
            stock_name = parts[1]
            stock_code = parts[2]
            date_part = parts[3] if len(parts) > 3 else ""
        else:
            print(f"⚠️ 이미지 파일명 형식을 인식할 수 없습니다: {image_filename}")
            return "", "", ""
        
        # 관련 파일들 찾기
        json_path = ""
        csv_path = ""
        text_path = ""
        
        # 1. JSON 파일 찾기
        json_pattern = f"{chart_type}_{stock_name}_{stock_code}_{date_part}.json"
        json_dir = "chart_data_json"
        if os.path.exists(json_dir):
            for file in os.listdir(json_dir):
                if file.startswith(f"{chart_type}_{stock_name}_{stock_code}_{date_part}"):
                    json_path = os.path.join(json_dir, file)
                    break
        
        # 2. CSV 파일 찾기
        csv_pattern = f"{chart_type}_{stock_name}_{stock_code}_{date_part}.csv"
        csv_dir = "chart_data_csv"
        if os.path.exists(csv_dir):
            for file in os.listdir(csv_dir):
                if file.startswith(f"{chart_type}_{stock_name}_{stock_code}_{date_part}"):
                    csv_path = os.path.join(csv_dir, file)
                    break
        
        # 3. 텍스트 요약 파일 찾기
        text_pattern = f"{chart_type}_{stock_name}_{stock_code}_{date_part}_summary.txt"
        text_dir = "chart_data_text"
        if os.path.exists(text_dir):
            for file in os.listdir(text_dir):
                if file.startswith(f"{chart_type}_{stock_name}_{stock_code}_{date_part}_summary"):
                    text_path = os.path.join(text_dir, file)
                    break
        
        print(f"📊 찾은 관련 파일들:")
        print(f"   JSON: {json_path if json_path else '없음'}")
        print(f"   CSV: {csv_path if csv_path else '없음'}")
        print(f"   텍스트: {text_path if text_path else '없음'}")
        
        return json_path, csv_path, text_path

def main():
    """메인 함수"""
    print("�� AI 제미나이 차트 분석 프로그램 (개선된 버전)")
    print("="*60)
    
    # 설정 파일에서 API 키 로드
    from config import config
    
    api_key = config.get_api_key()
    if not api_key:
        print("❌ API 키가 설정되지 않았습니다.")
        print("Google AI API 키를 입력해주세요:")
        print("(https://makersuite.google.com/app/apikey 에서 발급 가능)")
        
        api_key = input("🔑 Google AI API 키를 입력하세요: ").strip()
        if not api_key:
            print("❌ API 키가 필요합니다.")
            return
        
        # API 키 저장
        if config.set_api_key(api_key):
            print("✅ API 키가 저장되었습니다.")
        else:
            print("⚠️ API 키 저장에 실패했습니다.")
    
    # AI 분석기 초기화
    analyzer = AIChartAnalyzer(api_key)
    
    # 차트 폴더들 확인
    chart_folders = ["daily_charts", "weekly_charts", "monthly_charts"]
    available_folders = []
    
    for folder in chart_folders:
        if os.path.exists(folder):
            chart_files = [f for f in os.listdir(folder) if f.endswith('.png')]
            if chart_files:
                available_folders.append((folder, chart_files))
    
    if not available_folders:
        print("❌ 차트 이미지가 있는 폴더를 찾을 수 없습니다.")
        print("먼저 차트 생성 프로그램을 실행하여 차트를 생성해주세요.")
        return
    
    print("📁 발견된 차트 파일들:")
    file_index = 1
    file_mapping = {}
    
    for folder, files in available_folders:
        chart_type = folder.replace("_charts", "")
        print(f"\n📊 {chart_type} 차트:")
        for file in files:
            print(f"  {file_index}. {file}")
            file_mapping[file_index] = (folder, file, chart_type)
            file_index += 1
    
    # 분석할 파일 선택
    while True:
        try:
            choice = input(f"\n📊 분석할 차트 번호를 선택하세요 (1-{len(file_mapping)}): ").strip()
            file_index = int(choice)
            
            if file_index in file_mapping:
                folder, selected_file, chart_type = file_mapping[file_index]
                break
            else:
                print("❌ 올바른 번호를 입력해주세요.")
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
    
    # 파일 경로 설정
    image_path = os.path.join(folder, selected_file)
    
    print(f"\n🔍 분석 시작: {selected_file}")
    print(f"📁 파일: {image_path}")
    print(f"📊 차트 유형: {chart_type}")
    
    # 관련 데이터 파일들 자동 찾기
    print(f"\n🔍 관련 데이터 파일들을 찾는 중...")
    json_path, csv_path, text_path = analyzer.find_related_data_files(image_path)
    
    # 분석 모드 선택
    print(f"\n📊 분석 모드를 선택하세요:")
    print(f"1. 이미지만으로 분석 (기본)")
    print(f"2. 이미지 + 데이터 파일들과 함께 분석 (권장)")
    
    while True:
        try:
            mode_choice = input("선택 (1 또는 2): ").strip()
            if mode_choice in ['1', '2']:
                break
            else:
                print("❌ 1 또는 2를 입력해주세요.")
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
    
    # AI 분석 실행
    if mode_choice == '1':
        print(f"\n📊 이미지만으로 분석을 진행합니다...")
        result = analyzer.analyze_chart_image(image_path, "", chart_type)
    else:
        print(f"\n📊 이미지와 데이터 파일들을 함께 분석합니다...")
        if json_path or csv_path or text_path:
            print(f"✅ 관련 데이터 파일들을 찾았습니다!")
            result = analyzer.analyze_chart_with_data_files(
                image_path=image_path,
                json_data_path=json_path,
                csv_data_path=csv_path,
                text_summary_path=text_path,
                stock_name="",
                chart_type=chart_type
            )
        else:
            print(f"⚠️ 관련 데이터 파일을 찾을 수 없어 이미지만으로 분석합니다.")
            result = analyzer.analyze_chart_image(image_path, "", chart_type)
    
    if result:
        # 결과 저장
        output_dir = "ai_analysis_results"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"📁 {output_dir} 폴더를 생성했습니다.")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 종목정보 추출
        stock_info = result.get("종목정보", {})
        stock_name = stock_info.get("종목명", "unknown")
        stock_code = stock_info.get("종목번호", "000000")
        
        # JSON 파일 저장
        json_filename = f"analysis_{chart_type}_{stock_name}_{stock_code}_{timestamp}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Word 문서 저장
        doc_filename = f"analysis_{chart_type}_{stock_name}_{stock_code}_{timestamp}.docx"
        doc_path = os.path.join(output_dir, doc_filename)
        
        # JSON 파일 저장
        json_success = analyzer.save_analysis_result(result, json_path)
        
        # Word 문서 생성
        doc_success = analyzer.create_word_document(result, image_path, doc_path, chart_type)
        
        if json_success and doc_success:
            print("\n✅ AI 차트 분석이 완료되었습니다!")
            print(f"📄 JSON 결과 파일: {json_path}")
            print(f"📄 Word 문서 파일: {doc_path}")
            
            # 주요 결과 출력
            if "종합분석점수" in result:
                score = result["종합분석점수"]
                print(f"\n📊 종합 분석 점수: {score.get('점수', 'N/A')}/100")
                print(f"📝 요약: {score.get('요약', 'N/A')}")
            
            # 투자 아이디어 출력
            if chart_type == "일봉" and "단기투자아이디어" in result:
                idea = result["단기투자아이디어"]
                print(f"\n📈 단기 투자 아이디어:")
                print(f"   추세 요약: {idea.get('추세요약', 'N/A')}")
                print(f"   매매 시그널: {idea.get('매매시그널', 'N/A')}")
            elif chart_type == "주봉" and "중기투자아이디어" in result:
                idea = result["중기투자아이디어"]
                print(f"\n📈 중기 투자 아이디어:")
                print(f"   추세 요약: {idea.get('추세요약', 'N/A')}")
                print(f"   매매 시그널: {idea.get('매매시그널', 'N/A')}")
            elif chart_type == "월봉" and "장기투자아이디어" in result:
                idea = result["장기투자아이디어"]
                print(f"\n📈 장기 투자 아이디어:")
                print(f"   사이클 요약: {idea.get('사이클요약', 'N/A')}")
                print(f"   투자 전략: {idea.get('투자전략', 'N/A')}")
        else:
            if not json_success:
                print("❌ JSON 결과 저장에 실패했습니다.")
            if not doc_success:
                print("❌ Word 문서 생성에 실패했습니다.")
    else:
        print("❌ AI 분석에 실패했습니다.")

def analyze_single_chart_with_data(image_path: str, json_data_path: str = "", csv_data_path: str = "", 
                                  text_summary_path: str = "", chart_type: str = "일봉"):
    """
    단일 차트를 데이터 파일들과 함께 분석하는 편의 함수
    
    Args:
        image_path (str): 차트 이미지 파일 경로
        json_data_path (str): JSON 데이터 파일 경로
        csv_data_path (str): CSV 데이터 파일 경로
        text_summary_path (str): 텍스트 요약 파일 경로
        chart_type (str): 차트 유형 (일봉/주봉/월봉)
    """
    print("🤖 AI 제미나이 차트 분석 프로그램 (단일 파일 분석)")
    print("="*60)
    
    # 설정 파일에서 API 키 로드
    from config import config
    
    api_key = config.get_api_key()
    if not api_key:
        print("❌ API 키가 설정되지 않았습니다.")
        return None
    
    # AI 분석기 초기화
    analyzer = AIChartAnalyzer(api_key)
    
    # 파일 존재 확인
    if not os.path.exists(image_path):
        print(f"❌ 차트 이미지 파일을 찾을 수 없습니다: {image_path}")
        return None
    
    print(f"🔍 분석 시작: {os.path.basename(image_path)}")
    print(f"📁 파일: {image_path}")
    print(f"📊 차트 유형: {chart_type}")
    
    # AI 분석 실행
    result = analyzer.analyze_chart_with_data_files(
        image_path=image_path,
        json_data_path=json_data_path,
        csv_data_path=csv_data_path,
        text_summary_path=text_summary_path,
        stock_name="",
        chart_type=chart_type
    )
    
    if result:
        # 결과 저장
        output_dir = "ai_analysis_results"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 종목정보 추출
        stock_info = result.get("종목정보", {})
        stock_name = stock_info.get("종목명", "unknown")
        stock_code = stock_info.get("종목번호", "000000")
        
        # JSON 파일 저장
        json_filename = f"analysis_{chart_type}_{stock_name}_{stock_code}_{timestamp}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Word 문서 저장
        doc_filename = f"analysis_{chart_type}_{stock_name}_{stock_code}_{timestamp}.docx"
        doc_path = os.path.join(output_dir, doc_filename)
        
        # JSON 파일 저장
        json_success = analyzer.save_analysis_result(result, json_path)
        
        # Word 문서 생성
        doc_success = analyzer.create_word_document(result, image_path, doc_path, chart_type)
        
        if json_success and doc_success:
            print("\n✅ AI 차트 분석이 완료되었습니다!")
            print(f"📄 JSON 결과 파일: {json_path}")
            print(f"📄 Word 문서 파일: {doc_path}")
            return result
        else:
            print("❌ 결과 저장에 실패했습니다.")
            return None
    else:
        print("❌ AI 분석에 실패했습니다.")
        return None

if __name__ == "__main__":
    main() 