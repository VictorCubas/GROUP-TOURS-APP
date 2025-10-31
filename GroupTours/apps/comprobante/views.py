from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import ComprobantePago, ComprobantePagoDistribucion, Voucher
from .serializers import (
    ComprobantePagoSerializer,
    ComprobantePagoResumenSerializer,
    ComprobantePagoDistribucionSerializer,
    VoucherSerializer,
    VoucherResumenSerializer,
)
from apps.reserva.models import Reserva


class ComprobantePagoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de comprobantes de pago.

    Endpoints:
    - GET /api/comprobantes/ - Listar todos los comprobantes
    - GET /api/comprobantes/{id}/ - Obtener detalle de un comprobante
    - POST /api/comprobantes/ - Crear nuevo comprobante con distribuciones
    - PUT /api/comprobantes/{id}/ - Actualizar comprobante
    - DELETE /api/comprobantes/{id}/ - Eliminar comprobante
    - POST /api/comprobantes/{id}/anular/ - Anular un comprobante
    """
    queryset = ComprobantePago.objects.all()
    permission_classes = []

    def get_serializer_class(self):
        """Usar serializer simplificado para listado"""
        if self.action == 'list':
            return ComprobantePagoResumenSerializer
        return ComprobantePagoSerializer

    def get_queryset(self):
        """
        Filtrar comprobantes por query params.

        Query params disponibles:
        - reserva_id: filtrar por reserva
        - activo: filtrar por estado activo (true/false)
        - tipo: filtrar por tipo de comprobante
        """
        queryset = ComprobantePago.objects.select_related(
            'reserva', 'empleado', 'empleado__persona'
        ).prefetch_related('distribuciones')

        # Filtros opcionales
        reserva_id = self.request.query_params.get('reserva_id', None)
        if reserva_id:
            queryset = queryset.filter(reserva_id=reserva_id)

        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() == 'true'
            queryset = queryset.filter(activo=activo_bool)

        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        return queryset.order_by('-fecha_pago')

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """
        Anular un comprobante de pago.

        Body (opcional):
        {
            "motivo": "Razón de la anulación"
        }
        """
        comprobante = self.get_object()

        if not comprobante.activo:
            return Response(
                {'error': 'El comprobante ya está anulado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        motivo = request.data.get('motivo', None)
        comprobante.anular(motivo=motivo)

        return Response({
            'message': f'Comprobante {comprobante.numero_comprobante} anulado exitosamente',
            'numero_comprobante': comprobante.numero_comprobante,
            'activo': comprobante.activo,
        })

    @action(detail=True, methods=['get'], url_path='descargar-pdf')
    def descargar_pdf(self, request, pk=None):
        """
        GET /api/comprobantes/{id}/descargar-pdf/

        Genera y descarga el PDF del comprobante de pago.

        Si el PDF ya fue generado previamente, retorna el archivo existente.
        Si no existe, lo genera automáticamente.

        Query params opcionales:
        - regenerar=true : Fuerza la regeneración del PDF incluso si ya existe

        Respuesta:
        - Content-Type: application/pdf
        - Content-Disposition: attachment; filename="comprobante_CPG-2025-0001.pdf"
        """
        from django.http import FileResponse, HttpResponse
        import os

        comprobante = self.get_object()
        regenerar = request.query_params.get('regenerar', 'false').lower() == 'true'

        # Si no existe PDF o se solicita regenerar
        if not comprobante.pdf_generado or regenerar:
            try:
                comprobante.generar_pdf()
                comprobante.save()
            except Exception as e:
                return Response(
                    {'error': f'Error al generar PDF: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Verificar que el archivo existe
        if not comprobante.pdf_generado:
            return Response(
                {'error': 'No se pudo generar el PDF'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Verificar que el archivo físico existe
        pdf_path = comprobante.pdf_generado.path
        if not os.path.exists(pdf_path):
            # Intentar regenerar si el archivo fue eliminado
            try:
                comprobante.generar_pdf()
                comprobante.save()
                pdf_path = comprobante.pdf_generado.path
            except Exception as e:
                return Response(
                    {'error': f'El archivo PDF no existe y no se pudo regenerar: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Retornar el archivo PDF
        try:
            response = FileResponse(
                open(pdf_path, 'rb'),
                content_type='application/pdf'
            )
            filename = f'comprobante_{comprobante.numero_comprobante}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {'error': f'Error al leer el archivo PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ComprobantePagoDistribucionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de distribuciones de pago.

    Normalmente se crean junto con el ComprobantePago,
    pero este endpoint permite consultas y actualizaciones individuales.
    """
    queryset = ComprobantePagoDistribucion.objects.all()
    serializer_class = ComprobantePagoDistribucionSerializer
    permission_classes = []

    def get_queryset(self):
        """
        Filtrar distribuciones por query params.

        Query params disponibles:
        - comprobante_id: filtrar por comprobante
        - pasajero_id: filtrar por pasajero
        """
        queryset = ComprobantePagoDistribucion.objects.select_related(
            'comprobante', 'pasajero', 'pasajero__persona'
        )

        comprobante_id = self.request.query_params.get('comprobante_id', None)
        if comprobante_id:
            queryset = queryset.filter(comprobante_id=comprobante_id)

        pasajero_id = self.request.query_params.get('pasajero_id', None)
        if pasajero_id:
            queryset = queryset.filter(pasajero_id=pasajero_id)

        return queryset


class VoucherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consulta de vouchers.

    Los vouchers se generan automáticamente para cada pasajero cuando cumple las condiciones:
    1. Tiene datos reales cargados (por_asignar=False)
    2. Ha pagado el 100% de su precio asignado (esta_totalmente_pagado=True)

    Este endpoint es principalmente de solo lectura.

    Endpoints:
    - GET /api/vouchers/ - Listar todos los vouchers
    - GET /api/vouchers/{id}/ - Obtener detalle de un voucher
    - POST /api/vouchers/{id}/regenerar_qr/ - Regenerar código QR
    """
    queryset = Voucher.objects.all()
    permission_classes = []

    def get_serializer_class(self):
        """Usar serializer simplificado para listado"""
        if self.action == 'list':
            return VoucherResumenSerializer
        return VoucherSerializer

    def get_queryset(self):
        """
        Filtrar vouchers por query params.

        Query params disponibles:
        - reserva_id: filtrar por reserva (muestra todos los vouchers de pasajeros de esa reserva)
        - pasajero_id: filtrar por pasajero específico
        - activo: filtrar por estado activo (true/false)
        """
        queryset = Voucher.objects.select_related(
            'pasajero',
            'pasajero__persona',
            'pasajero__reserva',
            'pasajero__reserva__titular',
            'pasajero__reserva__paquete',
            'pasajero__reserva__salida',
            'pasajero__reserva__habitacion',
            'pasajero__reserva__habitacion__hotel'
        )

        reserva_id = self.request.query_params.get('reserva_id', None)
        if reserva_id:
            queryset = queryset.filter(pasajero__reserva_id=reserva_id)

        pasajero_id = self.request.query_params.get('pasajero_id', None)
        if pasajero_id:
            queryset = queryset.filter(pasajero_id=pasajero_id)

        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() == 'true'
            queryset = queryset.filter(activo=activo_bool)

        return queryset.order_by('-fecha_emision')

    @action(detail=True, methods=['post'])
    def regenerar_qr(self, request, pk=None):
        """
        Regenerar el código QR de un voucher.

        Útil si el archivo se perdió o se quiere actualizar.
        """
        voucher = self.get_object()

        try:
            voucher.generar_qr()
            voucher.save()

            return Response({
                'message': f'Código QR regenerado para voucher {voucher.codigo_voucher}',
                'qr_code': voucher.qr_code.url if voucher.qr_code else None
            })
        except Exception as e:
            return Response(
                {'error': f'Error al generar código QR: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='descargar-pdf')
    def descargar_pdf(self, request, pk=None):
        """
        GET /api/vouchers/{id}/descargar-pdf/

        Genera y descarga el PDF del voucher con toda la información del pasajero,
        reserva, paquete, salida, hotel y servicios incluidos.

        Si el PDF ya fue generado previamente, retorna el archivo existente.
        Si no existe, lo genera automáticamente.

        Query params opcionales:
        - regenerar=true : Fuerza la regeneración del PDF incluso si ya existe

        Respuesta:
        - Content-Type: application/pdf
        - Content-Disposition: attachment; filename="voucher_RSV-2025-0001-PAX-003-VOUCHER.pdf"
        """
        from django.http import FileResponse
        import os

        voucher = self.get_object()
        regenerar = request.query_params.get('regenerar', 'false').lower() == 'true'

        # Si no existe PDF o se solicita regenerar
        if not voucher.pdf_generado or regenerar:
            try:
                voucher.generar_pdf()
                voucher.save()
            except Exception as e:
                return Response(
                    {'error': f'Error al generar PDF: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Verificar que el archivo existe
        if not voucher.pdf_generado:
            return Response(
                {'error': 'No se pudo generar el PDF'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Verificar que el archivo físico existe
        pdf_path = voucher.pdf_generado.path
        if not os.path.exists(pdf_path):
            # Intentar regenerar si el archivo fue eliminado
            try:
                voucher.generar_pdf()
                voucher.save()
                pdf_path = voucher.pdf_generado.path
            except Exception as e:
                return Response(
                    {'error': f'El archivo PDF no existe y no se pudo regenerar: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Retornar el archivo PDF
        try:
            response = FileResponse(
                open(pdf_path, 'rb'),
                content_type='application/pdf'
            )
            filename = f'voucher_{voucher.codigo_voucher}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {'error': f'Error al leer el archivo PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ViewSet anidado: Comprobantes de una reserva específica
class ReservaComprobantesViewSet(viewsets.ModelViewSet):
    """
    ViewSet anidado para gestionar comprobantes de una reserva específica.

    URL: /api/reservas/{reserva_id}/comprobantes/

    Permite crear comprobantes directamente bajo una reserva.
    """
    serializer_class = ComprobantePagoSerializer
    permission_classes = []

    def get_queryset(self):
        """Obtener comprobantes de la reserva especificada en la URL"""
        reserva_id = self.kwargs.get('reserva_pk')
        return ComprobantePago.objects.filter(reserva_id=reserva_id).order_by('-fecha_pago')

    def perform_create(self, serializer):
        """Asignar automáticamente la reserva al crear el comprobante"""
        reserva_id = self.kwargs.get('reserva_pk')
        reserva = get_object_or_404(Reserva, pk=reserva_id)
        serializer.save(reserva=reserva)


# ViewSet anidado: Vouchers de una reserva específica
class ReservaVoucherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet anidado para obtener los vouchers de una reserva específica.

    URL: /api/reservas/{reserva_id}/vouchers/

    Como ahora hay un voucher por pasajero, puede haber múltiples vouchers por reserva.
    Solo se generan vouchers para pasajeros que:
    1. Tienen datos reales (por_asignar=False)
    2. Han pagado el 100% (esta_totalmente_pagado=True)
    """
    serializer_class = VoucherSerializer
    permission_classes = []

    def get_queryset(self):
        """Obtener vouchers de todos los pasajeros de la reserva especificada en la URL"""
        reserva_id = self.kwargs.get('reserva_pk')
        return Voucher.objects.filter(pasajero__reserva_id=reserva_id).select_related(
            'pasajero',
            'pasajero__persona',
            'pasajero__reserva',
            'pasajero__reserva__paquete',
            'pasajero__reserva__salida',
            'pasajero__reserva__habitacion',
            'pasajero__reserva__habitacion__hotel'
        ).order_by('pasajero__es_titular', 'pasajero__id')  # Titular primero

    def list(self, request, *args, **kwargs):
        """
        Retornar todos los vouchers de la reserva.
        """
        queryset = self.get_queryset()

        if not queryset.exists():
            return Response(
                {
                    'message': 'Esta reserva no tiene vouchers generados aún',
                    'info': 'Los vouchers se generan automáticamente cuando cada pasajero tiene datos reales y paga el 100%'
                },
                status=status.HTTP_200_OK,
                # Cambiar a 200 en lugar de 404 porque es una situación normal
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'vouchers': serializer.data
        })
