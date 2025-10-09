from django.db import models
from django.utils import timezone

class ZonaGeografica(models.Model):
    """
    Representa una zona o región geográfica que agrupa países.
    Ejemplo: Sudamérica, Europa, Sudeste Asiático.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Zona Geográfica"
        verbose_name_plural = "Zonas Geográficas"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre
