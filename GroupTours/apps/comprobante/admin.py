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
    list_display = ('codigo_voucher', 'get_pasajero_nombre', 'get_reserva_codigo', 'get_es_titular', 'fecha_emision', 'activo')
    list_filter = ('activo', 'fecha_emision', 'pasajero__es_titular')
    search_fields = ('codigo_voucher', 'pasajero__reserva__codigo', 'pasajero__persona__nombre', 'pasajero__persona__apellido')
    readonly_fields = ('codigo_voucher', 'fecha_emision', 'fecha_creacion', 'fecha_modificacion')

    fieldsets = (
        ('Información del Voucher', {
            'fields': ('pasajero', 'codigo_voucher', 'fecha_emision')
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

    def get_pasajero_nombre(self, obj):
        """Mostrar nombre completo del pasajero"""
        return f"{obj.pasajero.persona.nombre} {obj.pasajero.persona.apellido}"
    get_pasajero_nombre.short_description = 'Pasajero'

    def get_reserva_codigo(self, obj):
        """Mostrar código de la reserva"""
        return obj.pasajero.reserva.codigo
    get_reserva_codigo.short_description = 'Reserva'

    def get_es_titular(self, obj):
        """Mostrar si es titular"""
        return obj.pasajero.es_titular
    get_es_titular.short_description = 'Es Titular'
    get_es_titular.boolean = True

    def generar_qr_codes(self, request, queryset):
        """Acción para regenerar códigos QR de vouchers seleccionados"""
        for voucher in queryset:
            voucher.generar_qr()
            voucher.save()
        self.message_user(request, f"{queryset.count()} códigos QR generados exitosamente.")
    generar_qr_codes.short_description = "Generar códigos QR"
