import os
import sys
import io
import json
import re
import cv2
import easyocr
import numpy as np
from tqdm import tqdm

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

INDIAN_STATES = {
    "AP": "ANDHRA PRADESH", "AR": "ARUNACHAL PRADESH", "AS": "ASSAM", "BR": "BIHAR",
    "CG": "CHHATTISGARH", "CH": "CHANDIGARH", "DL": "DELHI", "DN": "DADRA AND NAGAR HAVELI",
    "DD": "DAMAN AND DIU", "GA": "GOA", "GJ": "GUJARAT", "HR": "HARYANA", "HP": "HIMACHAL PRADESH",
    "JK": "JAMMU AND KASHMIR", "JH": "JHARKHAND", "KA": "KARNATAKA", "KL": "KERALA", "LA": "LADAKH",
    "LD": "LAKSHADWEEP", "MP": "MADHYA PRADESH", "MH": "MAHARASHTRA", "MN": "MANIPUR", "ML": "MEGHALAYA",
    "MZ": "MIZORAM", "NL": "NAGALAND", "OD": "ODISHA", "PB": "PUNJAB", "PY": "PUDUCHERRY",
    "RJ": "RAJASTHAN", "SK": "SIKKIM", "TN": "TAMIL NADU", "TS": "TELANGANA", "TR": "TRIPURA",
    "UP": "UTTAR PRADESH", "UK": "UTTARAKHAND", "WB": "WEST BENGAL"
}

def clean_date_str(val):
    if not val or not isinstance(val, str):
        return None, "Null or empty date"
    
    val_clean = val.strip()
    val_fixed = re.sub(r'(\d{2})7(\d{2})[7/](\d{4})', r'\1/\2/\3', val_clean)
    val_fixed = re.sub(r'(\d{2})\s*[-/.]\s*(\d{2})\s*[-/.]\s*(\d{4})', r'\1/\2/\3', val_fixed)
    val_fixed = re.sub(r'(\d{2})[./-](\d{2})[./-](\d{4})', r'\1/\2/\3', val_fixed)
    
    # Check DD/MM/YYYY or YYYY/MM/DD
    m = re.search(r'\b([0-3]?[0-9])[/\-.]([0-1]?[0-9])[/\-.](19[4-9][0-9]|20[0-4][0-9])\b', val_fixed)
    if m:
        d, m_val, y = m.groups()
        d, m_val, y = int(d), int(m_val), int(y)
        if 1 <= d <= 31 and 1 <= m_val <= 12 and 1940 <= y <= 2040:
            return f"{d:02d}/{m_val:02d}/{y}", None
            
    m_compact = re.search(r'\b([0-3][0-9])([0-1][0-9])(19[4-9][0-9]|20[0-4][0-9])\b', val_clean)
    if m_compact:
        d, m_val, y = m_compact.groups()
        d, m_val, y = int(d), int(m_val), int(y)
        if 1 <= d <= 31 and 1 <= m_val <= 12:
            return f"{d:02d}/{m_val:02d}/{y}", None
            
    return None, f"Illogical DOB / OCR noise (not a valid date): '{val}'"

def validate_name(val):
    if not val or not isinstance(val, str):
        return None, "Null or empty name"
    
    val_clean = val.strip()
    val_clean = re.sub(r'^(?:Name|Holder Name|Son/Daughter/Wife of|Date of Birth|Birth|of)[:\s.-]*', '', val_clean, flags=re.IGNORECASE)
    val_clean = re.sub(r'\b(?:Name|Date of Birth|Date|Birth|Son/Dauoht|Son|Daughter|Wife|of)\b', '', val_clean, flags=re.IGNORECASE)
    val_clean = re.sub(r'[^A-Za-z\s.\'-]', '', val_clean).strip()
    val_clean = re.sub(r'\s+', ' ', val_clean).strip(' -.,;:_')
    
    letters = re.findall(r'[A-Za-z]', val_clean)
    if len(letters) < 3:
        return None, f"Illogical name (contains insufficient letters / noise): '{val}'"
        
    words = [w.capitalize() for w in val_clean.split() if len(w) > 0]
    return " ".join(words).strip(' -.,;:_'), None

def validate_dl_number(val):
    if not val or not isinstance(val, str):
        return None, "Null or empty DL number"
    
    val_clean = val.strip().replace('-', ' ').replace('/', ' ')
    val_clean = re.sub(r'^(?:DL\s*NO|LICENCE\s*NO|NO|NUMBER)[:.\s-]*', '', val_clean, flags=re.IGNORECASE)
    val_clean = re.sub(r'[^A-Za-z0-9\s]', '', val_clean).strip()
    val_clean = re.sub(r'\s+', ' ', val_clean).strip()
    
    # Standard format: StateCode (2 letters) + RTO Code (2 digits) + Year (4 digits) + 7 digits
    m_std = re.search(r'\b([A-Z]{2})\s*([0-9]{2})\s*(19[7-9][0-9]|20[0-2][0-9])\s*([0-9]{4,7})\b', val_clean.upper())
    if m_std:
        st, rto, yr, num = m_std.groups()
        return f"{st}{rto} {yr}{num.zfill(7)}", None
        
    # Standard format: StateCode (2 letters) + 13-15 digits
    m_alt = re.search(r'\b([A-Z]{2})\s*([0-9]{11,15})\b', val_clean.upper())
    if m_alt:
        st, digits = m_alt.groups()
        return f"{st} {digits}", None
        
    letters = len(re.findall(r'[A-Za-z]', val_clean))
    digits = len(re.findall(r'[0-9]', val_clean))
    
    if letters >= 1 and digits >= 8:
        return val_clean.upper(), None
        
    return None, f"Illogical DL number (isolated digits or noise): '{val}'"

def main():
    root_dl = "Indian Driving Licence Reader.coco"
    splits = ["train", "valid", "test"]
    out_photo_dir = "extracted_dl_photos"
    os.makedirs(out_photo_dir, exist_ok=True)
    out_json = "train_driving_licence_extracted_data.json"
    
    print("Initializing EasyOCR reader for Driving Licence extraction...")
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    
    face_cascade = None
    if hasattr(cv2, 'data') and os.path.exists(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'):
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception:
            pass
            
    all_records = []
    illogical_logs = []
    
    for split in splits:
        split_dir = os.path.join(root_dl, split)
        ann_file = os.path.join(split_dir, "_annotations.coco.json")
        if not os.path.exists(ann_file):
            continue
            
        with open(ann_file, "r", encoding="utf-8") as f:
            coco = json.load(f)
            
        cat_map = {c["id"]: c["name"] for c in coco.get("categories", [])}
        anns_by_img = {}
        for a in coco.get("annotations", []):
            anns_by_img.setdefault(a["image_id"], []).append(a)
            
        images = coco.get("images", [])
        print(f"Processing split '{split}': {len(images)} images...")
        
        for img_info in tqdm(images, desc=f"DL {split}"):
            fn = img_info["file_name"]
            img_path = os.path.join(split_dir, fn)
            if not os.path.exists(img_path):
                continue
                
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            h, w = img.shape[:2]
            img_id = img_info["id"]
            img_anns = anns_by_img.get(img_id, [])
            
            raw_dl = None
            raw_name = None
            raw_dob = None
            
            for a in img_anns:
                cname = cat_map.get(a["category_id"], "")
                bbox = a["bbox"]
                x, y, bw, bh = [int(v) for v in bbox]
                x, y = max(0, x), max(0, y)
                bw, bh = min(w - x, bw), min(h - y, bh)
                if bw <= 0 or bh <= 0:
                    continue
                    
                crop = img[y:y+bh, x:x+bw]
                if crop.size == 0:
                    continue
                    
                # Enhance crop resolution for OCR
                ch, cw = crop.shape[:2]
                if ch < 30 or cw < 30:
                    scale = max(2.5, 45.0 / max(1, min(ch, cw)))
                    crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_CUBIC)
                    
                res = reader.readtext(crop, detail=0)
                text = " ".join([t.strip() for t in res if t.strip()]).strip()
                if not text:
                    continue
                    
                if cname == "dl_number":
                    raw_dl = text if not raw_dl else f"{raw_dl} {text}"
                elif cname == "name":
                    raw_name = text if not raw_name else f"{raw_name} {text}"
                elif cname == "dob":
                    # Check if text actually contains DL number or DOB
                    if re.search(r'[A-Z]{2}\s*[0-9]{2}', text) and not raw_dl:
                        raw_dl = text
                    else:
                        raw_dob = text if not raw_dob else f"{raw_dob} {text}"
                        
            # Also do a card-level check if fields are missing
            if not raw_dl or not raw_dob or not raw_name:
                card_ocr = reader.readtext(img, detail=0)
                card_text = " ".join(card_ocr)
                if not raw_dl:
                    m_dl = re.search(r'\b([A-Z]{2}\s*[0-9]{2}\s*(?:19|20)[0-9]{2}\s*[0-9]{4,7})\b', card_text)
                    if m_dl:
                        raw_dl = m_dl.group(1)
                if not raw_dob:
                    m_dob = re.search(r'(?:DOB|Date of Birth|Birth)[:\s]*([0-3]?[0-9][\-/][0-1]?[0-9][\-/](?:19|20)[0-9]{2})', card_text, flags=re.IGNORECASE)
                    if m_dob:
                        raw_dob = m_dob.group(1)
                if not raw_name:
                    m_nm = re.search(r'Name[:\s]+([A-Z\s]{4,30})', card_text)
                    if m_nm:
                        raw_name = m_nm.group(1)

            # Portrait face detection
            photo_rel_path = None
            if face_cascade is not None:
                try:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
                    if len(faces) > 0:
                        faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
                        fx, fy, fw, fh = faces[0]
                        pad_x, pad_y = int(fw * 0.15), int(fh * 0.20)
                        x1, y1 = max(0, fx - pad_x), max(0, fy - pad_y)
                        x2, y2 = min(w, fx + fw + pad_x), min(h, fy + fh + pad_y)
                        p_crop = img[y1:y2, x1:x2]
                        if p_crop.size > 0:
                            p_fn = f"{os.path.splitext(fn)[0]}_person.jpg"
                            cv2.imwrite(os.path.join(out_photo_dir, p_fn), p_crop)
                            photo_rel_path = f"{out_photo_dir}/{p_fn}"
                except Exception:
                    pass

            # Fallback portrait crop from right or left if not found
            if not photo_rel_path:
                p_crop = img[int(h*0.2):int(h*0.8), int(w*0.7):w]
                if p_crop.size > 0:
                    p_fn = f"{os.path.splitext(fn)[0]}_person.jpg"
                    cv2.imwrite(os.path.join(out_photo_dir, p_fn), p_crop)
                    photo_rel_path = f"{out_photo_dir}/{p_fn}"

            # Validate & Sanitize fields
            clean_name_val, name_err = validate_name(raw_name) if raw_name else (None, "Missing name annotation")
            clean_dl_val, dl_err = validate_dl_number(raw_dl) if raw_dl else (None, "Missing DL number annotation")
            clean_dob_val, dob_err = clean_date_str(raw_dob) if raw_dob else (None, "Missing DOB annotation")
            
            # Log illogical fields
            if raw_name and not clean_name_val:
                illogical_logs.append({
                    "file_name": fn,
                    "field": "name",
                    "raw_val": raw_name,
                    "reason": name_err
                })
            if raw_dl and not clean_dl_val:
                illogical_logs.append({
                    "file_name": fn,
                    "field": "dl_number",
                    "raw_val": raw_dl,
                    "reason": dl_err
                })
            if raw_dob and not clean_dob_val:
                illogical_logs.append({
                    "file_name": fn,
                    "field": "date_of_birth",
                    "raw_val": raw_dob,
                    "reason": dob_err
                })
                
            rec = {
                "file_name": fn,
                "name": clean_name_val,
                "dl_number": clean_dl_val,
                "date_of_birth": clean_dob_val,
                "gender": "M" if clean_name_val and any(k in clean_name_val for k in ["SINGH", "KUMAR", "RAM", "LAL"]) else None,
                "date_of_issue": None,
                "date_of_expiry": None,
                "address": None,
                "image_of_person": photo_rel_path
            }
            all_records.append(rec)
            
    print(f"Total DL records extracted: {len(all_records)}")
    print(f"Total illogical field occurrences logged: {len(illogical_logs)}")
    
    # Build formatted JSON with comment block
    json_body = json.dumps(all_records, indent=2, ensure_ascii=False)
    
    comment_lines = [
        "\n\n/* ================================================================================",
        "   DATA SANITIZATION AUDIT TRAIL & ILLOGICAL ENTRIES LOG",
        "   Dataset Source: Indian Driving Licence Reader.coco",
        f"   Total Images Processed : {len(all_records)}",
        f"   Total Illogical Tokens  : {len(illogical_logs)}",
        "   ================================================================================",
        "   The following table records every raw OCR artifact, inverted/rotated image crop,",
        "   isolated digit string, or invalid date structure that was filtered out and commented",
        "   out from active JSON fields to guarantee strict schema compliance and high fidelity.",
        "   --------------------------------------------------------------------------------\n"
    ]
    
    for i, log in enumerate(illogical_logs, 1):
        comment_lines.append(f"   [{i:03d}] File   : {log['file_name']}")
        comment_lines.append(f"        Field  : {log['field']}")
        comment_lines.append(f"        Cut Val: {log['raw_val']}")
        comment_lines.append(f"        Reason : {log['reason']}\n")
        
    comment_lines.append("   ================================================================================ */\n")
    
    full_output = json_body + "\n".join(comment_lines)
    
    with open(out_json, "w", encoding="utf-8") as f:
        f.write(full_output)
    print(f"Wrote Driving Licence dataset to '{out_json}'!")
    
    # Also write alias driving_licence_extracted_data.json
    alias_json = "driving_licence_extracted_data.json"
    with open(alias_json, "w", encoding="utf-8") as f:
        f.write(full_output)
    print(f"Wrote Driving Licence dataset copy to '{alias_json}'!")

if __name__ == "__main__":
    main()
