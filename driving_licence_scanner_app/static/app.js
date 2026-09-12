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
    
    const resultFileName = document.getElementById('resultFileName');
    const validityBadge = document.getElementById('validityBadge');
    const portraitImg = document.getElementById('portraitImg');
    const dispName = document.getElementById('dispName');
    const dispRelative = document.getElementById('dispRelative');
    const relativeRow = document.getElementById('relativeRow');
    const dispDlNo = document.getElementById('dispDlNo');
    const dispBloodGroup = document.getElementById('dispBloodGroup');
    const dispGender = document.getElementById('dispGender');
    const dispDob = document.getElementById('dispDob');
    const dispDoi = document.getElementById('dispDoi');
    const dispDoe = document.getElementById('dispDoe');
    const dispAuthority = document.getElementById('dispAuthority');
    const vehicleClassesList = document.getElementById('vehicleClassesList');
    
    const jsonOutput = document.getElementById('jsonOutput');
    const toggleJson = document.getElementById('toggleJson');
    const copyJsonBtn = document.getElementById('copyJsonBtn');
    
    const historyList = document.getElementById('historyList');
    const scannedCount = document.getElementById('scannedCount');
    const exportJsonBtn = document.getElementById('exportJsonBtn');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');

    let cameraStream = null;
    let currentData = null;

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

    // File Upload / Drag & Drop
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleFiles(files);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files && fileInput.files.length > 0) {
            handleFiles(fileInput.files);
        }
    });

    async function handleFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        showLoader(`Processing ${files.length} Driving Licence file(s)...`);

        try {
            const resp = await fetch('/api/scan', {
                method: 'POST',
                body: formData
            });

            if (!resp.ok) throw new Error(`HTTP Error: ${resp.status}`);
            const data = await resp.json();

            if (data.extracted && data.extracted.length > 0) {
                renderResult(data.extracted[0]);
                loadHistory();
            }
        } catch (err) {
            alert(`Extraction Error: ${err.message}`);
        } finally {
            hideLoader();
            fileInput.value = '';
        }
    }

    // Camera Handlers
    startCameraBtn.addEventListener('click', async () => {
        if (cameraStream) {
            stopCamera();
            startCameraBtn.innerHTML = '<i class="fa-solid fa-power-off"></i> Start Camera';
            captureBtn.disabled = true;
            return;
        }

        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1920 }, height: { ideal: 1080 }, facingMode: "environment" }
            });
            videoFeed.srcObject = cameraStream;
            startCameraBtn.innerHTML = '<i class="fa-solid fa-video-slash"></i> Stop Camera';
            captureBtn.disabled = false;
        } catch (err) {
            alert(`Camera Access Failed: ${err.message}`);
        }
    });

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
            videoFeed.srcObject = null;
            if (startCameraBtn) startCameraBtn.innerHTML = '<i class="fa-solid fa-power-off"></i> Start Camera';
            if (captureBtn) captureBtn.disabled = true;
        }
    }

    captureBtn.addEventListener('click', async () => {
        if (!cameraStream) return;

        cameraCanvas.width = videoFeed.videoWidth || 1280;
        cameraCanvas.height = videoFeed.videoHeight || 720;
        const ctx = cameraCanvas.getContext('2d');
        ctx.drawImage(videoFeed, 0, 0, cameraCanvas.width, cameraCanvas.height);

        const base64Data = cameraCanvas.toDataURL('image/jpeg', 0.95);
        const fileName = `dl_capture_${Date.now()}.jpg`;

        showLoader("Running OCR & Licence Extraction...");

        try {
            const formData = new FormData();
            formData.append('image_base64', base64Data);
            formData.append('file_name', fileName);

            const resp = await fetch('/api/scan-camera', {
                method: 'POST',
                body: formData
            });

            if (!resp.ok) throw new Error(`HTTP Error: ${resp.status}`);
            const data = await resp.json();

            if (data.extracted) {
                renderResult(data.extracted);
                loadHistory();
            }
        } catch (err) {
            alert(`Camera Scan Error: ${err.message}`);
        } finally {
            hideLoader();
        }
    });

    // Render Data to Dashboard
    function renderResult(data) {
        currentData = data;
        resultFileName.textContent = data.file_name || "Driving Licence Scan";

        // Validity Badge
        const vStatus = (data.validity_status || "ACTIVE").toUpperCase();
        if (vStatus === "ACTIVE" || vStatus === "VALID") {
            validityBadge.className = "badge badge-success";
            validityBadge.innerHTML = '<i class="fa-solid fa-shield-check"></i> VALID';
        } else if (vStatus === "EXPIRED") {
            validityBadge.className = "badge badge-danger";
            validityBadge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> EXPIRED';
        } else {
            validityBadge.className = "badge badge-warning";
            validityBadge.innerHTML = '<i class="fa-solid fa-clock-rotate-left"></i> PENDING RENEWAL';
        }

        // Portrait
        if (data.image_of_person_url) {
            portraitImg.src = data.image_of_person_url;
        } else if (data.image_of_person) {
            portraitImg.src = `/${data.image_of_person}`;
        } else {
            portraitImg.src = "https://via.placeholder.com/150x180/1a2624/00f2fe?text=Driver+Photo";
        }

        // Primary Fields
        dispName.textContent = data.name || "---";
        if (data.father_or_husband_name) {
            relativeRow.style.display = "block";
            dispRelative.textContent = data.father_or_husband_name;
        } else {
            relativeRow.style.display = "none";
        }

        dispDlNo.textContent = data.dl_number || "---";
        dispBloodGroup.textContent = data.blood_group || "Unknown";
        dispGender.textContent = data.gender || "MALE";

        dispDob.textContent = data.date_of_birth || "---";
        dispDoi.textContent = data.date_of_issue || "---";
        dispDoe.textContent = data.date_of_expiry || "---";
        dispAuthority.textContent = data.issuing_authority || "---";

        // Vehicle Classes
        vehicleClassesList.innerHTML = '';
        const classes = data.vehicle_classes && data.vehicle_classes.length > 0 ? data.vehicle_classes : ["LMV"];
        classes.forEach(cls => {
            const span = document.createElement('span');
            span.className = 'cov-badge';
            span.textContent = cls;
            vehicleClassesList.appendChild(span);
        });

        // JSON accordion
        jsonOutput.textContent = JSON.stringify(data, null, 2);
    }

    // Toggle JSON
    toggleJson.addEventListener('click', () => {
        jsonOutput.classList.toggle('show');
        const icon = toggleJson.querySelector('.fa-chevron-down, .fa-chevron-up');
        if (icon) {
            icon.classList.toggle('fa-chevron-down');
            icon.classList.toggle('fa-chevron-up');
        }
    });

    // Copy JSON
    copyJsonBtn.addEventListener('click', () => {
        if (!currentData) return;
        navigator.clipboard.writeText(JSON.stringify(currentData, null, 2))
            .then(() => {
                const origHtml = copyJsonBtn.innerHTML;
                copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                setTimeout(() => copyJsonBtn.innerHTML = origHtml, 1500);
            });
    });

    // History API
    async function loadHistory() {
        try {
            const resp = await fetch('/api/history');
            if (!resp.ok) return;
            const data = await resp.json();
            const records = data.records || [];

            scannedCount.textContent = records.length;
            historyList.innerHTML = '';

            if (records.length === 0) {
                historyList.innerHTML = '<div class="empty-history">No driving licences scanned yet. Upload or capture an image to begin.</div>';
                return;
            }

            records.forEach((rec, idx) => {
                const item = document.createElement('div');
                item.className = 'history-item';
                item.innerHTML = `
                    <div class="history-info">
                        <span class="hist-name">${rec.name || 'Unassigned'}</span>
                        <span class="hist-meta">${rec.dl_number || 'Pending'} • ${rec.date_of_birth || 'DOB N/A'}</span>
                    </div>
                    <span class="badge ${rec.validity_status === 'EXPIRED' ? 'badge-danger' : 'badge-success'}">${rec.validity_status || 'VALID'}</span>
                `;
                item.addEventListener('click', () => renderResult(rec));
                historyList.appendChild(item);
            });

            if (!currentData && records.length > 0) {
                renderResult(records[0]);
            }
        } catch (err) {
            console.error("Failed to load history", err);
        }
    }

    // Export JSON
    exportJsonBtn.addEventListener('click', () => {
        window.location.href = '/api/export-json';
    });

    // Clear History
    clearHistoryBtn.addEventListener('click', async () => {
        if (confirm("Are you sure you want to clear all scanned driving licence history?")) {
            await fetch('/api/clear', { method: 'DELETE' });
            currentData = null;
            loadHistory();
        }
    });

    function showLoader(text) {
        loaderText.textContent = text || 'Processing...';
        loader.hidden = false;
    }

    function hideLoader() {
        loader.hidden = true;
    }

    // Initial load
    loadHistory();
});
