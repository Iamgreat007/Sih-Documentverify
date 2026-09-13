import os
import sys
import json
import requests
import numpy as np
import cv2
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse

# Add the old backend folder to path so we can import processor.py
backend_dir = os.path.join(settings.BASE_DIR, '..', 'backend')
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    from processor import detect_document_corners, four_point_transform, auto_deskew, apply_master_readable_pro, apply_ultra_sharp_text, apply_premium_color_scan
except ImportError:
    pass

from .models import VerifiedUser, DocumentRecord

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')

def load_json_data(doc_type):
    # Mapping doc types to file names
    mapping = {
        'aadhaar': 'aadhar.json',
        'driving_license': 'dl.json',
        'passport': 'passport.json',
        'visa': 'visa.json'
    }
    filename = mapping.get(doc_type, f"{doc_type}.json")
    filepath = os.path.join(DATA_DIR, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

@api_view(['POST'])
def ocr_view(request):
    """
    Simulates OCR extraction by reading from the predefined JSON files.
    Defaults to 'N/A' if fields are missing.
    Also saves <documentname>_pic.jpg and <documentname>_qr.jpg mock images.
    """
    doc_type = request.data.get('document_type', 'aadhaar')
    file_obj = request.FILES.get('file')
    
    json_data = load_json_data(doc_type)
    
    # Save mock pic and qr if file was uploaded
    pic_path = ""
    qr_path = ""
    if file_obj:
        output_dir = os.path.join(settings.BASE_DIR, '..', 'image')
        os.makedirs(output_dir, exist_ok=True)
        pic_path = os.path.join(output_dir, f"{doc_type}_pic.jpg")
        qr_path = os.path.join(output_dir, f"{doc_type}_qr.jpg")
        
        # Just write the uploaded file as both pic and qr for mockup
        file_content = file_obj.read()
        with open(pic_path, 'wb') as f:
            f.write(file_content)
        with open(qr_path, 'wb') as f:
            f.write(file_content)

    # Format fields as expected by frontend
    # If the JSON is empty, provide defaults or N/A
    fields = {}
    
    if doc_type == 'aadhaar':
        fields['name'] = {'key': 'name', 'label': 'Name', 'value': json_data.get('name', 'N/A'), 'confidence': 99, 'editable': True}
        fields['dateOfBirth'] = {'key': 'dateOfBirth', 'label': 'Date of Birth', 'value': json_data.get('dob', 'N/A'), 'confidence': 97, 'editable': True}
        fields['maskedAadhaar'] = {'key': 'maskedAadhaar', 'label': 'Masked Aadhaar Number', 'value': json_data.get('aadhaar_number', 'N/A'), 'confidence': 99, 'editable': True}
    elif doc_type == 'passport':
        fields['name'] = {'key': 'name', 'label': 'Name', 'value': json_data.get('name', 'N/A'), 'confidence': 99, 'editable': True}
        fields['passportNumber'] = {'key': 'passportNumber', 'label': 'Passport Number', 'value': json_data.get('passport_number', 'N/A'), 'confidence': 99, 'editable': True}
    elif doc_type == 'driving_license':
        fields['dlNumber'] = {'key': 'dlNumber', 'label': 'Licence Number', 'value': json_data.get('dl_number', 'N/A'), 'confidence': 99, 'editable': True}
        fields['name'] = {'key': 'name', 'label': 'Holder Name', 'value': json_data.get('name', 'N/A'), 'confidence': 99, 'editable': True}
    elif doc_type == 'visa':
        fields['visaNumber'] = {'key': 'visaNumber', 'label': 'Visa Number', 'value': json_data.get('visa_number', 'N/A'), 'confidence': 99, 'editable': True}
        
    return Response({"fields": fields, "pic_path": pic_path, "qr_path": qr_path})


@api_view(['POST'])
def validate_document_view(request):
    doc_type = request.data.get('docType', 'aadhaar')
    fields = request.data.get('fields', {})
    
    json_data = load_json_data(doc_type)
    
    # Simple validation mock using JSON data
    is_valid = True
    errors = []
    
    if doc_type == 'aadhaar':
        if fields.get('maskedAadhaar', {}).get('value') == 'N/A':
            is_valid = False
            errors.append("Aadhaar Number missing")
    
    return Response({
        "isValid": is_valid,
        "mrzValid": True,
        "checksumValid": is_valid,
        "expiryValid": True,
        "errors": errors
    })


@api_view(['POST'])
def detect_tampering_view(request):
    # Mock response
    return Response({
        "tampered": False,
        "tamperConfidence": 5,
        "anomalies": []
    })


@api_view(['POST'])
def verify_face_view(request):
    file_obj = request.FILES.get('file')
    
    # Try calling the Java Spring Boot Face Recognition API
    java_api_url = "http://localhost:8080/api/face-match"
    
    try:
        # In a real app, we would send the image file or paths.
        # Here we just pass mock paths
        payload = {
            "image1": "mock_pic1.jpg",
            "image2": "mock_pic2.jpg"
        }
        res = requests.post(java_api_url, json=payload, timeout=2)
        if res.status_code == 200:
            data = res.json()
            return Response({
                "matched": data.get("matched", True),
                "matchScore": data.get("score", 95.0),
                "livenessPassed": True
            })
    except Exception as e:
        print("Java Face API not reachable, falling back to mock:", e)
        
    return Response({
        "matched": True,
        "matchScore": 92,
        "livenessPassed": True
    })

@api_view(['POST'])
def save_verified_user_view(request):
    """
    Endpoint to save verified user data and documents.
    Provides final risk score and persists in the database.
    """
    data = request.data
    name = data.get('name', 'Unknown')
    score = data.get('average_risk_score', 15.0)
    
    user = VerifiedUser.objects.create(
        name=name,
        average_risk_score=score
    )
    
    return Response({"status": "success", "user_id": user.id})

@api_view(['POST'])
def detect_corners_view(request):
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({"corners": [], "confidence": 0, "image_width": 0, "image_height": 0})
        
    try:
        contents = file_obj.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        h, w = img.shape[:2]
        corners, confidence = detect_document_corners(img)
        corners_list = [{"x": float(pt[0]), "y": float(pt[1])} for pt in corners]

        return Response({
            "corners": corners_list,
            "confidence": confidence,
            "image_width": w,
            "image_height": h
        })
    except Exception as e:
        return Response({"corners": [], "confidence": 0, "image_width": 0, "image_height": 0})


@api_view(['POST'])
def scan_pro_view(request):
    file_obj = request.FILES.get('file')
    corners_str = request.data.get('corners')
    filter_mode = request.data.get('filter_mode', 'balanced')
    
    try:
        contents = file_obj.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if corners_str:
            pts_list = json.loads(corners_str)
            pts = np.array([[p['x'], p['y']] for p in pts_list], dtype="float32")
            warped = four_point_transform(img, pts)
        else:
            warped = img
            
        if warped is None:
            warped = img
            
        warped = auto_deskew(warped)
        
        if filter_mode == "color":
            result = apply_premium_color_scan(warped)
        elif filter_mode == "text":
            result = apply_ultra_sharp_text(warped)
        else:
            result = apply_master_readable_pro(warped)
            
        _, buffer = cv2.imencode(".png", result)
        return HttpResponse(buffer.tobytes(), content_type="image/png")
    except Exception as e:
        return Response({"error": str(e)}, status=500)

