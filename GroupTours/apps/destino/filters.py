import django_filters
from django.db.models import Q
from .models import Destino
from django.utils.timezone import make_aware
from datetime import datetime, timedelta

class DestinoFilter(django_filters.FilterSet):
    # Filtros directos
    nombre = django_filters.CharFilter(
        field_name="nombre",
        lookup_expr="icontains"
    )
    activo = django_filters.BooleanFilter(field_name="activo")
    pais = django_filters.CharFilter(
        field_name="pais__nombre",
        lookup_expr="icontains"
    )

    # Fechas
    fecha_creacion_desde = django_filters.DateFilter(
        field_name="fecha_creacion",
        lookup_expr="gte"
    )
    fecha_creacion_hasta = django_filters.DateFilter(
        field_name="fecha_creacion",
        lookup_expr="lte",
        method='filter_fecha_hasta'
    )
    
    def filter_fecha_hasta(self, queryset, name, value):
        siguiente_dia = datetime.combine(value, datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_creacion__lt=siguiente_dia)

    # Filtro unificado
    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = Destino
        fields = [
            "nombre",
            "activo",
            "pais",
            "fecha_creacion_desde",
            "fecha_creacion_hasta",
            "busqueda"
        ]

    def filter_busqueda(self, queryset, name, value):
        """
        Filtra destinos por nombre o nombre del país.
        """
        return queryset.filter(
            Q(nombre__icontains=value) |
            Q(pais__nombre__icontains=value)
        )
