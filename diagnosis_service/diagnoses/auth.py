import uuid
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class FarmerFromJWT:
    def __init__(self, payload):
        self.id = uuid.UUID(payload['user_id'])
        self.role = payload.get('role', 'farmer')
        self.is_authenticated = True

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return None  # No token provided, let other authenticators handle it
        token = header.split(' ')[1] # Extract the token part
        try:
            validated = UntypedToken(token) # This will validate the token and raise if invalid
            return (FarmerFromJWT(validated.payload), token) # Return the user and token for the request
        except (InvalidToken, TokenError) as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")
    
    