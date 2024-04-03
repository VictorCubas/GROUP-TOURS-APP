from django.shortcuts import redirect, render
from django.http import HttpResponse

from apps.permiso.models import Permiso
from .models import Rol
from .models import RolesPermisos
from django.core.paginator import Paginator, Page
from django.db.models import Q, Func, F
from unicodedata import normalize
# Create your views here.

def index(request):
    listaRoles = Rol.objects.all().order_by('-id')
    listaPermisos = Permiso.objects.all().order_by('id')
    listaRolesPermisos = getRolesPermisos(listaRoles)
    
    operaciones = ['add-success', 'add-error', 'add-warning', 'delete-success', 'delete-error', 'edit-success', 'edit-error']
    
    #se verifica cual de las operaciones se ejecuta para mostrar los mensajes de exitos y/o errores
    query_value = None
    query = None
    for operacion in operaciones:
        query = operacion
        query_value = request.GET.get(operacion, '')
        # print(f'query: {query}, query_value: {query_value}')
        
        if query_value.lower() == 'true':
            query_value = True
            break
        elif query_value.lower() == 'false':
            query_value = False
            break
    
    
    resultadosAPaginar = listaRolesPermisos
    cantidad_de_resultados = len(resultadosAPaginar)
    paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
    page_number = request.GET.get('page')  # Obtén el número de página de la URL
    page: Page = paginator.get_page(page_number)
    
    context = {
                'listaPermisos':listaPermisos,
                'cantidad_de_resultados': cantidad_de_resultados,
                'page': page,
                }
    
    mensaje = ''
    tipo = ''
    if query == 'delete-success' and query_value:
        context['eliminacionExitosa'] = query_value
        
    elif query == 'add-success':
        if query_value:
            mensaje = 'El rol se ha guardado con exito'
            tipo = 'success'
        else:    
            mensaje = 'Rol ya existente'
            tipo = 'warning'
            
        context['tipo'] = tipo
    elif query == 'edit-success':
        mensaje = 'El rol se ha editado con exito'
        context['tipo'] = 'success'
    
    context['mensaje'] = mensaje

    print(f'context: {context}')
    
    return render(request, 'rol.html', context)


def agregar(request):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre')
    descripcion = request.POST.get('txtDescripcion')
    permiso_ids = request.POST.getlist('txtPermisos')
    
    esValido = validarRepetido(nombre)
    
    if esValido:
        print('ES VALIDO!')
        # print(f'{nombre}, {descripcion}, {permiso_ids}')
        rol = Rol.objects.create(nombre=nombre, descripcion=descripcion)
        
        for p in permiso_ids:
            permiso = Permiso.objects.get(id=int(p))
            rolPermiso = RolesPermisos.objects.create(rol=rol, permiso=permiso)
    else:
        print('ES INVALIDO!')
        
    return redirect(f'/rol?add-success={esValido}', name='index-roles')    


def validarRepetido(nombre):
    '''
    Este metodo valida que si hay algun rol con el mismo nombre
    Se puede hacer de manera mas simple, solo reutilice lo que ya tenia
    '''
    
    # print('validar repetido')
    query_normalized = normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
        
    resultados_roles = Rol.objects.annotate(
        nombre_normalized=Func(F('nombre'), function='unaccent'),
    ).filter(
        Q(nombre_normalized=query_normalized)
    )
    
    # print(f'resultados_roles: {resultados_roles}')
    # print(f'len resultados_roles: {len(resultados_roles)}')
    
    if len(resultados_roles) == 0:
        return True

    return False

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
    
    return redirect(f'/rol?delete-success=true', name='index-roles')
    

def edicion(request, id):
    rol = None
    listaPermisos = []
    rolesPermisos = []
    permisosDelRol = []
    
    try:
        rol = Rol.objects.get(id=id)
        
        #recupera todos los permisos
        listaPermisos = Permiso.objects.all().order_by('id')
        
        #recupera solo los permisos del rol
        rolesPermisos = RolesPermisos.objects.filter(rol_id=rol.id)
        
        #se busca en la lista de permisos, los permisos que corresponde al rol para listar en el html
        for p in listaPermisos:
            selected = 'no'
            for rp in rolesPermisos:
                if rp.permiso.id == p.id:
                    selected = 'si'
                    break
            
            permisosDelRol.append({'permiso': p, 'selected': selected})
        
    except:
        pass

    
    return render(request, 'edicionRol.html', {
                                        'rol':rol,
                                        'listaPermisos':listaPermisos,
                                        'permisosDelRol':permisosDelRol})
    
    
    
def editar(request, id):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre')
    descripcion = request.POST.get('txtDescripcion')
    permiso_ids = request.POST.getlist('txtPermisos')
    
    rol = Rol.objects.get(id=int(id))
    rol.nombre = nombre
    rol.descripcion = descripcion
    rol.save()
   
    #recupero los permisos seleccionados despues de la edicion
    listaPermisosSeleccionados = []
    for p in permiso_ids:
        permiso = Permiso.objects.get(id=int(p))
        listaPermisosSeleccionados.append(permiso)
        
        
    #recupera solo los permisos del rol
    rolesPermisos = RolesPermisos.objects.filter(rol_id=rol.id)
    
    #se busca en la lista de permisos, los permisos que corresponde al rol para listar en el html
    for rp in rolesPermisos:
        rp.delete()
    
    for permiso in listaPermisosSeleccionados:
        rolPermiso = RolesPermisos.objects.create(rol=rol, permiso=permiso)
    
    # return redirect(f'/rol', name='index-roles')    
    return redirect(f'/rol?edit-success=true', name='index-roles')


def buscar(request):
    query = request.GET.get('q')  # Obtener el término de búsqueda del parámetro 'q'
    resultados_roles = []
    context = {}
    
    if query:
        query_normalized = normalize('NFKD', query).encode('ASCII', 'ignore').decode('ASCII')
        
        print('1')
        resultados_roles = Rol.objects.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized__icontains=query_normalized)
        )
        
        print('2')
        for res in resultados_roles:
            print(f'nombre: {res.nombre}')
            
        listaPermisos = Permiso.objects.all().order_by('id')
        listaRolesPermisos = getRolesPermisos(resultados_roles)
        resultadosAPaginar = listaRolesPermisos
        cantidad_de_resultados = len(resultadosAPaginar)
        paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
        page_number = request.GET.get('page')  # Obtén el número de página de la URL
        page: Page = paginator.get_page(page_number)
        
        context = {
                    'listaPermisos':listaPermisos,
                    'cantidad_de_resultados': cantidad_de_resultados,
                    'page': page,
                    'query': query
                    }
        
    return render(request, 'rol.html', context)


def getRolesPermisos(listaRoles):
    listaRolesPermisos = []
    
    for rol in listaRoles:
        listaPermisosAsignados = []
        listaAux = {}
        
        listaAux['rol'] = rol
        rolPermiso = RolesPermisos.objects.filter(rol_id=rol.id)
        
        for rp in rolPermiso:
            # permiso = Permiso.objects.get(id=int(rp.permiso_id))
            listaPermisosAsignados.append(rp.permiso)
            
        
        listaAux['permisos'] = listaPermisosAsignados
        listaRolesPermisos.append(listaAux)
        
    return listaRolesPermisos
