from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
import uuid

class FarmerFromJWT:
    """Minimal user-like object built from JWT claims — no DB hit."""
    def __init__(self, payload):
        self.id        = uuid.UUID(payload['user_id'])
        self.role      = payload.get('role', 'farmer')
        self.is_authenticated = True


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return None
        token = header.split(' ')[1]
        try:
            validated = UntypedToken(token)
            return (FarmerFromJWT(validated.payload), token)
        except (InvalidToken, TokenError) as e:
            raise AuthenticationFailed(str(e))


class IsFarmer:
    """Simple permission check — use in views."""
    @staticmethod
    def check(request):
        return request.user.role == 'farmer'