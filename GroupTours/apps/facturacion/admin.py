from django.contrib import admin
from .models import (
    Empresa,
    Establecimiento,
    PuntoExpedicion,
    Timbrado,
    TipoImpuesto,
    SubtipoImpuesto,
    FacturaElectronica,
    DetalleFactura
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


# ---------- DetalleFactura inline para FacturaElectronica ----------
class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 0
    readonly_fields = ('subtotal',)
    verbose_name = "Detalle de Factura"
    verbose_name_plural = "Detalles de Factura"


# ---------- FacturaElectronica admin ----------
@admin.register(FacturaElectronica)
class FacturaElectronicaAdmin(admin.ModelAdmin):
    list_display = (
        "numero_factura",
        "empresa",
        "reserva",
        "tipo_facturacion",  # NUEVO
        "pasajero",  # NUEVO
        "cliente_nombre",
        "total_general",
        "fecha_emision",
        "es_configuracion",
        "activo",
    )
    list_filter = (
        "empresa",
        "establecimiento",
        "timbrado",
        "tipo_impuesto",
        "tipo_facturacion",  # NUEVO
        "es_configuracion",
        "activo"
    )
    search_fields = ("numero_factura", "cliente_nombre", "cliente_numero_documento")
    readonly_fields = (
        "numero_factura",
        "fecha_emision",
        "total_exenta",
        "total_gravada_5",
        "total_gravada_10",
        "total_iva_5",
        "total_iva_10",
        "total_iva",
        "total_general"
    )
    list_editable = ("activo",)
    inlines = [DetalleFacturaInline]

    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'establecimiento', 'punto_expedicion', 'timbrado', 'es_configuracion', 'activo')
        }),
        ('Impuestos', {
            'fields': ('tipo_impuesto', 'subtipo_impuesto')
        }),
        ('Reserva y Facturación', {
            'fields': ('reserva', 'tipo_facturacion', 'pasajero'),
            'classes': ('collapse',)
        }),
        ('Factura', {
            'fields': ('numero_factura', 'fecha_emision', 'condicion_venta', 'moneda')
        }),
        ('Datos del Cliente', {
            'fields': ('cliente_tipo_documento', 'cliente_numero_documento', 'cliente_nombre',
                      'cliente_direccion', 'cliente_telefono', 'cliente_email'),
            'classes': ('collapse',)
        }),
        ('Totales', {
            'fields': ('total_exenta', 'total_gravada_5', 'total_gravada_10',
                      'total_iva_5', 'total_iva_10', 'total_iva', 'total_general'),
            'classes': ('collapse',)
        }),
    )


# ---------- DetalleFactura admin ----------
@admin.register(DetalleFactura)
class DetalleFacturaAdmin(admin.ModelAdmin):
    list_display = ("factura", "numero_item", "descripcion", "cantidad", "precio_unitario", "subtotal")
    list_filter = ("factura",)
    search_fields = ("descripcion",)
    readonly_fields = ("subtotal",)
