from django.shortcuts import render
from django.http import HttpResponse
from .models import Permiso
# Create your views here.

def index(request):
    # print(request.path)
    listaPermiso = Permiso.objects.all().order_by('id')
    return render(request, 'permiso.html', {'listaPermisos':listaPermiso})


def registrarPermiso(request):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre')
    descripcion = request.POST.get('txtDescripcion')
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')
   
    #se crea un permiso
    Permiso.objects.create(nombre=nombre, descripcion=descripcion, tipo=tipo, formulario=formulario)

    #se recupera toda la lista de permiso
    listaPermiso = Permiso.objects.all().order_by('id')

    return render(request, 'permiso.html',{'listaPermisos':listaPermiso} )