import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Notification, NotificationLog
from .serializers import NotificationSerializer, NotificationLogSerializer
from .auth import JWTAuthentication

logger = logging.getLogger(__name__)


class NotificationListView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """Return all notifications for the authenticated user."""
        notifs = Notification.objects.filter(user_id=request.user.id)
        return Response(NotificationSerializer(notifs, many=True).data)


class MarkReadView(APIView):
    """Mark a single notification as read."""
    authentication_classes = [JWTAuthentication]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user_id=request.user.id)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return Response({'detail': 'Marked as read.'})


class MarkAllReadView(APIView):
    """Mark all of the user's notifications as read."""
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        updated = Notification.objects.filter(
            user_id=request.user.id, is_read=False
        ).update(is_read=True)
        return Response({'detail': f'{updated} notifications marked as read.'})


class NotificationLogListView(APIView):
    """Admin only — view the raw RabbitMQ event log."""
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Admin only.'}, status=status.HTTP_403_FORBIDDEN)
        logs = NotificationLog.objects.all()[:100]
        return Response(NotificationLogSerializer(logs, many=True).data)


class HealthView(APIView):
    def get(self, request):
        return Response({'status': 'ok'})