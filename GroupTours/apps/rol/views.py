from django.shortcuts import render
from django.http import HttpResponse

from apps.permiso.models import Permiso
from .models import Rol
from .models import RolesPermisos
# Create your views here.

def index(request):
    # print(request.path)
    listaRoles = Rol.objects.all().order_by('id')
    listaPermisos = Permiso.objects.all().order_by('id')
    
    listaRolesPermisos = []
    
    rolesPermisosDic = []
    
    for rol in listaRoles:
        listaPermisosAsignados = []
        listaAux = {}
        
        listaAux['rol'] = rol
        rolPermiso = RolesPermisos.objects.filter(rol_id=rol.id)
        print(f'rolPermiso: {rolPermiso}')
        
        for rp in rolPermiso:
            # permiso = Permiso.objects.get(id=int(rp.permiso_id))
            listaPermisosAsignados.append(rp.permiso)
            
        
        listaAux['permisos'] = listaPermisosAsignados
        rolesPermisosDic.append(listaAux)
    
    # print(f'listaAux: {listaAux}')
    # print(f'rolesPermisosDic: {rolesPermisosDic}')
    for p in rolesPermisosDic:
        print(f'nombre: {p}')
    
    return render(request, 'rol.html', {'listaRoles':listaRoles,
                                        'listaPermisos':listaPermisos,
                                        'listaRolesPermisos':listaRolesPermisos,
                                        'rolesPermisosDic': rolesPermisosDic})


def agregar(request):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre')
    descripcion = request.POST.get('txtDescripcion')
    permiso_ids = request.POST.getlist('txtPermisos')
    
    print(f'{nombre}, {descripcion}, {permiso_ids}')
    rol = Rol.objects.create(nombre=nombre, descripcion=descripcion)
   
    permisoList = []
    for p in permiso_ids:
        permiso = Permiso.objects.get(id=int(p))
        permisoList.append(permiso)
        rolPermiso = RolesPermisos.objects.create(rol=rol, permiso=permiso)
    
    # print(f'permiso devuelto: {permiso}')
    
    #se crea un rol
    # Rol.objects.create(nombre=nombre, descripcion=descripcion, formulario=formulario)

    #se recupera toda la lista de permiso
    listaRoles = Rol.objects.all().order_by('id')
    listaPermisos = Permiso.objects.all().order_by('id')
    return render(request, 'rol.html', {'listaRoles':listaRoles,
                                        'listaPermisos':listaPermisos})

'''
def eliminar(request, id):
    try:
        permiso = Permiso.objects.get(id=id)
        permiso.delete()
    except:
        pass

    listaPermiso = Permiso.objects.all().order_by('id')

    return render(request, 'permiso.html', {'listaPermisos':listaPermiso})
'''