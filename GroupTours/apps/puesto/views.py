from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
import django_filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Puesto
from .serializers import PuestoSerializer


# -------------------- VIEWSET --------------------
class PuestoViewSet(viewsets.ModelViewSet):
    queryset = Puesto.objects.order_by('-fecha_creacion').all()
    serializer_class = PuestoSerializer
    permission_classes = []


    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Puesto.objects.count()
        activos = Puesto.objects.filter(activo=True).count()
        inactivos = Puesto.objects.filter(activo=False).count()
        en_uso = Puesto.objects.filter(en_uso=True).count()

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
        model = Puesto
        fields = '__all__'
        ordering = ['id']

        def __str__(self):
            return f'{self.nombre}'
