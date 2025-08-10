from .models import Permiso

# Create your views here.
from rest_framework import viewsets

#from apps.informe.pagination import StandardResultsSetPagination
from .serializers import PermisoSerializer

#imports para los apis
from rest_framework.decorators import api_view
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
import django_filters

#imports para el manejo de imagenes
# from django.core.files.storage import FileSystemStorage

class PermisoFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    tipo = django_filters.CharFilter(field_name='tipo', lookup_expr='exact')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = Permiso
        fields = ['nombre', 'tipo', 'activo']


class PermisoPagination(PageNumberPagination):
    page_size = 2  # o el valor que desees
    page_size_query_param = 'page_size'  # permite que el frontend especifique la cantidad

    def get_paginated_response(self, data):
        return Response({
            'totalItems': self.page.paginator.count,
            'pageSize': self.get_page_size(self.request),
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class PermisoListViewSet(viewsets.ModelViewSet):
    queryset = Permiso.objects.order_by('-fechaCreacion').all()
    serializer_class = PermisoSerializer
    pagination_class = PermisoPagination
    #pagination_class = StandardResultsSetPagination
    permission_classes = []
    
    filter_backends = [DjangoFilterBackend]
    filterset_class = PermisoFilter
    
    class Meta:
        model = Permiso
        fields = '__all__'
        ordering = ['id']
        
        def __str__(self):
            return f'{self.nombre} ({self.get_tipo_display()})'

# editado = False
# agregado = False
# eliminado = False
# elimninacion_no_permitida = False
# nombre_repetido = False
# operacion = None
# activo = True
# activado = False

# def index(request):
#     # print(request.path)
#     listaPermiso = None
#     global editado, operacion, agregado, eliminado, activado 
#     if operacion == "activar": 
#         listaPermiso = Permiso.objects.filter(activo=False).order_by('-id')

#     else: 
#         listaPermiso = Permiso.objects.filter(activo=True).order_by('-id')

#     operaciones = ['add-success', 'add-error', 'add-warning', 'delete-success', 'delete-error',
#                    'delete-warning', 'edit-success', 'edit-error', 'edit-warning']
    
    
#     resultadosAPaginar = listaPermiso
#     cantidad_de_resultados = len(resultadosAPaginar)
#     paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
#     page_number = request.GET.get('page')  # Obtén el número de página de la URL
#     page: Page = paginator.get_page(page_number)
    
#     context = {
#                 'listaPermisos':listaPermiso,
#                 'cantidad_de_resultados': cantidad_de_resultados,
#                 'page': page,
#                 'menu_activo': 'permiso'
#                 }
    
#     mensaje = ''
#     tipo = ''
    
#     if operacion == 'editar':
#         print(f'editado: {editado}')
#         context['editado'] = editado
#         context['operacion'] = operacion
#         print(f'context: {context}')
#         mensaje = 'El permiso se ha editado con exito'
        
#         if editado:
#             tipo = 'success'
#         else:
#             tipo = 'warning'
#             mensaje = 'Permiso ya existente'
            
#         editado = False
        
        
#         # if nombre_repetido:
#         #     mensaje = 'Permiso ya existente'
        
#     elif operacion == 'agregar':
#         context['operacion'] = operacion
        
#         if agregado:
#             context['agregado'] = True
#             tipo = 'success'
#             mensaje = 'El permiso se ha guardado con exito'
            
#             agregado = False
#         else:
#             context['agregado'] = False
#             mensaje = 'Permiso ya existente'
#             tipo = 'warning'
#     elif operacion == 'eliminar':
#         context['operacion'] = operacion
#         print(f'eliminado 2: {eliminado}')
        
#         context['eliminacionExitosa'] = eliminado
        
#         if eliminado:
#             context['eliminado'] = True
#             tipo = 'success'
            
#         else:
#             context['eliminado'] = False
#             tipo = 'warning'
            
#             if elimninacion_no_permitida:
#                 context['eliminacionExitosa'] = 'warning'
            
#         eliminado = False
        
        
#         print(f"eliminacionExitosa: {context['eliminacionExitosa']}")

#     elif operacion == 'activar':
#         context['operacion'] = operacion
    
#         context['activacionExitosa'] = activado
        
#         if activado:
#             context['activado'] = True
#             tipo = 'success'
            
#         else:
#             context['activado'] = False
#             tipo = 'warning'
            
#         activado = False
            
#     context['tipo'] = tipo
#     operacion = None
#     context['mensaje'] = mensaje
#     context['activo'] = activo

#     return render(request, 'permiso.html', context)


# def registrarPermiso(request):
#     #se recupera los datos del formulario
#     nombre = request.POST.get('txtNombre').strip()
#     descripcion = request.POST.get('txtDescripcion').strip()
#     tipo = request.POST.get('txtTipo')
#     formulario = request.POST.get('txtFormulario')

#     esValido = validarRepetido(nombre, None)
    
#     print(f'esValido: {esValido}')
    
#     global agregado, nombre_repetido, operacion
#     nombre_repetido = esValido
#     agregado = False
#     operacion = 'agregar'

#     if esValido:

#         try: 
#             #se crea un permiso
#             Permiso.objects.create(nombre=nombre, descripcion=descripcion, tipo=tipo, formulario=formulario)
#             agregado = True
#         except:
#             pass


#     return redirect(f'/permiso', name='index-permiso' )

# def edicionPermiso(request, codigo):
#     permiso = Permiso.objects.get(id=int(codigo))
    
#     rolesPermisos = RolesPermisos.objects.filter(permiso_id = permiso.id)
    
#     habilitarEdicion = True
#     if len(rolesPermisos) > 0:
#         habilitarEdicion = False
        
#     return render(request, "edicionPermiso.html", {
#                 "permiso": permiso, "habilitarEdicion": habilitarEdicion,
#                                         'menu_activo': 'permiso'})

# def editarPermiso(request, id):
#     nombre = request.POST.get('txtNombre').strip()
#     descripcion = request.POST.get('txtDescripcion').strip()
#     tipo = request.POST.get('txtTipo')
#     formulario = request.POST.get('txtFormulario')
#     esValido = False

#     global editado, operacion, nombre_repetido
#     editado = False
#     operacion = 'editar'

#     try:
#         permiso = Permiso.objects.get(id=id)

#         esValido = validarRepetido(nombre, permiso)
#         nombre_repetido = esValido
#         print(f'esValido: {esValido}')
#         if esValido:
#             permiso.nombre = nombre
#             permiso.descripcion = descripcion
#             permiso.tipo = tipo
#             permiso.formulario = formulario
#             # permiso.save()
            
#             editado = True
#     except:
#         pass
    
#     return redirect(f'/permiso', name='index-permiso' )

# def eliminar(request, id):
    
#     global eliminado, operacion, elimninacion_no_permitida, activo
#     eliminado = False
#     elimninacion_no_permitida = False
#     operacion = 'eliminar'
#     activo = True

#     try:
#         permiso = Permiso.objects.get(id=id)

#         permisoEstaEnUso = permisoEnUso(id)
        
#         print(f'permisoEnUso: {permisoEstaEnUso}')
        
#         if not permisoEstaEnUso:
#             # permiso.delete()
#             permiso.activo = False
#             permiso.save()
#             eliminado = True
#         else:
#             elimninacion_no_permitida = True
#     except:
#         pass

#     return redirect(f'/permiso', name='index-permiso' )


# def permisoEnUso(id):
#     rolesPermisos = RolesPermisos.objects.filter(permiso_id = id)
    
#     #significa que el permiso esta siendo usado por otro rol
#     return len(rolesPermisos) > 0


# def validarRepetido(nombre, permiso):
#     '''
#     Este metodo valida que si hay algun permiso con el mismo nombre
#     Se puede hacer de manera mas simple, solo reutilice lo que ya tenia
#     '''
    
#     nombre = nombre.lower()

#     # Normalizar y convertir a minúsculas el nombre para la consulta
#     query_normalized = normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')

#     resultados_permisos = None

#     if permiso:
#         resultados_permisos = Permiso.objects.annotate(
#             nombre_normalized=Func(
#                 Func(F('nombre'), function='unaccent'), 
#                 function='lower'
#             ),
#         ).filter(
#             Q(nombre_normalized=query_normalized)
#         ).exclude(
#             id=permiso.id  # Excluyendo el permiso actual basado en su id
#         )
#     else:
#         resultados_permisos = Permiso.objects.annotate(
#             nombre_normalized=Func(
#                 Func(F('nombre'), function='unaccent'), 
#                 function='lower'
#             ),
#         ).filter(
#             Q(nombre_normalized=query_normalized)
#         )
    
#     # print(f'resultados_roles: {resultados_roles}')
#     # print(f'len resultados_roles: {len(resultados_roles)}')
    
#     if len(resultados_permisos) == 0:
#         return True

#     return False


# def buscar(request):
#     activoTemp = request.GET.get('activo')
#     query = request.GET.get('q', '').strip()  # Obtener el término de búsqueda del parámetro 'q'
#     context = {}

#     # Filtrar por el estado de 'activo'
#     if activoTemp is not None and activoTemp != 'False':
#         permisos = Permiso.objects.filter(activo=True)
#         activoTemp = True
#     else:
#         permisos = Permiso.objects.filter(activo=False)
#         activoTemp = False
    
#     # Filtrar por el término de búsqueda 'q' si no está vacío
#     if query:
#         query_normalized = normalize('NFKD', query).encode('ASCII', 'ignore').decode('ASCII')
#         permisos = permisos.annotate(
#             nombre_normalized=Func(F('nombre'), function='unaccent')
#         ).filter(
#             Q(nombre_normalized__icontains=query_normalized)
#         )

    
#     listaPermisos = Permiso.objects.all().order_by('id')

#     resultadosAPaginar = permisos
#     cantidad_de_resultados = len(resultadosAPaginar)
#     paginator = Paginator(resultadosAPaginar, per_page=5)  # 5 resultados por página
#     page_number = request.GET.get('page')  # Obtén el número de página de la URL
#     page: Page = paginator.get_page(page_number)
    
#     context = {
#         'listaPermisos': listaPermisos,
#         'cantidad_de_resultados': cantidad_de_resultados,
#         'page': page,
#         'query': query,
#         'activo': activoTemp  # Incluye el valor de activo en el contexto
#     }

#     return render(request, 'permiso.html', context)

# def activar(request, id):
    
#     global activado, operacion, activo 
#     activado= False
#     activo= False
#     operacion = 'activar'

#     try:
#         permiso = Permiso.objects.get(id=id)

#         permiso.activo = True
#         activado = True
#         permiso.save()
#     except:
#         pass

#     return redirect(f'/permiso', name='index-permiso' )