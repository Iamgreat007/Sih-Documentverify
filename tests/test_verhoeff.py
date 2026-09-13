import unittest
from src.verhoeff import Verhoeff

class TestVerhoeffChecksum(unittest.TestCase):
    """
    Unit tests for Verhoeff Checksum Algorithm used in Aadhaar UID validation.
    """

    def test_valid_verhoeff_uids(self):
        valid_uids = [
            "836696393224",
            "556998868624"
        ]
        for uid in valid_uids:
            self.assertTrue(Verhoeff.validate(uid), f"UID {uid} should be valid")

    def test_invalid_verhoeff_uids(self):
        invalid_uids = [
            "123456789012",
            "111111111111",
            "000000000000"
        ]
        for uid in invalid_uids:
            self.assertFalse(Verhoeff.validate(uid), f"UID {uid} should be invalid")

if __name__ == "__main__":
    unittest.main()
