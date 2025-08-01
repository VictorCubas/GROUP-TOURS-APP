from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(request):
    mensaje = request.GET.get('mensaje', '')
    return render(request, 'index.html', {'mensaje': mensaje})
