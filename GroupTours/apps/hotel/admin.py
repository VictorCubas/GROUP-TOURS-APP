from django.contrib import admin
from .models import CadenaHotelera, Hotel, Habitacion, TipoHabitacion, Servicio

# -------------------- CADENA HOTELERA --------------------
@admin.register(CadenaHotelera)
class CadenaHoteleraAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'activo', 'fecha_creacion', 'fecha_modificacion')
    search_fields = ('nombre',)
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')


class HabitacionInline(admin.TabularInline):
    model = Habitacion
    extra = 1
    fields = ('tipo_habitacion', 'precio_noche', 'moneda', 'activo')


# -------------------- HOTEL --------------------
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nombre', 'ciudad', 'get_pais', 'cadena', 'activo',
        'fecha_creacion', 'fecha_modificacion'
    )
    list_filter = ('activo', 'ciudad__pais', 'cadena')
    search_fields = ('nombre', 'ciudad__nombre', 'ciudad__pais__nombre', 'cadena__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    
    inlines = [HabitacionInline]

    def get_pais(self, obj):
        return obj.ciudad.pais.nombre
    get_pais.short_description = 'País'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "servicios":
            # Solo servicios de tipo 'hotel' activos
            kwargs["queryset"] = Servicio.objects.filter(tipo='hotel', activo=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# -------------------- TIPO HABITACION --------------------
@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'capacidad', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'capacidad')
    search_fields = ('nombre',)
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')


# -------------------- HABITACION --------------------
@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'hotel', 'tipo_habitacion', 'precio_noche', 'moneda', 'activo')
    list_filter = ('activo', 'tipo_habitacion', 'moneda', 'hotel__ciudad')
    search_fields = ('tipo_habitacion__nombre', 'hotel__nombre', 'hotel__ciudad__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "servicios":
            kwargs["queryset"] = Servicio.objects.filter(tipo='habitacion', activo=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# -------------------- SERVICIO --------------------
# @admin.register(Servicio)
# class ServicioAdmin(admin.ModelAdmin):
#     list_display = ['id', 'nombre', 'tipo', 'activo', 'en_uso', 'fecha_creacion', 'fecha_modificacion']
#     list_filter = ['tipo', 'activo', 'en_uso']
#     search_fields = ['nombre', 'descripcion']
#     readonly_fields = ('fecha_creacion', 'fecha_modificacion')
