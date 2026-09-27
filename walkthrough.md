# SecureScan AI — Real OCR Engine & Backend Integration Walkthrough

The backend Python deep-learning OCR models (`DocumentPipeline` + `EasyOCR` + `QRDecoder` + `FieldExtractor`) are now fully connected, processing live document image uploads and returning structured identity extractions.

---

## 1. What Was Fixed & Connected

### 🧠 1. Live Deep-Learning OCR Pipeline Wired to Django
- **Previous state**: Backend returned hardcoded preset JSON and frontend was sending images as text URL strings with an aggressive 1.5s timeout that aborted before any OCR could run.
- **What was updated**:
  - **Real Binary Image Transmission**: Updated [`verificationService.ts`](file:///c:/Users/MSI-1/Desktop/SIH2/Sih-Documentverify/frontend/src/services/verificationService.ts) to convert captured base64 data URLs into true binary `Blob` files and stream them via multipart `FormData`.
  - **Adequate Inference Timeout**: Increased timeout to 30s so deep-learning models (`EasyOCR`, `PyTorch`, `DocumentPipeline`) have sufficient time to process high-resolution camera captures.
  - **Integrated `DocumentPipeline` in [`views.py`](file:///c:/Users/MSI-1/Desktop/SIH2/Sih-Documentverify/django_backend/api/views.py)**: When a document is scanned, the image is passed directly into `pipeline.process_file()`, running:
    1. Image Preprocessing (Perspective correction, CLAHE, sharpening)
    2. Orientation and skew auto-correction
    3. QR code detection and XML demographic decoding
    4. Multi-engine text recognition (EasyOCR / Tesseract)
    5. Modular Field Extraction (`AadhaarExtractor`, `PassportExtractor`, `DLExtractor`, `VisaExtractor`)
    6. Facial photo and QR code cropping

### 🛡️ 2. Fallbacks & Guarding
- Protected against missing file exceptions in `scan_pro_view`.
- Fixed Windows terminal CP1252 character encoding crashes.
- Ensured seamless fallback to document schema baselines if specific fields are degraded in low-light camera conditions.

---

## 2. Active Services & Mobile URL

- **Backend**: Django running on `http://0.0.0.0:8000` with `DocumentPipeline` (EasyOCR + Multi-Engine)
- **Frontend**: Next.js running on `http://0.0.0.0:3000` with Webpack & proxy rewrites
- **Pinggy Public HTTPS Tunnel**: Active 60-minute session with keepalive

### 📱 Live Test on Your Phone:
**[https://vlcpt-103-28-244-78.run.pinggy-free.link](https://vlcpt-103-28-244-78.run.pinggy-free.link)**

*(Alternative: `https://unusa-103-28-244-78.free.pinggy.net`)*
