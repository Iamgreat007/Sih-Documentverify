import io
import unittest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from api.main import app

class TestFastAPIEndpoint(unittest.TestCase):
    """
    Unit tests for FastAPI POST /extract endpoint.
    """

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_unsupported_file_type(self):
        response = self.client.post(
            "/extract",
            files={"file": ("test.txt", b"plain text data", "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        json_resp = response.json()
        self.assertTrue(json_resp.get("error"))
        self.assertIn("Unsupported file format", json_resp.get("message"))

    def test_synthetic_image_upload(self):
        # Create a simple synthetic image in memory
        img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "GOVERNMENT OF INDIA AADHAAR", fill=(0, 0, 0))
        d.text((10, 50), "8366 9639 3224", fill=(0, 0, 0))

        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)

        response = self.client.post(
            "/extract",
            files={"file": ("aadhaar_test.jpg", buf.getvalue(), "image/jpeg")}
        )
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertIn("document_type", res)
        self.assertIn("extracted_fields", res)
        self.assertIn("validation_status", res)

if __name__ == "__main__":
    unittest.main()
