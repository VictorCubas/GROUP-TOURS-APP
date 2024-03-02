from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(request):
    mensaje = request.GET.get('mensaje', '')
    # print(request.path)
    return render(request, 'index.html', {'mensaje': mensaje})


# def iniciarSesion(request):
#     return render(request, 'home.html')