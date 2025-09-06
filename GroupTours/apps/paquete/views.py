from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Paquete
from .serializers import PaqueteSerializer
from .filters import PaqueteFilter


# -------------------- PAGINACIÓN --------------------
class PaquetePagination(PageNumberPagination):
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
class PaqueteViewSet(viewsets.ModelViewSet):
    queryset = Paquete.objects.select_related("tipo_paquete", "destino", "distribuidora").order_by('-fecha_creacion')
    serializer_class = PaqueteSerializer
    pagination_class = PaquetePagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaqueteFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Paquete.objects.count()
        activos = Paquete.objects.filter(activo=True).count()
        inactivos = Paquete.objects.filter(activo=False).count()
        propios = Paquete.objects.filter(propio=True).count()
        de_distribuidora = Paquete.objects.filter(propio=False).count()

        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos,
            'total_propios': propios,
            'total_de_distribuidora': de_distribuidora
        })

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = self.filter_queryset(
            self.get_queryset().filter(activo=True)
        ).values('id', 'nombre')
        return Response(list(queryset))
