import os
import json
import cv2
import pandas as pd
import numpy as np
import streamlit as st
from PIL import Image

from src.pipeline import DocumentPipeline
from src.input_handler import InputHandler
from src.region_cropper import DocumentRegionCropper
from src.side_router import DocumentSideRules

st.set_page_config(
    page_title="Document Extraction System",
    layout="wide"
)

st.title("Scanner Document Extraction System")
st.caption("Side-Aware Document Processing Pipeline for Scanner Inputs (Aadhaar, Passport, Driving Licence)")

def get_pipeline():
    return DocumentPipeline(output_dir="output")

pipeline = get_pipeline()

# Sidebar: Document Feature Requirements Specification
with st.sidebar:
    st.header("📋 Feature Specification Matrix")
    st.markdown("Shows **which document requires which feature to extract**:")
    
    spec_data = [
        {
            "Document": "Aadhaar Card (2 Scans)",
            "Front Side": "Photo, Name, DOB, Gender, UID (No QR)",
            "Back Side": "2D QR Code, Address, UID (No Photo)"
        },
        {
            "Document": "Passport (1 Scan)",
            "Front Side": "Photo, Passport No, Surname, Given Name, DOB, Sex, Expiry, MRZ (No QR)",
            "Back Side": "N/A"
        },
        {
            "Document": "Driving Licence (2 Scans)",
            "Front Side": "Photo, Chip, DL No, Name, DOB, Validity NT (No QR)",
            "Back Side": "Small QR / Barcode, Address, Vehicle Classes"
        }
    ]
    st.table(pd.DataFrame(spec_data))

def save_uploaded_file(uploaded_file, name_prefix="scan") -> str:
    if not uploaded_file:
        return None
    temp_dir = "scratch"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{name_prefix}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# Document Scanner Mode Tabs
tab_aadhaar, tab_passport, tab_dl, tab_auto = st.tabs([
    "🪪 Aadhaar Scanner (Front + Back)",
    "📘 Passport Scanner (1 Image Data Page)",
    "💳 Driving Licence (Front + Back)",
    "📁 Single File / Auto-Detect"
])

# ==========================================
# TAB 1: AADHAAR SCANNER MODE (2 Separate Image Inputs)
# ==========================================
with tab_aadhaar:
    st.markdown("### 🪪 Aadhaar 2-Side Scanner Input")
    col1, col2 = st.columns(2)
    with col1:
        f_aadhaar_front = st.file_uploader("Upload Aadhaar FRONT Side Image (Photo, Name, DOB, Gender, UID)", type=["jpg", "png", "jpeg", "webp"], key="a_front")
    with col2:
        f_aadhaar_back = st.file_uploader("Upload Aadhaar BACK Side Image (Address, 2D QR Code, UID)", type=["jpg", "png", "jpeg", "webp"], key="a_back")

    if f_aadhaar_front or f_aadhaar_back:
        p_front = save_uploaded_file(f_aadhaar_front, "aadhaar_front")
        p_back = save_uploaded_file(f_aadhaar_back, "aadhaar_back")

        with st.spinner("Processing Aadhaar Scanned Images..."):
            res_json = pipeline.process_scanned_sides(front_path=p_front, back_path=p_back, doc_type="aadhaar")

        st.success("✅ Aadhaar Extraction Completed!")
        
        c_left, c_right = st.columns([1.1, 1])
        with c_left:
            st.markdown("#### 📊 Consolidated Extracted Text Data")
            fields = res_json.get("extracted_fields", {})
            fields_df = []
            for k, v in fields.items():
                if v:
                    clean_key = k.replace("_", " ").title()
                    fields_df.append({"Field Name": clean_key, "Extracted Value": str(v)})
            if fields_df:
                st.table(pd.DataFrame(fields_df))

        with c_right:
            st.markdown("#### 📷 Extracted Visual Component Images")
            img_c1, img_c2 = st.columns(2)
            crops = res_json.get("cropped_images", {})
            with img_c1:
                st.markdown("**Face Photo Box (From Front)**")
                if crops.get("photo_image_path") and os.path.exists(crops["photo_image_path"]):
                    st.image(crops["photo_image_path"], use_container_width=True)
                else:
                    st.caption("No photo extracted")
            with img_c2:
                st.markdown("**2D QR Code Box (From Back)**")
                if crops.get("qr_image_path") and os.path.exists(crops["qr_image_path"]):
                    st.image(crops["qr_image_path"], use_container_width=True)
                else:
                    st.caption("No QR code on front / back image")

        st.markdown("#### 📄 Output JSON File (Text Data + Photo & QR References)")
        st.json(res_json)

# ==========================================
# TAB 2: PASSPORT SCANNER MODE (1 Image Input)
# ==========================================
with tab_passport:
    st.markdown("### 📘 Passport Data Page Scanner Input")
    f_passport = st.file_uploader("Upload Passport Data Page Scan (1 Image - Photo, Details, MRZ Code)", type=["jpg", "png", "jpeg", "webp", "pdf"], key="pass_img")

    if f_passport:
        p_pass = save_uploaded_file(f_passport, "passport")
        with st.spinner("Processing Passport Scan..."):
            res_json = pipeline.process_scanned_sides(front_path=p_pass, doc_type="passport")

        st.success("✅ Passport Extraction Completed!")
        c_left, c_right = st.columns([1.1, 1])
        with c_left:
            st.markdown("#### 📊 Extracted Passport Text & MRZ Data")
            fields = res_json.get("extracted_fields", {})
            fields_df = []
            for k, v in fields.items():
                if v and k != "mrz_raw":
                    clean_key = k.replace("_", " ").title()
                    fields_df.append({"Field Name": clean_key, "Extracted Value": str(v)})
            if fields_df:
                st.table(pd.DataFrame(fields_df))

            if fields.get("mrz_raw"):
                st.markdown("**ICAO 9303 MRZ Code Zone**")
                st.code("\n".join(fields["mrz_raw"]) if isinstance(fields["mrz_raw"], list) else str(fields["mrz_raw"]), language="text")

        with c_right:
            st.markdown("#### 📷 Extracted Face Photo Box")
            crops = res_json.get("cropped_images", {})
            if crops.get("photo_image_path") and os.path.exists(crops["photo_image_path"]):
                st.image(crops["photo_image_path"], caption="Passport Holder Face Portrait", use_container_width=True)
            else:
                st.caption("No face photo box detected")
            
            st.info("ℹ️ Passports do not contain QR codes (QR search disabled).")

        st.markdown("#### 📄 Output JSON Record (Text Data + Photo Reference)")
        st.json(res_json)

# ==========================================
# TAB 3: DRIVING LICENCE SCANNER MODE (2 Separate Image Inputs)
# ==========================================
with tab_dl:
    st.markdown("### 💳 Driving Licence 2-Side Scanner Input")
    col1, col2 = st.columns(2)
    with col1:
        f_dl_front = st.file_uploader("Upload Driving Licence FRONT Side Image (Photo, Chip, DL No, Name, DOB, Validity)", type=["jpg", "png", "jpeg", "webp"], key="dl_front")
    with col2:
        f_dl_back = st.file_uploader("Upload Driving Licence BACK Side Image (Address, Small QR/Barcode, Vehicle Classes)", type=["jpg", "png", "jpeg", "webp"], key="dl_back")

    if f_dl_front or f_dl_back:
        p_dl_front = save_uploaded_file(f_dl_front, "dl_front")
        p_dl_back = save_uploaded_file(f_dl_back, "dl_back")

        with st.spinner("Processing Driving Licence Scans..."):
            res_json = pipeline.process_scanned_sides(front_path=p_dl_front, back_path=p_dl_back, doc_type="dl")

        st.success("✅ Driving Licence Extraction Completed!")
        c_left, c_right = st.columns([1.1, 1])
        with c_left:
            st.markdown("#### 📊 Consolidated DL Fields")
            fields = res_json.get("extracted_fields", {})
            fields_df = []
            for k, v in fields.items():
                if v:
                    clean_key = k.replace("_", " ").title()
                    fields_df.append({"Field Name": clean_key, "Extracted Value": str(v)})
            if fields_df:
                st.table(pd.DataFrame(fields_df))

        with c_right:
            st.markdown("#### 📷 Extracted Visual Component Images")
            img_c1, img_c2 = st.columns(2)
            crops = res_json.get("cropped_images", {})
            with img_c1:
                st.markdown("**Face Photo Box (From Front)**")
                if crops.get("photo_image_path") and os.path.exists(crops["photo_image_path"]):
                    st.image(crops["photo_image_path"], use_container_width=True)
                else:
                    st.caption("No photo extracted")
            with img_c2:
                st.markdown("**Small QR / Barcode Box (From Back)**")
                if crops.get("qr_image_path") and os.path.exists(crops["qr_image_path"]):
                    st.image(crops["qr_image_path"], use_container_width=True)
                else:
                    st.caption("No QR code extracted")

        st.markdown("#### 📄 Output JSON Record (Text Data + Photo & QR References)")
        st.json(res_json)

# ==========================================
# TAB 4: SINGLE FILE / AUTO DETECT MODE
# ==========================================
with tab_auto:
    st.markdown("### 📁 Single File Upload / Auto-Detect Pipeline")
    uploaded_files = st.file_uploader(
        "Upload Document File(s) - Photo, Scan or PDF",
        type=["jpg", "jpeg", "png", "webp", "pdf"],
        accept_multiple_files=True,
        key="auto_files"
    )

    if uploaded_files:
        target_paths = []
        temp_dir = "scratch"
        os.makedirs(temp_dir, exist_ok=True)
        for up_file in uploaded_files:
            path = os.path.join(temp_dir, up_file.name)
            with open(path, "wb") as f:
                f.write(up_file.getbuffer())
            target_paths.append(path)

        raw_results = []
        for path in target_paths:
            file_res = pipeline.process_file(path)
            raw_results.extend(file_res)

        aggregated_results = pipeline.aggregate_multi_side_scans(raw_results)

        for res in aggregated_results:
            target_path = os.path.join("scratch", res["file_name"]) if os.path.exists(os.path.join("scratch", res["file_name"])) else target_paths[0]
            st.divider()
            st.subheader(f"📄 Document: {res['document_name'].upper()} ({res['file_name']})")

            pages = InputHandler.load_document(target_path)
            p_idx = min(res.get("page_number", 1) - 1, len(pages) - 1)
            img_bgr = pages[p_idx][1]

            col_img, col_data = st.columns([1, 1.2])
            with col_img:
                st.markdown("### Document Picture")
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                st.image(img_rgb, caption=f"{res['file_name']}", use_container_width=True)
                st.markdown(f"**Detected Type**: `{res['document_name'].upper()}`")

            with col_data:
                st.markdown("### Extracted Features")
                fields = res["extracted_fields"]
                fields_df = [{"Field Name": k.replace("_", " ").title(), "Extracted Value": str(v)} for k, v in fields.items() if v and k not in ("immigration_stamps", "mrz_raw")]
                if fields_df:
                    st.table(pd.DataFrame(fields_df))

                tamp = res.get("tampering_detection", {})
                qr_status = "YES (QR Present)" if tamp.get("qr_detected") else "NO (No QR Code Detected / Non-QR Side)"
                st.markdown(f"**QR Code Status**: {qr_status}")

            st.divider()
            st.markdown("### Extracted Visual Components: Face Photo & QR / Barcode Box")

            crops = DocumentRegionCropper.crop_document_components(
                img_bgr, 
                doc_type=res.get("document_type", "unknown"), 
                side="auto",
                qr_info=tamp, 
                text_blocks=res.get("text_blocks", []),
                raw_text=res.get("raw_ocr_text", "")
            )
            
            c_photo, c_qr = st.columns(2)
            with c_photo:
                st.markdown("#### 📷 Face Photo Box")
                if crops.get("photo") is not None and crops["photo"].size > 0:
                    photo_rgb = cv2.cvtColor(crops["photo"], cv2.COLOR_BGR2RGB)
                    st.image(photo_rgb, caption="Detected Face Portrait", use_container_width=True)
                else:
                    st.caption("No face photo box detected")

            with c_qr:
                st.markdown("#### 🔲 QR / Barcode Box")
                if crops.get("qr") is not None and crops["qr"].size > 0:
                    qr_rgb = cv2.cvtColor(crops["qr"], cv2.COLOR_BGR2RGB)
                    st.image(qr_rgb, caption="Detected 2D QR Code / Barcode", use_container_width=True)
                else:
                    st.caption("No QR code box detected")
