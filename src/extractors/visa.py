import re
from typing import Dict, Any, List
from src.extractors.base import BaseExtractor
from src.mrz_parser import MRZParser

class VisaExtractor(BaseExtractor):
    """
    Visa Extractor: Parses Visa MRZ & endorsement text.
    Extracts visa_number, passport_number, name, visa_type, no_of_entries, date_of_issue, date_of_expiry, special_endorsement.
    """

    def extract(self, raw_text: str, text_blocks: List[Dict[str, Any]], qr_info: Dict[str, Any] = None) -> Dict[str, Any]:
        fields = {}

        mrz_data = MRZParser.parse_mrz(raw_text)
        if mrz_data:
            fields["passport_number"] = mrz_data.get("passport_number")
            fields["surname"] = mrz_data.get("surname")
            fields["given_name"] = mrz_data.get("given_name")
            fields["name"] = f"{fields.get('given_name', '')} {fields.get('surname', '')}".strip()
            fields["nationality"] = mrz_data.get("nationality")
            fields["dob"] = mrz_data.get("dob")
            fields["sex"] = mrz_data.get("sex")
            fields["date_of_expiry"] = mrz_data.get("expiry_date")
            fields["mrz_checksum_valid"] = mrz_data.get("mrz_checksum_valid")
            fields["mrz_raw"] = mrz_data.get("mrz_raw")
        else:
            fields["mrz_checksum_valid"] = False

        # Text Fallbacks for Visa fields if MRZ not found or incomplete
        if not fields.get("name"):
            n_match = re.search(r'(?:Name|Nom|Nombre|Bearer)\s*[:\s]*([A-Za-z\s\.\'-]+)', raw_text, re.IGNORECASE)
            fields["name"] = n_match.group(1).strip().split('\n')[0] if n_match else None

        if not fields.get("visa_number"):
            v_match = re.search(r'(?:VISA\s*NO|VISA|NUMBER)\s*[:\s]*([A-Z0-9]{6,12})', raw_text, re.IGNORECASE)
            fields["visa_number"] = v_match.group(1) if v_match else None

        if not fields.get("visa_type"):
            if "TOURIST" in raw_text.upper():
                fields["visa_type"] = "TOURIST"
            elif "BUSINESS" in raw_text.upper():
                fields["visa_type"] = "BUSINESS"
            elif "STUDENT" in raw_text.upper():
                fields["visa_type"] = "STUDENT"
            elif "EMPLOYMENT" in raw_text.upper():
                fields["visa_type"] = "EMPLOYMENT"

        if not fields.get("no_of_entries"):
            if "MULTIPLE" in raw_text.upper() or "MULT" in raw_text.upper():
                fields["no_of_entries"] = "MULTIPLE"
            elif "SINGLE" in raw_text.upper():
                fields["no_of_entries"] = "SINGLE"
            elif "DOUBLE" in raw_text.upper():
                fields["no_of_entries"] = "DOUBLE"

        return fields
