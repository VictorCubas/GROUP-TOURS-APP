from django.db import models

class TipoRemuneracion(models.Model):
    """
    Define las diferentes formas de remuneración que puede tener un empleado.
    Ejemplos:
    - Salario fijo
    - Comisión
    - Mixto (fijo + comisión)
    """

    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre del tipo de remuneración. Ej: 'Salario fijo', 'Comisión', 'Mixto'."
    )
    
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles o reglas adicionales del contrato"
    )
    
    activo = models.BooleanField(default=True)   # Para inactivar sin borrar
    en_uso = models.BooleanField(default=False)  # Para bloquear eliminación
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de Remuneracion"
        verbose_name_plural = "Tipos de Remuneraciones"
        db_table = "TipoRemuneracion"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
