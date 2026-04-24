from django.urls import path
from .views import (
    NotificationListView, MarkReadView,
    MarkAllReadView, NotificationLogListView, HealthView,
)

urlpatterns = [
    path('health/',                          HealthView.as_view(),             name='health'),
    path('notifications/',                   NotificationListView.as_view(),   name='notif-list'),
    path('notifications/<uuid:pk>/read/',    MarkReadView.as_view(),           name='notif-read'),
    path('notifications/read-all/',          MarkAllReadView.as_view(),        name='notif-read-all'),
    path('admin/logs/',                      NotificationLogListView.as_view(),name='notif-logs'),
]