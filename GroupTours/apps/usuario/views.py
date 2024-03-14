from django.shortcuts import render
from django.http import HttpResponse
from .models import Usuario
# Create your views here.

def index(request):
    # print(request.path)
    listaUsuario = Usuario.objects.all().order_by('id')
    return render(request, 'usuario.html', {'listaUsuarios':listaUsuario})


def registrarUsuario(request):
    #se recupera los datos del formulario
    documento = request.POST.get('txtDocumento')
    nombre = request.POST.get('txtNombre')
    telefono = request.POST.get('txtTelefono')
    correo = request.POST.get('txtCorreo')
    direccion = request.POST.get('txtDireccion')
    estado = request.POST.get('txtEstado')
    formulario = request.POST.get('txtFormulario')
   
    #se crea un usuario
    Usuario.objects.create(documento = documento,
                           nombre = nombre,
                           telefono = telefono,
                           correo = correo,
                           direccion = direccion,
                           estado = estado,
                           formulario = formulario)

    #se recupera toda la lista de usuarios
    listaUsuario = Usuario.objects.all().order_by('id')

    return render(request, 'usuario.html', {'listaUsuarios':listaUsuario} )

def eliminar(request, id):
    try:
        usuario = Usuario.objects.get(id=id)
        usuario.delete()
    except:
        pass

    listaUsuario = Usuario.objects.all().order_by('id')

    return render(request, 'usuario.html', {'listaUsuarios':listaUsuario})