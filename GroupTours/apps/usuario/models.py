from django.db import models

# Create your models here.

class Users(models.Model):
    '''
    Abstraccion de la clase Usuario
    '''
    document = models.CharField(max_length=8)
    name = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    phoneNumber = models.CharField(max_length=15)
    email = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    status = models.CharField(max_length=1, default='')
    form = models.CharField(max_length=50, default='')
    
    #personalizamos la tabla en posgres
    class Meta:
        verbose_name = 'Usuario'
        db_table = 'Usuario'

    
    def _str_(self):
        texto = '{} {} {}'
        return texto.format(self.document,
                            self.name, 
                            self.lastName,
                            self.phoneNumber,
                            self.email,
                            self.address,
                            self.status,
                            self.formulario) 