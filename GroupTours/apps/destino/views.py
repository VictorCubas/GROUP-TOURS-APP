from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Destino
from .serializers import DestinoSerializer
from .filters import DestinoFilter
from .pagination import DestinoPagination
from django.db import models

class DestinoViewSet(viewsets.ModelViewSet):
    queryset = Destino.objects.prefetch_related("hoteles").order_by('-fecha_creacion').all()
    serializer_class = DestinoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DestinoFilter
    pagination_class = DestinoPagination
    permission_classes = []

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Destino.objects.count()
        activos = Destino.objects.filter(activo=True).count()
        inactivos = Destino.objects.filter(activo=False).count()
        total_paises = Destino.objects.values('pais').distinct().count()
        
        data = [
            {'texto': 'Total', 'valor': str(total)},
            {'texto': 'Activos', 'valor': str(activos)},
            {'texto': 'Inactivos', 'valor': str(inactivos)},
            {'texto': 'Total Paises', 'valor': str(total_paises)},
        ]
        return Response(data)


    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = (
            self.filter_queryset(
                self.get_queryset().filter(activo=True)
            )
            .values('id', 'nombre', pais_nombre=models.F('pais__nombre'))  # ← cambio de alias
        )
        return Response(list(queryset))


