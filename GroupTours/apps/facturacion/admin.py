from django.contrib import admin
from .models import (
    Empresa,
    Establecimiento,
    PuntoExpedicion,
    Timbrado,
    TipoImpuesto,
    SubtipoImpuesto,
    FacturaElectronica
)

# ---------- SubtipoImpuesto inline para TipoImpuesto ----------
class SubtipoImpuestoInline(admin.TabularInline):
    model = SubtipoImpuesto
    extra = 1
    min_num = 0
    verbose_name = "Subtipo de Impuesto"
    verbose_name_plural = "Subtipos de Impuestos"


# ---------- TipoImpuesto admin ----------
@admin.register(TipoImpuesto)
class TipoImpuestoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)
    inlines = [SubtipoImpuestoInline]


# ---------- Empresa admin ----------
@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ruc", "telefono", "correo")
    search_fields = ("nombre", "ruc")
    list_filter = ("actividades",)


# ---------- Establecimiento admin ----------
@admin.register(Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display = ("empresa", "codigo", "nombre", "direccion")
    list_filter = ("empresa",)
    search_fields = ("codigo", "direccion")


# ---------- PuntoExpedicion admin ----------
@admin.register(PuntoExpedicion)
class PuntoExpedicionAdmin(admin.ModelAdmin):
    list_display = ("establecimiento", "codigo", "nombre", "descripcion")
    list_filter = ("establecimiento",)
    search_fields = ("codigo", "descripcion")


# ---------- Timbrado admin ----------
@admin.register(Timbrado)
class TimbradoAdmin(admin.ModelAdmin):
    list_display = ("numero", "empresa", "inicio_vigencia", "fin_vigencia")
    list_filter = ("empresa",)
    search_fields = ("numero",)


# ---------- FacturaElectronica admin ----------
@admin.register(FacturaElectronica)
class FacturaElectronicaAdmin(admin.ModelAdmin):
    list_display = (
        "numero_factura",
        "empresa",
        "establecimiento",
        "punto_expedicion",
        "timbrado",
        "tipo_impuesto",
        "subtipo_impuesto",
        "fecha_emision",
    )
    list_filter = ("empresa", "establecimiento", "timbrado", "tipo_impuesto")
    search_fields = ("numero_factura",)
    readonly_fields = ("numero_factura", "fecha_emision")  # no editable, se autogenera
