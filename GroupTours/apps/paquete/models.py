from django.db import models, transaction
from django.core.exceptions import ValidationError

# === Importaciones de tus apps existentes ===
from apps.tipo_paquete.models import TipoPaquete
from apps.distribuidora.models import Distribuidora
from apps.destino.models import Destino
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio
from apps.hotel.models import Hotel, Habitacion  # Importamos también Hotel

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
    Aquí se guarda el rango de precios calculado en base a los hoteles
    y habitaciones asociados.
    """
    paquete = models.ForeignKey(
        Paquete,
        on_delete=models.CASCADE,
        related_name="salidas"
    )
    fecha_salida = models.DateField()
    fecha_regreso = models.DateField(null=True, blank=True)
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

    # NUEVO: hoteles disponibles para esta salida
    hoteles = models.ManyToManyField(
        Hotel,
        related_name="salidas_paquete",
        help_text="Hoteles disponibles para esta salida del paquete"
    )

    # Rango oficial de precios (calculado en create_salida_paquete)
    precio_actual = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Precio mínimo calculado (por persona, según habitación más económica)"
    )
    precio_final = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text="Precio máximo de las habitaciones por cantidad de noches (puede ser nulo)"
    )

    cupo = models.PositiveIntegerField(default=0, help_text="Cupo total de pasajeros", null=True, blank=True)
    senia = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Monto de la seña del pago"
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salida de Paquete"
        verbose_name_plural = "Salidas de Paquete"
        ordering = ["fecha_salida"]

    def __str__(self):
        return f"{self.paquete.nombre} - {self.fecha_salida}"

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

# ---------------------------------------------------------------------
#  FUNCIÓN DE CREACIÓN DE SALIDA CON CÁLCULO DE RANGO
# ---------------------------------------------------------------------
@transaction.atomic
def create_salida_paquete(data):
    salida = SalidaPaquete.objects.create(
        paquete_id=data["paquete_id"],
        fecha_salida=data["fecha_salida"],
        fecha_regreso=data.get("fecha_regreso"),
        moneda_id=data["moneda_id"],
        cupo=data.get("cupo", 0),
        senia=data.get("senia"),
        precio_actual=0,  # temporal, se recalcula abajo
        precio_final=None  # puede ser nulo inicialmente
    )

    # Asociar hoteles
    salida.hoteles.set(data["hoteles_ids"])

    # Calcular cantidad de noches
    if salida.fecha_regreso:
        noches = (salida.fecha_regreso - salida.fecha_salida).days
    else:
        noches = 1  # si no hay fecha de regreso, consideramos 1 noche

    # Buscar todas las habitaciones activas de los hoteles seleccionados
    habitaciones = Habitacion.objects.filter(
        hotel__in=data["hoteles_ids"], activo=True
    )

    if habitaciones.exists():
        precios = [h.precio_noche * noches for h in habitaciones]
        salida.precio_actual = min(precios)  # precio mínimo
        salida.precio_final = max(precios) if precios else None  # precio máximo, puede ser nulo
        salida.save(update_fields=["precio_actual", "precio_final"])
    else:
        salida.precio_actual = 0
        salida.precio_final = None
        salida.save(update_fields=["precio_actual", "precio_final"])

    return salida