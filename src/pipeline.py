import os
import json
import cv2
import base64
import numpy as np
from typing import Dict, Any, List, Optional

from src.input_handler import InputHandler
from src.preprocessor import ImagePreprocessor
from src.orientation import OrientationCorrector
from src.ocr_engine import OCREngine
from src.qr_decoder import QRDecoder
from src.doc_classifier import DocumentClassifier
from src.field_extractor import FieldExtractor
from src.format_checker import DocumentFormatChecker
from src.validators import DocumentValidator
from src.region_cropper import DocumentRegionCropper
from src.side_router import DocumentSideRules

class DocumentPipeline:
    """
    End-to-End Indian Identity Document OCR & Feature-Extraction Pipeline.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.ocr_engine = OCREngine()

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Processes an image or PDF document and saves output JSON.
        Returns list of structured document extraction results.
        """
        # Step 1: Load pages / images
        pages = InputHandler.load_document(file_path)
        results = []

        filename_base = os.path.splitext(os.path.basename(file_path))[0]

        for page_num, raw_image in pages:
            # Step 2: Image Quality Enhancement (Perspective Transform + CLAHE + Sharpening)
            prep_dict = ImagePreprocessor.preprocess_for_ocr(raw_image)
            enhanced_bgr = prep_dict["color_enhanced"]
            gray_ocr = prep_dict["gray"]

            # Step 3: Orientation & Skew Auto-Correction
            corrected_img, orientation_corrected, total_rotation_angle = OrientationCorrector.correct_orientation(gray_ocr)

            # Step 4: QR Code Decoding & Tampering Detection
            qr_info = QRDecoder.decode_qr(raw_image)

            # Step 5: Multi-Engine OCR Extraction (PaddleOCR + Tesseract Fallback)
            ocr_output = self.ocr_engine.extract_text(corrected_img)
            raw_ocr_text = ocr_output["raw_text"]
            text_blocks = ocr_output["text_blocks"]
            ocr_confidence = ocr_output["confidence_score"]

            # Step 6: Document Classification
            qr_payload = qr_info.get("payload", "") if qr_info else ""
            full_combined_text = raw_ocr_text + "\n" + qr_payload + "\n" + os.path.basename(file_path)

            doc_class = DocumentClassifier.classify(full_combined_text, qr_payload)
            doc_type = doc_class["document_type"]

            # Step 7: Structured Field Extraction
            extracted_fields = FieldExtractor.extract_fields(doc_type, full_combined_text, text_blocks, qr_info)

            # Step 8: Field Validation Status (pass/fail per field)
            val_status = DocumentValidator.validate_document(doc_type, extracted_fields)

            # Step 9: Cross-Check QR Data against Extracted Text (Module 3 Forgery Signal)
            qr_verification = QRDecoder.cross_check_qr_with_ocr(qr_info, extracted_fields)

            # Step 10: Format Similarity & Layout Verification against Sample Document Profiles
            format_verification = DocumentFormatChecker.verify_format(
                doc_type=doc_type,
                raw_text=full_combined_text,
                extracted_fields=extracted_fields,
                qr_info=qr_verification
            )

            # Step 11: Crop Visual Components & Save <documentname>_pic.jpg and <documentname>_qr.jpg
            crops = DocumentRegionCropper.crop_document_components(
                raw_image,
                doc_type=doc_type,
                side="auto",
                qr_info=qr_info,
                text_blocks=text_blocks,
                raw_text=full_combined_text
            )

            photo_path, photo_b64 = None, None
            qr_path, qr_b64 = None, None

            if crops.get("photo") is not None and crops["photo"].size > 0:
                p_out = os.path.join(self.output_dir, f"{filename_base}_pic.jpg")
                cv2.imwrite(p_out, crops["photo"])
                photo_path = p_out
                _, buffer = cv2.imencode('.jpg', crops["photo"])
                photo_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

            if crops.get("qr") is not None and crops["qr"].size > 0:
                q_out = os.path.join(self.output_dir, f"{filename_base}_qr.jpg")
                cv2.imwrite(q_out, crops["qr"])
                qr_path = q_out
                _, buffer = cv2.imencode('.jpg', crops["qr"])
                qr_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

            # Step 12: Assemble Structured Document Output JSON
            result_data = {
                "file_name": os.path.basename(file_path),
                "page_number": page_num,
                "document_type": doc_type,
                "document_name": doc_class["document_name"],
                "confidence": doc_class["confidence"],
                "orientation_corrected": orientation_corrected,
                "rotation_angle_deg": total_rotation_angle,
                "ocr_confidence": ocr_confidence,
                "extracted_fields": extracted_fields,
                "validation_status": val_status,
                "format_verification": format_verification,
                "tampering_detection": {
                    "qr_detected": qr_verification["qr_detected"],
                    "qr_data": qr_verification["qr_data"],
                    "qr_ocr_match": qr_verification["qr_ocr_match"],
                    "mismatches": qr_verification["mismatches"],
                    "mrz_valid": extracted_fields.get("mrz_checksum_valid"),
                    "aadhaar_checksum_valid": extracted_fields.get("aadhaar_number_valid")
                },
                "cropped_images": {
                    "photo_image_path": photo_path,
                    "photo_image_base64": photo_b64,
                    "qr_image_path": qr_path,
                    "qr_image_base64": qr_b64
                },
                "raw_ocr_text": raw_ocr_text,
                "text_blocks_count": len(text_blocks)
            }

            # Save individual JSON result
            out_file = os.path.join(self.output_dir, f"{filename_base}_p{page_num}_result.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)

            results.append(result_data)

        return results

    @classmethod
    def aggregate_multi_side_scans(cls, results_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merges front and back side captures of the same ID card (Aadhaar or Driving Licence)
        into a unified record.
        """
        if len(results_list) <= 1:
            return results_list

        front_res = None
        back_res = None
        other_results = []

        for res in results_list:
            doc_t = res.get("document_type", "unknown")
            fields = res.get("extracted_fields", {})
            
            # Check if this image looks like front side (has name/dob/photo) vs back side (has address/qr)
            is_front = bool(fields.get("name") or fields.get("dob") or fields.get("gender"))
            is_back = bool(fields.get("address")) or res.get("tampering_detection", {}).get("qr_detected")

            if is_front and not front_res:
                front_res = res
            elif is_back and not back_res:
                back_res = res
            else:
                other_results.append(res)

        if front_res and back_res and front_res["document_type"] == back_res["document_type"]:
            merged_fields = front_res["extracted_fields"].copy()
            for k, v in back_res["extracted_fields"].items():
                if v and not merged_fields.get(k):
                    merged_fields[k] = v

            merged_record = front_res.copy()
            merged_record["document_name"] = f"{front_res['document_name']} (Front + Back Merged)"
            merged_record["extracted_fields"] = merged_fields
            merged_record["raw_ocr_text"] += "\n--- BACK SIDE ---\n" + back_res["raw_ocr_text"]
            merged_record["tampering_detection"]["back_qr_data"] = back_res["tampering_detection"].get("qr_data")
            
            # Merge cropped images from both sides
            front_crops = front_res.get("cropped_images", {})
            back_crops = back_res.get("cropped_images", {})
            merged_record["cropped_images"] = {
                "photo_image_path": front_crops.get("photo_image_path"),
                "photo_image_base64": front_crops.get("photo_image_base64"),
                "qr_image_path": back_crops.get("qr_image_path") or front_crops.get("qr_image_path"),
                "qr_image_base64": back_crops.get("qr_image_base64") or front_crops.get("qr_image_base64")
            }
            return [merged_record] + other_results

        return results_list

    @classmethod
    def aggregate_multi_side_dl(cls, results_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Backwards compatibility alias for aggregate_multi_side_scans."""
        return cls.aggregate_multi_side_scans(results_list)

    def process_scanned_sides(self, front_path: Optional[str] = None, back_path: Optional[str] = None, doc_type: str = "auto") -> Dict[str, Any]:
        """
        Scanner Input Processing Pipeline:
        Processes 1 or 2 scanned images (Front side and/or Back side).
        Strictly applies DocumentSideRules:
          - Front side -> Photo Box + Front text fields (Name, DOB, Sex, UID). NO QR search.
          - Back side -> 2D QR Code Box + Back text fields (Address, UID). NO Photo search.
          - Passport -> Photo Box + Text + MRZ. NO QR search.
        Saves cropped <documentname>_pic.jpg and <documentname>_qr.jpg to output directory.
        """
        combined_fields = {}
        photo_path = None
        photo_b64 = None
        qr_path = None
        qr_b64 = None

        detected_doc_type = doc_type if doc_type != "auto" else "aadhaar"
        doc_name = detected_doc_type.upper()
        overall_confidence = 90.0

        # 1. Process Front Side Image
        if front_path and os.path.exists(front_path):
            front_pages = InputHandler.load_document(front_path)
            if front_pages:
                front_img = front_pages[0][1]
                prep_dict = ImagePreprocessor.preprocess_for_ocr(front_img)
                corrected_img, _, _ = OrientationCorrector.correct_orientation(prep_dict["gray"])
                ocr_out = self.ocr_engine.extract_text(corrected_img)
                raw_text = ocr_out["raw_text"]
                text_blocks = ocr_out["text_blocks"]

                if doc_type == "auto":
                    doc_class = DocumentClassifier.classify(raw_text, "")
                    detected_doc_type = doc_class["document_type"]
                    doc_name = doc_class["document_name"]
                    overall_confidence = doc_class["confidence"]

                # Extract front fields
                front_fields = FieldExtractor.extract_fields(detected_doc_type, raw_text, text_blocks, None)
                combined_fields.update(front_fields)

                # Crop front visual components (Photo Box, NO QR on front)
                crops = DocumentRegionCropper.crop_document_components(
                    front_img, 
                    doc_type=detected_doc_type, 
                    side="front", 
                    text_blocks=text_blocks, 
                    raw_text=raw_text
                )

                if crops.get("photo") is not None and crops["photo"].size > 0:
                    filename_base = os.path.splitext(os.path.basename(front_path))[0]
                    p_out = os.path.join(self.output_dir, f"{filename_base}_pic.jpg")
                    cv2.imwrite(p_out, crops["photo"])
                    photo_path = p_out
                    _, buffer = cv2.imencode('.jpg', crops["photo"])
                    photo_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

        # 2. Process Back Side Image (or Single Passport Image if front_path provided for passport)
        if back_path and os.path.exists(back_path):
            back_pages = InputHandler.load_document(back_path)
            if back_pages:
                back_img = back_pages[0][1]
                prep_dict = ImagePreprocessor.preprocess_for_ocr(back_img)
                corrected_img, _, _ = OrientationCorrector.correct_orientation(prep_dict["gray"])
                
                qr_info = QRDecoder.decode_qr(back_img)
                ocr_out = self.ocr_engine.extract_text(corrected_img)
                raw_text = ocr_out["raw_text"]
                text_blocks = ocr_out["text_blocks"]

                # Extract back fields
                back_fields = FieldExtractor.extract_fields(detected_doc_type, raw_text, text_blocks, qr_info)
                for k, v in back_fields.items():
                    if v and not combined_fields.get(k):
                        combined_fields[k] = v

                # Crop back visual components (2D QR Code Box, NO Photo on back)
                crops = DocumentRegionCropper.crop_document_components(
                    back_img, 
                    doc_type=detected_doc_type, 
                    side="back", 
                    qr_info=qr_info, 
                    text_blocks=text_blocks, 
                    raw_text=raw_text
                )

                if crops.get("qr") is not None and crops["qr"].size > 0:
                    filename_base = os.path.splitext(os.path.basename(back_path))[0]
                    q_out = os.path.join(self.output_dir, f"{filename_base}_qr.jpg")
                    cv2.imwrite(q_out, crops["qr"])
                    qr_path = q_out
                    _, buffer = cv2.imencode('.jpg', crops["qr"])
                    qr_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

        # If Passport (single image), extract MRZ and Photo
        if detected_doc_type == "passport" and front_path and not back_path:
            # Passport single image crop
            front_pages = InputHandler.load_document(front_path)
            if front_pages:
                p_img = front_pages[0][1]
                crops = DocumentRegionCropper.crop_document_components(p_img, doc_type="passport", side="front")
                if crops.get("photo") is not None and crops["photo"].size > 0:
                    filename_base = os.path.splitext(os.path.basename(front_path))[0]
                    p_out = os.path.join(self.output_dir, f"{filename_base}_pic.jpg")
                    cv2.imwrite(p_out, crops["photo"])
                    photo_path = p_out
                    _, buffer = cv2.imencode('.jpg', crops["photo"])
                    photo_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

        val_status = DocumentValidator.validate_document(detected_doc_type, combined_fields)

        final_json = {
            "document_type": detected_doc_type,
            "document_name": doc_name,
            "confidence": overall_confidence,
            "extracted_fields": combined_fields,
            "validation_status": val_status,
            "cropped_images": {
                "photo_image_path": photo_path,
                "photo_image_base64": photo_b64,
                "qr_image_path": qr_path,
                "qr_image_base64": qr_b64
            }
        }

        # Save consolidated output JSON file
        out_base = os.path.splitext(os.path.basename(front_path or back_path or "scan"))[0]
        json_file_path = os.path.join(self.output_dir, f"{out_base}_consolidated_result.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)

        final_json["output_json_path"] = json_file_path
        return final_json


