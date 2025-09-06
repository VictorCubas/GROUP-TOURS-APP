from django.db import models
from apps.tipo_paquete.models import TipoPaquete
from apps.distribuidora.models import Distribuidora
from apps.destino.models import Destino

class Paquete(models.Model):
    nombre = models.CharField(max_length=150)

    tipo_paquete = models.ForeignKey(
        TipoPaquete,
        on_delete=models.PROTECT,
        related_name="paquetes"
    )

    distribuidora = models.ForeignKey(
        Distribuidora,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paquetes"
    )

    destino = models.ForeignKey(
        Destino,
        on_delete=models.PROTECT,
        related_name="paquetes"
    )

    propio = models.BooleanField(
        default=True,
        help_text="Marcar si el paquete es propio de la empresa. Si es False, debe tener una distribuidora."
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Campo de imagen
    imagen = models.ImageField(
        upload_to='paquetes/',  # Carpeta dentro de MEDIA_ROOT
        blank=True,
        null=True,
        help_text="Imagen representativa del paquete"
    )

    class Meta:
        verbose_name = "Paquete"
        verbose_name_plural = "Paquetes"
        db_table = "Paquete"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
