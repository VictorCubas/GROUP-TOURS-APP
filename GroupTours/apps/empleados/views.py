from django.shortcuts import render

# from apps.rol.models import UsuariosEmpleados
from .models import Empleado
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
activo = True
activado = False

# Create your views here.
def index(request):
    listaEmpleado = None
    global editado, operacion, agregado, eliminado, activado 
    
    if operacion == "activar": 
        listaEmpleado = Empleado.objects.filter(activo=False).order_by('-id')

    else: 
        listaEmpleado = Empleado.objects.filter(activo=True).order_by('-id')
        
    # print(f'empleados: {listaEmpleado}')
        
    # print(f'listaEmpleado: {listaEmpleado[0].en_uso}')
    
    resultadosAPaginar = listaEmpleado
    cantidad_de_resultados = len(resultadosAPaginar)
    paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
    page_number = request.GET.get('page')  # Obtén el número de página de la URL
    page: Page = paginator.get_page(page_number)
    
    context = {
                'listaEmpleados': listaEmpleado,
                'cantidad_de_resultados': cantidad_de_resultados,
                'page': page,
                'menu_activo': 'empleado'
                }
    
    mensaje = ''
    tipo = ''
    
    if operacion == 'editar':
        print(f'editado: {editado}')
        context['editado'] = editado
        context['operacion'] = operacion
        print(f'context: {context}')
        mensaje = 'El empleado se ha editado con exito'
        
        if editado:
            tipo = 'success'
        else:
            tipo = 'warning'
            mensaje = 'Empleado ya existente'
            
        editado = False
        
    elif operacion == 'agregar':
        context['operacion'] = operacion
        
        if agregado:
            context['agregado'] = True
            tipo = 'success'
            mensaje = 'El empleado se ha guardado con exito'
            
            agregado = False
        else:
            context['agregado'] = False
            mensaje = 'Empleaado ya existente'
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

    return render(request, 'empleados.html', context)