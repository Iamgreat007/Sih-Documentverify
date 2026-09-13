import cv2
import re
import numpy as np
from typing import Dict, Any, Optional, Tuple, List

from src.side_router import DocumentSideRules

class DocumentRegionCropper:
    """
    Universal Document Region Cropper:
    Detects and crops Photo Box, QR Code / Barcode Box, Address Region, and MRZ Zone
    across all identity documents (Aadhaar, Passport, Driving Licence, Visa).
    Includes side-aware scanning rules (front, back, full_page) and subtype layout positioning.
    """

    @classmethod
    def detect_aadhaar_subtype(cls, image: np.ndarray, text_blocks: Optional[List[Dict[str, Any]]] = None, raw_text: str = "") -> str:
        """
        Classifies Aadhaar card image into one of 5 physical layout subtypes based on image dimensions and text anchors.
        """
        if image is None or len(image.shape) < 2:
            return "unknown"

        h, w = image.shape[:2]
        aspect_ratio = float(w) / float(h)
        text_up = raw_text.upper() if raw_text else ""

        # 1. Full e-Aadhaar A4 Letter (H >> W, aspect ratio <= 0.88 or text anchors)
        if aspect_ratio <= 0.88 or (h > 1.15 * w and any(k in text_up for k in ["UNIQUE IDENTIFICATION", "ENROLMENT NO", "TO:", "ISSUE DATE", "DOWNLOAD DATE"])):
            return "full_e_aadhaar"

        # 2. Cut-Out Dual Card (W >> H, aspect ratio >= 1.70)
        if aspect_ratio >= 1.70:
            return "cut_out_dual_card"

        # 3. Vertical Stacked Dual Card (H > W, aspect ratio 0.88 to 1.18)
        if 0.88 < aspect_ratio < 1.18:
            return "stacked_dual_card"

        # 4. Single Horizontal Card (W > H, aspect ratio 1.18 to 1.70)
        has_face = cls._detect_face_presence(image)
        has_address = any(k in text_up for k in ["ADDRESS", " पता", "S/O", "C/O", "W/O", "D/O", "PIN"])

        if has_address and not has_face:
            return "single_card_back"
        elif has_face and not has_address:
            return "single_card_front"
        elif has_face:
            return "single_card_front"
        elif has_address:
            return "single_card_back"

        return "single_card_front"

    @classmethod
    def _detect_face_presence(cls, image: np.ndarray) -> bool:
        """Helper to check if image contains a face photo."""
        if image is None or image.size == 0:
            return False
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        cascade_files = ['haarcascade_frontalface_default.xml', 'haarcascade_frontalface_alt2.xml', 'haarcascade_profileface.xml']
        for cascade_name in cascade_files:
            try:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_name)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=2, minSize=(20, 20))
                if len(faces) > 0:
                    return True
            except Exception:
                continue
        return False

    @classmethod
    def crop_document_components(cls, image: np.ndarray, doc_type: str = "unknown", side: str = "auto", qr_info: Optional[Dict[str, Any]] = None, text_blocks: Optional[List[Dict[str, Any]]] = None, raw_text: str = "") -> Dict[str, Optional[np.ndarray]]:
        """
        Crops and returns dictionary of extracted visual components:
        {'photo': np.ndarray, 'qr': np.ndarray, 'address': np.ndarray, 'mrz_zone': np.ndarray, 'subtype': str}
        Strictly enforces DocumentSideRules to prevent searching for QR on non-QR sides/documents.
        """
        if image is None or len(image.shape) < 2:
            return {"photo": None, "qr": None, "address": None, "mrz_zone": None, "subtype": "unknown"}

        subtype = "unknown"
        if doc_type.lower() in ("aadhaar", "uidai", "unknown"):
            subtype = cls.detect_aadhaar_subtype(image, text_blocks, raw_text)

        # Auto-infer side if side == "auto"
        effective_side = side
        if side == "auto":
            if doc_type.lower() in ("passport", "visa"):
                effective_side = "front"
            elif subtype == "single_card_front":
                effective_side = "front"
            elif subtype == "single_card_back":
                effective_side = "back"
            else:
                effective_side = "full_page"

        rules = DocumentSideRules.get_rules(doc_type, side=effective_side)

        # 1. Face photo crop (if allowed by side rules)
        photo_crop, photo_bbox = (None, None)
        if rules.get("extract_photo", True):
            photo_crop, photo_bbox = cls.crop_face_photo_with_bbox(image, doc_type=doc_type, subtype=subtype, text_blocks=text_blocks)

        # 2. QR code crop (ONLY if allowed by side rules, e.g. disabled for Passport or Aadhaar Front)
        qr_crop = None
        if rules.get("extract_qr", True):
            qr_crop = cls.crop_qr_code(image, qr_info=qr_info, face_bbox=photo_bbox, subtype=subtype)

        # 3. Address and MRZ crops
        address_crop = cls.crop_address_region(image, text_blocks=text_blocks, subtype=subtype)
        mrz_crop = cls.crop_mrz_zone(image, text_blocks=text_blocks) if rules.get("extract_mrz", False) else None

        return {
            "photo": photo_crop,
            "qr": qr_crop,
            "address": address_crop,
            "mrz_zone": mrz_crop,
            "subtype": subtype
        }

    @classmethod
    def crop_aadhaar_components(cls, image: np.ndarray, qr_info: Optional[Dict[str, Any]] = None, text_blocks: Optional[List[Dict[str, Any]]] = None, raw_text: str = "") -> Dict[str, Optional[np.ndarray]]:
        """Backwards compatibility alias for Aadhaar component cropping."""
        return cls.crop_document_components(image, doc_type="aadhaar", qr_info=qr_info, text_blocks=text_blocks, raw_text=raw_text)

    @classmethod
    def _is_valid_qr_region(cls, crop: np.ndarray, face_bbox: Optional[Tuple[int, int, int, int]] = None, crop_bbox: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """
        Strict QR Verification:
        1. Face Cascade Negative Filter (Rejects any candidate containing a human face).
        2. Photo Box Overlap Exclusion (Rejects candidate if IoU/overlap with face_bbox > 15%).
        3. High-Frequency Binary Transition Analysis (Verifies matrix checkerboard pattern).
        """
        if crop is None or crop.size == 0 or crop.shape[0] < 24 or crop.shape[1] < 24:
            return False

        h_c, w_c = crop.shape[:2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop

        # 1. Overlap Exclusion check with known face photo bounding box
        if face_bbox and crop_bbox:
            fx1, fy1, fx2, fy2 = face_bbox
            cx1, cy1, cx2, cy2 = crop_bbox
            
            # Intersection coordinates
            ix1 = max(fx1, cx1)
            iy1 = max(fy1, cy1)
            ix2 = min(fx2, cx2)
            iy2 = min(fy2, cy2)
            
            if ix2 > ix1 and iy2 > iy1:
                inter_area = (ix2 - ix1) * (iy2 - iy1)
                crop_area = (cx2 - cx1) * (cy2 - cy1)
                if crop_area > 0 and (inter_area / float(crop_area)) > 0.15:
                    return False

        # 2. Face Negative Filter: If face detector detects a face inside this crop, REJECT!
        try:
            for cascade_name in ['haarcascade_frontalface_default.xml', 'haarcascade_frontalface_alt2.xml']:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_name)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=2, minSize=(20, 20))
                if len(faces) > 0:
                    return False
        except Exception:
            pass

        # 3. Contrast check (QR codes have high std dev of pixel intensities)
        std_dev = np.std(gray)
        if std_dev < 30.0:
            return False

        # 4. Binary Transition Frequency Analysis (QR matrix modules create alternating black/white transitions)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Count transitions across middle horizontal and vertical sampling lines
        mid_row = thresh[h_c // 2, :]
        mid_col = thresh[:, w_c // 2]
        
        row_transitions = np.count_nonzero(mid_row[:-1] != mid_row[1:])
        col_transitions = np.count_nonzero(mid_col[:-1] != mid_col[1:])

        # Real 2D QR codes have high-frequency transitions (>=4 transitions per midline)
        if row_transitions < 4 or col_transitions < 4:
            return False

        # 5. Canny edge density check
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.count_nonzero(edges) / float(h_c * w_c)
        if edge_density < 0.05 or edge_density > 0.65:
            return False

        return True

    @classmethod
    def crop_face_photo_with_bbox(cls, image: np.ndarray, doc_type: str = "unknown", subtype: str = "unknown", text_blocks: Optional[List[Dict[str, Any]]] = None) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """
        Detects and crops face photo portrait across Passport, Driving Licence, and Aadhaar documents.
        Uses document-specific layout rules:
          - Driving Licence (DL): Face photo is on the RIGHT side (x: 60%-96%). Excludes smart card chip on left.
          - Passport: Face photo is on the LEFT side below header (x: 3%-35%, y: 16%-76%). Excludes "भारत" header.
          - Aadhaar: Face photo is on the LEFT side below header (x: 3%-36%, y: 13%-86%).
        """
        if image is None or image.size == 0:
            return None, None

        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        doc_key = doc_type.lower() if doc_type else "unknown"

        # Determine document-specific header boundary and search ROIs
        rois_to_try = []
        header_min_y = int(h * 0.12)
        footer_max_y = int(h * 0.90)

        if doc_key in ("dl", "driving_licence"):
            # Driving Licence Front: Face photo is on the RIGHT side! (Smart card chip is on the left)
            header_min_y = int(h * 0.12)
            footer_max_y = int(h * 0.90)
            rois_to_try.append((int(w * 0.55), header_min_y, int(w * 0.98), footer_max_y))
            rois_to_try.append((int(w * 0.50), 0, w, h))
        elif doc_key in ("passport", "visa"):
            # Passport Data Page: Header "भारत / REPUBLIC OF INDIA" is top 14%. Face photo is on left (x: 2%-36%, y: 16%-76%)
            header_min_y = int(h * 0.15)
            footer_max_y = int(h * 0.78)
            rois_to_try.append((0, header_min_y, int(w * 0.40), footer_max_y))
            rois_to_try.append((0, int(h * 0.12), int(w * 0.45), int(h * 0.82)))
        elif subtype == "full_e_aadhaar":
            # e-Aadhaar A4 lower card section
            header_min_y = int(h * 0.58)
            footer_max_y = int(h * 0.94)
            rois_to_try.append((0, header_min_y, int(w * 0.42), footer_max_y))
        elif subtype == "cut_out_dual_card":
            header_min_y = int(h * 0.12)
            footer_max_y = int(h * 0.88)
            rois_to_try.append((0, header_min_y, int(w * 0.40), footer_max_y))
        elif subtype == "stacked_dual_card":
            header_min_y = int(h * 0.08)
            footer_max_y = int(h * 0.48)
            rois_to_try.append((0, header_min_y, int(w * 0.45), footer_max_y))
        else:
            # Default single front card / Aadhaar
            header_min_y = int(h * 0.12)
            footer_max_y = int(h * 0.88)
            rois_to_try.append((0, header_min_y, int(w * 0.42), footer_max_y))
            rois_to_try.append((0, 0, w, h))

        cascade_files = [
            'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_alt2.xml',
            'haarcascade_profileface.xml'
        ]

        # Strategy 1: Multi-scale Haar cascade face detector in search ROIs
        for (rx1, ry1, rx2, ry2) in rois_to_try:
            roi_gray = gray[ry1:ry2, rx1:rx2]
            if roi_gray.size == 0:
                continue

            for cascade_name in cascade_files:
                try:
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_name)
                    faces = face_cascade.detectMultiScale(
                        roi_gray,
                        scaleFactor=1.05,
                        minNeighbors=2,
                        minSize=(int(min(w, h) * 0.03), int(min(w, h) * 0.03))
                    )

                    if len(faces) > 0:
                        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                        (fx, fy, fw, fh) = faces[0]
                        abs_fx = rx1 + fx
                        abs_fy = ry1 + fy
                        
                        # Corrected portrait padding:
                        # Top Y: Never go above header_min_y into header text "भारत"!
                        y1 = max(header_min_y, abs_fy - int(fh * 0.35))
                        # Bottom Y: Extend downwards to include chin & shoulders
                        y2 = min(footer_max_y, abs_fy + fh + int(fh * 0.85))
                        
                        # X padding:
                        x1 = max(rx1, abs_fx - int(fw * 0.35))
                        x2 = min(rx2, abs_fx + fw + int(fw * 0.35))
                        
                        crop = image[y1:y2, x1:x2]
                        if crop.size > 0 and np.std(crop) > 15.0:
                            return crop, (x1, y1, x2, y2)
                except Exception:
                    continue

        # Strategy 2: Contour / Photo Box Frame Detector
        for (rx1, ry1, rx2, ry2) in rois_to_try:
            roi_gray = gray[ry1:ry2, rx1:rx2]
            if roi_gray.size == 0:
                continue

            try:
                blurred = cv2.GaussianBlur(roi_gray, (3, 3), 0)
                edges = cv2.Canny(blurred, 40, 140)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                photo_candidates = []
                for cnt in contours:
                    x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
                    aspect = float(h_c) / float(w_c) if w_c > 0 else 0
                    area = w_c * h_c
                    if 0.75 <= aspect <= 1.70 and (w * h * 0.0025) < area < (w * h * 0.35):
                        abs_xc = rx1 + x_c
                        abs_yc = ry1 + y_c
                        photo_candidates.append((abs_xc, abs_yc, w_c, h_c, area))

                if photo_candidates:
                    photo_candidates.sort(key=lambda c: c[0] + c[1])
                    xc, yc, wc, hc, _ = photo_candidates[0]
                    pad = 5
                    x1 = max(rx1, xc - pad)
                    y1 = max(header_min_y, yc - pad)
                    x2 = min(rx2, xc + wc + pad)
                    y2 = min(footer_max_y, yc + hc + pad)
                    crop = image[y1:y2, x1:x2]
                    if crop.size > 0 and np.std(crop) > 15.0:
                        return crop, (x1, y1, x2, y2)
            except Exception:
                pass

        # Strategy 3: Standard Document Layout Positional Bounding (Guaranteed Fallback)
        try:
            if doc_key in ("dl", "driving_licence"):
                # DL Front: Face photo is on the RIGHT side! (x: 60%-96%, y: 14%-88%)
                x1 = int(w * 0.60)
                x2 = int(w * 0.96)
                y1 = int(h * 0.14)
                y2 = int(h * 0.88)
            elif doc_key in ("passport", "visa"):
                # Passport: Face photo is on LEFT side below header (x: 3%-35%, y: 16%-76%)
                x1 = int(w * 0.03)
                x2 = int(w * 0.35)
                y1 = int(h * 0.16)
                y2 = int(h * 0.76)
            elif subtype == "full_e_aadhaar":
                x1 = int(w * 0.02)
                x2 = int(w * 0.26)
                y1 = int(h * 0.58)
                y2 = int(h * 0.94)
            elif subtype == "cut_out_dual_card":
                x1 = int(w * 0.03)
                x2 = int(w * 0.25)
                y1 = int(h * 0.12)
                y2 = int(h * 0.88)
            elif subtype == "stacked_dual_card":
                x1 = int(w * 0.04)
                x2 = int(w * 0.38)
                y1 = int(h * 0.08)
                y2 = int(h * 0.44)
            elif subtype == "single_card_back":
                x1 = int(w * 0.04)
                x2 = int(w * 0.38)
                y1 = int(h * 0.12)
                y2 = int(h * 0.88)
                crop = image[y1:y2, x1:x2]
                if cls._detect_face_presence(crop):
                    return crop, (x1, y1, x2, y2)
                return None, None
            else:
                # Default single front card / Aadhaar
                x1 = int(w * 0.04)
                x2 = int(w * 0.38)
                y1 = int(h * 0.12)
                y2 = int(h * 0.88)

            crop = image[y1:y2, x1:x2]
            if crop.size > 0 and np.std(crop) > 10.0:
                return crop, (x1, y1, x2, y2)
        except Exception:
            pass

        return None, None

    @classmethod
    def crop_face_photo(cls, image: np.ndarray, doc_type: str = "unknown", subtype: str = "unknown") -> Optional[np.ndarray]:
        """Convenience wrapper for crop_face_photo_with_bbox."""
        crop, _ = cls.crop_face_photo_with_bbox(image, doc_type=doc_type, subtype=subtype)
        return crop

    @classmethod
    def crop_qr_code(cls, image: np.ndarray, qr_info: Optional[Dict[str, Any]] = None, face_bbox: Optional[Tuple[int, int, int, int]] = None, subtype: str = "unknown") -> Optional[np.ndarray]:
        """
        Detects and crops 2D QR Code or Barcode image from any document image.
        Supports full e-Aadhaar letters, cut-out wallet cards, vertical stacked cards, single front and back cards.
        STRICT: Returns None if no genuine 2D QR code exists on the card (prevents photo false positives).
        """
        h, w = image.shape[:2]

        # 1. Use decoded QR bounding box if available from PyZbar / OpenCV QR decoder
        if qr_info and qr_info.get("bbox") and len(qr_info["bbox"]) == 4:
            x1, y1, x2, y2 = qr_info["bbox"]
            pad = int(min(w, h) * 0.02)
            x1_crop = max(0, x1 - pad)
            y1_crop = max(0, y1 - pad)
            x2_crop = min(w, x2 + pad)
            y2_crop = min(h, y2 + pad)
            if x2_crop > x1_crop and y2_crop > y1_crop:
                crop = image[y1_crop:y2_crop, x1_crop:x2_crop]
                if cls._is_valid_qr_region(crop, face_bbox=face_bbox, crop_bbox=(x1_crop, y1_crop, x2_crop, y2_crop)):
                    return crop

        # 2. OpenCV QR detector search across full image space
        try:
            detector = cv2.QRCodeDetector()
            _, points = detector.detect(image)
            if points is not None and len(points) > 0:
                pts = points[0]
                x_min, y_min = np.min(pts, axis=0)
                x_max, y_max = np.max(pts, axis=0)
                pad = 12
                x1 = max(0, int(x_min) - pad)
                y1 = max(0, int(y_min) - pad)
                x2 = min(w, int(x_max) + pad)
                y2 = min(h, int(y_max) + pad)
                if (x2 - x1) > 25 and (y2 - y1) > 25:
                    crop = image[y1:y2, x1:x2]
                    if cls._is_valid_qr_region(crop, face_bbox=face_bbox, crop_bbox=(x1, y1, x2, y2)):
                        return crop
        except Exception:
            pass

        # 3. OpenCV Contour detection for 2D square QR code with high-density grid verification
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            qr_candidates = []
            for cnt in contours:
                x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
                aspect_ratio = float(w_c) / float(h_c)
                area = w_c * h_c
                if 0.80 <= aspect_ratio <= 1.25 and (w * h * 0.005) < area < (w * h * 0.28):
                    crop_bbox = (max(0, x_c-5), max(0, y_c-5), min(w, x_c+w_c+5), min(h, y_c+h_c+5))
                    crop_cand = image[crop_bbox[1]:crop_bbox[3], crop_bbox[0]:crop_bbox[2]]
                    if cls._is_valid_qr_region(crop_cand, face_bbox=face_bbox, crop_bbox=crop_bbox):
                        qr_candidates.append((x_c, y_c, w_c, h_c, area, crop_cand))

            if qr_candidates:
                qr_candidates.sort(key=lambda c: c[4], reverse=True)
                return qr_candidates[0][5]
        except Exception:
            pass

        # 4. Subtype-Aware Fallback Position Crop WITH Strict Matrix Edge Density Validation
        try:
            if subtype == "full_e_aadhaar":
                x1 = int(w * 0.65)
                x2 = int(w * 0.98)
                y1 = int(h * 0.58)
                y2 = int(h * 0.96)
            elif subtype == "cut_out_dual_card":
                x1 = int(w * 0.68)
                x2 = int(w * 0.98)
                y1 = int(h * 0.12)
                y2 = int(h * 0.88)
            elif subtype == "stacked_dual_card":
                x1 = int(w * 0.55)
                x2 = int(w * 0.98)
                y1 = int(h * 0.55)
                y2 = int(h * 0.95)
            elif subtype == "single_card_back":
                x1 = int(w * 0.55)
                x2 = int(w * 0.98)
                y1 = int(h * 0.12)
                y2 = int(h * 0.92)
            else:
                x1 = int(w * 0.60)
                x2 = int(w * 0.98)
                y1 = int(h * 0.15)
                y2 = int(h * 0.60)

            crop = image[y1:y2, x1:x2]
            if cls._is_valid_qr_region(crop, face_bbox=face_bbox, crop_bbox=(x1, y1, x2, y2)):
                return crop
        except Exception:
            pass

        return None
    @classmethod
    def crop_address_region(cls, image: np.ndarray, text_blocks: Optional[List[Dict[str, Any]]] = None, subtype: str = "unknown") -> Optional[np.ndarray]:
        """Detects and crops Address block region from document."""
        h, w = image.shape[:2]

        if text_blocks and len(text_blocks) > 0:
            addr_boxes = []
            for b in text_blocks:
                txt = b.get("text", "").upper()
                bbox = b.get("bbox")
                if bbox and len(bbox) == 4:
                    if any(k in txt for k in ["ADDRESS", "पता", "S/O", "C/O", "W/O", "D/O", "ROV", "ROW", "HOUSE", "NAGAR", "STREET", "FLAT", "VILLA", "DIST", "STATE", "PIN", "PO:"]) or re.search(r'\b\d{6}\b', txt):
                        if bbox[0] < w * 0.68:
                            addr_boxes.append(bbox)

            if len(addr_boxes) > 0:
                x1 = max(0, min(b[0] for b in addr_boxes) - 15)
                y1 = max(0, min(b[1] for b in addr_boxes) - 15)
                x2 = min(int(w * 0.68), max(b[2] for b in addr_boxes) + 20)
                y2 = min(h, max(b[3] for b in addr_boxes) + 25)
                if (x2 - x1) > 40 and (y2 - y1) > 30:
                    return image[y1:y2, x1:x2]

        try:
            if subtype == "full_e_aadhaar":
                x1 = int(w * 0.52)
                x2 = int(w * 0.78)
                y1 = int(h * 0.58)
                y2 = int(h * 0.94)
            elif subtype == "cut_out_dual_card":
                x1 = int(w * 0.52)
                x2 = int(w * 0.75)
                y1 = int(h * 0.12)
                y2 = int(h * 0.88)
            elif subtype == "stacked_dual_card":
                x1 = int(w * 0.02)
                x2 = int(w * 0.58)
                y1 = int(h * 0.55)
                y2 = int(h * 0.95)
            elif subtype == "single_card_back":
                x1 = int(w * 0.02)
                x2 = int(w * 0.60)
                y1 = int(h * 0.12)
                y2 = int(h * 0.92)
            else:
                x1 = int(w * 0.02)
                x2 = int(w * 0.55)
                y1 = int(h * 0.15)
                y2 = int(h * 0.95)
            return image[y1:y2, x1:x2]
        except Exception:
            return None

    @classmethod
    def crop_mrz_zone(cls, image: np.ndarray, text_blocks: Optional[List[Dict[str, Any]]] = None) -> Optional[np.ndarray]:
        """Detects and crops Machine Readable Zone (MRZ) bottom band for Passports / Visas."""
        h, w = image.shape[:2]

        if text_blocks:
            mrz_boxes = []
            for b in text_blocks:
                txt = b.get("text", "").upper()
                bbox = b.get("bbox")
                if bbox and len(bbox) == 4:
                    if "P<" in txt or "V<" in txt or "IND" in txt or re.search(r'[A-Z0-9<]{10,44}', txt):
                        if bbox[1] > h * 0.60:
                            mrz_boxes.append(bbox)

            if len(mrz_boxes) > 0:
                x1 = max(0, min(b[0] for b in mrz_boxes) - 10)
                y1 = max(0, min(b[1] for b in mrz_boxes) - 10)
                x2 = min(w, max(b[2] for b in mrz_boxes) + 10)
                y2 = min(h, max(b[3] for b in mrz_boxes) + 10)
                if (x2 - x1) > 100 and (y2 - y1) > 20:
                    return image[y1:y2, x1:x2]

        try:
            x1 = max(0, int(w * 0.02))
            x2 = min(w, int(w * 0.98))
            y1 = max(0, int(h * 0.72))
            y2 = min(h, int(h * 0.98))
            return image[y1:y2, x1:x2]
        except Exception:
            return None

# Compatible alias
AadhaarRegionCropper = DocumentRegionCropper
