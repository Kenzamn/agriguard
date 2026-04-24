from django.urls import path
from django.http import JsonResponse
from . import views

def health_check(request):
    # This keeps Consul happy!
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('health/', health_check),
    path('',               views.login_view,       name='login'),
    path('register/',      views.register_view,    name='register'),
    path('dashboard/',     views.dashboard_view,   name='dashboard'),
    path('fields/',        views.fields_view,      name='fields'),
    path('diagnosis/',     views.diagnosis_view,   name='diagnosis'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('weather/',       views.weather_view,     name='weather'),
    path('admin-panel/',   views.admin_view,       name='admin'),
    path('history/', views.history_view, name='history'),
]