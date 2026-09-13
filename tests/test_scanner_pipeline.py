import pytest
import os
import cv2
import numpy as np
from src.pipeline import DocumentPipeline
from src.side_router import DocumentSideRules
from src.region_cropper import DocumentRegionCropper

@pytest.fixture
def temp_scanner_images(tmp_path):
    # Front Aadhaar Image (with synthetic photo box)
    front_img = np.ones((400, 650, 3), dtype=np.uint8) * 255
    cv2.putText(front_img, "GOVERNMENT OF INDIA", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(front_img, "Name: Vilas Rakhe", (250, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(front_img, "DOB: 15/08/1990", (250, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(front_img, "MALE", (250, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(front_img, "5486 3215 9874", (200, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    # Synthetic face box on front left
    front_img[80:260, 40:200] = [180, 150, 120]

    front_path = str(tmp_path / "scan_aadhaar_front.jpg")
    cv2.imwrite(front_path, front_img)

    # Back Aadhaar Image (with synthetic 2D QR grid)
    back_img = np.ones((400, 650, 3), dtype=np.uint8) * 255
    cv2.putText(back_img, "Address: House 123, Street 5, Delhi 110001", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(back_img, "5486 3215 9874", (200, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    # Synthetic QR grid on back right
    cell = 15
    for i in range(100, 260, cell):
        for j in range(450, 600, cell):
            if (i // cell + j // cell) % 2 == 0:
                back_img[i:i+cell, j:j+cell] = [0, 0, 0]

    back_path = str(tmp_path / "scan_aadhaar_back.jpg")
    cv2.imwrite(back_path, back_img)

    # Passport Image
    pass_img = np.ones((500, 750, 3), dtype=np.uint8) * 255
    cv2.putText(pass_img, "PASSPORT REPUBLIC OF INDIA", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(pass_img, "P<INDRAKHE<<VILAS<<<<<<<<<<<<<<<<<<<<<<<<<<<", (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(pass_img, "Z1234567<8IND9008154M3001019<<<<<<<<<<<<<<06", (50, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    pass_img[90:290, 50:210] = [180, 150, 120]

    pass_path = str(tmp_path / "scan_passport.jpg")
    cv2.imwrite(pass_path, pass_img)

    return front_path, back_path, pass_path

def test_document_side_rules():
    # Aadhaar Front: QR search disabled
    rules_af = DocumentSideRules.get_rules("aadhaar", side="front")
    assert rules_af["extract_photo"] is True
    assert rules_af["extract_qr"] is False

    # Aadhaar Back: Photo search disabled, QR search enabled
    rules_ab = DocumentSideRules.get_rules("aadhaar", side="back")
    assert rules_ab["extract_photo"] is False
    assert rules_ab["extract_qr"] is True

    # Passport: QR search disabled
    rules_p = DocumentSideRules.get_rules("passport", side="front")
    assert rules_p["extract_qr"] is False
    assert rules_p["extract_mrz"] is True

def test_scanner_pipeline_aadhaar_dual_side(temp_scanner_images, tmp_path):
    front_p, back_p, _ = temp_scanner_images
    pipeline = DocumentPipeline(output_dir=str(tmp_path / "output"))

    result = pipeline.process_scanned_sides(front_path=front_p, back_path=back_p, doc_type="aadhaar")

    assert result["document_type"] == "aadhaar"
    assert "extracted_fields" in result
    assert "cropped_images" in result
    
    crops = result["cropped_images"]
    assert crops["photo_image_path"] is not None
    assert crops["photo_image_path"].endswith("_pic.jpg")
    assert os.path.exists(crops["photo_image_path"])
    assert crops["photo_image_base64"] is not None
    assert crops["qr_image_path"] is not None
    assert crops["qr_image_path"].endswith("_qr.jpg")
    assert os.path.exists(crops["qr_image_path"])
    assert crops["qr_image_base64"] is not None

    # Check JSON output file was generated
    assert os.path.exists(result["output_json_path"])

def test_scanner_pipeline_passport_no_qr(temp_scanner_images, tmp_path):
    _, _, pass_p = temp_scanner_images
    pipeline = DocumentPipeline(output_dir=str(tmp_path / "output"))

    result = pipeline.process_scanned_sides(front_path=pass_p, doc_type="passport")

    assert result["document_type"] == "passport"
    crops = result["cropped_images"]
    assert crops["photo_image_path"] is not None
    assert crops["photo_image_path"].endswith("_pic.jpg")
    assert os.path.exists(crops["photo_image_path"])
    assert crops["photo_image_base64"] is not None
    # QR image should be None for Passport!
    assert crops["qr_image_path"] is None
    assert crops["qr_image_base64"] is None
