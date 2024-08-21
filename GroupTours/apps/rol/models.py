from django.db import models

from apps.permiso.models import Permiso

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
    
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=200, default='')
    permisos = models.ManyToManyField(Permiso, through=RolesPermisos, related_name='rol_permiso')
    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    
    #personalizamos la tabla en postgres
    class Meta:
        verbose_name = 'Rol'
        db_table = 'Rol'

    
    def _str_(self):
        texto = '{} {} {}'
        return texto.format(self.nombre, self.descripcion, self.tipo)
