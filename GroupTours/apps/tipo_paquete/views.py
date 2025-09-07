from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
import django_filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import TipoPaquete
from .serializers import TipoPaqueteSerializer


# -------------------- FILTROS --------------------
class TipoPaqueteFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = TipoPaquete
        fields = ['nombre', 'activo']


# -------------------- PAGINACIÓN --------------------
class TipoPaquetePagination(PageNumberPagination):
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


# -------------------- VIEWSET --------------------
class TipoPaqueteViewSet(viewsets.ModelViewSet):
    queryset = TipoPaquete.objects.order_by('-fecha_creacion').all()
    serializer_class = TipoPaqueteSerializer
    pagination_class = TipoPaquetePagination
    permission_classes = []

    filter_backends = [DjangoFilterBackend]
    filterset_class = TipoPaqueteFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = TipoPaquete.objects.count()
        activos = TipoPaquete.objects.filter(activo=True).count()
        inactivos = TipoPaquete.objects.filter(activo=False).count()
        en_uso = TipoPaquete.objects.filter(en_uso=True).count()

        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos,
            'total_en_uso': en_uso,
        })

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        """
        Retorna todos los tipos de paquete sin paginación (solo id y nombre)
        """
        queryset = self.filter_queryset(self.get_queryset().filter(activo=True)).values('id', 'nombre')
        return Response(list(queryset))
