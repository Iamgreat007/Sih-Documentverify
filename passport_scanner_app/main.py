import os
import io
import json
import base64
from typing import List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from extractor import PassportExtractor

app = FastAPI(title="AI Passport Screening & MRZ Extractor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
PORTRAITS_DIR = os.path.join(BASE_DIR, "extracted_portraits")
STATIC_DIR = os.path.join(BASE_DIR, "static")
JSON_STORE_PATH = os.path.join(BASE_DIR, "extracted_passport_data.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PORTRAITS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

extractor = PassportExtractor(output_photo_dir=PORTRAITS_DIR)

# Mount static and media directories
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/extracted_portraits", StaticFiles(directory=PORTRAITS_DIR), name="portraits")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

def load_history():
    if os.path.exists(JSON_STORE_PATH):
        try:
            with open(JSON_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(records):
    with open(JSON_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Passport Scanner App running. Static index.html not found.</h1>")

@app.post("/api/scan")
async def scan_passport_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    
    history = load_history()
    newly_extracted = []

    for file in files:
        contents = await file.read()
        file_name = file.filename or "uploaded_passport.jpg"
        save_path = os.path.join(UPLOADS_DIR, file_name)
        
        with open(save_path, "wb") as f:
            f.write(contents)

        result = extractor.process_image(contents, file_name=file_name)
        
        # Adjust portrait path for frontend display
        if result.get("image_of_person"):
            result["image_of_person_url"] = f"/extracted_portraits/{os.path.basename(result['image_of_person'])}"
        
        result["uploaded_image_url"] = f"/uploads/{file_name}"
        
        newly_extracted.append(result)
        history.insert(0, result)

    save_history(history)
    return JSONResponse(content={"status": "success", "extracted": newly_extracted, "total_records": len(history)})

@app.post("/api/scan-camera")
async def scan_camera_snapshot(image_base64: str = Form(...), file_name: str = Form("camera_capture.jpg")):
    if not image_base64:
        raise HTTPException(status_code=400, detail="No image data provided.")

    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]

    try:
        img_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")

    save_path = os.path.join(UPLOADS_DIR, file_name)
    with open(save_path, "wb") as f:
        f.write(img_bytes)

    result = extractor.process_image(img_bytes, file_name=file_name)
    
    if result.get("image_of_person"):
        result["image_of_person_url"] = f"/extracted_portraits/{os.path.basename(result['image_of_person'])}"
    result["uploaded_image_url"] = f"/uploads/{file_name}"

    history = load_history()
    history.insert(0, result)
    save_history(history)

    return JSONResponse(content={"status": "success", "extracted": result, "total_records": len(history)})

@app.get("/api/history")
async def get_history():
    history = load_history()
    return JSONResponse(content={"records": history, "total": len(history)})

@app.get("/api/export-json")
async def export_json():
    if not os.path.exists(JSON_STORE_PATH):
        save_history([])
    return FileResponse(
        path=JSON_STORE_PATH,
        filename="extracted_passport_data.json",
        media_type="application/json"
    )

@app.delete("/api/clear")
async def clear_history():
    save_history([])
    return JSONResponse(content={"status": "cleared", "total": 0})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
