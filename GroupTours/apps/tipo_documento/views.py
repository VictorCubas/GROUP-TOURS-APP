from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
import django_filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import TipoDocumento
from .serializers import TipoDocumentoSerializer


# -------------------- FILTROS --------------------
class TipoDocumentoFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = TipoDocumento
        fields = ['nombre', 'activo',]


# -------------------- PAGINACIÓN --------------------
class TipoDocumentoPagination(PageNumberPagination):
    page_size = 5  # puedes ajustar
    page_size_query_param = 'page_size'  # frontend puede setear page_size dinámico

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
class TipoDocumentoViewSet(viewsets.ModelViewSet):
    queryset = TipoDocumento.objects.order_by('-fecha_creacion').all()
    serializer_class = TipoDocumentoSerializer
    pagination_class = TipoDocumentoPagination
    permission_classes = []

    filter_backends = [DjangoFilterBackend]
    filterset_class = TipoDocumentoFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = TipoDocumento.objects.count()
        activos = TipoDocumento.objects.filter(activo=True).count()
        inactivos = TipoDocumento.objects.filter(activo=False).count()
        en_uso = TipoDocumento.objects.filter(en_uso=True).count()

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
        Retorna todos los tipos de documento sin paginación (solo id y nombre)
        """
        queryset = self.filter_queryset(self.get_queryset().filter(activo=True)).values('id', 'nombre')
        return Response(list(queryset))

    class Meta:
        model = TipoDocumento
        fields = '__all__'
        ordering = ['id']

        def __str__(self):
            return f'{self.nombre}'
