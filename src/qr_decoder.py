import cv2
import re
import numpy as np
from typing import Dict, Any, Optional

# Safe pyzbar import with fallback for Windows C-DLL missing dependencies
try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_AVAILABLE = True
except (ImportError, Exception):
    PYZBAR_AVAILABLE = False
    zbar_decode = None

class QRDecoder:
    """
    QR Code Detector, Decoder, and OCR Data Cross-Checker for Identity Document Tampering Detection.
    Decodes QR codes using OpenCV QRCodeDetector and pyzbar.
    """

    @classmethod
    def decode_qr(cls, image: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Detects and decodes QR codes in the image.
        Returns dictionary containing decoded payload and bounding box coordinates.
        """
        # Method 1: pyzbar decoding
        if PYZBAR_AVAILABLE and zbar_decode is not None:
            try:
                barcodes = zbar_decode(image)
                for barcode in barcodes:
                    if barcode.type == 'QRCODE':
                        qr_text = barcode.data.decode('utf-8', errors='ignore')
                        rect = barcode.rect
                        return {
                            "payload": qr_text,
                            "method": "pyzbar",
                            "bbox": [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                        }
            except Exception:
                pass

        # Method 2: OpenCV QRCodeDetector fallback
        try:
            detector = cv2.QRCodeDetector()
            res = detector.detectAndDecode(image)
            val = res[0] if isinstance(res, (tuple, list)) and len(res) > 0 else ""
            points = res[1] if isinstance(res, (tuple, list)) and len(res) > 1 else None

            if isinstance(val, str) and len(val.strip()) > 0:
                bbox = []
                if points is not None and len(points) > 0:
                    pts = points[0]
                    x_min, y_min = np.min(pts, axis=0)
                    x_max, y_max = np.max(pts, axis=0)
                    bbox = [int(x_min), int(y_min), int(x_max), int(y_max)]
                return {
                    "payload": val.strip(),
                    "method": "opencv",
                    "bbox": bbox
                }
        except Exception:
            pass

        return None

    @classmethod
    def parse_aadhaar_qr(cls, qr_payload: str) -> Dict[str, str]:
        """Parses Aadhaar XML / Secure QR text fields."""
        fields = {}
        # XML attribute parsing regex e.g. uid="...", name="...", dob="...", gender="..."
        patterns = {
            "name": r'name="([^"]+)"',
            "dob": r'dob="([^"]+)"',
            "gender": r'gender="([^"]+)"',
            "uid": r'uid="([^"]+)"',
            "co": r'co="([^"]+)"',
            "house": r'house="([^"]+)"',
            "street": r'street="([^"]+)"',
            "pc": r'pc="([^"]+)"',
        }
        for field, pattern in patterns.items():
            match = re.search(pattern, qr_payload, re.IGNORECASE)
            if match:
                fields[field] = match.group(1).strip()
        
        # If payload is plain text string with key values
        if not fields:
            fields["raw_payload"] = qr_payload
        return fields

    @classmethod
    def cross_check_qr_with_ocr(cls, qr_info: Optional[Dict[str, Any]], extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cross-checks decoded QR fields against OCR-extracted fields to detect text manipulation/tampering.
        Returns match status and any detected field mismatches.
        """
        if not qr_info or not qr_info.get("payload"):
            return {
                "qr_detected": False,
                "qr_data": None,
                "qr_ocr_match": None,
                "mismatches": ["QR code not detected on document"]
            }

        payload = qr_info["payload"]
        parsed_qr = cls.parse_aadhaar_qr(payload)
        mismatches = []
        matches_count = 0

        # Check Name
        qr_name = parsed_qr.get("name")
        ocr_name = extracted_fields.get("name")
        if qr_name and ocr_name:
            if qr_name.lower().strip() in ocr_name.lower().strip() or ocr_name.lower().strip() in qr_name.lower().strip():
                matches_count += 1
            else:
                mismatches.append(f"Name mismatch: QR='{qr_name}', OCR='{ocr_name}'")

        # Check DOB
        qr_dob = parsed_qr.get("dob")
        ocr_dob = extracted_fields.get("dob")
        if qr_dob and ocr_dob:
            if qr_dob in ocr_dob or ocr_dob in qr_dob:
                matches_count += 1
            else:
                mismatches.append(f"DOB mismatch: QR='{qr_dob}', OCR='{ocr_dob}'")

        # Check Document / Card Number
        ocr_number = extracted_fields.get("aadhaar_number") or extracted_fields.get("dl_number") or extracted_fields.get("passport_number")
        if ocr_number:
            clean_ocr_num = re.sub(r'\s+', '', ocr_number)
            if clean_ocr_num in payload.replace(' ', ''):
                matches_count += 1

        is_match = len(mismatches) == 0 and (matches_count > 0 or "raw_payload" in parsed_qr)

        return {
            "qr_detected": True,
            "qr_data": payload,
            "parsed_qr_fields": parsed_qr,
            "qr_ocr_match": is_match,
            "mismatches": mismatches
        }
