from django.urls import path
from . import views

urlpatterns = [
    path('ocr', views.ocr_view, name='ocr'),
    path('validate-document', views.validate_document_view, name='validate_document'),
    path('detect-tampering', views.detect_tampering_view, name='detect_tampering'),
    path('verify-face', views.verify_face_view, name='verify_face'),
    path('save-verified-user', views.save_verified_user_view, name='save_verified_user'),
    path('detect-corners', views.detect_corners_view, name='detect_corners'),
    path('scan-pro', views.scan_pro_view, name='scan_pro'),
]

