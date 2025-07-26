from django.shortcuts import render

# Create your views here.
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import LoginTokenSerializer

class LoginTokenView(TokenObtainPairView):
    serializer_class = LoginTokenSerializer