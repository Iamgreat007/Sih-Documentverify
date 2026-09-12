# AI Fake Identity & Document Screening System (SIH 26188)

A comprehensive suite of high-precision AI document extractors and interactive screening web applications for **Passports**, **Indian Driving Licences**, and **Aadhaar Cards**.

---

## Document Screening Suite Overview

| Application | Port | Document Type | Key Features |
| :--- | :--- | :--- | :--- |
| **Passport Scanner** (`passport_scanner_app/`) | `8000` | Passports (ICAO 9303) | Optical Character Recognition, ICAO 9303 MRZ Decoding, 2-line MRZ checksum validator, Place of Issue gazetteer matching, Portrait photo extraction. |
| **Driving Licence Scanner** (`driving_licence_scanner_app/`) | `8001` | Indian Driving Licences | Standard DL Number validation (`SSRR YYYYNNNNNNN`), Vehicle category (COV) tags (LMV, MCWG, TRANS), Blood group detection, Issuing RTO extraction, Live validity calculator. |
| **Aadhaar Scanner** (`aadhaar_scanner_app/`) | `8002` | UIDAI Aadhaar Cards | 12-digit Aadhaar UID formatting, **Verhoeff Mathematical Checksum Validation (Dihedral $D_5$ Modulo 10)**, Guardian (`C/O`) extraction, PIN Code & State gazetteer spelling correction. |

---

## Running the Applications

### 1. Indian Passport Scanner App (Port 8000)
- **One-Click Batch File**: Double-click `passport_scanner_app\run_app.bat`
- **PowerShell Script**:
  ```powershell
  .\passport_scanner_app\run_app.ps1
  ```
- **Terminal Command**:
  ```powershell
  .venv\Scripts\python -m uvicorn main:app --app-dir passport_scanner_app --host 127.0.0.1 --port 8000 --reload
  ```
- **Web UI**: Navigate to `http://127.0.0.1:8000`

---

### 2. Indian Driving Licence Scanner App (Port 8001)
- **One-Click Batch File**: Double-click `driving_licence_scanner_app\run_app.bat`
- **PowerShell Script**:
  ```powershell
  .\driving_licence_scanner_app\run_app.ps1
  ```
- **Terminal Command**:
  ```powershell
  .venv\Scripts\python -m uvicorn main:app --app-dir driving_licence_scanner_app --host 127.0.0.1 --port 8001 --reload
  ```
- **Web UI**: Navigate to `http://127.0.0.1:8001`
- **CLI Batch Extractor**:
  ```powershell
  .venv\Scripts\python driving_licence_scanner_app\extractor.py --dir "path/to/dl_images" --output "extracted_dl.json"
  ```

---

### 3. Aadhaar Card Scanner App (Port 8002)
- **One-Click Batch File**: Double-click `aadhaar_scanner_app\run_app.bat`
- **PowerShell Script**:
  ```powershell
  .\aadhaar_scanner_app\run_app.ps1
  ```
- **Terminal Command**:
  ```powershell
  .venv\Scripts\python -m uvicorn main:app --app-dir aadhaar_scanner_app --host 127.0.0.1 --port 8002 --reload
  ```
- **Web UI**: Navigate to `http://127.0.0.1:8002`
- **CLI Batch Extractor**:
  ```powershell
  .venv\Scripts\python aadhaar_scanner_app\extractor.py --dir "path/to/aadhaar_images" --output "extracted_aadhaar.json"
  ```

---

## Features Across All Applications

- **Dual Ingestion**: Drag-and-drop manual upload for single or batch images, plus live webcam video streaming with custom document alignment overlays.
- **Auto Deskewing**: Canny edge detection & Hough line angle detection to automatically rotate and level skewed or tilted cards.
- **Smart Portrait Extraction**: Haar Cascade frontal face detection with adaptive geometric fallback zones tailored to each document's physical layout.
- **Mathematical Integrity Verification**: Real-time ICAO 9303 check digit calculation for Passports and Verhoeff Modulo 10 check digit verification for Aadhaar.
- **Interactive UI**: Real-time card visualizer, live status badges, expandable JSON viewer with 1-click clipboard copy, and persistent session history.
