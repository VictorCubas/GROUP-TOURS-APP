from django.db import models

# Create your models here.

class Persona(models.Model):
    '''
    Abstraccion de la clase Persona
    '''
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    cedula = models.CharField(max_length=50, default='')
    fecha_nacimiento = models.DateTimeField()
    class Meta:
        abstract = True

class Empleado(Persona):
    '''
    Abstraccion de la clase Empleado
    '''
    descripcion = models.CharField(max_length=200, default='')
    tipo = models.CharField(max_length=1, default='')
    activo = models.BooleanField(default=True)
    
    #personalizamos la tabla en postgre
    class Meta:
        verbose_name = 'Empleado'
        db_table = 'Empleado'
    
    def _str_(self):
        texto = '{} {} {} {}'
        return texto.format(self.nombre, self.apellido, self.descripcion, self.tipo)
