from django.db import models

class TipoPaquete(models.Model):
    """
    Define los diferentes tipos de paquetes turísticos.
    Ejemplos:
    - Aéreo
    - Terrestre
    - Acuático
    - Espacial
    """

    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre del tipo de paquete. Ej: 'Aéreo', 'Terrestre', 'Acuático', 'Espacial'."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles o características del tipo de paquete."
    )

    activo = models.BooleanField(default=True)   # Para inactivar sin borrar
    en_uso = models.BooleanField(default=False)  # Para bloquear eliminación si está vinculado a paquetes
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de Paquete"
        verbose_name_plural = "Tipos de Paquetes"
        db_table = "TipoPaquete"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
