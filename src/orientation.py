import cv2
import numpy as np
import pytesseract

class OrientationCorrector:
    """
    Detects and corrects document skew angle and 90/180/270 degree rotation
    using OpenCV Hough Transform & Tesseract OSD (Orientation and Script Detection).
    """

    @classmethod
    def correct_orientation(cls, image: np.ndarray) -> tuple[np.ndarray, bool, float]:
        """
        Auto-detects rotation/skew and returns (corrected_image, was_corrected, total_angle).
        """
        # Step 1: Detect 90, 180, 270 degree coarse orientation via Tesseract OSD if available
        osd_angle = cls.detect_osd_rotation(image)

        # Apply coarse 90-degree rotations first
        rotated_img = image
        if osd_angle in (90, 180, 270):
            rotated_img = cls.rotate_by_cardinal_angle(image, osd_angle)

        # Step 2: Detect fine skew angle (-45 to +45 degrees) via Hough transform / minAreaRect
        skew_angle = cls.detect_skew_angle(rotated_img)

        final_angle = osd_angle + skew_angle
        was_corrected = abs(final_angle) > 0.5

        if abs(skew_angle) > 0.5:
            final_img = cls.rotate_arbitrary_angle(rotated_img, skew_angle)
        else:
            final_img = rotated_img

        return final_img, was_corrected, round(final_angle, 2)

    @staticmethod
    def detect_osd_rotation(image: np.ndarray) -> int:
        """Uses Tesseract OSD to detect coarse 0/90/180/270 rotation angle."""
        try:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            osd_data = pytesseract.image_to_osd(rgb, output_type=pytesseract.Output.DICT)
            rotate = osd_data.get('rotate', 0)
            return rotate
        except Exception:
            # If Tesseract OSD fails or missing binary, fallback to 0 degrees coarse angle
            return 0

    @staticmethod
    def detect_skew_angle(image: np.ndarray) -> float:
        """Detect fine skew angle using OpenCV Hough Lines transform."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)

        if lines is None:
            return 0.0

        angles = []
        for line in lines:
            line_arr = line.ravel()
            if len(line_arr) >= 4:
                x1, y1, x2, y2 = line_arr[:4]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # Keep only near-horizontal lines for skew check
                if -45 < angle < 45:
                    angles.append(angle)

        if not angles:
            return 0.0

        median_angle = float(np.median(angles))
        return median_angle

    @staticmethod
    def rotate_by_cardinal_angle(image: np.ndarray, angle: int) -> np.ndarray:
        """Rotates image by exact 90, 180, or 270 degrees."""
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    @staticmethod
    def rotate_arbitrary_angle(image: np.ndarray, angle: float) -> np.ndarray:
        """Rotates image by arbitrary float angle with canvas padding."""
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        nw = int((h * sin) + (w * cos))
        nh = int((h * cos) + (w * sin))

        M[0, 2] += (nw / 2) - center[0]
        M[1, 2] += (nh / 2) - center[1]

        rotated = cv2.warpAffine(image, M, (nw, nh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
