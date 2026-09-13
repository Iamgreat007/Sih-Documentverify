import os
import shutil
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from src.pipeline import DocumentPipeline

app = FastAPI(
    title="KYC Document OCR & Verification API",
    description="FastAPI service for identity document classification, OCR extraction, and checksum validation (Aadhaar, Passport, Visa, Driving Licence).",
    version="1.0.0"
)

# CORS middleware for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = DocumentPipeline(output_dir="output")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".bmp"}

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "KYC Document OCR & Extraction API",
        "endpoints": {
            "/extract": "POST - Upload document image or PDF for feature extraction"
        }
    }

@app.post("/extract")
async def extract_document(file: UploadFile = File(...)) -> JSONResponse:
    """
    Extracts structured KYC identity fields from uploaded photo or PDF document.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded. Please provide a valid document image or PDF."
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": True,
                "message": f"Unsupported file format '{ext}'. Supported formats: JPEG, PNG, WEBP, PDF.",
                "document_type": "unknown",
                "confidence": 0.0,
                "extracted_fields": {},
                "validation_status": {"overall": "fail"}
            }
        )

    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process document through end-to-end pipeline
        results = pipeline.process_file(temp_file_path)

        if not results:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": True,
                    "message": "Failed to parse document content from uploaded file.",
                    "document_type": "unknown",
                    "confidence": 0.0,
                    "extracted_fields": {},
                    "validation_status": {"overall": "fail"}
                }
            )

        res = results[0]

        response_payload = {
            "document_type": res["document_type"],
            "document_name": res["document_name"],
            "confidence": res["confidence"],
            "extracted_fields": res["extracted_fields"],
            "validation_status": res.get("validation_status", {"overall": "pass"}),
            "raw_ocr_text": res.get("raw_ocr_text", "")
        }

        return JSONResponse(status_code=status.HTTP_200_OK, content=response_payload)

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "message": f"An error occurred during OCR extraction: {str(e)}",
                "document_type": "unknown",
                "confidence": 0.0,
                "extracted_fields": {},
                "validation_status": {"overall": "fail"}
            }
        )
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
