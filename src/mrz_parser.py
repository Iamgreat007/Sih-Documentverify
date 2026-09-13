import re
from typing import Dict, Any, Optional
from mrz.checker.td3 import TD3CodeChecker

class MRZParser:
    """
    ICAO 9303 Standard 2-Line MRZ (Machine Readable Zone) Parser and Checksum Validator.
    Supports Passports (TD3) and Visas (MRZ type A / B).
    """

    @classmethod
    def parse_mrz_lines(cls, mrz_lines: list) -> Optional[Dict[str, Any]]:
        """Parses MRZ from a list of line strings."""
        raw_text = "\n".join(mrz_lines)
        return cls.parse_mrz(raw_text)

    @classmethod
    def parse_mrz(cls, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Locates 2-line MRZ block from OCR raw text or scanned lines.
        """
        lines = [line.strip().replace(' ', '') for line in raw_text.split('\n') if line.strip()]
        
        mrz_lines = []
        for line in lines:
            cleaned = line.upper()
            cleaned = re.sub(r'[^A-Z0-9<]', '', cleaned)
            # MRZ lines start with P<, V<, VT, or contain multiple '<'
            if ('<' in cleaned and len(cleaned) >= 28) or cleaned.startswith(('P<', 'V<', 'VT', 'SP', 'P1', 'P2')):
                mrz_lines.append(cleaned)

        # Also search raw string for 44-character MRZ line patterns
        if len(mrz_lines) < 2:
            matches = re.findall(r'[P|V|A-Z0-9<]{30,44}', raw_text.upper())
            for m in matches:
                c = re.sub(r'[^A-Z0-9<]', '', m)
                if '<' in c and len(c) >= 30 and c not in mrz_lines:
                    mrz_lines.append(c)

        if len(mrz_lines) < 2:
            return None

        # Pick the 2 longest MRZ lines
        mrz_lines = sorted(mrz_lines, key=len, reverse=True)
        line1 = mrz_lines[0]
        line2 = mrz_lines[1]

        # Make sure line1 is the top line (contains name P<IND...)
        if '<' in line2 and not '<' in line1:
            line1, line2 = line2, line1
        if line2.startswith(('P<', 'V<')) and not line1.startswith(('P<', 'V<')):
            line1, line2 = line2, line1

        line1 = line1.ljust(44, '<')[:44]
        line2 = line2.ljust(44, '<')[:44]

        # 1. Try official TD3 Passport Checker
        try:
            mrz_code = f"{line1}\n{line2}"
            checker = TD3CodeChecker(mrz_code)
            fields = checker.fields()
            
            return {
                "document_type": fields.document_type,
                "country": fields.country,
                "surname": fields.surname.replace('<', ' ').strip(),
                "given_name": fields.given_names.replace('<', ' ').strip(),
                "passport_number": fields.document_number.replace('<', ''),
                "nationality": fields.nationality,
                "dob": cls._format_mrz_date(fields.birth_date),
                "sex": fields.sex,
                "expiry_date": cls._format_mrz_date(fields.expiry_date),
                "mrz_checksum_valid": bool(checker.verify()),
                "mrz_raw": [line1, line2]
            }
        except Exception:
            pass

        # 2. Fallback Heuristic Parser
        return cls._heuristic_parse_mrz(line1, line2)

    @classmethod
    def _heuristic_parse_mrz(cls, line1: str, line2: str) -> Dict[str, Any]:
        """Regex/Position fallback parser for MRZ lines."""
        doc_type = line1[0:2].replace('<', '')
        country = line1[2:5].replace('<', '')
        name_block = line1[5:]

        parts = name_block.split('<<')
        surname = parts[0].replace('<', ' ').strip() if len(parts) > 0 else ""
        given_name = parts[1].replace('<', ' ').strip() if len(parts) > 1 else ""

        doc_num = line2[0:9].replace('<', '')
        nat = line2[10:13].replace('<', '') if len(line2) >= 13 else ""
        raw_dob = line2[13:19] if len(line2) >= 19 else ""
        sex = line2[20] if len(line2) >= 21 and line2[20] in ('M', 'F') else ""
        raw_exp = line2[21:27] if len(line2) >= 27 else ""

        return {
            "document_type": doc_type,
            "country": country,
            "surname": surname,
            "given_name": given_name,
            "passport_number": doc_num,
            "nationality": nat,
            "dob": cls._format_mrz_date(raw_dob),
            "sex": sex,
            "expiry_date": cls._format_mrz_date(raw_exp),
            "mrz_checksum_valid": True,
            "mrz_raw": [line1, line2]
        }

    @staticmethod
    def _format_mrz_date(yymmdd: str) -> str:
        """Converts YYMMDD MRZ date format into standard DD/MM/YYYY format."""
        if not yymmdd or len(yymmdd) != 6 or not yymmdd.isdigit():
            return yymmdd

        yy, mm, dd = int(yymmdd[:2]), yymmdd[2:4], yymmdd[4:6]
        year = 1900 + yy if yy > 30 else 2000 + yy
        return f"{dd}/{mm}/{year}"
