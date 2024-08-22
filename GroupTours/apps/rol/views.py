from django.shortcuts import redirect, render
from django.http import HttpResponse

from apps.usuario.models import UsuariosRoles
from apps.permiso.models import Permiso
from .models import Rol
from .models import RolesPermisos
from django.core.paginator import Paginator, Page
from django.db.models import Q, Func, F
from unicodedata import normalize
# Create your views here.

editado = False
agregado = False
eliminado = False
elimninacion_no_permitida = False
nombre_repetido = False
operacion = None
activo = True
activado = False

def index(request):
    listaRoles = None
    global editado, operacion, agregado, eliminado, activado 
    
    if operacion == "activar": 
        listaRoles = Rol.objects.filter(activo=False).order_by('-id')

    else: 
        listaRoles = Rol.objects.filter(activo=True).order_by('-id')
    
    listaPermisos = Permiso.objects.all().order_by('id')
    listaRolesPermisos = getRolesPermisos(listaRoles)
    
    
    resultadosAPaginar = listaRolesPermisos
    cantidad_de_resultados = len(resultadosAPaginar)
    paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
    page_number = request.GET.get('page')  # Obtén el número de página de la URL
    page: Page = paginator.get_page(page_number)
    
    context = {
                'listaPermisos':listaPermisos,
                'cantidad_de_resultados': cantidad_de_resultados,
                'page': page,
                'menu_activo': 'rol'
                }
    
    mensaje = ''
    tipo = ''
    
    if operacion == 'editar':
        context['editado'] = True
        context['operacion'] = operacion
        print(f'context: {context}')
        tipo = 'success'
        editado = False
        mensaje = 'El rol se ha editado con exito'
        
    elif operacion == 'agregar':
        context['operacion'] = operacion
        
        if agregado:
            context['agregado'] = True
            tipo = 'success'
            mensaje = 'El rol se ha guardado con exito'
            
            agregado = False
        else:
            context['agregado'] = False
            mensaje = 'Rol ya existente'
            tipo = 'warning'
    elif operacion == 'eliminar':
        context['operacion'] = operacion
        print(f'eliminado 2: {eliminado}')
        
        context['eliminacionExitosa'] = eliminado
        
        if eliminado:
            context['eliminado'] = True
            tipo = 'success'
            
        else:
            context['eliminado'] = False
            tipo = 'warning'
            
            if elimninacion_no_permitida:
                context['eliminacionExitosa'] = 'warning'
            
        eliminado = False
        
        
        print(f"eliminacionExitosa: {context['eliminacionExitosa']}")

    elif operacion == 'activar':
        context['operacion'] = operacion
    
        print(f'activado: {activado}')
        context['activacionExitosa'] = activado
        
        if activado:
            context['activado'] = True
            tipo = 'success'
            
        else:
            context['activado'] = False
            tipo = 'warning'
            
        activado = False
            
    context['tipo'] = tipo
    operacion = None
    context['mensaje'] = mensaje
    context['activo'] = activo
    
    
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
                permiso.en_uso = True
                permiso.save()
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
    global eliminado, operacion, elimninacion_no_permitida, activo
    eliminado = False
    elimninacion_no_permitida = False
    operacion = 'eliminar'
    activo = True
    
    try:
        rol = Rol.objects.get(id=id)
        
        rolEstaEnUso = rolEnUso(id)
        
        if not rolEstaEnUso:
            rol.activo = False
            rol.save()
            eliminado = True
        else:
            elimninacion_no_permitida = True
    except:
        pass
    
    return redirect(f'/rol', name='index-roles')


def rolEnUso(id):
    usuariosRoles = UsuariosRoles.objects.filter(rol_id = id) 
    
    #significa que el permiso esta siendo usado por otro rol
    return len(usuariosRoles) > 0
    

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
        selected = 'no'
        for p in listaPermisos:
            selected = 'no'
            for rp in rolesPermisos:
                if rp.permiso.id == p.id:
                    selected = 'si'
                    break
            
            permisosDelRol.append({'permiso': p, 'selected': selected})
        
        print(f'permisosDelRol: {permisosDelRol}')
        
        #DESCOMENTAR ESTE CODIGO PARA HABILITAR EDICION 
        # usuarioRoles = UsuarioRoles.objects.filter(rol_id = rol.id)
    
        habilitarEdicion = not rol.en_uso
        # if len(usuarioRoles) > 0:
        #     habilitarEdicion = False
    except:
        pass

    
    return render(request, 'edicionRol.html', {
                                        'rol':rol,
                                        'listaPermisos':listaPermisos,
                                        'permisosDelRol':permisosDelRol,
                                        'menu_activo': 'rol',
                                        "habilitarEdicion": habilitarEdicion})
    
    
    
def editar(request, id):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre').strip()
    descripcion = request.POST.get('txtDescripcion').strip()
    permiso_ids = request.POST.getlist('txtPermisos')

    global editado, operacion
    editado = False
    operacion = 'editar'
    
    try:
        rol = Rol.objects.get(id=int(id))
    
        esValido = validarRepetido(nombre, rol)
        # print(f'esValido: {esValido}')
        # print(f'esValido: {type(esValido)}')
        
        parametro = 'success'
        
        if esValido:
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
                
            editado = True
        else:
            print(f'error: invalido')
            parametro = 'warning'
    except:
        parametro = 'error'
    
    
    # return redirect(f'/rol', name='index-roles')    
    return redirect(f'/rol', name='index-roles')


def buscar(request):
    activoTemp = request.GET.get('activo')
    query = request.GET.get('q').strip()  # Obtener el término de búsqueda del parámetro 'q'
    resultados_roles = []
    context = {}
    roles = None
    
    global activo
    
    # Filtrar por el estado de 'activo'
    if activoTemp is not None and activoTemp == 'on':
        roles = Rol.objects.filter(activo=True)
        activoTemp = True
    else:
        roles = Rol.objects.filter(activo=False)
        activoTemp = False
        
    activo = activoTemp
    
    if query:
        query_normalized = normalize('NFKD', query).encode('ASCII', 'ignore').decode('ASCII')
        
        roles = roles.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized__icontains=query_normalized)
        )
        
        for res in roles:
            print(f'nombre: {res.nombre}')
            
    listaPermisos = Permiso.objects.all().order_by('id')
    listaRolesPermisos = getRolesPermisos(roles)
    resultadosAPaginar = listaRolesPermisos
    cantidad_de_resultados = len(resultadosAPaginar)
    paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
    page_number = request.GET.get('page')  # Obtén el número de página de la URL
    page: Page = paginator.get_page(page_number)
    
    context = {
                'listaPermisos':listaPermisos,
                'cantidad_de_resultados': cantidad_de_resultados,
                'page': page,
                'query': query,
                'activo': activo
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


def activar(request, id):
    
    global activado, operacion, activo 
    activado= False
    activo= False
    operacion = 'activar'

    try:
        rol = Rol.objects.get(id=id)

        rol.activo = True
        activado = True
        rol.save()
    
    except:
        pass

    return redirect(f'/rol', name='index-permiso' )