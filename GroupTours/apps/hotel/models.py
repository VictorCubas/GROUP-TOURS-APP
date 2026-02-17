from django.db import models
from apps.servicio.models import Servicio
from apps.moneda.models import Moneda
from apps.ciudad.models import Ciudad

class CadenaHotelera(models.Model):
    """
    Representa una cadena de hoteles, como 'Hard Rock', 'Hilton', etc.
    """
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cadena Hotelera"
        verbose_name_plural = "Cadenas Hoteleras"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Hotel(models.Model):
    """
    Hotel individual que puede pertenecer a una cadena.
    """
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    estrellas = models.PositiveSmallIntegerField(default=4)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    ciudad = models.ForeignKey(
        Ciudad,
        on_delete=models.PROTECT,
        related_name="hoteles"
    )
    cadena = models.ForeignKey(
        CadenaHotelera,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="hoteles"
    )
    servicios = models.ManyToManyField(
        Servicio,
        blank=True,
        related_name="hoteles"
    )
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hotel"
        verbose_name_plural = "Hoteles"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ciudad.nombre}, {self.ciudad.pais.nombre})"


class TipoHabitacion(models.Model):
    """
    Catálogo de tipos de habitación gestionable por el usuario.
    Ejemplos: "Doble Standard", "Suite Presidencial", "Triple Vista Mar".
    """
    nombre = models.CharField(max_length=80, unique=True)
    capacidad = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de Habitación"
        verbose_name_plural = "Tipos de Habitación"
        ordering = ["nombre"]
        db_table = "tipo_habitacion"

    def __str__(self):
        return f"{self.nombre} (Cap: {self.capacidad})"


class Habitacion(models.Model):
    """
    Relación entre un hotel y un tipo de habitación con su precio.
    """
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="habitaciones"
    )
    tipo_habitacion = models.ForeignKey(
        TipoHabitacion,
        on_delete=models.PROTECT,
        related_name="habitaciones",
        help_text="Tipo de habitación"
    )
    precio_noche = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name="habitaciones")
    servicios = models.ManyToManyField(Servicio, blank=True, related_name="habitaciones")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Habitación"
        verbose_name_plural = "Habitaciones"
        unique_together = ("hotel", "tipo_habitacion")
        ordering = ["hotel"]

    def __str__(self):
        return f"{self.hotel.nombre} - {self.tipo_habitacion.nombre}"
