import re
from typing import Dict, Any, List
from src.extractors.base import BaseExtractor

class DLExtractor(BaseExtractor):
    """
    Driving Licence Extractor: Flexible multi-state regex parser matching Indian state DL formats
    (e.g., TG00820260009319, TS-08-20200001234, DL1420110012345, MH0120090012345).
    Extracts dl_number, name, dob, address, issue_date, validity_nt, vehicle_classes, relation_name, blood_group.
    """

    STATE_DL_PATTERNS = [
        r'\b([A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{7})\b',        # e.g., TG00820260009319 / TS-08-2020-0001234
        r'\b([A-Z]{2}[-\s]?\d{2}[-\s]?\d{11})\b',                # e.g., TS00820260009319
        r'\b([A-Z]{2}[-\s]?\d{12,14})\b',                        # e.g., DL1420110012345
        r'\b(?:DL\s*NO|LICENCE\s*NO|DL)\.?\s*[:\s]*([A-Z0-9/\-\s]{10,20})\b'
    ]

    VEHICLE_CLASS_KEYWORDS = [
        "MCWG", "LMV", "MCWOG", "3W-CAB", "TRANS", "LDRX", "HMV", "HGMV"
    ]

    def extract(self, raw_text: str, text_blocks: List[Dict[str, Any]], qr_info: Dict[str, Any] = None) -> Dict[str, Any]:
        fields = {}

        # 1. DL Number Regex (Multi-state flexible matching)
        dl_number = None
        for pattern in self.STATE_DL_PATTERNS:
            m = re.search(pattern, raw_text, re.IGNORECASE)
            if m:
                clean_dl = re.sub(r'[-\s]', '', m.group(1)).upper()
                if len(clean_dl) >= 10:
                    dl_number = clean_dl
                    break

        fields["dl_number"] = dl_number

        # 2. DOB Extraction (supports /, -, .)
        dob_match = re.search(r'(?:DOB|Date of Birth|Birth)\s*[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})', raw_text, re.IGNORECASE)
        if not dob_match:
            dob_match = re.search(r'\b(\d{2}[-/\.]\d{2}[-/\.]\d{4})\b', raw_text)
        fields["dob"] = dob_match.group(1).replace("-", "/").replace(".", "/") if dob_match else None

        # 3. Name Extraction
        name_match = re.search(r'(?:Name|Holder|Name of Holder)\s*[:\s]*([A-Za-z\s\.\'-]{2,35})', raw_text, re.IGNORECASE)
        if name_match:
            cand = name_match.group(1).strip().split('\n')[0]
            fields["name"] = cand if len(cand) >= 2 else None
        else:
            # Check line before DOB or S/O line
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            cand_name = None
            for idx, l in enumerate(lines):
                if any(k in l.upper() for k in ["S/O", "D/O", "W/O", "SON OF", "DAUGHTER OF", "WIFE OF", "DOB:"]) and idx > 0:
                    prev_l = lines[idx-1]
                    clean_l = re.sub(r'[^A-Za-z\s\.\'-]', ' ', prev_l)
                    clean_l = re.sub(r'\s+', ' ', clean_l).strip()
                    if 3 <= len(clean_l) <= 35 and not any(k in clean_l.upper() for k in ["LICENCE", "DRIVING", "UNION", "AUTHORITY", "FORM", "TRANSPORT", "DEPARTMENT"]):
                        cand_name = clean_l
                        break
            fields["name"] = cand_name

        # 4. Dates: Issue Date & Validity
        issue_match = re.search(r'(?:Issue Date|DOI|Issued)\s*[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})', raw_text, re.IGNORECASE)
        fields["issue_date"] = issue_match.group(1).replace("-", "/").replace(".", "/") if issue_match else None

        val_match = re.search(r'(?:Validity|Valid Till|NT)\s*[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})', raw_text, re.IGNORECASE)
        fields["validity_nt"] = val_match.group(1).replace("-", "/").replace(".", "/") if val_match else None

        # 5. Vehicle Classes Extraction
        v_classes = []
        for v_code in self.VEHICLE_CLASS_KEYWORDS:
            if v_code in raw_text.upper():
                v_classes.append(v_code)
        fields["vehicle_classes"] = v_classes if v_classes else None

        # 6. Relation & Blood Group
        blood_match = re.search(r'(?:Blood Group|BG)\s*[:\s]*([ABO][+-])', raw_text, re.IGNORECASE)
        fields["blood_group"] = blood_match.group(1) if blood_match else None

        rel_match = re.search(r'(?:S/O|D/O|W/O|Son of|Daughter of|Wife of)\s*[:\s]*([A-Za-z\s\.\'-]{2,35})', raw_text, re.IGNORECASE)
        fields["relation_name"] = rel_match.group(1).strip() if rel_match else None

        # 7. Address Extraction (including PIN code)
        addr_match = re.search(r'(?:Address|Add)\s*[:\s]*(.+?)(?=\b\d{6}\b|$)', raw_text, re.IGNORECASE | re.DOTALL)
        if addr_match:
            full_addr = addr_match.group(0).strip()
            pin_m = re.search(r'\b\d{6}\b', raw_text[addr_match.start():addr_match.end()+20])
            if pin_m and pin_m.group(0) not in full_addr:
                full_addr += " - " + pin_m.group(0)
            fields["address"] = re.sub(r'\s+', ' ', full_addr).strip()
        else:
            fields["address"] = None

        return fields
