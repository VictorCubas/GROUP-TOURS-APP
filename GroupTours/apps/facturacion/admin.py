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
    list_display = ("nombre", "descripcion", "activo")
    search_fields = ("nombre",)
    inlines = [SubtipoImpuestoInline]
    list_filter = ("activo",)
    list_editable = ("activo",)


# ---------- SubtipoImpuesto admin (opcional para gestión directa) ----------
@admin.register(SubtipoImpuesto)
class SubtipoImpuestoAdmin(admin.ModelAdmin):
    list_display = ("tipo_impuesto", "nombre", "porcentaje", "activo")
    list_filter = ("tipo_impuesto", "activo")
    search_fields = ("nombre",)
    list_editable = ("activo",)


# ---------- Empresa admin ----------
@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ruc", "telefono", "correo", "activo")
    search_fields = ("nombre", "ruc")
    list_filter = ("activo",)
    list_editable = ("activo",)


# ---------- Establecimiento admin ----------
@admin.register(Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display = ("empresa", "codigo", "nombre", "direccion", "activo")
    list_filter = ("empresa", "activo")
    search_fields = ("codigo", "direccion")
    list_editable = ("activo",)


# ---------- PuntoExpedicion admin ----------
@admin.register(PuntoExpedicion)
class PuntoExpedicionAdmin(admin.ModelAdmin):
    list_display = ("establecimiento", "codigo", "nombre", "descripcion", "activo")
    list_filter = ("establecimiento", "activo")
    search_fields = ("codigo", "descripcion")
    list_editable = ("activo",)


# ---------- Timbrado admin ----------
@admin.register(Timbrado)
class TimbradoAdmin(admin.ModelAdmin):
    list_display = ("numero", "empresa", "inicio_vigencia", "fin_vigencia", "activo")
    list_filter = ("empresa", "activo")
    search_fields = ("numero",)
    list_editable = ("activo",)


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
        "es_configuracion",
        "activo",
    )
    list_filter = ("empresa", "establecimiento", "timbrado", "tipo_impuesto", "activo")
    search_fields = ("numero_factura",)
    readonly_fields = ("numero_factura", "fecha_emision")
    list_editable = ("activo",)
