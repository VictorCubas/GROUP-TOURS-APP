# apps/ubicaciones/models.py
from django.db import models
from apps.nacionalidad.models import Nacionalidad   # País

class Ciudad(models.Model):
    """
    Ciudad asociada a un país.
    """
    nombre = models.CharField(
        max_length=150,
        unique=True,
        help_text="Nombre de la ciudad, ej: Asunción."
    )
    pais = models.ForeignKey(
        Nacionalidad,
        on_delete=models.PROTECT,
        related_name="ciudades",
        help_text="País al que pertenece la ciudad."
    )
    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"
        db_table = "Ciudad"
        ordering = ["nombre"]

    # metodo de retorno
    def __str__(self):
        return f"{self.nombre} ({self.pais.nombre})"
