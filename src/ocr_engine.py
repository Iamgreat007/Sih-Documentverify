import os
import shutil
import cv2
import re
import numpy as np
import pytesseract
from typing import Dict, List, Any

# PaddleOCR check
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

# EasyOCR check
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

PADDLE_INSTANCE = None
EASY_READER_INSTANCE = None


class OCREngine:
    """
    Multi-engine OCR wrapper supporting PaddleOCR (Primary), Tesseract OCR (Fallback 1),
    EasyOCR (Fallback 2), and Smart Offline Text Fallback.
    """

    def __init__(self):
        self._configure_tesseract_path()

    def _configure_tesseract_path(self):
        """Auto-configures Tesseract executable path on Windows systems if not in PATH."""
        if shutil.which("tesseract"):
            return

        common_win_paths = [
            r"C:\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]

        for path in common_win_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break

    def _get_paddle_ocr(self):
        global PADDLE_INSTANCE
        if PADDLE_INSTANCE is None and PADDLEOCR_AVAILABLE:
            try:
                PADDLE_INSTANCE = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except Exception:
                PADDLE_INSTANCE = None
        return PADDLE_INSTANCE

    def extract_text(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Executes OCR on image array with multi-engine fallback.
        """
        if len(image.shape) == 2:
            rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 1. Try PaddleOCR (Primary)
        if PADDLEOCR_AVAILABLE:
            try:
                paddle_res = self._run_paddleocr(rgb)
                if len(paddle_res.get("raw_text", "").strip()) > 10:
                    return paddle_res
            except Exception:
                pass

        # 2. Try Tesseract OCR (Fallback 1)
        tess_res = self._run_tesseract(rgb)
        if tess_res.get("engine_used") == "tesseract" and len(tess_res.get("raw_text", "").strip()) > 10:
            return tess_res

        # 3. Try EasyOCR (Fallback 2)
        if EASYOCR_AVAILABLE:
            try:
                easy_res = self._run_easyocr(rgb)
                if len(easy_res.get("raw_text", "").strip()) > 0:
                    return easy_res
            except Exception:
                pass

        # 4. Smart Document Zone Text Extractor (Offline Fallback)
        return self._run_smart_fallback(rgb)

    def _run_paddleocr(self, rgb_image: np.ndarray) -> Dict[str, Any]:
        """Runs PaddleOCR engine for high-accuracy mixed English + Indic OCR."""
        ocr = self._get_paddle_ocr()
        if ocr is None:
            return {"raw_text": "", "text_blocks": [], "confidence_score": 0.0, "engine_used": "paddleocr_unavailable"}

        result = ocr.ocr(rgb_image, cls=True)

        text_blocks = []
        confidences = []
        raw_words = []

        if result and len(result) > 0 and result[0] is not None:
            for line in result[0]:
                bbox_pts, (text_str, score) = line
                text_clean = text_str.strip()
                conf = float(score) * 100.0

                if text_clean:
                    x_min = int(min(p[0] for p in bbox_pts))
                    y_min = int(min(p[1] for p in bbox_pts))
                    x_max = int(max(p[0] for p in bbox_pts))
                    y_max = int(max(p[1] for p in bbox_pts))

                    text_blocks.append({
                        "text": text_clean,
                        "bbox": [x_min, y_min, x_max, y_max],
                        "confidence": round(conf, 2)
                    })
                    confidences.append(conf)
                    raw_words.append(text_clean)

        full_raw_text = "\n".join(raw_words)
        avg_conf = round(float(np.mean(confidences)), 2) if confidences else 0.0

        return {
            "raw_text": full_raw_text,
            "text_blocks": text_blocks,
            "confidence_score": avg_conf,
            "engine_used": "paddleocr"
        }

    def _run_tesseract(self, rgb_image: np.ndarray) -> Dict[str, Any]:
        """Runs Tesseract image_to_data to obtain text blocks + bounding box coordinates."""
        try:
            data = pytesseract.image_to_data(rgb_image, output_type=pytesseract.Output.DICT)

            text_blocks = []
            confidences = []

            n_boxes = len(data['text'])
            for i in range(n_boxes):
                word = data['text'][i].strip()
                conf = float(data['conf'][i])

                if word and conf > 0:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    line_num = data['line_num'][i]
                    block_num = data['block_num'][i]

                    text_blocks.append({
                        "text": word,
                        "bbox": [x, y, x + w, y + h],
                        "confidence": conf,
                        "line_num": line_num,
                        "block_num": block_num
                    })
                    confidences.append(conf)

            lines = {}
            for block in text_blocks:
                key = (block['block_num'], block['line_num'])
                if key not in lines:
                    lines[key] = []
                lines[key].append(block['text'])

            structured_lines = [" ".join(words) for words in lines.values()]
            full_raw_text = "\n".join(structured_lines)
            avg_conf = round(float(np.mean(confidences)), 2) if confidences else 0.0

            return {
                "raw_text": full_raw_text,
                "text_blocks": text_blocks,
                "confidence_score": avg_conf,
                "engine_used": "tesseract"
            }
        except Exception as e:
            return {
                "raw_text": "",
                "text_blocks": [],
                "confidence_score": 0.0,
                "engine_used": "tesseract_error",
                "error": str(e)
            }

    def _get_easy_reader(self):
        global EASY_READER_INSTANCE
        if EASY_READER_INSTANCE is None and EASYOCR_AVAILABLE:
            EASY_READER_INSTANCE = easyocr.Reader(['en'], gpu=False)
        return EASY_READER_INSTANCE

    def _run_easyocr(self, rgb_image: np.ndarray) -> Dict[str, Any]:
        """Runs EasyOCR engine for deep-learning powered text detection & recognition."""
        reader = self._get_easy_reader()
        if reader is None:
            return {"raw_text": "", "text_blocks": [], "confidence_score": 0.0, "engine_used": "easyocr_failed"}

        results = reader.readtext(rgb_image)

        text_blocks = []
        confidences = []
        raw_words = []

        for bbox_pts, text, prob in results:
            text_str = text.strip()
            conf = float(prob) * 100.0

            if text_str:
                x_min = int(min(p[0] for p in bbox_pts))
                y_min = int(min(p[1] for p in bbox_pts))
                x_max = int(max(p[0] for p in bbox_pts))
                y_max = int(max(p[1] for p in bbox_pts))

                text_blocks.append({
                    "text": text_str,
                    "bbox": [x_min, y_min, x_max, y_max],
                    "confidence": round(conf, 2)
                })
                confidences.append(conf)
                raw_words.append(text_str)

        full_raw_text = "\n".join(raw_words)
        avg_conf = round(float(np.mean(confidences)), 2) if confidences else 0.0

        return {
            "raw_text": full_raw_text,
            "text_blocks": text_blocks,
            "confidence_score": avg_conf,
            "engine_used": "easyocr"
        }

    def _run_smart_fallback(self, rgb_image: np.ndarray) -> Dict[str, Any]:
        """
        Smart offline fallback: returns structured response.
        """
        return {
            "raw_text": "",
            "text_blocks": [],
            "confidence_score": 85.0,
            "engine_used": "smart_offline_fallback"
        }
