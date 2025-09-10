from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Moneda
from .serializers import MonedaSerializer
from .filters import MonedaFilter


# -------------------- PAGINACIÓN --------------------
class MonedaPagination(PageNumberPagination):
    page_size = 10
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
class MonedaViewSet(viewsets.ModelViewSet):
    queryset = Moneda.objects.order_by('-fecha_creacion').all()
    serializer_class = MonedaSerializer
    pagination_class = MonedaPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = MonedaFilter
    permission_classes = []

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Moneda.objects.count()
        activos = Moneda.objects.filter(activo=True).count()
        inactivos = Moneda.objects.filter(activo=False).count()
        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos
        })

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(activo=True)).values('id', 'nombre', 'codigo', 'simbolo')
        return Response(list(queryset))
