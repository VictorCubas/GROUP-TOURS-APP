from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import TipoRemuneracion
from .serializers import TipoRemuneracionSerializer

# -------------------- VIEWSET --------------------
class TipoRemuneracinoViewSet(viewsets.ModelViewSet):
    queryset = TipoRemuneracion.objects.order_by('-fecha_creacion').all()
    serializer_class = TipoRemuneracionSerializer
    permission_classes = []

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = TipoRemuneracion.objects.count()
        activos = TipoRemuneracion.objects.filter(activo=True).count()
        inactivos = TipoRemuneracion.objects.filter(activo=False).count()
        en_uso = TipoRemuneracion.objects.filter(en_uso=True).count()

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
        Retorna todos los tipos de contrato activos sin paginación (solo id y nombre)
        """
        queryset = self.get_queryset().filter(activo=True).values('id', 'nombre')
        return Response(list(queryset))

    class Meta:
        model = TipoRemuneracion
        fields = '__all__'
        ordering = ['id']

        def __str__(self):
            return f'{self.nombre}'
