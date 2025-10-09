from django.db import models
from apps.ciudad.models import Ciudad
from apps.hotel.models import Hotel

class Destino(models.Model):
    """
    Define los destinos posibles para los paquetes de viaje.
    El nombre del destino es el nombre de la ciudad.
    """

    ciudad = models.ForeignKey(
        Ciudad,
        on_delete=models.PROTECT,
        related_name="destinos",
        help_text="Ciudad que representa este destino."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles adicionales sobre el destino."
    )
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
        # Ordenamos por nombre de ciudad
        ordering = ["ciudad__nombre"]

    def __str__(self):
        # Ejemplo: "París (Francia)"
        return f"{self.ciudad.nombre} ({self.ciudad.pais.nombre})"
    
    
    # 🔹 Propiedad de solo lectura (no se guarda en BD)
    @property
    def zona_geografica(self):
        """
        Devuelve la zona geográfica asociada al país de la ciudad.
        Retorna None si no hay país o zona asociada.
        """
        try:
            return self.ciudad.pais.zona_geografica
        except AttributeError:
            return None
