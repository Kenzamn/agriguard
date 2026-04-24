from django.urls import path, include

urlpatterns = [
    path('api/notify/', include('notifications.urls')),
]