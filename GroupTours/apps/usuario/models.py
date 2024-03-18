from django.db import models

# Create your models here.

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
    estado = models.CharField(max_length=1, default='A')
    
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
                            self.estado) 