import django_filters
from django.db.models import Q
from .models import Paquete
from django.utils.timezone import make_aware
from datetime import datetime, timedelta


class PaqueteFilter(django_filters.FilterSet):
    # 🔹 Filtros directos
    tipo_paquete = django_filters.CharFilter(
        field_name="tipo_paquete__nombre",
        lookup_expr="icontains"
    )
    distribuidora = django_filters.CharFilter(
        field_name="distribuidora__nombre",
        lookup_expr="icontains"
    )
    destino = django_filters.CharFilter(
        field_name="destino__ciudad__nombre",
        lookup_expr="icontains"
    )
    propio = django_filters.BooleanFilter(field_name="propio")
    activo = django_filters.BooleanFilter(field_name="activo")

    # 🔹 Nuevo filtro de zona geográfica (igual que en Destino)
    zona_geografica = django_filters.CharFilter(
        field_name="destino__ciudad__pais__zona_geografica__nombre",
        lookup_expr="icontains",
        help_text="Filtrar por zona geográfica (ej: América del Sur, Europa, Caribe, etc.)"
    )

    # 🔹 Filtros adicionales
    modalidad = django_filters.CharFilter(
        field_name="modalidad",
        lookup_expr="iexact",  # búsqueda exacta pero insensible a mayúsculas
        help_text="Filtrar por modalidad (ej: fija, flexible)."
    )
    habitacion_fija = django_filters.BooleanFilter(
        field_name="habitacion_fija",
        help_text="Filtrar si el paquete tiene habitación fija."
    )

    # 🔹 Fechas
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

    # 🔹 Búsqueda unificada (nombre, destino, país o zona geográfica)
    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = Paquete
        fields = [
            "tipo_paquete",
            "distribuidora",
            "destino",
            "propio",
            "activo",
            "zona_geografica",     # 🔹 agregado aquí
            "modalidad",
            "habitacion_fija",
            "fecha_creacion_desde",
            "fecha_creacion_hasta"
        ]

    def filter_busqueda(self, queryset, name, value):
        """
        Filtra paquetes por nombre, destino, país o zona geográfica.
        """
        return queryset.filter(
            Q(nombre__icontains=value) |
            Q(destino__ciudad__nombre__icontains=value) |
            Q(destino__ciudad__pais__nombre__icontains=value) |
            Q(destino__ciudad__pais__zona_geografica__nombre__icontains=value) |  # 🔹 búsqueda por zona
            Q(tipo_paquete__nombre__icontains=value) |
            Q(distribuidora__nombre__icontains=value) |
            Q(modalidad__icontains=value)
        )
