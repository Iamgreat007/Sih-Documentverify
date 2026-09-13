# SecureScan AI — Multi-Preset Scanner & Verification Walkthrough

**SecureScan AI** is an AI-powered identity document verification prototype designed with a **CamScanner camera-first smartphone UX**. It integrates the camera and scanning engine from the [Web-CamScanner](https://github.com/shaheer-shehri/Web-CamScanner) repository and provides multi-side preset scanning with automated file saving directly to disk for your OCR engineering team.

---

## 1. Key Accomplishments

### 📱 Smartphone-First CamScanner Interface
- **Mobile Viewport Optimization**: Rendered in a clean smartphone frame with camera aspect ratio, laser scanning animations (`@keyframes laserSweep`), corner framing guides, and thumb-friendly controls.
- **Web-CamScanner Integration**: Reuses `react-webcam`, corner detection, deskewing, manual corner adjustment (`ManualCrop`), and contrast enhancement.
- **Client Fallback & FastAPI Compatibility**: Seamlessly attempts the Web-CamScanner backend endpoints (`/detect-corners` and `/scan-pro`) while gracefully falling back to client-side canvas transformations if the backend is offline.

### 🗂️ Document Presets & Multi-Side Scanning
Supports the requested presets with **Front & Back multi-sided capture**:
1. **Aadhaar Card**: Front side + Back side with demographic address details.
2. **Driving Licence**: Front side + Back side with vehicle classes (`MCWG, LMV`) and address.
3. **Passport**: Biometric front data page with MRZ zone.
4. **Visa**: International travel entry permit sticker page.
5. **Tampered Aadhaar (Demo Test)**: Visual tampering artifacts for demonstrating the **HIGH RISK** alert.

### 💾 Automatic Saving to the `image/` Folder for OCR
- Built a dedicated backend endpoint: [`/api/save-image`](file:///c:/Users/MSI-1/Desktop/SIH/frontend/src/app/api/save-image/route.ts).
- Every captured or preset scan is automatically saved into:
  ```
  c:\Users\MSI-1\Desktop\SIH\image\
  ├── aadhaar_front.svg (or .jpg)
  ├── aadhaar_back.svg (or .jpg)
  ├── driving_license_front.svg (or .jpg)
  ├── driving_license_back.svg (or .jpg)
  ├── passport_front.svg (or .jpg)
  └── visa_front.svg (or .jpg)
  ```
- Your friend/team member working on the Python OCR models can immediately load images directly:
  ```python
  import cv2
  img_front = cv2.imread("image/aadhaar_front.jpg")
  img_back = cv2.imread("image/aadhaar_back.jpg")
  ```

---

## 2. The 7-Step Verification Workflow

| Step | Screen | Description |
|---|---|---|
| **1** | **Scanner Home** | CamScanner viewfinder, laser scan, flash toggle, front/back switcher, and presets. |
| **2** | **Scan Review** | Scanned document preview (with Front/Back tabs), quality indicators, corner readjustment, and path notice (`image/...`). |
| **3** | **Document Type** | Auto-detected document type with 98% confidence, dropdown override, and file name. |
| **4** | **Extraction Screen** | Side-by-side OCR results with confidence pills (`Rahul Sharma ✓ 99%`) and inline editing. |
| **5** | **AI Verification** | Animated progress checklist: `✓ OCR Extraction`, `✓ Document Validation`, `⏳ Tampering Detection`, `⏳ Face Verification`, `⏳ Aadhaar eKYC`. |
| **6** | **Aadhaar eKYC** | Aadhaar demographic authentication (`XXXX XXXX 7821`), verification badges, and `eKYC VERIFIED` banner. |
| **7** | **Final Result** | **LOW RISK** (24/100) or **HIGH RISK** (78/100), 4 security checks, explanation, and `Done` button. |

---

## 3. Minimal Navigation

- **Scan**: Main scanner and linear verification workflow.
- **History**: Audit cards with masked identifiers, risk levels, and timestamps (`2 minutes ago`, `Yesterday`).
- **Settings**: Camera preference, verification strictness, and FastAPI backend URL (`http://localhost:8000`).

---

## 4. How to Run

1. **Start the Frontend**:
   ```bash
   cd c:\Users\MSI-1\Desktop\SIH\frontend
   npm run dev
   ```
   Open **`http://localhost:3000`** in your browser.

2. **Access Saved Images**:
   Check the folder at **`c:\Users\MSI-1\Desktop\SIH\image`** where all captured front and back scans are stored.
