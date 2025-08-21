from django.db import models
from datetime import date
from apps.nacionalidad.models import Nacionalidad
from apps.tipo_documento.models import TipoDocumento


class Persona(models.Model):
    """
    Clase base para personas.
    """

    # Constantes de género
    FEMENINO = 'F'
    MASCULINO = 'M'
    GENEROS = [
        (FEMENINO, 'Femenino'),
        (MASCULINO, 'Masculino'),
    ]

    # Campos comunes
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        related_name='personas'
    )
    documento = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=30)
    direccion = models.CharField(max_length=250, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Persona'
        db_table = 'Persona'

    def __str__(self):
        return self.documento


class PersonaFisica(Persona):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    sexo = models.CharField(
        max_length=1,
        choices=Persona.GENEROS,
        default=Persona.FEMENINO
    )
    nacionalidad = models.ForeignKey(
        Nacionalidad,
        on_delete=models.CASCADE,
        related_name="personas_fisicas"
    )

    @property
    def edad(self):
        if self.fecha_nacimiento:
            today = date.today()
            return (
                today.year - self.fecha_nacimiento.year
                - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
            )
        return None
    
    
    class Meta:
        db_table = 'PersonaFisica'
        verbose_name = 'Persona Física'

    def __str__(self):
        return f"{self.nombre} {self.apellido or ''}".strip()


class PersonaJuridica(Persona):
    razon_social = models.CharField(max_length=200)
    representante = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        db_table = 'PersonaJuridica'
        verbose_name = 'Persona Jurídica'
        
    def __str__(self):
        return self.razon_social
