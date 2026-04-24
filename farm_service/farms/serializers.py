from rest_framework import serializers
from .models import Field

class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = '__all__'
        read_only_fields = ['id', 'owner_id', 'status', 'created_at', 'updated_at']

    def validate_area_ha(self, value):
        if value <= 0:
            raise serializers.ValidationError("Area must be greater than 0.")
        return value

    def validate_color(self, value):
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be a hex value like #4CAF50.")
        return value