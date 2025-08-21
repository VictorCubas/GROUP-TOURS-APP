# views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from .models import Rol
from .serializers import RolCreateUpdateSerializer, RolSerializer
import django_filters

# Filtros opcionales para Rol
class RolFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = Rol
        fields = ['nombre', 'activo']

# Paginación
class RolPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response({
            'totalItems': self.page.paginator.count,
            'pageSize': self.get_page_size(self.request),
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

# ViewSet de Rol
class RolListViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.order_by('-fecha_creacion').all()
    serializer_class = RolSerializer
    pagination_class = RolPagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = RolFilter

    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Rol.objects.count()
        activos = Rol.objects.filter(activo=True).count()
        inactivos = Rol.objects.filter(activo=False).count()
        en_uso = Rol.objects.filter(en_uso=True).count()

        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos,
            'total_en_uso': en_uso,
        })

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RolCreateUpdateSerializer
        return RolSerializer