from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

class LoginTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
            data['debe_cambiar_contrasenia'] = self.user.debe_cambiar_contrasenia  # <--- Nuevo campo en respuesta
            return data
        except AuthenticationFailed:
            raise AuthenticationFailed({'message': 'Credenciales incorrectas'})