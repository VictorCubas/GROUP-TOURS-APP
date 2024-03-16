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

def edicionPermiso(request, codigo):
    permiso = Permiso.objects.get(id=int(codigo))
    return render(request, "edicionPermiso.html", {"permiso": permiso })

def editarPermiso(request, id):
    nombre = request.POST.get('txtNombre')
    descripcion = request.POST.get('txtDescripcion')
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')

    try:
        permiso = Permiso.objects.get(id=id)
        permiso.nombre = nombre
        permiso.descripcion = descripcion
        permiso.tipo = tipo
        permiso.formulario = formulario
        permiso.save()

    except:
        pass
    
    listaPermiso = Permiso.objects.all().order_by('id')
    return render(request, 'permiso.html',{'listaPermisos':listaPermiso} )

def eliminar(request, id):
    try:
        permiso = Permiso.objects.get(id=id)
        permiso.delete()
    except:
        pass

    listaPermiso = Permiso.objects.all().order_by('id')

    return render(request, 'permiso.html', {'listaPermisos':listaPermiso})