from rest_framework import serializers
from .models import Diagnosis, DiagnosisResult


class DiagnosisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisResult
        fields = ['id', 'disease_name', 'confidence_score', 'is_healthy', 'processed_at']

class DiagnosisSerializer(serializers.ModelSerializer):
    result = DiagnosisResultSerializer(read_only=True)  # nested, shown when completed

    class Meta:
        model = Diagnosis
        fields = ['id', 'field_id', 'farmer_id', 'image_path', 'status', 'created_at', 'updated_at', 'result']
        read_only_fields = ['id', 'farmer_id', 'image_path', 'status', 'created_at', 'updated_at', 'result']

class DiagnosisCreateSerializer(serializers.Serializer):
    '''used only for the upload endpoint, handles the image path and field_id'''
    field_id = serializers.UUIDField()
    image = serializers.ImageField()

    def validate_image(self, value):
        max_size = 10 * 1024 * 1024 # 10 MB
        if value.size > max_size:
            raise serializers.ValidationError("Image size must be less than 10 MB.")
        allowed = ['image/jpeg', 'image/png', 'image/webp']
        if value.content_type not in allowed:
            raise serializers.ValidationError("Unsupported image type. Allowed types: JPEG, PNG, WEBP.")
        return value