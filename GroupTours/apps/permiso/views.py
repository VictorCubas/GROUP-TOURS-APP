from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Permiso
from django.core.paginator import Paginator, Page
from django.db.models import Q, Func, F
from unicodedata import normalize
# Create your views here.

def index(request):
    # print(request.path)
    listaPermiso = Permiso.objects.all().order_by('-id')

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
    
    resultadosAPaginar = listaPermiso
    cantidad_de_resultados = len(resultadosAPaginar)
    paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
    page_number = request.GET.get('page')  # Obtén el número de página de la URL
    page: Page = paginator.get_page(page_number)
    
    context = {
                'listaPermisos':listaPermiso,
                'cantidad_de_resultados': cantidad_de_resultados,
                'page': page,
                }
    
    mensaje = ''
    tipo = ''
    if query == 'delete-success' and query_value:
        context['eliminacionExitosa'] = query_value
        
    elif query == 'add-success':
        if query_value:
            mensaje = 'El permiso se ha guardado con exito'
            tipo = 'success'
        else:    
            mensaje = 'Permiso ya existente'
            tipo = 'warning'
            
        context['tipo'] = tipo
    elif query == 'edit-success':
        mensaje = 'El permiso se ha editado con exito'
        context['tipo'] = 'success'
    
    elif query == 'add-error' or query == 'edit-error':
        mensaje = 'Error: Ocurrio algo inesperado. Vuelva a intentarlo'
        context['tipo'] = 'danger'  

    context['mensaje'] = mensaje

    return render(request, 'permiso.html', context)


def registrarPermiso(request):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre').strip()
    descripcion = request.POST.get('txtDescripcion').strip()
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')

    esValido = validarRepetido(nombre)
    parametro = "success"

    if esValido:

        try: 
            #se crea un permiso
            Permiso.objects.create(nombre=nombre, descripcion=descripcion, tipo=tipo, formulario=formulario)

        except:
            parametro = "error"


    return redirect(f'/permiso?add-{parametro}={ esValido }', name='index-permiso' )

def edicionPermiso(request, codigo):
    permiso = Permiso.objects.get(id=int(codigo))
    return render(request, "edicionPermiso.html", {"permiso": permiso })

def editarPermiso(request, id):
    nombre = request.POST.get('txtNombre').strip()
    descripcion = request.POST.get('txtDescripcion').strip()
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')

    parametro = "success"

    try:
        permiso = Permiso.objects.get(id=id)
        permiso.nombre = nombre
        permiso.descripcion = descripcion
        permiso.tipo = tipo
        permiso.formulario = formulario
        permiso.save()

    except:
        parametro = "error"
        pass
    
    return redirect(f'/permiso?edit-{parametro}=true', name='index-permiso' )

def eliminar(request, id):
    eliminacionExitosa = False

    try:
        permiso = Permiso.objects.get(id=id)
        permiso.delete()
        eliminacionExitosa = True
    except:
        pass

    return redirect(f'/permiso', name='index-permiso' )


def validarRepetido(nombre):
    '''
    Este metodo valida que si hay algun permiso con el mismo nombre
    Se puede hacer de manera mas simple, solo reutilice lo que ya tenia
    '''
    
    # print('validar repetido')
    query_normalized = normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
        
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