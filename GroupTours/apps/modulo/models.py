from django.db import models

# Create your models here.

class Modulo(models.Model):
    '''
    Abstraccion de la clase Modulo
    '''
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=200, default='')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True)  # Se actualiza al modificar
    en_uso = models.BooleanField(default=False)
    
    #personalizamos la tabla en posgres
    class Meta:
        verbose_name = 'Modulo'
        db_table = 'Modulo'

    
    def _str_(self):
        texto = '{} {} {}'
        return texto.format(self.nombre, self.descripcion)
