from rest_framework import serializers
from .models import Notification, NotificationLog


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['id', 'user_id', 'type', 'title', 'message', 'is_read', 'created_at']
        read_only_fields = fields


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationLog
        fields = ['id', 'event_type', 'payload', 'processed_at', 'success', 'error']
        read_only_fields = fields