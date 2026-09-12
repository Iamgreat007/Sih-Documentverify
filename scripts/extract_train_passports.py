import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
import cv2
import easyocr
import re
import numpy as np
from tqdm import tqdm

def main():
    train_dir = "Dataset/Passport data prediction.coco/train"
    ann_file = os.path.join(train_dir, "_annotations.coco.json")
    photos_out_dir = "extracted_train_photos"
    os.makedirs(photos_out_dir, exist_ok=True)
    output_json_path = "train_passport_extracted_data.json"

    print("Initializing EasyOCR reader (CPU mode)...")
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    print("EasyOCR ready!")

    if not os.path.exists(ann_file):
        print(f"Error: {ann_file} not found!")
        return

    with open(ann_file, "r", encoding="utf-8") as f:
        coco = json.load(f)

    cat_map = {c["id"]: c["name"] for c in coco["categories"]}
    
    # Map annotations by image_id
    anns_by_img = {}
    for a in coco.get("annotations", []):
        img_id = a["image_id"]
        anns_by_img.setdefault(img_id, []).append(a)

    images = coco.get("images", [])
    print(f"Total passport images to process: {len(images)}")

    all_extracted_records = []

    def extract_date(text):
        if not text:
            return None
        m = re.search(r'([0-9]{2}[/\-.][0-9]{2}[/\-.][0-9]{4}|[0-9]{2}\s+[A-Za-z]{3}\s+[0-9]{4})', text)
        if m:
            return m.group(1).replace(".", "/").replace("-", "/")
        return None

    def clean_mrz_line(raw):
        c = re.sub(r'[^A-Z0-9<]', '', raw.upper())
        return c

    for idx, img_info in enumerate(tqdm(images, desc="Extracting Passport Data")):
        file_name = img_info["file_name"]
        img_path = os.path.join(train_dir, file_name)
        img_id = img_info["id"]

        if not os.path.exists(img_path):
            continue

        img = cv2.imread(img_path)
        if img is None:
            continue

        h, w = img.shape[:2]
        img_anns = anns_by_img.get(img_id, [])

        extracted = {
            "file_name": file_name,
            "name": None,
            "passport_no": None,
            "date_of_birth": None,
            "gender": None,
            "date_of_issue": None,
            "date_of_expiry": None,
            "place_of_birth": None,
            "address": None,
            "mrz_code": [],
            "image_of_person": None
        }

        first_name = ""
        surname = ""
        mrz_candidates = []

        # Process Bounding Box Annotations
        for a in img_anns:
            cname = cat_map.get(a["category_id"], "")
            bbox = a["bbox"]
            x, y, bw, bh = [int(v) for v in bbox]
            x = max(0, x)
            y = max(0, y)
            bw = min(w - x, bw)
            bh = min(h - y, bh)

            if bw <= 0 or bh <= 0:
                continue

            crop = img[y:y+bh, x:x+bw]
            if crop.size == 0:
                continue

            if cname == "photo":
                photo_filename = f"{os.path.splitext(file_name)[0]}_person.jpg"
                photo_rel_path = f"{photos_out_dir}/{photo_filename}"
                photo_disk_path = os.path.join(photos_out_dir, photo_filename)
                cv2.imwrite(photo_disk_path, crop)
                extracted["image_of_person"] = photo_rel_path
            else:
                # Resize crop if too small or too huge for OCR
                ch, cw = crop.shape[:2]
                if ch < 30 or cw < 30:
                    scale = max(2.0, 40.0 / min(ch, cw))
                    crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_CUBIC)
                elif cw > 1200:
                    scale = 1000.0 / cw
                    crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_AREA)

                ocr_res = reader.readtext(crop, detail=0)
                text = " ".join([t.strip() for t in ocr_res if t.strip()]).strip()
                if not text:
                    continue

                if cname == "name":
                    first_name = text if not first_name else f"{first_name} {text}"
                elif cname == "Surname":
                    surname = text
                elif cname == "DOB":
                    extracted["date_of_birth"] = extract_date(text) or text
                elif cname == "ExpiryDate":
                    extracted["date_of_expiry"] = extract_date(text) or text
                elif cname == "passport number":
                    if "<" in text or len(text) > 15:
                        mrz_candidates.append(clean_mrz_line(text))
                    else:
                        p_match = re.search(r'([A-Z][0-9]{7,8}|[A-Z0-9]{8,9})', text)
                        if p_match:
                            extracted["passport_no"] = p_match.group(1)
                        else:
                            extracted["passport_no"] = text
                elif "Address" in cname:
                    extracted["address"] = text if not extracted["address"] else f"{extracted['address']}, {text}"
                elif cname == "total name":
                    mrz_candidates.append(clean_mrz_line(text))

        # Combine name
        if first_name and surname:
            extracted["name"] = f"{first_name} {surname}".strip()
        elif first_name:
            extracted["name"] = first_name
        elif surname:
            extracted["name"] = surname

        # Quick OCR on bottom strip (MRZ area)
        h_bot = int(h * 0.70)
        bot_crop = img[h_bot:h, 0:w]
        bh_c, bw_c = bot_crop.shape[:2]
        if bw_c > 1000:
            scale = 1000.0 / bw_c
            bot_crop = cv2.resize(bot_crop, (int(bw_c * scale), int(bh_c * scale)), interpolation=cv2.INTER_AREA)

        bot_ocr = reader.readtext(bot_crop, detail=0)
        for line in bot_ocr:
            clean_l = clean_mrz_line(line)
            if len(clean_l) >= 20 or clean_l.startswith("P<") or "<" in clean_l:
                mrz_candidates.append(clean_l)

        # Filter MRZ Line 1 and Line 2
        l1 = None
        l2 = None
        for mc in mrz_candidates:
            if mc.startswith("P<") and not l1:
                l1 = mc
            elif re.search(r'[0-9]{6}', mc) and len(mc) >= 20 and not l2:
                l2 = mc

        final_mrz = []
        if l1:
            final_mrz.append(l1)
        if l2:
            final_mrz.append(l2)
        extracted["mrz_code"] = final_mrz

        # Parse MRZ lines for exact decoded values
        for line in final_mrz:
            if line.startswith("P<") and not extracted["name"]:
                parts = line[5:].split("<<")
                if len(parts) >= 2:
                    s = parts[0].replace("<", " ").strip()
                    g = parts[1].replace("<", " ").strip()
                    extracted["name"] = f"{g} {s}".strip()

            m_l2 = re.search(r'([A-Z0-9<]{8,9})[0-9<]([A-Z]{3})([0-9]{6})[0-9<]([MF<])([0-9]{6})', line)
            if m_l2:
                p_no, nat, dob_raw, sex, exp_raw = m_l2.groups()
                if not extracted["passport_no"]:
                    extracted["passport_no"] = p_no.replace("<", "")
                if not extracted["gender"] and sex in ['M', 'F']:
                    extracted["gender"] = "M" if sex == 'M' else "F"
                if not extracted["date_of_birth"]:
                    yy = int(dob_raw[0:2])
                    century = "19" if yy > 25 else "20"
                    extracted["date_of_birth"] = f"{dob_raw[4:6]}/{dob_raw[2:4]}/{century}{dob_raw[0:2]}"
                if not extracted["date_of_expiry"]:
                    extracted["date_of_expiry"] = f"{exp_raw[4:6]}/{exp_raw[2:4]}/20{exp_raw[0:2]}"

        # If Place of Birth not set, use Address location if present
        if not extracted["place_of_birth"] and extracted["address"]:
            # Often address contains city/state
            addr_parts = [p.strip() for p in extracted["address"].split(",") if p.strip()]
            if addr_parts:
                extracted["place_of_birth"] = addr_parts[-1]

        # If photo wasn't found in annotations, use Haar cascade / center crop fallback
        if not extracted["image_of_person"]:
            # Check left side portrait zone (typical passport standard: 0.1w to 0.4w, 0.15h to 0.65h)
            fx, fy, fw, fh = int(w * 0.05), int(h * 0.15), int(w * 0.35), int(h * 0.50)
            crop_fb = img[fy:fy+fh, fx:fx+fw]
            if crop_fb.size > 0:
                photo_filename = f"{os.path.splitext(file_name)[0]}_person.jpg"
                photo_rel_path = f"{photos_out_dir}/{photo_filename}"
                photo_disk_path = os.path.join(photos_out_dir, photo_filename)
                cv2.imwrite(photo_disk_path, crop_fb)
                extracted["image_of_person"] = photo_rel_path

        all_extracted_records.append(extracted)

        # Save progress every 25 images
        if (idx + 1) % 25 == 0 or (idx + 1) == len(images):
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(all_extracted_records, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully extracted data for {len(all_extracted_records)} images.")
    print(f"Saved JSON to: {output_json_path}")
    print(f"Saved person photos to: {photos_out_dir}/")

if __name__ == "__main__":
    main()
