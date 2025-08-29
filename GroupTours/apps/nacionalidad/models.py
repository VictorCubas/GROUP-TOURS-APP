from django.db import models
from django.utils.translation import gettext_lazy as _

class Nacionalidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True,
            error_messages={
                'unique': _('Ya existe una nacionalidad con este nombre.'),
            })  # Ej: Paraguay
    codigo_alpha2 = models.CharField(
        max_length=2,
        unique=True,
        error_messages={
            'unique': _('Ya existe una nacionalidad con este código alpha2.'),
        }) 
    activo = models.BooleanField(default=True)              # Para inactivar sin borrar
    en_uso = models.BooleanField(default=False)              # Para inactivar sin borrar
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)  # Se actualiza al modificar

    class Meta:
        verbose_name = "Nacionalidad"
        verbose_name_plural = "Nacionalidades"
        db_table = 'Nacionalidad'
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo_alpha2})"