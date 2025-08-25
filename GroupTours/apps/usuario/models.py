# apps/usuario/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.empleado.models import Empleado
from apps.rol.models import Rol

class Usuario(AbstractUser):
    empleado = models.OneToOneField(
        Empleado,
        on_delete=models.CASCADE,
        related_name="usuario",
        help_text="Empleado asociado a este usuario del sistema",
        null=True,  # permite nulos
        blank=True, # permite dejar vacío en formularios/admin
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        related_name="usuarios",
        help_text="Rol asignado al usuario",
        null=True,  # permite nulos
        blank=True, # permite dejar vacío en formularios/admin
    )
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuario"

    def __str__(self):
        return f"{self.username} - {self.empleado.persona.nombre}"
