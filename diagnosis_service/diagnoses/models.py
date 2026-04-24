import uuid
from django.db import models

class Diagnosis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('processing', 'Processing'),
        ('completed', 'Completed'), ('failed', 'Failed'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field_id   = models.UUIDField()      # soft FK → Farm Service
    farmer_id  = models.UUIDField()      # soft FK → Auth Service
    image_path = models.CharField(max_length=500)
    status     = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Diagnosis {self.id} — {self.status}"


class DiagnosisResult(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    diagnosis       = models.OneToOneField(Diagnosis, on_delete=models.CASCADE, related_name='result')
    disease_name    = models.CharField(max_length=200)
    confidence_score= models.FloatField()   # 0.0 to 1.0
    is_healthy      = models.BooleanField()
    processed_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.disease_name} ({self.confidence_score:.0%})"