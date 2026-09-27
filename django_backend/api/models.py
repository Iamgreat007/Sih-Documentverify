from django.db import models

class VerifiedUser(models.Model):
    name = models.CharField(max_length=255)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    face_photo_path = models.CharField(max_length=500, null=True, blank=True)
    average_risk_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'api'

    def __str__(self):
        return f"{self.name} - Score: {self.average_risk_score}"

class DocumentRecord(models.Model):
    DOC_TYPES = [
        ('aadhaar', 'Aadhaar'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('visa', 'Visa'),
    ]

    user = models.ForeignKey(VerifiedUser, related_name='documents', on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    id_number = models.CharField(max_length=255)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    risk_score = models.FloatField(default=0.0)
    is_verified = models.BooleanField(default=False)
    
    # Paths to the extracted images
    pic_path = models.CharField(max_length=500, null=True, blank=True)
    qr_path = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        app_label = 'api'

    def __str__(self):
        return f"{self.doc_type} - {self.id_number} (Score: {self.risk_score})"

class ScanHistory(models.Model):
    document_type = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255)
    holder_name = models.CharField(max_length=255, blank=True, null=True)
    identifier = models.CharField(max_length=255, blank=True, null=True)
    risk_level = models.CharField(max_length=20)
    risk_score = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    image_thumbnail = models.TextField(blank=True, null=True)
    back_thumbnail = models.TextField(blank=True, null=True)
    ekyc_verified = models.BooleanField(default=False)
    
    result = models.JSONField(default=dict)
    extracted_fields = models.JSONField(default=dict)
    saved_paths = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        app_label = 'api'
        ordering = ['-timestamp']

    def __str__(self):
        return f"History: {self.document_type} - {self.identifier} ({self.timestamp})"
