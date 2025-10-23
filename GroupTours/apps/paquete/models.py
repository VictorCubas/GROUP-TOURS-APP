from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation

# === Importaciones de tus apps existentes ===
from apps.tipo_paquete.models import TipoPaquete
from apps.distribuidora.models import Distribuidora
from apps.destino.models import Destino
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio
from apps.hotel.models import Hotel, Habitacion


# ---------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------
def _to_decimal(value):
    """Convierte strings/números a Decimal de forma segura"""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


# ---------------------------------------------------------------------
# PAQUETE
# ---------------------------------------------------------------------
class Paquete(models.Model):
    """
    Paquete turístico genérico:
    contiene información base (destino, moneda, servicios incluidos).
    Las salidas concretas con fechas/precios se manejan en SalidaPaquete.
    """
    nombre = models.CharField(max_length=150)

    tipo_paquete = models.ForeignKey(
        TipoPaquete,
        on_delete=models.PROTECT,
        related_name="paquetes"
    )

    FLEXIBLE = "flexible"
    FIJO = "fijo"
    TIPO_SELECCION = [
        (FLEXIBLE, "Flexible"),
        (FIJO, "Fijo"),
    ]
    modalidad = models.CharField(
        max_length=10,
        choices=TIPO_SELECCION,
        default=FLEXIBLE,
        help_text="Define si el paquete es flexible o fijo."
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
        null=True,
        blank=True,
        related_name="paquetes"
    )

    propio = models.BooleanField(default=True)
    personalizado = models.BooleanField(default=False)
    cantidad_pasajeros = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad total de pasajeros (solo terrestre propio)"
    )
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    imagen = models.ImageField(upload_to="paquetes/", blank=True, null=True)

    class Meta:
        verbose_name = "Paquete"
        verbose_name_plural = "Paquetes"
        db_table = "Paquete"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
    
    
    @property
    def zona_geografica(self):
        """
        Devuelve la zona geográfica asociada al país del destino del paquete.
        Retorna None si no hay zona asociada.
        """
        try:
            return self.destino.zona_geografica
        except AttributeError:
            return None
        

    def clean(self):
        if (
            self.tipo_paquete
            and self.tipo_paquete.nombre.lower() == "terrestre"
            and self.propio
            and not self.cantidad_pasajeros
        ):
            raise ValidationError(
                "La cantidad de pasajeros es requerida para paquetes terrestres propios."
            )


# ---------------------------------------------------------------------
# PAQUETE SERVICIO
# ---------------------------------------------------------------------
class PaqueteServicio(models.Model):
    paquete = models.ForeignKey(
        Paquete,
        on_delete=models.CASCADE,
        related_name="paquete_servicios"
    )
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ("paquete", "servicio")
        verbose_name = "Paquete Servicio"
        verbose_name_plural = "Paquetes Servicios"

    def __str__(self):
        return f"{self.paquete.nombre} - {self.servicio.nombre} (${self.precio})"


# ---------------------------------------------------------------------
# TEMPORADA
# ---------------------------------------------------------------------
class Temporada(models.Model):
    nombre = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    paquetes = models.ManyToManyField(
        Paquete,
        related_name="temporadas",
        blank=True
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Temporada"
        verbose_name_plural = "Temporadas"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicio} → {self.fecha_fin})"


# ---------------------------------------------------------------------
# SALIDA DE PAQUETE
# ---------------------------------------------------------------------
class SalidaPaquete(models.Model):
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
        null=True,
        blank=True,
        related_name="salidas"
    )

    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name="salidas")
    hoteles = models.ManyToManyField(Hotel, related_name="salidas_paquete")

    habitacion_fija = models.ForeignKey(
        Habitacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="salidas_fijas"
    )

    precio_actual = models.DecimalField(max_digits=12, decimal_places=2)
    precio_final = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    ganancia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comision = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    precio_venta_sugerido_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    precio_venta_sugerido_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Cupo global (asientos en terrestre propio)
    cupo = models.PositiveIntegerField(
        default=0, null=True, blank=True,
        help_text="Cantidad de asientos disponibles (solo aplica para paquetes terrestres propios)."
    )

    senia = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salida de Paquete"
        verbose_name_plural = "Salidas de Paquete"
        ordering = ["fecha_salida"]

    def __str__(self):
        return f"{self.paquete.nombre} - {self.fecha_salida}"

    # -----------------------------
    # CÁLCULO DE PRECIO DE VENTA
    # -----------------------------
    def calcular_precio_venta(self):
        """
        Calcula los precios de venta mínimo y máximo considerando:
        - Para paquetes PROPIOS: precio_actual/precio_final + servicios + ganancia%
        - Para paquetes de DISTRIBUIDORA: precios de catálogo (hotel o habitación) + comisión%

        Prioridad de precios para distribuidoras:
        1. Si existe PrecioCatalogoHabitacion → usa esos
        2. Si existe PrecioCatalogoHotel → usa esos (aplica a todas las habitaciones del hotel)
        3. Si no existe ninguno → fallback a precio_actual/precio_final
        """
        ganancia = _to_decimal(self.ganancia)
        comision = _to_decimal(self.comision)

        # === CASO 1: Paquete de DISTRIBUIDORA ===
        if not self.paquete.propio:
            precios_list = []

            # Verificar si hay precios por habitación
            precios_habitacion = self.precios_catalogo.all()

            if precios_habitacion.exists():
                # CASO A: Usar precios específicos por habitación
                precios_list = [_to_decimal(pc.precio_catalogo) for pc in precios_habitacion]
            else:
                # CASO B: Verificar si hay precios por hotel
                precios_hotel = self.precios_catalogo_hoteles.all()

                if precios_hotel.exists():
                    # Usar precios por hotel (todas las habitaciones al mismo precio)
                    precios_list = [_to_decimal(ph.precio_catalogo) for ph in precios_hotel]
                else:
                    # CASO C: Fallback - usar precio_actual/precio_final
                    precios_list = []

            # Si después de todo no hay precios, usar precio_actual/precio_final
            if not precios_list:
                min_base = _to_decimal(self.precio_actual)
                max_base = _to_decimal(self.precio_final) or min_base
            else:
                min_base = min(precios_list)
                max_base = max(precios_list)

            # No se suman servicios para distribuidoras
            total_servicios = Decimal("0")

            # Aplicar comisión
            if comision > 0:
                factor = Decimal("1") + (comision / Decimal("100"))
            else:
                factor = Decimal("1")

            self.precio_venta_sugerido_min = min_base * factor
            self.precio_venta_sugerido_max = max_base * factor

        # === CASO 2: Paquete PROPIO ===
        else:
            min_base = _to_decimal(self.precio_actual)
            max_base = _to_decimal(self.precio_final) or min_base

            # Sumar servicios incluidos en el paquete
            total_servicios = Decimal("0")
            for ps in self.paquete.paquete_servicios.all():
                if ps.precio and ps.precio > 0:
                    total_servicios += _to_decimal(ps.precio)
                elif hasattr(ps.servicio, "precio") and ps.servicio.precio:
                    total_servicios += _to_decimal(ps.servicio.precio)

            # Costo total = habitación + servicios
            costo_total_min = min_base + total_servicios
            costo_total_max = max_base + total_servicios

            # Aplicar ganancia
            if ganancia > 0:
                factor = Decimal("1") + (ganancia / Decimal("100"))
            else:
                factor = Decimal("1")

            self.precio_venta_sugerido_min = costo_total_min * factor
            self.precio_venta_sugerido_max = costo_total_max * factor

        self.save(update_fields=["precio_venta_sugerido_min", "precio_venta_sugerido_max"])

    # -----------------------------
    # CAMBIO DE PRECIO CON HISTORIAL
    # -----------------------------
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
# CUPO DE HABITACIÓN POR SALIDA
# ---------------------------------------------------------------------
class CupoHabitacionSalida(models.Model):
    salida = models.ForeignKey(
        SalidaPaquete,
        on_delete=models.CASCADE,
        related_name="cupos_habitaciones"
    )
    habitacion = models.ForeignKey(
        Habitacion,
        on_delete=models.CASCADE,
        related_name="cupos_salidas"
    )
    cupo = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("salida", "habitacion")
        verbose_name = "Cupo de Habitación por Salida"
        verbose_name_plural = "Cupos de Habitaciones por Salida"

    def __str__(self):
        return f"{self.salida} - {self.habitacion} ({self.cupo} disponibles)"


# ---------------------------------------------------------------------
# PRECIO DE CATÁLOGO DE HOTEL (DISTRIBUIDORAS)
# ---------------------------------------------------------------------
class PrecioCatalogoHotel(models.Model):
    """
    Almacena precios de catálogo de distribuidora a nivel de HOTEL.
    Cuando se define un precio por hotel, se aplica a TODAS las habitaciones de ese hotel.
    Solo aplica para paquetes de distribuidora (propio=False).

    Este modelo permite simplificar la carga de precios cuando todas las habitaciones
    de un hotel tienen el mismo precio en el catálogo de la distribuidora.
    """
    salida = models.ForeignKey(
        SalidaPaquete,
        on_delete=models.CASCADE,
        related_name="precios_catalogo_hoteles"
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="precios_catalogo_distribuidora"
    )
    precio_catalogo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Precio base del catálogo de la distribuidora para TODAS las habitaciones de este hotel"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("salida", "hotel")
        verbose_name = "Precio de Catálogo de Hotel"
        verbose_name_plural = "Precios de Catálogo de Hoteles"

    def __str__(self):
        return f"{self.salida} - {self.hotel.nombre} - ${self.precio_catalogo}"


# ---------------------------------------------------------------------
# PRECIO DE CATÁLOGO DE HABITACIÓN (DISTRIBUIDORAS)
# ---------------------------------------------------------------------
class PrecioCatalogoHabitacion(models.Model):
    """
    Almacena los precios de catálogo de distribuidora por habitación y salida.
    Solo aplica para paquetes de distribuidora (propio=False).
    Estos precios representan el costo base del catálogo al cual se le aplicará la comisión.

    Cuando existen precios específicos por habitación, estos tienen prioridad sobre
    los precios por hotel (PrecioCatalogoHotel).
    """
    salida = models.ForeignKey(
        SalidaPaquete,
        on_delete=models.CASCADE,
        related_name="precios_catalogo"
    )
    habitacion = models.ForeignKey(
        Habitacion,
        on_delete=models.CASCADE,
        related_name="precios_catalogo_distribuidora"
    )
    precio_catalogo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Precio base del catálogo de la distribuidora para esta habitación"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("salida", "habitacion")
        verbose_name = "Precio de Catálogo de Habitación"
        verbose_name_plural = "Precios de Catálogo de Habitaciones"

    def __str__(self):
        return f"{self.salida} - {self.habitacion} - ${self.precio_catalogo}"


# ---------------------------------------------------------------------
# HISTORIAL DE PRECIO DE PAQUETE
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
# HISTORIAL DE PRECIO DE HABITACIÓN
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
# FUNCIÓN DE CREACIÓN DE SALIDA CON CÁLCULO DE RANGO
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

    # Asociar hoteles
    salida.hoteles.set(data["hoteles_ids"])

    # Calcular noches
    if salida.fecha_regreso:
        noches = (salida.fecha_regreso - salida.fecha_salida).days
    else:
        noches = 1

    # Calcular precios en base a habitaciones
    habitaciones = Habitacion.objects.filter(hotel__in=data["hoteles_ids"], activo=True)
    if habitaciones.exists():
        precios = [h.precio_noche * noches for h in habitaciones]
        salida.precio_actual = min(precios)
        salida.precio_final = max(precios) if precios else None
        salida.save(update_fields=["precio_actual", "precio_final"])
    else:
        salida.precio_actual = 0
        salida.precio_final = None
        salida.save(update_fields=["precio_actual", "precio_final"])

    # Calcular venta sugerida
    salida.calcular_precio_venta()

    return salida
