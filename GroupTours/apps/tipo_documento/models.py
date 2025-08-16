from django.db import models

class TipoDocumento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)  # Ej: DNI, Pasaporte
    descripcion = models.TextField(blank=True, null=True)   # Info adicional
    activo = models.BooleanField(default=True)              # Para inactivar sin borrar
    en_uso = models.BooleanField(default=False)             # Para bloquear eliminación
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)  # Se actualiza al modificar

    class Meta:
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documentos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre