# AI Driving Licence Screening & Field Extractor App

Interactive web application and standalone CLI tool for extracting structured demographic fields, vehicle authorizations (COV), dates, and driver portraits from Indian Driving Licences.

---

## Features

1. **Manual File Upload**: Drag and drop single or multiple Driving Licence images (JPG, PNG).
2. **Live Webcam Scanner**: Real-time camera streaming with card alignment guide and snapshot capture.
3. **Structured Field Extraction**:
   - **`name`**: Driver / Holder's Full Name (with surname ordering correction)
   - **`dl_number`**: Standard Indian DL format (`SSRR YYYYNNNNNNN` or state RTO pattern)
   - **`father_or_husband_name`**: S/O, D/O, W/O relative name
   - **`date_of_birth`**: Clean `DD/MM/YYYY`
   - **`gender`**: `MALE` / `FEMALE`
   - **`date_of_issue`**: Issue date / Valid from
   - **`date_of_expiry`**: Expiry date / Valid till
   - **`blood_group`**: `A+`, `B+`, `O+`, `AB+`, etc.
   - **`vehicle_classes`**: Authorized categories (`LMV`, `MCWG`, `TRANS`, `HMV`, etc.)
   - **`issuing_authority`**: RTO / State Transport Authority
   - **`validity_status`**: Live status calculation (`VALID`, `EXPIRED`, `PENDING_RENEWAL`)
   - **`image_of_person`**: Automatically cropped driver portrait photo
4. **Interactive Dashboard**:
   - Visual Smart Card simulation with simulated chip & badge.
   - Vehicle class badge chips (COV).
   - Real-time JSON viewer with instant "Copy JSON" button.
   - Session history panel with click-to-view previous scans.
   - One-click "Export All JSON" to download `extracted_driving_licence_data.json`.
5. **Standalone CLI Mode**: Process individual images or batch folders directly via command line.

---

## How to Run

### Option 1: Web Application (Direct Launch Script)
- Double-click `run_app.bat`
- Or run in PowerShell:
  ```powershell
  .\driving_licence_scanner_app\run_app.ps1
  ```

Open your browser and navigate to:
```
http://127.0.0.1:8001
```

### Option 2: Standalone CLI Tool
Process a single image:
```powershell
.venv\Scripts\python driving_licence_scanner_app\extractor.py --image "path\to\driving_licence.jpg"
```

Batch process an entire directory:
```powershell
.venv\Scripts\python driving_licence_scanner_app\extractor.py --dir "path\to\images_folder" --output "my_extracted_dl_data.json"
```

---

## Output JSON Schema Example

```json
{
  "file_name": "sample_dl.jpg",
  "name": "Jaspreet Singh",
  "dl_number": "PB23 20240004974",
  "father_or_husband_name": "Gurdev Singh",
  "date_of_birth": "14/08/1992",
  "gender": "MALE",
  "date_of_issue": "10/05/2024",
  "date_of_expiry": "13/08/2042",
  "blood_group": "B+",
  "vehicle_classes": [
    "LMV",
    "MCWG"
  ],
  "issuing_authority": "Transport Department, Govt. of Punjab",
  "validity_status": "ACTIVE",
  "address": null,
  "image_of_person": "extracted_portraits/sample_dl_driver_photo.jpg"
}
```
