from django.shortcuts import render
from django.http import HttpResponse
from .models import Usuario
# Create your views here.

def index(request):
    # print(request.path)
    listaUsuario = Usuario.objects.all().order_by('id')
    
    context = {'listaUsuarios':listaUsuario, 'menu_activo': 'usuario'}
    
    
    return render(request, 'usuario.html', context)


def registrarUsuario(request):
    #se recupera los datos del formulario
    documento = request.POST.get('txtDocumento')
    nombre = request.POST.get('txtNombre')
    apellido = request.POST.get('txtApellido')
    telefono = request.POST.get('txtTelefono')
    correo = request.POST.get('txtCorreo')
    direccion = request.POST.get('txtDireccion')
    estado = request.POST.get('txtEstado')
   
    #se crea un usuario
    Usuario.objects.create(documento = documento,
                           nombre = nombre,
                           apellido = apellido,
                           telefono = telefono,
                           correo = correo,
                           direccion = direccion,
                           estado = estado)

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