# apps/arqueo_caja/admin.py
from django.contrib import admin
from .models import Caja, AperturaCaja, MovimientoCaja, CierreCaja


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_caja', 'nombre', 'punto_expedicion',
        'estado_actual', 'saldo_actual', 'activo'
    ]
    list_filter = ['estado_actual', 'activo']
    search_fields = ['nombre', 'numero_caja']
    ordering = ['numero_caja']
    readonly_fields = ['numero_caja', 'estado_actual', 'saldo_actual', 'fecha_creacion', 'fecha_modificacion']

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'numero_caja', 'descripcion')
        }),
        ('Punto de Expedición (Obligatorio)', {
            'fields': ('punto_expedicion',),
            'description': 'Todas las cajas emiten facturas y deben tener un punto de expedición asignado (relación 1:1)'
        }),
        ('Estado', {
            'fields': ('estado_actual', 'saldo_actual', 'activo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_apertura', 'caja', 'responsable', 'fecha_hora_apertura',
        'monto_inicial', 'esta_abierta', 'activo'
    ]
    list_filter = ['esta_abierta', 'activo', 'fecha_hora_apertura']
    search_fields = ['codigo_apertura', 'caja__nombre', 'responsable__persona__nombre']
    ordering = ['-fecha_hora_apertura']
    readonly_fields = [
        'codigo_apertura', 'fecha_hora_apertura', 'fecha_creacion', 'fecha_modificacion'
    ]

    fieldsets = (
        ('Identificación', {
            'fields': ('codigo_apertura', 'caja', 'responsable')
        }),
        ('Datos de Apertura', {
            'fields': ('fecha_hora_apertura', 'monto_inicial', 'observaciones_apertura')
        }),
        ('Estado', {
            'fields': ('esta_abierta', 'activo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_movimiento', 'apertura_caja', 'tipo_movimiento', 'concepto',
        'monto', 'metodo_pago', 'fecha_hora_movimiento', 'usuario_registro', 'activo'
    ]
    list_filter = ['tipo_movimiento', 'metodo_pago', 'concepto', 'activo', 'fecha_hora_movimiento']
    search_fields = [
        'numero_movimiento', 'referencia', 'descripcion',
        'apertura_caja__codigo_apertura', 'usuario_registro__persona__nombre'
    ]
    ordering = ['-fecha_hora_movimiento']
    readonly_fields = [
        'numero_movimiento', 'fecha_hora_movimiento', 'fecha_creacion', 'fecha_modificacion'
    ]

    fieldsets = (
        ('Identificación', {
            'fields': ('numero_movimiento', 'apertura_caja', 'comprobante')
        }),
        ('Tipo de Movimiento', {
            'fields': ('tipo_movimiento', 'concepto', 'monto', 'metodo_pago')
        }),
        ('Información Adicional', {
            'fields': ('referencia', 'descripcion')
        }),
        ('Fechas y Auditoría', {
            'fields': ('fecha_hora_movimiento', 'usuario_registro', 'activo')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_cierre', 'apertura_caja', 'fecha_hora_cierre',
        'saldo_teorico_efectivo', 'saldo_real_efectivo', 'diferencia_efectivo',
        'requiere_autorizacion', 'activo'
    ]
    list_filter = ['requiere_autorizacion', 'activo', 'fecha_hora_cierre']
    search_fields = [
        'codigo_cierre', 'apertura_caja__codigo_apertura',
        'apertura_caja__caja__nombre'
    ]
    ordering = ['-fecha_hora_cierre']
    readonly_fields = [
        'codigo_cierre', 'fecha_hora_cierre', 'diferencia_efectivo',
        'diferencia_porcentaje', 'requiere_autorizacion',
        'fecha_creacion', 'fecha_modificacion'
    ]

    fieldsets = (
        ('Identificación', {
            'fields': ('codigo_cierre', 'apertura_caja', 'fecha_hora_cierre')
        }),
        ('Totales Calculados', {
            'fields': (
                'total_efectivo', 'total_tarjetas', 'total_transferencias',
                'total_cheques', 'total_otros_ingresos', 'total_egresos'
            )
        }),
        ('Saldos Teóricos', {
            'fields': ('saldo_teorico_efectivo', 'saldo_teorico_total')
        }),
        ('Arqueo Físico', {
            'fields': ('saldo_real_efectivo', 'detalle_billetes')
        }),
        ('Diferencias', {
            'fields': (
                'diferencia_efectivo', 'diferencia_porcentaje',
                'justificacion_diferencia'
            )
        }),
        ('Autorización', {
            'fields': (
                'requiere_autorizacion', 'autorizado_por',
                'fecha_autorizacion'
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones_cierre',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
