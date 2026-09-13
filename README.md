# Indian Identity Document OCR & KYC Feature Extraction API

Automated, end-to-end KYC identity document classification, feature extraction, and checksum validation service for **Aadhaar Card**, **Indian Passport**, **Indian Visa**, and **Driving Licence**.

---

## 🌟 Key Features

1. **Document Classification**: Classifies uploaded photo scans as `aadhaar`, `passport`, `driving_licence`, `visa`, or `unknown` with confidence scoring.
2. **OpenCV Preprocessing & De-skewing**:
   - Boundary detection and 4-point perspective transform (`cv2.getPerspectiveTransform`) to straighten skewed photo scans.
   - CLAHE luminance contrast enhancement, unsharp mask sharpening, and edge-preserving bilateral denoising.
   - Auto-orientation correction (0° / 90° / 180° / 270°).
3. **Document Extraction Logic**:
   - **Aadhaar**: QR-first extraction via `pyzbar` / `OpenCV` to parse embedded XML attributes (Name, DOB, Gender, UID, Address). Fallback to OCR for text and masked UIDs (`XXXX XXXX 1234`). Verhoeff checksum validation.
   - **Passport & Visa**: Machine Readable Zone (MRZ) parser per ICAO Doc 9303 standard. Parses passport number, names, nationality, DOB, sex, expiry date, issuing country, and validates Modulo 10 check digits.
   - **Driving Licence**: Multi-state regex parser matching Indian state DL formats (`TS...`, `DL...`, `MH...`). Extracts DL number, Name, DOB, Address, Issue/Expiry, and Vehicle Classes (`MCWG`, `LMV`).
4. **Multi-Engine OCR**: Primary **PaddleOCR** engine (optimized for Indic + English scripts) with Tesseract OCR fallback.
5. **FastAPI Web Service**: `POST /extract` endpoint accepting image or PDF upload and returning structured JSON response with `document_type`, `confidence`, `extracted_fields`, `validation_status` (`pass`/`fail` per field), and `raw_ocr_text`.
6. **Unit Tests**: Full `pytest` suite for Verhoeff Aadhaar checksums, ICAO 9303 MRZ check digits, Document Classifier, and FastAPI endpoint.

---

## 📁 Project Structure

```
.
├── api/
│   ├── __init__.py
│   └── main.py                 # FastAPI service with POST /extract endpoint
├── src/
│   ├── preprocessor.py         # Perspective transform, de-skewing & CLAHE
│   ├── orientation.py          # Auto-rotation alignment
│   ├── ocr_engine.py           # PaddleOCR primary with Tesseract fallback
│   ├── doc_classifier.py       # Heuristic & keyword document classifier
│   ├── qr_decoder.py           # QR decoder for Aadhaar XML data
│   ├── mrz_parser.py           # ICAO 9303 MRZ parser & check digits
│   ├── verhoeff.py             # Verhoeff checksum validator for Aadhaar
│   ├── validators.py           # Field-level validation engine ('pass'/'fail')
│   ├── extractors/
│   │   ├── base.py             # BaseExtractor abstract class
│   │   ├── aadhaar.py          # Aadhaar QR-first + OCR extractor
│   │   ├── passport.py         # Passport MRZ extractor
│   │   ├── visa.py             # Visa MRZ extractor
│   │   └── dl.py               # Flexible multi-state Driving Licence extractor
│   ├── format_checker.py       # Document format similarity checker
│   └── pipeline.py             # Pipeline orchestrator
├── tests/
│   ├── test_verhoeff.py        # Verhoeff unit tests
│   ├── test_mrz.py             # MRZ check digits unit tests
│   ├── test_classifier.py     # Document classifier unit tests
│   └── test_api.py            # FastAPI POST /extract unit tests
├── samples/                    # Sample fixture identity documents
├── app.py                      # Streamlit Web UI dashboard (port 8502)
├── requirements.txt            # Python dependencies
└── README.md                   # System documentation
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.9 - 3.11 installed.
- Tesseract-OCR binary installed (optional for Tesseract fallback mode).

### 2. Install Dependencies
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 💻 Running the FastAPI Service

To launch the FastAPI service on port 8000:

```powershell
.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger API Documentation: **`http://localhost:8000/docs`**

### Example Request using cURL:
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@samples/aadhaar/aadhaar_compact.jpg"
```

### Example JSON Response:
```json
{
  "document_type": "aadhaar",
  "document_name": "Aadhaar Card",
  "confidence": 95.0,
  "extracted_fields": {
    "aadhaar_number": "836696393224",
    "aadhaar_number_valid": true,
    "dob": "20/06/1986",
    "gender": "MALE",
    "name": "Parvez Alam",
    "address": "Address ..."
  },
  "validation_status": {
    "aadhaar_number": "pass",
    "dob": "pass",
    "name": "pass",
    "overall": "pass"
  },
  "raw_ocr_text": "UNIQUE IDENTIFICATION AUTHORITY OF INDIA..."
}
```

---

## 🧪 Running Unit Tests

Run the complete test suite using `unittest` or `pytest`:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

---

## 🖥️ Running the Streamlit Web Dashboard

To run the interactive web interface:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```
Web Interface URL: **`http://localhost:8502`**
