from django.db import models

# Create your models here.
import uuid
from django.db import models

class Field(models.Model):
    SOIL_CHOICES = [
        ('clay', 'Clay'), ('sandy', 'Sandy'), ('loamy', 'Loamy'),
        ('silty', 'Silty'), ('peaty', 'Peaty'), ('chalky', 'Chalky'),
    ]
    IRRIGATION_CHOICES = [
        ('drip', 'Drip'), ('sprinkler', 'Sprinkler'),
        ('flood', 'Flood'), ('manual', 'Manual'),
    ]
    STATUS_CHOICES = [
        ('healthy', 'Healthy'), ('warning', 'Warning'), ('disease', 'Disease'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id         = models.UUIDField()                          # soft FK → Auth Service user
    name             = models.CharField(max_length=200)
    crop_type        = models.CharField(max_length=100)
    area_ha          = models.DecimalField(max_digits=8, decimal_places=2)
    planted_date     = models.DateField()
    soil_type        = models.CharField(max_length=20, choices=SOIL_CHOICES, blank=True)
    irrigation_method= models.CharField(max_length=20, choices=IRRIGATION_CHOICES, blank=True)
    notes            = models.TextField(blank=True)
    color            = models.CharField(max_length=7, blank=True)  # hex e.g. #4CAF50
    wilaya           = models.CharField(max_length=50, blank=True)
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default='healthy')
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.crop_type} ({self.status})"