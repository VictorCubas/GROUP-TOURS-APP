from django.db import models

class Moneda(models.Model):
    nombre = models.CharField(max_length=50, unique=True, help_text="Nombre de la moneda. Ej: 'Dólar', 'Guaraní'")
    simbolo = models.CharField(max_length=5, help_text="Símbolo de la moneda. Ej: '$', 'Gs'")
    codigo = models.CharField(max_length=3, unique=True, help_text="Código de la moneda. Ej: 'USD', 'PYG'")
    activo = models.BooleanField(default=True, help_text="Indica si la moneda está activa")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
