from fastapi import FastAPI, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
import logging
from processor import (
    get_scan_pipeline, 
    four_point_transform, 
    apply_master_readable_pro,
    apply_premium_color_scan,
    apply_ultra_sharp_text,
    detect_and_warp,
    rotate_image_horizontal,
    apply_perspective_tilt,
    estimate_vertical_tilt_from_corners,
    detect_document_corners,
    auto_trim_white_borders,
    auto_deskew
)
import numpy as np
import cv2
import json
from fastapi import Form
import img2pdf
from typing import List


logger = logging.getLogger(__name__)

app = FastAPI()

# IMPORTANT: This allows your React app to talk to your Python API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "WebCam Scanner API is running",
        "endpoints": ["/scan", "/detect-corners", "/scan-pro", "/generate-pdf"]
    }

@app.post("/scan")
async def scan_document(file: UploadFile = File(...)):
    # 1. Read the uploaded file
    img_bytes = await file.read()
    
    # 2. Run through your 'processor.py' logic
    processed_img = get_scan_pipeline(img_bytes)
    
    # 3. Check if processing was successful
    if processed_img is None:
        return Response(content=b"Error: Could not process image", status_code=400)
    
    # 4. Encode back to PNG to send to the browser
    _, buffer = cv2.imencode(".png", processed_img)
    
    return Response(content=buffer.tobytes(), media_type="image/png")


@app.post("/detect-corners")
async def detect_corners(file: UploadFile = File(...)):
    """
    Detect document corners from an uploaded image.

    Returns the best 4-point polygon, confidence score,
    and image dimensions for frontend coordinate mapping.
    
    If confidence is high (>0.6), the frontend can auto-process.
    If confidence is low, the frontend should show manual crop UI
    with these detected corners pre-populated.
    """
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None or img.size == 0:
            return {"corners": [], "confidence": 0, "image_width": 0, "image_height": 0}

        h, w = img.shape[:2]
        corners, confidence = detect_document_corners(img)

        # Convert corners to list of {x, y} dicts for JSON
        corners_list = [{"x": float(pt[0]), "y": float(pt[1])} for pt in corners]

        return {
            "corners": corners_list,
            "confidence": confidence,
            "image_width": w,
            "image_height": h
        }
    except Exception:
        logger.exception("detect_corners endpoint failed")
        return {"corners": [], "confidence": 0, "image_width": 0, "image_height": 0}


@app.post("/scan-pro")
async def scan_pro(
    file: UploadFile = File(...), 
    corners: str = Form(None), 
    filter_mode: str = Form("balanced"),
    horizontal_tilt: float = Form(0.0),
    vertical_tilt: float = Form(0.0),
    auto_deskew_enabled: bool = Form(True)
):
    """
    Advanced scan with manual corner adjustment, filter selection, and rotation controls.
    
    Parameters:
    - file: Image file to process
    - corners: JSON string of corner points for perspective correction
    - filter_mode: "balanced" (default), "color", or "text"
    - horizontal_tilt: Rotation angle in degrees (-45 to 45)
    - vertical_tilt: Vertical perspective angle in degrees (-45 to 45)
    - auto_deskew_enabled: Whether to automatically correct text skew (default: True)
    """
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None or img.size == 0:
            return Response(content=b"Error: Could not decode image", status_code=400)

        # STEP 1: Perspective correction (crop/warp)
        pts = None
        if corners:
            pts_list = json.loads(corners) 
            pts = np.array([[p['x'], p['y']] for p in pts_list], dtype="float32")
            if pts.shape != (4, 2):
                return Response(content=b"Error: corners must contain 4 points", status_code=400)
            
            warped = four_point_transform(img, pts)
            if warped is None:
                warped = img
        else:
            # detect_and_warp already includes auto_deskew
            warped = detect_and_warp(img)
            if warped is None:
                warped = img

        if warped is None or warped.size == 0:
            return Response(content=b"Error: Could not process image", status_code=400)

        # STEP 2: Always apply deskew after crop (unless disabled)
        # This ensures text lines are horizontal regardless of how the document was cropped
        if auto_deskew_enabled:
            warped = auto_deskew(warped)

        # STEP 3: Apply rotation adjustments if specified
        if horizontal_tilt != 0:
            warped = rotate_image_horizontal(warped, horizontal_tilt)
            warped = auto_trim_white_borders(warped)
        
        # If no explicit vertical tilt provided but corners are known, estimate and apply
        applied_vertical_tilt = vertical_tilt
        if applied_vertical_tilt == 0 and pts is not None:
            applied_vertical_tilt = estimate_vertical_tilt_from_corners(pts)
        
        if applied_vertical_tilt != 0:
            warped = apply_perspective_tilt(warped, applied_vertical_tilt)
            warped = auto_trim_white_borders(warped)

        # STEP 4: Apply the selected filter
        if filter_mode == "color":
            result = apply_premium_color_scan(warped)
        elif filter_mode == "text":
            result = apply_ultra_sharp_text(warped)
        else:  # "balanced" or default
            result = apply_master_readable_pro(warped)

        if result is None or result.size == 0:
            return Response(content=b"Error: Filter processing failed", status_code=400)

        _, buffer = cv2.imencode(".png", result)
        return Response(content=buffer.tobytes(), media_type="image/png")
    except Exception as e:
        logger.exception("scan_pro endpoint failed")
        return Response(content=f"Error: {str(e)}".encode(), status_code=500)

@app.post("/generate-pdf")
async def generate_pdf(files: List[UploadFile] = File(...)):
    image_data_list = [await f.read() for f in files]
    
    # Force the PDF to use a standard A4 layout (Portrait)
    # This ensures your card doesn't look 'distorted' on the page
    a4_layout = img2pdf.get_layout_fun((img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297)))
    
    pdf_bytes = img2pdf.convert(image_data_list, layout_fun=a4_layout)
    
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=MagicScan.pdf"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)