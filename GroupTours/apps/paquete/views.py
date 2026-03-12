from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import HttpResponse

from .models import Paquete, SalidaPaquete
from .serializers import (
    PaqueteSerializer,
    SalidaPaqueteSerializer,
    SalidaPaqueteActualizarFechasSerializer,
    SalidaPaqueteListSerializer,
    SalidaPaqueteDetalleSerializer,
    ReservaPasajeroDetalleSerializer,
)
from .filters import PaqueteFilter, SalidaFilter


# -------------------- PAGINACIÓN --------------------
class PaquetePagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return Response({
            "totalItems": self.page.paginator.count,
            "pageSize": self.get_page_size(self.request),
            "totalPages": self.page.paginator.num_pages,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


# -------------------- VIEWSET --------------------
class PaqueteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Paquete con soporte de:
    - Subida de imagen (MultiPartParser / FormData)
    - Filtrado por DjangoFilterBackend (incluye modalidad y habitacion_fija)
    - Paginación personalizada
    - Endpoints extra: resumen y todos
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    queryset = (
        Paquete.objects.select_related(
            "tipo_paquete",
            "destino",
            "destino__ciudad__pais__zona_geografica",  # ✅ acceso optimizado
            "distribuidora",
            "moneda"
        )
        .prefetch_related(
            "paquete_servicios__servicio",
            "salidas__moneda",
            "salidas__hoteles",
            "salidas__habitacion_fija__hotel",
        )
        .order_by("-fecha_creacion")
    )

    serializer_class = PaqueteSerializer
    pagination_class = PaquetePagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaqueteFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Paquete.objects.count()
        activos = Paquete.objects.filter(activo=True).count()
        propios = Paquete.objects.filter(propio=True).count()
        de_distribuidora = Paquete.objects.filter(propio=False).count()

        data = [
            {"texto": "Total", "valor": str(total)},
            {"texto": "Activos", "valor": str(activos)},
            {"texto": "Propios", "valor": str(propios)},
            {"texto": "Distribuidora", "valor": str(de_distribuidora)},
        ]
        return Response(data)

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = (
            self.filter_queryset(
                self.get_queryset().filter(activo=True)
            )
            .values(
                "id",
                "nombre",
                "destino__ciudad__nombre",
                "destino__ciudad__pais__nombre",
                "destino__ciudad__pais__zona_geografica__nombre",  # ✅ nueva línea
            )
        )

        data = [
            {
                "id": item["id"],
                "nombre": item["nombre"],
                "destino": item["destino__ciudad__nombre"],
                "pais": item["destino__ciudad__pais__nombre"],
                "zona_geografica": item["destino__ciudad__pais__zona_geografica__nombre"],
            }
            for item in queryset
        ]
        return Response(data)


# -------------------- PAGINACIÓN SALIDAS --------------------
class SalidaPaginacion(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return Response({
            "totalItems": self.page.paginator.count,
            "pageSize": self.get_page_size(self.request),
            "totalPages": self.page.paginator.num_pages,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


# -------------------- VIEWSET SALIDA PAQUETE --------------------
class SalidaPaqueteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las Salidas de Paquete.

    Endpoints disponibles:
    - GET  /api/paquete/salidas/                          → Listado paginado con filtros
    - GET  /api/paquete/salidas/{id}/                     → Detalle con reservas y pasajeros
    - POST /api/paquete/salidas/                          → Crear nueva salida
    - PUT/PATCH /api/paquete/salidas/{id}/                → Actualizar salida
    - PATCH /api/paquete/salidas/{id}/actualizar-fechas/  → Solo actualizar fechas
    - DELETE /api/paquete/salidas/{id}/                   → Soft delete
    - GET  /api/paquete/salidas/{id}/pasajeros/           → Todos los pasajeros de la salida
    - GET  /api/paquete/salidas/resumen/                  → Estadísticas globales

    Filtros disponibles (query params):
    - paquete_id, paquete (nombre), activo
    - reserva_codigo (código de reserva asociada)
    - fecha_salida_desde, fecha_salida_hasta
    - busqueda (nombre de paquete, código de salida o reserva)
    """

    serializer_class = SalidaPaqueteSerializer
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = SalidaFilter
    pagination_class = SalidaPaginacion

    def get_queryset(self):
        base_qs = SalidaPaquete.objects.select_related(
            "paquete",
            "paquete__destino__ciudad__pais",
            "moneda",
            "temporada",
            "habitacion_fija__tipo_habitacion",
            "habitacion_fija__hotel",
        ).prefetch_related(
            "hoteles",
            "cupos_habitaciones__habitacion__tipo_habitacion",
            "precios_catalogo_hoteles__hotel",
            "precios_catalogo__habitacion__tipo_habitacion",
        ).order_by("-fecha_creacion")

        # Para el detalle también pre-cargamos reservas y pasajeros
        if self.action == "retrieve":
            base_qs = base_qs.prefetch_related(
                "reservas__titular",
                "reservas__pasajeros__persona__tipo_documento",
                "reservas__habitacion__tipo_habitacion",
            )

        return base_qs

    def get_serializer_class(self):
        if self.action == "list":
            return SalidaPaqueteListSerializer
        if self.action == "retrieve":
            return SalidaPaqueteDetalleSerializer
        return SalidaPaqueteSerializer

    # ----- ACTION: pasajeros -----
    @action(detail=True, methods=["get"], url_path="pasajeros")
    def pasajeros(self, request, pk=None):
        """
        GET /api/paquete/salidas/{id}/pasajeros/

        Retorna todos los pasajeros de reservas activas (no canceladas) de la salida.
        Incluye nombre, documento, datos de pago, ticket y voucher.
        """
        salida = self.get_object()
        from apps.reserva.models import Pasajero

        pasajeros_qs = Pasajero.objects.filter(
            reserva__salida=salida,
            reserva__activo=True,
        ).exclude(
            reserva__estado="cancelada"
        ).select_related(
            "persona__tipo_documento",
            "reserva",
        ).order_by("reserva__codigo", "es_titular")

        data = []
        for p in pasajeros_qs:
            data.append({
                "id": p.id,
                "reserva_codigo": p.reserva.codigo,
                "reserva_estado": p.reserva.estado,
                "reserva_estado_display": p.reserva.estado_display,
                "es_titular": p.es_titular,
                "por_asignar": p.por_asignar,
                "nombre": p.persona.nombre,
                "apellido": p.persona.apellido,
                "documento": p.persona.documento,
                "tipo_documento": p.persona.tipo_documento.nombre if p.persona.tipo_documento else None,
                "fecha_nacimiento": p.persona.fecha_nacimiento,
                "edad": p.persona.edad,
                "precio_asignado": p.precio_asignado,
                "monto_pagado": p.monto_pagado,
                "saldo_pendiente": p.saldo_pendiente,
                "tiene_sena_pagada": p.tiene_sena_pagada,
                "esta_totalmente_pagado": p.esta_totalmente_pagado,
                "ticket_numero": p.ticket_numero,
                "voucher_codigo": p.voucher_codigo,
            })

        return Response({
            "salida_id": salida.id,
            "salida_codigo": salida.codigo,
            "paquete": salida.paquete.nombre,
            "fecha_salida": salida.fecha_salida,
            "total_pasajeros": len(data),
            "pasajeros": data,
        })

    # ----- ACTION: exportar pasajeros a Excel -----
    @action(detail=True, methods=["get"], url_path="pasajeros/exportar-excel")
    def pasajeros_exportar_excel(self, request, pk=None):
        """
        GET /api/paquete/salidas/{id}/pasajeros/exportar-excel/

        Descarga un Excel con el listado de pasajeros de la salida.
        """
        from apps.reserva.models import Pasajero
        from .utils import generar_excel_pasajeros_salida

        salida = self.get_object()

        pasajeros_qs = Pasajero.objects.filter(
            reserva__salida=salida,
            reserva__activo=True,
        ).exclude(
            reserva__estado="cancelada"
        ).select_related(
            "persona__tipo_documento",
            "reserva",
        ).order_by("reserva__codigo", "es_titular")

        data = []
        for p in pasajeros_qs:
            data.append({
                "id": p.id,
                "reserva_codigo": p.reserva.codigo,
                "reserva_estado": p.reserva.estado,
                "reserva_estado_display": p.reserva.estado_display,
                "es_titular": p.es_titular,
                "por_asignar": p.por_asignar,
                "nombre": p.persona.nombre,
                "apellido": p.persona.apellido,
                "documento": p.persona.documento,
                "tipo_documento": p.persona.tipo_documento.nombre if p.persona.tipo_documento else None,
                "fecha_nacimiento": p.persona.fecha_nacimiento,
                "edad": p.persona.edad,
                "precio_asignado": p.precio_asignado,
                "monto_pagado": p.monto_pagado,
                "saldo_pendiente": p.saldo_pendiente,
                "tiene_sena_pagada": p.tiene_sena_pagada,
                "esta_totalmente_pagado": p.esta_totalmente_pagado,
                "ticket_numero": p.ticket_numero,
                "voucher_codigo": p.voucher_codigo,
            })

        excel_buffer = generar_excel_pasajeros_salida(salida, data)
        filename = f"pasajeros_{salida.codigo}.xlsx"

        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ----- ACTION: resumen -----
    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """
        GET /api/paquete/salidas/resumen/

        Estadísticas globales de salidas.
        """
        from django.utils.timezone import now
        from django.db.models import Count, Q

        hoy = now().date()
        qs = SalidaPaquete.objects.all()

        total = qs.count()
        activas = qs.filter(activo=True).count()
        proximas = qs.filter(activo=True, fecha_salida__gte=hoy).count()
        pasadas = qs.filter(activo=True, fecha_salida__lt=hoy).count()

        return Response([
            {"texto": "Total salidas", "valor": str(total)},
            {"texto": "Activas", "valor": str(activas)},
            {"texto": "Próximas", "valor": str(proximas)},
            {"texto": "Realizadas", "valor": str(pasadas)},
        ])

    # ----- ACTUALIZAR FECHAS -----
    @action(detail=True, methods=["patch"], url_path="actualizar-fechas")
    def actualizar_fechas(self, request, pk=None):
        """
        PATCH /api/paquete/salidas/{id}/actualizar-fechas/

        Actualiza solo las fechas de salida y regreso sin afectar otros campos.
        """
        salida = self.get_object()
        serializer = SalidaPaqueteActualizarFechasSerializer(
            salida, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            salida.calcular_precio_venta()
            return Response({
                **serializer.data,
                "mensaje": "Fechas actualizadas correctamente",
                "paquete": salida.paquete.nombre,
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ----- SOFT DELETE -----
    def destroy(self, request, *args, **kwargs):
        salida = self.get_object()
        salida.activo = False
        salida.save()
        return Response({
            "mensaje": "Salida desactivada correctamente",
            "id": salida.id,
        }, status=status.HTTP_200_OK)
