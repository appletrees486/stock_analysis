// 다중 대량 차트 분석 페이지 자바스크립트

document.addEventListener('DOMContentLoaded', function() {
    const dragDropZone = document.getElementById('dragDropZone');
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');
    const fileItems = document.getElementById('fileItems');
    const formActions = document.getElementById('formActions');
    const startAnalysisBtn = document.getElementById('startAnalysisBtn');
    const clearFilesBtn = document.getElementById('clearFilesBtn');
    const batchQueue = document.getElementById('batchQueue');
    const queueItems = document.getElementById('queueItems');
    const errorDiv = document.getElementById('error');
    
    // 메일 발송 옵션 요소들
    const emailOptions = document.getElementById('emailOptions');
    const emailEnabled = document.getElementById('emailEnabled');
    const emailInputGroup = document.getElementById('emailInputGroup');
    const emailAddress = document.getElementById('emailAddress');
    
    let selectedFiles = [];
    let analysisQueue = [];
    let statusIntervals = {};

    // 드래그 앤 드롭 이벤트
    dragDropZone.addEventListener('click', () => fileInput.click());
    
    dragDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dragDropZone.classList.add('dragover');
    });
    
    dragDropZone.addEventListener('dragleave', () => {
        dragDropZone.classList.remove('dragover');
    });
    
    dragDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dragDropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // 파일 처리 함수
    function handleFiles(files) {
        const newFiles = Array.from(files).filter(file => {
            // 파일 타입 및 크기 검증
            if (file.type !== 'text/plain' && !file.name.endsWith('.txt')) {
                showError(`${file.name}: 텍스트 파일(.txt)만 업로드 가능합니다.`);
                return false;
            }
            
            if (file.size > 1024 * 1024) {
                showError(`${file.name}: 파일 크기가 1MB를 초과합니다.`);
                return false;
            }
            
            return true;
        });
        
        // 중복 파일 제거
        const existingNames = selectedFiles.map(f => f.name);
        const uniqueFiles = newFiles.filter(file => !existingNames.includes(file.name));
        
        if (uniqueFiles.length !== newFiles.length) {
            showError('일부 파일이 이미 선택되어 있습니다.');
        }
        
        selectedFiles.push(...uniqueFiles);
        updateFileList();
        updateFormVisibility();
    }

    // 파일 목록 업데이트
    function updateFileList() {
        if (selectedFiles.length === 0) {
            fileList.style.display = 'none';
            return;
        }
        
        fileList.style.display = 'block';
        fileItems.innerHTML = '';
        
        selectedFiles.forEach((file, index) => {
            const fileItem = createFileItem(file, index);
            fileItems.appendChild(fileItem);
        });
    }

    // 파일 아이템 생성
    function createFileItem(file, index) {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-file-index', index);
        
        // 파일 정보 분석
        const fileInfo = analyzeFileInfo(file);
        
        div.innerHTML = `
            <div class="file-icon">📄</div>
            <div class="file-info">
                <div class="file-name">${file.name}</div>
                <div class="file-details">
                    크기: ${(file.size / 1024).toFixed(2)} KB | 
                    차트: ${fileInfo.chartType} | 
                    거래타입: ${fileInfo.tradingType} | 
                    종목수: ${fileInfo.stockCount}개
                </div>
            </div>
            <div class="file-actions">
                <button class="remove-btn" onclick="removeFile(${index})">제거</button>
            </div>
        `;
        
        return div;
    }

    // 파일 정보 분석
    function analyzeFileInfo(file) {
        const fileName = file.name.toLowerCase();
        
        // 차트 타입 감지
        let chartType = '일봉';
        if (fileName.includes('주간') || fileName.includes('weekly') || fileName.includes('week')) {
            chartType = '주봉';
        } else if (fileName.includes('월간') || fileName.includes('monthly') || fileName.includes('month')) {
            chartType = '월봉';
        }
        
        // 거래타입 감지
        let tradingType = '거래대금';
        if (fileName.includes('거래율') || fileName.includes('turnover')) {
            tradingType = '거래율';
        }
        
        // 종목 수 계산 (파일 내용 미리보기)
        let stockCount = 0;
        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            const lines = content.split('\n').filter(line => line.trim());
            stockCount = lines.length;
            
            // 파일 아이템 업데이트
            const fileIndex = selectedFiles.findIndex(f => f === file);
            const fileItem = document.querySelector(`[data-file-index="${fileIndex}"]`);
            if (fileItem) {
                const details = fileItem.querySelector('.file-details');
                details.textContent = `크기: ${(file.size / 1024).toFixed(2)} KB | 차트: ${chartType} | 거래타입: ${tradingType} | 종목수: ${stockCount}개`;
            }
        };
        reader.readAsText(file);
        
        return { chartType, tradingType, stockCount };
    }

    // 파일 제거
    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        updateFileList();
        updateFormVisibility();
    };

    // 폼 가시성 업데이트
    function updateFormVisibility() {
        if (selectedFiles.length > 0) {
            formActions.style.display = 'block';
            emailOptions.style.display = 'block';
        } else {
            formActions.style.display = 'none';
            emailOptions.style.display = 'none';
        }
    }

    // 분석 시작
    startAnalysisBtn.addEventListener('click', async function() {
        if (selectedFiles.length === 0) {
            showError('분석할 파일을 선택해주세요.');
            return;
        }
        
        hideError();
        setLoading(true);
        
        try {
            // 각 파일에 대해 분석 큐에 추가
            for (const file of selectedFiles) {
                const fileInfo = analyzeFileInfo(file);
                const batchId = await startSingleBatchAnalysis(file, fileInfo);
                
                if (batchId) {
                    analysisQueue.push({
                        batchId,
                        fileName: file.name,
                        chartType: fileInfo.chartType,
                        tradingType: fileInfo.tradingType,
                        status: 'waiting',
                        progress: 0,
                        completed: 0,
                        total: 0,
                        startTime: null,
                        error: null
                    });
                }
            }
            
            // 큐 표시
            showBatchQueue();
            
            // 순차적 분석 시작
            startSequentialAnalysis();
            
        } catch (error) {
            console.error('분석 시작 오류:', error);
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    // 단일 배치 분석 시작
    async function startSingleBatchAnalysis(file, fileInfo) {
        try {
            const formData = new FormData();
            formData.append('stock_list', file);
            formData.append('chart_type', fileInfo.chartType);
            formData.append('trading_type', fileInfo.tradingType);
            
            // 메일 발송 옵션 추가
            if (emailEnabled.checked && emailAddress.value.trim()) {
                formData.append('email_enabled', 'true');
                formData.append('email_address', emailAddress.value.trim());
            }
            
            const response = await fetch('/api/analyze/batch', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || '배치 분석 시작 중 오류가 발생했습니다.');
            }
            
            return data.batch_id;
            
        } catch (error) {
            console.error(`파일 ${file.name} 분석 시작 오류:`, error);
            throw error;
        }
    }

    // 배치 큐 표시
    function showBatchQueue() {
        batchQueue.style.display = 'block';
        updateQueueDisplay();
    }

    // 큐 표시 업데이트
    function updateQueueDisplay() {
        if (analysisQueue.length === 0) {
            queueItems.innerHTML = '<div class="empty-state"><div class="icon">📊</div><p>분석 큐가 비어있습니다.</p></div>';
            return;
        }
        
        queueItems.innerHTML = '';
        
        analysisQueue.forEach((item, index) => {
            const queueItem = createQueueItem(item, index);
            queueItems.appendChild(queueItem);
        });
    }

    // 큐 아이템 생성
    function createQueueItem(item, index) {
        const div = document.createElement('div');
        div.className = 'queue-item';
        
        const statusClass = `status-${item.status}`;
        const progressPercent = item.total > 0 ? (item.completed / item.total * 100).toFixed(1) : 0;
        
        div.innerHTML = `
            <div class="queue-header">
                <div class="queue-info">
                    <div class="file-name">${item.fileName}</div>
                    <div class="file-details">${item.chartType} - ${item.tradingType}</div>
                </div>
                <div class="queue-actions">
                    <span class="queue-status ${statusClass}">${getStatusText(item.status)}</span>
                    ${item.status === 'completed' ? `
                        <button class="action-btn btn-view" onclick="viewResults('${item.batchId}')">결과보기</button>
                        <button class="action-btn btn-download" onclick="downloadResults('${item.batchId}')">다운로드</button>
                    ` : ''}
                    <button class="action-btn btn-remove" onclick="removeFromQueue(${index})">제거</button>
                </div>
            </div>
            <div class="queue-progress" style="display: ${item.status === 'running' ? 'block' : 'none'};">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progressPercent}%"></div>
                </div>
                <div class="progress-text">
                    <span>${progressPercent}%</span>
                    <span>(${item.completed}/${item.total})</span>
                </div>
            </div>
        `;
        
        return div;
    }

    // 순차적 분석 시작
    async function startSequentialAnalysis() {
        for (let i = 0; i < analysisQueue.length; i++) {
            const item = analysisQueue[i];
            
            if (item.status === 'waiting') {
                item.status = 'running';
                item.startTime = new Date().toISOString();
                
                // 상태 업데이트
                updateQueueDisplay();
                
                // 상태 모니터링 시작
                startStatusMonitoring(item.batchId, i);
                
                // 다음 분석까지 대기 (현재 분석이 완료될 때까지)
                await waitForCompletion(item.batchId);
            }
        }
    }

    // 상태 모니터링 시작
    function startStatusMonitoring(batchId, queueIndex) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/batch/status/${batchId}`);
                const status = await response.json();
                
                if (status.error) {
                    analysisQueue[queueIndex].status = 'failed';
                    analysisQueue[queueIndex].error = status.error;
                    clearInterval(interval);
                    updateQueueDisplay();
                    return;
                }
                
                // 상태 업데이트
                analysisQueue[queueIndex].progress = status.progress || 0;
                analysisQueue[queueIndex].completed = status.completed || 0;
                analysisQueue[queueIndex].total = status.total || 0;
                
                if (status.status === 'completed') {
                    analysisQueue[queueIndex].status = 'completed';
                    clearInterval(interval);
                } else if (status.status === 'failed') {
                    analysisQueue[queueIndex].status = 'failed';
                    analysisQueue[queueIndex].error = status.error || '알 수 없는 오류';
                    clearInterval(interval);
                }
                
                updateQueueDisplay();
                
            } catch (error) {
                console.error(`배치 ${batchId} 상태 확인 오류:`, error);
            }
        }, 2000);
        
        statusIntervals[batchId] = interval;
    }

    // 완료 대기
    function waitForCompletion(batchId) {
        return new Promise((resolve) => {
            const checkCompletion = () => {
                const item = analysisQueue.find(q => q.batchId === batchId);
                if (item && (item.status === 'completed' || item.status === 'failed')) {
                    resolve();
                } else {
                    setTimeout(checkCompletion, 1000);
                }
            };
            checkCompletion();
        });
    }

    // 상태 텍스트 변환
    function getStatusText(status) {
        const statusMap = {
            'waiting': '대기 중',
            'running': '분석 중',
            'completed': '완료',
            'failed': '실패'
        };
        return statusMap[status] || status;
    }

    // 결과 보기
    window.viewResults = function(batchId) {
        window.open(`/api/batch/results/${batchId}`, '_blank');
    };

    // 결과 다운로드
    window.downloadResults = function(batchId) {
        window.location.href = `/api/download/${batchId}`;
    };

    // 큐에서 제거
    window.removeFromQueue = function(index) {
        const item = analysisQueue[index];
        if (item && statusIntervals[item.batchId]) {
            clearInterval(statusIntervals[item.batchId]);
            delete statusIntervals[item.batchId];
        }
        
        analysisQueue.splice(index, 1);
        updateQueueDisplay();
    };

    // 파일 초기화
    clearFilesBtn.addEventListener('click', function() {
        selectedFiles = [];
        analysisQueue = [];
        
        // 모든 상태 모니터링 중단
        Object.values(statusIntervals).forEach(interval => clearInterval(interval));
        statusIntervals = {};
        
        updateFileList();
        updateFormVisibility();
        batchQueue.style.display = 'none';
        hideError();
    });

    // 메일 발송 옵션 이벤트 리스너
    emailEnabled.addEventListener('change', function() {
        if (this.checked) {
            emailInputGroup.style.display = 'block';
        } else {
            emailInputGroup.style.display = 'none';
            emailAddress.value = '';
        }
    });

    // 에러 표시
    function showError(message) {
        document.getElementById('errorMessage').textContent = message;
        errorDiv.style.display = 'flex';
        errorDiv.scrollIntoView({ behavior: 'smooth' });
    }

    // 에러 숨기기
    function hideError() {
        errorDiv.style.display = 'none';
    }

    // 로딩 상태 설정
    function setLoading(loading) {
        if (loading) {
            startAnalysisBtn.classList.add('loading');
            startAnalysisBtn.disabled = true;
        } else {
            startAnalysisBtn.classList.remove('loading');
            startAnalysisBtn.disabled = false;
        }
    }

    // 페이지 이탈 시 상태 모니터링 중단
    window.addEventListener('beforeunload', function() {
        Object.values(statusIntervals).forEach(interval => clearInterval(interval));
    });
});
