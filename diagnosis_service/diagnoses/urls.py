from django.urls import path
from .views import DiagnosisListCreateView, DiagnosisDetailView, AdminDiagnosisListView
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('health/', health, name='health'),
    path('diagnoses/',             DiagnosisListCreateView.as_view(), name='diagnosis-list-create'),
    path('diagnoses/<uuid:pk>/',   DiagnosisDetailView.as_view(),     name='diagnosis-detail'),
    path('admin/diagnoses/',       AdminDiagnosisListView.as_view(),  name='admin-diagnosis-list'),
]