"""
src/processor.py

Provides utility functions used by the DocumentPipeline.
The _rotate_image function is required by pipeline.py for orientation correction.
"""
import cv2
import numpy as np


def _rotate_image(image, angle):
    """
    Rotates image by the given angle (in degrees) while preserving content.
    Positive angle = counter-clockwise rotation.
    """
    if abs(angle) < 0.1:
        return image

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

    rotated = cv2.warpAffine(image, M, (new_w, new_h),
                              flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
    return rotated
