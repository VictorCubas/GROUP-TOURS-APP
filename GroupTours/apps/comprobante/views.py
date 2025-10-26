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

    Los vouchers se generan automáticamente cuando una reserva se confirma.
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
        - reserva_id: filtrar por reserva
        - activo: filtrar por estado activo (true/false)
        """
        queryset = Voucher.objects.select_related(
            'reserva',
            'reserva__titular',
            'reserva__paquete',
            'reserva__salida',
            'reserva__habitacion',
            'reserva__habitacion__hotel'
        )

        reserva_id = self.request.query_params.get('reserva_id', None)
        if reserva_id:
            queryset = queryset.filter(reserva_id=reserva_id)

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


# ViewSet anidado: Voucher de una reserva específica
class ReservaVoucherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet anidado para obtener el voucher de una reserva específica.

    URL: /api/reservas/{reserva_id}/voucher/

    Como es OneToOne, siempre habrá máximo un voucher por reserva.
    """
    serializer_class = VoucherSerializer
    permission_classes = []

    def get_queryset(self):
        """Obtener voucher de la reserva especificada en la URL"""
        reserva_id = self.kwargs.get('reserva_pk')
        return Voucher.objects.filter(reserva_id=reserva_id)

    def list(self, request, *args, **kwargs):
        """
        Retornar el voucher directamente (no como lista) si existe.
        """
        queryset = self.get_queryset()
        voucher = queryset.first()

        if not voucher:
            return Response(
                {'message': 'Esta reserva no tiene voucher generado aún'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(voucher)
        return Response(serializer.data)
