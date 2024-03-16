from django.shortcuts import render
from django.http import HttpResponse

from apps.permiso.models import Permiso
from .models import Rol
from .models import RolesPermisos
# Create your views here.

def index(request):
    listaRoles = Rol.objects.all().order_by('id')
    listaPermisos = Permiso.objects.all().order_by('id')
    
    listaRolesPermisos = getRolesPermisos(listaRoles)
    
    return render(request, 'rol.html', {'listaRoles':listaRoles,
                                        'listaPermisos':listaPermisos,
                                        'listaRolesPermisos':listaRolesPermisos,})


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
    
    listaRoles = Rol.objects.all().order_by('id')
    listaPermisos = Permiso.objects.all().order_by('id')
    listaRolesPermisos = getRolesPermisos(listaRoles)
    
    return render(request, 'rol.html', {'listaRoles':listaRoles,
                                        'listaPermisos':listaPermisos,
                                        'listaRolesPermisos':listaRolesPermisos,})


def eliminar(request, id):
    eliminacionExitosa = False
    try:
        rolesPermisos = RolesPermisos.objects.filter(rol_id=id)
        
        for r in rolesPermisos:
            r.delete()
            
        rol = Rol.objects.get(id=id)
        rol.delete()
        
        eliminacionExitosa = True
    except:
        pass

    listaRoles = Rol.objects.all().order_by('id')
    listaPermisos = Permiso.objects.all().order_by('id')
    listaRolesPermisos = getRolesPermisos(listaRoles)
    
    return render(request, 'rol.html', {'listaRoles':listaRoles,
                                        'listaPermisos':listaPermisos,
                                        'listaRolesPermisos':listaRolesPermisos,
                                        'eliminacionExitosa': eliminacionExitosa})


def getRolesPermisos(listaRoles):
    listaRolesPermisos = []
    
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
        listaRolesPermisos.append(listaAux)
        
    return listaRolesPermisos