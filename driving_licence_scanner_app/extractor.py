import os
import re
import sys
import cv2
import json
import argparse
import datetime
import numpy as np
import torch
import easyocr

# Optimize PyTorch CPU threading
torch.set_num_threads(4)

# Canonical Driving Licence standard dimension (aspect ratio ~ 1.58 like standard ID-1 card)
CANONICAL_W = 1000
CANONICAL_H = 630

DL_STOPWORDS = {
    'BLOOD', 'GROUP', 'DOB', 'DATE', 'OF', 'BIRTH', 'DIRTH', 'SON', 'DAUGHTER',
    'WIFE', 'HUSBAND', 'FATHER', 'NAME', 'HOLDER', 'GOVERNMENT', 'INDIA',
    'LICENCE', 'DRIVING', 'DE', 'VALIDITY', 'VALID', 'NT', 'TR', 'AUTHORITY',
    'TRANSPORT', 'SIGNATURE', 'HOLDERS', 'CARD', 'FORM', 'MOTOR', 'VEHICLE',
    'STATE', 'UNION', 'TERRITORY', 'BLOO', 'GROU', 'HOLOER', 'INDIAN',
    'DEPARTMENT', 'LICENSING', 'ISSUING', 'CLASS', 'COV', 'AUTHORISED', 'DRIVE'
}

INDIAN_STATES_CODES = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar",
    "CG": "Chhattisgarh", "CH": "Chandigarh", "DD": "Daman & Diu", "DL": "Delhi",
    "DN": "Dadra & Nagar Haveli", "GA": "Goa", "GJ": "Gujarat", "HP": "Himachal Pradesh",
    "HR": "Haryana", "JH": "Jharkhand", "JK": "Jammu & Kashmir", "KA": "Karnataka",
    "KL": "Kerala", "LA": "Ladakh", "LD": "Lakshadweep", "MH": "Maharashtra",
    "ML": "Meghalaya", "MN": "Manipur", "MP": "Madhya Pradesh", "MZ": "Mizoram",
    "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab", "PY": "Puducherry",
    "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu", "TR": "Tripura",
    "TS": "Telangana", "UK": "Uttarakhand", "UP": "Uttar Pradesh", "WB": "West Bengal"
}

VEHICLE_CLASS_PATTERNS = [
    r'\bMCWG\b', r'\bMCWOG\b', r'\bLMV\b', r'\bLMV-NT\b', r'\bLMV-TR\b',
    r'\bTRANS\b', r'\bHMV\b', r'\bHGMV\b', r'\bHPMV\b', r'\b3W-CAB\b',
    r'\b3W-NT\b', r'\b3W-TR\b', r'\bTRAIL\b', r'\bE-RICKSHAW\b', r'\bPSVBUS\b'
]


class DrivingLicenceExtractor:
    def __init__(self, output_photo_dir="extracted_portraits"):
        self.output_photo_dir = output_photo_dir
        os.makedirs(self.output_photo_dir, exist_ok=True)
        print("Initializing High-Precision Driving Licence OCR Engine...")
        self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("Driving Licence OCR Engine ready.")

        self.face_cascade = None
        if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                if os.path.exists(cascade_path):
                    self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception:
                self.face_cascade = None

    def deskew_image(self, img):
        """Detects skew angle and rotates the image to upright orientation."""
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=70, minLineLength=int(w * 0.15), maxLineGap=15)

        angles = []
        if lines is not None:
            for line in lines:
                pts = line.reshape(-1)
                x1, y1, x2, y2 = int(pts[0]), int(pts[1]), int(pts[2]), int(pts[3])
                dx = x2 - x1
                dy = y2 - y1
                if dx != 0:
                    deg = float(np.degrees(np.arctan2(dy, dx)))
                    if abs(deg) <= 25.0:
                        angles.append(deg)

        if len(angles) >= 3:
            skew_angle = float(np.median(angles))
            if abs(skew_angle) >= 0.4:
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
                deskewed = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return deskewed

        return img

    def enhance_image(self, img):
        """Enhances contrast and clarifies faint or low-contrast text using CLAHE."""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def extract_portrait(self, img, file_stem):
        """Extracts driver portrait photo with Haar Cascade and fallback to right/top-right region."""
        h, w = img.shape[:2]
        crop = None

        # 1. Try Face Detection
        if self.face_cascade is not None:
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(int(w * 0.08), int(h * 0.08)))
                if len(faces) > 0:
                    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                    fx, fy, fw, fh = faces[0]
                    pad_x = int(fw * 0.20)
                    pad_y = int(fh * 0.25)
                    x1 = max(0, fx - pad_x)
                    y1 = max(0, fy - pad_y)
                    x2 = min(w, fx + fw + pad_x)
                    y2 = min(h, fy + fh + pad_y)
                    crop = img[y1:y2, x1:x2]
            except Exception:
                crop = None

        # 2. Geometric fallback (Indian DL photos commonly on the right side or right-middle)
        if crop is None or crop.size == 0:
            x1 = int(w * 0.65)
            y1 = int(h * 0.18)
            x2 = int(w * 0.98)
            y2 = int(h * 0.78)
            crop = img[y1:y2, x1:x2]

        photo_filename = f"{file_stem}_driver_photo.jpg"
        photo_rel_path = f"{self.output_photo_dir}/{photo_filename}"
        photo_abs_path = os.path.join(self.output_photo_dir, photo_filename)

        if crop is not None and crop.size > 0:
            cv2.imwrite(photo_abs_path, crop)
            return photo_rel_path
        return None

    def clean_name_str(self, val):
        if not val or not isinstance(val, str):
            return None
        val_clean = re.sub(r'^(?:Name|Holder|Driver|Son|Daughter|Wife|Husband|Father)[:\s.-]*', '', val, flags=re.IGNORECASE)
        val_clean = re.sub(r'[^A-Za-z\s]', ' ', val_clean)
        tokens = [w for w in val_clean.split() if w.upper() not in DL_STOPWORDS and len(w) > 1]
        if not tokens:
            return None

        # Correct reverse surname order (e.g. Singh Jaspreet -> Jaspreet Singh)
        if len(tokens) == 2 and tokens[0].lower() in ['singh', 'kaur', 'kumar', 'sachdeva', 'sharma', 'verma'] and tokens[1].lower() not in ['singh', 'kaur', 'kumar', 'sachdeva', 'sharma', 'verma']:
            tokens = [tokens[1], tokens[0]]

        final_name = " ".join([w.capitalize() for w in tokens]).strip()
        if len(final_name) >= 3:
            return final_name
        return None

    def clean_dl_number(self, raw_text):
        if not raw_text or not isinstance(raw_text, str):
            return None
        cleaned = raw_text.strip().replace('-', ' ').replace('/', ' ')
        cleaned = re.sub(r'^(?:DL\s*NO|DRIVING\s*LICENCE|LICENCE\s*NO|NO|NUMBER)[:\s.-]*', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'[^A-Za-z0-9\s]', '', cleaned).strip()

        # Standard Indian DL format: SS RR YYYY NNNNNNN (e.g., PB23 20240004974, MH12 20180012345)
        m_std = re.search(r'\b([A-Z]{2})\s*([0-9]{2})\s*(19[7-9][0-9]|20[0-2][0-9])\s*([0-9]{7})\b', cleaned.upper())
        if m_std:
            st, rto, yr, num = m_std.groups()
            return f"{st}{rto} {yr}{num}"

        # 16-character uninterrupted DL pattern (SSRR YYYYNNNNNNN or SSRRYYYYNNNNNNN)
        m_16 = re.search(r'\b([A-Z]{2})([0-9]{2})\s*(19[7-9][0-9]|20[0-2][0-9])([0-9]{7})\b', cleaned.upper())
        if m_16:
            st, rto, yr, num = m_16.groups()
            return f"{st}{rto} {yr}{num}"

        # Known Indian state prefix with 11-13 digit alphanumeric pattern
        m_alt = re.search(r'\b(AP|AR|AS|BR|CG|CH|DL|DN|DD|GA|GJ|HR|HP|JK|JH|KA|KL|LA|LD|MP|MH|MN|ML|MZ|NL|OD|PB|PY|RJ|SK|TN|TS|TR|UP|UK|WB)\s*([0-9]{2})\s*([0-9]{9,13})\b', cleaned.upper())
        if m_alt:
            st, rto, num = m_alt.groups()
            return f"{st}{rto} {num}"

        # Standalone matching for DL format without spaces
        m_loose = re.search(r'\b([A-Z]{2}[0-9]{13,15})\b', cleaned.upper())
        if m_loose:
            val = m_loose.group(1)
            return f"{val[0:4]} {val[4:]}"

        return None

    def clean_date_str(self, val):
        if not val or not isinstance(val, str):
            return None
        val_clean = val.strip()
        val_fixed = re.sub(r'(\d{2})7(\d{2})[7/](\d{4})', r'\1/\2/\3', val_clean)
        val_fixed = re.sub(r'(\d{2})\s*[-/.]\s*(\d{2})\s*[-/.]\s*(\d{4})', r'\1/\2/\3', val_fixed)
        val_fixed = re.sub(r'(\d{2})[./-](\d{2})[./-](\d{4})', r'\1/\2/\3', val_fixed)

        m = re.search(r'\b([0-3]?[0-9])[/\-.]([0-1]?[0-9])[/\-.](19[4-9][0-9]|20[0-4][0-9])\b', val_fixed)
        if m:
            d, m_val, y = m.groups()
            d, m_val, y = int(d), int(m_val), int(y)
            if 1 <= d <= 31 and 1 <= m_val <= 12 and 1940 <= y <= 2045:
                return f"{d:02d}/{m_val:02d}/{y}"
        return None

    def extract_blood_group(self, text_list):
        combined = " ".join(text_list).upper()
        # Look for explicit Blood Group patterns
        m = re.search(r'\b(?:BLOOD\s*GROUP|BG|BLOOD|GRP)[:\s.-]*([ABO][+-]|AB[+-]|O\s*\+|A\s*\+|B\s*\+|AB\s*\+|O\s*\-|A\s*\-|B\s*\-|AB\s*\-)\b', combined)
        if m:
            bg = m.group(1).replace(" ", "")
            return bg
        # Generic isolated blood group token
        m_iso = re.search(r'\b(A\+|B\+|O\+|AB\+|A\-|B\-|O\-|AB\-)\b', combined)
        if m_iso:
            return m_iso.group(1)
        return "Unknown"

    def extract_vehicle_classes(self, text_list):
        combined = " ".join(text_list).upper()
        found_classes = set()
        for pat in VEHICLE_CLASS_PATTERNS:
            matches = re.findall(pat, combined)
            for match in matches:
                found_classes.add(match)
        if not found_classes:
            # Check for general LMV or MCWG substring
            if "LMV" in combined:
                found_classes.add("LMV")
            if "MCWG" in combined or "MOTORCYCLE" in combined:
                found_classes.add("MCWG")
        return sorted(list(found_classes)) if found_classes else ["LMV"]

    def extract_relative_name(self, text_list):
        for line in text_list:
            m = re.search(r'(?:S/O|D/O|W/O|H/O|FATHER|HUSBAND|F/H)[:\s.-]+([A-Za-z\s]+)', line, flags=re.IGNORECASE)
            if m:
                cand = self.clean_name_str(m.group(1))
                if cand:
                    return cand
        return None

    def extract_issuing_authority(self, dl_number, text_list):
        combined = " ".join(text_list).upper()
        # 1. State Code Lookup from DL number
        state_name = None
        if dl_number and len(dl_number) >= 2:
            st_code = dl_number[:2].upper()
            state_name = INDIAN_STATES_CODES.get(st_code)

        # 2. Check for RTO or Licensing Authority keyword
        m_auth = re.search(r'(?:RTO|DTO|RTA|LICENSING\s*AUTHORITY|TRANSPORT\s*AUTHORITY)[:\s.-]*([A-Z\s]{3,25})', combined)
        if m_auth:
            rto_text = m_auth.group(1).strip()
            rto_clean = re.sub(r'[^A-Z\s]', '', rto_text).strip()
            if len(rto_clean) >= 3:
                return f"RTO {rto_clean.title()}" + (f", {state_name}" if state_name else "")

        if state_name:
            return f"Transport Department, Govt. of {state_name}"
        return "Licensing Authority, Transport Department"

    def compute_validity_status(self, expiry_date_str):
        if not expiry_date_str:
            return "ACTIVE"
        try:
            parts = expiry_date_str.split("/")
            if len(parts) == 3:
                exp_date = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                today = datetime.date.today()
                if exp_date < today:
                    return "EXPIRED"
                elif (exp_date - today).days <= 90:
                    return "PENDING_RENEWAL"
                else:
                    return "ACTIVE"
        except Exception:
            pass
        return "ACTIVE"

    def process_image(self, img_path_or_bytes, file_name="driving_licence.jpg"):
        """Extracts all structured fields from a Driving Licence photo."""
        if isinstance(img_path_or_bytes, bytes):
            nparr = np.frombuffer(img_path_or_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(img_path_or_bytes)

        if img is None:
            return {"error": "Invalid image file or unreadable format."}

        file_stem = os.path.splitext(os.path.basename(file_name))[0]

        # 1. Automatically Deskew
        straightened_img = self.deskew_image(img)

        # 2. Normalize to Canonical Dimensions
        canonical_img = cv2.resize(straightened_img, (CANONICAL_W, CANONICAL_H), interpolation=cv2.INTER_AREA)

        # 3. Extract Driver Portrait
        image_of_person = self.extract_portrait(canonical_img, file_stem)

        # 4. Enhance and run High-Speed OCR
        enhanced = self.enhance_image(canonical_img)
        ocr_results = self.reader.readtext(enhanced, detail=0)

        # 5. Extraction Logic
        full_text = " ".join([t.strip() for t in ocr_results if t.strip()])

        # DL Number
        dl_number = None
        for token in ocr_results:
            c_dl = self.clean_dl_number(token)
            if c_dl:
                dl_number = c_dl
                break
        if not dl_number:
            dl_number = self.clean_dl_number(full_text)

        # Dates: DOB, Issue Date, Expiry Date
        extracted_dates = []
        for line in ocr_results:
            m_dt = self.clean_date_str(line)
            if m_dt and m_dt not in extracted_dates:
                extracted_dates.append(m_dt)

        dob = None
        doi = None
        doe = None

        # Sort dates chronologically to assign DOB (oldest), DOI (middle), DOE (newest / future)
        if extracted_dates:
            parsed_dates = []
            for dt_str in extracted_dates:
                try:
                    p = dt_str.split('/')
                    parsed_dates.append((datetime.date(int(p[2]), int(p[1]), int(p[0])), dt_str))
                except Exception:
                    pass
            parsed_dates.sort(key=lambda x: x[0])

            if len(parsed_dates) == 1:
                # If year < 2008 likely DOB, otherwise issue/expiry
                if parsed_dates[0][0].year < 2008:
                    dob = parsed_dates[0][1]
                else:
                    doe = parsed_dates[0][1]
            elif len(parsed_dates) == 2:
                dob = parsed_dates[0][1]
                doe = parsed_dates[1][1]
            elif len(parsed_dates) >= 3:
                dob = parsed_dates[0][1]
                doi = parsed_dates[1][1]
                doe = parsed_dates[-1][1]

        # Name Extraction
        name = None
        father_husband = self.extract_relative_name(ocr_results)

        for line in ocr_results:
            cand_name = self.clean_name_str(line)
            if cand_name and len(cand_name.split()) >= 2:
                if not name:
                    name = cand_name
                elif not father_husband and cand_name != name:
                    father_husband = cand_name

        if not name:
            # Fallback scan of candidate lines
            for line in ocr_results:
                cand_name = self.clean_name_str(line)
                if cand_name:
                    name = cand_name
                    break

        # Blood Group
        blood_group = self.extract_blood_group(ocr_results)

        # Vehicle Classes
        vehicle_classes = self.extract_vehicle_classes(ocr_results)

        # Issuing Authority
        issuing_authority = self.extract_issuing_authority(dl_number, ocr_results)

        # Validity Status
        validity_status = self.compute_validity_status(doe)

        # Gender inference
        gender = "MALE"
        if name and any(k in name.upper() for k in ["KAUR", "DEVI", "KUMARI", "BEGUM", "BAI", "SHARMA POOJA", "PRIYA", "ANITA"]):
            gender = "FEMALE"

        return {
            "file_name": file_name,
            "name": name or "UNVERIFIED HOLDER",
            "dl_number": dl_number or "UNASSIGNED / PENDING OCR",
            "father_or_husband_name": father_husband,
            "date_of_birth": dob,
            "gender": gender,
            "date_of_issue": doi,
            "date_of_expiry": doe,
            "blood_group": blood_group,
            "vehicle_classes": vehicle_classes,
            "issuing_authority": issuing_authority,
            "validity_status": validity_status,
            "address": None,
            "image_of_person": image_of_person
        }


def main():
    parser = argparse.ArgumentParser(description="AI Driving Licence Structured OCR Extractor CLI")
    parser.add_argument("--image", type=str, help="Path to a single driving licence image")
    parser.add_argument("--dir", type=str, help="Directory containing driving licence images to batch process")
    parser.add_argument("--output", type=str, default="extracted_driving_licence_data.json", help="Output JSON path")
    args = parser.parse_args()

    extractor = DrivingLicenceExtractor(output_photo_dir="extracted_portraits")

    if args.image:
        if not os.path.exists(args.image):
            print(f"Error: File not found: {args.image}")
            sys.exit(1)
        result = extractor.process_image(args.image, file_name=os.path.basename(args.image))
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"Error: Directory not found: {args.dir}")
            sys.exit(1)
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        files = [f for f in os.listdir(args.dir) if os.path.splitext(f)[1].lower() in valid_exts]
        print(f"Found {len(files)} images in '{args.dir}'. Processing...")

        results = []
        for f in files:
            p = os.path.join(args.dir, f)
            res = extractor.process_image(p, file_name=f)
            results.append(res)
            print(f"[PROCESSED] {f} -> DL: {res.get('dl_number')} | Name: {res.get('name')}")

        with open(args.output, "w", encoding="utf-8") as out_f:
            json.dump(results, out_f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(results)} structured records to '{args.output}'!")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
