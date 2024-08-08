from django.db import models

# Create your models here.

class Empleado(models.Model):
    '''
    Abstraccion de la clase Empleado
    '''
    
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=200, default='')
    tipo = models.CharField(max_length=1, default='')
    formulario = models.CharField(max_length=50, default='')
    activo = models.BooleanField(default=True)
    
    #personalizamos la tabla en postgre
    class Meta:
        verbose_name = 'Empleado'
        db_table = 'Empleado'
    
    def _str_(self):
        texto = '{} {} {} {}'
        return texto.format(self.nombre, self.apellido, self.descripcion, self.tipo)
