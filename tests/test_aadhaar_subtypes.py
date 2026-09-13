import pytest
import cv2
import numpy as np
from src.region_cropper import DocumentRegionCropper

def create_synthetic_qr_image(size=(200, 200)):
    """Generates a synthetic high-contrast binary 2D grid resembling a QR code."""
    np.random.seed(42)
    qr = np.zeros(size, dtype=np.uint8)
    cell = size[0] // 10
    for i in range(0, size[0], cell):
        for j in range(0, size[1], cell):
            if (i // cell + j // cell) % 2 == 0:
                qr[i:i+cell, j:j+cell] = 255
    # Add finder pattern boxes at corners
    qr[10:50, 10:50] = 255
    qr[20:40, 20:40] = 0
    qr[10:50, size[1]-50:size[1]-10] = 255
    qr[20:40, size[1]-40:size[1]-20] = 0
    qr[size[0]-50:size[0]-10, 10:50] = 255
    qr[size[0]-40:size[0]-20, 20:40] = 0
    return cv2.cvtColor(qr, cv2.COLOR_GRAY2BGR)

def create_synthetic_photo_image(size=(200, 160)):
    """Generates a smooth gradient portrait image (resembling a face photo)."""
    img = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    for y in range(size[0]):
        for x in range(size[1]):
            img[y, x] = [180 + (y % 30), 150 + (x % 30), 120 + ((x + y) % 20)]
    # Draw simple head shape
    cv2.ellipse(img, (size[1]//2, size[0]//2), (40, 50), 0, 0, 360, (100, 100, 100), -1)
    return img

def test_aadhaar_subtype_classification():
    # 1. Full e-Aadhaar A4 (Tall portrait H > W)
    a4_img = np.ones((1000, 700, 3), dtype=np.uint8) * 255
    sub_a4 = DocumentRegionCropper.detect_aadhaar_subtype(a4_img, raw_text="UNIQUE IDENTIFICATION AUTHORITY OF INDIA ENROLMENT NO")
    assert sub_a4 == "full_e_aadhaar"

    # 2. Cut-Out Dual Card (Wide landscape W > H, aspect ratio ~ 2.0)
    cutout_img = np.ones((350, 750, 3), dtype=np.uint8) * 255
    sub_cutout = DocumentRegionCropper.detect_aadhaar_subtype(cutout_img)
    assert sub_cutout == "cut_out_dual_card"

    # 3. Stacked Dual Card (Square-ish H > W, aspect ratio ~ 1.0)
    stacked_img = np.ones((600, 550, 3), dtype=np.uint8) * 255
    sub_stacked = DocumentRegionCropper.detect_aadhaar_subtype(stacked_img)
    assert sub_stacked == "stacked_dual_card"

    # 4. Single Card Back (Address text present, no face photo)
    back_img = np.ones((300, 480, 3), dtype=np.uint8) * 255
    sub_back = DocumentRegionCropper.detect_aadhaar_subtype(back_img, raw_text="ADDRESS S/O JOHN DOE PIN 560001")
    assert sub_back == "single_card_back"

def test_qr_vs_photo_disambiguation():
    # Create image with ONLY a face photo (No QR code)
    photo_only_img = np.ones((400, 600, 3), dtype=np.uint8) * 240
    photo = create_synthetic_photo_image((150, 120))
    photo_only_img[50:200, 50:170] = photo

    # Photo cropping should succeed or return valid candidate
    photo_crop = DocumentRegionCropper.crop_face_photo(photo_only_img, subtype="single_card_front")
    
    # QR Code cropping MUST return None (Must NOT crop the photo as QR code!)
    qr_crop = DocumentRegionCropper.crop_qr_code(photo_only_img, subtype="single_card_front")
    assert qr_crop is None

def test_qr_code_detection_synthetic():
    # Create image with a synthetic QR code on right side
    qr_img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    qr_pattern = create_synthetic_qr_image((160, 160))
    qr_img[50:210, 400:560] = qr_pattern

    qr_crop = DocumentRegionCropper.crop_qr_code(qr_img, subtype="single_card_back")
    assert qr_crop is not None
    assert qr_crop.shape[0] >= 30 and qr_crop.shape[1] >= 30

def test_single_card_back_returns_no_face_photo():
    # Single back side of Aadhaar card has NO face photo
    back_img = np.ones((350, 550, 3), dtype=np.uint8) * 255
    photo_crop = DocumentRegionCropper.crop_face_photo(back_img, subtype="single_card_back")
    assert photo_crop is None
