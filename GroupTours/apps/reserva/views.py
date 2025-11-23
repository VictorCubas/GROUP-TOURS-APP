from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Reserva, ReservaServiciosAdicionales, Pasajero
from .serializers import (
    ReservaSerializer,
    ReservaServiciosAdicionalesSerializer,
    ReservaServiciosAdicionalesCreateSerializer,
    PasajeroSerializer,
    PasajeroEstadoCuentaSerializer,
    ReservaDetalleSerializer,
    ReservaListadoSerializer
)
from .filters import ReservaFilter
from .services import (
    obtener_detalle_reserva,
    obtener_resumen_reserva,
    obtener_pasajeros_reserva,
    obtener_comprobantes_reserva,
    obtener_servicios_reserva,
    distribuir_devolucion_en_pasajeros,
)
from django.core.exceptions import ObjectDoesNotExist, ValidationError


def obtener_o_crear_pasajero_pendiente(reserva, sufijo=""):
    """
    Obtiene o crea un pasajero "pendiente" para una reserva.
    Este pasajero se usa para asignar pagos cuando aún no se han cargado todos los pasajeros.

    El pasajero pendiente usa datos de contacto del TITULAR (email, teléfono) para que
    las comunicaciones lleguen correctamente, pero con nombre genérico "Por Asignar X".

    Args:
        reserva: Instancia de Reserva
        sufijo: Sufijo para diferenciar múltiples pasajeros pendientes
                "" -> documento_titular + "_PEND" / "Por Asignar"
                "1" -> documento_titular + "_PEND_1" / "Por Asignar 1"
                "2" -> documento_titular + "_PEND_2" / "Por Asignar 2"

    Returns:
        Pasajero: Instancia del pasajero pendiente para esta reserva

    Raises:
        ValueError: Si la reserva no tiene titular asignado
    """
    from apps.persona.models import PersonaFisica

    # Validar que la reserva tenga titular
    if not reserva.titular:
        raise ValueError('No se puede crear pasajero pendiente sin titular en la reserva')

    # Construir documento único basado en el titular
    documento_base = reserva.titular.documento
    if sufijo:
        documento = f'{documento_base}_PEND_{sufijo}'
        nombre = f'Por Asignar {sufijo}'
    else:
        documento = f'{documento_base}_PEND'
        nombre = 'Por Asignar'

    # Buscar si ya existe un pasajero pendiente para esta reserva con este documento
    pasajero_pendiente = reserva.pasajeros.filter(
        persona__documento=documento
    ).first()

    if pasajero_pendiente:
        return pasajero_pendiente

    # Crear PersonaFisica usando datos del titular para contacto
    # pero nombre genérico para que sea claro que es pendiente
    persona_pendiente, created = PersonaFisica.objects.get_or_create(
        documento=documento,
        defaults={
            'nombre': nombre,
            'apellido': '',
            'email': reserva.titular.email,  # Email del titular para comunicaciones
            'telefono': reserva.titular.telefono,  # Teléfono del titular
            'tipo_documento': reserva.titular.tipo_documento,
            'nacionalidad': reserva.titular.nacionalidad,
            'fecha_nacimiento': reserva.titular.fecha_nacimiento,
            'sexo': reserva.titular.sexo,
        }
    )

    # Crear el pasajero pendiente para esta reserva
    pasajero_pendiente = Pasajero.objects.create(
        reserva=reserva,
        persona=persona_pendiente,
        es_titular=False,
        por_asignar=True,  # Marcar como pendiente de asignación
        precio_asignado=reserva.precio_unitario or 0
    )

    return pasajero_pendiente

class ReservaPagination(PageNumberPagination):
    page_size = 5
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

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.select_related("titular", "paquete").prefetch_related("pasajeros").order_by('-fecha_reserva')
    serializer_class = ReservaSerializer
    pagination_class = ReservaPagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservaFilter

    def get_serializer_class(self):
        """
        Usa ReservaDetalleSerializer para retrieve (GET individual)
        y el serializer normal para list/create/update
        """
        if self.action == 'retrieve':
            return ReservaDetalleSerializer
        return ReservaSerializer

    def get_queryset(self):
        """
        Optimiza las queries cuando se solicita el detalle de una reserva
        """
        queryset = Reserva.objects.select_related("titular", "paquete").prefetch_related("pasajeros").order_by('-fecha_reserva')

        if self.action == 'retrieve':
            # Precargar todas las relaciones necesarias para el detalle
            queryset = queryset.select_related(
                'titular',
                'paquete',
                'paquete__tipo_paquete',
                'paquete__destino',
                'paquete__destino__ciudad',
                'paquete__destino__ciudad__pais',
                'paquete__moneda',
                'paquete__distribuidora',
                'salida',
                'salida__temporada',
                'habitacion',
                'habitacion__hotel',
                'habitacion__hotel__cadena',
                'habitacion__hotel__ciudad',
            ).prefetch_related(
                'pasajeros',
                'pasajeros__persona',
                'pasajeros__distribuciones_pago',
                'pasajeros__distribuciones_pago__comprobante',
                'servicios_adicionales',
                'servicios_adicionales__servicio',
                'comprobantes',
                'comprobantes__distribuciones',
                'comprobantes__distribuciones__pasajero',
                'comprobantes__empleado',
                'comprobantes__empleado__persona',
                'paquete__paquete_servicios',
                'paquete__paquete_servicios__servicio',
            )

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """
        Sobrescribe el método retrieve para crear pasajeros 'Por Asignar' automáticamente
        cuando la reserva tiene menos pasajeros de los esperados.

        Si la reserva cumple:
        - Tiene menos pasajeros registrados que cantidad_pasajeros
        - Tiene titular asignado
        - Tiene cantidad_pasajeros > 0

        Entonces crea automáticamente pasajeros "Por Asignar X" para completar la cantidad faltante.
        """
        # Obtener la reserva
        instance = self.get_object()

        # Verificar si necesitamos crear pasajeros pendientes
        # Solo si la cantidad actual de pasajeros es menor a la cantidad esperada
        if instance.titular and instance.cantidad_pasajeros and instance.cantidad_pasajeros > 0:
            cantidad_actual = instance.pasajeros.count()

            # Si hay menos pasajeros de los esperados, crear los faltantes
            if cantidad_actual < instance.cantidad_pasajeros:
                # Crear pasajeros pendientes para completar la cantidad
                for i in range(cantidad_actual + 1, instance.cantidad_pasajeros + 1):
                    sufijo = str(i)
                    obtener_o_crear_pasajero_pendiente(instance, sufijo)

                # Refrescar la instancia para incluir los pasajeros recién creados
                instance.refresh_from_db()

        # Serializar y retornar
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Reserva.objects.count()
        pendientes = Reserva.objects.filter(estado="pendiente").count()
        confirmadas = Reserva.objects.filter(estado="confirmada").count()
        finalizadas = Reserva.objects.filter(estado="finalizada").count()
        canceladas = Reserva.objects.filter(estado="cancelada").count()

        data = [
            {"texto": "Total", "valor": total},
            {"texto": "Pendientes", "valor": pendientes},
            {"texto": "Confirmadas", "valor": confirmadas},
            {"texto": "Finalizadas", "valor": finalizadas},
            {"texto": "Canceladas", "valor": canceladas},
        ]
        return Response(data)

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = self.filter_queryset(
            self.get_queryset()
        ).values('id', 'titular__nombre', 'paquete__nombre')
        return Response(list(queryset))

    # ----- ENDPOINT: Listar servicios adicionales de una reserva -----
    @action(detail=True, methods=['get'], url_path='servicios-adicionales')
    def servicios_adicionales(self, request, pk=None):
        """
        GET /api/reservas/{id}/servicios-adicionales/
        Lista todos los servicios adicionales de una reserva específica
        """
        reserva = self.get_object()
        servicios = reserva.servicios_adicionales.filter(activo=True)
        serializer = ReservaServiciosAdicionalesSerializer(servicios, many=True)
        return Response(serializer.data)

    # ----- ENDPOINT: Agregar servicio adicional a una reserva -----
    @action(detail=True, methods=['post'], url_path='agregar-servicio')
    def agregar_servicio(self, request, pk=None):
        """
        POST /api/reservas/{id}/agregar-servicio/
        Body: {
            "servicio_id": 1,
            "cantidad": 2,
            "precio_unitario": 150.00,
            "observacion": "Solicitado por teléfono" (opcional)
        }
        """
        reserva = self.get_object()
        serializer = ReservaServiciosAdicionalesCreateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(reserva=reserva)
            # Retornar el servicio creado con toda la información
            response_serializer = ReservaServiciosAdicionalesSerializer(
                ReservaServiciosAdicionales.objects.get(id=serializer.instance.id)
            )
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ----- ENDPOINT: Obtener resumen de costos de una reserva -----
    @action(detail=True, methods=['get'], url_path='resumen-costos')
    def resumen_costos(self, request, pk=None):
        """
        GET /api/reservas/{id}/resumen-costos/
        Retorna un resumen de costos: base, adicionales y total
        """
        reserva = self.get_object()

        data = {
            "precio_base_paquete": reserva.precio_base_paquete,
            "cantidad_pasajeros": reserva.cantidad_pasajeros,
            "costo_paquete_total": reserva.precio_base_paquete * reserva.cantidad_pasajeros,
            "costo_servicios_adicionales": reserva.costo_servicios_adicionales,
            "costo_total_estimado": reserva.costo_total_estimado,
            "monto_pagado": reserva.monto_pagado,
            "saldo_pendiente": reserva.costo_total_estimado - reserva.monto_pagado,
        }
        return Response(data)

    # ----- ENDPOINT: Generar comprobante para una reserva -----
    @action(detail=True, methods=['post'], url_path='generar-comprobante')
    def generar_comprobante(self, request, pk=None):
        """
        POST /api/reservas/{id}/generar-comprobante/

        Genera un comprobante de pago para una reserva existente.
        Útil para reservas que tienen monto_pagado pero no tienen comprobante.

        Body (opcional):
        {
            "empleado_id": 1,  // Opcional, si no se proporciona usa el primero disponible
            "tipo": "sena",    // Opcional, por defecto "sena"
            "metodo_pago": "transferencia"  // Opcional, por defecto "transferencia"
        }

        Respuesta:
        {
            "message": "Comprobante generado exitosamente",
            "comprobante_id": 15,
            "numero_comprobante": "CPG-2025-0015",
            "monto": 440.00
        }
        """
        from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion
        from apps.empleado.models import Empleado
        from decimal import Decimal

        reserva = self.get_object()

        # Validar que la reserva tenga monto_pagado
        if not reserva.monto_pagado or reserva.monto_pagado <= 0:
            return Response(
                {'error': 'La reserva no tiene monto pagado registrado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que tenga titular
        if not reserva.titular:
            return Response(
                {'error': 'La reserva no tiene titular asignado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si ya existe un comprobante
        comprobante_existente = ComprobantePago.objects.filter(reserva=reserva, activo=True).first()
        if comprobante_existente:
            return Response(
                {
                    'message': 'Ya existe un comprobante para esta reserva',
                    'comprobante_id': comprobante_existente.id,
                    'numero_comprobante': comprobante_existente.numero_comprobante,
                    'monto': comprobante_existente.monto
                },
                status=status.HTTP_200_OK
            )

        # Obtener empleado (desde request o usar el primero disponible)
        empleado_id = request.data.get('empleado_id')
        if empleado_id:
            empleado = get_object_or_404(Empleado, id=empleado_id)
        else:
            empleado = Empleado.objects.first()
            if not empleado:
                return Response(
                    {'error': 'No hay empleados registrados en el sistema'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Obtener parámetros opcionales
        tipo = request.data.get('tipo', 'sena')
        metodo_pago = request.data.get('metodo_pago', 'transferencia')

        # Crear el comprobante
        # Obtener el empleado del usuario autenticado
        usuario_autenticado = request.user
        empleado_registrador = None
        if hasattr(usuario_autenticado, 'empleado') and usuario_autenticado.empleado:
            empleado_registrador = usuario_autenticado.empleado

        comprobante = ComprobantePago(
            reserva=reserva,
            tipo=tipo,
            monto=reserva.monto_pagado,
            metodo_pago=metodo_pago,
            observaciones='Comprobante generado para presentación',
            empleado=empleado
        )
        # Guardar con el usuario_registro
        comprobante.save(usuario_registro=empleado_registrador)

        # Obtener o crear pasajero titular
        pasajero_titular = reserva.pasajeros.filter(es_titular=True).first()
        if not pasajero_titular:
            # Si no existe, crear el pasajero titular
            pasajero_titular = Pasajero.objects.create(
                reserva=reserva,
                persona=reserva.titular,
                es_titular=True
            )

        # Crear distribución para el titular
        ComprobantePagoDistribucion.objects.create(
            comprobante=comprobante,
            pasajero=pasajero_titular,
            monto=reserva.monto_pagado,
            observaciones='Distribución automática al titular'
        )

        # Actualizar monto de reserva (esto recalcula el estado)
        comprobante.actualizar_monto_reserva()

        return Response({
            'message': 'Comprobante generado exitosamente',
            'comprobante_id': comprobante.id,
            'numero_comprobante': comprobante.numero_comprobante,
            'monto': float(comprobante.monto),
            'pdf_url': f'comprobantes/{comprobante.id}/descargar-pdf/'
        }, status=status.HTTP_201_CREATED)

    # ----- ENDPOINT: Descargar PDF del comprobante de una reserva -----
    @action(detail=True, methods=['get'], url_path='descargar-comprobante')
    def descargar_comprobante(self, request, pk=None):
        """
        GET /api/reservas/{id}/descargar-comprobante/

        Descarga el PDF del comprobante de pago de una reserva.
        Si no existe comprobante, retorna error 404.
        Si existe pero no tiene PDF, lo genera automáticamente.

        Query params opcionales:
        - regenerar=true : Fuerza la regeneración del PDF

        Respuesta:
        - Content-Type: application/pdf
        - Content-Disposition: attachment; filename="comprobante_CPG-2025-0001.pdf"
        """
        from django.http import FileResponse
        from apps.comprobante.models import ComprobantePago
        import os

        reserva = self.get_object()

        # Buscar el comprobante activo de la reserva
        comprobante = ComprobantePago.objects.filter(reserva=reserva, activo=True).first()

        if not comprobante:
            return Response(
                {
                    'error': 'Esta reserva no tiene comprobante de pago',
                    'hint': 'Use el endpoint POST /api/reservas/{id}/generar-comprobante/ para crear uno'
                },
                status=status.HTTP_404_NOT_FOUND
            )

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

        # Verificar que el archivo físico existe
        if not comprobante.pdf_generado:
            return Response(
                {'error': 'No se pudo generar el PDF'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

    # ----- ENDPOINT: Descargar factura global de una reserva -----
    @action(detail=True, methods=['get'], url_path='descargar-factura-global')
    def descargar_factura_global(self, request, pk=None):
        """
        GET /api/reservas/{id}/descargar-factura-global/

        Genera (si no existe) y descarga el PDF de la factura global de una reserva.
        Este endpoint unifica la generación y descarga en un solo paso.

        Query params opcionales:
        - regenerar_pdf=true : Fuerza la regeneración del PDF
        - subtipo_impuesto_id : ID del subtipo de impuesto (si no se especifica, usa configuración)

        Facturación a nombre de tercero (opcional):
        - cliente_facturacion_id : ID de ClienteFacturacion existente
        - tercero_nombre : Nombre completo o razón social del tercero
        - tercero_tipo_documento : Tipo de documento (CI, RUC, PASAPORTE, OTRO)
        - tercero_numero_documento : Número de documento del tercero
        - tercero_direccion : Dirección del tercero (opcional)
        - tercero_telefono : Teléfono del tercero (opcional)
        - tercero_email : Email del tercero (opcional)

        Nota: Si no se especifican datos de tercero, la factura se emite a nombre del titular de la reserva.

        Respuesta:
        - Content-Type: application/pdf
        - Content-Disposition: attachment; filename="factura_001-001-0000001.pdf"

        Errores comunes:
        - 400: La reserva no cumple las condiciones para facturar
        - 404: No existe configuración de facturación
        - 500: Error al generar/descargar PDF
        """
        from apps.facturacion.models import (
            FacturaElectronica,
            generar_factura_global,
            validar_factura_global
        )
        from django.http import FileResponse
        from django.core.exceptions import ValidationError as DjangoValidationError
        import os

        try:
            reserva = self.get_object()

            # 1. Verificar si ya existe factura global
            factura = reserva.facturas.filter(
                tipo_facturacion='total',
                activo=True
            ).first()

            # 2. Si no existe, generarla
            if not factura:
                try:
                    # Validar que se puede facturar
                    validar_factura_global(reserva)

                    # Obtener parámetros de facturación
                    subtipo_impuesto_id = request.query_params.get('subtipo_impuesto_id', None)

                    # Parámetros para facturación a nombre de tercero
                    cliente_facturacion_id = request.query_params.get('cliente_facturacion_id', None)
                    tercero_nombre = request.query_params.get('tercero_nombre', None)
                    tercero_tipo_documento = request.query_params.get('tercero_tipo_documento', None)
                    tercero_numero_documento = request.query_params.get('tercero_numero_documento', None)
                    tercero_direccion = request.query_params.get('tercero_direccion', None)
                    tercero_telefono = request.query_params.get('tercero_telefono', None)
                    tercero_email = request.query_params.get('tercero_email', None)

                    # Generar factura (con o sin tercero)
                    factura = generar_factura_global(
                        reserva,
                        subtipo_impuesto_id=subtipo_impuesto_id,
                        cliente_facturacion_id=cliente_facturacion_id,
                        tercero_nombre=tercero_nombre,
                        tercero_tipo_documento=tercero_tipo_documento,
                        tercero_numero_documento=tercero_numero_documento,
                        tercero_direccion=tercero_direccion,
                        tercero_telefono=tercero_telefono,
                        tercero_email=tercero_email
                    )

                except DjangoValidationError as e:
                    return Response({
                        'error': 'No se puede generar factura',
                        'detalle': str(e.message) if hasattr(e, 'message') else str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 3. Verificar/generar PDF
            regenerar_pdf = request.query_params.get('regenerar_pdf', 'false').lower() == 'true'

            if not factura.pdf_generado or regenerar_pdf:
                try:
                    factura.generar_pdf()
                except Exception as e:
                    return Response({
                        'error': f'Error al generar PDF: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 4. Verificar que el archivo físico existe
            if not factura.pdf_generado:
                return Response({
                    'error': 'No se pudo generar el PDF'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            pdf_path = factura.pdf_generado.path
            if not os.path.exists(pdf_path):
                # Intentar regenerar si el archivo fue eliminado
                try:
                    factura.generar_pdf()
                    pdf_path = factura.pdf_generado.path
                except Exception as e:
                    return Response({
                        'error': f'El archivo PDF no existe y no se pudo regenerar: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 5. Retornar el archivo PDF
            try:
                response = FileResponse(
                    open(pdf_path, 'rb'),
                    content_type='application/pdf'
                )
                filename = f'factura_{factura.numero_factura.replace("-", "_")}.pdf'
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except Exception as e:
                return Response({
                    'error': f'Error al leer el archivo PDF: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({
                'error': f'Error al procesar factura: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    @action(detail=True, methods=['get'], url_path='descargar-factura-individual')
    def descargar_factura_individual(self, request, pk=None):
        """
        GET /api/reservas/{id}/descargar-factura-individual/?pasajero_id=XX

        Genera (si no existe) y descarga el PDF de la factura individual de un pasajero.
        Similar a la factura global, pero sólo para un pasajero específico.

        Query params:
        - pasajero_id (requerido)
        - regenerar_pdf=true : Fuerza la regeneración del PDF
        - subtipo_impuesto_id : ID del subtipo de impuesto (opcional)

        Facturación a nombre de tercero (opcional):
        - cliente_facturacion_id : ID de ClienteFacturacion existente
        - tercero_nombre : Nombre completo o razón social del tercero
        - tercero_tipo_documento : Tipo de documento (CI, RUC, PASAPORTE, OTRO)
        - tercero_numero_documento : Número de documento del tercero
        - tercero_direccion : Dirección del tercero (opcional)
        - tercero_telefono : Teléfono del tercero (opcional)
        - tercero_email : Email del tercero (opcional)

        Nota: Si no se especifican datos de tercero, la factura se emite a nombre del pasajero.

        Errores comunes:
        - 400: Falta pasajero_id o la reserva no cumple condiciones
        - 404: No existe configuración de facturación
        - 500: Error al generar/descargar PDF
        """
        from apps.facturacion.models import (
            FacturaElectronica,
            generar_factura_individual,
            validar_factura_individual
        )
        from django.http import FileResponse
        from django.core.exceptions import ValidationError as DjangoValidationError
        import os

        try:
            reserva = self.get_object()
            pasajero_id = request.query_params.get('pasajero_id')

            if not pasajero_id:
                return Response({'error': 'Debe especificar un pasajero_id'},
                                status=status.HTTP_400_BAD_REQUEST)

            pasajero = reserva.pasajeros.filter(id=pasajero_id).first()
            if not pasajero:
                return Response({'error': 'Pasajero no encontrado en esta reserva'},
                                status=status.HTTP_404_NOT_FOUND)

            # 1. Verificar si ya existe factura individual activa
            factura = reserva.facturas.filter(
                tipo_facturacion='por_pasajero',
                pasajero=pasajero,
                activo=True
            ).first()

            # 2. Si no existe, generarla
            if not factura:
                try:
                    validar_factura_individual(reserva, pasajero)

                    # Obtener parámetros de facturación
                    subtipo_impuesto_id = request.query_params.get('subtipo_impuesto_id', None)

                    # Parámetros para facturación a nombre de tercero
                    cliente_facturacion_id = request.query_params.get('cliente_facturacion_id', None)
                    tercero_nombre = request.query_params.get('tercero_nombre', None)
                    tercero_tipo_documento = request.query_params.get('tercero_tipo_documento', None)
                    tercero_numero_documento = request.query_params.get('tercero_numero_documento', None)
                    tercero_direccion = request.query_params.get('tercero_direccion', None)
                    tercero_telefono = request.query_params.get('tercero_telefono', None)
                    tercero_email = request.query_params.get('tercero_email', None)

                    # Generar factura (con o sin tercero)
                    factura = generar_factura_individual(
                        reserva,
                        pasajero,
                        subtipo_impuesto_id=subtipo_impuesto_id,
                        cliente_facturacion_id=cliente_facturacion_id,
                        tercero_nombre=tercero_nombre,
                        tercero_tipo_documento=tercero_tipo_documento,
                        tercero_numero_documento=tercero_numero_documento,
                        tercero_direccion=tercero_direccion,
                        tercero_telefono=tercero_telefono,
                        tercero_email=tercero_email
                    )
                except DjangoValidationError as e:
                    return Response({
                        'error': 'No se puede generar factura individual',
                        'detalle': str(e.message) if hasattr(e, 'message') else str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 3. Verificar/generar PDF
            regenerar_pdf = request.query_params.get('regenerar_pdf', 'false').lower() == 'true'
            if not factura.pdf_generado or regenerar_pdf:
                try:
                    factura.generar_pdf()
                except Exception as e:
                    return Response({
                        'error': f'Error al generar PDF: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if not factura.pdf_generado or not os.path.exists(factura.pdf_generado.path):
                return Response({'error': 'No se pudo generar o encontrar el PDF'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 4. Retornar archivo
            response = FileResponse(open(factura.pdf_generado.path, 'rb'), content_type='application/pdf')
            filename = f'factura_{factura.numero_factura.replace("-", "_")}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            return Response({
                'error': f'Error al procesar factura individual: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    # ----- ENDPOINT: Registrar seña de una reserva -----
    @action(detail=True, methods=['post'], url_path='registrar-senia')
    def registrar_senia(self, request, pk=None):
        """
        POST /api/reservas/{id}/registrar-senia/

        Registra el pago de seña para una reserva.
        Crea un ComprobantePago de tipo 'sena' con las distribuciones especificadas.

        Los pasajeros "pendientes" se crean bajo demanda cuando se especifican en las distribuciones.
        No se crean automáticamente al inicio del proceso.

        Soporta distribuciones para pasajeros ya cargados y pasajeros "pendientes".

        IMPORTANTE: Requiere especificar la modalidad de facturación (global o individual).
        Si el pago de seña es suficiente, la reserva se confirmará automáticamente.

        Body:
        {
            "modalidad_facturacion": "global",  // requerido: "global" o "individual"
            "condicion_pago": "credito",        // requerido: "contado" o "credito"
            "metodo_pago": "transferencia",     // requerido
            "referencia": "TRF-001",            // opcional
            "observaciones": "Seña inicial",    // opcional
            "empleado": 1,                      // opcional, usa el primer empleado si no se especifica
            "distribuciones": [                 // requerido
                {"pasajero": 1, "monto": 210.00},             // pasajero ya cargado (ID)
                {"pasajero": "pendiente_1", "monto": 210.00}, // primer pasajero pendiente
                {"pasajero": "pendiente_2", "monto": 210.00}, // segundo pasajero pendiente
                {"pasajero": "pendiente_3", "monto": 210.00}  // tercer pasajero pendiente
            ]
        }

        Respuesta exitosa:
        {
            "message": "Seña registrada exitosamente",
            "comprobante": {
                "id": 15,
                "numero_comprobante": "CPG-2025-0015",
                "tipo": "sena",
                "monto": 420.00,
                "fecha_pago": "2025-10-26T10:30:00Z",
                "distribuciones": [...],
                "pdf_url": "/api/comprobantes/15/descargar-pdf/"
            },
            "reserva": {
                "id": 1,
                "codigo": "RSV-2025-0001",
                "estado": "confirmada",  // Se confirma automáticamente si el pago es suficiente
                "estado_display": "Confirmado Incompleto",
                "modalidad_facturacion": "global",
                "modalidad_facturacion_display": "Facturación Global (Una factura total)",
                "monto_pagado": 420.00,
                "saldo_pendiente": 6652.00,
                "puede_confirmarse": true,
                "datos_completos": false
            },
            "titular": {...}
        }
        """
        from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion
        from apps.empleado.models import Empleado
        from decimal import Decimal

        reserva = self.get_object()

        # Validar que la reserva tenga titular
        if not reserva.titular:
            return Response(
                {'error': 'La reserva no tiene titular asignado. No se pueden crear pasajeros pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que la reserva tenga cantidad de pasajeros definida
        if not reserva.cantidad_pasajeros or reserva.cantidad_pasajeros <= 0:
            return Response(
                {'error': 'La reserva no tiene cantidad de pasajeros definida'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar campos requeridos
        if 'modalidad_facturacion' not in request.data:
            return Response(
                {'error': 'El campo modalidad_facturacion es requerido. Use "global" o "individual"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que la modalidad sea válida
        modalidad_facturacion = request.data['modalidad_facturacion']
        if modalidad_facturacion not in ['global', 'individual']:
            return Response(
                {'error': 'Modalidad inválida. Use "global" o "individual"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar campo condicion_pago
        if 'condicion_pago' not in request.data:
            return Response(
                {'error': 'El campo condicion_pago es requerido. Use "contado" o "credito"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que la condicion_pago sea válida
        condicion_pago = request.data['condicion_pago']
        if condicion_pago not in ['contado', 'credito']:
            return Response(
                {'error': 'Condición de pago inválida. Use "contado" o "credito"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'metodo_pago' not in request.data:
            return Response(
                {'error': 'El campo metodo_pago es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'distribuciones' not in request.data or not request.data['distribuciones']:
            return Response(
                {'error': 'Debe especificar las distribuciones de pago para cada pasajero'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener empleado
        empleado_id = request.data.get('empleado')
        if empleado_id:
            try:
                empleado = Empleado.objects.get(id=empleado_id)
            except Empleado.DoesNotExist:
                return Response(
                    {'error': f'No existe empleado con ID {empleado_id}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            empleado = Empleado.objects.first()
            if not empleado:
                return Response(
                    {'error': 'No hay empleados registrados en el sistema'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validar distribuciones
        distribuciones = request.data['distribuciones']
        if not isinstance(distribuciones, list) or len(distribuciones) == 0:
            return Response(
                {'error': 'Las distribuciones deben ser una lista con al menos un elemento'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calcular monto total de las distribuciones
        monto_total = Decimal('0')
        pasajeros_validados = []

        for dist in distribuciones:
            if 'pasajero' not in dist or 'monto' not in dist:
                return Response(
                    {'error': 'Cada distribución debe tener pasajero y monto'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # Verificar si es "pendiente", "pendiente_X" o un ID numérico
                pasajero_id = dist['pasajero']

                if isinstance(pasajero_id, str) and pasajero_id.startswith("pendiente"):
                    # Extraer sufijo si existe: "pendiente" -> "", "pendiente_1" -> "1"
                    if "_" in pasajero_id:
                        sufijo = pasajero_id.split("_", 1)[1]
                    else:
                        sufijo = ""

                    # Obtener o crear el pasajero pendiente para esta reserva
                    pasajero = obtener_o_crear_pasajero_pendiente(reserva, sufijo)
                else:
                    # Buscar pasajero existente por ID
                    pasajero = reserva.pasajeros.get(id=pasajero_id)

                pasajeros_validados.append({
                    'pasajero': pasajero,
                    'monto': Decimal(str(dist['monto']))
                })
                monto_total += Decimal(str(dist['monto']))

            except Pasajero.DoesNotExist:
                return Response(
                    {'error': f'El pasajero con ID {dist["pasajero"]} no pertenece a esta reserva'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except (ValueError, TypeError) as e:
                return Response(
                    {'error': f'Monto inválido: {dist.get("monto")}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validar que el monto total es mayor a 0
        if monto_total <= 0:
            return Response(
                {'error': 'El monto total de la seña debe ser mayor a 0'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # VALIDACIÓN TEMPRANA: Verificar que el usuario autenticado tenga caja abierta
        # ANTES de crear el comprobante y los pasajeros pendientes
        from apps.arqueo_caja.models import AperturaCaja

        usuario_autenticado = request.user
        empleado_registrador = None
        if hasattr(usuario_autenticado, 'empleado') and usuario_autenticado.empleado:
            empleado_registrador = usuario_autenticado.empleado

        # Si no hay empleado_registrador, usar el empleado asignado como fallback
        empleado_para_validar = empleado_registrador if empleado_registrador else empleado

        # Verificar que tenga caja abierta
        apertura_activa = AperturaCaja.objects.filter(
            responsable=empleado_para_validar,
            esta_abierta=True,
            activo=True
        ).first()

        if not apertura_activa:
            # Obtener nombre del empleado para mensaje de error
            empleado_nombre = "El empleado"
            if empleado_para_validar and empleado_para_validar.persona:
                persona = empleado_para_validar.persona
                try:
                    persona_fisica = persona.personafisica
                    empleado_nombre = f"{persona_fisica.nombre} {persona_fisica.apellido or ''}".strip()
                except:
                    try:
                        persona_juridica = persona.personajuridica
                        empleado_nombre = persona_juridica.razon_social
                    except:
                        pass

            return Response(
                {'error': f'No se puede registrar el pago. {empleado_nombre} no tiene una caja abierta. Por favor, abra una caja antes de registrar pagos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear el comprobante
        try:
            comprobante = ComprobantePago(
                reserva=reserva,
                tipo='sena',
                monto=monto_total,
                metodo_pago=request.data['metodo_pago'],
                referencia=request.data.get('referencia', ''),
                observaciones=request.data.get('observaciones', ''),
                empleado=empleado
            )
            # Guardar con el usuario_registro
            comprobante.save(usuario_registro=empleado_registrador)

            # Crear las distribuciones
            for dist_data in pasajeros_validados:
                ComprobantePagoDistribucion.objects.create(
                    comprobante=comprobante,
                    pasajero=dist_data['pasajero'],
                    monto=dist_data['monto']
                )

            # Actualizar monto pagado en la reserva y confirmar si corresponde
            # El método actualizar_monto_reserva() ahora acepta modalidad_facturacion y condicion_pago
            # y se encarga de confirmar la reserva automáticamente si es necesario
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                comprobante.actualizar_monto_reserva(
                    modalidad_facturacion=modalidad_facturacion,
                    condicion_pago=condicion_pago
                )
            except DjangoValidationError as e:
                # Si hay un error de validación, lo propagamos al usuario
                # y eliminamos el comprobante creado (rollback manual)
                comprobante.delete()
                return Response(
                    {'error': f'Error al confirmar la reserva: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                # Si falla por otro motivo, registramos el error
                print(f"Advertencia: Error al actualizar monto de reserva: {str(e)}")
                comprobante.delete()
                return Response(
                    {'error': f'Error al procesar el pago: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Refrescar la reserva para obtener el estado actualizado
            reserva.refresh_from_db()

            # Serializar el comprobante para la respuesta
            from apps.comprobante.serializers import ComprobantePagoSerializer
            comprobante_serializer = ComprobantePagoSerializer(comprobante)

            # Serializar datos del titular (siempre presente en nuevas reservas)
            from .serializers import PersonaFisicaSimpleSerializer
            titular_serializer = PersonaFisicaSimpleSerializer(reserva.titular)
            titular_data = titular_serializer.data

            # Obtener información de moneda
            moneda_data = None
            if reserva.paquete and reserva.paquete.moneda:
                moneda_data = {
                    'id': reserva.paquete.moneda.id,
                    'nombre': reserva.paquete.moneda.nombre,
                    'simbolo': reserva.paquete.moneda.simbolo,
                    'codigo': reserva.paquete.moneda.codigo
                }

            # Obtener nombre del paquete y destino
            nombre_paquete = reserva.paquete.nombre if reserva.paquete else None
            nombre_destino = None

            if reserva.paquete and reserva.paquete.destino:
                destino = reserva.paquete.destino

                ciudad_nombre = None
                pais_nombre = None

                if hasattr(destino, 'ciudad') and destino.ciudad:
                    ciudad_nombre = str(destino.ciudad) if not isinstance(destino.ciudad, str) else destino.ciudad

                if hasattr(destino, 'pais') and destino.pais:
                    pais_nombre = str(destino.pais) if not isinstance(destino.pais, str) else destino.pais

                # Construir nombre del destino
                if ciudad_nombre and pais_nombre:
                    nombre_destino = f"{ciudad_nombre}, {pais_nombre}"
                elif ciudad_nombre:
                    nombre_destino = ciudad_nombre
                elif pais_nombre:
                    nombre_destino = pais_nombre

            # Construir información detallada de las distribuciones para mostrar en la vista
            from django.db.models import Sum
            distribuciones_detalle = []
            for dist in comprobante.distribuciones.all():
                # Calcular monto total pagado por este pasajero hasta el momento
                monto_pagado_total = ComprobantePagoDistribucion.objects.filter(
                    pasajero=dist.pasajero,
                    comprobante__activo=True
                ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

                precio_asignado = dist.pasajero.precio_asignado or Decimal('0')
                saldo_pendiente = precio_asignado - monto_pagado_total
                porcentaje_pagado = (monto_pagado_total / precio_asignado * 100) if precio_asignado > 0 else 0

                distribuciones_detalle.append({
                    'id': dist.id,
                    'pasajero_id': dist.pasajero.id,
                    'pasajero_nombre': f"{dist.pasajero.persona.nombre} {dist.pasajero.persona.apellido}",
                    'pasajero_documento': dist.pasajero.persona.documento,
                    'es_titular': dist.pasajero.es_titular,
                    'monto': float(dist.monto),
                    'observaciones': dist.observaciones,
                    # Información financiera del pasajero
                    'precio_asignado': float(precio_asignado),
                    'monto_pagado_total': float(monto_pagado_total),
                    'saldo_pendiente': float(saldo_pendiente),
                    'porcentaje_pagado': round(float(porcentaje_pagado), 2)
                })

            return Response({
                'message': 'Seña registrada exitosamente',
                'comprobante': comprobante_serializer.data,
                'distribuciones_detalle': distribuciones_detalle,  # Información detallada para mostrar en la vista
                'reserva': {
                    'id': reserva.id,
                    'codigo': reserva.codigo,
                    'estado': reserva.estado,
                    'estado_display': reserva.estado_display,
                    'nombre_paquete': nombre_paquete,
                    'nombre_destino': nombre_destino,
                    'moneda': moneda_data,
                    'modalidad_facturacion': reserva.modalidad_facturacion,
                    'modalidad_facturacion_display': reserva.get_modalidad_facturacion_display() if reserva.modalidad_facturacion else None,
                    'condicion_pago': reserva.condicion_pago,
                    'condicion_pago_display': reserva.get_condicion_pago_display() if reserva.condicion_pago else None,
                    'costo_total_estimado': float(reserva.costo_total_estimado),
                    'monto_pagado': float(reserva.monto_pagado),
                    'saldo_pendiente': float(reserva.costo_total_estimado - reserva.monto_pagado),
                    'puede_confirmarse': reserva.puede_confirmarse(),
                    'datos_completos': reserva.datos_completos
                },
                'titular': titular_data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Error de validación (por ejemplo, no tiene caja abierta)
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            # Limpiar el mensaje si viene como lista
            if error_msg.startswith('[') and error_msg.endswith(']'):
                error_msg = error_msg.strip("[]'\"")
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DjangoValidationError as e:
            # Error de validación de Django
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            if error_msg.startswith('[') and error_msg.endswith(']'):
                error_msg = error_msg.strip("[]'\"")
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al crear el comprobante: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ----- ENDPOINT: Registrar pago (parcial o completo) de una reserva -----
    @action(detail=True, methods=['post'], url_path='registrar-pago')
    def registrar_pago(self, request, pk=None):
        """
        POST /api/reservas/{id}/registrar-pago/

        Registra un pago parcial o completo para una reserva.
        Crea un ComprobantePago con las distribuciones especificadas.

        Los pasajeros "pendientes" se crean bajo demanda cuando se especifican en las distribuciones.
        No se crean automáticamente al inicio del proceso.

        IMPORTANTE: Si la reserva está en estado 'pendiente' y este pago la confirmará,
        es OBLIGATORIO especificar la modalidad de facturación Y la condición de pago.

        Body:
        {
            "tipo": "pago_parcial",          // requerido: "pago_parcial" o "pago_total"
            "metodo_pago": "transferencia",  // requerido
            "modalidad_facturacion": "global", // CONDICIONAL: requerido SOLO si la reserva está 'pendiente' y este pago la confirmará
            "condicion_pago": "credito",     // CONDICIONAL: requerido SOLO si la reserva está 'pendiente' y este pago la confirmará
            "referencia": "TRF-002",         // opcional
            "observaciones": "Segundo pago", // opcional
            "empleado": 1,                   // opcional, usa el primer empleado si no se especifica
            "distribuciones": [              // requerido
                {"pasajero": 1, "monto": 1000.00},
                {"pasajero": 2, "monto": 1000.00},
                {"pasajero": "pendiente_1", "monto": 500.00}, // primer pasajero pendiente
                {"pasajero": "pendiente_2", "monto": 500.00}, // segundo pasajero pendiente
                {"pasajero": "pendiente_3", "monto": 500.00}  // tercer pasajero pendiente
            ]
        }

        Respuesta exitosa:
        {
            "message": "Pago registrado exitosamente",
            "comprobante": {...},
            "reserva": {
                "id": 1,
                "codigo": "RSV-2025-0001",
                "estado": "confirmada",  // o "finalizada" si ya tiene todos los datos
                "modalidad_facturacion": "global",
                "monto_pagado": 7072.00,
                "saldo_pendiente": 0.00,
                "esta_totalmente_pagada": true
            }
        }
        """
        from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion
        from apps.empleado.models import Empleado
        from decimal import Decimal

        reserva = self.get_object()

        # Validar que la reserva tenga titular
        if not reserva.titular:
            return Response(
                {'error': 'La reserva no tiene titular asignado. No se pueden crear pasajeros pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que la reserva tenga cantidad de pasajeros definida
        if not reserva.cantidad_pasajeros or reserva.cantidad_pasajeros <= 0:
            return Response(
                {'error': 'La reserva no tiene cantidad de pasajeros definida'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ========================================================================
        # VALIDACIÓN CONDICIONAL DE MODALIDAD DE FACTURACIÓN Y CONDICIÓN DE PAGO
        # ========================================================================
        # Calcular el monto del pago actual para determinar si confirmará la reserva
        monto_actual = reserva.monto_pagado
        monto_nuevo_pago = Decimal('0')

        if 'distribuciones' in request.data and request.data['distribuciones']:
            for dist in request.data['distribuciones']:
                if 'monto' in dist:
                    try:
                        monto_nuevo_pago += Decimal(str(dist['monto']))
                    except (ValueError, TypeError):
                        pass  # Se validará más adelante

        monto_total_proyectado = monto_actual + monto_nuevo_pago
        podria_confirmar = monto_total_proyectado >= reserva.seña_total

        # Determinar si necesitamos modalidad de facturación y condición de pago
        modalidad_facturacion = None
        condicion_pago = None

        if reserva.estado == 'pendiente' and not reserva.modalidad_facturacion and podria_confirmar:
            # La reserva está pendiente, no tiene modalidad y este pago la confirmará
            # Por lo tanto, es OBLIGATORIO especificar la modalidad Y la condición de pago
            if 'modalidad_facturacion' not in request.data:
                return Response({
                    'error': 'Modalidad de facturación requerida',
                    'detalle': 'Este pago confirmará la reserva. Debe especificar la modalidad de facturación.',
                    'info': {
                        'monto_pago': float(monto_nuevo_pago),
                        'monto_actual': float(monto_actual),
                        'monto_total_proyectado': float(monto_total_proyectado),
                        'senia_requerida': float(reserva.seña_total),
                    },
                    'opciones_modalidad': [
                        {'valor': 'global', 'descripcion': 'Facturación Global (Una factura total)'},
                        {'valor': 'individual', 'descripcion': 'Facturación Individual (Por pasajero)'}
                    ]
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar que la modalidad sea válida
            modalidad_facturacion = request.data['modalidad_facturacion']
            if modalidad_facturacion not in ['global', 'individual']:
                return Response({
                    'error': 'Modalidad inválida. Use "global" o "individual"'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar condición de pago
            if 'condicion_pago' not in request.data:
                return Response({
                    'error': 'Condición de pago requerida',
                    'detalle': 'Debe especificar la condición de pago: "contado" o "credito"',
                    'opciones_condicion': [
                        {'valor': 'contado', 'descripcion': 'Contado'},
                        {'valor': 'credito', 'descripcion': 'Crédito'}
                    ]
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar que la condición de pago sea válida
            condicion_pago = request.data['condicion_pago']
            if condicion_pago not in ['contado', 'credito']:
                return Response({
                    'error': 'Condición de pago inválida. Use "contado" o "credito"'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Si ya tiene modalidad o no la necesita, continuar sin ella
        # ========================================================================

        # Validar campos requeridos
        if 'tipo' not in request.data:
            return Response(
                {'error': 'El campo tipo es requerido (pago_parcial o pago_total)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.data['tipo'] not in ['pago_parcial', 'pago_total']:
            return Response(
                {'error': 'El tipo debe ser "pago_parcial" o "pago_total"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'metodo_pago' not in request.data:
            return Response(
                {'error': 'El campo metodo_pago es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'distribuciones' not in request.data or not request.data['distribuciones']:
            return Response(
                {'error': 'Debe especificar las distribuciones de pago para cada pasajero'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener empleado
        empleado_id = request.data.get('empleado')
        if empleado_id:
            try:
                empleado = Empleado.objects.get(id=empleado_id)
            except Empleado.DoesNotExist:
                return Response(
                    {'error': f'No existe empleado con ID {empleado_id}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            empleado = Empleado.objects.first()
            if not empleado:
                return Response(
                    {'error': 'No hay empleados registrados en el sistema'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validar distribuciones
        distribuciones = request.data['distribuciones']
        if not isinstance(distribuciones, list) or len(distribuciones) == 0:
            return Response(
                {'error': 'Las distribuciones deben ser una lista con al menos un elemento'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calcular monto total de las distribuciones
        monto_total = Decimal('0')
        pasajeros_validados = []

        for dist in distribuciones:
            if 'pasajero' not in dist or 'monto' not in dist:
                return Response(
                    {'error': 'Cada distribución debe tener pasajero y monto'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # Verificar si es "pendiente", "pendiente_X" o un ID numérico
                pasajero_id = dist['pasajero']

                if isinstance(pasajero_id, str) and pasajero_id.startswith("pendiente"):
                    # Extraer sufijo si existe: "pendiente" -> "", "pendiente_1" -> "1"
                    if "_" in pasajero_id:
                        sufijo = pasajero_id.split("_", 1)[1]
                    else:
                        sufijo = ""

                    # Obtener o crear el pasajero pendiente para esta reserva
                    pasajero = obtener_o_crear_pasajero_pendiente(reserva, sufijo)
                else:
                    # Buscar pasajero existente por ID
                    pasajero = reserva.pasajeros.get(id=pasajero_id)

                pasajeros_validados.append({
                    'pasajero': pasajero,
                    'monto': Decimal(str(dist['monto']))
                })
                monto_total += Decimal(str(dist['monto']))

            except Pasajero.DoesNotExist:
                return Response(
                    {'error': f'El pasajero con ID {dist["pasajero"]} no pertenece a esta reserva'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except (ValueError, TypeError) as e:
                return Response(
                    {'error': f'Monto inválido: {dist.get("monto")}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validar que el monto total es mayor a 0
        if monto_total <= 0:
            return Response(
                {'error': 'El monto total del pago debe ser mayor a 0'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # VALIDACIÓN TEMPRANA: Verificar que el usuario autenticado tenga caja abierta
        # ANTES de crear el comprobante y los pasajeros pendientes
        from apps.arqueo_caja.models import AperturaCaja

        usuario_autenticado = request.user
        empleado_registrador = None
        if hasattr(usuario_autenticado, 'empleado') and usuario_autenticado.empleado:
            empleado_registrador = usuario_autenticado.empleado

        # Si no hay empleado_registrador, usar el empleado asignado como fallback
        empleado_para_validar = empleado_registrador if empleado_registrador else empleado

        # Verificar que tenga caja abierta
        apertura_activa = AperturaCaja.objects.filter(
            responsable=empleado_para_validar,
            esta_abierta=True,
            activo=True
        ).first()

        if not apertura_activa:
            # Obtener nombre del empleado para mensaje de error
            empleado_nombre = "El empleado"
            if empleado_para_validar and empleado_para_validar.persona:
                persona = empleado_para_validar.persona
                try:
                    persona_fisica = persona.personafisica
                    empleado_nombre = f"{persona_fisica.nombre} {persona_fisica.apellido or ''}".strip()
                except:
                    try:
                        persona_juridica = persona.personajuridica
                        empleado_nombre = persona_juridica.razon_social
                    except:
                        pass

            return Response(
                {'error': f'No se puede registrar el pago. {empleado_nombre} no tiene una caja abierta. Por favor, abra una caja antes de registrar pagos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear el comprobante
        try:
            comprobante = ComprobantePago(
                reserva=reserva,
                tipo=request.data['tipo'],
                monto=monto_total,
                metodo_pago=request.data['metodo_pago'],
                referencia=request.data.get('referencia', ''),
                observaciones=request.data.get('observaciones', ''),
                empleado=empleado
            )
            # Guardar con el usuario_registro (puede lanzar ValidationError si no hay caja abierta)
            comprobante.save(usuario_registro=empleado_registrador)

            # Crear las distribuciones
            for dist_data in pasajeros_validados:
                ComprobantePagoDistribucion.objects.create(
                    comprobante=comprobante,
                    pasajero=dist_data['pasajero'],
                    monto=dist_data['monto']
                )

            # Actualizar monto pagado en la reserva y establecer modalidad y condición de pago si corresponde
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                print(f"[DEBUG VIEW] Antes de actualizar_monto_reserva - Reserva {reserva.id}, Estado: {reserva.estado}")
                comprobante.actualizar_monto_reserva(
                    modalidad_facturacion=modalidad_facturacion,
                    condicion_pago=condicion_pago
                )
                print(f"[DEBUG VIEW] Después de actualizar_monto_reserva - Reserva {reserva.id}, Estado: {reserva.estado}")
            except DjangoValidationError as e:
                # Si hay un error de validación, eliminamos el comprobante (rollback manual)
                comprobante.delete()
                return Response(
                    {'error': f'Error al confirmar la reserva: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                # Si falla por otro motivo, eliminamos el comprobante
                print(f"Error al actualizar monto de reserva: {str(e)}")
                comprobante.delete()
                return Response(
                    {'error': f'Error al procesar el pago: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Refrescar la reserva para obtener el estado actualizado
            reserva.refresh_from_db()

            # ========================================================================
            # NOTA: Las facturas individuales NO se auto-generan aquí
            # ========================================================================
            # En lugar de generar las facturas automáticamente, el campo
            # 'puede_descargar_factura' en el serializer de cada pasajero indicará
            # si cumple las condiciones para generar su factura individual.
            # El frontend mostrará un botón "Generar y Descargar Factura" cuando
            # puede_descargar_factura=true.
            #
            # Esto permite que el usuario genere las facturas individualmente cuando
            # lo necesite, en lugar de auto-generarlas todas en este momento.
            # ========================================================================

            # Serializar el comprobante para la respuesta
            from apps.comprobante.serializers import ComprobantePagoSerializer
            comprobante_serializer = ComprobantePagoSerializer(comprobante)

            # Serializar datos del titular (siempre presente en nuevas reservas)
            from .serializers import PersonaFisicaSimpleSerializer
            titular_serializer = PersonaFisicaSimpleSerializer(reserva.titular)
            titular_data = titular_serializer.data

            # Obtener información de moneda
            moneda_data = None
            if reserva.paquete and reserva.paquete.moneda:
                moneda_data = {
                    'id': reserva.paquete.moneda.id,
                    'nombre': reserva.paquete.moneda.nombre,
                    'simbolo': reserva.paquete.moneda.simbolo,
                    'codigo': reserva.paquete.moneda.codigo
                }

            # Obtener nombre del paquete y destino
            nombre_paquete = reserva.paquete.nombre if reserva.paquete else None
            nombre_destino = None

            if reserva.paquete and reserva.paquete.destino:
                destino = reserva.paquete.destino

                ciudad_nombre = None
                pais_nombre = None

                if hasattr(destino, 'ciudad') and destino.ciudad:
                    ciudad_nombre = str(destino.ciudad) if not isinstance(destino.ciudad, str) else destino.ciudad

                if hasattr(destino, 'pais') and destino.pais:
                    pais_nombre = str(destino.pais) if not isinstance(destino.pais, str) else destino.pais

                # Construir nombre del destino
                if ciudad_nombre and pais_nombre:
                    nombre_destino = f"{ciudad_nombre}, {pais_nombre}"
                elif ciudad_nombre:
                    nombre_destino = ciudad_nombre
                elif pais_nombre:
                    nombre_destino = pais_nombre

            # Mapear estado interno a texto base para la respuesta
            estado_base_map = {
                'pendiente': 'pendiente',
                'confirmada': 'confirmado',
                'finalizada': 'finalizado',
                'cancelada': 'cancelado',
            }
            estado_response = estado_base_map.get(reserva.estado, reserva.estado)

            # Construir información detallada de las distribuciones para mostrar en la vista
            from django.db.models import Sum
            distribuciones_detalle = []
            for dist in comprobante.distribuciones.all():
                # Calcular monto total pagado por este pasajero hasta el momento
                monto_pagado_total = ComprobantePagoDistribucion.objects.filter(
                    pasajero=dist.pasajero,
                    comprobante__activo=True
                ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

                precio_asignado = dist.pasajero.precio_asignado or Decimal('0')
                saldo_pendiente = precio_asignado - monto_pagado_total
                porcentaje_pagado = (monto_pagado_total / precio_asignado * 100) if precio_asignado > 0 else 0

                distribuciones_detalle.append({
                    'id': dist.id,
                    'pasajero_id': dist.pasajero.id,
                    'pasajero_nombre': f"{dist.pasajero.persona.nombre} {dist.pasajero.persona.apellido}",
                    'pasajero_documento': dist.pasajero.persona.documento,
                    'es_titular': dist.pasajero.es_titular,
                    'monto': float(dist.monto),
                    'observaciones': dist.observaciones,
                    # Información financiera del pasajero
                    'precio_asignado': float(precio_asignado),
                    'monto_pagado_total': float(monto_pagado_total),
                    'saldo_pendiente': float(saldo_pendiente),
                    'porcentaje_pagado': round(float(porcentaje_pagado), 2)
                })

            return Response({
                'message': 'Pago registrado exitosamente',
                'comprobante': comprobante_serializer.data,
                'distribuciones_detalle': distribuciones_detalle,  # Información detallada para mostrar en la vista
                'reserva': {
                    'id': reserva.id,
                    'codigo': reserva.codigo,
                    'estado': estado_response,  # Estado base sin sufijos
                    'estado_interno': reserva.estado,  # Estado interno real (pendiente/confirmada/finalizada/cancelada)
                    'estado_display': reserva.estado_display,  # Texto completo (ej: "Confirmado Incompleto")
                    'modalidad_facturacion': reserva.modalidad_facturacion,  # Modalidad de facturación
                    'modalidad_facturacion_display': reserva.get_modalidad_facturacion_display() if reserva.modalidad_facturacion else None,
                    'nombre_paquete': nombre_paquete,
                    'nombre_destino': nombre_destino,
                    'moneda': moneda_data,
                    'costo_total_estimado': float(reserva.costo_total_estimado),
                    'monto_pagado': float(reserva.monto_pagado),
                    'saldo_pendiente': float(reserva.costo_total_estimado - reserva.monto_pagado),
                    'puede_confirmarse': reserva.puede_confirmarse(),
                    'datos_completos': reserva.datos_completos
                },
                'titular': titular_data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Error de validación (por ejemplo, no tiene caja abierta)
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            # Limpiar el mensaje si viene como lista
            if error_msg.startswith('[') and error_msg.endswith(']'):
                error_msg = error_msg.strip("[]'\"")
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DjangoValidationError as e:
            # Error de validación de Django
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            if error_msg.startswith('[') and error_msg.endswith(']'):
                error_msg = error_msg.strip("[]'\"")
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al crear el comprobante: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ----- ENDPOINT: Obtener resumen simplificado de una reserva -----
    @action(detail=True, methods=['get'], url_path='detalle-resumen')
    def detalle_resumen(self, request, pk=None):
        """
        GET /api/reservas/{id}/detalle-resumen/

        Obtiene un resumen simplificado de la reserva con datos clave.
        Es más ligero que el retrieve completo, ideal para dashboards o listados.

        Respuesta ejemplo:
        {
            "id": 1,
            "codigo": "RSV-2025-0001",
            "estado": "confirmada",
            "estado_display": "Confirmado Completo",
            "fecha_reserva": "2025-10-15T10:30:00Z",
            "titular": {
                "id": 5,
                "nombre_completo": "Juan Pérez",
                "documento": "12345678",
                "email": "juan@example.com",
                "telefono": "0981123456"
            },
            "paquete": {
                "id": 3,
                "nombre": "Tour a Encarnación",
                "destino": {
                    "ciudad": "Encarnación",
                    "pais": "Paraguay"
                }
            },
            "fechas": {
                "salida": "2025-12-01",
                "regreso": "2025-12-05"
            },
            "cantidad_pasajeros": 2,
            "costos": {
                "precio_unitario": 3536.0,
                "costo_total": 7072.0,
                "monto_pagado": 420.0,
                "saldo_pendiente": 6652.0,
                "seña_total": 420.0,
                "moneda": {
                    "simbolo": "Gs.",
                    "codigo": "PYG"
                }
            },
            "validaciones": {
                "puede_confirmarse": true,
                "esta_totalmente_pagada": false,
                "datos_completos": true
            }
        }
        """
        try:
            resumen = obtener_resumen_reserva(pk)
            return Response(resumen)
        except ObjectDoesNotExist as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener resumen: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ----- ENDPOINT: Obtener solo pasajeros de una reserva -----
    @action(detail=True, methods=['get'], url_path='detalle-pasajeros')
    def detalle_pasajeros(self, request, pk=None):
        """
        GET /api/reservas/{id}/detalle-pasajeros/

        Obtiene la lista de pasajeros con su información de pagos.

        Respuesta ejemplo:
        [
            {
                "id": 1,
                "es_titular": true,
                "persona": {
                    "id": 5,
                    "nombre": "Juan",
                    "apellido": "Pérez",
                    "nombre_completo": "Juan Pérez",
                    "documento": "12345678",
                    "email": "juan@example.com",
                    "telefono": "0981123456"
                },
                "precio_asignado": 3536.0,
                "monto_pagado": 210.0,
                "saldo_pendiente": 3326.0,
                "porcentaje_pagado": 5.94,
                "seña_requerida": 210.0,
                "tiene_sena_pagada": true,
                "esta_totalmente_pagado": false,
                "ticket_numero": null,
                "voucher_codigo": null
            },
            ...
        ]
        """
        try:
            pasajeros = obtener_pasajeros_reserva(pk)
            return Response(pasajeros)
        except ObjectDoesNotExist as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener pasajeros: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ----- ENDPOINT: Obtener solo comprobantes de una reserva -----
    @action(detail=True, methods=['get'], url_path='detalle-comprobantes')
    def detalle_comprobantes(self, request, pk=None):
        """
        GET /api/reservas/{id}/detalle-comprobantes/

        Obtiene todos los comprobantes de pago de una reserva.

        Respuesta ejemplo:
        [
            {
                "id": 1,
                "numero_comprobante": "CPG-2025-0001",
                "fecha_pago": "2025-10-15T10:30:00Z",
                "tipo": "sena",
                "tipo_display": "Seña",
                "metodo_pago": "transferencia",
                "metodo_pago_display": "Transferencia Bancaria",
                "monto": 420.0,
                "referencia": "TRF-001",
                "observaciones": "Seña inicial",
                "distribuciones": [
                    {
                        "pasajero_id": 1,
                        "pasajero_nombre": "Juan Pérez",
                        "monto": 210.0,
                        "observaciones": null
                    },
                    ...
                ],
                "empleado": {
                    "id": 2,
                    "nombre": "María González"
                },
                "pdf_url": "/media/comprobantes/CPG-2025-0001.pdf"
            },
            ...
        ]
        """
        try:
            comprobantes = obtener_comprobantes_reserva(pk)
            return Response(comprobantes)
        except ObjectDoesNotExist as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener comprobantes: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ----- ENDPOINT: Cancelar una reserva -----
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar_reserva(self, request, pk=None):
        """
        POST /api/reservas/{id}/cancelar/

        CANCELACIÓN TOTAL de la reserva - Cancela TODOS los pasajeros.
        
        Aplica las políticas de reembolso:
        - > 20 días antes de la salida → se devuelve el monto reembolsable (sin seña)
        - ≤ 20 días antes de la salida → no se devuelve ningún monto
        
        Comportamiento según modalidad de facturación:
        
        FACTURACIÓN GLOBAL:
        - Se cancela la reserva completa
        - Se genera UNA Nota de Crédito por la factura global
        - Devolución por el monto reembolsable total (excluyendo seña)
        
        FACTURACIÓN INDIVIDUAL:
        - Se cancelan TODOS los pasajeros de la reserva
        - Se generará una Nota de Crédito por cada factura individual (manual)
        - Devolución por el monto reembolsable total de todos los pasajeros
        
        Siempre:
        - Libera los cupos en paquetes propios
        - Registra el motivo y fecha de cancelación
        - Crea comprobante de devolución si aplica (con movimiento de caja automático)
        
        Body:
        {
            "motivo_cancelacion_id": "1",  // requerido - ver opciones abajo
            "motivo_observaciones": "El cliente cambió de planes",  // opcional
            "metodo_devolucion": "efectivo",  // condicional: requerido si aplica reembolso
            "observaciones": "Observaciones del comprobante",  // opcional
            "referencia": "REF-001"  // opcional
        }
        
        Motivos disponibles:
        - 1: Cancelación voluntaria del cliente
        - 2: Cambio de planes del cliente
        - 3: Problemas de salud
        - 4: Problemas con documentación
        - 5: Cancelación automática por falta de pago
        - 6: Fuerza mayor / Caso fortuito
        - 7: Error en la reserva
        - 8: Otro motivo
        
        IMPORTANTE: Esta es una cancelación TOTAL. 
        No se puede cancelar solo algunos pasajeros en esta versión.
        """
        from decimal import Decimal

        from apps.comprobante.models import ComprobantePago
        from apps.empleado.models import Empleado
        from apps.arqueo_caja.models import AperturaCaja
        from apps.comprobante.serializers import ComprobantePagoSerializer

        reserva = self.get_object()

        if reserva.estado == 'cancelada':
            return Response(
                {'error': 'La reserva ya se encuentra cancelada.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reserva.salida or not reserva.salida.fecha_salida:
            return Response(
                {'error': 'La reserva no tiene fecha de salida definida. No se puede cancelar automáticamente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener información de TODOS los pasajeros (incluidos pendientes)
        pasajeros_info = []
        for pasajero in reserva.pasajeros.all():
            pasajeros_info.append({
                'id': pasajero.id,
                'nombre': f"{pasajero.persona.nombre} {pasajero.persona.apellido}",
                'precio_asignado': float(pasajero.precio_asignado or 0),
                'monto_pagado': float(pasajero.monto_pagado),
                'saldo_pendiente': float(pasajero.saldo_pendiente),
                'es_pendiente': '_PEND' in pasajero.persona.documento
            })
        
        # Obtener facturas que serán afectadas
        from apps.facturacion.models import FacturaElectronica
        facturas_info = []
        facturas_activas = FacturaElectronica.objects.filter(
            reserva=reserva,
            activo=True
        )
        
        for factura in facturas_activas:
            facturas_info.append({
                'id': factura.id,
                'numero': factura.numero_factura,
                'tipo': factura.tipo_facturacion,
                'total': float(factura.total_general),
                'pasajero': {
                    'id': factura.pasajero.id,
                    'nombre': f"{factura.pasajero.persona.nombre} {factura.pasajero.persona.apellido}"
                } if factura.pasajero else None
            })

        dias_restantes = reserva.dias_hasta_salida
        if dias_restantes is None:
            return Response(
                {'error': 'No se pudo calcular la cantidad de días hasta la salida.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        motivo_cancelacion_id = request.data.get('motivo_cancelacion_id') or '1'
        motivo_observaciones = request.data.get('motivo_observaciones', '') or ''
        observaciones = request.data.get('observaciones', '') or ''
        referencia = request.data.get('referencia', '') or ''

        # Validar que el motivo_cancelacion_id sea válido
        motivos_validos = [choice[0] for choice in Reserva.MOTIVOS_CANCELACION]
        if motivo_cancelacion_id not in motivos_validos:
            return Response(
                {
                    'error': f'Motivo de cancelación inválido. Debe ser uno de: {", ".join(motivos_validos)}',
                    'motivos_disponibles': [
                        {'id': id_motivo, 'descripcion': desc}
                        for id_motivo, desc in Reserva.MOTIVOS_CANCELACION
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        montos = reserva.calcular_montos_cancelacion()
        monto_reembolsable = montos['monto_reembolsable']
        aplica_reembolso = dias_restantes > 20 and monto_reembolsable > 0

        metodo_devolucion = request.data.get('metodo_devolucion')
        if aplica_reembolso and not metodo_devolucion:
            return Response(
                {'error': 'Debe indicar el método de devolución cuando corresponde un reembolso.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        empleado_id = request.data.get('empleado')
        if empleado_id:
            try:
                empleado = Empleado.objects.get(id=empleado_id)
            except Empleado.DoesNotExist:
                return Response(
                    {'error': f'No existe empleado con ID {empleado_id}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            empleado = getattr(request.user, 'empleado', None)
            if not empleado:
                empleado = Empleado.objects.first()

        if not empleado:
            return Response(
                {'error': 'No se pudo determinar el empleado que registra la cancelación.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        empleado_registrador = getattr(request.user, 'empleado', None) or empleado

        if aplica_reembolso:
            # Validar método de pago
            metodos_validos = [choice[0] for choice in ComprobantePago.METODOS_PAGO]
            if metodo_devolucion not in metodos_validos:
                return Response(
                    {'error': f'Método de devolución inválido. Opciones: {", ".join(metodos_validos)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            apertura_activa = AperturaCaja.objects.filter(
                responsable=empleado_registrador,
                esta_abierta=True,
                activo=True
            ).first()

            if not apertura_activa:
                return Response(
                    {'error': 'No se puede registrar la devolución. El empleado no tiene una caja abierta.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        comprobante_data = None

        try:
            with transaction.atomic():
                reserva.marcar_cancelada(
                    motivo_cancelacion_id=motivo_cancelacion_id,
                    motivo_observaciones=motivo_observaciones,
                    liberar_cupo=True
                )

                if aplica_reembolso:
                    comprobante = ComprobantePago(
                        reserva=reserva,
                        tipo='devolucion',
                        monto=monto_reembolsable,
                        metodo_pago=metodo_devolucion,
                        referencia=referencia,
                        observaciones=(
                            observaciones or f"Devolución por cancelación voluntaria de la reserva {reserva.codigo}"
                        ),
                        empleado=empleado
                    )
                    comprobante.save(usuario_registro=empleado_registrador)

                    distribuir_devolucion_en_pasajeros(reserva, comprobante, monto_reembolsable)
                    comprobante.actualizar_monto_reserva()
                    comprobante.refresh_from_db()
                    comprobante_data = ComprobantePagoSerializer(comprobante).data

                reserva.refresh_from_db()

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error al cancelar la reserva: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = ReservaDetalleSerializer(reserva)
        
        # Información sobre cupos liberados
        cupos_info = {
            'fueron_liberados': reserva.cupos_liberados,
            'cantidad_pasajeros': reserva.cantidad_pasajeros,
            'es_paquete_propio': reserva.paquete.propio if reserva.paquete else False,
            'observacion': 'Cupos liberados' if reserva.cupos_liberados else 'No se liberaron cupos (paquete de distribuidor)'
        }
        
        response_data = {
            'message': 'Reserva cancelada exitosamente',
            'tipo_cancelacion': 'total',
            'modalidad_facturacion': reserva.modalidad_facturacion,
            'dias_hasta_salida': dias_restantes,
            'politica_aplicada': '> 20 días: reembolso aplicado' if dias_restantes > 20 else '≤ 20 días: sin reembolso',
            'monto_sena': float(montos['monto_sena']),
            'monto_pagos_adicionales': float(montos['monto_pagos_adicionales']),
            'monto_reembolsable': float(monto_reembolsable),
            'reembolso_generado': bool(comprobante_data),
            'comprobante_devolucion': comprobante_data,
            'pasajeros_cancelados': len(pasajeros_info),
            'pasajeros_afectados': pasajeros_info,
            'facturas_afectadas': len(facturas_info),
            'facturas_info': facturas_info,
            'cupos_info': cupos_info,
            'reserva': serializer.data,
        }
        
        # Agregar advertencia si es facturación individual
        if reserva.modalidad_facturacion == 'individual':
            response_data['advertencia'] = (
                'CANCELACIÓN TOTAL: Se cancelaron TODOS los pasajeros de esta reserva. '
                'Cada pasajero con factura individual tendrá su propia Nota de Crédito.'
            )
        
        return Response(response_data, status=status.HTTP_200_OK)

    # ----- ENDPOINT: Cancelación Automática de Reservas Vencidas -----
    @action(detail=False, methods=['get', 'post'], url_path='cancelacion-automatica')
    def cancelacion_automatica(self, request):
        """
        GET/POST /api/reservas/cancelacion-automatica/
        
        Procesa la cancelación automática de reservas que NO están pagadas al 100%
        y faltan menos de 15 días para la salida.
        
        Criterios de elegibilidad:
        - Estado: pendiente o confirmada
        - Tiene fecha de salida definida
        - Días hasta salida: < 15
        - NO está pagada al 100%
        - Está activa
        
        Query params:
        - dry_run=true: Solo muestra qué reservas se cancelarían SIN aplicar cambios (SIMULACIÓN)
        - dry_run=false: Ejecuta la cancelación real (solo en POST)
        
        GET siempre ejecuta en modo dry-run (simulación segura)
        POST puede ejecutar la cancelación real si dry_run=false
        
        Respuesta:
        {
            "dry_run": true/false,
            "total_evaluadas": 50,
            "total_califican": 3,
            "reservas_procesadas": [
                {
                    "id": 123,
                    "codigo": "RSV-2025-0123",
                    "estado": "confirmada",
                    "dias_hasta_salida": 10,
                    "fecha_salida": "2025-12-02",
                    "monto_pagado": 1000000,
                    "monto_total": 5000000,
                    "porcentaje_pagado": 20.0,
                    "titular": "Juan Pérez",
                    "paquete": "Paquete XYZ",
                    "accion": "Se cancelaría" o "Cancelada",
                    "motivo": "Faltan 10 días y solo pagó 20%"
                }
            ],
            "mensaje": "Descripción del resultado",
            "advertencia": "Advertencia si aplica"
        }
        """
        from datetime import timedelta
        from django.utils import timezone
        
        # Determinar si es dry-run
        # GET siempre es dry-run, POST puede ser real o dry-run según parámetro
        if request.method == 'GET':
            dry_run = True
        else:
            # POST: leer parámetro (default False = ejecuta la cancelación)
            dry_run_param = request.query_params.get('dry_run', 'false').lower()
            dry_run = dry_run_param in ['true', '1', 'yes']
        
        hoy = timezone.now().date()
        
        # Obtener todas las reservas que podrían calificar
        queryset = Reserva.objects.filter(
            estado__in=['pendiente', 'confirmada'],
            salida__isnull=False,
            salida__fecha_salida__isnull=False,
            activo=True
        ).select_related('salida', 'paquete', 'titular', 'habitacion')
        
        total_evaluadas = queryset.count()
        reservas_procesadas = []
        canceladas_count = 0
        
        for reserva in queryset:
            dias_restantes = reserva.dias_hasta_salida
            
            # Validar que tenga días hasta salida
            if dias_restantes is None:
                continue
            
            # Solo procesar si faltan menos de 15 días
            if dias_restantes >= 15:
                continue
            
            # Solo procesar si NO está totalmente pagada
            if reserva.esta_totalmente_pagada():
                continue
            
            # Calcular información de la reserva
            monto_pagado = float(reserva.monto_pagado) if reserva.monto_pagado else 0.0
            monto_total = float(reserva.costo_total_estimado) if reserva.costo_total_estimado else 0.0
            porcentaje_pagado = (monto_pagado / monto_total * 100) if monto_total > 0 else 0.0
            
            titular_nombre = f"{reserva.titular.nombre} {reserva.titular.apellido}" if reserva.titular else "Sin titular"
            
            reserva_info = {
                'id': reserva.id,
                'codigo': reserva.codigo,
                'estado': reserva.estado,
                'estado_display': reserva.get_estado_display(),
                'dias_hasta_salida': dias_restantes,
                'fecha_salida': reserva.salida.fecha_salida.isoformat() if reserva.salida and reserva.salida.fecha_salida else None,
                'monto_pagado': monto_pagado,
                'monto_total': monto_total,
                'porcentaje_pagado': round(porcentaje_pagado, 2),
                'titular': titular_nombre,
                'paquete': reserva.paquete.nombre if reserva.paquete else None,
                'cantidad_pasajeros': reserva.cantidad_pasajeros or 0,
                'motivo': f"Faltan {dias_restantes} días y solo pagó {round(porcentaje_pagado, 2)}%"
            }
            
            # Ejecutar cancelación o solo simular
            if dry_run:
                reserva_info['accion'] = 'Se cancelaría (simulación)'
                reserva_info['aplicado'] = False
            else:
                # Cancelar la reserva realmente
                try:
                    exito = reserva.marcar_cancelada(
                        motivo_cancelacion_id='5',  # '5' = Cancelación automática por falta de pago
                        motivo_observaciones=f"Cancelación automática por falta de pago. Días restantes: {dias_restantes}, Pagado: {round(porcentaje_pagado, 2)}%",
                        liberar_cupo=True
                    )
                    if exito:
                        reserva_info['accion'] = 'Cancelada exitosamente'
                        reserva_info['aplicado'] = True
                        canceladas_count += 1
                    else:
                        reserva_info['accion'] = 'Ya estaba cancelada'
                        reserva_info['aplicado'] = False
                except Exception as e:
                    reserva_info['accion'] = f'Error al cancelar: {str(e)}'
                    reserva_info['aplicado'] = False
                    reserva_info['error'] = str(e)
            
            reservas_procesadas.append(reserva_info)
        
        # Construir respuesta
        total_califican = len(reservas_procesadas)
        
        if dry_run:
            if total_califican == 0:
                mensaje = "✅ No se encontraron reservas que califiquen para cancelación automática"
            else:
                mensaje = f"⚠️ [SIMULACIÓN] Se encontraron {total_califican} reservas que SERÍAN canceladas si ejecutas sin dry_run"
        else:
            if canceladas_count == 0:
                mensaje = "✅ No se cancelaron reservas (ninguna calificaba o ya estaban canceladas)"
            else:
                mensaje = f"✅ Se cancelaron automáticamente {canceladas_count} reservas"
        
        response_data = {
            'dry_run': dry_run,
            'metodo': request.method,
            'total_evaluadas': total_evaluadas,
            'total_califican': total_califican,
            'total_canceladas': canceladas_count if not dry_run else 0,
            'reservas_procesadas': reservas_procesadas,
            'mensaje': mensaje,
            'criterios': {
                'estados_validos': ['pendiente', 'confirmada'],
                'dias_limite': 15,
                'debe_estar_impaga': True,
                'debe_estar_activa': True
            }
        }
        
        # Agregar advertencia si es simulación
        if dry_run and total_califican > 0:
            response_data['advertencia'] = (
                f"⚠️ ESTO ES UNA SIMULACIÓN. Las {total_califican} reservas mostradas NO han sido canceladas. "
                "Para cancelarlas realmente, ejecuta POST /api/reservas/cancelacion-automatica/ (sin ?dry_run=true)"
            )
        
        # Agregar confirmación si se ejecutó realmente
        if not dry_run and canceladas_count > 0:
            response_data['confirmacion'] = (
                f"✅ Se han cancelado {canceladas_count} reservas en la base de datos. "
                "Los cupos han sido liberados y se registró el motivo de cancelación."
            )
        
        return Response(response_data, status=status.HTTP_200_OK)

    # ----- ENDPOINT: Ajustar fecha de salida para testing -----
    @action(detail=True, methods=['post'], url_path='ajustar-fecha-testing')
    def ajustar_fecha_testing(self, request, pk=None):
        """
        POST /api/reservas/{id}/ajustar-fecha-testing/
        
        ⚠️ ENDPOINT PARA TESTING ÚNICAMENTE ⚠️
        
        Modifica la fecha de salida de una reserva para poder probar
        la funcionalidad de cancelación automática.
        
        Body (opcional):
        {
            "dias_hasta_salida": 10,         // Días hasta la salida (default: 10)
            "ajustar_para": "calificar"      // "calificar" o "no_calificar" (default: "calificar")
        }
        
        - "calificar": Ajusta fecha para que califique para cancelación (< 15 días)
        - "no_calificar": Ajusta fecha para que NO califique (> 15 días, ej: 20 días)
        
        La cancelación automática requiere:
        - Días hasta salida < 15
        - NO estar pagada al 100%
        - Estado: pendiente o confirmada
        
        Respuesta:
        {
            "mensaje": "Fecha ajustada exitosamente",
            "reserva_id": 274,
            "reserva_codigo": "RSV-2025-0272",
            "antes": {
                "fecha_salida": "2025-12-20",
                "dias_hasta_salida": 28,
                "calificaba": false
            },
            "despues": {
                "fecha_salida": "2025-12-02",
                "dias_hasta_salida": 10,
                "califica_ahora": true
            },
            "estado_pago": {
                "esta_totalmente_pagada": true,
                "porcentaje_pagado": 100.0,
                "nota": "La reserva está pagada al 100%, no calificará por este criterio"
            },
            "advertencia": "⚠️ Este cambio es para TESTING. Afecta la base de datos real."
        }
        """
        from datetime import date, timedelta
        
        reserva = self.get_object()
        
        # Validar que tenga salida
        if not reserva.salida or not reserva.salida.fecha_salida:
            return Response(
                {'error': 'La reserva no tiene fecha de salida definida.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener parámetros del body
        dias_hasta_salida = request.data.get('dias_hasta_salida', 10)
        ajustar_para = request.data.get('ajustar_para', 'calificar').lower()
        
        # Validar días
        try:
            dias_hasta_salida = int(dias_hasta_salida)
        except (ValueError, TypeError):
            return Response(
                {'error': 'El parámetro "dias_hasta_salida" debe ser un número entero.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ajustar días según el objetivo
        if ajustar_para == 'calificar':
            # Para que califique: < 15 días
            if dias_hasta_salida >= 15:
                dias_hasta_salida = 10  # Default seguro para calificar
        elif ajustar_para == 'no_calificar':
            # Para que NO califique: >= 15 días
            if dias_hasta_salida < 15:
                dias_hasta_salida = 20  # Default seguro para no calificar
        else:
            return Response(
                {'error': 'El parámetro "ajustar_para" debe ser "calificar" o "no_calificar".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Guardar estado anterior
        fecha_anterior = reserva.salida.fecha_salida
        dias_anteriores = reserva.dias_hasta_salida
        
        # Verificar si calificaba antes
        calificaba_antes = (
            dias_anteriores is not None and 
            dias_anteriores < 15 and 
            not reserva.esta_totalmente_pagada() and
            reserva.estado in ['pendiente', 'confirmada']
        )
        
        # Calcular nueva fecha
        hoy = date.today()
        nueva_fecha = hoy + timedelta(days=dias_hasta_salida)
        
        # Modificar la fecha de salida
        reserva.salida.fecha_salida = nueva_fecha
        reserva.salida.save(update_fields=['fecha_salida'])
        
        # Refrescar la reserva para obtener el nuevo cálculo de días
        reserva.refresh_from_db()
        reserva.salida.refresh_from_db()
        
        # Verificar si califica después del cambio
        nuevos_dias = reserva.dias_hasta_salida
        esta_totalmente_pagada = reserva.esta_totalmente_pagada()
        
        califica_ahora = (
            nuevos_dias is not None and 
            nuevos_dias < 15 and 
            not esta_totalmente_pagada and
            reserva.estado in ['pendiente', 'confirmada']
        )
        
        # Calcular porcentaje pagado
        monto_pagado = float(reserva.monto_pagado) if reserva.monto_pagado else 0.0
        monto_total = float(reserva.costo_total_estimado) if reserva.costo_total_estimado else 0.0
        porcentaje_pagado = (monto_pagado / monto_total * 100) if monto_total > 0 else 0.0
        
        # Construir respuesta
        response_data = {
            'mensaje': 'Fecha de salida ajustada exitosamente para testing',
            'reserva_id': reserva.id,
            'reserva_codigo': reserva.codigo,
            'antes': {
                'fecha_salida': fecha_anterior.isoformat() if fecha_anterior else None,
                'dias_hasta_salida': dias_anteriores,
                'calificaba': calificaba_antes
            },
            'despues': {
                'fecha_salida': nueva_fecha.isoformat(),
                'dias_hasta_salida': nuevos_dias,
                'califica_ahora': califica_ahora
            },
            'estado_pago': {
                'esta_totalmente_pagada': esta_totalmente_pagada,
                'monto_pagado': monto_pagado,
                'monto_total': monto_total,
                'porcentaje_pagado': round(porcentaje_pagado, 2)
            },
            'criterios_cancelacion': {
                'dias_menor_15': nuevos_dias < 15 if nuevos_dias is not None else False,
                'no_pagada_100': not esta_totalmente_pagada,
                'estado_valido': reserva.estado in ['pendiente', 'confirmada'],
                'todos_cumplen': califica_ahora
            },
            'advertencia': '⚠️ Este cambio es para TESTING. La fecha fue modificada en la base de datos real.'
        }
        
        # Agregar nota si no califica por pago
        if esta_totalmente_pagada:
            response_data['nota'] = (
                'La reserva está pagada al 100%. Aunque los días sean < 15, '
                'NO calificará para cancelación automática porque ya está pagada.'
            )
        
        # Agregar nota si no califica por estado
        if reserva.estado not in ['pendiente', 'confirmada']:
            response_data['nota'] = (
                f'La reserva está en estado "{reserva.estado}". '
                'Solo reservas en estado "pendiente" o "confirmada" califican para cancelación automática.'
            )
        
        # Agregar próximos pasos sugeridos
        if califica_ahora:
            response_data['proximos_pasos'] = (
                'La reserva ahora CALIFICA para cancelación automática. '
                'Puedes ejecutar: GET /api/reservas/cancelacion-automatica/ para verificarla en la lista, '
                'o POST /api/reservas/cancelacion-automatica/ para ejecutar la cancelación masiva.'
            )
        else:
            razones = []
            if nuevos_dias >= 15:
                razones.append(f'Faltan {nuevos_dias} días (necesita < 15)')
            if esta_totalmente_pagada:
                razones.append('Está pagada al 100%')
            if reserva.estado not in ['pendiente', 'confirmada']:
                razones.append(f'Estado "{reserva.estado}" no válido')
            
            response_data['proximos_pasos'] = (
                f'La reserva NO califica para cancelación automática. '
                f'Razones: {", ".join(razones)}. '
                f'Puedes ajustar nuevamente con días < 15 o cambiar el estado de pago.'
            )
        
        return Response(response_data, status=status.HTTP_200_OK)

    # ----- ENDPOINT: Obtener solo servicios de una reserva -----
    @action(detail=True, methods=['get'], url_path='detalle-servicios')
    def detalle_servicios(self, request, pk=None):
        """
        GET /api/reservas/{id}/detalle-servicios/

        Obtiene todos los servicios (base y adicionales) de una reserva.

        Respuesta ejemplo:
        {
            "servicios_base": [
                {
                    "id": 1,
                    "servicio": {
                        "id": 5,
                        "nombre": "Desayuno",
                        "descripcion": "Desayuno buffet"
                    },
                    "precio": 0.0,
                    "incluido": true,
                    "observaciones": null
                },
                ...
            ],
            "servicios_adicionales": [
                {
                    "id": 3,
                    "servicio": {
                        "id": 8,
                        "nombre": "Tour adicional",
                        "descripcion": "Tour a la ciudad"
                    },
                    "cantidad": 2,
                    "precio_unitario": 150.0,
                    "subtotal": 300.0,
                    "observacion": null,
                    "fecha_agregado": "2025-10-16T14:00:00Z"
                },
                ...
            ],
            "costo_servicios_adicionales": 300.0
        }
        """
        try:
            servicios = obtener_servicios_reserva(pk)
            return Response(servicios)
        except ObjectDoesNotExist as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener servicios: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='forzar-actualizacion-estado')
    def forzar_actualizacion_estado(self, request, pk=None):
        """
        Fuerza la actualización del estado de una reserva.
        Útil cuando el estado no se actualizó correctamente después de un pago.

        POST /api/reservas/{id}/forzar-actualizacion-estado/
        """
        reserva = self.get_object()

        estado_anterior = reserva.estado

        # Refrescar la reserva desde la base de datos
        reserva.refresh_from_db()

        # Forzar la actualización del estado
        reserva.actualizar_estado()

        # Refrescar nuevamente para obtener el estado actualizado
        reserva.refresh_from_db()

        return Response({
            'message': 'Estado actualizado exitosamente',
            'estado_anterior': estado_anterior,
            'estado_actual': reserva.estado,
            'estado_display': reserva.estado_display,
            'datos_completos': reserva.datos_completos,
            'esta_totalmente_pagada': reserva.esta_totalmente_pagada(),
            'puede_descargar_factura_global': self._calcular_puede_descargar_factura_global(reserva),
        }, status=status.HTTP_200_OK)

    def _calcular_puede_descargar_factura_global(self, reserva):
        """Helper para calcular puede_descargar_factura_global"""
        if reserva.modalidad_facturacion != 'global' or not reserva.condicion_pago:
            return False

        if reserva.condicion_pago == 'contado':
            return reserva.estado == 'finalizada' and reserva.esta_totalmente_pagada()
        elif reserva.condicion_pago == 'credito':
            return reserva.estado in ['confirmada', 'finalizada']

        return False

    @action(detail=True, methods=['get'], url_path='diagnostico-estado')
    def diagnostico_estado(self, request, pk=None):
        """
        Endpoint temporal de diagnóstico para verificar por qué una reserva
        no pasa al estado 'finalizada'.

        GET /api/reservas/{id}/diagnostico-estado/
        """
        reserva = self.get_object()

        # Recopilar información de diagnóstico
        pasajeros_info = []
        pasajeros_reales = reserva.pasajeros.exclude(persona__documento__contains='_PEND')

        for p in reserva.pasajeros.all():
            pasajeros_info.append({
                'id': p.id,
                'nombre': f"{p.persona.nombre} {p.persona.apellido}",
                'documento': p.persona.documento,
                'es_pendiente': '_PEND' in p.persona.documento,
                'precio_asignado': float(p.precio_asignado or 0),
                'monto_pagado': float(p.monto_pagado),
                'saldo_pendiente': float(p.saldo_pendiente),
                'esta_totalmente_pagado': p.esta_totalmente_pagado,
                'tiene_sena_pagada': p.tiene_sena_pagada,
            })

        # Validaciones
        validaciones = {
            'cantidad_pasajeros': reserva.cantidad_pasajeros,
            'pasajeros_cargados_reales': reserva.pasajeros_cargados,
            'pasajeros_total': reserva.pasajeros.count(),
            'faltan_datos_pasajeros': reserva.faltan_datos_pasajeros,
            'datos_completos': reserva.datos_completos,
            'puede_confirmarse': reserva.puede_confirmarse(),
            'esta_totalmente_pagada': reserva.esta_totalmente_pagada(),
            'todos_pasajeros_reales_pagados': pasajeros_reales.exists() and all(p.esta_totalmente_pagado for p in pasajeros_reales),
        }

        # Determinar por qué no está en finalizada
        razones_no_finalizada = []
        if reserva.estado == 'confirmada':
            if not reserva.esta_totalmente_pagada():
                razones_no_finalizada.append("No está totalmente pagada")
                if not reserva.faltan_datos_pasajeros:
                    # Verificar cuáles pasajeros no están totalmente pagados
                    for p in pasajeros_reales:
                        if not p.esta_totalmente_pagado:
                            razones_no_finalizada.append(
                                f"Pasajero {p.id} ({p.persona.nombre}) tiene saldo pendiente: {p.saldo_pendiente}"
                            )
            if not reserva.datos_completos:
                razones_no_finalizada.append("Datos no completos (faltan pasajeros por cargar)")

        # Calcular puede_descargar_factura_global
        puede_descargar_factura_global = False
        if reserva.modalidad_facturacion == 'global' and reserva.condicion_pago:
            if reserva.condicion_pago == 'contado':
                puede_descargar_factura_global = (
                    reserva.estado == 'finalizada' and
                    reserva.esta_totalmente_pagada()
                )
            elif reserva.condicion_pago == 'credito':
                puede_descargar_factura_global = reserva.estado in ['confirmada', 'finalizada']

        return Response({
            'reserva_id': reserva.id,
            'codigo': reserva.codigo,
            'estado_actual': reserva.estado,
            'estado_display': reserva.estado_display,
            'modalidad_facturacion': reserva.modalidad_facturacion,
            'condicion_pago': reserva.condicion_pago,
            'costo_total_estimado': float(reserva.costo_total_estimado),
            'monto_pagado_reserva': float(reserva.monto_pagado),
            'saldo_pendiente_reserva': float(reserva.costo_total_estimado - reserva.monto_pagado),
            'validaciones': validaciones,
            'pasajeros': pasajeros_info,
            'razones_no_finalizada': razones_no_finalizada if razones_no_finalizada else ['Cumple todas las condiciones para estar finalizada'],
            'puede_descargar_factura_global': puede_descargar_factura_global,
            'requisitos_factura_global': {
                'modalidad': reserva.modalidad_facturacion == 'global',
                'condicion_pago': reserva.condicion_pago,
                'estado_requerido': 'finalizada' if reserva.condicion_pago == 'contado' else 'confirmada o finalizada',
                'estado_actual': reserva.estado,
                'cumple_estado': reserva.estado == 'finalizada' if reserva.condicion_pago == 'contado' else reserva.estado in ['confirmada', 'finalizada'],
                'totalmente_pagada': reserva.esta_totalmente_pagada(),
            }
        })


class ReservaServiciosAdicionalesViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar servicios adicionales de forma global
    (no necesariamente vinculado a una reserva específica en la URL)
    """
    queryset = ReservaServiciosAdicionales.objects.select_related(
        'reserva', 'servicio'
    ).order_by('-fecha_agregado')
    serializer_class = ReservaServiciosAdicionalesSerializer
    permission_classes = []

    def get_queryset(self):
        """Permite filtrar por reserva usando query params"""
        queryset = super().get_queryset()
        reserva_id = self.request.query_params.get('reserva_id', None)
        if reserva_id is not None:
            queryset = queryset.filter(reserva_id=reserva_id)
        return queryset


class PasajeroViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar pasajeros.

    Endpoints:
    - GET /api/pasajeros/ - Listar todos los pasajeros
    - GET /api/pasajeros/{id}/ - Obtener detalle de un pasajero
    - POST /api/pasajeros/ - Crear nuevo pasajero
    - PUT /api/pasajeros/{id}/ - Actualizar pasajero
    - DELETE /api/pasajeros/{id}/ - Eliminar pasajero
    - GET /api/pasajeros/{id}/estado-cuenta/ - Obtener estado de cuenta completo
    """
    queryset = Pasajero.objects.select_related(
        'persona',
        'reserva',
        'reserva__paquete',
        'reserva__salida'
    ).order_by('-fecha_registro')
    serializer_class = PasajeroSerializer
    permission_classes = []

    def get_queryset(self):
        """
        Filtrar pasajeros por query params.

        Query params disponibles:
        - reserva_id: filtrar por reserva
        - persona_id: filtrar por persona
        - es_titular: filtrar solo titulares (true/false)
        """
        queryset = super().get_queryset()

        reserva_id = self.request.query_params.get('reserva_id', None)
        if reserva_id is not None:
            queryset = queryset.filter(reserva_id=reserva_id)

        persona_id = self.request.query_params.get('persona_id', None)
        if persona_id is not None:
            queryset = queryset.filter(persona_id=persona_id)

        es_titular = self.request.query_params.get('es_titular', None)
        if es_titular is not None:
            es_titular_bool = es_titular.lower() == 'true'
            queryset = queryset.filter(es_titular=es_titular_bool)

        return queryset

    def perform_update(self, serializer):
        """
        Después de actualizar un pasajero, recalcular el estado de la reserva.

        Esto es crucial cuando se actualiza un pasajero "Por Asignar" a una persona real,
        ya que verifica si todos los pasajeros ya están asignados (datos_completos=True)
        y actualiza el estado de la reserva según corresponda:

        - Si tiene pago total (100%) + datos completos → estado "finalizada"
        - Si tiene seña pagada → estado "confirmada"
        - Si no tiene seña → estado "pendiente"

        El método actualizar_estado() también actualiza el flag datos_completos.

        IMPORTANTE: Actualización automática de por_asignar y puede_descargar_factura
        ---------------------------------------------------------------------------
        Si se está actualizando el campo persona_id (asignando una persona real):
        1. Automáticamente cambia por_asignar de True a False
        2. El campo puede_descargar_factura se recalculará en la respuesta
        3. Si el pasajero ya está totalmente pagado, puede_descargar_factura será True

        Ejemplo de escenario:
        - Pasajero temporal "Por Asignar 1" recibe pago del 100%
        - puede_descargar_factura = False (porque por_asignar=True)
        - Se asigna una persona real → PATCH /api/pasajeros/{id}/ con persona_id=5
        - por_asignar cambia a False automáticamente
        - La respuesta incluirá puede_descargar_factura = True
        - El frontend puede mostrar el botón "Generar y Descargar Factura"
        """
        # Verificar si se está actualizando la persona (asignando datos reales)
        persona_id = serializer.validated_data.get('persona')
        pasajero_actual = self.get_object()

        # Si se está cambiando la persona Y el pasajero estaba por_asignar
        if persona_id and pasajero_actual.por_asignar:
            # Verificar que no sea una persona "pendiente" (con _PEND en el documento)
            if not persona_id.documento or '_PEND' not in persona_id.documento:
                # Cambiar por_asignar a False porque ahora tiene datos reales
                serializer.validated_data['por_asignar'] = False

        # Guardar el pasajero actualizado
        pasajero = serializer.save()

        # Actualizar el estado de la reserva asociada
        if pasajero.reserva:
            pasajero.reserva.actualizar_estado()

    @action(detail=True, methods=['get'], url_path='estado-cuenta')
    def estado_cuenta(self, request, pk=None):
        """
        GET /api/pasajeros/{id}/estado-cuenta/

        Retorna el estado de cuenta completo del pasajero incluyendo:
        - Información personal
        - Precio asignado
        - Monto pagado
        - Saldo pendiente
        - Porcentaje pagado
        - Seña requerida y si fue pagada
        - Estado de pago completo
        - Historial detallado de pagos (distribuciones de comprobantes)

        Respuesta ejemplo:
        {
            "id": 1,
            "reserva_codigo": "RSV-2025-0001",
            "paquete_nombre": "Tour a Encarnación",
            "persona": {
                "id": 5,
                "nombre": "Juan",
                "apellido": "Pérez",
                "documento": "12345678",
                "email": "juan@example.com",
                "telefono": "0981123456"
            },
            "es_titular": true,
            "precio_asignado": 5000.00,
            "monto_pagado": 2000.00,
            "saldo_pendiente": 3000.00,
            "porcentaje_pagado": 40.00,
            "seña_requerida": 1500.00,
            "tiene_sena_pagada": true,
            "esta_totalmente_pagado": false,
            "ticket_numero": null,
            "voucher_codigo": null,
            "fecha_registro": "2025-10-15T10:30:00Z",
            "historial_pagos": [
                {
                    "fecha_pago": "2025-10-15T10:30:00Z",
                    "numero_comprobante": "CPG-2025-0001",
                    "tipo": "sena",
                    "tipo_display": "Seña",
                    "metodo_pago": "transferencia",
                    "metodo_pago_display": "Transferencia Bancaria",
                    "monto_distribuido": 1500.00,
                    "comprobante_activo": true,
                    "observaciones": null
                },
                {
                    "fecha_pago": "2025-10-20T14:00:00Z",
                    "numero_comprobante": "CPG-2025-0005",
                    "tipo": "pago_parcial",
                    "tipo_display": "Pago Parcial",
                    "metodo_pago": "efectivo",
                    "metodo_pago_display": "Efectivo",
                    "monto_distribuido": 500.00,
                    "comprobante_activo": true,
                    "observaciones": "Pago en oficina"
                }
            ]
        }
        """
        pasajero = self.get_object()
        serializer = PasajeroEstadoCuentaSerializer(pasajero)
        return Response(serializer.data)


class ReservaListadoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet optimizado para listar reservas con información mínima.

    Este endpoint está diseñado para ser más rápido y eficiente que /api/reservas/
    al recuperar solo los datos esenciales para mostrar en listados y tablas.

    Endpoints disponibles:
    - GET /api/reservas_v2/ - Listar reservas (paginado)
    - GET /api/reservas_v2/{id}/ - Obtener detalle completo de una reserva

    Soporta los mismos filtros que /api/reservas/:
    - estado: filtrar por estado (pendiente, confirmada, finalizada, cancelada)
    - datos_completos: filtrar por datos completos (true/false)
    - titular: filtrar por nombre del titular (búsqueda parcial)
    - paquete: filtrar por nombre del paquete (búsqueda parcial)
    - codigo: filtrar por código de reserva (búsqueda parcial)
    - observacion: filtrar por observación (búsqueda parcial)
    - activo: filtrar por estado activo (true/false)
    - documento: filtrar por documento del titular (búsqueda parcial)
    - fecha_reserva_desde: filtrar desde fecha (YYYY-MM-DD)
    - fecha_reserva_hasta: filtrar hasta fecha (YYYY-MM-DD)
    - busqueda: búsqueda general en código, titular, documento, paquete

    Paginación:
    - page: número de página (default: 1)
    - page_size: cantidad de items por página (default: 10)

    Ejemplo:
    GET /api/reservas_v2/?page=1&page_size=10&activo=true&estado=confirmada
    """
    serializer_class = ReservaListadoSerializer
    pagination_class = ReservaPagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservaFilter

    def get_queryset(self):
        """
        Queryset optimizado con select_related para minimizar consultas a la BD.
        Solo precarga las relaciones necesarias para el listado.
        """
        return Reserva.objects.select_related(
            'titular',
            'paquete',
            'paquete__moneda',
            'paquete__destino',
            'paquete__destino__ciudad',
            'paquete__destino__ciudad__pais'
        ).order_by('-fecha_reserva')

    def get_serializer_class(self):
        """
        Usa ReservaDetalleSerializer para retrieve (GET individual)
        y ReservaListadoSerializer para list
        """
        if self.action == 'retrieve':
            return ReservaDetalleSerializer
        return ReservaListadoSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Al obtener una reserva individual, usa el mismo queryset optimizado
        que el endpoint /api/reservas/{id}/ para obtener toda la información.
        """
        # Obtener la instancia con todas las relaciones precargadas
        instance = Reserva.objects.select_related(
            'titular',
            'paquete',
            'paquete__tipo_paquete',
            'paquete__destino',
            'paquete__destino__ciudad',
            'paquete__destino__ciudad__pais',
            'paquete__moneda',
            'paquete__distribuidora',
            'salida',
            'salida__temporada',
            'salida__moneda',
            'habitacion',
            'habitacion__hotel',
            'habitacion__hotel__cadena',
            'habitacion__hotel__ciudad',
            'habitacion__moneda',
        ).prefetch_related(
            'pasajeros',
            'pasajeros__persona',
            'pasajeros__distribuciones_pago',
            'pasajeros__distribuciones_pago__comprobante',
            'servicios_adicionales',
            'servicios_adicionales__servicio',
            'comprobantes',
            'comprobantes__distribuciones',
            'comprobantes__distribuciones__pasajero',
            'comprobantes__distribuciones__pasajero__persona',
            'comprobantes__empleado',
            'comprobantes__empleado__persona',
            'paquete__paquete_servicios',
            'paquete__paquete_servicios__servicio',
        ).get(pk=kwargs['pk'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='confirmar')
    def confirmar_reserva(self, request, pk=None):
        """
        Confirma una reserva y establece la modalidad de facturación.

        POST /api/reservas/{id}/confirmar/

        Body:
        {
            "modalidad_facturacion": "global"  // o "individual"
        }

        Response 200:
        {
            "mensaje": "Reserva confirmada exitosamente",
            "reserva": {...},
            "modalidad_seleccionada": "global"
        }
        """
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            reserva = self.get_object()

            if reserva.estado != 'pendiente':
                return Response({
                    "error": "Solo se pueden confirmar reservas en estado 'pendiente'",
                    "estado_actual": reserva.estado
                }, status=status.HTTP_400_BAD_REQUEST)

            if not reserva.puede_confirmarse():
                return Response({
                    "error": "Seña insuficiente",
                    "detalle": f"Debe pagar al menos {reserva.seña_total} Gs para confirmar",
                    "pagado": str(reserva.monto_pagado),
                    "falta": str(reserva.seña_total - reserva.monto_pagado)
                }, status=status.HTTP_400_BAD_REQUEST)

            modalidad = request.data.get('modalidad_facturacion')
            if not modalidad:
                return Response({
                    "error": "Modalidad requerida",
                    "detalle": "Debe especificar 'modalidad_facturacion': 'global' o 'individual'"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Actualizar estado y modalidad
            reserva.actualizar_estado(modalidad_facturacion=modalidad)

            serializer = self.get_serializer(reserva)
            return Response({
                "mensaje": "Reserva confirmada exitosamente",
                "reserva": serializer.data,
                "modalidad_seleccionada": modalidad
            }, status=status.HTTP_200_OK)

        except DjangoValidationError as e:
            return Response({
                "error": str(e.message) if hasattr(e, 'message') else str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": f"Error al confirmar reserva: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
