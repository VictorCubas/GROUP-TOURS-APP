from django.db import models

# Create your models here.

class Permiso(models.Model):
    '''
    Abstraccion de la clase Permiso
    '''
    
    TIPO_CHOICES = [
        ('C', 'Crear'),
        ('R', 'Leer'),
        ('U', 'Actualizar'),
        ('D', 'Eliminar'),
        ('E', 'Exportar'),
    ]

    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=200, default='')
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default='C')
    modulo = models.CharField(max_length=50, default='')
    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    
    #personalizamos la tabla en posgres
    class Meta:
        verbose_name = 'Permiso'
        db_table = 'Permiso'

    
    def _str_(self):
        texto = '{} {} {}'
        return texto.format(self.nombre, self.descripcion, self.tipo)
