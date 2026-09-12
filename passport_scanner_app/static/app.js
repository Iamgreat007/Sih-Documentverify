document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const tabUpload = document.getElementById('tabUpload');
    const tabCamera = document.getElementById('tabCamera');
    const uploadPanel = document.getElementById('uploadPanel');
    const cameraPanel = document.getElementById('cameraPanel');
    
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    const videoFeed = document.getElementById('videoFeed');
    const cameraCanvas = document.getElementById('cameraCanvas');
    const startCameraBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('captureBtn');
    
    const loader = document.getElementById('loader');
    const loaderText = document.getElementById('loaderText');
    
    const historyList = document.getElementById('historyList');
    const scannedCount = document.getElementById('scannedCount');
    
    const resultFileName = document.getElementById('resultFileName');
    const portraitImg = document.getElementById('portraitImg');
    const dispName = document.getElementById('dispName');
    const dispPassportNo = document.getElementById('dispPassportNo');
    const dispGender = document.getElementById('dispGender');
    const dispNationality = document.getElementById('dispNationality');
    const dispDob = document.getElementById('dispDob');
    const dispDoi = document.getElementById('dispDoi');
    const dispDoe = document.getElementById('dispDoe');
    const dispPob = document.getElementById('dispPob');
    const dispPoi = document.getElementById('dispPoi');
    const dispAddress = document.getElementById('dispAddress');
    const mrzLine1 = document.getElementById('mrzLine1');
    const mrzLine2 = document.getElementById('mrzLine2');
    const mrzBadge = document.getElementById('mrzBadge');
    const jsonOutput = document.getElementById('jsonOutput');
    
    const exportJsonBtn = document.getElementById('exportJsonBtn');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const copyJsonBtn = document.getElementById('copyJsonBtn');
    const toggleJson = document.getElementById('toggleJson');

    let stream = null;
    let currentRecord = null;
    let allRecords = [];

    // Tab Switching
    tabUpload.addEventListener('click', () => {
        tabUpload.classList.add('active');
        tabCamera.classList.remove('active');
        uploadPanel.classList.add('active');
        cameraPanel.classList.remove('active');
        stopCamera();
    });

    tabCamera.addEventListener('click', () => {
        tabCamera.classList.add('active');
        tabUpload.classList.remove('active');
        cameraPanel.classList.add('active');
        uploadPanel.classList.remove('active');
    });

    // File Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleFilesUpload(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFilesUpload(fileInput.files);
        }
    });

    // Camera Stream Management
    startCameraBtn.addEventListener('click', async () => {
        if (stream) {
            stopCamera();
            startCameraBtn.innerHTML = '<i class="fa-solid fa-power-off"></i> Start Camera';
            captureBtn.disabled = true;
            return;
        }

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1920 }, height: { ideal: 1080 } }
            });
            videoFeed.srcObject = stream;
            startCameraBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Camera';
            captureBtn.disabled = false;
        } catch (err) {
            alert('Unable to access camera: ' + err.message);
        }
    });

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            videoFeed.srcObject = null;
            startCameraBtn.innerHTML = '<i class="fa-solid fa-power-off"></i> Start Camera';
            captureBtn.disabled = true;
        }
    }

    // Capture Snapshot & Scan
    captureBtn.addEventListener('click', async () => {
        if (!stream) return;

        const context = cameraCanvas.getContext('2d');
        cameraCanvas.width = videoFeed.videoWidth || 1280;
        cameraCanvas.height = videoFeed.videoHeight || 720;
        context.drawImage(videoFeed, 0, 0, cameraCanvas.width, cameraCanvas.height);

        const base64Data = cameraCanvas.toDataURL('image/jpeg', 0.95);
        showLoader('Processing Camera Snapshot with OCR & MRZ...');

        try {
            const formData = new FormData();
            formData.append('image_base64', base64Data);
            formData.append('file_name', `camera_${Date.now()}.jpg`);

            const res = await fetch('/api/scan-camera', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (data.status === 'success') {
                renderResult(data.extracted);
                loadHistory();
            } else {
                alert('Scan error: ' + (data.error || 'Failed to scan'));
            }
        } catch (err) {
            alert('Request failed: ' + err.message);
        } finally {
            hideLoader();
        }
    });

    // Upload Files
    async function handleFilesUpload(files) {
        showLoader(`Processing ${files.length} uploaded passport photo(s)...`);
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const res = await fetch('/api/scan', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (data.status === 'success' && data.extracted.length > 0) {
                renderResult(data.extracted[0]);
                loadHistory();
            } else {
                alert('Extraction failed or no valid records returned.');
            }
        } catch (err) {
            alert('Upload error: ' + err.message);
        } finally {
            hideLoader();
            fileInput.value = '';
        }
    }

    // Render Scanned Result to UI
    function renderResult(record) {
        currentRecord = record;
        resultFileName.textContent = record.file_name || 'Passport Scan';
        
        dispName.textContent = record.name || '---';
        dispPassportNo.textContent = record.passport_no || '---';
        dispGender.textContent = record.gender || '---';
        dispNationality.textContent = 'IND';
        dispDob.textContent = record.date_of_birth || '---';
        dispDoi.textContent = record.date_of_issue || '---';
        dispDoe.textContent = record.date_of_expiry || '---';
        dispPob.textContent = record.place_of_birth || '---';
        dispPoi.textContent = record.place_of_issue || '---';
        dispAddress.textContent = record.address || record.place_of_birth || '---';

        // Portrait Image
        if (record.image_of_person_url) {
            portraitImg.src = record.image_of_person_url;
        } else if (record.image_of_person) {
            portraitImg.src = `/${record.image_of_person}`;
        } else {
            portraitImg.src = 'https://via.placeholder.com/150x180/1a2236/4facfe?text=No+Photo';
        }

        // MRZ Code
        if (record.mrz_code && record.mrz_code.length > 0) {
            mrzLine1.textContent = record.mrz_code[0] || '---';
            mrzLine2.textContent = record.mrz_code[1] || '';
            mrzBadge.style.display = 'inline-block';
        } else {
            mrzLine1.textContent = 'MRZ not detected on visual zone';
            mrzLine2.textContent = '';
            mrzBadge.style.display = 'none';
        }

        // Clean JSON for viewer
        const exportObj = {
            file_name: record.file_name,
            name: record.name,
            passport_no: record.passport_no,
            date_of_birth: record.date_of_birth,
            gender: record.gender,
            date_of_issue: record.date_of_issue,
            date_of_expiry: record.date_of_expiry,
            place_of_birth: record.place_of_birth,
            place_of_issue: record.place_of_issue,
            address: record.address,
            mrz_code: record.mrz_code,
            image_of_person: record.image_of_person
        };
        jsonOutput.textContent = JSON.stringify(exportObj, null, 2);
    }

    // Load History
    async function loadHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            allRecords = data.records || [];
            scannedCount.textContent = allRecords.length;

            if (allRecords.length === 0) {
                historyList.innerHTML = '<div class="empty-history">No passports scanned yet. Upload or capture an image to begin.</div>';
                return;
            }

            historyList.innerHTML = '';
            allRecords.forEach((rec, idx) => {
                const item = document.createElement('div');
                item.className = `history-item ${idx === 0 ? 'active' : ''}`;
                item.innerHTML = `
                    <div class="history-meta">
                        <span class="history-title">${rec.name || rec.passport_no || rec.file_name}</span>
                        <span class="history-sub">${rec.file_name} • ${rec.date_of_birth || 'DOB N/A'}</span>
                    </div>
                    <i class="fa-solid fa-chevron-right text-muted"></i>
                `;
                item.addEventListener('click', () => {
                    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    renderResult(rec);
                });
                historyList.appendChild(item);
            });

            if (!currentRecord && allRecords.length > 0) {
                renderResult(allRecords[0]);
            }
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    }

    // UI Utilities
    function showLoader(text) {
        loaderText.textContent = text;
        loader.hidden = false;
    }

    function hideLoader() {
        loader.hidden = true;
    }

    // Copy JSON
    copyJsonBtn.addEventListener('click', () => {
        if (!jsonOutput.textContent) return;
        navigator.clipboard.writeText(jsonOutput.textContent);
        copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
        setTimeout(() => {
            copyJsonBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy JSON';
        }, 2000);
    });

    // Export All JSON
    exportJsonBtn.addEventListener('click', () => {
        window.location.href = '/api/export-json';
    });

    // Clear History
    clearHistoryBtn.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to clear all scan history?')) return;
        try {
            await fetch('/api/clear', { method: 'DELETE' });
            currentRecord = null;
            loadHistory();
            dispName.textContent = '---';
            dispPassportNo.textContent = '---';
            dispGender.textContent = '---';
            dispDob.textContent = '---';
            dispDoi.textContent = '---';
            dispDoe.textContent = '---';
            dispPob.textContent = '---';
            dispAddress.textContent = '---';
            mrzLine1.textContent = '---';
            mrzLine2.textContent = '';
            portraitImg.src = 'https://via.placeholder.com/150x180/1a2236/4facfe?text=Portrait';
            jsonOutput.textContent = '{}';
        } catch (err) {
            alert('Failed to clear history: ' + err.message);
        }
    });

    // Toggle JSON pre
    toggleJson.addEventListener('click', () => {
        jsonOutput.style.display = jsonOutput.style.display === 'none' ? 'block' : 'none';
    });

    // Initial Load
    loadHistory();
});
