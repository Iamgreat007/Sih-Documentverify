import os
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple

class InputHandler:
    """
    Handles input document files (Images JPG/PNG and PDF documents).
    Converts PDFs page-by-page into OpenCV BGR numpy arrays.
    """

    SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    SUPPORTED_PDF_EXTS = {'.pdf'}

    @classmethod
    def load_document(cls, file_path: str) -> List[Tuple[int, np.ndarray]]:
        """
        Loads document from disk.
        Returns list of (page_num, bgr_image_array).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext in cls.SUPPORTED_IMAGE_EXTS:
            return cls._load_image(file_path)
        elif ext in cls.SUPPORTED_PDF_EXTS:
            return cls._load_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Supported: Images or PDF.")

    @staticmethod
    def _load_image(file_path: str) -> List[Tuple[int, np.ndarray]]:
        """Reads image via OpenCV or PIL fallback."""
        img = cv2.imread(file_path)
        if img is None:
            # Fallback to PIL for tricky image encodings
            pil_img = Image.open(file_path).convert('RGB')
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return [(1, img)]

    @staticmethod
    def _load_pdf(file_path: str) -> List[Tuple[int, np.ndarray]]:
        """Renders PDF pages to high-resolution (300 DPI) images using PyMuPDF."""
        pages = []
        doc = fitz.open(file_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            # Render at 300 DPI for high OCR accuracy
            zoom = 300 / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert PyMuPDF Pixmap to NumPy BGR Image
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, 3))
            bgr_img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            pages.append((page_idx + 1, bgr_img))
        doc.close()
        return pages
