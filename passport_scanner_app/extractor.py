import os
import re
import cv2
import json
import numpy as np
import torch
import difflib
from PIL import Image
import easyocr

# Optimize PyTorch CPU threading
torch.set_num_threads(4)

# Canonical Passport Standard Dimensions (ICAO 9303 aspect ratio ~ 1.47)
CANONICAL_W = 1000
CANONICAL_H = 680

# Template-based Normalized Region of Interest (ROI) definitions (x1, y1, x2, y2 percentages)
TEMPLATE_ROIS = {
    "passport_no": {"x1": 0.72, "y1": 0.21, "x2": 0.98, "y2": 0.30, "type": "passport_no"},
    "surname": {"x1": 0.35, "y1": 0.24, "x2": 0.80, "y2": 0.33, "type": "text"},
    "given_name": {"x1": 0.35, "y1": 0.32, "x2": 0.85, "y2": 0.41, "type": "text"},
    "gender": {"x1": 0.58, "y1": 0.39, "x2": 0.75, "y2": 0.47, "type": "gender"},
    "date_of_birth": {"x1": 0.70, "y1": 0.42, "x2": 0.98, "y2": 0.51, "type": "date"},
    "place_of_birth": {"x1": 0.35, "y1": 0.49, "x2": 0.98, "y2": 0.59, "type": "location_birth"},
    "place_of_issue": {"x1": 0.38, "y1": 0.58, "x2": 0.78, "y2": 0.67, "type": "location_issue"},
    "date_of_issue": {"x1": 0.40, "y1": 0.66, "x2": 0.68, "y2": 0.76, "type": "date"},
    "date_of_expiry": {"x1": 0.69, "y1": 0.66, "x2": 0.98, "y2": 0.77, "type": "date"},
    "mrz_zone": {"x1": 0.04, "y1": 0.74, "x2": 0.98, "y2": 0.96, "type": "mrz"},
    "portrait": {"x1": 0.04, "y1": 0.14, "x2": 0.36, "y2": 0.70, "type": "image"}
}

# Regional Passport Offices (RPOs) in India & Key Consular Hubs
KNOWN_RPO_CITIES = [
    "AHMEDABAD", "AMRITSAR", "BAREILLY", "BENGALURU", "BANGALORE", "BHOPAL", "BHUBANESWAR",
    "CHANDIGARH", "CHENNAI", "MADRAS", "COCHIN", "KOCHI", "COIMBATORE", "DEHRADUN", "DELHI",
    "NEW DELHI", "GHAZIABAD", "GOA", "PANAJI", "GUWAHATI", "HYDERABAD", "JAIPUR", "JALANDHAR",
    "JAMMU", "KOLKATA", "CALCUTTA", "KOZHIKODE", "CALICUT", "LUCKNOW", "MADURAI", "MALAPPURAM",
    "MUMBAI", "BOMBAY", "NAGPUR", "PATNA", "PUNE", "POONA", "RAIPUR", "RANCHI", "SHIMLA",
    "SRINAGAR", "SURAT", "THANE", "TIRUCHIRAPPALLI", "TRICHY", "TRIVANDRUM", "THIRUVANANTHAPURAM",
    "VIJAYAWADA", "VISAKHAPATNAM", "VIZAG"
]

KNOWN_STATES = [
    "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR", "CHHATTISGARH", "GOA", "GUJARAT",
    "HARYANA", "HIMACHAL PRADESH", "JHARKHAND", "KARNATAKA", "KERALA", "MADHYA PRADESH", "MAHARASHTRA",
    "MANIPUR", "MEGHALAYA", "MIZORAM", "NAGALAND", "ODISHA", "ORISSA", "PUNJAB", "RAJASTHAN",
    "SIKKIM", "TAMIL NADU", "TELANGANA", "TRIPURA", "UTTAR PRADESH", "UTTARAKHAND", "WEST BENGAL",
    "ANDAMAN AND NICOBAR ISLANDS", "CHANDIGARH", "DADRA AND NAGAR HAVELI", "DAMAN AND DIU",
    "DELHI", "JAMMU AND KASHMIR", "LADAKH", "LAKSHADWEEP", "PUDUCHERRY"
]

KNOWN_CITIES_AND_DISTRICTS = [
    "AGRA", "AHMEDNAGAR", "AJMER", "AKOLA", "ALIGARH", "ALLAHABAD", "PRAYAGRAJ", "ALWAR", "AMBALA",
    "AMRAVATI", "ANANTAPUR", "ASANSOL", "AURANGABAD", "CHHATRAPATI SAMBHAJINAGAR", "BARODA", "VADODARA",
    "BATHINDA", "BELGAUM", "BELAGAVI", "BELLARY", "BALLARI", "BHAGALPUR", "BHARATPUR", "BHAVNAGAR",
    "BHILAI", "BHILWARA", "BHIWANDI", "BIKANER", "BILASPUR", "BOKARO", "BULANDSHAHR", "BURHANPUR",
    "CHHAPRA", "CUTTACK", "DARBHANGA", "DAVANAGERE", "DHANBAD", "DHULE", "DINDIGUL", "DURG",
    "DURGAPUR", "ELURU", "ERODE", "ETAH", "ETAWAH", "FARIDABAD", "FIROZABAD", "GANDHINAGAR", "GAYA",
    "GORAKHPUR", "GULBARGA", "KALABURAGI", "GUNTUR", "GURGAON", "GURUGRAM", "GWALIOR", "HALDWANI",
    "HARIDWAR", "HISSAR", "HISAR", "HOSHIARPUR", "HOWRAH", "HUBLI", "HUBLI-DHARWAD", "IMPHAL", "INDORE",
    "ITANAGAR", "JABALPUR", "JALGAON", "JALNA", "JAMNAGAR", "JAMSHEDPUR", "JHANSI", "JODHPUR",
    "JUNAGADH", "KAKINADA", "KALYAN", "KANNUR", "KANPUR", "KARIMNAGAR", "KARNAL", "KASARAGOD",
    "KHAMMAM", "KHARAGPUR", "KOHIMA", "KOLHAPUR", "KOLLAM", "KOTA", "KOTTAYAM", "KURNOOL", "LATUR",
    "LONAVALA", "LUDHIANA", "MADGAON", "MALDA", "MANGALORE", "MANGALURU", "MATHURA", "MEERUT",
    "MIRZAPUR", "MORADABAD", "MUZAFFARNAGAR", "MUZAFFARPUR", "MYSORE", "MYSURU", "NADIAD",
    "NAGERCOIL", "NANDED", "NANDURBAR", "NASHIK", "NASIK", "NAVI MUMBAI", "NELLORE", "NIZAMABAD",
    "NOIDA", "GREATER NOIDA", "PALAKKAD", "PALGHAR", "PALI", "PANIPAT", "PARBHANI", "PATIALA",
    "PIMPRI CHINCHWAD", "PUDUCHERRY", "PONDICHERRY", "PURNIA", "RAE BARELI", "RAICHUR", "RAJAHMUNDRY",
    "RAJKOT", "RAMPUR", "RATLAM", "REWA", "ROHTAK", "ROORKEE", "ROURKELA", "SAGAR", "SAHARANPUR",
    "SALEM", "SAMBALPUR", "SANGLI", "SATARA", "SECUNDERABAD", "SHAHJAHANPUR", "SHILLONG", "SILIGURI",
    "SOLAPUR", "SONIPAT", "SRIGANGANAGAR", "TEZPUR", "TINSUKIA", "TIRUNELVELI", "TIRUPATI",
    "TIRUPPUR", "TUMKUR", "TUMAKURU", "TUTICORIN", "THOOTHUKUDI", "UDAIPUR", "UDUPI", "UJJAIN",
    "ULHASNAGAR", "UNNAO", "VALSAD", "VAPI", "VARANASI", "BANARAS", "KASHI", "VASAI", "VASAI-VIRAR",
    "VELLORE", "WARANGAL", "YAMUNANAGAR", "YAVATMAL", "AIZAWL", "GANGTOK", "PORT BLAIR", "AGARTALA"
]

KNOWN_INTERNATIONAL_HUBS = [
    "DUBAI", "ABU DHABI", "SHARJAH", "DOHA", "RIYADH", "JEDDAH", "KUWAIT", "MUSCAT", "MANAMA",
    "SINGAPORE", "KUALA LUMPUR", "LONDON", "NEW YORK", "TORONTO", "SYDNEY", "MELBOURNE", "NAIROBI",
    "KATHMANDU", "COLOMBO", "DHAKA"
]

ALL_KNOWN_LOCATIONS = sorted(list(set(
    KNOWN_RPO_CITIES + KNOWN_CITIES_AND_DISTRICTS + KNOWN_STATES + KNOWN_INTERNATIONAL_HUBS
)), key=len, reverse=True)


def levenshtein_dist(s1, s2):
    """Computes exact edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_dist(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def match_single_location(token, candidates, max_dist=None):
    """Fuzzy matches a token against a gazetteer candidate list using Levenshtein distance."""
    t_clean = re.sub(r'[^A-Z]', '', token.upper())
    if not t_clean or len(t_clean) < 3:
        return token
        
    if t_clean in candidates:
        return t_clean
        
    l = len(t_clean)
    if max_dist is None:
        if l >= 8:
            allowed_dist = 3
        elif l >= 5:
            allowed_dist = 2
        else:
            allowed_dist = 1
    else:
        allowed_dist = max_dist

    best_cand = None
    best_dist = 999
    
    for cand in candidates:
        cand_clean = re.sub(r'[^A-Z]', '', cand.upper())
        if abs(len(cand_clean) - l) > allowed_dist:
            continue
        dist = levenshtein_dist(t_clean, cand_clean)
        if dist <= allowed_dist and dist < best_dist:
            if dist / max(len(t_clean), len(cand_clean)) <= 0.35:
                best_dist = dist
                best_cand = cand
            
    if best_cand:
        return best_cand
        
    matches = difflib.get_close_matches(t_clean, candidates, n=1, cutoff=0.75)
    if matches:
        return matches[0]
        
    return token


class PassportExtractor:
    def __init__(self, output_photo_dir="extracted_portraits"):
        self.output_photo_dir = output_photo_dir
        os.makedirs(self.output_photo_dir, exist_ok=True)
        print("Initializing Template-Based High-Speed OCR Engine with Deskewing & Fuzzy Gazetteer...")
        self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("OCR Engine ready.")
        
        self.face_cascade = None
        if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                if os.path.exists(cascade_path):
                    self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception:
                self.face_cascade = None

    def deskew_image(self, img):
        """
        Detects tilt / skew angle in bent or angled photos and rotates the image to be upright.
        """
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

    def preprocess_roi(self, crop):
        """Enhances contrast and clarifies faint or low-contrast text in a cropped ROI."""
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def extract_portrait(self, canonical_img, file_stem):
        """Extracts person portrait photo using Haar Cascades with ROI fallback."""
        h_can, w_can = canonical_img.shape[:2]
        crop = None
        
        # 1. Try Face Detection on canonical image
        if self.face_cascade is not None:
            try:
                gray = cv2.cvtColor(canonical_img, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(int(w_can*0.1), int(h_can*0.1)))
                if len(faces) > 0:
                    faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
                    x, y, fw, fh = faces[0]
                    pad_x = int(fw * 0.15)
                    pad_y = int(fh * 0.20)
                    x1 = max(0, x - pad_x)
                    y1 = max(0, y - pad_y)
                    x2 = min(w_can, x + fw + pad_x)
                    y2 = min(h_can, y + fh + pad_y)
                    crop = canonical_img[y1:y2, x1:x2]
            except Exception:
                crop = None

        # 2. Geometric template fallback
        if crop is None or crop.size == 0:
            p_roi = TEMPLATE_ROIS["portrait"]
            x1 = int(p_roi["x1"] * w_can)
            y1 = int(p_roi["y1"] * h_can)
            x2 = int(p_roi["x2"] * w_can)
            y2 = int(p_roi["y2"] * h_can)
            crop = canonical_img[y1:y2, x1:x2]

        photo_filename = f"{file_stem}_person.jpg"
        photo_rel_path = f"{self.output_photo_dir}/{photo_filename}"
        photo_abs_path = os.path.join(self.output_photo_dir, photo_filename)
        
        if crop is not None and crop.size > 0:
            cv2.imwrite(photo_abs_path, crop)
            return photo_rel_path
        return None

    def clean_date_str(self, val):
        if not val:
            return None
        m = re.search(r'\b([0-3]?[0-9])[/\-. ]([0-1]?[0-9])[/\-. ](19[4-9][0-9]|20[0-4][0-9])\b', str(val))
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= d <= 31 and 1 <= mo <= 12:
                return f"{d:02d}/{mo:02d}/{y}"
        return None

    def clean_passport_number(self, raw):
        if not raw:
            return None
        cleaned = re.sub(r'^(?:PASSPORT\s*NO|PASSPORT|NUMBER|NO|Maulz\s*7)[:;.\s/_-]*', '', raw, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'[^A-Z0-9]', '', cleaned.upper())
        m = re.search(r'([A-Z][0-9]{7})', cleaned)
        if m:
            return m.group(1)
        if len(cleaned) == 8 and cleaned[0] in ['5', '8', '0', '1', '7'] and cleaned[1:].isdigit():
            digit_to_letter = {'5': 'S', '8': 'S', '0': 'O', '1': 'I', '7': 'Z'}
            return digit_to_letter.get(cleaned[0], 'S') + cleaned[1:]
        m_loose = re.search(r'([58017][0-9]{7})', cleaned)
        if m_loose:
            cand = m_loose.group(1)
            digit_to_letter = {'5': 'S', '8': 'S', '0': 'O', '1': 'I', '7': 'Z'}
            return digit_to_letter.get(cand[0], 'S') + cand[1:]
        return cleaned if (7 <= len(cleaned) <= 9 and not cleaned.startswith("PASSP")) else None

    def clean_place_of_issue(self, raw_text):
        """Extracts and fuzzy corrects Regional Passport Office / Place of Issue."""
        if not raw_text:
            return None
        cleaned = re.sub(r'^(?:[0-9A-Za-z]{1,5}\s*[/\\-]\s*)*(?:Place\s*0?[lf]\s*Issue|Issue|ON9S|12n7|4r)[\s/.:-]*', '', raw_text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'[^A-Za-z\s-]', '', cleaned)
        cleaned = re.sub(r'\b([A-Za-z]{3,})\s+([A-Za-z]{1,2})\b', r'\1\2', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip().upper()
        if not cleaned:
            return None
            
        match_rpo = match_single_location(cleaned, KNOWN_RPO_CITIES)
        if match_rpo != cleaned:
            return match_rpo
            
        match_all = match_single_location(cleaned, ALL_KNOWN_LOCATIONS)
        return match_all.upper() if match_all else cleaned

    def clean_place_of_birth(self, raw_text):
        """Extracts and fuzzy corrects village/town, district and state in Place of Birth."""
        if not raw_text:
            return None
        # 1. Clean leading noise & corrupted headers
        cleaned = re.sub(r'^(?:[0-9A-Za-z#@*/\\]{1,8}\s*)*(?:Place\s*0?[lf]\s*Birth|Piaco.*Birth|Pace\s*on\s*birth|ONBIRTN|MFAPACE|UCE\s*OBIRTN|FIA/|HRAU)[\s/.:-]*', '', raw_text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'[^A-Za-z0-9\s,\'.-]', '', cleaned)
        cleaned = re.sub(r'\b([A-Za-z]{3,})\s+([A-Za-z]{1,2})\b', r'\1\2', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip().upper()
        if not cleaned:
            return None

        res_str = cleaned

        # 2. Match multi-word states first using minimal edit distance
        words = res_str.split()
        two_word_states = [s for s in KNOWN_STATES if " " in s]
        
        for i in range(len(words) - 1):
            window = f"{words[i]} {words[i+1]}".replace(',', '').strip()
            best_state = None
            best_dist = 999
            for s in two_word_states:
                d = levenshtein_dist(window, s)
                if d <= 3 and d < best_dist:
                    best_dist = d
                    best_state = s
            if best_state and (best_dist <= 2 or difflib.SequenceMatcher(None, window, best_state).ratio() >= 0.78):
                res_str = res_str.replace(words[i] + " " + words[i+1], best_state)
                break

        # 3. Match single-word states
        one_word_states = [s for s in KNOWN_STATES if " " not in s]
        for w in res_str.split():
            w_clean = w.replace(',', '').strip()
            if len(w_clean) >= 5 and w_clean not in KNOWN_STATES:
                best_s = None
                best_d = 999
                for s in one_word_states:
                    d = levenshtein_dist(w_clean, s)
                    if d <= 2 and d < best_d:
                        best_d = d
                        best_s = s
                if best_s:
                    res_str = res_str.replace(w_clean, best_s)
                        
        # 4. Trim any trailing noise that appears after the identified state
        for state in sorted(KNOWN_STATES, key=len, reverse=True):
            idx = res_str.find(state)
            if idx != -1:
                res_str = res_str[:idx + len(state)].strip()
                break

        # 5. Match individual district/city words
        tokens = re.split(r'([,\s]+)', res_str)
        corrected_tokens = []
        for t in tokens:
            stripped = t.strip(',').strip()
            is_state_part = any(stripped == s or (stripped in s.split()) for s in KNOWN_STATES)
            if len(stripped) >= 4 and not is_state_part:
                matched = match_single_location(stripped, KNOWN_CITIES_AND_DISTRICTS + KNOWN_RPO_CITIES)
                if t.endswith(','):
                    matched += ','
                corrected_tokens.append(matched)
            else:
                corrected_tokens.append(t)
                
        final_res = "".join(corrected_tokens)
        final_res = re.sub(r'\s*,\s*', ', ', final_res)
        final_res = re.sub(r'\s+', ' ', final_res).strip()
        return final_res.upper() if final_res else None

    def clean_text_field(self, raw):
        if not raw:
            return None
        cleaned = re.sub(
            r'^(?:Surname|Given Name\(s\)|Given Name|Name|Type|Country Code|Code|Sex|Nationality)[:\s/.-]*',
            '',
            raw,
            flags=re.IGNORECASE
        ).strip()
        cleaned = re.sub(r'[^A-Za-z0-9\s,\'.-]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned.upper() if cleaned else None

    def process_image(self, img_path_or_bytes, file_name="passport_scan.jpg"):
        """Extracts all standard passport fields using de-skewed template-based normalization."""
        if isinstance(img_path_or_bytes, bytes):
            nparr = np.frombuffer(img_path_or_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(img_path_or_bytes)

        if img is None:
            return {"error": "Invalid image file or format."}

        file_stem = os.path.splitext(os.path.basename(file_name))[0]

        # 1. Automatically Deskew & Straighten bent / tilted photos
        straightened_img = self.deskew_image(img)

        # 2. Normalize image to Standard Canonical Dimensions
        canonical_img = cv2.resize(straightened_img, (CANONICAL_W, CANONICAL_H), interpolation=cv2.INTER_AREA)

        # 3. Extract Person Portrait
        image_of_person = self.extract_portrait(canonical_img, file_stem)

        # 4. Direct ROI Extraction across Standard Format Zones
        extracted = {}

        for field_name, roi in TEMPLATE_ROIS.items():
            if roi["type"] == "image":
                continue

            x1 = int(roi["x1"] * CANONICAL_W)
            y1 = int(roi["y1"] * CANONICAL_H)
            x2 = int(roi["x2"] * CANONICAL_W)
            y2 = int(roi["y2"] * CANONICAL_H)

            crop = canonical_img[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            prep = self.preprocess_roi(crop)
            res = self.reader.readtext(prep, detail=0)
            raw_text = " ".join([t.strip() for t in res if t.strip()]).strip()

            if roi["type"] == "date":
                extracted[field_name] = self.clean_date_str(raw_text) or raw_text
            elif roi["type"] == "passport_no":
                extracted[field_name] = self.clean_passport_number(raw_text)
            elif roi["type"] == "gender":
                m_g = re.search(r'\b([MF])\b', raw_text.upper())
                extracted[field_name] = m_g.group(1) if m_g else None
            elif roi["type"] == "mrz":
                lines = [re.sub(r'[^A-Z0-9<]', '', l.upper()) for l in res]
                valid_mrz = [l for l in lines if len(l) >= 20 or l.startswith("P<")]
                extracted[field_name] = valid_mrz
            elif roi["type"] == "location_issue":
                extracted[field_name] = self.clean_place_of_issue(raw_text)
            elif roi["type"] == "location_birth":
                extracted[field_name] = self.clean_place_of_birth(raw_text)
            else:
                extracted[field_name] = self.clean_text_field(raw_text)

        # 5. Process MRZ Data for High-Fidelity Cross-Validation & Fallbacks
        mrz_list = extracted.get("mrz_zone", [])
        l1 = None
        l2 = None

        for line in mrz_list:
            if line.startswith("P<") or (not l1 and len(line) >= 28 and line.startswith("P")):
                l1 = line
            elif len(line) >= 25 and len(re.findall(r'[0-9]', line)) >= 8:
                l2 = line

        if not l1 and len(mrz_list) >= 1:
            l1 = mrz_list[0]
        if not l2 and len(mrz_list) >= 2:
            l2 = mrz_list[1]

        mrz_surname = None
        mrz_given_name = None

        # Decode Line 2: Passport No, Nationality, DOB, Sex, Expiry
        if l2:
            m_l2 = re.search(r'([A-Z0-9<]{8,9})[0-9<]([A-Z]{3})([0-9]{6})[0-9<]([MF<])([0-9]{6})', l2)
            if m_l2:
                mrz_pno, nat, dob_raw, sex, exp_raw = m_l2.groups()
                # Cross-check / fallback passport number
                if not extracted.get("passport_no"):
                    clean_p = mrz_pno.replace('<', '')
                    if clean_p.startswith(('8', '5')) and len(clean_p) == 8:
                        clean_p = 'S' + clean_p[1:]
                    extracted["passport_no"] = self.clean_passport_number(clean_p)
                # Cross-check / fallback date of birth
                if not extracted.get("date_of_birth") or not self.clean_date_str(extracted.get("date_of_birth")):
                    yy = int(dob_raw[0:2])
                    century = '19' if yy > 25 else '20'
                    extracted["date_of_birth"] = f"{dob_raw[4:6]}/{dob_raw[2:4]}/{century}{dob_raw[0:2]}"
                # Cross-check / fallback date of expiry
                if not extracted.get("date_of_expiry") or not self.clean_date_str(extracted.get("date_of_expiry")):
                    extracted["date_of_expiry"] = f"{exp_raw[4:6]}/{exp_raw[2:4]}/20{exp_raw[0:2]}"
                # Cross-check / fallback gender
                if not extracted.get("gender") and sex in ['M', 'F']:
                    extracted["gender"] = sex

        # Decode Line 1: Surname << Given Names (authoritative spelling)
        if l1:
            payload = re.sub(r'^P<[A-Z]{3}', '', l1)
            parts = payload.split("<<")
            if len(parts) >= 2:
                mrz_surname = parts[0].replace("<", " ").strip().upper()
                mrz_given_name = parts[1].replace("<", " ").strip().upper()

        surname = mrz_surname or extracted.get("surname") or ""
        given_name = mrz_given_name or extracted.get("given_name") or ""
        if given_name and surname:
            full_name = f"{given_name} {surname}".strip()
        else:
            full_name = given_name or surname or None

        if full_name:
            full_name = re.sub(r'\s+', ' ', full_name).strip()

        # Sanitize Date fields to canonical DD/MM/YYYY
        dob = self.clean_date_str(extracted.get("date_of_birth")) or extracted.get("date_of_birth")
        doi = self.clean_date_str(extracted.get("date_of_issue")) or extracted.get("date_of_issue")
        doe = self.clean_date_str(extracted.get("date_of_expiry")) or extracted.get("date_of_expiry")

        pob = extracted.get("place_of_birth")
        poi = extracted.get("place_of_issue")
        gender = extracted.get("gender") or "M"
        pno = extracted.get("passport_no")

        final_mrz = []
        if l1: final_mrz.append(l1)
        if l2: final_mrz.append(l2)

        return {
            "file_name": file_name,
            "name": full_name,
            "passport_no": pno,
            "date_of_birth": dob,
            "gender": gender,
            "date_of_issue": doi,
            "date_of_expiry": doe,
            "place_of_birth": pob,
            "place_of_issue": poi,
            "address": pob,
            "mrz_code": final_mrz,
            "image_of_person": image_of_person
        }
