from django.db import models
from apps.moneda.models import Moneda

class Hotel(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    
    # Precio por habitación
    precio_habitacion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Precio por habitación"
    )
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.PROTECT,
        related_name="hoteles",
        default=1,
        help_text="Moneda en la que se expresa el precio por habitación"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hotel"
        verbose_name_plural = "Hoteles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
