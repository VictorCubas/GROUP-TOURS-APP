from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Servicio
from .serializers import ServicioSerializer
from .filters import ServicioFilter

# -------------------- PAGINACIÓN --------------------
class ServicioPagination(PageNumberPagination):
    page_size = 100
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
class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.order_by('-fecha_creacion').all()
    serializer_class = ServicioSerializer
    pagination_class = ServicioPagination
    permission_classes = []

    filter_backends = [DjangoFilterBackend]
    filterset_class = ServicioFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Servicio.objects.count()
        activos = Servicio.objects.filter(activo=True).count()
        inactivos = Servicio.objects.filter(activo=False).count()
        en_uso = Servicio.objects.filter(en_uso=True).count()

        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos,
            'total_en_uso': en_uso,
        })

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(activo=True)).values('id', 'nombre')
        return Response(list(queryset))
