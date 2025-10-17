import django_filters
from django.db.models import Q
from .models import Reserva
from django.utils.timezone import make_aware
from datetime import datetime, timedelta


class ReservaFilter(django_filters.FilterSet):
    estado = django_filters.CharFilter(field_name="estado", lookup_expr="iexact")
    datos_completos = django_filters.BooleanFilter(field_name="datos_completos")
    titular = django_filters.CharFilter(field_name="titular__nombre", lookup_expr="icontains")
    paquete = django_filters.CharFilter(field_name="paquete__nombre", lookup_expr="icontains")
    codigo = django_filters.CharFilter(field_name="codigo", lookup_expr="icontains")
    observacion = django_filters.CharFilter(field_name="observacion", lookup_expr="icontains")
    activo = django_filters.BooleanFilter(field_name="activo")
    documento = django_filters.CharFilter(field_name="titular__documento", lookup_expr="icontains")

    fecha_reserva_desde = django_filters.DateFilter(field_name="fecha_reserva", lookup_expr="gte")
    fecha_reserva_hasta = django_filters.DateFilter(field_name="fecha_reserva", method='filter_fecha_hasta')

    def filter_fecha_hasta(self, queryset, name, value):
        siguiente_dia = datetime.combine(value, datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_reserva__lt=siguiente_dia)

    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = Reserva
        fields = [
            "estado", "datos_completos", "titular", "paquete", "codigo", "observacion",
            "fecha_reserva_desde", "fecha_reserva_hasta", "activo", "documento"
        ]

    def filter_busqueda(self, queryset, name, value):
        return queryset.filter(
            Q(codigo__icontains=value) |
            Q(observacion__icontains=value) |
            Q(titular__nombre__icontains=value) |
            Q(titular__apellido__icontains=value) |
            Q(titular__documento__icontains=value) |
            Q(paquete__nombre__icontains=value)
        )
