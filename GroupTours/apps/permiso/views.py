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
from rest_framework.decorators import action

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
    
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        """
        Retorna todos los permisos sin paginación con modulo {id, nombre}
        """
        queryset = self.filter_queryset(
            self.get_queryset().filter(activo=True).select_related('modulo')
        )

        permisos = [
            {
                "id": permiso.id,
                "nombre": permiso.nombre,
                "descripcion": permiso.descripcion,
                "tipo": permiso.tipo,
                "modulo": {
                    "id": permiso.modulo.id if permiso.modulo else None,
                    "nombre": permiso.modulo.nombre if permiso.modulo else None
                }
            }
            for permiso in queryset
        ]

        return Response(permisos)
    
    
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Permiso.objects.count()
        activos = Permiso.objects.filter(activo=True).count()
        inactivos = Permiso.objects.filter(activo=False).count()
        en_uso = Permiso.objects.filter(en_uso=True).count()

        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos,
            'total_en_uso': en_uso,
        })
    
    class Meta:
        model = Permiso
        fields = '__all__'
        ordering = ['id']
        
        def __str__(self):
            return f'{self.nombre} ({self.get_tipo_display()})'