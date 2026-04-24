from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, MeView, ChangePasswordView, LogoutView,
    AdminUserListView, AdminUserDetailView,
)
from .tokens import AgriGuardTokenView
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [

    path('health/', health, name='health'),
    # public
    path('register/',          RegisterView.as_view(),      name='register'),
    path('login/',             AgriGuardTokenView.as_view(), name='login'),
    path('token/refresh/',     TokenRefreshView.as_view(),   name='token-refresh'),

    # authenticated farmer
    path('me/',                MeView.as_view(),             name='me'),
    path('me/password/',       ChangePasswordView.as_view(), name='change-password'),
    path('logout/',            LogoutView.as_view(),         name='logout'),

    # admin
    path('admin/users/',          AdminUserListView.as_view(),         name='admin-user-list'),
    path('admin/users/<uuid:pk>/', AdminUserDetailView.as_view(),      name='admin-user-detail'),
]