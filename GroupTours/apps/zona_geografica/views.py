from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import ZonaGeografica
from .serializers import ZonaGeograficaSerializer
from .filters import ZonaGeograficaFilter
from .pagination import ZonaGeograficaPagination


class ZonaGeograficaViewSet(viewsets.ModelViewSet):
    """
    CRUD completo para Zonas Geográficas.
    """
    queryset = ZonaGeografica.objects.all().order_by("-fecha_creacion")
    serializer_class = ZonaGeograficaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ZonaGeograficaFilter
    pagination_class = ZonaGeograficaPagination
    permission_classes = []

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        total = ZonaGeografica.objects.count()
        activos = ZonaGeografica.objects.filter(activo=True).count()
        inactivos = ZonaGeografica.objects.filter(activo=False).count()

        data = [
            {"texto": "Total", "valor": str(total)},
            {"texto": "Activos", "valor": str(activos)},
            {"texto": "Inactivos", "valor": str(inactivos)},
        ]
        return Response(data)

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=["get"], url_path="todos", pagination_class=None)
    def todos(self, request):
        """
        Lista simplificada de zonas activas.
        """
        queryset = self.filter_queryset(
            self.get_queryset().filter(activo=True)
        ).values("id", "nombre")
        return Response(list(queryset))
