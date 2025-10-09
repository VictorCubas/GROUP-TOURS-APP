from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models

from .models import Destino
from .serializers import DestinoSerializer
from .filters import DestinoFilter
from .pagination import DestinoPagination


class DestinoViewSet(viewsets.ModelViewSet):
    """
    CRUD de destinos, ahora vinculados a una ciudad.
    """
    queryset = (
        Destino.objects
        .select_related("ciudad", "ciudad__pais")   # para evitar N+1
        .prefetch_related("hoteles")
        .order_by("-fecha_creacion")
    )
    serializer_class = DestinoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DestinoFilter
    pagination_class = DestinoPagination
    permission_classes = []

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        total = Destino.objects.count()
        activos = Destino.objects.filter(activo=True).count()
        inactivos = Destino.objects.filter(activo=False).count()
        # Países distintos a través de ciudad
        total_paises = (
            Destino.objects
            .values("ciudad__pais")
            .distinct()
            .count()
        )

        data = [
            {"texto": "Total", "valor": str(total)},
            {"texto": "Activos", "valor": str(activos)},
            {"texto": "Inactivos", "valor": str(inactivos)},
            {"texto": "Total Países", "valor": str(total_paises)},
        ]
        return Response(data)

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=["get"], url_path="todos", pagination_class=None)
    def todos(self, request):
        """
        Lista simplificada de destinos activos,
        mostrando ciudad y país.
        """
        queryset = (
            self.filter_queryset(
                self.get_queryset().filter(activo=True)
            )
            .values(
                "id",
                ciudad_nombre=models.F("ciudad__nombre"),
                pais_nombre=models.F("ciudad__pais__nombre"),
                zona_geografica_nombre=models.F("ciudad__pais__zona_geografica__nombre"), 
            )
        )
        return Response(list(queryset))
