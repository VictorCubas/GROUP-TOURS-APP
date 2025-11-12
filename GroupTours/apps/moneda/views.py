from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q

from .models import Moneda, CotizacionMoneda
from .serializers import MonedaSerializer, CotizacionMonedaSerializer, CotizacionMonedaCreateSerializer
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


# -------------------- VIEWSET COTIZACIONES --------------------
class CotizacionMonedaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cotizaciones de monedas.

    Endpoints disponibles:
    - GET /cotizaciones/ - Listar cotizaciones
    - POST /cotizaciones/ - Crear nueva cotización
    - GET /cotizaciones/{id}/ - Detalle de cotización
    - PUT/PATCH /cotizaciones/{id}/ - Actualizar cotización
    - DELETE /cotizaciones/{id}/ - Eliminar cotización
    - GET /cotizaciones/vigente/?moneda_codigo=USD - Obtener cotización vigente
    - GET /cotizaciones/historial/?moneda_codigo=USD&fecha_desde=2025-11-01&fecha_hasta=2025-11-09 - Historial
    """
    queryset = CotizacionMoneda.objects.select_related('moneda', 'usuario_registro').order_by('-fecha_vigencia', '-fecha_creacion')
    serializer_class = CotizacionMonedaSerializer
    pagination_class = MonedaPagination
    filter_backends = [DjangoFilterBackend]
    permission_classes = []

    def get_serializer_class(self):
        """Usar serializer diferente para crear/actualizar"""
        if self.action in ['create', 'update', 'partial_update']:
            return CotizacionMonedaCreateSerializer
        return CotizacionMonedaSerializer

    def perform_create(self, serializer):
        """Guardar usuario que registra la cotización"""
        serializer.save(usuario_registro=self.request.user if self.request.user.is_authenticated else None)

    def create(self, request, *args, **kwargs):
        """
        Crear nueva cotización o actualizar si ya existe para esa fecha.

        Request Body:
        {
            "moneda": 1,  // ID de la moneda (ej: USD)
            "valor_en_guaranies": 7300.00,
            "fecha_vigencia": "2025-11-09",  // Opcional, por defecto hoy
            "observaciones": "Cotización del BCP"  // Opcional
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verificar si ya existe cotización para esa moneda y fecha
        moneda = serializer.validated_data['moneda']
        fecha_vigencia = serializer.validated_data.get('fecha_vigencia', timezone.now().date())

        cotizacion_existente = CotizacionMoneda.objects.filter(
            moneda=moneda,
            fecha_vigencia=fecha_vigencia
        ).first()

        if cotizacion_existente:
            # Actualizar existente
            for attr, value in serializer.validated_data.items():
                setattr(cotizacion_existente, attr, value)

            cotizacion_existente.usuario_registro = self.request.user if self.request.user.is_authenticated else None
            cotizacion_existente.save()

            response_serializer = CotizacionMonedaSerializer(cotizacion_existente)
            return Response({
                'message': 'Cotización actualizada exitosamente',
                'updated': True,
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            # Crear nueva
            self.perform_create(serializer)
            response_serializer = CotizacionMonedaSerializer(serializer.instance)
            return Response({
                'message': 'Cotización registrada exitosamente',
                'created': True,
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='vigente')
    def vigente(self, request):
        """
        Obtener cotización vigente para una moneda específica.

        Query params:
        - moneda_codigo: Código de la moneda (ej: USD) - Requerido
        - fecha: Fecha de referencia (formato: YYYY-MM-DD) - Opcional, por defecto hoy

        Ejemplo: GET /cotizaciones/vigente/?moneda_codigo=USD
        """
        moneda_codigo = request.query_params.get('moneda_codigo')
        fecha_param = request.query_params.get('fecha')

        if not moneda_codigo:
            return Response({
                'error': 'El parámetro moneda_codigo es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            moneda = Moneda.objects.get(codigo=moneda_codigo)
        except Moneda.DoesNotExist:
            return Response({
                'error': f'No existe la moneda con código {moneda_codigo}'
            }, status=status.HTTP_404_NOT_FOUND)

        # Determinar fecha
        if fecha_param:
            try:
                from datetime import datetime
                fecha = datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            fecha = timezone.now().date()

        # Buscar cotización vigente
        cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda, fecha)

        if not cotizacion:
            return Response({
                'error': f'No existe cotización vigente para {moneda.nombre} en la fecha {fecha}',
                'moneda_codigo': moneda_codigo,
                'fecha': fecha
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = CotizacionMonedaSerializer(cotizacion)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='historial')
    def historial(self, request):
        """
        Obtener historial de cotizaciones con filtros.

        Query params:
        - moneda_codigo: Código de la moneda (ej: USD) - Opcional
        - fecha_desde: Fecha inicio (formato: YYYY-MM-DD) - Opcional
        - fecha_hasta: Fecha fin (formato: YYYY-MM-DD) - Opcional

        Ejemplo: GET /cotizaciones/historial/?moneda_codigo=USD&fecha_desde=2025-11-01&fecha_hasta=2025-11-09
        """
        queryset = self.get_queryset()

        # Filtrar por moneda
        moneda_codigo = request.query_params.get('moneda_codigo')
        if moneda_codigo:
            queryset = queryset.filter(moneda__codigo=moneda_codigo)

        # Filtrar por rango de fechas
        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')

        if fecha_desde:
            queryset = queryset.filter(fecha_vigencia__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_vigencia__lte=fecha_hasta)

        # Paginar
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
