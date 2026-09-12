# AI Passport Screening & MRZ Scanner App

Interactive web application for manual file upload and live camera scanning of passports to extract structured demographic fields, ICAO 9303 MRZ codes, and individual portrait photos into JSON.

## Features

1. **Manual File Upload**: Drag and drop single or multiple passport images (JPG, PNG).
2. **Live Webcam Scanner**: Real-time camera streaming with alignment guide overlay and one-click snapshot capture.
3. **Structured Extraction**:
   - **`name`**: Given names and surname
   - **`passport_no`**: Passport number
   - **`date_of_birth`**: Clean `DD/MM/YYYY` date
   - **`gender`**: `M` / `F`
   - **`date_of_issue`**: Issue date
   - **`date_of_expiry`**: Expiration date
   - **`place_of_birth`**: Place of birth
   - **`address`**: Permanent address
   - **`mrz_code`**: Decoded ICAO 9303 Line 1 & Line 2 MRZ strings
   - **`image_of_person`**: Automatically cropped portrait photo
4. **Interactive Dashboard**:
   - Live visual summary card with portrait photo and key attributes.
   - Decoded MRZ strip with checksum badge.
   - Real-time JSON viewer with instant "Copy JSON" button.
   - Session history panel with click-to-view previous scans.
   - One-click "Export All JSON" to download `extracted_passport_data.json`.

---

## How to Run

### Option 1: Direct Launch Script
- Double click [run_app.bat](file:///d:/SIH%20Hackathon/passport_scanner_app/run_app.bat)
- Or run in PowerShell:
  ```powershell
  .\passport_scanner_app\run_app.ps1
  ```

### Option 2: Terminal Command
```powershell
.venv\Scripts\python -m uvicorn main:app --app-dir passport_scanner_app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```
