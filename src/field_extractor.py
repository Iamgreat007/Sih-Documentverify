from typing import Dict, Any, List
from src.extractors.aadhaar import AadhaarExtractor
from src.extractors.passport import PassportExtractor
from src.extractors.visa import VisaExtractor
from src.extractors.dl import DLExtractor

class FieldExtractor:
    """
    Modular Field Extractor orchestrating per-document extractors:
    Aadhaar, Passport, Visa, and Driving Licence.
    """

    EXTRACTORS = {
        "aadhaar": AadhaarExtractor(),
        "passport": PassportExtractor(),
        "visa": VisaExtractor(),
        "driving_licence": DLExtractor(),
        "dl": DLExtractor()
    }

    @classmethod
    def extract_fields(cls, doc_type: str, raw_text: str, text_blocks: List[Dict[str, Any]], qr_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extracts structured fields using the appropriate document type extractor.
        """
        extractor = cls.EXTRACTORS.get(doc_type, cls.EXTRACTORS["passport"])
        return extractor.extract(raw_text, text_blocks, qr_info)
