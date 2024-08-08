from django.shortcuts import render

# Create your views here.
def empleados(request):
    return render(request, 'empleados.html')