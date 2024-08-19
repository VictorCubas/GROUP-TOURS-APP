from django.db import models

from apps.rol.models import Rol

class Usuario(models.Model):
    '''
    Abstraccion de la clase Usuario
    '''
    documento = models.CharField(max_length=8)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    correo = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)
    
    #personalizamos la tabla en postgres
    class Meta:
        verbose_name = 'Usuario'
        db_table = 'Usuario'

    
    def _str_(self):
        texto = '{} {} {} {} {} {} {}'
        return texto.format(self.documento,
                            self.nombre, 
                            self.apellido,
                            self.telefono,
                            self.correo,
                            self.direccion,
                            self.activo) 
        
class UsuariosRoles(models.Model):
    '''
    Abstraccion de la clase UsuariosRoles
    '''
    
    usuario = models.ForeignKey(Usuario, related_name='usuarios_roles', on_delete=models.SET_NULL, null=True)
    rol = models.ForeignKey(Rol, related_name='usuarios_roles', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'UsuariosRoles'
        db_table = 'UsuariosRoles'