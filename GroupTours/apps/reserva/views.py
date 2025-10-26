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
    PasajeroEstadoCuentaSerializer
)
from .filters import ReservaFilter


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

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Reserva.objects.count()
        pendientes = Reserva.objects.filter(estado="pendiente").count()
        confirmadas = Reserva.objects.filter(estado="confirmada").count()
        incompletas = Reserva.objects.filter(estado="incompleta").count()
        finalizadas = Reserva.objects.filter(estado="finalizada").count()
        canceladas = Reserva.objects.filter(estado="cancelada").count()

        data = [
            {"texto": "Total", "valor": total},
            {"texto": "Pendientes", "valor": pendientes},
            {"texto": "Confirmadas", "valor": confirmadas},
            {"texto": "Incompletas", "valor": incompletas},
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

    # ----- ENDPOINT: Registrar seña de una reserva -----
    @action(detail=True, methods=['post'], url_path='registrar-senia')
    def registrar_senia(self, request, pk=None):
        """
        POST /api/reservas/{id}/registrar-senia/

        Registra el pago de seña para una reserva.
        Crea un ComprobantePago de tipo 'sena' con las distribuciones especificadas.

        Soporta distribuciones para pasajeros ya cargados y pasajeros "pendientes".

        Body:
        {
            "metodo_pago": "transferencia",  // requerido
            "referencia": "TRF-001",         // opcional
            "observaciones": "Seña inicial", // opcional
            "empleado": 1,                   // opcional, usa el primer empleado si no se especifica
            "distribuciones": [              // requerido
                {"pasajero": 1, "monto": 210.00},            // pasajero ya cargado
                {"pasajero": "pendiente", "monto": 210.00}   // pasajero por asignar
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
                "estado": "confirmada",
                "monto_pagado": 420.00,
                "saldo_pendiente": 6652.00,
                "puede_confirmarse": true
            }
        }
        """
        from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion
        from apps.empleado.models import Empleado
        from decimal import Decimal

        reserva = self.get_object()

        # Validar que hay pasajeros en la reserva
        if not reserva.pasajeros.exists():
            return Response(
                {'error': 'La reserva no tiene pasajeros registrados'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar campos requeridos
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

            # Actualizar monto pagado en la reserva
            comprobante.actualizar_monto_reserva()

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

            return Response({
                'message': 'Seña registrada exitosamente',
                'comprobante': comprobante_serializer.data,
                'reserva': {
                    'id': reserva.id,
                    'codigo': reserva.codigo,
                    'estado': reserva.estado,
                    'nombre_paquete': nombre_paquete,
                    'nombre_destino': nombre_destino,
                    'moneda': moneda_data,
                    'costo_total_estimado': float(reserva.costo_total_estimado),
                    'monto_pagado': float(reserva.monto_pagado),
                    'saldo_pendiente': float(reserva.costo_total_estimado - reserva.monto_pagado),
                    'puede_confirmarse': reserva.puede_confirmarse()
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

        Body:
        {
            "tipo": "pago_parcial",          // requerido: "pago_parcial" o "pago_total"
            "metodo_pago": "transferencia",  // requerido
            "referencia": "TRF-002",         // opcional
            "observaciones": "Segundo pago", // opcional
            "empleado": 1,                   // opcional, usa el primer empleado si no se especifica
            "distribuciones": [              // requerido
                {"pasajero": 1, "monto": 1000.00},
                {"pasajero": 2, "monto": 1000.00},
                {"pasajero": "pendiente", "monto": 500.00}  // pasajero por asignar
            ]
        }

        Respuesta exitosa:
        {
            "message": "Pago registrado exitosamente",
            "comprobante": {...},
            "reserva": {
                "id": 1,
                "codigo": "RSV-2025-0001",
                "estado": "finalizada",
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

        # Validar que hay pasajeros en la reserva
        if not reserva.pasajeros.exists():
            return Response(
                {'error': 'La reserva no tiene pasajeros registrados'},
                status=status.HTTP_400_BAD_REQUEST
            )

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

            # Actualizar monto pagado en la reserva
            comprobante.actualizar_monto_reserva()

            # Serializar el comprobante para la respuesta
            from apps.comprobante.serializers import ComprobantePagoSerializer
            comprobante_serializer = ComprobantePagoSerializer(comprobante)

            # Obtener información de moneda
            moneda_data = None
            if reserva.paquete and reserva.paquete.moneda:
                moneda_data = {
                    'id': reserva.paquete.moneda.id,
                    'nombre': reserva.paquete.moneda.nombre,
                    'simbolo': reserva.paquete.moneda.simbolo,
                    'codigo': reserva.paquete.moneda.codigo
                }

            return Response({
                'message': 'Pago registrado exitosamente',
                'comprobante': comprobante_serializer.data,
                'reserva': {
                    'id': reserva.id,
                    'codigo': reserva.codigo,
                    'estado': reserva.estado,
                    'moneda': moneda_data,
                    'monto_pagado': float(reserva.monto_pagado),
                    'saldo_pendiente': float(reserva.costo_total_estimado - reserva.monto_pagado),
                    'esta_totalmente_pagada': reserva.esta_totalmente_pagada()
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Error al crear el comprobante: {str(e)}'},
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
