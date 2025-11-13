# apps/arqueo_caja/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from decimal import Decimal, InvalidOperation


def _to_decimal(value):
    """Helper para convertir valores a Decimal de forma segura"""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


class Caja(models.Model):
    """
    Representa un punto de venta físico donde se manejan transacciones.
    Puede estar asociada a un PuntoExpedicion para emisión de facturas.
    """

    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo (ej: Caja Principal, Caja 1)"
    )

    numero_caja = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        help_text="Número único de la caja con formato 001, 002, 003..."
    )

    # Relación opcional con punto de expedición para facturación
    punto_expedicion = models.ForeignKey(
        'facturacion.PuntoExpedicion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cajas',
        help_text="Punto de expedición asociado (si emite facturas desde esta caja)"
    )

    # Indicador de si emite facturas
    emite_facturas = models.BooleanField(
        default=True,
        help_text="Indica si esta caja puede emitir facturas electrónicas"
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción adicional"
    )

    ubicacion = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Ubicación física de la caja"
    )

    # Estado actual
    estado_actual = models.CharField(
        max_length=20,
        choices=[
            ('abierta', 'Abierta'),
            ('cerrada', 'Cerrada'),
        ],
        default='cerrada'
    )

    saldo_actual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Saldo actual en la caja"
    )

    # Auditoría
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Caja"
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ['numero_caja']

    def __str__(self):
        if self.punto_expedicion:
            return f"{self.nombre} (#{self.numero_caja}) - PE: {self.punto_expedicion}"
        return f"{self.nombre} (#{self.numero_caja})"

    def save(self, *args, **kwargs):
        # Auto-generar número de caja
        if not self.numero_caja:
            # Obtener el último número de caja
            ultima_caja = Caja.objects.all().order_by('-id').first()
            if ultima_caja and ultima_caja.numero_caja:
                try:
                    ultimo_numero = int(ultima_caja.numero_caja)
                    nuevo_numero = ultimo_numero + 1
                except (ValueError, TypeError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1

            # Formatear con ceros a la izquierda (001, 002, 003...)
            self.numero_caja = f"{nuevo_numero:03d}"

        super().save(*args, **kwargs)

    def clean(self):
        """Validaciones de negocio"""
        # Validar que si emite facturas, tenga punto de expedición
        if self.emite_facturas and not self.punto_expedicion:
            raise ValidationError(
                "Una caja que emite facturas debe tener un punto de expedición asociado"
            )

    def puede_abrir(self):
        """Verifica si la caja puede ser abierta"""
        return self.estado_actual == 'cerrada' and self.activo

    def puede_cerrar(self):
        """Verifica si la caja puede ser cerrada"""
        return self.estado_actual == 'abierta'


class AperturaCaja(models.Model):
    """
    Registro de apertura de caja (inicio de turno).
    Cada apertura representa un turno de trabajo de un empleado en una caja específica.
    """

    # Identificación
    codigo_apertura = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Código único: APR-2025-0001"
    )

    # Relaciones
    caja = models.ForeignKey(
        Caja,
        on_delete=models.PROTECT,
        related_name='aperturas',
        help_text="Caja que se está abriendo"
    )

    responsable = models.ForeignKey(
        'empleado.Empleado',
        on_delete=models.PROTECT,
        related_name='aperturas_caja',
        help_text="Empleado responsable del turno"
    )

    # Datos de apertura
    fecha_hora_apertura = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de apertura"
    )

    monto_inicial = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Monto inicial con el que se abre (fondo de cambio)"
    )

    observaciones_apertura = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones al momento de abrir"
    )

    # Estado
    esta_abierta = models.BooleanField(
        default=True,
        help_text="True si la caja sigue abierta, False si ya fue cerrada"
    )

    # Auditoría
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "AperturaCaja"
        verbose_name = "Apertura de Caja"
        verbose_name_plural = "Aperturas de Caja"
        ordering = ['-fecha_hora_apertura']
        indexes = [
            models.Index(fields=['caja', 'esta_abierta']),
            models.Index(fields=['responsable', 'fecha_hora_apertura']),
        ]

    def __str__(self):
        return f"{self.codigo_apertura} - {self.caja.nombre}"

    def save(self, *args, **kwargs):
        # Auto-generar código de apertura
        if not self.codigo_apertura:
            year = now().year
            last_id = AperturaCaja.objects.filter(
                fecha_hora_apertura__year=year
            ).count() + 1
            self.codigo_apertura = f"APR-{year}-{last_id:04d}"

        super().save(*args, **kwargs)

        # Actualizar estado de la caja
        if self.esta_abierta:
            self.caja.estado_actual = 'abierta'
            self.caja.saldo_actual = self.monto_inicial
            self.caja.save(update_fields=['estado_actual', 'saldo_actual'])

    def clean(self):
        """Validaciones de negocio"""
        # No puede haber más de una apertura activa por caja
        if self.esta_abierta:
            aperturas_activas = AperturaCaja.objects.filter(
                caja=self.caja,
                esta_abierta=True,
                activo=True
            ).exclude(pk=self.pk)

            if aperturas_activas.exists():
                raise ValidationError(
                    f"Ya existe una apertura activa para la caja {self.caja.nombre}"
                )

        # El monto inicial debe ser positivo o cero
        if self.monto_inicial < 0:
            raise ValidationError("El monto inicial no puede ser negativo")


class MovimientoCaja(models.Model):
    """
    Registra todos los movimientos (ingresos/egresos) de una caja abierta.
    Cada movimiento afecta el saldo de la caja.
    """

    TIPOS_MOVIMIENTO = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]

    CONCEPTOS_INGRESO = [
        ('venta_efectivo', 'Venta en Efectivo'),
        ('venta_tarjeta', 'Venta con Tarjeta'),
        ('cobro_cuenta', 'Cobro de Cuenta por Cobrar'),
        ('deposito', 'Depósito'),
        ('transferencia_recibida', 'Transferencia Recibida'),
        ('ajuste_positivo', 'Ajuste Positivo'),
        ('otro_ingreso', 'Otro Ingreso'),
    ]

    CONCEPTOS_EGRESO = [
        ('pago_proveedor', 'Pago a Proveedor'),
        ('pago_servicio', 'Pago de Servicio'),
        ('gasto_operativo', 'Gasto Operativo'),
        ('retiro_efectivo', 'Retiro de Efectivo'),
        ('devolucion', 'Devolución a Cliente'),
        ('ajuste_negativo', 'Ajuste Negativo'),
        ('otro_egreso', 'Otro Egreso'),
    ]

    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('transferencia', 'Transferencia Bancaria'),
        ('cheque', 'Cheque'),
        ('qr', 'Pago QR'),
        ('otro', 'Otro'),
    ]

    # Identificación
    numero_movimiento = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Código único: MOV-2025-0001"
    )

    # Relaciones
    apertura_caja = models.ForeignKey(
        AperturaCaja,
        on_delete=models.PROTECT,
        related_name='movimientos',
        help_text="Apertura de caja a la que pertenece este movimiento"
    )

    comprobante = models.ForeignKey(
        'comprobante.ComprobantePago',
        on_delete=models.PROTECT,
        related_name='movimientos_caja',
        null=True,
        blank=True,
        help_text="Comprobante asociado (si aplica)"
    )

    # Tipo de movimiento
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPOS_MOVIMIENTO,
        help_text="Ingreso o Egreso"
    )

    concepto = models.CharField(
        max_length=50,
        help_text="Concepto del movimiento"
    )

    # Montos
    monto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Monto del movimiento"
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO,
        help_text="Método de pago utilizado"
    )

    # Información adicional
    referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Referencia del movimiento (número de factura, recibo, etc.)"
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción detallada del movimiento"
    )

    # Fechas
    fecha_hora_movimiento = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora del movimiento"
    )

    # Auditoría
    usuario_registro = models.ForeignKey(
        'empleado.Empleado',
        on_delete=models.PROTECT,
        related_name='movimientos_registrados',
        help_text="Usuario que registró el movimiento"
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "MovimientoCaja"
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ['-fecha_hora_movimiento']
        indexes = [
            models.Index(fields=['apertura_caja', 'tipo_movimiento']),
            models.Index(fields=['fecha_hora_movimiento']),
            models.Index(fields=['comprobante']),
        ]

    def __str__(self):
        return f"{self.numero_movimiento} - {self.get_tipo_movimiento_display()}: ${self.monto}"

    def save(self, *args, **kwargs):
        # Auto-generar número de movimiento
        if not self.numero_movimiento:
            year = now().year
            last_id = MovimientoCaja.objects.filter(
                fecha_hora_movimiento__year=year
            ).count() + 1
            self.numero_movimiento = f"MOV-{year}-{last_id:04d}"

        super().save(*args, **kwargs)

        # Actualizar saldo de la caja
        self.actualizar_saldo_caja()

    def clean(self):
        """Validaciones de negocio"""
        # Validar que la apertura esté abierta
        if not self.apertura_caja.esta_abierta:
            raise ValidationError("No se pueden registrar movimientos en una caja cerrada")

        # Validar monto positivo
        if self.monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero")

        # Validar concepto según tipo
        if self.tipo_movimiento == 'ingreso':
            conceptos_validos = [c[0] for c in self.CONCEPTOS_INGRESO]
            if self.concepto not in conceptos_validos:
                raise ValidationError(f"Concepto '{self.concepto}' no válido para ingreso")

        elif self.tipo_movimiento == 'egreso':
            conceptos_validos = [c[0] for c in self.CONCEPTOS_EGRESO]
            if self.concepto not in conceptos_validos:
                raise ValidationError(f"Concepto '{self.concepto}' no válido para egreso")

    def actualizar_saldo_caja(self):
        """Actualiza el saldo de la caja según el tipo de movimiento"""
        caja = self.apertura_caja.caja
        monto_decimal = _to_decimal(self.monto)

        if self.tipo_movimiento == 'ingreso':
            caja.saldo_actual = _to_decimal(caja.saldo_actual) + monto_decimal
        elif self.tipo_movimiento == 'egreso':
            caja.saldo_actual = _to_decimal(caja.saldo_actual) - monto_decimal

        caja.save(update_fields=['saldo_actual'])


class CierreCaja(models.Model):
    """
    Registro de cierre de caja (fin de turno con arqueo).
    Incluye comparación entre saldo teórico y saldo real contado.
    """

    # Identificación
    codigo_cierre = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Código único: CIE-2025-0001"
    )

    # Relación con apertura
    apertura_caja = models.OneToOneField(
        AperturaCaja,
        on_delete=models.PROTECT,
        related_name='cierre',
        help_text="Apertura de caja que se está cerrando"
    )

    # Fechas
    fecha_hora_cierre = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de cierre"
    )

    # === CÁLCULOS AUTOMÁTICOS (desde movimientos) ===

    # Ingresos por método de pago
    total_efectivo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total ingresado en efectivo"
    )

    total_tarjetas = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total de tarjetas (débito + crédito)"
    )

    total_transferencias = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total de transferencias"
    )

    total_cheques = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total de cheques"
    )

    total_otros_ingresos = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Otros métodos de pago"
    )

    # Egresos
    total_egresos = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total de egresos del turno"
    )

    # === SALDOS TEÓRICOS ===

    saldo_teorico_efectivo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Saldo esperado en efectivo = monto_inicial + efectivo - egresos"
    )

    saldo_teorico_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Saldo total esperado (todos los métodos)"
    )

    # === ARQUEO (CONTEO FÍSICO) ===

    saldo_real_efectivo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Efectivo físicamente contado"
    )

    # Detalle del conteo físico
    detalle_billetes = models.JSONField(
        null=True,
        blank=True,
        help_text="Detalle del conteo de billetes por denominación"
    )
    # Ejemplo: {"100000": 10, "50000": 5, "20000": 15}

    # === DIFERENCIAS ===

    diferencia_efectivo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Diferencia = saldo_real - saldo_teorico"
    )

    diferencia_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Porcentaje de diferencia respecto al teórico"
    )

    # === OBSERVACIONES ===

    observaciones_cierre = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones generales del cierre"
    )

    justificacion_diferencia = models.TextField(
        blank=True,
        null=True,
        help_text="Justificación de la diferencia (si la hay)"
    )

    # === AUTORIZACIÓN (si hay diferencia significativa) ===

    requiere_autorizacion = models.BooleanField(
        default=False,
        help_text="True si la diferencia supera el umbral permitido"
    )

    autorizado_por = models.ForeignKey(
        'empleado.Empleado',
        on_delete=models.PROTECT,
        related_name='cierres_autorizados',
        null=True,
        blank=True,
        help_text="Supervisor que autorizó el cierre con diferencia"
    )

    fecha_autorizacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de autorización"
    )

    # Auditoría
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "CierreCaja"
        verbose_name = "Cierre de Caja"
        verbose_name_plural = "Cierres de Caja"
        ordering = ['-fecha_hora_cierre']
        indexes = [
            models.Index(fields=['apertura_caja']),
            models.Index(fields=['fecha_hora_cierre']),
        ]

    def __str__(self):
        return f"{self.codigo_cierre} - {self.apertura_caja.caja.nombre}"

    def save(self, *args, **kwargs):
        # Auto-generar código de cierre
        if not self.codigo_cierre:
            year = now().year
            last_id = CierreCaja.objects.filter(
                fecha_hora_cierre__year=year
            ).count() + 1
            self.codigo_cierre = f"CIE-{year}-{last_id:04d}"

        # Calcular diferencia si se tiene saldo real
        if self.saldo_real_efectivo is not None and self.saldo_teorico_efectivo is not None:
            saldo_real = _to_decimal(self.saldo_real_efectivo)
            saldo_teorico = _to_decimal(self.saldo_teorico_efectivo)
            self.diferencia_efectivo = saldo_real - saldo_teorico

            # Calcular porcentaje
            if saldo_teorico != 0:
                self.diferencia_porcentaje = (
                    (self.diferencia_efectivo / saldo_teorico) * 100
                )

            # Determinar si requiere autorización (umbral: ±2%)
            if abs(_to_decimal(self.diferencia_porcentaje or 0)) > 2:
                self.requiere_autorizacion = True

        super().save(*args, **kwargs)

        # Marcar la apertura como cerrada
        self.apertura_caja.esta_abierta = False
        self.apertura_caja.save(update_fields=['esta_abierta'])

        # Actualizar estado de la caja
        self.apertura_caja.caja.estado_actual = 'cerrada'
        self.apertura_caja.caja.save(update_fields=['estado_actual'])

    def calcular_totales_desde_movimientos(self):
        """
        Calcula los totales de ingresos/egresos basado en los movimientos registrados.
        """
        from django.db.models import Sum

        movimientos = self.apertura_caja.movimientos.filter(activo=True)

        # Ingresos por método de pago
        ingresos = movimientos.filter(tipo_movimiento='ingreso')

        self.total_efectivo = _to_decimal(
            ingresos.filter(metodo_pago='efectivo')
            .aggregate(total=Sum('monto'))['total']
        )

        self.total_tarjetas = _to_decimal(
            ingresos.filter(metodo_pago__in=['tarjeta_debito', 'tarjeta_credito'])
            .aggregate(total=Sum('monto'))['total']
        )

        self.total_transferencias = _to_decimal(
            ingresos.filter(metodo_pago='transferencia')
            .aggregate(total=Sum('monto'))['total']
        )

        self.total_cheques = _to_decimal(
            ingresos.filter(metodo_pago='cheque')
            .aggregate(total=Sum('monto'))['total']
        )

        self.total_otros_ingresos = _to_decimal(
            ingresos.filter(metodo_pago__in=['qr', 'otro'])
            .aggregate(total=Sum('monto'))['total']
        )

        # Egresos
        self.total_egresos = _to_decimal(
            movimientos.filter(tipo_movimiento='egreso')
            .aggregate(total=Sum('monto'))['total']
        )

        # Calcular saldos teóricos
        monto_inicial = _to_decimal(self.apertura_caja.monto_inicial)

        self.saldo_teorico_efectivo = (
            monto_inicial +
            self.total_efectivo -
            self.total_egresos
        )

        self.saldo_teorico_total = (
            monto_inicial +
            self.total_efectivo +
            self.total_tarjetas +
            self.total_transferencias +
            self.total_cheques +
            self.total_otros_ingresos -
            self.total_egresos
        )

        self.save()

    def generar_resumen(self):
        """Genera un resumen del cierre en formato dict"""
        duracion = self.fecha_hora_cierre - self.apertura_caja.fecha_hora_apertura

        return {
            'codigo_cierre': self.codigo_cierre,
            'caja': self.apertura_caja.caja.nombre,
            'responsable': str(self.apertura_caja.responsable),
            'fecha_apertura': self.apertura_caja.fecha_hora_apertura.strftime('%d/%m/%Y %H:%M'),
            'fecha_cierre': self.fecha_hora_cierre.strftime('%d/%m/%Y %H:%M'),
            'duracion_turno': str(duracion),

            'monto_inicial': str(self.apertura_caja.monto_inicial),

            'ingresos': {
                'efectivo': str(self.total_efectivo),
                'tarjetas': str(self.total_tarjetas),
                'transferencias': str(self.total_transferencias),
                'cheques': str(self.total_cheques),
                'otros': str(self.total_otros_ingresos),
                'total': str(
                    self.total_efectivo + self.total_tarjetas +
                    self.total_transferencias + self.total_cheques +
                    self.total_otros_ingresos
                ),
            },

            'egresos': {
                'total': str(self.total_egresos),
            },

            'arqueo': {
                'saldo_teorico': str(self.saldo_teorico_efectivo) if self.saldo_teorico_efectivo else None,
                'saldo_real': str(self.saldo_real_efectivo) if self.saldo_real_efectivo else None,
                'diferencia': str(self.diferencia_efectivo) if self.diferencia_efectivo else None,
                'diferencia_porcentaje': str(self.diferencia_porcentaje) if self.diferencia_porcentaje else None,
            },

            'requiere_autorizacion': self.requiere_autorizacion,
            'observaciones': self.observaciones_cierre,
        }
