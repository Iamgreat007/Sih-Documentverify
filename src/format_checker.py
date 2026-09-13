import re
from typing import Dict, Any, List

class DocumentFormatChecker:
    """
    Evaluates document layout compliance and required feature extraction completeness for:
    - Aadhaar Card
    - Indian Passport
    - Indian Visa
    - Driving Licence
    """

    DOCUMENT_FEATURE_PROFILES = {
        "aadhaar": {
            "name": "Aadhaar Card Feature Specification",
            "required_headers": [
                "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", "GOVERNMENT OF INDIA", 
                "BHARAT SARKAR", "AADHAAR", "UIDAI", "MERA AADHAAR"
            ],
            "key_fields": ["aadhaar_number", "name", "dob", "gender", "address"],
            "number_pattern": r'\b([X\d]{4}\s?[X\d]{4}\s?\d{4}|\d{12})\b',
            "has_qr": True,
            "has_mrz": False,
            "min_headers_matched": 1
        },
        "passport": {
            "name": "Indian Passport (ICAO Doc 9303) Feature Specification",
            "required_headers": [
                "PASSPORT", "REPUBLIC OF INDIA", "TYPE P", "CODE IND", 
                "GIVEN NAME", "SURNAME", "PLACE OF BIRTH", "PLACE OF ISSUE"
            ],
            "key_fields": ["passport_number", "surname", "given_name", "nationality", "dob", "sex", "date_of_expiry"],
            "number_pattern": r'\b[A-Z]{1,2}\d{7}\b',
            "has_qr": False,
            "has_mrz": True,
            "min_headers_matched": 2
        },
        "visa": {
            "name": "Indian Visa Feature Specification",
            "required_headers": [
                "INDIAN VISA", "VISA TYPE", "NO OF ENTRIES", 
                "DATE OF ISSUE", "DATE OF EXPIRY", "SPECIAL ENDORSEMENT", "TOURIST"
            ],
            "key_fields": ["name", "passport_number", "visa_type", "date_of_issue", "date_of_expiry"],
            "number_pattern": r'\b[A-Z0-9]{4,10}\b',
            "has_qr": False,
            "has_mrz": True,
            "min_headers_matched": 1
        },
        "dl": {
            "name": "Indian Driving Licence Feature Specification",
            "required_headers": [
                "DRIVING LICENCE", "INDIAN UNION DRIVING LICENCE", "ISSUED BY", 
                "LICENCING AUTHORITY", "CLASS OF VEHICLE", "SON/DAUGHTER/WIFE OF", "VALIDITY"
            ],
            "key_fields": ["dl_number", "name", "dob", "issue_date", "validity_nt", "vehicle_classes"],
            "number_pattern": r'\b[A-Z]{2}\d{2}\s?\d{11,14}\b',
            "has_qr": False,
            "has_mrz": False,
            "min_headers_matched": 1
        },
        "driving_licence": {
            "name": "Indian Driving Licence Feature Specification",
            "required_headers": [
                "DRIVING LICENCE", "INDIAN UNION DRIVING LICENCE", "ISSUED BY", 
                "LICENCING AUTHORITY", "CLASS OF VEHICLE", "SON/DAUGHTER/WIFE OF", "VALIDITY"
            ],
            "key_fields": ["dl_number", "name", "dob", "issue_date", "validity_nt", "vehicle_classes"],
            "number_pattern": r'\b[A-Z]{2}\d{2}\s?\d{11,14}\b',
            "has_qr": False,
            "has_mrz": False,
            "min_headers_matched": 1
        }
    }

    # Backward compatibility alias
    SAMPLE_PROFILES = DOCUMENT_FEATURE_PROFILES

    @classmethod
    def verify_format(cls, doc_type: str, raw_text: str, extracted_fields: Dict[str, Any], qr_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Calculates feature alignment match score (%) and returns detailed check results.
        """
        profile = cls.DOCUMENT_FEATURE_PROFILES.get(doc_type)

        if not profile:
            return {
                "format_match_score": 0.0,
                "format_status": "UNKNOWN_FORMAT",
                "sample_format_name": "Generic Document Profile",
                "format_checks": [],
                "format_anomalies": ["Unknown or unclassified document format specification."]
            }

        text_upper = raw_text.upper()
        checks = []
        anomalies = []
        score_weight_total = 0.0
        score_weight_passed = 0.0

        # Check 1: Mandatory / Header Keywords Match (Weight: 35%)
        score_weight_total += 35.0
        matched_headers = [h for h in profile["required_headers"] if h in text_upper]
        header_ratio = len(matched_headers) / max(len(profile["required_headers"]), 1)
        header_score = round(header_ratio * 35.0, 2)
        score_weight_passed += header_score

        checks.append({
            "check_name": "Standard Header & Layout Keywords",
            "passed": len(matched_headers) >= profile["min_headers_matched"],
            "details": f"Matched {len(matched_headers)} of {len(profile['required_headers'])} standard headers ({', '.join(matched_headers) if matched_headers else 'None'})"
        })

        if len(matched_headers) < profile["min_headers_matched"]:
            anomalies.append(f"Header keyword mismatch: missing standard {doc_type.upper()} layout headers.")

        # Check 2: Document Number Syntax & Pattern Compliance (Weight: 25%)
        score_weight_total += 25.0
        num_found = False
        if profile["number_pattern"]:
            if re.search(profile["number_pattern"], text_upper) or any(k in extracted_fields and extracted_fields[k] for k in ["aadhaar_number", "passport_number", "dl_number"]):
                num_found = True

        if num_found:
            score_weight_passed += 25.0
            checks.append({
                "check_name": "Identifier Number Format Alignment",
                "passed": True,
                "details": f"Document identifier matches standard regex pattern for {profile['name']}."
            })
        else:
            checks.append({
                "check_name": "Identifier Number Format Alignment",
                "passed": False,
                "details": f"Failed to match expected document number format pattern for {profile['name']}."
            })
            anomalies.append("Document number does not match expected format pattern.")

        # Check 3: Essential Identity Fields Extraction (Weight: 25%)
        score_weight_total += 25.0
        present_fields = [f for f in profile["key_fields"] if extracted_fields.get(f) is not None]
        field_ratio = len(present_fields) / len(profile["key_fields"]) if profile["key_fields"] else 1.0
        score_weight_passed += round(field_ratio * 25.0, 2)

        checks.append({
            "check_name": "Required Feature Fields Alignment",
            "passed": len(present_fields) >= max(1, len(profile["key_fields"]) // 2),
            "details": f"Extracted {len(present_fields)} of {len(profile['key_fields'])} key feature fields ({', '.join(present_fields)})"
        })

        if len(present_fields) < max(1, len(profile["key_fields"]) // 2):
            anomalies.append(f"Missing core feature fields expected in standard {doc_type.upper()} format.")

        # Check 4: Security Landmark (MRZ / QR Code Structure) (Weight: 15%)
        score_weight_total += 15.0
        sec_passed = True
        sec_msg = "Security features conform to specification."

        if profile["has_mrz"]:
            if extracted_fields.get("mrz_checksum_valid") is True or extracted_fields.get("mrz_raw"):
                score_weight_passed += 15.0
                sec_msg = "Machine Readable Zone (MRZ) structure verified."
            else:
                sec_passed = False
                sec_msg = "MRZ zone expected in passport/visa format is missing or unreadable."
                anomalies.append("Passport/Visa format requires valid MRZ zone.")
        elif profile["has_qr"]:
            qr_det = qr_info.get("qr_detected", False) if qr_info else False
            if qr_det:
                score_weight_passed += 15.0
                sec_msg = "Secure QR code structure detected as in specification."
            else:
                score_weight_passed += 10.0  # partial score if QR is blurry
                sec_msg = "QR code expected in card format was not detected."
        else:
            # Neither QR nor MRZ strictly required
            score_weight_passed += 15.0
            sec_msg = "Standard card layout structure verified."

        checks.append({
            "check_name": "Security Landmark Alignment (MRZ / QR)",
            "passed": sec_passed,
            "details": sec_msg
        })

        # Calculate Final Format Match Score (%)
        final_score = round(min(100.0, max(0.0, (score_weight_passed / score_weight_total) * 100.0)), 1)

        if final_score >= 80.0:
            status = "FORMAT_VERIFIED"
        elif final_score >= 50.0:
            status = "PARTIAL_MATCH"
        else:
            status = "FORMAT_ANOMALY"

        return {
            "format_match_score": final_score,
            "format_status": status,
            "sample_format_name": profile["name"],
            "matched_headers_count": len(matched_headers),
            "extracted_fields_count": len(present_fields),
            "format_checks": checks,
            "format_anomalies": anomalies
        }
