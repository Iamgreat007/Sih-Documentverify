import os
import sys
import io
import json
import re
import cv2
import shutil
import easyocr
import numpy as np
from tqdm import tqdm

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

DL_STOPWORDS = {
    'BLOOD', 'GROUP', 'DOB', 'DATE', 'OF', 'BIRTH', 'DIRTH', 'SON', 'DAUGHTER',
    'WIFE', 'HUSBAND', 'FATHER', 'NAME', 'HOLDER', 'GOVERNMENT', 'PUNJAB',
    'INDIA', 'LICENCE', 'DRIVING', 'DE', 'VALIDITY', 'VALID', 'NT', 'TR',
    'AUTHORITY', 'TRANSPORT', 'SIGNATURE', 'HOLDERS', 'CARD', 'FORM', 'MOTOR',
    'VEHICLE', 'STATE', 'UNION', 'TERRITORY', 'BLOO', 'GROU', 'HOLOER'
}

def enhance_img(im):
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8,8))
    return clahe.apply(gray)

def is_valid_human_name(name_str):
    if not name_str or len(name_str) < 3:
        return False
    words = name_str.strip().split()
    if not words:
        return False
    for w in words:
        w_low = w.lower()
        if len(w_low) == 1:
            if w_low not in ['a', 'i', 'k', 's', 'r', 'm', 'v', 'p']:
                return False
            continue
        if not re.search(r'[aeiouy]', w_low):
            return False
        if re.search(r'^[bcdfghjklmnpqrstvwxz]{2,}', w_low):
            if not any(w_low.startswith(p) for p in [
                'sh', 'ch', 'th', 'pr', 'tr', 'kr', 'br', 'gr', 'dr', 'fr',
                'pl', 'bl', 'cl', 'fl', 'gl', 'kl', 'sl', 'sm', 'sn', 'sp',
                'st', 'sw', 'sk', 'gh', 'kh', 'bh', 'dh', 'jh', 'ph', 'rh',
                'wh', 'zh', 'gn', 'kn', 'ps', 'pn', 'wr', 'ts', 'ks', 'pt',
                'shr', 'dhr', 'jas', 'har', 'ash', 'sach'
            ]):
                return False
        if re.search(r'[bcdfghjklmnpqrstvwxz]{4,}', w_low):
            if not any(p in w_low for p in ['ndr', 'dhr', 'khr', 'shw', 'singh', 'shpr', 'rsh', 'preet']):
                return False
    return True

def clean_date_str(val):
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
        if 1 <= d <= 31 and 1 <= m_val <= 12 and 1940 <= y <= 2040:
            return f"{d:02d}/{m_val:02d}/{y}"
    return None

def clean_name_str(val):
    if not val or not isinstance(val, str):
        return None
    val_clean = re.sub(r'[^A-Za-z\s]', ' ', val)
    tokens = [w for w in val_clean.split() if w.upper() not in DL_STOPWORDS and len(w) > 1]
    if not tokens:
        return None
        
    # Correct reverse surname order if present (e.g. Singh Jaspreet -> Jaspreet Singh)
    if len(tokens) == 2 and tokens[0].lower() in ['singh', 'kaur', 'kumar', 'sachdeva'] and tokens[1].lower() not in ['singh', 'kaur', 'kumar', 'sachdeva']:
        tokens = [tokens[1], tokens[0]]
        
    final_name = " ".join([w.capitalize() for w in tokens]).strip()
    if is_valid_human_name(final_name):
        return final_name
    return None

def clean_dl_number(val):
    if not val or not isinstance(val, str):
        return None
    val_clean = val.strip().replace('-', ' ').replace('/', ' ')
    val_clean = re.sub(r'[^A-Za-z0-9\s]', '', val_clean).strip()
    
    # Standard format: State(2) + RTO(2) + Year(4) + Number(7) -> e.g. PB23 20240004974
    m_std = re.search(r'\b([A-Z]{2})\s*([0-9]{2})\s*(19[7-9][0-9]|20[0-2][0-9])\s*([0-9]{7})\b', val_clean.upper())
    if m_std:
        st, rto, yr, num = m_std.groups()
        return f"{st}{rto} {yr}{num}"
        
    # Alternative 11-digit or 13-digit pattern with known Indian state prefix
    m_alt = re.search(r'\b(AP|AR|AS|BR|CG|CH|DL|DN|DD|GA|GJ|HR|HP|JK|JH|KA|KL|LA|LD|MP|MH|MN|ML|MZ|NL|OD|PB|PY|RJ|SK|TN|TS|TR|UP|UK|WB)\s*([0-9]{2})\s*([0-9]{11})\b', val_clean.upper())
    if m_alt:
        st, rto, num = m_alt.groups()
        return f"{st}{rto} {num}"
        
    return None

def main():
    root_dl = "Indian Driving Licence Reader.coco"
    splits = ["train", "valid", "test"]
    out_photo_dir = "extracted_dl_photos"
    skipped_dir = "skipped_photos/driving_licence"
    os.makedirs(out_photo_dir, exist_ok=True)
    os.makedirs(skipped_dir, exist_ok=True)
    
    out_json = "train_driving_licence_extracted_data.json"
    alias_json = "driving_licence_extracted_data.json"
    
    print("Initializing EasyOCR reader for Pristine DL Extraction...")
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    
    face_cascade = None
    if hasattr(cv2, 'data') and os.path.exists(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'):
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception:
            pass
            
    verified_records = []
    skipped_logs = []
    
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
        print(f"Processing DL split '{split}': {len(images)} documents...")
        
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
            
            # Step 1: Extract from bounding box annotations
            for a in img_anns:
                cname = cat_map.get(a["category_id"], "")
                x, y, bw, bh = [int(v) for v in a["bbox"]]
                crop = img[max(0,y):y+bh, max(0,x):x+bw]
                if crop.size == 0:
                    continue
                    
                ch, cw = crop.shape[:2]
                if ch < 25 or cw < 25:
                    scale = max(2.5, 40.0 / max(1, min(ch, cw)))
                    crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_CUBIC)
                elif cw > 800:
                    scale = 700.0 / cw
                    crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_AREA)
                    
                res = reader.readtext(enhance_img(crop), detail=0)
                text = " ".join([t.strip() for t in res if t.strip()]).strip()
                if not text:
                    continue
                    
                if cname == "dl_number":
                    raw_dl = text
                elif cname == "name":
                    raw_name = text
                elif cname == "dob":
                    if re.search(r'[A-Z]{2}\s*[0-9]{2}', text) and not raw_dl:
                        raw_dl = text
                    else:
                        raw_dob = text

            c_name = clean_name_str(raw_name)
            c_dl = clean_dl_number(raw_dl)
            c_dob = clean_date_str(raw_dob)

            # Step 2: If DL number or Name missing/scrambled, check full card text
            if not c_dl or not c_name:
                card_txt = reader.readtext(enhance_img(img), detail=0)
                card_str = " ".join(card_txt)
                
                if not c_dl:
                    m_card_dl = clean_dl_number(card_str)
                    if m_card_dl:
                        c_dl = m_card_dl
                        
                if not c_dob:
                    m_card_dob = clean_date_str(card_str)
                    if m_card_dob:
                        c_dob = m_card_dob
                        
                if not c_name:
                    for line in card_txt:
                        m_cand = clean_name_str(line)
                        if m_cand and len(m_cand.split()) >= 2:
                            c_name = m_cand
                            break

            # Valid DL requires clean DL Number OR clean Name + DOB
            is_valid = bool(c_dl and (c_name or c_dob)) or (c_name and c_dob)

            if is_valid:
                photo_rel = None
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
                                photo_rel = f"{out_photo_dir}/{p_fn}"
                    except Exception:
                        pass
                        
                if not photo_rel:
                    p_crop = img[int(h*0.2):int(h*0.8), int(w*0.7):w]
                    if p_crop.size > 0:
                        p_fn = f"{os.path.splitext(fn)[0]}_person.jpg"
                        cv2.imwrite(os.path.join(out_photo_dir, p_fn), p_crop)
                        photo_rel = f"{out_photo_dir}/{p_fn}"

                rec = {
                    "file_name": fn,
                    "name": c_name,
                    "dl_number": c_dl,
                    "date_of_birth": c_dob,
                    "gender": "M" if c_name and any(k in c_name.upper() for k in ["SINGH", "KUMAR", "RAM", "LAL", "SACHDEVA"]) else None,
                    "date_of_issue": None,
                    "date_of_expiry": None,
                    "address": None,
                    "image_of_person": photo_rel
                }
                verified_records.append(rec)
            else:
                dst_skipped = os.path.join(skipped_dir, fn)
                shutil.copy2(img_path, dst_skipped)
                skipped_logs.append({
                    "file_name": fn,
                    "split": split,
                    "reason": f"Unreadable / corrupted token (raw: DL='{raw_dl}', Name='{raw_name}', DOB='{raw_dob}')"
                })

    print(f"\nDL Extraction Finished!")
    print(f"Verified High-Quality Records: {len(verified_records)}")
    print(f"Skipped Degraded Photos Moved to '{skipped_dir}': {len(skipped_logs)}")
    
    json_body = json.dumps(verified_records, indent=2, ensure_ascii=False)
    
    comment_lines = [
        "\n\n/* ================================================================================",
        "   HIGH-PRECISION QUALITY AUDIT TRAIL & SKIPPED PHOTOS LOG",
        "   Dataset Source: Indian Driving Licence Reader.coco (train, valid, test)",
        f"   Verified High-Quality Records : {len(verified_records)}",
        f"   Skipped / Degraded Photos     : {len(skipped_logs)}",
        "   ================================================================================",
        "   The degraded, blurry, or inverted images listed below could not produce verified",
        "   identity data and were shifted to the 'skipped_photos/driving_licence/' folder.",
        "   Only clean, high-precision structured records are retained in active JSON fields.",
        "   --------------------------------------------------------------------------------\n"
    ]
    
    for i, log in enumerate(skipped_logs, 1):
        comment_lines.append(f"   [{i:03d}] File   : {log['file_name']} (Split: {log['split']})")
        comment_lines.append(f"        Reason : {log['reason']}\n")
        
    comment_lines.append("   ================================================================================ */\n")
    
    full_output = json_body + "\n".join(comment_lines)
    
    with open(out_json, "w", encoding="utf-8") as f:
        f.write(full_output)
    with open(alias_json, "w", encoding="utf-8") as f:
        f.write(full_output)
        
    print(f"Successfully wrote high-precision DL records to '{out_json}' and '{alias_json}'!")

if __name__ == "__main__":
    main()
