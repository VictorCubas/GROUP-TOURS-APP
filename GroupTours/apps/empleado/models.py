from django.db import models

from apps.persona.models import Persona
from apps.puesto.models import Puesto
from apps.tipo_remuneracion.models import TipoRemuneracion

class Empleado(models.Model):
    persona = models.OneToOneField(
        Persona,
        on_delete=models.CASCADE,
        related_name='empleado',
        help_text="Persona asociada al empleado"
    )
    puesto = models.ForeignKey(
        Puesto,
        on_delete=models.PROTECT,
        related_name='empleados',
        help_text="Puesto que ocupa el empleado"
    )
    tipo_remuneracion = models.ForeignKey(
        TipoRemuneracion,
        on_delete=models.PROTECT,
        related_name='empleados',
        help_text="Tipo de remuneración del empleado"
    )
    salario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Salario base del empleado, si aplica"
    )
    porcentaje_comision = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Porcentaje de comisión del empleado, si aplica"
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        db_table = "Empleado"
        # ordering = ["persona__nombre"]

    def __str__(self):
        return f"{self.persona.nombre} ({self.puesto.nombre})"
