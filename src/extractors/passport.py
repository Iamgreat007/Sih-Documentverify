import re
from typing import Dict, Any, List
from src.extractors.base import BaseExtractor
from src.mrz_parser import MRZParser

class PassportExtractor(BaseExtractor):
    """
    Passport Extractor: Parses Machine Readable Zone (MRZ) per ICAO 9303 format.
    Extracts passport_number, surname, given_name, nationality, dob, sex, date_of_expiry, issuing_country.
    Includes text fallbacks for OCR text extraction.
    """

    def extract(self, raw_text: str, text_blocks: List[Dict[str, Any]], qr_info: Dict[str, Any] = None) -> Dict[str, Any]:
        fields = {}

        # 1. Parse ICAO 9303 MRZ
        mrz_data = MRZParser.parse_mrz(raw_text)
        if mrz_data:
            fields["passport_number"] = mrz_data.get("passport_number")
            fields["surname"] = mrz_data.get("surname")
            fields["given_name"] = mrz_data.get("given_name")
            fields["name"] = f"{fields.get('given_name', '')} {fields.get('surname', '')}".strip()
            fields["nationality"] = mrz_data.get("nationality")
            fields["issuing_country"] = mrz_data.get("issuing_country") or "IND"
            fields["dob"] = mrz_data.get("dob")
            fields["sex"] = mrz_data.get("sex")
            fields["date_of_expiry"] = mrz_data.get("expiry_date")
            fields["mrz_checksum_valid"] = mrz_data.get("mrz_checksum_valid")
            fields["mrz_raw"] = mrz_data.get("mrz_raw")
        else:
            fields["mrz_checksum_valid"] = False

        # 2. Text Fallbacks for Passport fields
        if not fields.get("passport_number"):
            p_match = re.search(r'\b([A-Z]{1,2}\d{7})\b', raw_text)
            if not p_match:
                p_match = re.search(r'(?:Passport No|Passport Number)\s*[:\s]*([A-Z0-9]{8,9})', raw_text, re.IGNORECASE)
            fields["passport_number"] = p_match.group(1) if p_match else None

        if not fields.get("given_name"):
            g_match = re.search(r'(?:Given Name[s]?|Given Name)\s*[:\s]*([A-Za-z\s\.\'-]{2,35})', raw_text, re.IGNORECASE)
            if g_match:
                fields["given_name"] = g_match.group(1).strip().split('\n')[0]

        if not fields.get("surname"):
            s_match = re.search(r'(?:Surname|Nom)\s*[:\s]*([A-Za-z\s\.\'-]{2,35})', raw_text, re.IGNORECASE)
            if s_match:
                fields["surname"] = s_match.group(1).strip().split('\n')[0]

        if not fields.get("name"):
            g = fields.get("given_name", "")
            s = fields.get("surname", "")
            full_n = f"{g} {s}".strip()
            if full_n:
                fields["name"] = full_n
            else:
                n_match = re.search(r'(?:Name|Holder)\s*[:\s]*([A-Za-z\s\.\'-]{2,35})', raw_text, re.IGNORECASE)
                fields["name"] = n_match.group(1).strip().split('\n')[0] if n_match else None

        if not fields.get("dob"):
            dob_match = re.search(r'(?:Date of Birth|DOB|Birth)\s*[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})', raw_text, re.IGNORECASE)
            if not dob_match:
                dob_match = re.search(r'\b(\d{2}[-/\.]\d{2}[-/\.]\d{4})\b', raw_text)
            fields["dob"] = dob_match.group(1).replace("-", "/").replace(".", "/") if dob_match else None

        if not fields.get("date_of_expiry"):
            exp_match = re.search(r'(?:Date of Expiry|Expiry)\s*[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})', raw_text, re.IGNORECASE)
            fields["date_of_expiry"] = exp_match.group(1).replace("-", "/").replace(".", "/") if exp_match else None

        if not fields.get("sex"):
            if re.search(r'\bSex\s*[:\s]*F\b|\bFEMALE\b', raw_text, re.IGNORECASE):
                fields["sex"] = "F"
            elif re.search(r'\bSex\s*[:\s]*M\b|\bMALE\b', raw_text, re.IGNORECASE):
                fields["sex"] = "M"

        if not fields.get("nationality"):
            if "REPUBLIC OF INDIA" in raw_text.upper() or "IND" in raw_text.upper():
                fields["nationality"] = "IND"
                fields["issuing_country"] = "IND"

        return fields
