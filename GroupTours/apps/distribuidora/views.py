from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Distribuidora
from .serializers import DistribuidoraSerializer

class DistribuidoraViewSet(viewsets.ModelViewSet):
    queryset = Distribuidora.objects.order_by('-fecha_creacion').all()
    serializer_class = DistribuidoraSerializer
    permission_classes = []

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Distribuidora.objects.count()
        activos = Distribuidora.objects.filter(activo=True).count()
        inactivos = Distribuidora.objects.filter(activo=False).count()
        en_uso = Distribuidora.objects.filter(en_uso=True).count()

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
        Retorna todos los distribuidores activos sin paginación (solo id y nombre)
        """
        queryset = self.get_queryset().filter(activo=True).values('id', 'nombre')
        return Response(list(queryset))
