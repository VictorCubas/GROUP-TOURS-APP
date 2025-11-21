import django_filters
from django.db.models import Q
from .models import FacturaElectronica, NotaCreditoElectronica
from django.utils.timezone import make_aware
from datetime import datetime, timedelta


class FacturaElectronicaFilter(django_filters.FilterSet):
    """
    Filtros para FacturaElectronica.

    Filtros disponibles:
    - activo: Boolean (True/False) - Filtra facturas activas o anuladas
    - es_configuracion: Boolean - Filtra configuraciones vs facturas reales
    - tipo_facturacion: String (total/por_pasajero)
    - condicion_venta: String (contado/credito)
    - reserva_id: Integer - ID de la reserva
    - pasajero_id: Integer - ID del pasajero
    - numero_factura: String (contiene)
    - cliente_nombre: String (contiene)
    - cliente_documento: String (contiene)
    - fecha_emision_desde: Date (>=)
    - fecha_emision_hasta: Date (<=)
    - fecha_anulacion_desde: Date (>=)
    - fecha_anulacion_hasta: Date (<=)
    - busqueda: String - Búsqueda general (número, cliente, documento)
    """

    activo = django_filters.BooleanFilter(field_name="activo")
    es_configuracion = django_filters.BooleanFilter(field_name="es_configuracion")
    tipo_facturacion = django_filters.CharFilter(field_name="tipo_facturacion", lookup_expr="iexact")
    condicion_venta = django_filters.CharFilter(field_name="condicion_venta", lookup_expr="iexact")

    # Relaciones
    reserva_id = django_filters.NumberFilter(field_name="reserva__id")
    pasajero_id = django_filters.NumberFilter(field_name="pasajero__id")
    punto_expedicion_id = django_filters.NumberFilter(field_name="punto_expedicion__id")

    # Campos de texto
    numero_factura = django_filters.CharFilter(field_name="numero_factura", lookup_expr="icontains")
    cliente_nombre = django_filters.CharFilter(field_name="cliente_nombre", lookup_expr="icontains")
    cliente_documento = django_filters.CharFilter(field_name="cliente_numero_documento", lookup_expr="icontains")

    # Fechas de emisión
    fecha_emision_desde = django_filters.DateTimeFilter(field_name="fecha_emision", lookup_expr="gte")
    fecha_emision_hasta = django_filters.DateTimeFilter(field_name="fecha_emision", method='filter_fecha_emision_hasta')

    # Fechas de anulación
    fecha_anulacion_desde = django_filters.DateTimeFilter(field_name="fecha_anulacion", lookup_expr="gte")
    fecha_anulacion_hasta = django_filters.DateTimeFilter(field_name="fecha_anulacion", method='filter_fecha_anulacion_hasta')

    # Búsqueda general
    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = FacturaElectronica
        fields = [
            "activo", "es_configuracion", "tipo_facturacion", "condicion_venta",
            "reserva_id", "pasajero_id", "punto_expedicion_id",
            "numero_factura", "cliente_nombre", "cliente_documento",
            "fecha_emision_desde", "fecha_emision_hasta",
            "fecha_anulacion_desde", "fecha_anulacion_hasta",
            "busqueda"
        ]

    def filter_fecha_emision_hasta(self, queryset, name, value):
        """Incluye todo el día especificado (hasta las 23:59:59)"""
        siguiente_dia = datetime.combine(value.date(), datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_emision__lt=siguiente_dia)

    def filter_fecha_anulacion_hasta(self, queryset, name, value):
        """Incluye todo el día especificado (hasta las 23:59:59)"""
        siguiente_dia = datetime.combine(value.date(), datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_anulacion__lt=siguiente_dia)

    def filter_busqueda(self, queryset, name, value):
        """
        Búsqueda general en múltiples campos.
        Busca en: número de factura, nombre del cliente, documento del cliente
        """
        return queryset.filter(
            Q(numero_factura__icontains=value) |
            Q(cliente_nombre__icontains=value) |
            Q(cliente_numero_documento__icontains=value) |
            Q(reserva__codigo__icontains=value)
        )


class NotaCreditoElectronicaFilter(django_filters.FilterSet):
    """
    Filtros para NotaCreditoElectronica.

    Filtros disponibles:
    - activo: Boolean (True/False)
    - tipo_nota: String (total/parcial)
    - motivo: String
    - factura_id: Integer - ID de la factura afectada
    - numero_nota: String (contiene)
    - fecha_emision_desde: Date (>=)
    - fecha_emision_hasta: Date (<=)
    - busqueda: String - Búsqueda general
    """

    activo = django_filters.BooleanFilter(field_name="activo")
    tipo_nota = django_filters.CharFilter(field_name="tipo_nota", lookup_expr="iexact")
    motivo = django_filters.CharFilter(field_name="motivo", lookup_expr="iexact")

    # Relaciones
    factura_id = django_filters.NumberFilter(field_name="factura_afectada__id")

    # Campos de texto
    numero_nota = django_filters.CharFilter(field_name="numero_nota_credito", lookup_expr="icontains")

    # Fechas de emisión
    fecha_emision_desde = django_filters.DateTimeFilter(field_name="fecha_emision", lookup_expr="gte")
    fecha_emision_hasta = django_filters.DateTimeFilter(field_name="fecha_emision", method='filter_fecha_emision_hasta')

    # Búsqueda general
    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = NotaCreditoElectronica
        fields = [
            "activo", "tipo_nota", "motivo",
            "factura_id",
            "numero_nota",
            "fecha_emision_desde", "fecha_emision_hasta",
            "busqueda"
        ]

    def filter_fecha_emision_hasta(self, queryset, name, value):
        """Incluye todo el día especificado (hasta las 23:59:59)"""
        siguiente_dia = datetime.combine(value.date(), datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_emision__lt=siguiente_dia)

    def filter_busqueda(self, queryset, name, value):
        """
        Búsqueda general en múltiples campos.
        Busca en: número de nota, número de factura afectada
        """
        return queryset.filter(
            Q(numero_nota_credito__icontains=value) |
            Q(factura_afectada__numero_factura__icontains=value)
        )
