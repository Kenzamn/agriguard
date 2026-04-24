from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class AgriGuardTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # these claims are decoded by Farm, Diagnosis, Notification services
        token['user_id']    = str(user.id)
        token['role']       = user.role
        token['first_name'] = user.first_name
        token['last_name']  = user.last_name
        token['wilaya']     = user.wilaya
        return token


class AgriGuardTokenView(TokenObtainPairView):
    serializer_class = AgriGuardTokenSerializer