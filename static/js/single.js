// 단일 차트 분석 페이지 자바스크립트

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('singleAnalysisForm');
    const stockCodeInput = document.getElementById('stock_code');
    const submitBtn = document.getElementById('submitBtn');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');

    // 종목코드 입력 검증
    stockCodeInput.addEventListener('input', function(e) {
        const value = e.target.value;
        // 숫자만 입력 가능
        if (value && !/^\d{0,6}$/.test(value)) {
            e.target.value = value.replace(/\D/g, '');
        }
        
        // 6자리 입력 시 자동으로 포커스 해제
        if (value.length === 6) {
            e.target.blur();
        }
    });

    // 폼 제출 처리
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // 종목코드 검증
        const stockCode = stockCodeInput.value.trim();
        if (!stockCode || stockCode.length !== 6) {
            showError('6자리 종목코드를 입력해주세요.');
            return;
        }
        
        // 결과 및 에러 숨기기
        hideResult();
        hideError();
        
        // 로딩 상태 시작
        setLoading(true);
        
        try {
            const chartType = document.getElementById('chart_type').value;
            
            // API 호출
            const response = await fetch('/api/analyze/single/chart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    stock_code: stockCode,
                    chart_type: chartType
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || '분석 중 오류가 발생했습니다.');
            }
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // 결과 표시
            showResult(data);
            
        } catch (error) {
            console.error('분석 오류:', error);
            showError(error.message);
        } finally {
            // 로딩 상태 종료
            setLoading(false);
        }
    });

    // 결과 표시 함수
    function showResult(data) {
        // 메타데이터 설정
        document.getElementById('resultStock').textContent = data.stock_name || 'N/A';
        document.getElementById('resultChartType').textContent = data.chart_type || 'N/A';
        document.getElementById('resultTime').textContent = new Date().toLocaleString('ko-KR');
        
        // 분석 점수 설정
        const score = data.analysis_score || 0;
        document.getElementById('analysisScore').textContent = score;
        
        // 점수에 따른 색상 변경
        const scoreCircle = document.querySelector('.score-circle');
        if (score >= 80) {
            scoreCircle.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
        } else if (score >= 60) {
            scoreCircle.style.background = 'linear-gradient(135deg, #ffc107, #fd7e14)';
        } else {
            scoreCircle.style.background = 'linear-gradient(135deg, #dc3545, #e83e8c)';
        }
        
        // 점수 설명 설정
        let scoreDescription = '';
        if (score >= 80) {
            scoreDescription = '매우 좋은 투자 기회입니다.';
        } else if (score >= 60) {
            scoreDescription = '적당한 투자 기회입니다.';
        } else {
            scoreDescription = '투자에 주의가 필요합니다.';
        }
        document.getElementById('scoreDescription').textContent = scoreDescription;
        
        // 분석 요약 설정
        document.getElementById('analysisSummary').innerHTML = formatText(data.summary || '분석 요약이 없습니다.');
        
        // 상세 분석 설정
        document.getElementById('analysisDetails').innerHTML = formatText(data.detailed_analysis || '상세 분석이 없습니다.');
        
        // 결과 표시
        resultDiv.style.display = 'block';
        
        // 결과로 스크롤
        resultDiv.scrollIntoView({ behavior: 'smooth' });
    }

    // 에러 표시 함수
    function showError(message) {
        document.getElementById('errorMessage').textContent = message;
        errorDiv.style.display = 'flex';
        errorDiv.scrollIntoView({ behavior: 'smooth' });
    }

    // 결과 숨기기 함수
    function hideResult() {
        resultDiv.style.display = 'none';
    }

    // 에러 숨기기 함수
    function hideError() {
        errorDiv.style.display = 'none';
    }

    // 로딩 상태 설정 함수
    function setLoading(loading) {
        if (loading) {
            submitBtn.classList.add('loading');
            submitBtn.disabled = true;
        } else {
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }
    }

    // 텍스트 포맷팅 함수
    function formatText(text) {
        if (!text) return '';
        
        // 줄바꿈을 <br>로 변환
        text = text.replace(/\n/g, '<br>');
        
        // 굵은 텍스트 처리
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // 기울임 텍스트 처리
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        return text;
    }

    // 폼 초기화 시 결과 숨기기
    form.addEventListener('reset', function() {
        hideResult();
        hideError();
    });
}); 