import uuid
from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ('diagnosis_done',  'Diagnosis Done'),
        ('disease_alert',   'Disease Alert'),
        ('weather_alert',   'Weather Alert'),
        ('system',          'System'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id    = models.UUIDField(db_index=True)
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type}] {self.title} → {self.user_id}"


class NotificationLog(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type   = models.CharField(max_length=50)
    payload      = models.JSONField()
    processed_at = models.DateTimeField(auto_now_add=True)
    success      = models.BooleanField(default=True)
    error        = models.TextField(blank=True)

    class Meta:
        ordering = ['-processed_at']

    def __str__(self):
        return f"{self.event_type} — {'ok' if self.success else 'FAILED'}"