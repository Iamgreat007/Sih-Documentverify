import unittest
from src.mrz_parser import MRZParser

class TestMRZParser(unittest.TestCase):
    """
    Unit tests for ICAO 9303 MRZ parsing and check digit validation.
    """

    def test_parse_valid_passport_mrz(self):
        mrz_lines = [
            "P<INDTESTER<<JANE<<<<<<<<<<<<<<<<<<<<<<<<<<",
            "L6027710<4IND8305295M2311241<<<<<<<<<<<<<<8"
        ]
        parsed = MRZParser.parse_mrz_lines(mrz_lines)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get("passport_number"), "L6027710")
        self.assertEqual(parsed.get("surname"), "TESTER")
        self.assertEqual(parsed.get("given_name"), "JANE")
        self.assertTrue(parsed.get("mrz_checksum_valid"))

    def test_parse_valid_visa_mrz(self):
        mrz_lines = [
            "VTINDTESTER<<JANE<SMITH<<<<<<<<<<<<<<<<<<<<",
            "VJDCHCC<<AUS9310140M1706262AUS<<<<<<<<<<<8"
        ]
        parsed = MRZParser.parse_mrz_lines(mrz_lines)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed.get("mrz_checksum_valid"))

if __name__ == "__main__":
    unittest.main()
