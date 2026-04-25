from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, MeView, ChangePasswordView, LogoutView,
    AdminUserListView, AdminUserDetailView,
    InternalFarmersByWilayaView,
)
from .tokens import AgriGuardTokenView
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path('health/', health, name='health'),

    # Public
    path('register/',      RegisterView.as_view(),       name='register'),
    path('login/',         AgriGuardTokenView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(),   name='token-refresh'),

    # Authenticated farmer
    path('me/',            MeView.as_view(),             name='me'),
    path('me/password/',   ChangePasswordView.as_view(), name='change-password'),
    path('logout/',        LogoutView.as_view(),         name='logout'),

    # Admin
    path('admin/users/',           AdminUserListView.as_view(),   name='admin-user-list'),
    path('admin/users/<uuid:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),

    # Internal — used by weather-scheduler only, NOT exposed via Traefik
    # (Traefik only routes /api/auth/* through consul, and this path is
    #  called container-to-container: agriguard-auth:8001/api/auth/internal/...)
    path('internal/farmers-by-wilaya/', InternalFarmersByWilayaView.as_view(),
         name='internal-farmers-by-wilaya'),
]