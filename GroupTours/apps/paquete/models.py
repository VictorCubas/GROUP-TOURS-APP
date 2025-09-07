from django.db import models
from django.core.exceptions import ValidationError
from apps.tipo_paquete.models import TipoPaquete
from apps.distribuidora.models import Distribuidora
from apps.destino.models import Destino
from apps.moneda.models import Moneda

class Paquete(models.Model):
    nombre = models.CharField(max_length=150)

    tipo_paquete = models.ForeignKey(
        TipoPaquete,
        on_delete=models.PROTECT,
        related_name="paquetes"
    )

    distribuidora = models.ForeignKey(
        Distribuidora,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paquetes"
    )

    destino = models.ForeignKey(
        Destino,
        on_delete=models.PROTECT,
        related_name="paquetes"
    )
    
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.PROTECT,
        related_name="paquetes",
        null=True,
        blank=True
    )

    propio = models.BooleanField(
        default=True,
        help_text="Marcar si el paquete es propio de la empresa. Si es False, debe tener una distribuidora."
    )

    # Precio total del paquete
    precio = models.IntegerField(
        default=0,
        help_text="Precio total del paquete"
    )

    # Pago inicial
    sena = models.IntegerField(
        default=0,
        help_text="Pago inicial o seña del paquete"
    )

    # Fechas
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de inicio del paquete"
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de fin del paquete"
    )

    # Si es personalizado no requiere fecha de salida
    personalizado = models.BooleanField(
        default=False,
        help_text="Si está marcado, no requiere fechas de salida"
    )

    # Cantidad de pasajeros totales (solo para paquetes terrestres propios)
    cantidad_pasajeros = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad total de pasajeros (solo para paquetes terrestres propios)"
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Campo de imagen
    imagen = models.ImageField(
        upload_to='paquetes/',
        blank=True,
        null=True,
        help_text="Imagen representativa del paquete"
    )

    class Meta:
        verbose_name = "Paquete"
        verbose_name_plural = "Paquetes"
        db_table = "Paquete"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        """
        Validaciones personalizadas:
        - Si personalizado=False, fecha_inicio y fecha_fin son requeridas.
        - Si es paquete terrestre propio, cantidad_pasajeros es requerida.
        """
        # Validar fechas si no es personalizado
        if not self.personalizado:
            if not self.fecha_inicio or not self.fecha_fin:
                raise ValidationError("Las fechas de inicio y fin son requeridas para paquetes no personalizados.")

        # Validar pasajeros solo si es terrestre y propio
        if (
            self.tipo_paquete and 
            self.tipo_paquete.nombre.lower() == "terrestre" and 
            self.propio and 
            not self.cantidad_pasajeros
        ):
            raise ValidationError("La cantidad de pasajeros es requerida para paquetes terrestres propios.")
