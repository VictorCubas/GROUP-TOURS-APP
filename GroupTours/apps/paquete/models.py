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
# TIPO DE COSTO DE SALIDA (catálogo)
# ---------------------------------------------------------------------
class TipoCostoSalida(models.Model):
    """
    Catálogo reutilizable de tipos de costo operativo para paquetes terrestres propios.
    Ejemplos: Bus, Coordinador, IVA, Tasa municipal.

    dividir_por_pasajeros=True  → el monto ingresado es el costo total del contrato
                                   (ej: bus). El sistema lo divide por el cupo al calcular.
    dividir_por_pasajeros=False → el monto ingresado es el costo directo por pasajero.
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código estable para identificar el tipo (ej: BUS, COORDINADOR). No debe cambiarse una vez creado."
    )
    nombre = models.CharField(max_length=100, unique=True)
    dividir_por_pasajeros = models.BooleanField(
        default=False,
        help_text="Si es True, el monto se divide por el cupo de la salida al calcular el costo por pasajero."
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de Costo de Salida"
        verbose_name_plural = "Tipos de Costo de Salida"
        db_table = "TipoCostoSalida"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------
# ITEM DE COSTO POR PAQUETE (plantilla / default)
# ---------------------------------------------------------------------
class ItemCostoPaquete(models.Model):
    """
    Monto por defecto de un tipo de costo para todas las salidas de un paquete.
    Solo aplica a paquetes terrestres propios.
    Si una salida necesita un monto diferente, se crea un ItemCostoSalida (override).
    """
    paquete = models.ForeignKey(
        Paquete,
        on_delete=models.CASCADE,
        related_name="items_costo_default"
    )
    tipo_costo = models.ForeignKey(
        TipoCostoSalida,
        on_delete=models.PROTECT,
        related_name="items_paquete"
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("paquete", "tipo_costo")
        verbose_name = "Ítem de Costo por Paquete"
        verbose_name_plural = "Ítems de Costo por Paquete"
        db_table = "ItemCostoPaquete"

    def __str__(self):
        return f"{self.paquete.nombre} - {self.tipo_costo.nombre}: {self.monto}"


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
    codigo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        blank=True,
        help_text="Código único de la salida (ej: SAL-2026-0001)"
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

    costo_base_desde = models.DecimalField(max_digits=12, decimal_places=2)
    costo_base_hasta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

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

    def save(self, *args, **kwargs):
        if not self.codigo:
            from django.utils.timezone import now as tz_now
            year = tz_now().year
            last_num = SalidaPaquete.objects.filter(
                fecha_creacion__year=year
            ).count() + 1
            self.codigo = f"SAL-{year}-{last_num:04d}"
        super().save(*args, **kwargs)

    # -----------------------------
    # ÍTEMS DE COSTO OPERATIVO
    # -----------------------------
    def _calcular_costo_items(self):
        """
        Suma todos los ítems de costo activos del paquete, aplicando overrides por salida.
        Lógica template+override:
          - Si existe ItemCostoSalida para el tipo → usa ese monto (override).
          - Si no existe → usa ItemCostoPaquete (default del paquete).
        Si dividir_por_pasajeros=True, divide el monto por el cupo de la salida.
        """
        cupo = self.cupo or 1
        total = Decimal("0")

        for item_default in self.paquete.items_costo_default.filter(activo=True).select_related("tipo_costo"):
            tipo_costo = item_default.tipo_costo
            if not tipo_costo.activo:
                continue

            override = self.items_costo.filter(tipo_costo=tipo_costo, activo=True).first()
            monto = _to_decimal(override.monto if override else item_default.monto)

            if tipo_costo.dividir_por_pasajeros:
                monto = monto / Decimal(str(cupo))

            total += monto

        return total

    # -----------------------------
    # CÁLCULO DE PRECIO DE VENTA
    # -----------------------------
    def calcular_precio_venta(self):
        """
        Calcula los precios de venta mínimo y máximo desde los precios de catálogo.

        Tanto propios como distribuidoras usan PrecioCatalogoHabitacion como fuente de precio.
        La diferencia es que distribuidoras aplican comision% y propios no aplican ningún factor.

        Prioridad:
        1. PrecioCatalogoHabitacion → precios específicos por habitación
        2. PrecioCatalogoHotel      → precio genérico del hotel para todas sus habitaciones
        3. Fallback a costo_base_desde/hasta si no hay catálogo definido

        ── LÓGICA ANTERIOR (cálculo automático para propios) ──────────────────────────
        Si en el futuro se quiere volver al cálculo automático para paquetes propios,
        el rango min/max se calculaba así (antes de que el precio entrara por catálogo):

        if self.paquete.propio:
            noches = (self.fecha_regreso - self.fecha_salida).days \
                     if self.fecha_regreso and self.fecha_salida else 1
            precios_habitaciones = []
            for cupo_hab in self.cupos_habitacion.filter(activo=True):
                precio_noche = _to_decimal(cupo_hab.habitacion.precio_noche)
                precios_habitaciones.append(precio_noche * noches)
            total_servicios = sum(
                _to_decimal(ps.precio or ps.servicio.precio)
                for ps in self.paquete.paquete_servicios.all()
            )
            total_items_costo = sum(
                item.monto / _to_decimal(self.cupo) if item.tipo_costo.dividir_por_pasajeros and self.cupo
                else item.monto
                for item in self.items_costo.filter(activo=True)
            )
            ganancia = _to_decimal(self.ganancia)
            factor = Decimal("1") + (ganancia / Decimal("100")) if ganancia > 0 else Decimal("1")
            min_base = (min(precios_habitaciones) + total_servicios + total_items_costo) * factor
            max_base = (max(precios_habitaciones) + total_servicios + total_items_costo) * factor
        ────────────────────────────────────────────────────────────────────────────────
        """
        precios_list = []

        precios_habitacion = self.precios_catalogo_habitaciones.all()
        if precios_habitacion.exists():
            precios_list = [_to_decimal(pc.precio_catalogo) for pc in precios_habitacion]
        else:
            precios_hotel = self.precios_catalogo_hoteles.all()
            if precios_hotel.exists():
                precios_list = [_to_decimal(ph.precio_catalogo) for ph in precios_hotel]

        if not precios_list:
            min_base = _to_decimal(self.costo_base_desde)
            max_base = _to_decimal(self.costo_base_hasta) or min_base
        else:
            min_base = min(precios_list)
            max_base = max(precios_list)

        self.precio_venta_sugerido_min = min_base
        self.precio_venta_sugerido_max = max_base

        self.save(update_fields=["precio_venta_sugerido_min", "precio_venta_sugerido_max"])

    # -----------------------------
    # CONVERSIÓN DE MONEDA
    # -----------------------------
    def obtener_precio_en_guaranies(self):
        """
        Retorna el precio de la salida convertido a guaraníes.
        Si ya está en guaraníes, retorna el precio original.

        Returns:
            dict: {
                'precio_min': Decimal,
                'precio_max': Decimal,
                'moneda_original': str (código),
                'cotizacion_aplicada': Decimal o None,
                'fecha_cotizacion': date o None
            }
        """
        from apps.moneda.models import CotizacionMoneda
        from django.core.exceptions import ValidationError

        # Si la moneda es guaraníes, retornar directamente
        if self.moneda.codigo == 'PYG':
            return {
                'precio_min': self.costo_base_desde,
                'precio_max': self.costo_base_hasta or self.costo_base_desde,
                'moneda_original': self.moneda.codigo,
                'cotizacion_aplicada': None,
                'fecha_cotizacion': None
            }

        # Obtener cotización vigente
        cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(self.moneda)

        if not cotizacion:
            raise ValidationError(
                f"No se puede calcular precio en guaraníes. "
                f"No existe cotización vigente para {self.moneda.nombre}"
            )

        valor_cotizacion = _to_decimal(cotizacion.valor_en_guaranies)

        return {
            'precio_min': self.costo_base_desde * valor_cotizacion,
            'precio_max': (self.costo_base_hasta or self.costo_base_desde) * valor_cotizacion,
            'moneda_original': self.moneda.codigo,
            'cotizacion_aplicada': cotizacion.valor_en_guaranies,
            'fecha_cotizacion': cotizacion.fecha_vigencia
        }

    @property
    def precio_en_guaranies(self):
        """Property para acceso rápido al precio convertido"""
        try:
            return self.obtener_precio_en_guaranies()
        except ValidationError:
            return None

    # -----------------------------
    # CONVERSIÓN A MONEDA ALTERNATIVA (USD/PYG)
    # -----------------------------
    def obtener_precio_en_moneda_alternativa(self, fecha=None):
        """
        Retorna el precio de la salida en la moneda alternativa.
        - Si la salida es en PYG, convierte a USD
        - Si la salida es en USD, convierte a PYG

        Args:
            fecha: date (opcional) - Fecha para obtener cotización. Default: fecha_salida

        Returns:
            dict: {
                'moneda_alternativa': str (código),
                'precio_min': Decimal,
                'precio_max': Decimal,
                'precio_venta_min': Decimal o None,
                'precio_venta_max': Decimal o None,
                'senia': Decimal o None,
                'cotizacion_aplicada': Decimal,
                'fecha_cotizacion': date
            }

        Raises:
            ValidationError: Si no existe cotización vigente
        """
        from apps.moneda.models import Moneda, CotizacionMoneda
        from .utils import convertir_entre_monedas

        fecha_referencia = fecha or self.fecha_salida

        # Determinar moneda alternativa
        if self.moneda.codigo == 'PYG':
            # Salida en PYG, mostrar en USD
            moneda_alternativa = Moneda.objects.get(codigo='USD')
        elif self.moneda.codigo == 'USD':
            # Salida en USD, mostrar en PYG
            moneda_alternativa = Moneda.objects.get(codigo='PYG')
        else:
            raise ValidationError(f"Moneda no soportada: {self.moneda.codigo}")

        # Obtener cotización
        if self.moneda.codigo == 'USD' or moneda_alternativa.codigo == 'USD':
            moneda_usd = Moneda.objects.get(codigo='USD')
            cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd, fecha_referencia)

            if not cotizacion:
                raise ValidationError(
                    f"No existe cotización de USD vigente para {fecha_referencia.strftime('%d/%m/%Y')}"
                )
        else:
            cotizacion = None

        # Convertir precios
        precio_min = convertir_entre_monedas(
            self.costo_base_desde,
            self.moneda,
            moneda_alternativa,
            fecha_referencia
        )

        precio_max = convertir_entre_monedas(
            self.costo_base_hasta or self.costo_base_desde,
            self.moneda,
            moneda_alternativa,
            fecha_referencia
        ) if self.costo_base_hasta else precio_min

        precio_venta_min = convertir_entre_monedas(
            self.precio_venta_sugerido_min,
            self.moneda,
            moneda_alternativa,
            fecha_referencia
        ) if self.precio_venta_sugerido_min else None

        precio_venta_max = convertir_entre_monedas(
            self.precio_venta_sugerido_max,
            self.moneda,
            moneda_alternativa,
            fecha_referencia
        ) if self.precio_venta_sugerido_max else None

        senia_convertida = convertir_entre_monedas(
            self.senia,
            self.moneda,
            moneda_alternativa,
            fecha_referencia
        ) if self.senia else None

        return {
            'moneda_alternativa': moneda_alternativa.codigo,
            'precio_min': precio_min,
            'precio_max': precio_max,
            'precio_venta_min': precio_venta_min,
            'precio_venta_max': precio_venta_max,
            'senia': senia_convertida,
            'cotizacion_aplicada': cotizacion.valor_en_guaranies if cotizacion else None,
            'fecha_cotizacion': cotizacion.fecha_vigencia if cotizacion else None
        }

    @property
    def precio_en_moneda_alternativa(self):
        """Property para acceso rápido al precio en moneda alternativa"""
        try:
            return self.obtener_precio_en_moneda_alternativa()
        except (ValidationError, Exception):
            return None

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

        self.costo_base_desde = nuevo_precio
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
# ITEM DE COSTO POR SALIDA (override)
# ---------------------------------------------------------------------
class ItemCostoSalida(models.Model):
    """
    Override de monto de un tipo de costo para una salida específica.
    Solo existe cuando el monto de la salida difiere del default del paquete (ItemCostoPaquete).
    Si no existe ItemCostoSalida para un tipo, se usa el ItemCostoPaquete correspondiente.
    """
    salida = models.ForeignKey(
        SalidaPaquete,
        on_delete=models.CASCADE,
        related_name="items_costo"
    )
    tipo_costo = models.ForeignKey(
        TipoCostoSalida,
        on_delete=models.PROTECT,
        related_name="items_salida"
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("salida", "tipo_costo")
        verbose_name = "Ítem de Costo por Salida"
        verbose_name_plural = "Ítems de Costo por Salida"
        db_table = "ItemCostoSalida"

    def __str__(self):
        return f"{self.salida} - {self.tipo_costo.nombre}: {self.monto} (override)"


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
        related_name="precios_catalogo_habitaciones"
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
        return f"{self.habitacion.hotel.nombre} - {self.habitacion.tipo_habitacion.nombre} - {self.precio}"


# ---------------------------------------------------------------------
# FUNCIÓN DE CREACIÓN DE SALIDA CON CÁLCULO DE RANGO
# ---------------------------------------------------------------------
@transaction.atomic
def create_salida_paquete(data):
    """
    Crea una SalidaPaquete con precio base en 0.
    Los precios reales (costo_base_desde/hasta y precio_venta_sugerido) se calculan
    después de que el serializer asigne los PrecioCatalogoHabitacion correspondientes.

    ── LÓGICA ANTERIOR (cálculo automático desde habitaciones para propios) ──────────
    Si en el futuro se quiere restaurar el cálculo automático al crear la salida,
    se calculaba el rango desde las habitaciones asociadas al paquete:

    if paquete.propio and paquete.modalidad == 'fijo' and paquete.habitacion_fija:
        hab = paquete.habitacion_fija
        noches = (fecha_regreso - fecha_salida).days if fecha_regreso else 1
        precio_noche = hab.precio_noche or Decimal("0")
        # Convertir moneda si difieren:
        # if hab.moneda != moneda: precio_noche = convertir_entre_monedas(...)
        total_servicios = sum(
            ps.precio or ps.servicio.precio or 0
            for ps in paquete.paquete_servicios.all()
        )
        costo_base = precio_noche * noches + total_servicios
        ganancia = data.get("ganancia") or Decimal("0")
        factor = Decimal("1") + (ganancia / Decimal("100")) if ganancia > 0 else Decimal("1")
        costo_base_desde = costo_base * factor
        costo_base_hasta = costo_base_desde
    elif paquete.propio and paquete.modalidad == 'flexible':
        # Iterar sobre todas las habitaciones del hotel para obtener rango min/max
        # costo_base_desde = precio de la habitación más barata × noches * factor
        # costo_base_hasta  = precio de la habitación más cara  × noches * factor
        pass
    ────────────────────────────────────────────────────────────────────────────────
    """
    salida = SalidaPaquete.objects.create(
        paquete_id=data["paquete_id"],
        fecha_salida=data["fecha_salida"],
        fecha_regreso=data.get("fecha_regreso"),
        moneda_id=data["moneda_id"],
        cupo=data.get("cupo", 0),
        senia=data.get("senia"),
        costo_base_desde=0,
        costo_base_hasta=None,
        ganancia=data.get("ganancia"),
        comision=data.get("comision")
    )

    salida.hoteles.set(data["hoteles_ids"])

    return salida
