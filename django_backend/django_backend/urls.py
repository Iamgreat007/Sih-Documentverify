from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # Since frontend expects /scan-pro and /detect-corners at root level initially
    path('detect-corners', include([path('', include('api.urls'))])), # Actually, just map it explicitly
]

# Quick fix to allow root level routing for CV endpoints
from api import views
urlpatterns += [
    path('detect-corners', views.detect_corners_view),
    path('scan-pro', views.scan_pro_view),
]
