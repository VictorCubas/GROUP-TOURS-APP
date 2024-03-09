from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(request):
    # print(request.path)
    return render(request, 'permiso.html')


# def iniciarSesion(request):
#     return render(request, 'home.html')