from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def logout(request):
    # print(request.path)
    return render(request, 'index.html')


# def iniciarSesion(request):
#     return render(request, 'home.html')