from django.urls import path
from .views import FieldListCreateView, FieldDetailView, AdminFieldListView
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('health/', health, name='health'),
    path('fields/',           FieldListCreateView.as_view(), name='field-list-create'),
    path('fields/<uuid:pk>/', FieldDetailView.as_view(),     name='field-detail'),
    path('admin/fields/',     AdminFieldListView.as_view(),  name='admin-field-list'),
]