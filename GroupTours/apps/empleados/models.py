from django.db import models

# Create your models here.

class Persona(models.Model):
    '''
    Abstraccion de la clase Persona
    '''
    
    SOLTERO = 'S'
    CASADO = 'C'
    VIUDO = 'V'
    
    ESTADO_CIVIL = [
        (SOLTERO, 'Soltero'),
        (CASADO, 'Casado'),
        (VIUDO, 'Viudo'),
    ]
    
    FEMENINO = 'F'
    MASCULINO = 'M'
    GENEROS = (
        (FEMENINO, ('Femenino')),
        (MASCULINO, ('Masculino'))
    )
    
    CI = 'CI'
    DNI = 'DNI'
    PASSPORT = 'PASAPORTE'
    TIPOS_DOCUMENTOS = (
        (CI, ('CI')),
        (DNI, ('DNI')),
        (PASSPORT, ('Pasaporte'))
    )
    
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    cedula = models.CharField(max_length=50, default='')
    direccion = models.CharField(max_length=250, default='')
    estado_civil = models.CharField(
        max_length=1,
        choices=ESTADO_CIVIL,
        default=SOLTERO
    )
    
    sexo = models.CharField(
        max_length=1,
        choices=GENEROS,
        default=FEMENINO
    )
    
    documento = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name='Tipos de documentos',
        choices=TIPOS_DOCUMENTOS,
        default=CI
    )
    
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
    en_uso = models.BooleanField(default=False)
    
    #personalizamos la tabla en postgre
    class Meta:
        verbose_name = 'Empleado'
        db_table = 'Empleado'
    
    def _str_(self):
        texto = '{} {} {} {}'
        return texto.format(self.nombre, self.apellido, self.descripcion, self.tipo)
