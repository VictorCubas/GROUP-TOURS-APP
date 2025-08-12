from .models import Modulo

# Create your views here.
from rest_framework import viewsets

#from apps.informe.pagination import StandardResultsSetPagination
from .serializers import ModuloSerializer

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

class ModuloFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = Modulo
        fields = ['nombre', 'activo']


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


class ModuloListViewSet(viewsets.ModelViewSet):
    queryset = Modulo.objects.order_by('-fecha_creacion').all()
    serializer_class = ModuloSerializer
    pagination_class = PermisoPagination
    #pagination_class = StandardResultsSetPagination
    permission_classes = []
    
    filter_backends = [DjangoFilterBackend]
    filterset_class = ModuloFilter
    
    
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Modulo.objects.count()
        activos = Modulo.objects.filter(activo=True).count()
        inactivos = Modulo.objects.filter(activo=False).count()
        en_uso = Modulo.objects.filter(en_uso=True).count()

        return Response({
            'total_permisos': total,
            'total_activos': activos,
            'total_inactivos': inactivos,
            'total_en_uso': en_uso,
        })
    
    class Meta:
        model = Modulo
        fields = '__all__'
        ordering = ['id']
        
        def __str__(self):
            return f'{self.nombre}'