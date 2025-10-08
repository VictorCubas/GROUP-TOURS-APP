import django_filters
from django.db.models import Q
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from .models import Destino


class DestinoFilter(django_filters.FilterSet):
    """
    Permite filtrar destinos por ciudad, país, estado y fechas.
    Soporta parámetros:
    - nombre=<texto>       -> filtra ciudad
    - pais_nombre=<texto>  -> filtra país
    """

    # 🔹 Filtro por nombre de ciudad
    nombre = django_filters.CharFilter(
        field_name="ciudad__nombre",
        lookup_expr="icontains"
    )

    # 🔹 Filtro por nombre de país
    pais_nombre = django_filters.CharFilter(
        field_name="ciudad__pais__nombre",
        lookup_expr="icontains"
    )
    
    zona_geografica = django_filters.CharFilter(field_name="ciudad__pais__zona_geografica__nombre", lookup_expr="icontains")  # 🔹 agregado

    activo = django_filters.BooleanFilter(field_name="activo")

    # Fechas de creación
    fecha_creacion_desde = django_filters.DateFilter(
        field_name="fecha_creacion",
        lookup_expr="gte"
    )
    fecha_creacion_hasta = django_filters.DateFilter(
        field_name="fecha_creacion",
        lookup_expr="lte",
        method="filter_fecha_hasta"
    )

    # Búsqueda unificada: ciudad o país
    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = Destino
        fields = [
            "nombre",          # 🔹 parámetro URL: ?nombre=Rio
            "pais_nombre",     # 🔹 parámetro URL: ?pais_nombre=Brasil
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
        """
        Filtra destinos por ciudad o país en un solo campo.
        """
        return queryset.filter(
            Q(ciudad__nombre__icontains=value) |
            Q(ciudad__pais__nombre__icontains=value) |
            Q(ciudad__pais__zona_geografica__nombre__icontains=value)  # 🔹 búsqueda por zona
        )
