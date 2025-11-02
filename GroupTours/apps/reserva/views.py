from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

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
    obtener_servicios_reserva
)
from django.core.exceptions import ObjectDoesNotExist


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
        comprobante = ComprobantePago.objects.create(
            reserva=reserva,
            tipo=tipo,
            monto=reserva.monto_pagado,
            metodo_pago=metodo_pago,
            observaciones='Comprobante generado para presentación',
            empleado=empleado
        )

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

                    # Obtener subtipo de impuesto si se especificó
                    subtipo_impuesto_id = request.query_params.get('subtipo_impuesto_id', None)

                    # Generar factura
                    factura = generar_factura_global(reserva, subtipo_impuesto_id)

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
                    subtipo_impuesto_id = request.query_params.get('subtipo_impuesto_id', None)
                    factura = generar_factura_individual(reserva, pasajero, subtipo_impuesto_id)
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

        # Crear el comprobante
        try:
            comprobante = ComprobantePago.objects.create(
                reserva=reserva,
                tipo='sena',
                monto=monto_total,
                metodo_pago=request.data['metodo_pago'],
                referencia=request.data.get('referencia', ''),
                observaciones=request.data.get('observaciones', ''),
                empleado=empleado
            )

            # Crear las distribuciones
            for dist_data in pasajeros_validados:
                ComprobantePagoDistribucion.objects.create(
                    comprobante=comprobante,
                    pasajero=dist_data['pasajero'],
                    monto=dist_data['monto']
                )

            # Actualizar monto pagado en la reserva y confirmar si corresponde
            # El método actualizar_monto_reserva() ahora acepta modalidad_facturacion
            # y se encarga de confirmar la reserva automáticamente si es necesario
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                comprobante.actualizar_monto_reserva(modalidad_facturacion=modalidad_facturacion)
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
                    'costo_total_estimado': float(reserva.costo_total_estimado),
                    'monto_pagado': float(reserva.monto_pagado),
                    'saldo_pendiente': float(reserva.costo_total_estimado - reserva.monto_pagado),
                    'puede_confirmarse': reserva.puede_confirmarse(),
                    'datos_completos': reserva.datos_completos
                },
                'titular': titular_data
            }, status=status.HTTP_201_CREATED)

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
        es OBLIGATORIO especificar la modalidad de facturación.

        Body:
        {
            "tipo": "pago_parcial",          // requerido: "pago_parcial" o "pago_total"
            "metodo_pago": "transferencia",  // requerido
            "modalidad_facturacion": "global", // CONDICIONAL: requerido SOLO si la reserva está 'pendiente' y este pago la confirmará
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
        # VALIDACIÓN CONDICIONAL DE MODALIDAD DE FACTURACIÓN
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

        # Determinar si necesitamos modalidad de facturación
        modalidad_facturacion = None

        if reserva.estado == 'pendiente' and not reserva.modalidad_facturacion and podria_confirmar:
            # La reserva está pendiente, no tiene modalidad y este pago la confirmará
            # Por lo tanto, es OBLIGATORIO especificar la modalidad
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

        # Crear el comprobante
        try:
            comprobante = ComprobantePago.objects.create(
                reserva=reserva,
                tipo=request.data['tipo'],
                monto=monto_total,
                metodo_pago=request.data['metodo_pago'],
                referencia=request.data.get('referencia', ''),
                observaciones=request.data.get('observaciones', ''),
                empleado=empleado
            )

            # Crear las distribuciones
            for dist_data in pasajeros_validados:
                ComprobantePagoDistribucion.objects.create(
                    comprobante=comprobante,
                    pasajero=dist_data['pasajero'],
                    monto=dist_data['monto']
                )

            # Actualizar monto pagado en la reserva y establecer modalidad si corresponde
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                comprobante.actualizar_monto_reserva(modalidad_facturacion=modalidad_facturacion)
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
