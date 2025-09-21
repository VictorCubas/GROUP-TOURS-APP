from django.db import models
from django.core.exceptions import ValidationError

# === Importaciones de tus apps existentes ===
from apps.tipo_paquete.models import TipoPaquete
from apps.distribuidora.models import Distribuidora
from apps.destino.models import Destino
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio
from apps.hotel.models import Habitacion   # Usamos tu modelo de hotel/habitación existente


# ---------------------------------------------------------------------
#  PAQUETE
# ---------------------------------------------------------------------
class Paquete(models.Model):
    """
    Paquete turístico genérico: contiene información base (destino, moneda,
    servicios incluidos). Las salidas concretas con fechas/precios
    se manejan en SalidaPaquete.
    """
    nombre = models.CharField(max_length=150)

    tipo_paquete = models.ForeignKey(
        TipoPaquete, on_delete=models.PROTECT, related_name="paquetes"
    )
    distribuidora = models.ForeignKey(
        Distribuidora, on_delete=models.PROTECT,
        null=True, blank=True, related_name="paquetes"
    )
    destino = models.ForeignKey(
        Destino, on_delete=models.PROTECT, related_name="paquetes"
    )
    moneda = models.ForeignKey(
        Moneda, on_delete=models.PROTECT,
        null=True, blank=True, related_name="paquetes"
    )

    servicios = models.ManyToManyField(
        Servicio, related_name="paquetes", blank=True,
        help_text="Lista de servicios incluidos en el paquete"
    )

    propio = models.BooleanField(
        default=True,
        help_text="Si es False, debe tener una distribuidora asociada."
    )

    # Estos precios pueden ser referenciales (no obligatorios).
    precio = models.IntegerField(default=0, help_text="Precio referencial")
    sena = models.IntegerField(default=0, help_text="Pago inicial o seña referencial")

    # Fechas generales del paquete (pueden abarcar varias salidas)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    personalizado = models.BooleanField(
        default=False,
        help_text="Si está marcado, no requiere fechas de salida generales."
    )

    cantidad_pasajeros = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Cantidad total de pasajeros (solo para paquetes terrestres propios)"
    )

    # Estado e info extra
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    imagen = models.ImageField(
        upload_to='paquetes/', blank=True, null=True,
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
        if not self.personalizado:
            if not self.fecha_inicio or not self.fecha_fin:
                raise ValidationError(
                    "Las fechas de inicio y fin son requeridas para paquetes no personalizados."
                )
        if (
            self.tipo_paquete and
            self.tipo_paquete.nombre.lower() == "terrestre" and
            self.propio and
            not self.cantidad_pasajeros
        ):
            raise ValidationError(
                "La cantidad de pasajeros es requerida para paquetes terrestres propios."
            )


# ---------------------------------------------------------------------
#  TEMPORADA
# ---------------------------------------------------------------------
class Temporada(models.Model):
    """
    Agrupa un rango de fechas (Alta, Media, Baja) y puede asociarse
    a varios paquetes.  No define precios, solo sirve de agrupador.
    """
    nombre = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    paquetes = models.ManyToManyField(
        Paquete,
        related_name="temporadas",
        blank=True,
        help_text="Paquetes que pertenecen a esta temporada"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Temporada"
        verbose_name_plural = "Temporadas"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicio} → {self.fecha_fin})"


# ---------------------------------------------------------------------
#  SALIDA DE PAQUETE
# ---------------------------------------------------------------------
class SalidaPaquete(models.Model):
    """
    Representa una salida específica de un paquete en una fecha concreta.
    Aquí va el precio 'vigente' y la moneda.
    """
    paquete = models.ForeignKey(
        Paquete,
        on_delete=models.CASCADE,
        related_name="salidas"
    )
    fecha_salida = models.DateField()
    temporada = models.ForeignKey(
        Temporada,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="salidas"
    )
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.PROTECT,
        related_name="salidas"
    )

    # Precio vigente
    precio_actual = models.DecimalField(max_digits=12, decimal_places=2)

    cupo = models.PositiveIntegerField(default=0, help_text="Cupo total de pasajeros")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salida de Paquete"
        verbose_name_plural = "Salidas de Paquete"
        ordering = ["fecha_salida"]

    def __str__(self):
        return f"{self.paquete.nombre} - {self.fecha_salida}"

    # Método para cambiar precio y mantener historial
    def change_price(self, nuevo_precio):
        precio_actual_vigente = self.historial_precios.filter(vigente=True).first()
        if precio_actual_vigente:
            precio_actual_vigente.vigente = False
            precio_actual_vigente.save()
        HistorialPrecioPaquete.objects.create(
            salida=self,
            precio=nuevo_precio,
            vigente=True
        )
        self.precio_actual = nuevo_precio
        self.save()


# ---------------------------------------------------------------------
#  HISTORIAL DE PRECIO DE PAQUETE
# ---------------------------------------------------------------------
class HistorialPrecioPaquete(models.Model):
    """
    Registra todos los cambios de precio para una salida concreta.
    """
    salida = models.ForeignKey(
        SalidaPaquete,
        on_delete=models.CASCADE,
        related_name="historial_precios"
    )
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    vigente = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial Precio Paquete"
        verbose_name_plural = "Historiales Precio Paquete"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"{self.salida} - {self.precio}"


# ---------------------------------------------------------------------
#  HISTORIAL DE PRECIO DE HABITACIÓN
# ---------------------------------------------------------------------
class HistorialPrecioHabitacion(models.Model):
    """
    Permite llevar un control histórico de precios de habitaciones
    de hotel vinculadas a un paquete/salida.
    """
    habitacion = models.ForeignKey(
        Habitacion,
        on_delete=models.CASCADE,
        related_name="historial_precios"
    )
    salida = models.ForeignKey(
        SalidaPaquete,
        on_delete=models.CASCADE,
        related_name="historial_habitaciones"
    )
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    vigente = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial Precio Habitación"
        verbose_name_plural = "Historiales Precio Habitación"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"{self.habitacion.hotel.nombre} - {self.habitacion.numero} - {self.precio}"
