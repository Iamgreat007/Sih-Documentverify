import unittest
from src.extractors.aadhaar import AadhaarExtractor
from src.extractors.passport import PassportExtractor
from src.extractors.dl import DLExtractor
from src.extractors.visa import VisaExtractor

class TestDynamicNameExtraction(unittest.TestCase):
    """
    Unit tests for dynamic non-hardcoded name extractions across all document types.
    """

    def test_aadhaar_mixed_case_name(self):
        ocr_text = """
        भारत सरकार
        Government of India
        विलास राखे
        Vilas Rakhe
        जन्म तारीख/DOB: 30/05/1995
        पुरुष/ MALE
        7730 0889 2163
        """
        extractor = AadhaarExtractor()
        res = extractor.extract(ocr_text, [])
        self.assertEqual(res.get("name"), "Vilas Rakhe")
        self.assertEqual(res.get("aadhaar_number"), "773008892163")
        self.assertEqual(res.get("dob"), "30/05/1995")
        self.assertEqual(res.get("gender"), "MALE")

    def test_aadhaar_devnagari_combined_line(self):
        ocr_text = """
        Government of India
        अनिल कुमार / Anil Kumar
        DOB: 15/08/1988
        MALE
        8366 9639 3224
        """
        extractor = AadhaarExtractor()
        res = extractor.extract(ocr_text, [])
        self.assertEqual(res.get("name"), "Anil Kumar")

    def test_dl_dynamic_name(self):
        ocr_text = """
        INDIAN UNION DRIVING LICENCE
        DL NO TS00820260009319
        Name: Rajesh Varma
        DOB: 10/09/1990
        S/O: Suresh Varma
        """
        extractor = DLExtractor()
        res = extractor.extract(ocr_text, [])
        self.assertEqual(res.get("name"), "Rajesh Varma")
        self.assertEqual(res.get("dl_number"), "TS00820260009319")

    def test_passport_text_fallback_name(self):
        ocr_text = """
        PASSPORT REPUBLIC OF INDIA
        Given Name: Garima
        Surname: Thapliyal
        DOB: 01/07/1994
        Sex: F
        """
        extractor = PassportExtractor()
        res = extractor.extract(ocr_text, [])
        self.assertEqual(res.get("name"), "Garima Thapliyal")

if __name__ == "__main__":
    unittest.main()
