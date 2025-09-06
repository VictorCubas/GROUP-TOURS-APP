from django.db import models

class Servicio(models.Model):
    """
    Define los diferentes servicios incluidos en un paquete.
    Ejemplos:
    - Pasajes aéreos desde Asunción
    - Traslado in/out
    - Alojamiento 5 noches
    - Equipaje de mano 10kg
    - Tasas de embarque
    - Desayuno
    - Asistencia básica al pasajero
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre del servicio, ej: 'Traslado in/out', 'Desayuno'."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles adicionales sobre el servicio."
    )
    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        db_table = "Servicio"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre