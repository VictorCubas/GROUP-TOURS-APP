from django.shortcuts import render
from django.http import HttpResponse
from .models import Permiso
from django.core.paginator import Paginator, Page
# Create your views here.

def index(request):
    # print(request.path)
    listaPermiso = Permiso.objects.all().order_by('-id')

    operaciones = ['add-success', 'add-error', 'add-warning', 'delete-success', 'delete-error',
                   'delete-warning', 'edit-success', 'edit-error', 'edit-warning']
    
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
    if query == 'delete-success':
        context['eliminacionExitosa'] = query_value
        
    if query == 'delete-warning':
        print(f'delete warning {query_value}')
        context['eliminacionExitosa'] = 'warning'
        
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
        
    elif query == 'edit-warning':
        mensaje = 'Permiso ya existente, verifique que el nombre no sea repetido'
        context['tipo'] = 'warning'
        
    elif query == 'add-error' or query == 'edit-error':
        mensaje = 'Error: Ocurrio algo inesperado. Vuelva a intentarlo'
        context['tipo'] = 'danger'  

    context['mensaje'] = mensaje

    return render(request, 'permiso.html', context)


def registrarPermiso(request):
    #se recupera los datos del formulario
    nombre = request.POST.get('txtNombre')
    descripcion = request.POST.get('txtDescripcion')
    tipo = request.POST.get('txtTipo')
    formulario = request.POST.get('txtFormulario')
   
    #se crea un permiso
    Permiso.objects.create(nombre=nombre, descripcion=descripcion, tipo=tipo, formulario=formulario)

    #se recupera toda la lista de permiso
    listaPermiso = Permiso.objects.all().order_by('id')

    return render(request, 'permiso.html',{'listaPermisos':listaPermiso} )

def eliminar(request, id):
    try:
        permiso = Permiso.objects.get(id=id)
        permiso.delete()
    except:
        pass

    listaPermiso = Permiso.objects.all().order_by('id')

    return render(request, 'permiso.html', {'listaPermisos':listaPermiso})