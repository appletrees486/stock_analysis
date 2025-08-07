// 대량 차트 분석 페이지 자바스크립트

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('batchAnalysisForm');
    const fileInput = document.getElementById('stock_list');
    const filePreview = document.getElementById('filePreview');
    const submitBtn = document.getElementById('submitBtn');
    const batchStatusDiv = document.getElementById('batchStatus');
    const errorDiv = document.getElementById('error');
    
    let batchId = null;
    let statusInterval = null;

    // 파일 선택 시 미리보기
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // 파일 크기 확인 (1MB)
            if (file.size > 1024 * 1024) {
                showError('파일 크기가 1MB를 초과합니다.');
                fileInput.value = '';
                return;
            }

            // 파일 타입 확인
            if (file.type !== 'text/plain' && !file.name.endsWith('.txt')) {
                showError('텍스트 파일(.txt)만 업로드 가능합니다.');
                fileInput.value = '';
                return;
            }

            // 파일 내용 미리보기
            const reader = new FileReader();
            reader.onload = function(e) {
                const content = e.target.result;
                const lines = content.split('\n').filter(line => line.trim());
                
                filePreview.innerHTML = `
                    <div class="file-selected">
                        <p style="color: #28a745;">✓ ${file.name}</p>
                        <small>파일 크기: ${(file.size / 1024).toFixed(2)} KB</small>
                        <div style="margin-top: 10px; text-align: left;">
                            <strong>포함된 종목코드:</strong>
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 5px; max-height: 100px; overflow-y: auto;">
                                ${lines.slice(0, 10).join('<br>')}
                                ${lines.length > 10 ? `<br><small>... 외 ${lines.length - 10}개</small>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            };
            reader.readAsText(file);
        }
    });

    // 폼 제출 처리
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // 에러 숨기기
        hideError();
        
        // 로딩 상태 시작
        setLoading(true);
        
        try {
            const formData = new FormData(form);
            
            // API 호출
            const response = await fetch('/api/analyze/batch', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || '대량 분석 시작 중 오류가 발생했습니다.');
            }
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // 배치 ID 저장
            batchId = data.batch_id;
            
            // 배치 상태 표시 시작
            showBatchStatus();
            startStatusCheck();
            
        } catch (error) {
            console.error('대량 분석 오류:', error);
            showError(error.message);
        } finally {
            // 로딩 상태 종료
            setLoading(false);
        }
    });

    // 배치 상태 표시 함수
    function showBatchStatus() {
        batchStatusDiv.style.display = 'block';
        batchStatusDiv.scrollIntoView({ behavior: 'smooth' });
    }

    // 상태 확인 시작 함수
    function startStatusCheck() {
        if (statusInterval) {
            clearInterval(statusInterval);
        }
        statusInterval = setInterval(checkBatchStatus, 2000);
    }

    // 배치 상태 확인 함수
    async function checkBatchStatus() {
        if (!batchId) return;
        
        try {
            const response = await fetch(`/api/batch/status/${batchId}`);
            const status = await response.json();
            
            if (status.error) {
                clearInterval(statusInterval);
                showError(`상태 확인 오류: ${status.error}`);
                return;
            }
            
            // 상태 정보 업데이트
            updateStatusDisplay(status);
            
            // 완료 시 결과 확인
            if (status.status === 'completed') {
                clearInterval(statusInterval);
                showBatchResults();
            } else if (status.status === 'failed') {
                clearInterval(statusInterval);
                showError(`분석 실패: ${status.error || '알 수 없는 오류'}`);
            }
            
        } catch (error) {
            console.error('상태 확인 오류:', error);
        }
    }

    // 상태 표시 업데이트 함수
    function updateStatusDisplay(status) {
        // 배치 정보
        document.getElementById('batchId').textContent = `배치 ID: ${batchId}`;
        document.getElementById('batchChartType').textContent = `차트 유형: ${status.chart_type || 'N/A'}`;
        
        // 진행률
        const progress = status.progress || 0;
        document.getElementById('progressFill').style.width = `${progress}%`;
        document.getElementById('progressPercent').textContent = `${progress.toFixed(1)}%`;
        document.getElementById('progressCount').textContent = `(${status.completed || 0}/${status.total || 0})`;
        
        // 상태 세부사항
        document.getElementById('startTime').textContent = formatDateTime(status.start_time);
        document.getElementById('completedCount').textContent = status.completed || 0;
        document.getElementById('failedCount').textContent = status.failed || 0;
        document.getElementById('batchStatusText').textContent = getStatusText(status.status);
    }

    // 배치 결과 표시 함수
    async function showBatchResults() {
        try {
            const response = await fetch(`/api/batch/results/${batchId}`);
            const data = await response.json();
            
            if (data.error) {
                showError(`결과 조회 오류: ${data.error}`);
            } else {
                // 결과 섹션 표시
                document.getElementById('batchResults').style.display = 'block';
                
                // 다운로드 버튼 이벤트
                document.getElementById('downloadBtn').onclick = function() {
                    window.location.href = `/api/download/${batchId}`;
                };
                
                // 결과 보기 버튼 이벤트
                document.getElementById('viewResultsBtn').onclick = function() {
                    showResultsSummary(data);
                };
            }
        } catch (error) {
            console.error('결과 조회 오류:', error);
            showError('결과를 불러오는 중 오류가 발생했습니다.');
        }
    }

    // 결과 요약 표시 함수
    function showResultsSummary(data) {
        const results = data.results || [];
        const status = data.status || {};
        
        // 간단한 결과 요약을 알림으로 표시
        const successCount = results.filter(r => !r.error).length;
        const errorCount = results.filter(r => r.error).length;
        
        alert(`분석 완료!\n\n` +
              `총 종목 수: ${status.total || 0}\n` +
              `성공: ${successCount}\n` +
              `실패: ${errorCount}\n\n` +
              `결과 파일을 다운로드하여 상세 내용을 확인하세요.`);
    }

    // 상태 텍스트 변환 함수
    function getStatusText(status) {
        const statusMap = {
            'running': '분석 중',
            'completed': '완료',
            'failed': '실패',
            'waiting': '대기 중'
        };
        return statusMap[status] || status;
    }

    // 날짜 시간 포맷팅 함수
    function formatDateTime(dateString) {
        if (!dateString) return '-';
        try {
            const date = new Date(dateString);
            return date.toLocaleString('ko-KR');
        } catch (error) {
            return dateString;
        }
    }

    // 에러 표시 함수
    function showError(message) {
        document.getElementById('errorMessage').textContent = message;
        errorDiv.style.display = 'flex';
        errorDiv.scrollIntoView({ behavior: 'smooth' });
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

    // 폼 초기화 시 미리보기도 초기화
    form.addEventListener('reset', function() {
        filePreview.innerHTML = `
            <div class="upload-placeholder">
                <span class="upload-icon">📁</span>
                <p>종목 리스트 파일을 선택하세요</p>
                <small>텍스트 파일만 가능 (최대 1MB)</small>
            </div>
        `;
        hideError();
        
        // 배치 상태 숨기기
        batchStatusDiv.style.display = 'none';
        
        // 상태 확인 중단
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
        
        batchId = null;
    });

    // 페이지 이탈 시 상태 확인 중단
    window.addEventListener('beforeunload', function() {
        if (statusInterval) {
            clearInterval(statusInterval);
        }
    });
}); 