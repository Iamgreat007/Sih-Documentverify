import unittest
from src.doc_classifier import DocumentClassifier

class TestDocumentClassifier(unittest.TestCase):
    """
    Unit tests for document classifier heuristics.
    """

    def test_classify_aadhaar(self):
        text = "UNIQUE IDENTIFICATION AUTHORITY OF INDIA Government of India Aadhaar 8366 9639 3224 Male DOB: 20/06/1986"
        res = DocumentClassifier.classify(text)
        self.assertEqual(res["document_type"], "aadhaar")
        self.assertGreaterEqual(res["confidence"], 50.0)

    def test_classify_passport(self):
        text = "PASSPORT REPUBLIC OF INDIA P<INDDOE<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< L1234567"
        res = DocumentClassifier.classify(text)
        self.assertEqual(res["document_type"], "passport")
        self.assertGreaterEqual(res["confidence"], 50.0)

    def test_classify_driving_licence(self):
        text = "UNION DRIVING LICENCE LICENCING AUTHORITY DL NO DL1420110012345 CLASS OF VEHICLE MCWG LMV"
        res = DocumentClassifier.classify(text)
        self.assertIn(res["document_type"], ["driving_licence", "dl"])
        self.assertGreaterEqual(res["confidence"], 50.0)

    def test_classify_visa(self):
        text = "INDIAN VISA VISA TYPE TOURIST NO OF ENTRIES SINGLE VTINDDOE<<JOHN"
        res = DocumentClassifier.classify(text)
        self.assertEqual(res["document_type"], "visa")

    def test_classify_unknown(self):
        text = "Random unclassified plain text without any document landmarks"
        res = DocumentClassifier.classify(text)
        self.assertEqual(res["document_type"], "unknown")
        self.assertEqual(res["confidence"], 0.0)

if __name__ == "__main__":
    unittest.main()
