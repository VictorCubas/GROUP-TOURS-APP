from django.db import models

from apps.permiso.models import Permiso
from django.utils import timezone

# Create your models here.
class RolesPermisos(models.Model):
    '''
    Abstraccion de la clase RolesPermisos
    '''
    
    rol = models.ForeignKey('Rol', related_name='roles_permisos', on_delete=models.SET_NULL, null=True)
    permiso = models.ForeignKey(Permiso, related_name='roles_permisos', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'RolesPermisos'
        db_table = 'RolesPermisos'
        

class Rol(models.Model):
    '''
    Abstraccion de la clase Rol
    '''
    
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=200, default='')
    permisos = models.ManyToManyField(Permiso, through=RolesPermisos, related_name='rol_permiso')
    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)  # Se actualiza al modificar
    
    #personalizamos la tabla en postgres
    class Meta:
        verbose_name = 'Rol'
        db_table = 'Rol'

    
    def _str_(self):
        texto = '{} {} {}'
        return texto.format(self.nombre, self.descripcion, self.fecha_creacion)
