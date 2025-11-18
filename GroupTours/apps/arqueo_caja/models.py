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
    Cada caja tiene asignado un PuntoExpedicion exclusivo (relación 1:1) para emisión de facturas.
    Todas las cajas emiten facturas electrónicas.
    """

    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo (ej: Caja Principal, Caja 1)"
    )

    numero_caja = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Número de la caja (formato: ESTABLECIMIENTO-PUNTO_EXPEDICION)"
    )

    # Relación 1:1 OBLIGATORIA con punto de expedición
    punto_expedicion = models.OneToOneField(
        'facturacion.PuntoExpedicion',
        on_delete=models.PROTECT,
        related_name='caja',
        help_text="Punto de expedición exclusivo de esta caja (relación 1:1)",
        error_messages={
            'unique': 'Ya existe una caja con este punto de expedición.'
        }
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción adicional"
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
        # Asignar número de caja con formato ESTABLECIMIENTO-PUNTO_EXPEDICION
        if self.punto_expedicion and not self.numero_caja:
            establecimiento_codigo = self.punto_expedicion.establecimiento.codigo
            pe_codigo = self.punto_expedicion.codigo
            self.numero_caja = f"{establecimiento_codigo}-{pe_codigo}"

        super().save(*args, **kwargs)

    def clean(self):
        """Validaciones de negocio"""
        # Validar que el punto de expedición sea obligatorio
        if not self.punto_expedicion:
            raise ValidationError(
                "Todas las cajas deben tener un punto de expedición asociado"
            )

        # Validar que el punto de expedición no esté usado por otra caja (1:1)
        # Django ya valida esto con OneToOneField, pero agregamos mensaje personalizado
        if self.punto_expedicion:
            caja_existente = Caja.objects.filter(
                punto_expedicion=self.punto_expedicion
            ).exclude(pk=self.pk).first()

            if caja_existente:
                raise ValidationError(
                    f"El punto de expedición {self.punto_expedicion} ya está asignado "
                    f"a la caja '{caja_existente.nombre}'"
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

    def generar_pdf(self):
        """
        Genera un PDF con los datos de la apertura de caja.
        Retorna un objeto BytesIO con el PDF generado.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        from io import BytesIO

        # Crear buffer para el PDF
        buffer = BytesIO()

        # Crear el canvas
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Fuentes
        title_font = "Helvetica-Bold"
        normal_font = "Helvetica"

        # Posición inicial
        y = height - 80

        # ENCABEZADO
        c.setFont(title_font, 20)
        c.drawString(50, y, "APERTURA DE CAJA")

        # Línea decorativa
        c.setStrokeColor(colors.HexColor("#2c3e50"))
        c.setLineWidth(2)
        c.line(50, y - 10, width - 50, y - 10)

        y -= 50

        # INFORMACIÓN DE LA APERTURA
        c.setFont(title_font, 12)
        c.drawString(50, y, f"Código: {self.codigo_apertura}")

        # Convertir a zona horaria local si está en UTC
        from django.utils import timezone
        fecha_local = timezone.localtime(self.fecha_hora_apertura)
        c.drawString(350, y, f"Fecha: {fecha_local.strftime('%d/%m/%Y %H:%M')}")

        y -= 30

        # INFORMACIÓN DE LA CAJA
        c.setFont(title_font, 12)
        c.drawString(50, y, "INFORMACION DE LA CAJA")
        c.setLineWidth(1)
        c.line(50, y - 5, 250, y - 5)

        y -= 25
        c.setFont(normal_font, 10)
        c.drawString(50, y, f"Caja: {self.caja.nombre}")
        y -= 15

        # Punto de expedición
        if self.caja.punto_expedicion:
            pe = self.caja.punto_expedicion
            establecimiento = pe.establecimiento
            c.drawString(50, y, f"Punto de Expedición: {establecimiento.codigo}-{pe.codigo}")
            y -= 15
            if establecimiento.direccion:
                c.drawString(50, y, f"Dirección: {establecimiento.direccion}")
                y -= 15

        # Badge de estado con color
        y -= 10
        c.setFont(normal_font, 10)
        c.drawString(50, y, "Estado:")

        # Color según el estado
        if self.esta_abierta:
            badge_color = colors.HexColor("#27ae60")  # Verde
            estado_text = "ABIERTA"
        else:
            badge_color = colors.HexColor("#e74c3c")  # Rojo
            estado_text = "CERRADA"

        # Dibujar badge redondeado
        badge_x = 100
        badge_y = y - 3
        badge_width = len(estado_text) * 6 + 16
        badge_height = 16
        badge_radius = 4

        # Fondo del badge con bordes redondeados
        c.setFillColor(badge_color)
        c.roundRect(badge_x, badge_y, badge_width, badge_height, badge_radius, fill=1, stroke=0)

        # Texto del badge en blanco
        c.setFillColor(colors.white)
        c.setFont(title_font, 9)
        c.drawString(badge_x + 8, badge_y + 4, estado_text)

        # Restaurar color negro
        c.setFillColor(colors.black)

        y -= 30

        # RESPONSABLE
        c.setFont(title_font, 12)
        c.drawString(50, y, "RESPONSABLE")
        c.line(50, y - 5, 200, y - 5)

        y -= 25
        c.setFont(normal_font, 10)
        if self.responsable and self.responsable.persona:
            from apps.persona.models import PersonaFisica
            persona = self.responsable.persona

            # Convertir a PersonaFisica si es una instancia de Persona base
            try:
                if not isinstance(persona, PersonaFisica):
                    persona = PersonaFisica.objects.get(pk=persona.pk)

                nombre_completo = f"{persona.nombre} {persona.apellido or ''}".strip()
                c.drawString(50, y, f"Nombre: {nombre_completo}")
                y -= 15
            except (PersonaFisica.DoesNotExist, AttributeError):
                # Si no es PersonaFisica, solo mostrar el documento
                pass

            if persona.documento:
                c.drawString(50, y, f"Documento: {persona.documento}")
                y -= 15

        # MONTOS INICIALES
        y -= 20
        c.setFont(title_font, 12)
        c.drawString(50, y, "MONTOS INICIALES")
        c.line(50, y - 5, 220, y - 5)

        y -= 30

        # Tabla de montos
        data = [
            ['Moneda', 'Monto'],
            ['Guaraníes (Gs)', f"Gs {self.monto_inicial:,.2f}"]
        ]

        # Si existe monto inicial alternativo (USD), agregarlo
        # Nota: En tu modelo actual no veo este campo, pero en el payload que enviaste
        # hay "monto_inicial_alternativo". Si quieres mostrarlo, necesitarás agregarlo al modelo.
        # Por ahora lo comentaré:
        # if hasattr(self, 'monto_inicial_alternativo') and self.monto_inicial_alternativo:
        #     data.append(['Dólares (USD)', f"$ {self.monto_inicial_alternativo:,.2f}"])

        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495e")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), title_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),

            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#34495e")),
        ]))

        # Dibujar tabla
        table.wrapOn(c, width, height)
        table.drawOn(c, 50, y - len(data) * 25)

        y -= len(data) * 25 + 30

        # OBSERVACIONES
        if self.observaciones_apertura:
            c.setFont(title_font, 12)
            c.drawString(50, y, "OBSERVACIONES")
            c.line(50, y - 5, 220, y - 5)

            y -= 25
            c.setFont(normal_font, 10)

            # Dividir observaciones en líneas si es muy largo
            observaciones = self.observaciones_apertura
            max_chars = 85
            lines = []
            while len(observaciones) > max_chars:
                # Buscar el último espacio antes del límite
                split_pos = observaciones[:max_chars].rfind(' ')
                if split_pos == -1:
                    split_pos = max_chars
                lines.append(observaciones[:split_pos])
                observaciones = observaciones[split_pos:].lstrip()
            if observaciones:
                lines.append(observaciones)

            for line in lines:
                c.drawString(50, y, line)
                y -= 15

        # PIE DE PÁGINA
        y = 50
        c.setFont(normal_font, 8)
        c.setFillColor(colors.grey)
        c.drawString(50, y, f"Generado el {now().strftime('%d/%m/%Y %H:%M')}")
        c.drawString(width - 200, y, "Sistema GroupTours - Arqueo de Caja")

        # Finalizar PDF
        c.showPage()
        c.save()

        # Retornar al inicio del buffer
        buffer.seek(0)
        return buffer


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
        """
        Recalcula el saldo de la caja desde cero basándose en todos los movimientos activos.
        Esto asegura que el saldo sea correcto incluso después de anulaciones.
        """
        from django.db.models import Sum

        caja = self.apertura_caja.caja

        # Obtener el monto inicial de la apertura
        monto_inicial = _to_decimal(self.apertura_caja.monto_inicial)

        # Sumar todos los ingresos activos
        total_ingresos = MovimientoCaja.objects.filter(
            apertura_caja=self.apertura_caja,
            tipo_movimiento='ingreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total']
        total_ingresos = _to_decimal(total_ingresos)

        # Sumar todos los egresos activos
        total_egresos = MovimientoCaja.objects.filter(
            apertura_caja=self.apertura_caja,
            tipo_movimiento='egreso',
            activo=True
        ).aggregate(total=Sum('monto'))['total']
        total_egresos = _to_decimal(total_egresos)

        # Calcular saldo actual = monto_inicial + ingresos - egresos
        caja.saldo_actual = monto_inicial + total_ingresos - total_egresos

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

    def generar_pdf(self):
        """
        Genera un PDF con los datos completos del cierre de caja.
        Incluye todos los movimientos del responsable de la caja.
        Retorna un objeto BytesIO con el PDF generado.
        """
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib.units import inch
        from io import BytesIO

        # Crear buffer para el PDF
        buffer = BytesIO()

        # Crear el canvas con tamaño carta
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Fuentes
        title_font = "Helvetica-Bold"
        normal_font = "Helvetica"

        # Posición inicial
        y = height - 60

        # ===============================
        # ENCABEZADO
        # ===============================
        c.setFont(title_font, 18)
        c.drawString(50, y, "CIERRE DE CAJA")

        # Línea decorativa
        c.setStrokeColor(colors.HexColor("#2c3e50"))
        c.setLineWidth(2)
        c.line(50, y - 8, width - 50, y - 8)

        y -= 35

        # ===============================
        # INFORMACIÓN DEL CIERRE
        # ===============================
        c.setFont(title_font, 11)
        c.drawString(50, y, f"Código: {self.codigo_cierre}")

        # Convertir a zona horaria local si está en UTC
        from django.utils import timezone
        fecha_cierre_local = timezone.localtime(self.fecha_hora_cierre)
        c.drawString(width - 220, y, f"Fecha: {fecha_cierre_local.strftime('%d/%m/%Y %H:%M')}")

        y -= 25

        # ===============================
        # INFORMACIÓN DE LA CAJA Y RESPONSABLE
        # ===============================
        c.setFont(title_font, 10)
        c.drawString(50, y, "CAJA:")
        c.setFont(normal_font, 9)
        c.drawString(100, y, f"{self.apertura_caja.caja.nombre}")

        c.setFont(title_font, 10)
        c.drawString(300, y, "RESPONSABLE:")
        c.setFont(normal_font, 9)
        responsable_nombre = ""
        if self.apertura_caja.responsable and self.apertura_caja.responsable.persona:
            from apps.persona.models import PersonaFisica
            persona = self.apertura_caja.responsable.persona
            try:
                if not isinstance(persona, PersonaFisica):
                    persona = PersonaFisica.objects.get(pk=persona.pk)
                responsable_nombre = f"{persona.nombre} {persona.apellido or ''}".strip()
            except (PersonaFisica.DoesNotExist, AttributeError):
                responsable_nombre = str(self.apertura_caja.responsable)
        else:
            responsable_nombre = str(self.apertura_caja.responsable)

        c.drawString(390, y, responsable_nombre)

        y -= 20

        # Punto de expedición
        if self.apertura_caja.caja.punto_expedicion:
            pe = self.apertura_caja.caja.punto_expedicion
            establecimiento = pe.establecimiento
            c.setFont(normal_font, 8)
            c.drawString(50, y, f"PE: {establecimiento.codigo}-{pe.codigo}")
            y -= 12

        y -= 10

        # ===============================
        # TABLA RESUMEN PRINCIPAL
        # ===============================
        c.setFont(title_font, 10)
        c.drawString(50, y, "RESUMEN DEL TURNO")
        c.setLineWidth(1)
        c.line(50, y - 3, 180, y - 3)

        y -= 20

        # Calcular totales
        total_ingresos = (
            self.total_efectivo +
            self.total_tarjetas +
            self.total_transferencias +
            self.total_cheques +
            self.total_otros_ingresos
        )

        # Datos de la tabla resumen
        data_resumen = [
            ['Concepto', 'Monto'],
            ['Monto Inicial', f"Gs {self.apertura_caja.monto_inicial:,.0f}"],
            ['Total Ingresos', f"Gs {total_ingresos:,.0f}"],
            ['Total Egresos', f"Gs {self.total_egresos:,.0f}"],
        ]

        table_resumen = Table(data_resumen, colWidths=[3*inch, 2*inch])
        table_resumen.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495e")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), title_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),

            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),

            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#34495e")),
        ]))

        table_resumen.wrapOn(c, width, height)
        table_resumen.drawOn(c, 50, y - len(data_resumen) * 20)

        y -= len(data_resumen) * 20 + 25

        # ===============================
        # DETALLE INGRESOS POR MÉTODO
        # ===============================
        c.setFont(title_font, 10)
        c.drawString(50, y, "DETALLE INGRESOS POR MÉTODO DE PAGO")
        c.line(50, y - 3, 280, y - 3)

        y -= 20

        data_ingresos = [
            ['Método de Pago', 'Monto'],
            ['Efectivo', f"Gs {self.total_efectivo:,.0f}"],
            ['Tarjetas', f"Gs {self.total_tarjetas:,.0f}"],
            ['Transferencias', f"Gs {self.total_transferencias:,.0f}"],
            ['Cheques', f"Gs {self.total_cheques:,.0f}"],
            ['Otros', f"Gs {self.total_otros_ingresos:,.0f}"],
        ]

        table_ingresos = Table(data_ingresos, colWidths=[3*inch, 2*inch])
        table_ingresos.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#27ae60")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), title_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),

            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),

            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#27ae60")),
        ]))

        table_ingresos.wrapOn(c, width, height)
        table_ingresos.drawOn(c, 50, y - len(data_ingresos) * 20)

        y -= len(data_ingresos) * 20 + 25

        # ===============================
        # ARQUEO DE CAJA
        # ===============================
        c.setFont(title_font, 10)
        c.drawString(50, y, "ARQUEO DE CAJA")
        c.line(50, y - 3, 160, y - 3)

        y -= 20

        # Determinar color de la diferencia
        diferencia_color = colors.black
        if self.diferencia_efectivo:
            if self.diferencia_efectivo > 0:
                diferencia_color = colors.HexColor("#27ae60")  # Verde para sobrante
            elif self.diferencia_efectivo < 0:
                diferencia_color = colors.HexColor("#e74c3c")  # Rojo para faltante

        data_arqueo = [
            ['Concepto', 'Monto'],
            ['Saldo Teórico', f"Gs {self.saldo_teorico_efectivo:,.0f}" if self.saldo_teorico_efectivo else "N/A"],
            ['Saldo Real Contado', f"Gs {self.saldo_real_efectivo:,.0f}" if self.saldo_real_efectivo else "N/A"],
            ['Diferencia', f"Gs {self.diferencia_efectivo:,.0f}" if self.diferencia_efectivo else "Gs 0"],
        ]

        # Agregar porcentaje si existe
        if self.diferencia_porcentaje:
            data_arqueo.append(['Diferencia %', f"{self.diferencia_porcentaje:.2f}%"])

        table_arqueo = Table(data_arqueo, colWidths=[3*inch, 2*inch])

        # Estilos base
        styles_arqueo = [
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), title_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),

            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),

            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#3498db")),
        ]

        # Aplicar color a la fila de diferencia
        styles_arqueo.append(('TEXTCOLOR', (1, 3), (1, 3), diferencia_color))
        styles_arqueo.append(('FONTNAME', (1, 3), (1, 3), title_font))

        table_arqueo.setStyle(TableStyle(styles_arqueo))

        table_arqueo.wrapOn(c, width, height)
        table_arqueo.drawOn(c, 50, y - len(data_arqueo) * 20)

        y -= len(data_arqueo) * 20 + 15

        # Badge de autorización si requiere
        if self.requiere_autorizacion:
            c.setFont(title_font, 9)
            badge_color = colors.HexColor("#e74c3c") if not self.autorizado_por else colors.HexColor("#27ae60")
            badge_text = "REQUIERE AUTORIZACION" if not self.autorizado_por else "AUTORIZADO"

            badge_x = 50
            badge_y = y - 3
            badge_width = len(badge_text) * 6 + 16
            badge_height = 16

            c.setFillColor(badge_color)
            c.roundRect(badge_x, badge_y, badge_width, badge_height, 4, fill=1, stroke=0)

            c.setFillColor(colors.white)
            c.drawString(badge_x + 8, badge_y + 4, badge_text)
            c.setFillColor(colors.black)

            y -= 25

        # ===============================
        # MOVIMIENTOS DEL RESPONSABLE
        # ===============================
        y -= 10

        # Verificar si hay espacio, si no, crear nueva página
        if y < 250:
            c.showPage()
            y = height - 60

        c.setFont(title_font, 10)
        c.drawString(50, y, "MOVIMIENTOS DEL TURNO")
        c.line(50, y - 3, 200, y - 3)

        y -= 20

        # Obtener movimientos del responsable en esta apertura
        movimientos = self.apertura_caja.movimientos.filter(
            activo=True,
            usuario_registro=self.apertura_caja.responsable
        ).order_by('fecha_hora_movimiento')

        if movimientos.exists():
            # Encabezados de la tabla de movimientos
            data_movimientos = [
                ['#', 'Fecha/Hora', 'Tipo', 'Concepto', 'Método', 'Monto']
            ]

            # Función auxiliar para obtener el display del concepto
            def get_concepto_label(concepto_value, tipo_mov):
                """Obtiene la etiqueta legible del concepto"""
                if tipo_mov == 'ingreso':
                    conceptos_dict = dict(MovimientoCaja.CONCEPTOS_INGRESO)
                else:
                    conceptos_dict = dict(MovimientoCaja.CONCEPTOS_EGRESO)
                return conceptos_dict.get(concepto_value, concepto_value)

            # Agregar cada movimiento
            for idx, mov in enumerate(movimientos, 1):
                fecha_mov = timezone.localtime(mov.fecha_hora_movimiento)
                tipo_display = "ING" if mov.tipo_movimiento == 'ingreso' else "EGR"

                # Obtener el concepto legible
                concepto_display = get_concepto_label(mov.concepto, mov.tipo_movimiento)
                if len(concepto_display) > 20:
                    concepto_display = concepto_display[:17] + "..."

                # Acortar método
                metodo_display = mov.get_metodo_pago_display()
                if len(metodo_display) > 12:
                    metodo_display = metodo_display[:9] + "..."

                data_movimientos.append([
                    str(idx),
                    fecha_mov.strftime('%d/%m %H:%M'),
                    tipo_display,
                    concepto_display,
                    metodo_display,
                    f"Gs {mov.monto:,.0f}"
                ])

            # Limitar a los primeros movimientos que quepan en la página
            max_movimientos = min(len(data_movimientos) - 1, 15)  # -1 porque el primer elemento es el header
            if max_movimientos < len(data_movimientos) - 1:
                data_movimientos = data_movimientos[:max_movimientos + 1]
                # Agregar nota de que hay más movimientos
                data_movimientos.append(['...', 'Más movimientos disponibles en el sistema', '', '', '', ''])

            table_movimientos = Table(data_movimientos, colWidths=[0.4*inch, 1.1*inch, 0.5*inch, 1.5*inch, 1.2*inch, 1.3*inch])
            table_movimientos.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#95a5a6")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), title_font),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 0), (-1, 0), 4),

                # Contenido
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (1, 1), (4, -1), 'LEFT'),
                ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
                ('FONTNAME', (0, 1), (-1, -1), normal_font),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('TOPPADDING', (0, 1), (-1, -1), 3),

                # Bordes
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#95a5a6")),
            ]))

            # Calcular espacio necesario
            table_height = len(data_movimientos) * 15

            if y - table_height < 100:
                c.showPage()
                y = height - 60
                c.setFont(title_font, 10)
                c.drawString(50, y, "MOVIMIENTOS DEL TURNO (continuación)")
                y -= 20

            table_movimientos.wrapOn(c, width, height)
            table_movimientos.drawOn(c, 50, y - table_height)

            y -= table_height + 15
        else:
            c.setFont(normal_font, 9)
            c.drawString(50, y, "No se registraron movimientos durante este turno.")
            y -= 20

        # ===============================
        # OBSERVACIONES
        # ===============================
        if self.observaciones_cierre or self.justificacion_diferencia:
            if y < 120:
                c.showPage()
                y = height - 60

            c.setFont(title_font, 10)
            c.drawString(50, y, "OBSERVACIONES")
            c.line(50, y - 3, 180, y - 3)

            y -= 18
            c.setFont(normal_font, 8)

            observaciones_text = ""
            if self.observaciones_cierre:
                observaciones_text += self.observaciones_cierre
            if self.justificacion_diferencia:
                if observaciones_text:
                    observaciones_text += "\n\n"
                observaciones_text += f"Justificación de diferencia: {self.justificacion_diferencia}"

            # Dividir en líneas
            max_chars = 95
            lines = []
            for paragraph in observaciones_text.split('\n'):
                while len(paragraph) > max_chars:
                    split_pos = paragraph[:max_chars].rfind(' ')
                    if split_pos == -1:
                        split_pos = max_chars
                    lines.append(paragraph[:split_pos])
                    paragraph = paragraph[split_pos:].lstrip()
                if paragraph:
                    lines.append(paragraph)

            for line in lines[:8]:  # Limitar a 8 líneas
                c.drawString(50, y, line)
                y -= 11

        # ===============================
        # PIE DE PÁGINA
        # ===============================
        y = 50
        c.setFont(normal_font, 7)
        c.setFillColor(colors.grey)
        c.drawString(50, y, f"Generado el {now().strftime('%d/%m/%Y %H:%M')}")
        c.drawString(width - 240, y, "Sistema GroupTours - Arqueo de Caja")

        # Finalizar PDF
        c.showPage()
        c.save()

        # Retornar al inicio del buffer
        buffer.seek(0)
        return buffer
