from django.db import models, transaction
from django.core.exceptions import ValidationError

# === Importaciones de tus apps existentes ===
from apps.tipo_paquete.models import TipoPaquete
from apps.distribuidora.models import Distribuidora
from apps.destino.models import Destino
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio
from apps.hotel.models import Hotel, Habitacion  # Importamos también Hotel
from decimal import Decimal, InvalidOperation

def _to_decimal(value):
    """Convierte strings/números a Decimal de forma segura"""
    if value is None:
        return Decimal("0")
    try:
        # soporta valores con coma decimal "12,5" o con punto "12.5"
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
    
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
    
    FLEXIBLE = 'flexible'
    FIJO = 'fijo'
    TIPO_SELECCION = [
        (FLEXIBLE, 'Flexible'),
        (FIJO, 'Fijo'),
    ]

    modalidad = models.CharField(
        max_length=10,
        choices=TIPO_SELECCION,
        default=FLEXIBLE,
        help_text=(
            "Define si el paquete es 'flexible' (varios hoteles/rooms a elegir) "
            "o 'fijo' (hotel y habitación predefinidos)."
        )
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
    Maneja precios base (precio_actual, precio_final) y los precios de
    venta sugeridos aplicando ganancia o comisión.
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

    hoteles = models.ManyToManyField(
        Hotel,
        related_name="salidas_paquete",
        help_text="Hoteles disponibles para esta salida del paquete"
    )
    
    habitacion_fija = models.ForeignKey(
        Habitacion,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="salidas_fijas",
        help_text="Sólo para paquetes fijos: la habitación concreta de esta salida."
    )

    # Precios base
    precio_actual = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Precio mínimo calculado (por persona, base sin comisión/ganancia)"
    )
    precio_final = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text="Precio máximo calculado (puede ser nulo)"
    )

    # Ajustes económicos
    ganancia = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Ganancia % aplicada si el paquete es propio"
    )
    comision = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Comisión % aplicada si el paquete es de distribuidora"
    )

    # Precios sugeridos
    precio_venta_sugerido_min = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Precio de venta sugerido mínimo"
    )
    precio_venta_sugerido_max = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Precio de venta sugerido máximo"
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

    def calcular_precio_venta(self):
        """
        Calcula y actualiza los precios de venta sugeridos según:
        - Si paquete.propio => aplica ganancia %
        - Si es distribuidora => aplica comisión %
        """
        # ✅ Aseguramos que todos los valores sean Decimals
        min_base = _to_decimal(self.precio_actual)
        max_base = _to_decimal(self.precio_final) or min_base

        ganancia = _to_decimal(self.ganancia)
        comision = _to_decimal(self.comision)

        # ✅ Determinamos factor según tipo de paquete
        if self.paquete.propio and ganancia > 0:
            factor = Decimal("1") + (ganancia / Decimal("100"))
        elif not self.paquete.propio and comision > 0:
            factor = Decimal("1") + (comision / Decimal("100"))
        else:
            factor = Decimal("1")

        # ✅ Calculamos y guardamos sugeridos
        self.precio_venta_sugerido_min = min_base * factor
        self.precio_venta_sugerido_max = max_base * factor

        self.save(update_fields=["precio_venta_sugerido_min", "precio_venta_sugerido_max"])

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
        precio_actual=0,
        precio_final=None,
        ganancia=data.get("ganancia"),
        comision=data.get("comision")
    )

    salida.hoteles.set(data["hoteles_ids"])

    # Calcular noches
    if salida.fecha_regreso:
        noches = (salida.fecha_regreso - salida.fecha_salida).days
    else:
        noches = 1

    habitaciones = Habitacion.objects.filter(
        hotel__in=data["hoteles_ids"], activo=True
    )

    if habitaciones.exists():
        precios = [h.precio_noche * noches for h in habitaciones]
        salida.precio_actual = min(precios)
        salida.precio_final = max(precios) if precios else None
        salida.save(update_fields=["precio_actual", "precio_final"])
    else:
        salida.precio_actual = 0
        salida.precio_final = None
        salida.save(update_fields=["precio_actual", "precio_final"])

    # Calcular el precio de venta sugerido
    salida.calcular_precio_venta()

    return salida
