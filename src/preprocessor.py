import cv2
import numpy as np

class ImagePreprocessor:
    """
    Image quality enhancement & document boundary alignment pipeline.
    Includes perspective transform de-skewing, CLAHE contrast enhancement,
    unsharp mask sharpening, and edge-preserving denoising.
    """

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Orders coordinates: [top-left, top-right, bottom-right, bottom-left].
        """
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    @classmethod
    def four_point_transform(cls, image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """
        Warp image using perspective transform given 4 quad points.
        """
        rect = cls.order_points(pts)
        (tl, tr, br, bl) = rect

        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        return warped

    @classmethod
    def detect_and_deskew_boundary(cls, image: np.ndarray) -> np.ndarray:
        """
        Detects document boundary using contour analysis and applies 4-point perspective transform.
        """
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blur, 75, 200)

            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)

                # Check if contour is a 4-point polygon covering significant area
                if len(approx) == 4 and cv2.contourArea(c) > (h * w * 0.15):
                    pts = approx.reshape(4, 2)
                    return cls.four_point_transform(image, pts)
        except Exception:
            pass

        return image

    @staticmethod
    def enhance_contrast_clahe(image: np.ndarray, clip_limit: float = 2.0, tile_grid_size=(8, 8)) -> np.ndarray:
        """Apply CLAHE on the luminance channel (LAB color space)."""
        if len(image.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            return clahe.apply(image)
        
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    @staticmethod
    def sharpen(image: np.ndarray, strength: float = 1.5) -> np.ndarray:
        """Sharpen image using Unsharp Masking technique."""
        blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=3)
        sharpened = cv2.addWeighted(image, strength, blurred, 1.0 - strength, 0)
        return sharpened

    @staticmethod
    def denoise_preserve_edges(image: np.ndarray) -> np.ndarray:
        """Bilateral filter for noise reduction while preserving text boundaries."""
        return cv2.bilateralFilter(image, d=5, sigmaColor=50, sigmaSpace=50)

    @classmethod
    def preprocess_for_ocr(cls, image: np.ndarray) -> dict:
        """
        Full preprocessing pipeline: boundary de-skewing, CLAHE, sharpening, denoising, and binarization.
        """
        # 1. Perspective Transform De-skewing
        deskewed = cls.detect_and_deskew_boundary(image)

        # 2. CLAHE Contrast enhancement
        enhanced = cls.enhance_contrast_clahe(deskewed)
        
        # 3. Unsharp Masking
        sharpened = cls.sharpen(enhanced, strength=1.5)
        
        # 4. Edge-preserving Denoising
        denoised = cls.denoise_preserve_edges(sharpened)

        # 5. Grayscale & Thresholding
        gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY) if len(denoised.shape) == 3 else denoised.copy()
        _, binarized = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return {
            "deskewed": deskewed,
            "color_enhanced": denoised,
            "gray": gray,
            "binarized": binarized
        }
