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
        null=True,
        blank=True,
    )
    roles = models.ManyToManyField(
        Rol,
        related_name="usuarios",
        help_text="Roles asignado al usuario",
    )
    activo = models.BooleanField(default=True)
    debe_cambiar_contrasenia = models.BooleanField(default=True) 
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuario"

    def __str__(self):
        empleado_nombre = getattr(self.empleado.persona, 'nombre', '') if self.empleado else ''
        return f"{self.username} - {empleado_nombre}"