import cv2
import numpy as np
import logging
from PIL import Image, ImageEnhance
import scipy.ndimage


logger = logging.getLogger(__name__)


def auto_deskew(image, max_angle=15):
    """
    Automatically detects and corrects skew angle of a document.
    Uses multiple detection strategies for robust results:
    1. Text line detection via Hough Transform
    2. Projection profile analysis
    3. Minimum area rectangle fallback
    
    Args:
        image: Input image (BGR format)
        max_angle: Maximum angle to correct (ignores larger angles as likely detection errors)
    
    Returns:
        Deskewed image with text lines horizontal
    """
    if image is None or image.size == 0:
        return image
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # Strategy 1: Enhanced Hough Line detection for text lines
        angle1 = _detect_skew_hough_lines(gray, max_angle)
        
        # Strategy 2: Projection profile analysis (more reliable for text)
        angle2 = _detect_skew_projection_profile(gray, max_angle)
        
        # Strategy 3: Minimum area rectangle of text content
        angle3 = _detect_skew_minarea_rect(gray, max_angle)
        
        # Combine results - use majority voting or weighted average
        angles = [a for a in [angle1, angle2, angle3] if a is not None]
        
        if not angles:
            return image
        
        # If results are consistent, use median
        if len(angles) >= 2:
            # Check consistency - if angles are within 2 degrees of each other
            angle_std = np.std(angles)
            if angle_std < 3.0:
                final_angle = np.median(angles)
            else:
                # Use the one with smallest absolute value (most conservative)
                final_angle = min(angles, key=abs)
        else:
            final_angle = angles[0]
        
        # Lower threshold for correction - 0.2 degrees is perceptible
        if abs(final_angle) < 0.2:
            return image
        
        # Rotate to correct the skew
        rotated = _rotate_image(image, final_angle)
        
        # Trim any white borders created by rotation
        rotated = _crop_rotation_borders(rotated)
        
        return rotated
    
    except Exception:
        logger.exception("auto_deskew failed")
        return image


def _detect_skew_hough_lines(gray, max_angle):
    """
    Detect skew using Hough Line Transform on text edges.
    """
    try:
        h, w = gray.shape
        
        # Multi-scale text detection - better for various document types
        all_angles = []
        
        for blur_size in [(3, 3), (5, 5)]:
            blurred = cv2.GaussianBlur(gray, blur_size, 0)
            
            # Edge detection with lower thresholds for text
            edges = cv2.Canny(blurred, 30, 100, apertureSize=3)
            
            # Connect text into horizontal lines with horizontal kernel
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (min(w // 10, 50), 1))
            dilated = cv2.dilate(edges, kernel_h, iterations=2)
            
            # Hough Line detection with lower thresholds for better detection
            min_line_length = max(w // 8, 50)
            lines = cv2.HoughLinesP(dilated, 1, np.pi / 720,  # Higher angular resolution
                                    threshold=50,
                                    minLineLength=min_line_length, 
                                    maxLineGap=min(w // 20, 30))
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    dx = x2 - x1
                    dy = y2 - y1
                    
                    # Only consider sufficiently long lines
                    length = np.sqrt(dx**2 + dy**2)
                    if length < min_line_length * 0.5:
                        continue
                    
                    if dx == 0:
                        continue
                    
                    angle = np.degrees(np.arctan2(dy, dx))
                    
                    # Only consider near-horizontal lines (text lines)
                    if abs(angle) <= max_angle:
                        # Weight by line length
                        all_angles.extend([angle] * int(length / 20))
        
        if not all_angles:
            return None
        
        # Use median for robustness against outliers
        return np.median(all_angles)
    
    except Exception:
        return None


def _detect_skew_projection_profile(gray, max_angle, angle_range=None):
    """
    Detect skew using projection profile analysis.
    This is highly effective for text documents as text lines create
    distinct horizontal patterns when properly aligned.
    """
    try:
        h, w = gray.shape
        
        # Binarize the image for projection
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Test range of angles
        if angle_range is None:
            angle_range = np.arange(-max_angle, max_angle + 0.1, 0.25)
        
        best_angle = 0
        best_variance = 0
        
        for angle in angle_range:
            # Rotate binary image
            if angle != 0:
                rotated = scipy.ndimage.rotate(binary, angle, reshape=False, mode='constant', cval=0)
            else:
                rotated = binary
            
            # Calculate horizontal projection (sum of each row)
            projection = np.sum(rotated, axis=1)
            
            # Non-zero projection values only
            projection = projection[projection > 0]
            
            if len(projection) < 10:
                continue
            
            # Higher variance means text lines are more aligned horizontally
            variance = np.var(projection)
            
            if variance > best_variance:
                best_variance = variance
                best_angle = angle
        
        # Refine the angle with smaller steps
        if abs(best_angle) > 0:
            fine_range = np.arange(best_angle - 0.5, best_angle + 0.5, 0.05)
            for angle in fine_range:
                if angle != 0:
                    rotated = scipy.ndimage.rotate(binary, angle, reshape=False, mode='constant', cval=0)
                else:
                    rotated = binary
                
                projection = np.sum(rotated, axis=1)
                projection = projection[projection > 0]
                
                if len(projection) < 10:
                    continue
                
                variance = np.var(projection)
                
                if variance > best_variance:
                    best_variance = variance
                    best_angle = angle
        
        return best_angle if abs(best_angle) <= max_angle else None
    
    except Exception:
        return None


def _detect_skew_minarea_rect(gray, max_angle):
    """
    Fallback deskew method using minimum area rectangle of text content.
    """
    try:
        # Threshold to find content
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Clean up with morphology
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Find all text coordinates
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return None
        
        # Get minimum area rectangle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        
        # Normalize angle (minAreaRect returns angles in -90 to 0 range)
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
        
        # Validate angle is within bounds
        if abs(angle) > max_angle:
            return None
        
        return angle
    
    except Exception:
        return None


def _crop_rotation_borders(image):
    """
    Crop white borders created by rotation.
    """
    if image is None or image.size == 0:
        return image
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Find non-white pixels
        _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        
        coords = cv2.findNonZero(thresh)
        if coords is None:
            return image
        
        x, y, cw, ch = cv2.boundingRect(coords)
        
        # Add small padding
        pad = 3
        x = max(0, x - pad)
        y = max(0, y - pad)
        cw = min(image.shape[1] - x, cw + 2 * pad)
        ch = min(image.shape[0] - y, ch + 2 * pad)
        
        if cw < 50 or ch < 50:
            return image
        
        return image[y:y+ch, x:x+cw]
    
    except Exception:
        return image


def _rotate_image(image, angle):
    """
    Rotates image by the given angle while preserving content.
    """
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    
    # Get rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new image size to fit rotated content
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix for new size
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    
    # Perform rotation with white background
    rotated = cv2.warpAffine(image, M, (new_w, new_h),
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(255, 255, 255))
    
    return rotated


def order_points(pts):
    """
    Ensures points are in a specific order: 
    [top-left, top-right, bottom-right, bottom-left]
    """
    rect = np.zeros((4, 2), dtype="float32")

    # The top-left point will have the smallest sum, whereas
    # the bottom-right point will have the largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Compute the difference between the points:
    # top-right will have the smallest difference,
    # bottom-left will have the largest difference
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    """
    Performs the perspective warp to 'flatten' the document.
    Returns None if inputs are invalid to avoid cv2 assertions.
    """
    # Enhanced validation
    if image is None:
        return None
    
    # Check image dimensions and size
    if not hasattr(image, 'shape') or len(image.shape) < 2:
        return None
    
    if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
        return None

    if pts is None or len(pts) != 4:
        return None

    rect = order_points(pts.astype("float32"))
    (tl, tr, br, bl) = rect

    # Compute the width of the new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # Compute the height of the new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    # Avoid warp on degenerate inputs
    if maxWidth <= 0 or maxHeight <= 0 or maxWidth > 10000 or maxHeight > 10000:
        return None

    try:
        # Set up destination points for a "bird's eye view"
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        # Calculate the transformation matrix and apply it
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        
        # Validate output
        if warped is None or warped.size == 0:
            return None
            
        return warped
    except Exception:
        logger.exception("four_point_transform failed")
        return None


def detect_and_warp(img):
    """
    Automated version of the scan pipeline: detects document 
    edges and applies perspective correction.
    Uses detect_document_corners for robust detection.
    """
    # Enhanced validation
    if img is None:
        return None
    
    if not hasattr(img, 'shape') or len(img.shape) < 2:
        return None
        
    if img.size == 0 or img.shape[0] == 0 or img.shape[1] == 0:
        return None

    orig = img.copy()
    
    try:
        # Use the unified corner detection function
        corners, confidence = detect_document_corners(img)
        
        if corners is not None and confidence > 0.1:
            warped = four_point_transform(orig, corners)
            if warped is not None:
                # Auto-deskew to straighten text lines
                warped = auto_deskew(warped)
                warped = auto_trim_white_borders(warped)
                return warped
        
        # If no document found, return original image (prevents crashing)
        return orig
    except Exception:
        logger.exception("detect_and_warp failed")
        return orig


def apply_master_readable_pro(warped_image):
    """
    Professional Document Scanner - Clear Text with White Background
    Optimized for readable text without blur
    """
    
    # === STAGE 1: NO BLURRING - Preserve original text sharpness ===
    # Skip bilateral filter - it was causing text blur
    
    # === STAGE 2: SHADOW REMOVAL IN LAB SPACE ===
    lab = cv2.cvtColor(warped_image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Background estimation with large kernel
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45))
    bg_l = cv2.morphologyEx(l_channel, cv2.MORPH_CLOSE, kernel)
    bg_l = cv2.GaussianBlur(bg_l, (0, 0), sigmaX=50, sigmaY=50)
    
    # Division normalization
    l_corrected = cv2.divide(l_channel.astype(float), bg_l.astype(float) + 1e-6, scale=245)
    l_corrected = np.clip(l_corrected, 0, 255).astype(np.uint8)
    
    # === STAGE 3: GENTLE WHITENING (preserve text) ===
    lut_white = np.zeros(256, dtype=np.uint8)
    for i in range(256):
        if i >= 240:  # Only very light becomes white
            lut_white[i] = 255
        elif i >= 210:  # Gentle transition
            lut_white[i] = int(210 + (i - 210) * (255 - 210) / (240 - 210))
        else:  # Preserve everything else including text
            lut_white[i] = i
    
    l_whitened = cv2.LUT(l_corrected, lut_white)
    
    # Light CLAHE for local contrast
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_whitened)
    
    # Merge back
    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    result = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    
    # === STAGE 4: COLOR CHANNEL WHITENING ===
    b, g, r = cv2.split(result)
    b = cv2.LUT(b, lut_white)
    g = cv2.LUT(g, lut_white)
    r = cv2.LUT(r, lut_white)
    result = cv2.merge([b, g, r])
    
    # === STAGE 5: ENHANCE TEXT WITH OPENCV SHARPENING ===
    # Use kernel-based sharpening - more effective for text than UnsharpMask
    sharpen_kernel = np.array([
        [0, -0.5, 0],
        [-0.5, 3, -0.5],
        [0, -0.5, 0]
    ], dtype=np.float32)
    result = cv2.filter2D(result, -1, sharpen_kernel)
    
    # === STAGE 6: FINAL COLOR GRADING ===
    pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    
    # Moderate contrast for clear text
    pil_img = ImageEnhance.Contrast(pil_img).enhance(1.2)
    
    # Slight brightness
    pil_img = ImageEnhance.Brightness(pil_img).enhance(1.03)
    
    # Natural color
    pil_img = ImageEnhance.Color(pil_img).enhance(1.05)
    
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def apply_ultra_sharp_text(warped_image):
    """
    Ultra-Sharp Text Mode - Optimized for Pure Text Documents
    Crisp black text on pure white background
    """
    # === STAGE 1: MINIMAL DENOISING ===
    denoised = cv2.bilateralFilter(warped_image, 3, 25, 25)
    
    # Convert to grayscale
    gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
    
    # === STAGE 2: AGGRESSIVE SHADOW REMOVAL ===
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (50, 50))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel_large)
    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=60, sigmaY=60)
    
    # Division normalization with boost for whiter background
    normalized = cv2.divide(gray.astype(float), bg.astype(float) + 1e-6, scale=265)
    normalized = np.clip(normalized, 0, 255).astype(np.uint8)
    
    # === STAGE 3: LEVELS FOR PURE WHITE BACKGROUND ===
    # Push light grays to pure white
    lut_white = np.zeros(256, dtype=np.uint8)
    for i in range(256):
        if i >= 200:
            lut_white[i] = 255
        elif i >= 160:
            lut_white[i] = int(160 + (i - 160) * (255 - 160) / (200 - 160))
        elif i <= 80:  # Darken text
            lut_white[i] = int(i * 0.8)
        else:
            lut_white[i] = i
    
    whitened = cv2.LUT(normalized, lut_white)
    
    # === STAGE 4: ENHANCED CONTRAST ===
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(whitened)
    
    # === STAGE 5: CLEAN BINARIZATION (Optional - for pure B&W) ===
    # Use Otsu's method for optimal threshold
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Slight morphological cleanup
    kernel_small = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_small)
    
    # Convert back to BGR
    return cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)


def apply_premium_color_scan(warped_image):
    """
    Premium Color Scanner - Vivid Colors with Clear Text on White Background
    """
    # === STAGE 1: NO BLURRING - preserve text ===
    
    # === STAGE 2: SHADOW REMOVAL IN LAB SPACE ===
    lab = cv2.cvtColor(warped_image, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    
    # Large kernel for smooth background
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45))
    bg_l = cv2.morphologyEx(l_channel, cv2.MORPH_CLOSE, kernel)
    bg_l = cv2.GaussianBlur(bg_l, (0, 0), sigmaX=50, sigmaY=50)
    
    # Division normalization
    l_corrected = cv2.divide(l_channel.astype(float), bg_l.astype(float) + 1e-6, scale=245)
    l_corrected = np.clip(l_corrected, 0, 255).astype(np.uint8)
    
    # === STAGE 3: GENTLE WHITENING ===
    lut_white = np.zeros(256, dtype=np.uint8)
    for i in range(256):
        if i >= 240:
            lut_white[i] = 255
        elif i >= 210:
            lut_white[i] = int(210 + (i - 210) * (255 - 210) / (240 - 210))
        else:
            lut_white[i] = i
    
    l_whitened = cv2.LUT(l_corrected, lut_white)
    
    # Light CLAHE
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_whitened)
    
    # Merge back
    lab_final = cv2.merge([l_enhanced, a, b])
    bgr_result = cv2.cvtColor(lab_final, cv2.COLOR_LAB2BGR)
    
    # === STAGE 4: COLOR CHANNEL WHITENING ===
    b_ch, g_ch, r_ch = cv2.split(bgr_result)
    b_ch = cv2.LUT(b_ch, lut_white)
    g_ch = cv2.LUT(g_ch, lut_white)
    r_ch = cv2.LUT(r_ch, lut_white)
    bgr_result = cv2.merge([b_ch, g_ch, r_ch])
    
    # === STAGE 5: OPENCV SHARPENING ===
    sharpen_kernel = np.array([
        [0, -0.5, 0],
        [-0.5, 3, -0.5],
        [0, -0.5, 0]
    ], dtype=np.float32)
    bgr_result = cv2.filter2D(bgr_result, -1, sharpen_kernel)
    
    # === STAGE 6: COLOR GRADING ===
    pil_img = Image.fromarray(cv2.cvtColor(bgr_result, cv2.COLOR_BGR2RGB))
    
    # Moderate contrast
    pil_img = ImageEnhance.Contrast(pil_img).enhance(1.2)
    
    # Vibrant colors
    pil_img = ImageEnhance.Color(pil_img).enhance(1.25)
    
    # Slight brightness
    pil_img = ImageEnhance.Brightness(pil_img).enhance(1.03)
    
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def _safe_contour_area(contour):
    """Safely compute contour area, returning 0 on error."""
    if contour is None:
        return 0
    try:
        c = np.asarray(contour, dtype=np.float32)
        if c.size < 6:  # Need at least 3 points (6 values)
            return 0
        return cv2.contourArea(c)
    except Exception:
        return 0


def _safe_sort_contours(cnts, max_count=3):
    """Safely sort contours by area, filtering out invalid ones."""
    valid = []
    for c in cnts:
        area = _safe_contour_area(c)
        if area > 0:
            valid.append((c, area))
    valid.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in valid[:max_count]]


def _find_best_quad(cnts, image_area, min_area_ratio=0.05):
    """
    Find the best quadrilateral contour from a list of contours.
    Tries multiple epsilon values for polygon approximation.
    Returns (best_contour, best_area) or (None, 0).
    """
    best_contour = None
    best_area = 0
    
    for c in cnts:
        if c is None or len(c) < 4:
            continue
        
        try:
            area = _safe_contour_area(c)
        except Exception:
            continue
            
        if area < image_area * min_area_ratio:
            continue
        
        peri = cv2.arcLength(c, True)
        if peri <= 0:
            continue
        
        # Try various epsilon values from tight to loose
        for eps in [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1]:
            approx = cv2.approxPolyDP(c, eps * peri, True)
            if len(approx) == 4:
                if cv2.isContourConvex(approx) and area > best_area:
                    rect = cv2.minAreaRect(approx)
                    w_rect, h_rect = rect[1]
                    if w_rect > 0 and h_rect > 0:
                        aspect = max(w_rect, h_rect) / min(w_rect, h_rect)
                        if aspect < 4:
                            best_area = area
                            best_contour = approx
                break
    
    return best_contour, best_area


def _find_quad_from_hull(cnts, image_area, min_area_ratio=0.08):
    """
    For contours that don't directly approximate to 4 points,
    use convex hull and find the 4 extreme corners that best 
    represent the actual page shape (preserving tilt).
    """
    best_contour = None
    best_area = 0
    
    for c in cnts:
        if c is None or len(c) < 4:
            continue
        
        try:
            area = _safe_contour_area(c)
        except Exception:
            continue
            
        if area < image_area * min_area_ratio:
            continue
        
        hull = cv2.convexHull(c)
        if hull is None or len(hull) < 4:
            continue
            
        try:
            hull_area = _safe_contour_area(hull)
        except Exception:
            continue
        
        if hull_area < image_area * min_area_ratio:
            continue
        
        # Try to approximate hull to 4 points with various epsilon values
        peri = cv2.arcLength(hull, True)
        quad = None
        
        for eps in [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.12]:
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) == 4:
                quad = approx
                break
            elif len(approx) < 4:
                # If we reduced too much, use last approximation with more points
                break
        
        # If approximation didn't work, find the 4 extreme corners of hull
        if quad is None and len(hull) >= 4:
            quad = _find_extreme_corners(hull)
        
        if quad is not None and len(quad) == 4:
            try:
                quad_area = _safe_contour_area(quad)
                if quad_area > best_area:
                    best_area = quad_area
                    best_contour = quad.reshape(4, 1, 2)
            except Exception:
                pass
    
    return best_contour, best_area


def _find_extreme_corners(hull):
    """
    Find the 4 extreme corner points from a convex hull.
    Uses a combination of:
    1. Furthest points from centroid
    2. Points with maximum distance sum to other corners
    This preserves the actual page tilt instead of fitting a rectangle.
    """
    if hull is None or len(hull) < 4:
        return None
    
    # Flatten hull points
    pts = hull.reshape(-1, 2).astype(np.float32)
    
    # Method 1: Find the 4 points that form the largest quadrilateral
    # Start with points at extreme positions (top-left, top-right, bottom-right, bottom-left)
    
    # Calculate centroid
    cx, cy = np.mean(pts[:, 0]), np.mean(pts[:, 1])
    
    # For each point, calculate its angle from centroid
    angles = np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx)
    
    # Divide into 4 quadrants and find the furthest point in each
    # Quadrants: top-right (0 to -pi/2), top-left (-pi/2 to -pi), 
    #            bottom-left (pi/2 to pi), bottom-right (0 to pi/2)
    
    quadrants = [
        (-np.pi, -np.pi/2),      # top-left
        (-np.pi/2, 0),           # top-right
        (0, np.pi/2),            # bottom-right
        (np.pi/2, np.pi)         # bottom-left
    ]
    
    corners = []
    for q_start, q_end in quadrants:
        # Find points in this quadrant
        mask = (angles >= q_start) & (angles < q_end)
        if not np.any(mask):
            # Extend search range slightly
            mask = (angles >= q_start - 0.2) & (angles < q_end + 0.2)
        
        if np.any(mask):
            quad_pts = pts[mask]
            # Find the furthest point from centroid in this quadrant
            dists = np.sqrt((quad_pts[:, 0] - cx)**2 + (quad_pts[:, 1] - cy)**2)
            furthest_idx = np.argmax(dists)
            corners.append(quad_pts[furthest_idx])
    
    if len(corners) != 4:
        # Fallback: Find 4 points that maximize the quadrilateral area
        return _find_max_area_quad(pts)
    
    return np.array(corners, dtype=np.float32).reshape(4, 1, 2)


def _find_max_area_quad(pts):
    """
    Find 4 points from a set that form the maximum area quadrilateral.
    Uses a simplified approach: find extreme points in 4 directions.
    """
    if len(pts) < 4:
        return None
    
    # Find extreme points
    top_left_score = pts[:, 0] + pts[:, 1]  # minimize x + y
    top_right_score = -pts[:, 0] + pts[:, 1]  # minimize -x + y (maximize x, minimize y)
    bottom_right_score = -pts[:, 0] - pts[:, 1]  # minimize -x - y
    bottom_left_score = pts[:, 0] - pts[:, 1]  # minimize x - y
    
    tl = pts[np.argmin(top_left_score)]
    tr = pts[np.argmin(top_right_score)]
    br = pts[np.argmin(bottom_right_score)]
    bl = pts[np.argmin(bottom_left_score)]
    
    # Check for duplicate points
    corners = [tl, tr, br, bl]
    unique_corners = []
    for c in corners:
        is_dup = False
        for uc in unique_corners:
            if np.linalg.norm(c - uc) < 10:
                is_dup = True
                break
        if not is_dup:
            unique_corners.append(c)
    
    if len(unique_corners) < 4:
        return None
    
    return np.array(unique_corners[:4], dtype=np.float32).reshape(4, 1, 2)


def _line_intersection(line1, line2):
    """Find intersection point of two lines given in (rho, theta) format."""
    rho1, theta1 = line1
    rho2, theta2 = line2
    
    cos1, sin1 = np.cos(theta1), np.sin(theta1)
    cos2, sin2 = np.cos(theta2), np.sin(theta2)
    
    denom = cos1 * sin2 - cos2 * sin1
    if abs(denom) < 1e-10:
        return None
    
    x = (sin2 * rho1 - sin1 * rho2) / denom
    y = (cos1 * rho2 - cos2 * rho1) / denom
    
    return (x, y)


def _detect_page_with_hough_lines(gray, image_area):
    """
    Use Hough Line Transform to detect page edges and find corners
    as line intersections. Works well for rectangular documents.
    """
    h, w = gray.shape[:2]
    best_contour = None
    best_area = 0
    
    # Heavy blur to remove text
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    
    for canny_low, canny_high in [(20, 50), (30, 70), (15, 40)]:
        edges = cv2.Canny(blurred, canny_low, canny_high)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        
        # Detect lines using Hough Transform
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=80)
        
        if lines is None or len(lines) < 4:
            continue
        
        # Separate lines into horizontal and vertical groups
        horizontal = []
        vertical = []
        
        for line in lines:
            rho, theta = line[0]
            # Horizontal: theta near 0 or pi
            if theta < np.pi/6 or theta > 5*np.pi/6:
                vertical.append((rho, theta))
            # Vertical: theta near pi/2
            elif np.pi/3 < theta < 2*np.pi/3:
                horizontal.append((rho, theta))
        
        if len(horizontal) < 2 or len(vertical) < 2:
            continue
        
        # Sort to get top/bottom horizontal and left/right vertical
        horizontal.sort(key=lambda x: x[0])
        vertical.sort(key=lambda x: x[0])
        
        # Get extreme lines (first and last in each group)
        top_line = horizontal[0]
        bottom_line = horizontal[-1]
        left_line = vertical[0]
        right_line = vertical[-1]
        
        # Find corner intersections
        tl = _line_intersection(top_line, left_line)
        tr = _line_intersection(top_line, right_line)
        bl = _line_intersection(bottom_line, left_line)
        br = _line_intersection(bottom_line, right_line)
        
        if all(c is not None for c in [tl, tr, bl, br]):
            # Validate corners are within image bounds (with some margin)
            margin = 50
            valid = True
            for cx, cy in [tl, tr, bl, br]:
                if cx < -margin or cx > w + margin or cy < -margin or cy > h + margin:
                    valid = False
                    break
            
            if valid:
                pts = np.array([tl, tr, br, bl], dtype=np.float32)
                pts = np.clip(pts, 0, [[w-1, h-1]])
                area = _safe_contour_area(pts)
                
                if area > image_area * 0.15 and area > best_area:
                    best_area = area
                    best_contour = pts.reshape(4, 1, 2).astype(np.float32)
    
    return best_contour, best_area


def _detect_page_with_grabcut(image, initial_rect=None):
    """
    Use GrabCut algorithm for foreground/background segmentation.
    Works well when page clearly contrasts with background.
    """
    h, w = image.shape[:2]
    
    # If no initial rect, use center region
    if initial_rect is None:
        margin_x, margin_y = w // 8, h // 8
        initial_rect = (margin_x, margin_y, w - 2*margin_x, h - 2*margin_y)
    
    mask = np.zeros((h, w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    
    try:
        cv2.grabCut(image, mask, initial_rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
        
        # Create binary mask from GrabCut result
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # Clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        mask2 = cv2.morphologyEx(mask2 * 255, cv2.MORPH_CLOSE, kernel)
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel)
        
        return mask2
    except Exception:
        return None


def _refine_corners_with_harris(gray, corners, search_radius=30):
    """
    Refine corner positions using Harris corner detection.
    Searches for strongest corner near each initial corner.
    """
    h, w = gray.shape[:2]
    refined = []
    
    # Detect Harris corners
    harris = cv2.cornerHarris(gray, blockSize=2, ksize=3, k=0.04)
    harris = cv2.dilate(harris, None)
    
    for corner in corners:
        cx, cy = int(corner[0]), int(corner[1])
        
        # Define search region
        x1 = max(0, cx - search_radius)
        y1 = max(0, cy - search_radius)
        x2 = min(w, cx + search_radius)
        y2 = min(h, cy + search_radius)
        
        # Find strongest corner in region
        region = harris[y1:y2, x1:x2]
        if region.size > 0:
            local_max = np.unravel_index(np.argmax(region), region.shape)
            new_y, new_x = y1 + local_max[0], x1 + local_max[1]
            refined.append([new_x, new_y])
        else:
            refined.append([cx, cy])
    
    return np.array(refined, dtype=np.float32)


def _verify_and_adjust_corners(gray, corners, search_radius=25):
    """
    Verify each corner is at an actual edge (bright-to-dark transition).
    Adjusts corners inward if they're in dark regions (background).
    """
    h, w = gray.shape[:2]
    adjusted = []
    
    # Get ordered corners: TL, TR, BR, BL
    ordered = order_points(corners)
    
    # For each corner, check if it's on the page (bright) or background (dark)
    # and adjust toward the page if needed
    for i, corner in enumerate(ordered):
        cx, cy = int(corner[0]), int(corner[1])
        cx = np.clip(cx, 0, w-1)
        cy = np.clip(cy, 0, h-1)
        
        # Get local intensity at corner
        local_intensity = gray[cy, cx]
        
        # Determine search direction based on corner position
        # TL(0): search right and down, TR(1): search left and down
        # BR(2): search left and up, BL(3): search right and up
        if i == 0:  # TL
            dx, dy = 1, 1
        elif i == 1:  # TR
            dx, dy = -1, 1
        elif i == 2:  # BR
            dx, dy = -1, -1
        else:  # BL
            dx, dy = 1, -1
        
        # If corner is in dark region, move toward bright (page)
        if local_intensity < 120:
            # Search along diagonal toward page center
            best_x, best_y = cx, cy
            
            for step in range(1, search_radius):
                nx = cx + dx * step
                ny = cy + dy * step
                
                if 0 <= nx < w and 0 <= ny < h:
                    intensity = gray[ny, nx]
                    # Look for transition to bright area
                    if intensity > 140:
                        # Found page edge, use this point
                        best_x, best_y = nx, ny
                        break
            
            adjusted.append([best_x, best_y])
        else:
            # Corner is already on bright area, find the edge
            # by moving outward until we hit dark region
            edge_x, edge_y = cx, cy
            
            for step in range(1, search_radius):
                nx = cx - dx * step  # Move opposite direction (outward)
                ny = cy - dy * step
                
                if 0 <= nx < w and 0 <= ny < h:
                    intensity = gray[ny, nx]
                    if intensity < 100:  # Found dark background
                        # Step back one to stay on page edge
                        edge_x = cx - dx * (step - 1)
                        edge_y = cy - dy * (step - 1)
                        break
                else:
                    # Hit image boundary
                    edge_x, edge_y = cx, cy
                    break
            
            adjusted.append([edge_x, edge_y])
    
    return np.array(adjusted, dtype=np.float32)


def _shrink_to_page_edges(gray, corners):
    """
    Given initial corners, shrink each corner inward to find actual page edges.
    Uses intensity profiles to detect bright-to-dark transitions.
    """
    h, w = gray.shape[:2]
    ordered = order_points(corners)
    tl, tr, br, bl = ordered
    
    # Calculate center of detected region
    center_x = (tl[0] + tr[0] + br[0] + bl[0]) / 4
    center_y = (tl[1] + tr[1] + br[1] + bl[1]) / 4
    
    adjusted = []
    for corner in ordered:
        cx, cy = corner
        
        # Direction from corner toward center
        dx = 1 if center_x > cx else -1
        dy = 1 if center_y > cy else -1
        
        # Check if current position is dark (background)
        cx_int, cy_int = int(np.clip(cx, 0, w-1)), int(np.clip(cy, 0, h-1))
        
        if gray[cy_int, cx_int] < 130:
            # Corner is in dark area, move toward center until bright
            for step in range(1, 50):
                nx = int(cx + dx * step)
                ny = int(cy + dy * step)
                if 0 <= nx < w and 0 <= ny < h:
                    if gray[ny, nx] > 150:
                        adjusted.append([nx, ny])
                        break
            else:
                adjusted.append([cx, cy])
        else:
            adjusted.append([cx, cy])
    
    return np.array(adjusted, dtype=np.float32)


def _tighten_contour_with_edges(gray, corners, image_area):
    """Snap detected quad to strong outer edges to avoid wide margins."""
    try:
        base = order_points(corners.reshape(4, 2).astype(np.float32))
        base_area = _safe_contour_area(base)
        if base_area <= 0:
            return base

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 120)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)

        cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = _safe_sort_contours(cnts, 5)

        for c in cnts:
            area = _safe_contour_area(c)
            if area < image_area * 0.15:
                continue

            rect = cv2.minAreaRect(c)
            box = cv2.boxPoints(rect)
            box = order_points(box.astype(np.float32))
            box_area = _safe_contour_area(box)

            if box_area <= 0:
                continue

            # Prefer boxes that are meaningfully tighter but not aggressively small
            if box_area < base_area * 0.95 and box_area > base_area * 0.35:
                return box

        return base
    except Exception:
        return corners.reshape(4, 2).astype(np.float32)
    # New function to score quadrilaterals
def _score_quad(gray, quad):
    """Score a quadrilateral by how well it isolates bright paper from background."""
    try:
        h, w = gray.shape[:2]
        quad = quad.reshape(4, 2).astype(np.float32)
        area = _safe_contour_area(quad)
        if area <= 0:
            return -1e9

        # Reject unrealistically small/large
        ratio = area / float(h * w)
        if ratio < 0.05 or ratio > 0.9:
            return -1e9

        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [quad.astype(np.int32)], 255)

        inside_vals = gray[mask == 255]
        if inside_vals.size == 0:
            return -1e9
        inside_mean = float(inside_vals.mean())

        dilated = cv2.dilate(mask, np.ones((15, 15), np.uint8), iterations=1)
        border = cv2.bitwise_and(dilated, cv2.bitwise_not(mask))
        border_vals = gray[border == 255]
        if border_vals.size == 0:
            border_mean = inside_mean
        else:
            border_mean = float(border_vals.mean())

        contrast = inside_mean - border_mean
        score = contrast * ratio * 100.0
        return score
    except Exception:
        return -1e9

def _select_best_quad(gray, candidates, image_area):
    best = None
    best_score = -1e9
    for quad in candidates:
        if quad is None:
            continue
        try:
            if quad.shape != (4, 2):
                quad = quad.reshape(4, 2)
        except Exception:
            continue
        score = _score_quad(gray, quad)
        if score > best_score:
            best_score = score
            best = quad.reshape(4, 2).astype(np.float32)
    return best


def _snap_edges_to_bright_region(gray, corners, max_shift=20, intensity_threshold=170):
    """Shift each page edge inward until it sits on a bright region (paper)."""
    try:
        tl, tr, br, bl = order_points(corners.reshape(4, 2).astype(np.float32))
        h, w = gray.shape[:2]

        def sample_line(p1, p2, samples=50):
            xs = np.linspace(p1[0], p2[0], samples)
            ys = np.linspace(p1[1], p2[1], samples)
            xs = np.clip(xs, 0, w - 1).astype(np.int32)
            ys = np.clip(ys, 0, h - 1).astype(np.int32)
            return gray[ys, xs].mean()

        # Top edge: move down until bright
        for s in range(1, max_shift + 1):
            mean_intensity = sample_line((tl[0], tl[1] + s), (tr[0], tr[1] + s))
            if mean_intensity > intensity_threshold:
                tl[1] += s
                tr[1] += s
                break

        # Bottom edge: move up until bright
        for s in range(1, max_shift + 1):
            mean_intensity = sample_line((bl[0], bl[1] - s), (br[0], br[1] - s))
            if mean_intensity > intensity_threshold:
                bl[1] -= s
                br[1] -= s
                break

        # Left edge: move right until bright
        for s in range(1, max_shift + 1):
            mean_intensity = sample_line((tl[0] + s, tl[1]), (bl[0] + s, bl[1]))
            if mean_intensity > intensity_threshold:
                tl[0] += s
                bl[0] += s
                break

        # Right edge: move left until bright
        for s in range(1, max_shift + 1):
            mean_intensity = sample_line((tr[0] - s, tr[1]), (br[0] - s, br[1]))
            if mean_intensity > intensity_threshold:
                tr[0] -= s
                br[0] -= s
                break

        snapped = np.array([tl, tr, br, bl], dtype=np.float32)
        snapped[:, 0] = np.clip(snapped[:, 0], 0, w - 1)
        snapped[:, 1] = np.clip(snapped[:, 1], 0, h - 1)
        return snapped
    except Exception:
        return corners.reshape(4, 2).astype(np.float32)


def _refine_edges_with_local_contrast(gray, corners, max_shift=25, samples=50):
    """Refine each edge by scanning perpendicular offsets and picking the brightest line."""
    try:
        h, w = gray.shape[:2]
        rect = order_points(corners.reshape(4, 2).astype(np.float32))
        tl, tr, br, bl = rect

        def line_mean(p1, p2):
            xs = np.linspace(p1[0], p2[0], samples)
            ys = np.linspace(p1[1], p2[1], samples)
            xs = np.clip(xs, 0, w - 1).astype(np.int32)
            ys = np.clip(ys, 0, h - 1).astype(np.int32)
            return gray[ys, xs].mean()

        def best_offset(p1, p2):
            v = p2 - p1
            norm = np.array([v[1], -v[0]], dtype=np.float32)
            nlen = np.linalg.norm(norm)
            if nlen < 1e-4:
                return 0.0, np.array([0.0, 0.0], dtype=np.float32)
            norm /= nlen
            best_o = 0.0
            best_mean = -1e9
            for o in range(-max_shift, max_shift + 1):
                shift = norm * o
                m = line_mean(p1 + shift, p2 + shift)
                if m > best_mean:
                    best_mean = m
                    best_o = o
            return best_o, norm

        offsets = {}
        # top, right, bottom, left edges
        offsets['top'] = best_offset(tl, tr)
        offsets['right'] = best_offset(tr, br)
        offsets['bottom'] = best_offset(br, bl)
        offsets['left'] = best_offset(bl, tl)

        # Apply offsets: each corner gets average of its two adjacent edge shifts
        tl_new = tl + (offsets['top'][0] * offsets['top'][1] + offsets['left'][0] * offsets['left'][1]) * 0.5
        tr_new = tr + (offsets['top'][0] * offsets['top'][1] + offsets['right'][0] * offsets['right'][1]) * 0.5
        br_new = br + (offsets['right'][0] * offsets['right'][1] + offsets['bottom'][0] * offsets['bottom'][1]) * 0.5
        bl_new = bl + (offsets['bottom'][0] * offsets['bottom'][1] + offsets['left'][0] * offsets['left'][1]) * 0.5

        refined = np.array([tl_new, tr_new, br_new, bl_new], dtype=np.float32)
        refined[:, 0] = np.clip(refined[:, 0], 0, w - 1)
        refined[:, 1] = np.clip(refined[:, 1], 0, h - 1)
        return refined
    except Exception:
        return corners.reshape(4, 2).astype(np.float32)


def _balance_side_gaps(gray, corners, max_diff_ratio=0.06, max_shift_px=18):
    """Reduce asymmetry when one side has a much larger gap to the image border.

    Keeps shifts conservative to avoid over-expanding the quad.
    """
    try:
        h, w = gray.shape[:2]
        rect = order_points(corners.reshape(4, 2).astype(np.float32))
        tl, tr, br, bl = rect

        left_gap = min(tl[0], bl[0])
        right_gap = (w - 1) - max(tr[0], br[0])
        top_gap = min(tl[1], tr[1])
        bottom_gap = (h - 1) - max(bl[1], br[1])

        thresh_x = max_diff_ratio * w
        thresh_y = max_diff_ratio * h

        # Horizontal balancing
        if left_gap - right_gap > thresh_x:
            shift = min(max_shift_px, (left_gap - right_gap - thresh_x) * 0.5)
            tl[0] -= shift
            bl[0] -= shift
        elif right_gap - left_gap > thresh_x:
            shift = min(max_shift_px, (right_gap - left_gap - thresh_x) * 0.5)
            tr[0] -= shift
            br[0] -= shift

        # Vertical balancing (less common but keeps symmetry)
        if top_gap - bottom_gap > thresh_y:
            shift = min(max_shift_px, (top_gap - bottom_gap - thresh_y) * 0.5)
            tl[1] -= shift
            tr[1] -= shift
        elif bottom_gap - top_gap > thresh_y:
            shift = min(max_shift_px, (bottom_gap - top_gap - thresh_y) * 0.5)
            bl[1] -= shift
            br[1] -= shift

        balanced = np.array([tl, tr, br, bl], dtype=np.float32)
        balanced[:, 0] = np.clip(balanced[:, 0], 0, w - 1)
        balanced[:, 1] = np.clip(balanced[:, 1], 0, h - 1)
        return balanced
    except Exception:
        return corners.reshape(4, 2).astype(np.float32)


def _tighten_contour_with_text(gray, corners, image_area):
    """Use text/content mask to pull corners inward when the page is mostly background."""
    try:
        base = order_points(corners.reshape(4, 2).astype(np.float32))
        base_area = _safe_contour_area(base)
        if base_area <= 0:
            return base

        text_mask = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 10
        )
        text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        coords = cv2.findNonZero(text_mask)
        if coords is None or len(coords) < 50:
            return base

        rect = cv2.minAreaRect(coords)
        box = cv2.boxPoints(rect)

        # Gentle padding to keep small margins
        pad = max(4, int(min(gray.shape[:2]) * 0.01))
        box = box.astype(np.float32)
        box[:, 0] = np.clip(box[:, 0], 0, gray.shape[1] - 1)
        box[:, 1] = np.clip(box[:, 1], 0, gray.shape[0] - 1)
        box = order_points(box)
        box = box + np.array([[-pad, -pad], [pad, -pad], [pad, pad], [-pad, pad]], dtype=np.float32)
        box[:, 0] = np.clip(box[:, 0], 0, gray.shape[1] - 1)
        box[:, 1] = np.clip(box[:, 1], 0, gray.shape[0] - 1)

        box_area = _safe_contour_area(box)
        if box_area <= 0:
            return base

        # Only use if text box is reasonably close to detected page size
        if box_area < base_area * 0.9 and box_area > image_area * 0.1:
            return box

        return base
    except Exception:
        return corners.reshape(4, 2).astype(np.float32)


def _snap_to_min_area_rect(corners, image_area):
    """Project the quad to its minimum-area rectangle to align with page axes."""
    try:
        pts = corners.reshape(-1, 2).astype(np.float32)
        base_area = _safe_contour_area(pts)
        if base_area <= 0:
            return pts

        rect = cv2.minAreaRect(pts)
        box = cv2.boxPoints(rect).astype(np.float32)
        box = order_points(box)
        box_area = _safe_contour_area(box)

        if box_area <= 0 or box_area < image_area * 0.05:
            return pts

        # Prefer the rectangular fit if it is close in size or tighter than the current quad
        if 0.6 * base_area <= box_area <= 1.05 * base_area:
            return box
        if box_area < base_area:
            return box

        return pts
    except Exception:
        return corners.reshape(4, 2).astype(np.float32)


def detect_document_corners(image):
    """
    Detects document/page edges optimized for black and white pages.
    Uses multiple strategies:
    1. Intensity thresholding (pages are bright)
    2. Hough Lines for precise edge detection
    3. GrabCut for foreground segmentation
    4. Harris corner refinement
    
    Returns: (corners_4x2_float32, confidence_0_to_1)
    """
    if image is None or image.size == 0:
        return None, 0.0

    h, w = image.shape[:2]
    image_area = h * w
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    best_contour = None
    best_area = 0
    
    # STRATEGY 1: Hough Lines - precise edge detection
    contour, area = _detect_page_with_hough_lines(gray, image_area)
    if contour is not None and area > best_area:
        best_area = area
        best_contour = contour
    
    # STRATEGY 2: Intensity threshold (pages are bright)
    if best_contour is None or best_area < image_area * 0.25:
        for thresh_val in [180, 160, 140, 120, 200]:
            _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10)))
            
            cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = _safe_sort_contours(cnts, 3)
            
            contour, area = _find_best_quad(cnts, image_area, 0.15)
            if contour is not None and area > best_area:
                best_area = area
                best_contour = contour
            
            contour, area = _find_quad_from_hull(cnts, image_area, 0.15)
            if contour is not None and area > best_area:
                best_area = area
                best_contour = contour

    # STRATEGY 3: GrabCut segmentation
    if best_contour is None or best_area < image_area * 0.25:
        grabcut_mask = _detect_page_with_grabcut(image)
        if grabcut_mask is not None:
            cnts, _ = cv2.findContours(grabcut_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = _safe_sort_contours(cnts, 3)
            
            contour, area = _find_best_quad(cnts, image_area, 0.15)
            if contour is not None and area > best_area:
                best_area = area
                best_contour = contour
            
            contour, area = _find_quad_from_hull(cnts, image_area, 0.15)
            if contour is not None and area > best_area:
                best_area = area
                best_contour = contour

    # STRATEGY 4: Otsu threshold
    if best_contour is None or best_area < image_area * 0.25:
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        otsu = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
        otsu = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
        
        cnts, _ = cv2.findContours(otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = _safe_sort_contours(cnts, 3)
        
        contour, area = _find_best_quad(cnts, image_area, 0.15)
        if contour is not None and area > best_area:
            best_area = area
            best_contour = contour
        
        contour, area = _find_quad_from_hull(cnts, image_area, 0.15)
        if contour is not None and area > best_area:
            best_area = area
            best_contour = contour

    # STRATEGY 5: Heavy blur edge detection (fallback)
    if best_contour is None or best_area < image_area * 0.2:
        heavily_blurred = cv2.GaussianBlur(gray, (25, 25), 0)
        
        for low, high in [(20, 50), (30, 70), (15, 40)]:
            edged = cv2.Canny(heavily_blurred, low, high)
            edged = cv2.dilate(edged, np.ones((7, 7), np.uint8), iterations=3)
            
            cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = _safe_sort_contours(cnts, 3)
            
            contour, area = _find_best_quad(cnts, image_area, 0.15)
            if contour is not None and area > best_area:
                best_area = area
                best_contour = contour
            
            contour, area = _find_quad_from_hull(cnts, image_area, 0.15)
            if contour is not None and area > best_area:
                best_area = area
                best_contour = contour

    # Refine corners using Harris corner detection
    if best_contour is not None:
        corners = best_contour.reshape(4, 2)
        
        # First, shrink corners that are in dark background to actual page edges
        corners = _shrink_to_page_edges(gray, corners)
        
        # Then apply Harris corner detection for precise corner placement
        corners = _refine_corners_with_harris(gray, corners, search_radius=30)
        
        # Final verification - ensure corners are on bright regions
        corners = _verify_and_adjust_corners(gray, corners, search_radius=20)

        candidates = []
        candidates.append(corners)
        candidates.append(_tighten_contour_with_edges(gray, corners, image_area))
        candidates.append(_tighten_contour_with_text(gray, corners, image_area))
        candidates.append(_snap_to_min_area_rect(corners, image_area))
        candidates.append(_snap_edges_to_bright_region(gray, corners, max_shift=12, intensity_threshold=175))
        candidates.append(_refine_edges_with_local_contrast(gray, corners, max_shift=18, samples=60))
        candidates.append(_balance_side_gaps(gray, corners, max_diff_ratio=0.08, max_shift_px=14))

        corners = _select_best_quad(gray, candidates, image_area)

        # Also apply sub-pixel refinement
        try:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)
            corners = cv2.cornerSubPix(gray, corners, (5, 5), (-1, -1), criteria)
        except Exception:
            pass

        best_contour = corners.reshape(4, 1, 2)
        best_area = _safe_contour_area(corners)

    if best_contour is not None:
        corners = order_points(best_contour.reshape(4, 2).astype("float32"))
        area_ratio = best_area / image_area
        
        if area_ratio >= 0.35:
            confidence = min(1.0, 0.8 + (area_ratio - 0.35) * 0.4)
        elif area_ratio >= 0.25:
            confidence = 0.65 + (area_ratio - 0.25) * 1.5
        elif area_ratio >= 0.15:
            confidence = 0.4 + (area_ratio - 0.15) * 2.5
        else:
            confidence = area_ratio / 0.15 * 0.4
        return corners, round(confidence, 3)

    # Fallback: full image bounds
    margin = 10
    fallback = np.array([
        [margin, margin], [w - margin, margin],
        [w - margin, h - margin], [margin, h - margin]
    ], dtype="float32")
    return fallback, 0.0

def auto_trim_white_borders(image):
    """
    Removes white borders left by rotation. Crops to the content area.
    """
    if image is None or image.size == 0:
        return image
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Threshold to find non-white pixels
        _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        # Find bounding rect of content
        coords = cv2.findNonZero(thresh)
        if coords is None:
            return image
        x, y, cw, ch = cv2.boundingRect(coords)
        # Add small padding
        pad = 5
        x = max(0, x - pad)
        y = max(0, y - pad)
        cw = min(image.shape[1] - x, cw + 2 * pad)
        ch = min(image.shape[0] - y, ch + 2 * pad)
        if cw < 50 or ch < 50:  # Safety: don't crop to nothing
            return image
        return image[y:y+ch, x:x+cw]
    except Exception:
        return image


def get_scan_pipeline(image_bytes):
    """Run the default scan pipeline from raw image bytes.

    The pipeline decodes the input image, estimates document contour,
    applies perspective correction, deskews text, trims rotation borders,
    and returns the balanced readable scan output.
    """
    try:
        # 1. Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None or img.size == 0:
            return None
            
        # 2. Pre-process for Edge Detection (We use grayscale ONLY for detection)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)

        # 3. Find Contours
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = _safe_sort_contours(cnts, 5)
        
        screen_cnt = None
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                screen_cnt = approx
                break

        # 4. Perspective Warp
        if screen_cnt is None:
            warped = img
        else:
            # We warp the ORIGINAL COLOR IMAGE (img), not the grayscale one
            warped = four_point_transform(img, screen_cnt.reshape(4, 2))
            # If transform failed, use original
            if warped is None:
                warped = img
            else:
                # Auto-deskew to straighten text lines
                warped = auto_deskew(warped)
                warped = auto_trim_white_borders(warped)

        # 5. THE "MAGIC" FILTER - Now uses improved algorithm
        magic_result = apply_master_readable_pro(warped)
        
        return magic_result
    except Exception:
        logger.exception("get_scan_pipeline failed")
        return None


def rotate_image_horizontal(image, angle):
    """
    Rotates image horizontally (Z-axis rotation) by the specified angle.
    Positive angle = clockwise rotation.
    
    Args:
        image: Input image (BGR format)
        angle: Rotation angle in degrees (-45 to 45 recommended)
    
    Returns:
        Rotated image with preserved content
    """
    if image is None or angle == 0:
        return image
    
    try:
        # Get image dimensions
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        
        # Calculate rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calculate new bounding dimensions to prevent cropping
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # Adjust rotation matrix for translation
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        # Perform rotation with white background
        rotated = cv2.warpAffine(image, M, (new_w, new_h), 
                                 borderMode=cv2.BORDER_CONSTANT, 
                                 borderValue=(255, 255, 255))
        
        return rotated
    except Exception:
        logger.exception("rotate_image_horizontal failed")
        return image


def apply_perspective_tilt(image, vertical_angle):
    """
    Applies vertical perspective tilt (X-axis rotation) to correct document viewing angle.
    Simulates 3D rotation around horizontal axis.
    
    Args:
        image: Input image (BGR format)
        vertical_angle: Tilt angle in degrees (-45 to 45)
                       Positive = top of document tilts away from viewer
                       Negative = top of document tilts toward viewer
    
    Returns:
        Perspective-corrected image
    """
    if image is None or vertical_angle == 0:
        return image
    
    try:
        h, w = image.shape[:2]
        
        # Convert angle to radians
        angle_rad = np.radians(vertical_angle)
        
        # Calculate perspective transformation
        # The strength factor controls how much perspective is applied
        strength = np.tan(angle_rad) * h / 2
        
        # Define source points (original corners)
        src_pts = np.float32([
            [0, 0],           # Top-left
            [w, 0],           # Top-right
            [w, h],           # Bottom-right
            [0, h]            # Bottom-left
        ])
        
        # Define destination points (with perspective applied)
        # Positive angle: top edge moves away (gets smaller)
        # Negative angle: bottom edge moves away (gets smaller)
        if vertical_angle > 0:
            # Top edge compression
            offset_top = strength
            dst_pts = np.float32([
                [offset_top, 0],
                [w - offset_top, 0],
                [w, h],
                [0, h]
            ])
        else:
            # Bottom edge compression
            offset_bottom = abs(strength)
            dst_pts = np.float32([
                [0, 0],
                [w, 0],
                [w - offset_bottom, h],
                [offset_bottom, h]
            ])
        
        # Calculate perspective transform matrix
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        # Apply transformation with white background
        result = cv2.warpPerspective(image, matrix, (w, h),
                                      borderMode=cv2.BORDER_CONSTANT,
                                      borderValue=(255, 255, 255))
        
        return result
    except Exception:
        logger.exception("apply_perspective_tilt failed")
        return image


def estimate_vertical_tilt_from_corners(pts):
    """Estimate vertical perspective tilt from a quadrilateral.

    Positive angle means top edge should be compressed (top closer to camera).
    Negative angle means bottom edge should be compressed.
    """
    try:
        rect = order_points(pts.reshape(4, 2).astype(np.float32))
        tl, tr, br, bl = rect

        top_w = np.linalg.norm(tr - tl)
        bottom_w = np.linalg.norm(br - bl)
        height = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2.0

        if height <= 1e-3:
            return 0.0

        width_diff = top_w - bottom_w
        angle_deg = np.degrees(np.arctan2(width_diff, height))

        # Clamp to sane range to avoid overcorrection
        angle_deg = float(np.clip(angle_deg, -25.0, 25.0))
        return angle_deg
    except Exception:
        return 0.0