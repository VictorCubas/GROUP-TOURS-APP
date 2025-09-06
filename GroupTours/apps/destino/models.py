from django.db import models
from apps.nacionalidad.models import Nacionalidad
from apps.hotel.models import Hotel

class Destino(models.Model):
    """
    Define los destinos posibles para los paquetes de viaje.
    """

    nombre = models.CharField(
        max_length=150,
        unique=True,
        help_text="Nombre del destino."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles adicionales sobre el destino."
    )
    pais = models.ForeignKey(
        Nacionalidad,
        on_delete=models.PROTECT,
        related_name='destinos',
        blank=True,
        null=True,
        help_text="País al que pertenece el destino (opcional)."
    )

    # Relación muchos a muchos con hoteles
    hoteles = models.ManyToManyField(
        Hotel,
        blank=True,
        related_name="destinos",
        help_text="Hoteles disponibles en este destino"
    )

    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Destino"
        verbose_name_plural = "Destinos"
        db_table = "Destino"
        ordering = ["nombre"]

    def __str__(self):
        if self.pais:
            return f"{self.nombre} ({self.pais.nombre})"
        return self.nombre
