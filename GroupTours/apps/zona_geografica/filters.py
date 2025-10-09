import django_filters
from django.db.models import Q
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from .models import ZonaGeografica


class ZonaGeograficaFilter(django_filters.FilterSet):
    """
    Permite filtrar zonas geográficas por nombre, estado y fechas.
    Soporta:
    - nombre=<texto>       -> filtra por nombre de la zona
    - activo=true/false    -> filtra por estado
    - busqueda=<texto>     -> búsqueda libre por nombre o descripción
    """

    nombre = django_filters.CharFilter(field_name="nombre", lookup_expr="icontains")
    activo = django_filters.BooleanFilter(field_name="activo")

    fecha_creacion_desde = django_filters.DateFilter(field_name="fecha_creacion", lookup_expr="gte")
    fecha_creacion_hasta = django_filters.DateFilter(field_name="fecha_creacion", method="filter_fecha_hasta")

    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = ZonaGeografica
        fields = [
            "nombre",
            "activo",
            "fecha_creacion_desde",
            "fecha_creacion_hasta",
            "busqueda",
        ]

    def filter_fecha_hasta(self, queryset, name, value):
        siguiente_dia = datetime.combine(value, datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_creacion__lt=siguiente_dia)

    def filter_busqueda(self, queryset, name, value):
        return queryset.filter(
            Q(nombre__icontains=value) |
            Q(descripcion__icontains=value)
        )
