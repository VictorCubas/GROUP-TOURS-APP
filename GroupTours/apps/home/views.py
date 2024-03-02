from django.shortcuts import redirect, render
from django.http import HttpResponse

# Create your views here.

def home(request):
    email = request.POST.get('email')
    password = request.POST.get('password')

    if email == 'admin@gmail.com':
        return render(request, 'home.html')
    else:
        mensaje = 'Verifique las credenciales'
        return redirect(f'/?mensaje={mensaje}', name='index-login')