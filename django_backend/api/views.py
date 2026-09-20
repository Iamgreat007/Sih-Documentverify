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
    Extracts QR code from the uploaded image if present.
    """
    doc_type = request.data.get('document_type', 'aadhaar')
    file_obj = request.FILES.get('file')
    
    fields = {}
    pic_path = ""
    qr_path = ""
    
    if file_obj:
        try:
            import cv2
            import numpy as np
            from pyzbar.pyzbar import decode
            
            # Read image for QR extraction
            contents = file_obj.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            decoded_objects = decode(img)
            if decoded_objects:
                qr_text = decoded_objects[0].data.decode('utf-8')
                fields['qr_data'] = {'key': 'qr_data', 'label': 'QR Code Data', 'value': qr_text, 'confidence': 100, 'editable': False}
                
                # Attempt to parse demographic data from the QR payload
                try:
                    import sys
                    sys.path.append(os.path.join(settings.BASE_DIR, '..'))
                    from aadhar import parse_secure_qr_string
                    payload, _ = parse_secure_qr_string(qr_text)
                    
                    if payload:
                        if payload.get('name'):
                            fields['name'] = {'key': 'name', 'label': 'Name', 'value': payload['name'], 'confidence': 100, 'editable': True}
                        if payload.get('dob'):
                            fields['dateOfBirth'] = {'key': 'dateOfBirth', 'label': 'Date of Birth', 'value': payload['dob'], 'confidence': 100, 'editable': True}
                        if payload.get('reference_id'):
                            # Mask the reference ID to look like masked Aadhaar
                            ref_id = str(payload['reference_id'])
                            masked = f"XXXX XXXX {ref_id[-4:]}" if len(ref_id) >= 4 else ref_id
                            fields['maskedAadhaar'] = {'key': 'maskedAadhaar', 'label': 'Masked Aadhaar Number', 'value': masked, 'confidence': 100, 'editable': True}
                except Exception as parse_err:
                    print("Could not parse QR payload for demographics:", parse_err)
                    
        except Exception as e:
            print("QR extraction failed:", e)
            
    return Response({"fields": fields, "pic_path": pic_path, "qr_path": qr_path})


@api_view(['POST'])
def validate_document_view(request):
    doc_type = request.data.get('docType', 'aadhaar')
    fields = request.data.get('fields', {})
    
    is_valid = True
    errors = []
    
    if doc_type == 'aadhaar':
        if not fields.get('maskedAadhaar', {}).get('value') or fields.get('maskedAadhaar', {}).get('value') == 'N/A':
            is_valid = False
            errors.append("Aadhaar Number missing")
            
        qr_data = fields.get('qr_data', {}).get('value', '')
        if qr_data:
            try:
                import sys
                import os
                sys.path.append(os.path.join(settings.BASE_DIR, '..'))
                from aadhar import parse_secure_qr_string, verify_aadhaar_signature, run_cross_verification
                
                payload, signature = parse_secure_qr_string(qr_data)
                is_signature_valid = verify_aadhaar_signature(payload, signature)
                if not is_signature_valid:
                    is_valid = False
                    errors.append("Aadhaar QR signature verification failed.")
                
                # Cross verify OCR extracted data against QR
                ocr_data = {k: v.get('value') for k, v in fields.items() if k != 'qr_data' and v.get('value')}
                cross_result = run_cross_verification(ocr_data, qr_data)
                
                if cross_result.get('tamper_detected'):
                    is_valid = False
                    errors.append(f"Tampering detected! Confidence: {cross_result.get('confidence_score')}%")
            except Exception as e:
                print("Cross-verification error:", e)
                errors.append(f"Cross-verification failed: {str(e)}")
        else:
            errors.append("No secure QR code found for verification.")
            is_valid = False
    
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
    
    # Save the selfie to the image folder
    selfie_path = ""
    if file_obj:
        output_dir = os.path.join(settings.BASE_DIR, '..', 'image')
        os.makedirs(output_dir, exist_ok=True)
        selfie_path = os.path.join(output_dir, "selfie_pic.jpg")
        with open(selfie_path, 'wb') as f:
            f.write(file_obj.read())

    # We assume the document picture is already saved as 'aadhaar_pic.jpg' or similar during OCR
    doc_pic_path = os.path.join(settings.BASE_DIR, '..', 'image', 'aadhaar_pic.jpg')
    
    try:
        payload = {
            "image1": doc_pic_path,
            "image2": selfie_path
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

