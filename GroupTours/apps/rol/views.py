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
    
    operaciones = ['add-success', 'add-error', 'add-warning', 'delete-success', 'delete-error', 'edit-success', 'edit-error', 'edit-warning']
    
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
        else:
            query = ''
    
    
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
    
    print(f'query: {query}')
    if query == 'delete-success' and query_value:
        context['eliminacionExitosa'] = query_value
        
    elif query == 'add-success':
        if query_value:
            mensaje = 'El rol se ha guardado con exito'
            tipo = 'success'
        else:    
            mensaje = 'Rol ya existente. Verifique que el nombre no sea repetido'
            tipo = 'warning'
            
        context['tipo'] = tipo
        
    elif query == 'edit-success':
        mensaje = 'El rol se ha editado con exito'
        context['tipo'] = 'success'
    
    elif query == 'edit-warning':
        mensaje = 'Rol ya existente. Verifique que el nombre no sea repetido'
        context['tipo'] = 'warning'
        
    elif query == 'add-error' or query == 'edit-error' or query == 'delete-error':
        mensaje = 'Error: Ocurrio algo inesperado. Vuelva a intentarlo'
        context['tipo'] = 'danger'
    
    
    context['mensaje'] = mensaje

    print(f'context: {context}')
    
    return render(request, 'rol.html', context)


def agregar(request):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre').strip()
    descripcion = request.POST.get('txtDescripcion').strip()
    permiso_ids = request.POST.getlist('txtPermisos')
    
    esValido = validarRepetido(nombre, None)
    
    parametro = 'success'
    
    if esValido:
        print('ES VALIDO!')
        # print(f'{nombre}, {descripcion}, {permiso_ids}')
        try:
            rol = Rol.objects.create(nombre=nombre, descripcion=descripcion)
        
            for p in permiso_ids:
                permiso = Permiso.objects.get(id=int(p))
                print('me creo......')
                rolPermiso = RolesPermisos.objects.create(rol=rol, permiso=permiso)
        except:
            parametro = 'error'
            pass
        
    return redirect(f'/rol?add-{parametro}={esValido}', name='index-roles')    


def validarRepetido(nombre, rol):
    '''
    Este metodo valida que si hay algun rol con el mismo nombre
    Se puede hacer de manera mas simple, solo reutilice lo que ya tenia
    '''
    
    # print('validar repetido')
    query_normalized = normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
    
    resultados_roles = None
    
    if rol:
        #significa que un rol se esta editando y no agregando uno nuevo
        # rolesPermisos = RolesPermisos.objects.filter(permiso_id=permiso.id)
        # if len(rolesPermisos) != 0:
        #     #es invalido, existe roles usando este permiso. No se puede editar
        #     return False
        
        resultados_roles = Rol.objects.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized=query_normalized)
        ).exclude(
            id=rol.id  # Excluyendo el rol actual basado en su id
        )
    else:
        resultados_roles = Rol.objects.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized=query_normalized)
        )
    
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
        eliminacionExitosa = False
        pass
    
    return redirect(f'/rol?delete-success={eliminacionExitosa}', name='index-roles')
    

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
    nombre = request.POST.get('txtNombre').strip()
    descripcion = request.POST.get('txtDescripcion').strip()
    permiso_ids = request.POST.getlist('txtPermisos')
    
    rol = Rol.objects.get(id=int(id))
   
    esValido = validarRepetido(nombre, rol)
    print(f'esValido: {esValido}')
    print(f'esValido: {type(esValido)}')
    
    parametro = 'success'
    
    if esValido:
        print('entro aca????')
        
        rol.nombre = nombre
        rol.descripcion = descripcion
        rol.save()
        try:
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
        except:
            parametro = 'error'
    else:
        print(f'error: invalido')
        parametro = 'warning'
    
    # return redirect(f'/rol', name='index-roles')    
    return redirect(f'/rol?edit-{parametro}=true', name='index-roles')


def buscar(request):
    query = request.GET.get('q').strip()  # Obtener el término de búsqueda del parámetro 'q'
    resultados_roles = []
    context = {}
    
    if query:
        query_normalized = normalize('NFKD', query).encode('ASCII', 'ignore').decode('ASCII')
        
        resultados_roles = Rol.objects.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized__icontains=query_normalized)
        )
        
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
