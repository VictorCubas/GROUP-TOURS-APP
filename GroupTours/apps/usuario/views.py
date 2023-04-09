from django.shortcuts import render
from rest_framework import generics, viewsets
from .models import Usuario
from .serializers import UsuarioSerializer

class UsuarioList(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    
    
    # def index(request):
    #     return render(request, "usuarios.html")