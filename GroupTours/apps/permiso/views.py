from django.shortcuts import render, redirect
from django.http import HttpResponse

from apps.rol.models import RolesPermisos
from .models import Permiso
from django.core.paginator import Paginator, Page
from django.db.models import Q, Func, F
from unicodedata import normalize
from django.core.paginator import Paginator, Page
# Create your views here.

editado = False
agregado = False
eliminado = False
elimninacion_no_permitida = False
nombre_repetido = False
operacion = None

def index(request):
    # print(request.path)
    listaPermiso = Permiso.objects.all().order_by('-id')

    operaciones = ['add-success', 'add-error', 'add-warning', 'delete-success', 'delete-error',
                   'delete-warning', 'edit-success', 'edit-error', 'edit-warning']
    
    
    global editado, operacion, agregado, eliminado
    resultadosAPaginar = listaPermiso
    cantidad_de_resultados = len(resultadosAPaginar)
    paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
    page_number = request.GET.get('page')  # Obtén el número de página de la URL
    page: Page = paginator.get_page(page_number)
    
    context = {
                'listaPermisos':listaPermiso,
                'cantidad_de_resultados': cantidad_de_resultados,
                'page': page,
                'menu_activo': 'permiso'
                }
    
    mensaje = ''
    tipo = ''
    
    if operacion == 'editar':
        context['editado'] = True
        context['operacion'] = operacion
        print(f'context: {context}')
        tipo = 'success'
        editado = False
        mensaje = 'El permiso se ha editado con exito'
        
    elif operacion == 'agregar':
        context['operacion'] = operacion
        
        if agregado:
            context['agregado'] = True
            tipo = 'success'
            mensaje = 'El permiso se ha guardado con exito'
            
            agregado = False
        else:
            context['agregado'] = False
            mensaje = 'Permiso ya existente'
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
            
    context['tipo'] = tipo
    operacion = None
    context['mensaje'] = mensaje

    return render(request, 'permiso.html', context)


def registrarPermiso(request):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre').strip()
    descripcion = request.POST.get('txtDescripcion').strip()
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')

    esValido = validarRepetido(nombre, None)
    
    global agregado, nombre_repetido, operacion
    nombre_repetido = esValido
    agregado = False
    operacion = 'agregar'

    if esValido:

        try: 
            #se crea un permiso
            Permiso.objects.create(nombre=nombre, descripcion=descripcion, tipo=tipo, formulario=formulario)
            agregado = True
        except:
            parametro = "error"


    return redirect(f'/permiso', name='index-permiso' )

def edicionPermiso(request, codigo):
    permiso = Permiso.objects.get(id=int(codigo))
    
    rolesPermisos = RolesPermisos.objects.filter(permiso_id = permiso.id)
    
    habilitarEdicion = True
    if len(rolesPermisos) > 0:
        habilitarEdicion = False
        
    return render(request, "edicionPermiso.html", {"permiso": permiso, "habilitarEdicion": habilitarEdicion })

def editarPermiso(request, id):
    nombre = request.POST.get('txtNombre').strip()
    descripcion = request.POST.get('txtDescripcion').strip()
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')
    esValido = False

    global editado, operacion
    editado = False
    operacion = 'editar'
    parametro = "success"

    try:
        permiso = Permiso.objects.get(id=id)

        esValido = validarRepetido(nombre, permiso)
        if esValido:
            permiso.nombre = nombre
            permiso.descripcion = descripcion
            permiso.tipo = tipo
            permiso.formulario = formulario
            permiso.save()
            
            editado = True
    except:
        pass
    
    return redirect(f'/permiso', name='index-permiso' )

def eliminar(request, id):
    
    global eliminado, operacion, elimninacion_no_permitida
    eliminado = False
    elimninacion_no_permitida = False
    operacion = 'eliminar'

    try:
        permiso = Permiso.objects.get(id=id)

        permisoEstaEnUso = permisoEnUso(id)
        
        print(f'permisoEnUso: {permisoEstaEnUso}')
        
        if not permisoEstaEnUso:
            permiso.delete()
            eliminado = True
        else:
            elimninacion_no_permitida = True
    except:
        pass

    return redirect(f'/permiso', name='index-permiso' )


def permisoEnUso(id):
    rolesPermisos = RolesPermisos.objects.filter(permiso_id = id)
    
    #significa que el permiso esta siendo usado por otro rol
    return len(rolesPermisos) > 0


def validarRepetido(nombre, permiso):
    '''
    Este metodo valida que si hay algun permiso con el mismo nombre
    Se puede hacer de manera mas simple, solo reutilice lo que ya tenia
    '''
    
    # print('validar repetido')
    query_normalized = normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
    resultados_permisos= None
    
    if permiso:
        # rolesPermisos = RolesPermisos.objects.filter(permiso_id = permiso.id)
        # if len(rolesPermisos) > 0:
        #     return False

        resultados_permisos = Permiso.objects.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized=query_normalized)
        ).exclude(
            id=permiso.id  # Excluyendo el permiso actual basado en su id
        )

    else:    
        resultados_permisos = Permiso.objects.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized=query_normalized)
        )
    
    # print(f'resultados_roles: {resultados_roles}')
    # print(f'len resultados_roles: {len(resultados_roles)}')
    
    if len(resultados_permisos) == 0:
        return True

    return False


def buscar(request):
    print('hola.....')
    query = request.GET.get('q').strip()  # Obtener el término de búsqueda del parámetro 'q'
    resultados = []
    context = {}
    
    if query:
        query_normalized = normalize('NFKD', query).encode('ASCII', 'ignore').decode('ASCII')
        
        resultados = Permiso.objects.annotate(
            nombre_normalized=Func(F('nombre'), function='unaccent'),
        ).filter(
            Q(nombre_normalized__icontains=query_normalized)
        )
        
        print(resultados) 
        listaPermisos = Permiso.objects.all().order_by('id')

        resultadosAPaginar = resultados
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
        
    return render(request, 'permiso.html', context)