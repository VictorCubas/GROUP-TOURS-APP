from django.db import models

class Distribuidora(models.Model):
    """
    Define las distribuidoras (operadores) disponibles.
    """

    nombre = models.CharField(
        max_length=150,
        unique=True,
        help_text="Nombre de la distribuidora u operador."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles adicionales sobre la distribuidora."
    )
    telefono = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Número de contacto de la distribuidora (opcional)."
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Correo de contacto de la distribuidora (opcional)."
    )
    activo = models.BooleanField(default=True)   # Para inactivar sin borrar
    en_uso = models.BooleanField(default=False)  # Para bloquear eliminación
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Distribuidora"
        verbose_name_plural = "Distribuidoras"
        db_table = "Distribuidora"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
