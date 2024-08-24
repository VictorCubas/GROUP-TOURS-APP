from django.shortcuts import render
from django.http import HttpResponse
from .models import Usuario
from apps.rol.models import Rol
from .models import UsuariosRoles
# Create your views here.

def index(request):
    # print(request.path)
    listaUsuarios = Usuario.objects.all().order_by('id')
    listaRoles = Rol.objects.all().order_by('id')
    listaUsuarioRoles = getUsuariosRoles(listaUsuarios)
    
    context = {
        'listaUsuarios':listaUsuarios,
        'listaRoles': listaRoles,
        'menu_activo': 'usuario'}
    
    
    return render(request, 'usuario.html', context)


def getUsuariosRoles(listaUsuarios):
    listaUsuariosRoles = []
    
    for usuario in listaUsuarios:
        listaRolesAsignados = []
        listaAux = {}
        
        listaAux['rol'] = usuario
        rolPermiso = UsuariosRoles.objects.filter(rol_id=usuario.id)
        
        for rp in rolPermiso:
            # permiso = Permiso.objects.get(id=int(rp.permiso_id))
            listaRolesAsignados.append(rp.permiso)
            
        
        listaAux['permisos'] = listaRolesAsignados
        listaUsuariosRoles.append(listaAux)
        
    return listaUsuariosRoles


def registrarUsuario(request):
    #se recupera los datos del formulario
    documento = request.POST.get('txtDocumento')
    nombre = request.POST.get('txtNombre')
    apellido = request.POST.get('txtApellido')
    telefono = request.POST.get('txtTelefono')
    correo = request.POST.get('txtCorreo')
    direccion = request.POST.get('txtDireccion')
   
    #se crea un usuario
    Usuario.objects.create(documento = documento,
                           nombre = nombre,
                           apellido = apellido,
                           telefono = telefono,
                           correo = correo,
                           direccion = direccion,)

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