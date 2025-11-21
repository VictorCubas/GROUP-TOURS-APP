# apps/arqueo_caja/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import Caja, AperturaCaja, MovimientoCaja, CierreCaja
from .serializers import (
    CajaListSerializer, CajaDetailSerializer, CajaCreateSerializer,
    AperturaCajaListSerializer, AperturaCajaDetailSerializer, AperturaCajaCreateSerializer,
    MovimientoCajaListSerializer, MovimientoCajaDetailSerializer, MovimientoCajaCreateSerializer,
    CierreCajaListSerializer, CierreCajaDetailSerializer, CierreCajaCreateSerializer,
    CierreCajaAutorizarSerializer, CierreCajaSimpleSerializer
)
from .pagination import CustomPageNumberPagination


class CajaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de cajas (puntos de venta).

    Acciones personalizadas:
    - GET /cajas/{id}/estado/ - Obtener estado actual de la caja
    - GET /cajas/{id}/historial/ - Historial de aperturas y cierres
    - GET /cajas/puntos-expedicion-disponibles/ - Lista de PEs disponibles (sin caja asignada)
    """
    queryset = Caja.objects.all().select_related('punto_expedicion', 'punto_expedicion__establecimiento')
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['estado_actual', 'activo', 'punto_expedicion']
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return CajaListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CajaCreateSerializer
        return CajaDetailSerializer

    def update(self, request, *args, **kwargs):
        """Actualizar una caja con validaciones adicionales"""
        caja = self.get_object()

        # Si se está intentando desactivar (activo=False)
        if 'activo' in request.data and request.data['activo'] == False:
            if caja.estado_actual == 'abierta':
                return Response(
                    {'error': 'No se puede desactivar una caja que está abierta. Cierre la caja primero.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Actualizar parcialmente una caja con validaciones adicionales"""
        caja = self.get_object()

        # Si se está intentando desactivar (activo=False)
        if 'activo' in request.data and request.data['activo'] == False:
            if caja.estado_actual == 'abierta':
                return Response(
                    {'error': 'No se puede desactivar una caja que está abierta. Cierre la caja primero.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminar (desactivar) una caja - Soft delete"""
        caja = self.get_object()

        # Validar que la caja esté cerrada
        if caja.estado_actual == 'abierta':
            return Response(
                {'error': 'No se puede eliminar una caja que está abierta. Cierre la caja primero.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Soft delete: marcar como inactiva
        caja.activo = False
        caja.save(update_fields=['activo'])

        return Response(
            {'message': 'Caja desactivada exitosamente'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def estado(self, request, pk=None):
        """Obtener estado actual de la caja con información resumida"""
        caja = self.get_object()

        # Buscar apertura activa
        apertura_activa = caja.aperturas.filter(
            esta_abierta=True,
            activo=True
        ).select_related('responsable', 'responsable__persona').first()

        data = {
            'caja': CajaDetailSerializer(caja).data,
            'estado': caja.estado_actual,
            'saldo_actual': caja.saldo_actual,
            'apertura_activa': None
        }

        if apertura_activa:
            data['apertura_activa'] = AperturaCajaDetailSerializer(apertura_activa).data

        return Response(data)

    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Historial de aperturas y cierres de la caja"""
        caja = self.get_object()

        aperturas = caja.aperturas.all().select_related(
            'responsable', 'responsable__persona'
        ).prefetch_related('cierre').order_by('-fecha_hora_apertura')[:10]

        historial = []
        for apertura in aperturas:
            item = {
                'apertura': AperturaCajaListSerializer(apertura).data,
                'cierre': None
            }

            if hasattr(apertura, 'cierre'):
                item['cierre'] = CierreCajaListSerializer(apertura.cierre).data

            historial.append(item)

        return Response(historial)

    @action(detail=False, methods=['get'], url_path='resumen', pagination_class=None)
    def resumen(self, request):
        """Resumen estadístico de todas las cajas"""
        total = Caja.objects.count()
        activas = Caja.objects.filter(activo=True).count()
        inactivas = Caja.objects.filter(activo=False).count()
        abiertas = Caja.objects.filter(estado_actual='abierta', activo=True).count()
        cerradas = Caja.objects.filter(estado_actual='cerrada', activo=True).count()

        # Saldo total en cajas abiertas
        saldo_total = Caja.objects.filter(
            estado_actual='abierta',
            activo=True
        ).aggregate(total=Sum('saldo_actual'))['total'] or 0

        ultimos_30_dias = timezone.now() - timedelta(days=30)
        nuevas = Caja.objects.filter(fecha_creacion__gte=ultimos_30_dias).count()

        data = [
            {'texto': 'Total Cajas', 'valor': str(total)},
            {'texto': 'Activas', 'valor': str(activas)},
            {'texto': 'Inactivas', 'valor': str(inactivas)},
            {'texto': 'Abiertas Ahora', 'valor': str(abiertas)},
            {'texto': 'Cerradas', 'valor': str(cerradas)},
            {'texto': 'Saldo Total en Cajas Abiertas', 'valor': f'Gs {saldo_total:,.0f}'},
            {'texto': 'Nuevas últimos 30 días', 'valor': str(nuevas)},
        ]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='puntos-expedicion-disponibles', pagination_class=None)
    def puntos_expedicion_disponibles(self, request):
        """
        Retorna la lista de Puntos de Expedición que NO tienen una caja asignada.
        Útil para el selector del frontend al crear/editar cajas.

        GET /api/cajas/puntos-expedicion-disponibles/

        Returns:
            Lista de PuntoExpedicion que están activos y no tienen caja asignada.
        """
        from apps.facturacion.models import PuntoExpedicion
        from apps.facturacion.serializers import PuntoExpedicionSerializer

        # Obtener PEs que no tienen caja asignada
        # Con la relación OneToOneField, los PE sin caja no tienen el atributo 'caja'
        pes_disponibles = PuntoExpedicion.objects.filter(
            activo=True
        ).exclude(
            caja__isnull=False  # Excluir los que YA tienen caja
        ).select_related('establecimiento').order_by('establecimiento', 'codigo')

        serializer = PuntoExpedicionSerializer(pes_disponibles, many=True)
        return Response(serializer.data)


class AperturaCajaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de aperturas de caja.

    Acciones personalizadas:
    - GET /aperturas/activas/ - Listar aperturas activas
    - GET /aperturas/{id}/resumen/ - Resumen de la apertura con movimientos
    - POST /aperturas/{id}/anular/ - Anular apertura (solo si no hay movimientos)
    """
    queryset = AperturaCaja.objects.all().select_related(
        'caja', 'responsable', 'responsable__persona'
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['caja', 'responsable', 'esta_abierta', 'activo']
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return AperturaCajaListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AperturaCajaCreateSerializer
        return AperturaCajaDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Crear una nueva apertura de caja.
        El responsable se asigna automáticamente desde el usuario autenticado.
        Validaciones:
        - El usuario debe tener un empleado asociado
        - El empleado no debe tener otra caja abierta
        - La caja debe estar cerrada

        Returns:
        {
            "id": 1,
            "codigo_apertura": "APR-2025-0001",
            "caja": 1,
            "caja_nombre": "Caja Principal",
            "responsable": 1,
            "responsable_nombre": "Juan Pérez",
            "fecha_hora_apertura": "2025-11-17T15:42:00.000Z",
            "monto_inicial": "1000000.00",
            "observaciones_apertura": "",
            "esta_abierta": true,
            "activo": true
        }
        """
        # Obtener el empleado del usuario autenticado
        try:
            empleado = request.user.empleado
        except AttributeError:
            return Response(
                {'error': 'El usuario no tiene un empleado asociado. Contacte al administrador.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not empleado:
            return Response(
                {'error': 'El usuario no tiene un empleado asociado. Contacte al administrador.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que el empleado no tenga otra caja abierta
        apertura_existente = AperturaCaja.objects.filter(
            responsable=empleado,
            esta_abierta=True,
            activo=True
        ).first()

        if apertura_existente:
            return Response(
                {
                    'error': f'Ya tienes una caja abierta: {apertura_existente.caja.nombre} (Apertura: {apertura_existente.codigo_apertura}). Debes cerrarla antes de abrir otra.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que la caja esté cerrada
        caja_id = request.data.get('caja')
        if caja_id:
            try:
                caja = Caja.objects.get(pk=caja_id)
                if caja.estado_actual != 'cerrada':
                    return Response(
                        {'error': f'La caja {caja.nombre} ya está abierta. No se puede abrir nuevamente.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Caja.DoesNotExist:
                return Response(
                    {'error': 'La caja especificada no existe.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Asignar el responsable automáticamente si no se proporciona
        data = request.data.copy()
        if 'responsable' not in data or not data.get('responsable'):
            data['responsable'] = empleado.id

        # Crear la apertura
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Retornar usando AperturaCajaListSerializer para incluir todos los datos
        apertura = AperturaCaja.objects.get(pk=serializer.instance.id)
        response_serializer = AperturaCajaListSerializer(apertura)

        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'])
    def activas(self, request):
        """Listar todas las aperturas activas (cajas abiertas)"""
        aperturas_activas = self.queryset.filter(
            esta_abierta=True,
            activo=True
        ).select_related('caja', 'responsable', 'responsable__persona')

        serializer = AperturaCajaListSerializer(aperturas_activas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def resumen(self, request, pk=None):
        """Resumen detallado de la apertura con movimientos"""
        apertura = self.get_object()

        # Obtener movimientos
        movimientos = apertura.movimientos.filter(activo=True).select_related(
            'usuario_registro', 'usuario_registro__persona', 'comprobante'
        ).order_by('-fecha_hora_movimiento')

        # Calcular totales
        from decimal import Decimal
        from django.db.models import Sum

        # Ingresos por método de pago
        ingresos = movimientos.filter(tipo_movimiento='ingreso')

        total_efectivo = ingresos.filter(
            metodo_pago='efectivo'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        total_tarjetas = ingresos.filter(
            metodo_pago__in=['tarjeta_debito', 'tarjeta_credito']
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        total_transferencias = ingresos.filter(
            metodo_pago='transferencia'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        total_cheques = ingresos.filter(
            metodo_pago='cheque'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        total_otros = ingresos.filter(
            metodo_pago__in=['qr', 'otro']
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        # Total de todos los ingresos (para información)
        total_ingresos = total_efectivo + total_tarjetas + total_transferencias + total_cheques + total_otros

        # Egresos
        total_egresos = movimientos.filter(
            tipo_movimiento='egreso'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        # Saldo esperado en EFECTIVO (para arqueo de caja)
        saldo_esperado_efectivo = apertura.monto_inicial + total_efectivo - total_egresos

        # Saldo total (incluyendo todos los métodos de pago - solo informativo)
        saldo_total = apertura.monto_inicial + total_ingresos - total_egresos

        data = {
            'apertura': AperturaCajaDetailSerializer(apertura).data,
            'movimientos': MovimientoCajaListSerializer(movimientos[:50], many=True).data,
            'totales': {
                'monto_inicial': apertura.monto_inicial,

                # Desglose de ingresos por método
                'ingresos_por_metodo': {
                    'efectivo': total_efectivo,
                    'tarjetas': total_tarjetas,
                    'transferencias': total_transferencias,
                    'cheques': total_cheques,
                    'otros': total_otros,
                    'total': total_ingresos
                },

                'total_egresos': total_egresos,

                # Saldo esperado en EFECTIVO (lo que se debe contar físicamente)
                'saldo_esperado_efectivo': saldo_esperado_efectivo,

                # Saldo total (incluyendo todos los métodos - solo informativo)
                'saldo_total': saldo_total,

                'cantidad_movimientos': movimientos.count()
            }
        }

        return Response(data)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """Anular apertura (solo si no tiene movimientos)"""
        apertura = self.get_object()

        # Validar que no haya movimientos
        if apertura.movimientos.filter(activo=True).exists():
            return Response(
                {'error': 'No se puede anular una apertura con movimientos registrados'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que no tenga cierre
        if hasattr(apertura, 'cierre'):
            return Response(
                {'error': 'No se puede anular una apertura que ya tiene cierre'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anular
        apertura.activo = False
        apertura.esta_abierta = False
        apertura.save()

        # Actualizar estado de la caja
        apertura.caja.estado_actual = 'cerrada'
        apertura.caja.save()

        return Response({'message': 'Apertura anulada exitosamente'})

    @action(detail=False, methods=['get'], url_path='resumen-general', pagination_class=None)
    def resumen_general(self, request):
        """Resumen estadístico de aperturas"""
        from decimal import Decimal

        total = AperturaCaja.objects.count()
        activas = AperturaCaja.objects.filter(activo=True).count()
        inactivas = AperturaCaja.objects.filter(activo=False).count()
        abiertas = AperturaCaja.objects.filter(esta_abierta=True, activo=True).count()
        cerradas = AperturaCaja.objects.filter(esta_abierta=False, activo=True).count()

        # Monto total inicial en aperturas abiertas
        monto_total_inicial = AperturaCaja.objects.filter(
            esta_abierta=True,
            activo=True
        ).aggregate(total=Sum('monto_inicial'))['total'] or Decimal('0')

        # Total de movimientos en aperturas activas
        total_movimientos = MovimientoCaja.objects.filter(
            apertura_caja__esta_abierta=True,
            apertura_caja__activo=True,
            activo=True
        ).count()

        ultimos_30_dias = timezone.now() - timedelta(days=30)
        nuevas = AperturaCaja.objects.filter(fecha_hora_apertura__gte=ultimos_30_dias).count()

        # Hoy
        hoy = timezone.now().date()
        aperturas_hoy = AperturaCaja.objects.filter(
            fecha_hora_apertura__date=hoy
        ).count()

        data = [
            {'texto': 'Total Aperturas', 'valor': str(total)},
            {'texto': 'Activas', 'valor': str(activas)},
            {'texto': 'Inactivas', 'valor': str(inactivas)},
            {'texto': 'Abiertas Ahora', 'valor': str(abiertas)},
            {'texto': 'Cerradas', 'valor': str(cerradas)},
            {'texto': 'Monto Inicial Total (Abiertas)', 'valor': f'Gs {monto_total_inicial:,.0f}'},
            {'texto': 'Movimientos en Aperturas Activas', 'valor': str(total_movimientos)},
            {'texto': 'Aperturas Hoy', 'valor': str(aperturas_hoy)},
            {'texto': 'Nuevas últimos 30 días', 'valor': str(nuevas)},
        ]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='tengo-caja-abierta', pagination_class=None)
    def tengo_caja_abierta(self, request):
        """
        Verifica si el usuario autenticado tiene una caja abierta.
        Incluye información sobre el saldo actual y movimientos.

        GET /api/arqueo-caja/aperturas/tengo-caja-abierta/

        Returns:
            - tiene_caja_abierta: boolean
            - apertura_id: ID de la apertura (si existe)
            - caja_nombre: Nombre de la caja (si existe)
            - fecha_hora_apertura: Fecha y hora de apertura (si existe)
            - monto_inicial: Monto inicial en guaraníes (si existe)
            - monto_inicial_alternativo: Monto inicial en USD (si existe)
            - saldo_actual: Saldo actual de la caja
            - total_ingresos: Total de ingresos registrados
            - total_egresos: Total de egresos registrados
            - cantidad_movimientos: Cantidad de movimientos registrados
            - notificacion: Mensaje informativo sobre el estado de la caja
        """
        from .services import obtener_caja_abierta_por_usuario
        from decimal import Decimal
        from django.db.models import Sum

        try:
            empleado = request.user.empleado
        except AttributeError:
            return Response({
                'tiene_caja_abierta': False,
                'error': 'Usuario no tiene empleado asociado'
            })

        apertura = obtener_caja_abierta_por_usuario(empleado)

        if apertura:
            # Calcular totales de movimientos
            movimientos_activos = apertura.movimientos.filter(activo=True)

            total_ingresos = movimientos_activos.filter(
                tipo_movimiento='ingreso'
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

            total_egresos = movimientos_activos.filter(
                tipo_movimiento='egreso'
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

            cantidad_movimientos = movimientos_activos.count()

            # Obtener saldo actual de la caja
            saldo_actual = apertura.caja.saldo_actual

            # Calcular monto inicial alternativo (convertir de PYG a USD)
            monto_inicial_alternativo = None
            try:
                from apps.moneda.models import Moneda, CotizacionMoneda

                # Obtener la moneda USD
                moneda_usd = Moneda.objects.get(codigo='USD', activo=True)

                # Obtener cotización vigente
                cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)

                if cotizacion:
                    # Convertir de PYG a USD (dividir por la cotización)
                    monto_pyg = Decimal(str(apertura.monto_inicial))
                    valor_cotizacion = Decimal(str(cotizacion.valor_en_guaranies))

                    if valor_cotizacion != 0:
                        monto_usd = monto_pyg / valor_cotizacion
                        monto_inicial_alternativo = round(monto_usd, 2)
            except Exception:
                # Si hay error al obtener cotización, monto_inicial_alternativo será None
                pass

            # Generar notificación informativa
            notificacion = None
            if cantidad_movimientos == 0:
                notificacion = "Caja abierta sin movimientos. Los pagos registrados se agregarán automáticamente."
            else:
                notificacion = f"Caja activa con {cantidad_movimientos} movimiento(s) registrado(s)."

            return Response({
                'tiene_caja_abierta': True,
                'apertura_id': apertura.id,
                'codigo_apertura': apertura.codigo_apertura,
                'caja_id': apertura.caja.id,
                'caja_nombre': apertura.caja.nombre,
                'fecha_hora_apertura': apertura.fecha_hora_apertura,
                'monto_inicial': apertura.monto_inicial,
                'monto_inicial_alternativo': monto_inicial_alternativo,
                'saldo_actual': saldo_actual,
                'total_ingresos': total_ingresos,
                'total_egresos': total_egresos,
                'cantidad_movimientos': cantidad_movimientos,
                'notificacion': notificacion
            })
        else:
            return Response({
                'tiene_caja_abierta': False,
                'notificacion': 'No tienes una caja abierta. Los pagos se registrarán sin movimiento de caja.'
            })

    @action(detail=True, methods=['get'], url_path='pdf')
    def descargar_pdf(self, request, pk=None):
        """
        Genera y descarga el PDF de la apertura de caja.

        GET /api/arqueo-caja/aperturas/{id}/pdf/

        Returns:
            PDF file con los datos de la apertura de caja
        """
        from django.http import HttpResponse

        apertura = self.get_object()

        # Generar PDF
        pdf_buffer = apertura.generar_pdf()

        # Crear respuesta HTTP con el PDF
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="apertura_{apertura.codigo_apertura}.pdf"'

        return response


class MovimientoCajaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de movimientos de caja.

    Acciones personalizadas:
    - GET /movimientos/estadisticas/ - Estadísticas por tipo y método de pago

    Filtros personalizados:
    - usuario_id: Filtra por ID del usuario (convierte a empleado automáticamente)
    """
    queryset = MovimientoCaja.objects.all().select_related(
        'apertura_caja', 'apertura_caja__caja', 'usuario_registro',
        'usuario_registro__persona', 'comprobante'
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'apertura_caja', 'tipo_movimiento', 'concepto', 'metodo_pago',
        'usuario_registro', 'comprobante', 'activo'
    ]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtro personalizado por usuario_id
        usuario_id = self.request.query_params.get('usuario_id')
        if usuario_id:
            try:
                from apps.usuario.models import Usuario
                usuario = Usuario.objects.get(id=usuario_id)
                if usuario.empleado:
                    queryset = queryset.filter(usuario_registro=usuario.empleado)
                else:
                    # Si el usuario no tiene empleado asociado, no devolver resultados
                    queryset = queryset.none()
            except Usuario.DoesNotExist:
                queryset = queryset.none()

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return MovimientoCajaListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return MovimientoCajaCreateSerializer
        return MovimientoCajaDetailSerializer

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de movimientos por tipo y método de pago"""
        # Filtros opcionales
        apertura_id = request.query_params.get('apertura_caja')
        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')

        queryset = self.queryset.filter(activo=True)

        if apertura_id:
            queryset = queryset.filter(apertura_caja_id=apertura_id)

        if fecha_desde:
            queryset = queryset.filter(fecha_hora_movimiento__date__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha_hora_movimiento__date__lte=fecha_hasta)

        # Estadísticas
        por_tipo = queryset.values('tipo_movimiento').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        )

        por_metodo = queryset.values('metodo_pago').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        )

        por_concepto = queryset.values('concepto', 'tipo_movimiento').annotate(
            total=Sum('monto'),
            cantidad=Count('id')
        )

        return Response({
            'por_tipo': list(por_tipo),
            'por_metodo': list(por_metodo),
            'por_concepto': list(por_concepto)
        })

    @action(detail=False, methods=['get'], url_path='resumen-general', pagination_class=None)
    def resumen_general(self, request):
        """
        Resumen estadístico general de movimientos de caja.
        Similar al formato de resumen-general de otras vistas.

        GET /api/arqueo-caja/movimientos/resumen-general/
        """
        from decimal import Decimal

        # Contadores generales
        total = MovimientoCaja.objects.filter(activo=True).count()
        inactivos = MovimientoCaja.objects.filter(activo=False).count()
        ingresos_count = MovimientoCaja.objects.filter(
            tipo_movimiento='ingreso',
            activo=True
        ).count()
        egresos_count = MovimientoCaja.objects.filter(
            tipo_movimiento='egreso',
            activo=True
        ).count()

        # Montos totales
        total_ingresos = MovimientoCaja.objects.filter(
            tipo_movimiento='ingreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        total_egresos = MovimientoCaja.objects.filter(
            tipo_movimiento='egreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        # Balance neto
        balance_neto = total_ingresos - total_egresos

        # Por método de pago (ingresos)
        efectivo = MovimientoCaja.objects.filter(
            metodo_pago='efectivo',
            tipo_movimiento='ingreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        tarjetas = MovimientoCaja.objects.filter(
            metodo_pago__in=['tarjeta_debito', 'tarjeta_credito'],
            tipo_movimiento='ingreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        transferencias = MovimientoCaja.objects.filter(
            metodo_pago='transferencia',
            tipo_movimiento='ingreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        # Movimientos con comprobante asociado
        con_comprobante = MovimientoCaja.objects.filter(
            comprobante__isnull=False,
            activo=True
        ).count()

        sin_comprobante = MovimientoCaja.objects.filter(
            comprobante__isnull=True,
            activo=True
        ).count()

        # Movimientos de hoy
        hoy = timezone.now().date()
        movimientos_hoy = MovimientoCaja.objects.filter(
            fecha_hora_movimiento__date=hoy,
            activo=True
        ).count()

        ingresos_hoy = MovimientoCaja.objects.filter(
            fecha_hora_movimiento__date=hoy,
            tipo_movimiento='ingreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        egresos_hoy = MovimientoCaja.objects.filter(
            fecha_hora_movimiento__date=hoy,
            tipo_movimiento='egreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        # Últimos 30 días
        ultimos_30_dias = timezone.now() - timedelta(days=30)
        nuevos_30_dias = MovimientoCaja.objects.filter(
            fecha_hora_movimiento__gte=ultimos_30_dias,
            activo=True
        ).count()

        ingresos_30_dias = MovimientoCaja.objects.filter(
            fecha_hora_movimiento__gte=ultimos_30_dias,
            tipo_movimiento='ingreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        data = [
            {'texto': 'Total Movimientos', 'valor': str(total)},
            {'texto': 'Movimientos Inactivos/Anulados', 'valor': str(inactivos)},
            {'texto': 'Total Ingresos (Cantidad)', 'valor': str(ingresos_count)},
            {'texto': 'Total Egresos (Cantidad)', 'valor': str(egresos_count)},
            {'texto': 'Total Ingresos (Monto)', 'valor': f'Gs {total_ingresos:,.0f}'},
            {'texto': 'Total Egresos (Monto)', 'valor': f'Gs {total_egresos:,.0f}'},
            {'texto': 'Balance Neto', 'valor': f'Gs {balance_neto:,.0f}'},
            {'texto': 'Ingresos en Efectivo', 'valor': f'Gs {efectivo:,.0f}'},
            {'texto': 'Ingresos con Tarjetas', 'valor': f'Gs {tarjetas:,.0f}'},
            {'texto': 'Ingresos por Transferencia', 'valor': f'Gs {transferencias:,.0f}'},
            {'texto': 'Con Comprobante de Pago', 'valor': str(con_comprobante)},
            {'texto': 'Sin Comprobante (Manuales)', 'valor': str(sin_comprobante)},
            {'texto': 'Movimientos Hoy', 'valor': str(movimientos_hoy)},
            {'texto': 'Ingresos Hoy', 'valor': f'Gs {ingresos_hoy:,.0f}'},
            {'texto': 'Egresos Hoy', 'valor': f'Gs {egresos_hoy:,.0f}'},
            {'texto': 'Nuevos últimos 30 días', 'valor': str(nuevos_30_dias)},
            {'texto': 'Ingresos últimos 30 días', 'valor': f'Gs {ingresos_30_dias:,.0f}'},
        ]
        return Response(data)


class CierreCajaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de cierres de caja.

    Acciones personalizadas:
    - POST /cierres/{id}/calcular_totales/ - Recalcular totales desde movimientos
    - POST /cierres/{id}/registrar_arqueo/ - Registrar conteo físico
    - POST /cierres/{id}/autorizar/ - Autorizar cierre con diferencia
    - GET /cierres/{id}/resumen/ - Resumen detallado del cierre
    """
    queryset = CierreCaja.objects.all().select_related(
        'apertura_caja', 'apertura_caja__caja', 'apertura_caja__responsable',
        'apertura_caja__responsable__persona', 'autorizado_por',
        'autorizado_por__persona'
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['apertura_caja', 'requiere_autorizacion', 'activo']
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return CierreCajaListSerializer
        elif self.action in ['create']:
            return CierreCajaCreateSerializer
        return CierreCajaDetailSerializer

    @action(detail=True, methods=['post'])
    def calcular_totales(self, request, pk=None):
        """Recalcular totales desde los movimientos"""
        cierre = self.get_object()
        cierre.calcular_totales_desde_movimientos()

        return Response({
            'message': 'Totales recalculados exitosamente',
            'cierre': CierreCajaDetailSerializer(cierre).data
        })

    @action(detail=True, methods=['post'])
    def registrar_arqueo(self, request, pk=None):
        """Registrar el conteo físico del efectivo"""
        cierre = self.get_object()

        saldo_real = request.data.get('saldo_real_efectivo')
        detalle_billetes = request.data.get('detalle_billetes')
        justificacion = request.data.get('justificacion_diferencia')

        if saldo_real is None:
            return Response(
                {'error': 'El campo saldo_real_efectivo es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cierre.saldo_real_efectivo = saldo_real
        if detalle_billetes:
            cierre.detalle_billetes = detalle_billetes
        if justificacion:
            cierre.justificacion_diferencia = justificacion

        cierre.save()

        return Response({
            'message': 'Arqueo registrado exitosamente',
            'cierre': CierreCajaDetailSerializer(cierre).data
        })

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        """Autorizar un cierre que requiere autorización por diferencia"""
        cierre = self.get_object()

        serializer = CierreCajaAutorizarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        autorizado_por = serializer.validated_data['autorizado_por']
        observaciones = serializer.validated_data.get('observaciones', '')

        # Autorizar
        cierre.autorizado_por = autorizado_por
        cierre.fecha_autorizacion = timezone.now()

        if observaciones:
            cierre.observaciones_cierre = (
                f"{cierre.observaciones_cierre or ''}\n\n"
                f"Autorización: {observaciones}"
            )

        cierre.save()

        return Response({
            'message': 'Cierre autorizado exitosamente',
            'cierre': CierreCajaDetailSerializer(cierre).data
        })

    @action(detail=True, methods=['get'])
    def resumen(self, request, pk=None):
        """Obtener resumen detallado del cierre"""
        cierre = self.get_object()
        resumen = cierre.generar_resumen()

        return Response(resumen)

    @action(detail=False, methods=['post'], url_path='cerrar-simple')
    def cerrar_simple(self, request):
        """
        Endpoint simplificado para cerrar caja.

        POST /api/arqueo-caja/cierres/cerrar-simple/

        Body:
        {
            "apertura_caja": integer,
            "saldo_real_efectivo": decimal,
            "observaciones": string (optional)
        }

        Response:
        {
            "codigo_cierre": string,
            "fecha_cierre": datetime,
            "monto_inicial": decimal,
            "total_vendido": decimal,
            "total_gastado": decimal,
            "saldo_teorico": decimal,
            "saldo_real": decimal,
            "diferencia": decimal,
            "diferencia_porcentaje": decimal,
            "requiere_autorizacion": boolean,
            "estado": string
        }
        """
        from decimal import Decimal

        # Validar datos de entrada
        serializer = CierreCajaSimpleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Obtener datos validados
        apertura = serializer.validated_data['apertura_caja']
        saldo_real_efectivo = serializer.validated_data['saldo_real_efectivo']
        observaciones = serializer.validated_data.get('observaciones', '')

        # Crear el cierre
        cierre = CierreCaja.objects.create(
            apertura_caja=apertura,
            saldo_real_efectivo=saldo_real_efectivo,
            observaciones_cierre=observaciones
        )

        # Calcular totales automáticamente
        cierre.calcular_totales_desde_movimientos()

        # Recargar para obtener los valores actualizados
        cierre.refresh_from_db()

        # Determinar estado
        estado = "completado"
        if cierre.requiere_autorizacion:
            estado = "pendiente_autorizacion"

        # Calcular total vendido (ingresos) y total gastado (egresos)
        total_vendido = (
            cierre.total_efectivo +
            cierre.total_tarjetas +
            cierre.total_transferencias +
            cierre.total_cheques +
            cierre.total_otros_ingresos
        )
        total_gastado = cierre.total_egresos

        # Preparar respuesta
        response_data = {
            'id': cierre.id,  # ID del cierre para poder descargar el PDF
            'codigo_cierre': cierre.codigo_cierre,
            'fecha_cierre': cierre.fecha_hora_cierre,
            'monto_inicial': cierre.apertura_caja.monto_inicial,
            'total_vendido': total_vendido,
            'total_gastado': total_gastado,
            'saldo_teorico': cierre.saldo_teorico_efectivo,
            'saldo_real': cierre.saldo_real_efectivo,
            'diferencia': cierre.diferencia_efectivo,
            'diferencia_porcentaje': cierre.diferencia_porcentaje,
            'requiere_autorizacion': cierre.requiere_autorizacion,
            'estado': estado,
            'pdf_url': f'/api/arqueo-caja/cierres/{cierre.id}/pdf/'  # URL para descargar el PDF
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='resumen-general', pagination_class=None)
    def resumen_general(self, request):
        """Resumen estadístico de todos los cierres"""
        from decimal import Decimal

        total = CierreCaja.objects.filter(activo=True).count()
        con_diferencia = CierreCaja.objects.filter(
            diferencia_efectivo__gt=0,
            activo=True
        ).count() + CierreCaja.objects.filter(
            diferencia_efectivo__lt=0,
            activo=True
        ).count()
        sin_diferencia = CierreCaja.objects.filter(
            diferencia_efectivo=0,
            activo=True
        ).count()
        requieren_autorizacion = CierreCaja.objects.filter(
            requiere_autorizacion=True,
            activo=True
        ).count()
        autorizados = CierreCaja.objects.filter(
            requiere_autorizacion=True,
            autorizado_por__isnull=False,
            activo=True
        ).count()

        # Diferencia total
        diferencia_total = CierreCaja.objects.filter(
            activo=True
        ).aggregate(total=Sum('diferencia_efectivo'))['total'] or Decimal('0')

        # Hoy
        hoy = timezone.now().date()
        cierres_hoy = CierreCaja.objects.filter(
            fecha_hora_cierre__date=hoy,
            activo=True
        ).count()

        ultimos_30_dias = timezone.now() - timedelta(days=30)
        nuevos = CierreCaja.objects.filter(
            fecha_hora_cierre__gte=ultimos_30_dias,
            activo=True
        ).count()

        # Promedio de diferencia
        promedio_diferencia = Decimal('0')
        if total > 0:
            promedio_diferencia = diferencia_total / total

        data = [
            {'texto': 'Total Cierres', 'valor': str(total)},
            {'texto': 'Con Diferencias', 'valor': str(con_diferencia)},
            {'texto': 'Sin Diferencias', 'valor': str(sin_diferencia)},
            {'texto': 'Requieren Autorización', 'valor': str(requieren_autorizacion)},
            {'texto': 'Autorizados', 'valor': str(autorizados)},
            {'texto': 'Diferencia Total Acumulada', 'valor': f'Gs {diferencia_total:,.0f}'},
            {'texto': 'Promedio Diferencia por Cierre', 'valor': f'Gs {promedio_diferencia:,.0f}'},
            {'texto': 'Cierres Hoy', 'valor': str(cierres_hoy)},
            {'texto': 'Nuevos últimos 30 días', 'valor': str(nuevos)},
        ]
        return Response(data)

    @action(detail=True, methods=['get'], url_path='pdf')
    def descargar_pdf(self, request, pk=None):
        """
        Genera y descarga el PDF del cierre de caja.
        Incluye todos los datos del cierre y movimientos del responsable.

        GET /api/arqueo-caja/cierres/{id}/pdf/

        Returns:
            PDF file con los datos completos del cierre de caja
        """
        from django.http import HttpResponse

        cierre = self.get_object()

        # Generar PDF
        pdf_buffer = cierre.generar_pdf()

        # Crear respuesta HTTP con el PDF
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="cierre_{cierre.codigo_cierre}.pdf"'

        return response

    @action(detail=False, methods=['post'], url_path='cerrar-cajas-abiertas')
    def cerrar_cajas_abiertas(self, request):
        """
        Endpoint administrativo para cerrar todas las cajas que quedaron abiertas.
        Útil para resetear el sistema o corregir aperturas huérfanas.

        POST /api/arqueo-caja/cierres/cerrar-cajas-abiertas/

        Response:
        {
            "message": "Se cerraron X cajas exitosamente",
            "cajas_cerradas": [
                {
                    "caja_nombre": "Caja 1",
                    "codigo_cierre": "CIE-2025-0001",
                    "apertura_codigo": "APR-2025-0001",
                    "monto_inicial": 1000000.00,
                    "saldo_teorico": 1000000.00
                },
                ...
            ]
        }
        """
        from decimal import Decimal
        from django.db import transaction

        # Buscar todas las aperturas que están abiertas
        aperturas_abiertas = AperturaCaja.objects.filter(
            esta_abierta=True,
            activo=True
        ).select_related('caja', 'responsable', 'responsable__persona')

        if not aperturas_abiertas.exists():
            return Response({
                'message': 'No hay cajas abiertas para cerrar',
                'cajas_cerradas': []
            }, status=status.HTTP_200_OK)

        cajas_cerradas = []
        errores = []

        # Procesar cada apertura
        with transaction.atomic():
            for apertura in aperturas_abiertas:
                try:
                    # Crear el cierre con saldo real = saldo teórico (asumimos que está correcto)
                    # Ya que estamos haciendo un cierre administrativo/automático
                    cierre = CierreCaja.objects.create(
                        apertura_caja=apertura,
                        saldo_real_efectivo=apertura.caja.saldo_actual,
                        observaciones_cierre="Cierre automático - Reseteo de sistema"
                    )

                    # Calcular totales automáticamente
                    cierre.calcular_totales_desde_movimientos()

                    # Recargar para obtener los valores actualizados
                    cierre.refresh_from_db()

                    cajas_cerradas.append({
                        'caja_id': apertura.caja.id,
                        'caja_nombre': apertura.caja.nombre,
                        'codigo_cierre': cierre.codigo_cierre,
                        'apertura_codigo': apertura.codigo_apertura,
                        'monto_inicial': str(apertura.monto_inicial),
                        'saldo_teorico': str(cierre.saldo_teorico_efectivo) if cierre.saldo_teorico_efectivo else '0.00',
                        'saldo_real': str(cierre.saldo_real_efectivo) if cierre.saldo_real_efectivo else '0.00',
                        'diferencia': str(cierre.diferencia_efectivo) if cierre.diferencia_efectivo else '0.00'
                    })

                except Exception as e:
                    errores.append({
                        'caja_nombre': apertura.caja.nombre,
                        'apertura_codigo': apertura.codigo_apertura,
                        'error': str(e)
                    })

        # Preparar respuesta
        response_data = {
            'message': f'Se cerraron {len(cajas_cerradas)} cajas exitosamente',
            'total_cerradas': len(cajas_cerradas),
            'total_errores': len(errores),
            'cajas_cerradas': cajas_cerradas
        }

        if errores:
            response_data['errores'] = errores

        return Response(response_data, status=status.HTTP_200_OK)
