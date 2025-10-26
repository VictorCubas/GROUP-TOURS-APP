from django.contrib import admin
from .models import ComprobantePago, ComprobantePagoDistribucion, Voucher


class ComprobantePagoDistribucionInline(admin.TabularInline):
    model = ComprobantePagoDistribucion
    extra = 1
    fields = ('pasajero', 'monto', 'observaciones')
    readonly_fields = ('fecha_creacion',)


@admin.register(ComprobantePago)
class ComprobantePagoAdmin(admin.ModelAdmin):
    list_display = ('numero_comprobante', 'reserva', 'tipo', 'monto', 'metodo_pago', 'fecha_pago', 'activo')
    list_filter = ('tipo', 'metodo_pago', 'activo', 'fecha_pago')
    search_fields = ('numero_comprobante', 'reserva__codigo', 'referencia')
    readonly_fields = ('numero_comprobante', 'fecha_pago', 'fecha_creacion', 'fecha_modificacion')
    inlines = [ComprobantePagoDistribucionInline]

    fieldsets = (
        ('Información del Comprobante', {
            'fields': ('reserva', 'numero_comprobante', 'fecha_pago', 'tipo')
        }),
        ('Detalles del Pago', {
            'fields': ('monto', 'metodo_pago', 'referencia', 'empleado')
        }),
        ('Documentación', {
            'fields': ('pdf_generado', 'observaciones')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_modificacion')
        }),
    )


@admin.register(ComprobantePagoDistribucion)
class ComprobantePagoDistribucionAdmin(admin.ModelAdmin):
    list_display = ('comprobante', 'pasajero', 'monto', 'fecha_creacion')
    list_filter = ('fecha_creacion',)
    search_fields = ('comprobante__numero_comprobante', 'pasajero__persona__nombre')
    readonly_fields = ('fecha_creacion',)


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('codigo_voucher', 'reserva', 'fecha_emision', 'activo')
    list_filter = ('activo', 'fecha_emision')
    search_fields = ('codigo_voucher', 'reserva__codigo')
    readonly_fields = ('codigo_voucher', 'fecha_emision', 'fecha_creacion', 'fecha_modificacion')

    fieldsets = (
        ('Información del Voucher', {
            'fields': ('reserva', 'codigo_voucher', 'fecha_emision')
        }),
        ('Documentación', {
            'fields': ('qr_code', 'pdf_generado', 'url_publica')
        }),
        ('Información Adicional', {
            'fields': ('instrucciones_especiales', 'contacto_emergencia')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_modificacion')
        }),
    )

    actions = ['generar_qr_codes']

    def generar_qr_codes(self, request, queryset):
        """Acción para regenerar códigos QR de vouchers seleccionados"""
        for voucher in queryset:
            voucher.generar_qr()
            voucher.save()
        self.message_user(request, f"{queryset.count()} códigos QR generados exitosamente.")
    generar_qr_codes.short_description = "Generar códigos QR"
