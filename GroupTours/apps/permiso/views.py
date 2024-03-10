from django.shortcuts import render
from django.http import HttpResponse
from .models import Permiso
# Create your views here.

def index(request):
    # print(request.path)
    return render(request, 'permiso.html')


def registrarPermiso(request):
    nombre = request.POST.get('txtNombre')
    descripcion = request.POST.get('txtDescripcion')
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')
   
    Permiso.objects.create(nombre=nombre, descripcion=descripcion, tipo=tipo, formulario=formulario)

    listaPermiso = Permiso.objects.all().order_by('id')

    return render(request, 'permiso.html',{'listaPermisos':listaPermiso} )