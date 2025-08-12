from django.db import models

from apps.modulo.models import Modulo

# Create your models here.

class Permiso(models.Model):
    '''
    Abstraccion de la clase Permiso
    '''
    
    TIPO_CHOICES = [
        ('C', 'Creacion'),
        ('R', 'Lectura'),
        ('U', 'Modificacion'),
        ('D', 'Eliminacion'),
        ('E', 'Exportar'),
    ]

    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200, default='')
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default='C')
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name="permisos")
    activo = models.BooleanField(default=True)
    en_uso = models.BooleanField(default=False)
    fechaCreacion = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name='fecha creacion')
    
    #personalizamos la tabla en posgres
    class Meta:
        verbose_name = 'Permiso'
        db_table = 'Permiso'

    
    def _str_(self):
        texto = '{} {} {}'
        return texto.format(self.nombre, self.descripcion, self.tipo)
