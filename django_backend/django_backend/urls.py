from django.contrib import admin
from django.urls import path, include
from api import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # Root-level CV endpoints (frontend expects these at top-level via Next.js rewrites)
    path('detect-corners', views.detect_corners_view),
    path('scan-pro', views.scan_pro_view),
]
