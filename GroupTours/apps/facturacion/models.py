# apps/facturacion/models.py
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

# ---------- Tipos de impuesto ----------
class TipoImpuesto(models.Model):
    nombre = models.CharField(max_length=50)  # Ej: "IVA", "IRP", "ISC"
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)  # Nuevo campo

    def __str__(self):
        return self.nombre


class SubtipoImpuesto(models.Model):
    tipo_impuesto = models.ForeignKey(TipoImpuesto, on_delete=models.CASCADE, related_name="subtipos")
    nombre = models.CharField(max_length=50)  # Ej: "IVA 10%", "IVA 5%", "IVA 0%"
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(default=True)  # Nuevo campo

    def __str__(self):
        return f"{self.tipo_impuesto.nombre} - {self.nombre}"


# ---------- Empresa (única) ----------
class Empresa(models.Model):
    # Solo una empresa en todo el sistema
    ruc = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=250, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    actividades = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True) 

    def save(self, *args, **kwargs):
        if not self.pk and Empresa.objects.exists():
            raise ValueError("Solo puede existir una empresa en el sistema")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


# ---------- Establecimiento ----------
class Establecimiento(models.Model):
    nombre = models.CharField(max_length=100, default='SIN NOMBRE')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="establecimientos")
    codigo = models.CharField(max_length=3)  # Ej: "001"
    direccion = models.CharField(max_length=250, blank=True, null=True)
    activo = models.BooleanField(default=True) 

    class Meta:
        unique_together = ("empresa", "codigo")

    def __str__(self):
        return f"{self.empresa.nombre} - Estab {self.codigo}"


# ---------- Punto de Expedición ----------
class PuntoExpedicion(models.Model):
    nombre = models.CharField(max_length=100, default='SIN NOMBRE')
    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.CASCADE, related_name="puntos_expedicion")
    codigo = models.CharField(max_length=3)  # Ej: "001"
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True) 

    class Meta:
        unique_together = ("establecimiento", "codigo")

    def __str__(self):
        return f"{self.establecimiento.codigo}-{self.codigo}"


# ---------- Timbrado ----------
class Timbrado(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="timbrados")
    numero = models.CharField(max_length=20)
    inicio_vigencia = models.DateField()
    fin_vigencia = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.numero} ({self.empresa.nombre})"


# ---------- Cliente de Facturación ----------
class ClienteFacturacion(models.Model):
    """
    Modelo para almacenar datos de clientes de facturación.
    Permite registrar terceros para emitir facturas a su nombre.
    Puede estar vinculado a una Persona del sistema o ser independiente.
    """
    # Datos obligatorios
    nombre = models.CharField(
        max_length=200,
        help_text="Nombre completo o razón social del cliente"
    )
    tipo_documento = models.ForeignKey(
        'tipo_documento.TipoDocumento',
        on_delete=models.PROTECT,
        related_name='clientes_facturacion',
        help_text="Tipo de documento de identidad"
    )
    numero_documento = models.CharField(
        max_length=20,
        help_text="Número de documento (CI, RUC, Pasaporte, etc.)"
    )

    # Datos opcionales
    direccion = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        help_text="Dirección del cliente"
    )
    telefono = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Teléfono de contacto"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Correo electrónico"
    )

    # Relación opcional con Persona del sistema
    persona = models.ForeignKey(
        'persona.Persona',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clientes_facturacion',
        help_text="Persona del sistema asociada (opcional)"
    )

    # Control
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cliente_facturacion'
        verbose_name = 'Cliente de Facturación'
        verbose_name_plural = 'Clientes de Facturación'
        indexes = [
            models.Index(fields=['numero_documento', 'tipo_documento']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.tipo_documento.nombre}: {self.numero_documento})"

    def clean(self):
        """Validaciones del modelo"""
        if not self.nombre or not self.nombre.strip():
            raise ValidationError("El nombre del cliente es obligatorio")
        if not self.numero_documento or not self.numero_documento.strip():
            raise ValidationError("El número de documento es obligatorio")


# ---------- Factura Electrónica ----------
class FacturaElectronica(models.Model):
    CONDICION_VENTA_CHOICES = [
        ('contado', 'Contado'),
        ('credito', 'Crédito'),
    ]

    TIPO_FACTURACION_CHOICES = [
        ('total', 'Factura Total (Reserva Completa)'),
        ('por_pasajero', 'Factura por Pasajero Individual'),
    ]

    # Relaciones básicas
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="facturas")
    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.PROTECT)
    punto_expedicion = models.ForeignKey(PuntoExpedicion, on_delete=models.PROTECT, null=True, blank=True)
    timbrado = models.ForeignKey(Timbrado, on_delete=models.PROTECT)
    es_configuracion = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    tipo_impuesto = models.ForeignKey(TipoImpuesto, on_delete=models.PROTECT)
    subtipo_impuesto = models.ForeignKey(SubtipoImpuesto, on_delete=models.SET_NULL, null=True, blank=True)

    # Relación con Reserva (solo para facturas reales)
    reserva = models.ForeignKey(
        'reserva.Reserva',
        on_delete=models.PROTECT,
        related_name='facturas',
        null=True,
        blank=True,
        help_text="Reserva asociada a esta factura"
    )

    # NUEVO: Tipo de facturación
    tipo_facturacion = models.CharField(
        max_length=20,
        choices=TIPO_FACTURACION_CHOICES,
        default='total',
        null=True,
        blank=True,
        help_text="Modalidad de facturación: total o por pasajero"
    )

    # NUEVO: Relación con Pasajero (solo si tipo_facturacion='por_pasajero')
    pasajero = models.ForeignKey(
        'reserva.Pasajero',
        on_delete=models.PROTECT,
        related_name='facturas',
        null=True,
        blank=True,
        help_text="Pasajero específico (solo si tipo_facturacion='por_pasajero')"
    )

    # NUEVO: Cliente de facturación (tercero opcional)
    cliente_facturacion = models.ForeignKey(
        'ClienteFacturacion',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='facturas',
        help_text="Cliente a nombre del cual se emite la factura (tercero opcional). Si se especifica, sobrescribe los datos del titular/pasajero"
    )

    # Datos de la factura (solo para facturas reales)
    numero_factura = models.CharField(max_length=15, editable=False, null=True, blank=True)
    fecha_emision = models.DateTimeField(null=True, blank=True)

    # Datos del cliente
    cliente_tipo_documento = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Tipo de documento: RUC, CI, etc."
    )
    cliente_numero_documento = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Número de documento del cliente"
    )
    cliente_nombre = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Nombre o razón social del cliente"
    )
    cliente_direccion = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Dirección del cliente"
    )
    cliente_telefono = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Teléfono del cliente"
    )
    cliente_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email del cliente"
    )

    # Condiciones de venta
    condicion_venta = models.CharField(
        max_length=10,
        choices=CONDICION_VENTA_CHOICES,
        default='contado',
        null=True,
        blank=True
    )

    # Campos específicos para crédito
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento del crédito. Para crédito: fecha_salida - 15 días"
    )

    # Moneda
    moneda = models.ForeignKey(
        'moneda.Moneda',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Moneda de la factura"
    )

    # Totales calculados (se llenan automáticamente)
    total_exenta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total de operaciones exentas"
    )
    total_gravada_5 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total gravado IVA 5%"
    )
    total_gravada_10 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total gravado IVA 10%"
    )
    total_iva_5 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="IVA 5%"
    )
    total_iva_10 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="IVA 10%"
    )
    total_iva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total IVA"
    )
    total_general = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total general de la factura"
    )

    # PDF generado
    pdf_generado = models.FileField(
        upload_to='facturas/pdf/',
        null=True,
        blank=True,
        help_text="PDF de la factura"
    )

    class Meta:
        unique_together = ("establecimiento", "punto_expedicion", "numero_factura")

    def __str__(self):
        if self.es_configuracion:
            return f"CONFIG - {self.empresa.nombre}"
        return f"{self.numero_factura} - {self.empresa.nombre}"

    @property
    def total_acreditado(self):
        """
        Calcula el total acreditado por notas de crédito activas.
        Suma todos los totales de las NC que afectan esta factura.
        """
        from django.db.models import Sum
        total = self.notas_credito.filter(activo=True).aggregate(
            total=Sum('total_general')
        )['total']
        return total or Decimal('0')

    @property
    def saldo_neto(self):
        """
        Calcula el saldo neto de la factura.
        Formula: total_general - total_acreditado
        Este es el monto que aún está vigente de la factura.
        """
        return self.total_general - self.total_acreditado

    @property
    def esta_totalmente_acreditada(self):
        """
        Verifica si la factura fue completamente anulada por notas de crédito.
        Retorna True si el saldo neto es 0.
        """
        return self.saldo_neto == Decimal('0')

    @property
    def esta_parcialmente_acreditada(self):
        """
        Verifica si la factura tiene notas de crédito pero no está totalmente anulada.
        """
        return self.total_acreditado > Decimal('0') and not self.esta_totalmente_acreditada

    def puede_generar_nota_credito(self):
        """
        Valida si se puede generar una nota de crédito para esta factura.

        Returns:
            tuple: (bool, str) - (puede_generar, mensaje)
        """
        if not self.activo:
            return False, "Factura inactiva"

        if self.es_configuracion:
            return False, "No se puede acreditar una factura de configuración"

        if self.esta_totalmente_acreditada:
            return False, "Factura ya totalmente acreditada"

        if self.saldo_neto <= Decimal('0'):
            return False, "No hay saldo disponible para acreditar"

        return True, "OK"

    def save(self, *args, **kwargs):
        # Validar si es configuración
        if self.es_configuracion:
            # Si es configuración, no se requiere punto de expedición
            self.punto_expedicion = None
            self.numero_factura = None
            self.fecha_emision = None
        else:
            # Si es factura real, se requiere punto de expedición
            if not self.punto_expedicion:
                raise ValueError("El punto de expedición es obligatorio para facturas reales")
            if not self.numero_factura:
                self.numero_factura = self.generar_numero_factura()

        super().save(*args, **kwargs)

    def generar_numero_factura(self):
        """
        Formato: XXX-XXX-XXXXXXX
        Donde:
        - XXX = código del establecimiento
        - XXX = código del punto de expedición
        - XXXXXXX = correlativo incremental
        """
        ultimo = FacturaElectronica.objects.filter(
            establecimiento=self.establecimiento,
            punto_expedicion=self.punto_expedicion,
            es_configuracion=False
        ).aggregate(max_num=Max('numero_factura'))['max_num']

        if ultimo:
            try:
                correlativo = int(ultimo.split('-')[2]) + 1
            except:
                correlativo = 1
        else:
            correlativo = 1

        correlativo_str = str(correlativo).zfill(7)
        return f"{self.establecimiento.codigo}-{self.punto_expedicion.codigo}-{correlativo_str}"

    def calcular_totales(self):
        """
        Calcula los totales de la factura basándose en sus detalles.
        """
        from decimal import Decimal

        self.total_exenta = Decimal('0')
        self.total_gravada_5 = Decimal('0')
        self.total_gravada_10 = Decimal('0')

        for detalle in self.detalles.all():
            self.total_exenta += detalle.monto_exenta
            self.total_gravada_5 += detalle.monto_gravada_5
            self.total_gravada_10 += detalle.monto_gravada_10

        # Calcular IVA (la base gravada ya incluye el IVA, hay que extraerlo)
        # IVA 5% = base * 5/105
        # IVA 10% = base * 10/110
        self.total_iva_5 = (self.total_gravada_5 * Decimal('5')) / Decimal('105')
        self.total_iva_10 = (self.total_gravada_10 * Decimal('10')) / Decimal('110')
        self.total_iva = self.total_iva_5 + self.total_iva_10

        self.total_general = self.total_exenta + self.total_gravada_5 + self.total_gravada_10

        self.save()

    def generar_pdf(self):
        """
        Genera un PDF de la factura usando ReportLab siguiendo el formato oficial paraguayo.
        Retorna la ruta del archivo generado.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from django.core.files.base import ContentFile
        from django.conf import settings
        import io
        import os

        # Crear buffer para el PDF
        buffer = io.BytesIO()

        # Crear documento con márgenes más estrechos
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Lista de elementos del documento
        elements = []

        # Estilos
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleFactura',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=2,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT
        )

        small_bold_style = ParagraphStyle(
            'SmallBold',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        )

        small_center_style = ParagraphStyle(
            'SmallCenter',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER
        )

        # ===== ANCHO ESTÁNDAR PARA TODAS LAS TABLAS =====
        # Basado en la tabla de TOTALES: 2.3 + 0.8 + 0.8 + 0.9 + 0.9 + 0.8 = 6.5 inches
        TABLE_WIDTH = 6.5*inch

        # ===== ENCABEZADO CON BORDE =====
        # Construir encabezado con logo y datos de empresa
        logo_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'logo_group_tours.png')

        header_data = []

        # Fila 1: Logo y datos empresa (TOTAL: 6.5")
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
            empresa_info = Paragraph(f'''
                <b>{self.empresa.nombre}</b><br/>
                {self.empresa.direccion or ''}<br/>
                Teléfono: {self.empresa.telefono or 'N/A'}<br/>
                {self.empresa.correo or ''}<br/>
                Actividad económica: Agencia de Viajes
            ''', small_style)

            datos_fiscales = Paragraph(f'''
                <b>RUC:</b> {self.empresa.ruc}<br/>
                <b>Timbrado N°:</b> {self.timbrado.numero}<br/>
                <b>Fecha de Inicio de Vigencia:</b> {self.timbrado.inicio_vigencia.strftime('%d/%m/%Y')}<br/>
                <br/>
                <b>FACTURA ELECTRÓNICA</b><br/>
                <b>{self.numero_factura}</b>
            ''', small_style)

            # Total: 1.5 + 3.0 + 2.0 = 6.5"
            header_table = Table([[logo, empresa_info, datos_fiscales]],
                                colWidths=[1.5*inch, 3.0*inch, 2.0*inch])
        else:
            empresa_info = Paragraph(f'''
                <b>{self.empresa.nombre}</b><br/>
                {self.empresa.direccion or ''}<br/>
                Teléfono: {self.empresa.telefono or 'N/A'}<br/>
                {self.empresa.correo or ''}
            ''', small_style)

            datos_fiscales = Paragraph(f'''
                <b>RUC:</b> {self.empresa.ruc}<br/>
                <b>Timbrado N°:</b> {self.timbrado.numero}<br/>
                <b>Fecha Inicio Vigencia:</b> {self.timbrado.inicio_vigencia.strftime('%d/%m/%Y')}<br/>
                <br/>
                <b>FACTURA ELECTRÓNICA</b><br/>
                <b>{self.numero_factura}</b>
            ''', small_style)

            # Total: 4.5 + 2.0 = 6.5"
            header_table = Table([[empresa_info, datos_fiscales]],
                                colWidths=[4.5*inch, 2.0*inch])

        header_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 0.15*inch))

        # ===== DATOS DE TRANSACCIÓN =====
        transaccion_data = [
            [
                Paragraph(f'<b>Fecha y hora de emisión:</b> {self.fecha_emision.strftime("%d-%m-%Y %H:%M:%S")}', small_style),
                Paragraph(f'<b>RUC/Documento de Identidad No:</b> {self.cliente_numero_documento}', small_style)
            ],
            [
                Paragraph(f'<b>Condición de venta:</b> {self.condicion_venta.capitalize()}', small_style),
                Paragraph(f'<b>Nombre o Razón Social:</b> {self.cliente_nombre}', small_style)
            ],
            [
                Paragraph(f'<b>Moneda:</b> {self.moneda.nombre.upper()}', small_style),
                Paragraph(f'<b>Dirección:</b> {self.cliente_direccion or "N/A"}', small_style)
            ],
            [
                Paragraph('', small_style),
                Paragraph(f'<b>Teléfono:</b> {self.cliente_telefono or "N/A"}', small_style)
            ],
            [
                Paragraph('', small_style),
                Paragraph(f'<b>Correo Electrónico:</b> {self.cliente_email or "N/A"}', small_style)
            ]
        ]

        # Total: 3.25 + 3.25 = 6.5"
        transaccion_table = Table(transaccion_data, colWidths=[3.25*inch, 3.25*inch])
        transaccion_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        elements.append(transaccion_table)
        elements.append(Spacer(1, 0.15*inch))

        # ===== TABLA DE DETALLES =====
        # Encabezados con span para "Valor de Venta"
        detalle_header = ['Cod', 'Descripción', 'Unidad\nmedida', 'Cantidad', 'Precio\nUnitario', 'Descuento', 'Valor de Venta', '', '']
        sub_header = ['', '', '', '', '', '', 'Exentas', '5%', '10%']

        detalle_data = [detalle_header, sub_header]

        for detalle in self.detalles.all():
            # Formatear los valores de venta
            exenta_val = f"{int(detalle.monto_exenta):,}" if detalle.monto_exenta > 0 else "0"
            iva5_val = f"{int(detalle.monto_gravada_5):,}" if detalle.monto_gravada_5 > 0 else "0"
            iva10_val = f"{int(detalle.monto_gravada_10):,}" if detalle.monto_gravada_10 > 0 else "0"

            detalle_data.append([
                '',  # Código
                str(detalle.descripcion)[:50],
                'UNI',
                str(int(detalle.cantidad)),
                f"{int(detalle.precio_unitario):,}",
                '',
                exenta_val,  # Columna separada para Exentas
                iva5_val,    # Columna separada para 5%
                iva10_val    # Columna separada para 10%
            ])

        # Agregar filas vacías si es necesario
        while len(detalle_data) < 7:
            detalle_data.append(['', '', '', '', '', '', '', '', ''])

        # Total: 0.4 + 2.2 + 0.5 + 0.5 + 0.7 + 0.5 + 0.6 + 0.55 + 0.55 = 6.5"
        detalle_table = Table(detalle_data, colWidths=[0.4*inch, 2.2*inch, 0.5*inch, 0.5*inch, 0.7*inch, 0.5*inch, 0.6*inch, 0.55*inch, 0.55*inch])
        detalle_table.setStyle(TableStyle([
            # Bordes generales
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),

            # Span del encabezado "Valor de Venta" (fusionar 3 columnas)
            ('SPAN', (6, 0), (8, 0)),

            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Contenido
            ('ALIGN', (2, 2), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        elements.append(detalle_table)
        elements.append(Spacer(1, 0.1*inch))

        # ===== TOTALES =====
        total_exenta = int(self.total_exenta)
        total_5 = int(self.total_gravada_5)
        total_10 = int(self.total_gravada_10)
        iva_5 = int(self.total_iva_5)
        iva_10 = int(self.total_iva_10)
        total_iva = int(self.total_iva)
        total_gral = int(self.total_general)

        totales_data = [
            ['SUBTOTAL:', '', '', '', '', f"{total_gral:,}"],
            ['TOTAL DE LA OPERACIÓN:', '', '', '', '', f"{total_gral:,}"],
            ['TOTAL EN GUARANÍES:', '', '', '', '', f"{total_gral:,}"],
            ['LIQUIDACIÓN IVA:', '(5%)', '(10%)', f"{iva_5 + iva_10:,}", 'TOTAL IVA:', f"{total_iva:,}"]
        ]

        # Total: 2.3 + 0.8 + 0.8 + 0.9 + 0.9 + 0.8 = 6.5"
        totales_table = Table(totales_data, colWidths=[2.3*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.9*inch, 0.8*inch])
        totales_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        elements.append(totales_table)
        elements.append(Spacer(1, 0.15*inch))

        # ===== PIE DE PÁGINA CON QR Y VALIDEZ =====
        try:
            import qrcode
            from io import BytesIO

            # Generar CDC simulado (en producción vendría de la SET)
            cdc_simulado = f"0144 4444 0170 0100 1001 4528 2250 1201 7158 7322 {self.id:04d}"
            url_consulta = "https://ekuatia.set.gov.py/consultas/"

            # Generar código QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
            qr.add_data(url_consulta)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")

            # Guardar QR en buffer
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)

            # Crear imagen de QR para ReportLab
            qr_image = Image(qr_buffer, width=0.8*inch, height=0.8*inch)

            # Estilo para el pie
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=7,
                leading=9,
                alignment=TA_LEFT
            )

            footer_bold_style = ParagraphStyle(
                'FooterBold',
                parent=styles['Normal'],
                fontSize=7,
                leading=9,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT
            )

            cdc_style = ParagraphStyle(
                'CDC',
                parent=styles['Normal'],
                fontSize=8,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#0066cc'),
                alignment=TA_LEFT
            )

            # Texto del pie de página
            footer_text = f'''
                <b>Consulte la validez de esta Factura Electrónica con el número de CDC impreso abajo en:</b><br/>
                <font color="#0066cc">{url_consulta}</font><br/>
                <br/>
                <font color="#0066cc" size="8"><b>CDC: {cdc_simulado}</b></font><br/>
                <br/>
                <b>ESTE DOCUMENTO ES UNA REPRESENTACIÓN GRÁFICA DE UN DOCUMENTO ELECTRÓNICO (XML)</b><br/>
                <br/>
                <b>Información de interés del facturador electrónico emisor.</b><br/>
                Si su documento electrónico presenta algún error, podrá solicitar la modificación dentro de las<br/>
                72 horas siguientes de la emisión de este comprobante
            '''

            footer_paragraph = Paragraph(footer_text, footer_style)

            # Total: 1.0 + 5.5 = 6.5"
            footer_table = Table([[qr_image, footer_paragraph]], colWidths=[1.0*inch, 5.5*inch])
            footer_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ]))

            elements.append(footer_table)

        except ImportError:
            # Si qrcode no está instalado, mostrar mensaje simple
            footer_text = Paragraph(
                f'<i>Documento asociado: Reserva {self.reserva.codigo if self.reserva else "N/A"}</i>',
                small_center_style
            )
            elements.append(footer_text)

        # Agregar referencia a la reserva si existe
        if self.reserva:
            elements.append(Spacer(1, 0.1*inch))
            reserva_text = Paragraph(
                f'<i>Reserva asociada: {self.reserva.codigo}</i>',
                small_center_style
            )
            elements.append(reserva_text)

        # Construir PDF
        doc.build(elements)

        # Guardar el PDF
        buffer.seek(0)
        filename = f"factura_{self.numero_factura.replace('-', '_')}.pdf"

        self.pdf_generado.save(filename, ContentFile(buffer.read()), save=True)

        return self.pdf_generado.path


# ---------- Detalle de Factura ----------
class DetalleFactura(models.Model):
    """
    Representa un ítem/línea en la factura.
    Cada detalle tiene su desglose de IVA.
    """
    factura = models.ForeignKey(
        FacturaElectronica,
        on_delete=models.CASCADE,
        related_name='detalles',
        help_text="Factura a la que pertenece este detalle"
    )

    numero_item = models.PositiveIntegerField(
        help_text="Número de línea en la factura"
    )

    descripcion = models.CharField(
        max_length=250,
        help_text="Descripción del producto o servicio"
    )

    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cantidad de unidades"
    )

    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Precio unitario"
    )

    # Desglose por tipo de gravamen
    monto_exenta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto exento de IVA"
    )

    monto_gravada_5 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto gravado con IVA 5%"
    )

    monto_gravada_10 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto gravado con IVA 10%"
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Subtotal del ítem (cantidad * precio_unitario)"
    )

    class Meta:
        ordering = ['numero_item']
        unique_together = ('factura', 'numero_item')
        verbose_name = "Detalle de Factura"
        verbose_name_plural = "Detalles de Factura"

    def __str__(self):
        return f"{self.factura.numero_factura} - Item {self.numero_item}: {self.descripcion}"

    def save(self, *args, **kwargs):
        # Calcular subtotal
        from decimal import Decimal
        self.subtotal = Decimal(str(self.cantidad)) * Decimal(str(self.precio_unitario))
        super().save(*args, **kwargs)


# ---------- Funciones auxiliares para facturación ----------
def obtener_o_crear_cliente_facturacion(
    cliente_facturacion_id=None,
    tercero_nombre=None,
    tercero_tipo_documento=None,
    tercero_numero_documento=None,
    tercero_direccion=None,
    tercero_telefono=None,
    tercero_email=None,
    persona=None
):
    """
    Función híbrida para obtener o crear un ClienteFacturacion.

    Prioridades:
    1. Si se proporciona cliente_facturacion_id, lo busca y retorna
    2. Si se proporcionan datos de tercero, busca por documento o crea uno nuevo
    3. Si se proporciona persona, crea un cliente vinculado a esa persona
    4. Si no hay nada, retorna None

    Args:
        cliente_facturacion_id: ID de cliente existente
        tercero_nombre: Nombre del tercero
        tercero_tipo_documento: ID o nombre del TipoDocumento
        tercero_numero_documento: Número de documento
        tercero_direccion: Dirección (opcional)
        tercero_telefono: Teléfono (opcional)
        tercero_email: Email (opcional)
        persona: Instancia de Persona para vincular (opcional)

    Returns:
        ClienteFacturacion o None

    Raises:
        ValidationError: Si los datos son inválidos
    """
    from apps.tipo_documento.models import TipoDocumento

    # Opción 1: Buscar cliente existente por ID
    if cliente_facturacion_id:
        try:
            cliente = ClienteFacturacion.objects.get(id=cliente_facturacion_id, activo=True)
            return cliente
        except ClienteFacturacion.DoesNotExist:
            raise ValidationError(f"No existe cliente de facturación con ID {cliente_facturacion_id}")

    # Opción 2: Crear/obtener cliente desde datos de tercero
    if tercero_nombre and tercero_tipo_documento and tercero_numero_documento:
        # Obtener instancia de TipoDocumento
        if isinstance(tercero_tipo_documento, int):
            # Si es ID, buscar por ID
            try:
                tipo_doc_obj = TipoDocumento.objects.get(id=tercero_tipo_documento, activo=True)
            except TipoDocumento.DoesNotExist:
                raise ValidationError(f"No existe tipo de documento con ID {tercero_tipo_documento}")
        elif isinstance(tercero_tipo_documento, str):
            # Intentar convertir a int si es un string numérico
            if tercero_tipo_documento.isdigit():
                try:
                    tipo_doc_obj = TipoDocumento.objects.get(id=int(tercero_tipo_documento), activo=True)
                except TipoDocumento.DoesNotExist:
                    raise ValidationError(f"No existe tipo de documento con ID {tercero_tipo_documento}")
            else:
                # Si no es numérico, buscar por nombre
                tipo_doc_obj = TipoDocumento.objects.filter(nombre__iexact=tercero_tipo_documento, activo=True).first()
                if not tipo_doc_obj:
                    raise ValidationError(f"No existe tipo de documento '{tercero_tipo_documento}'")
        else:
            # Ya es una instancia de TipoDocumento
            tipo_doc_obj = tercero_tipo_documento

        # Buscar si ya existe un cliente con ese documento
        cliente_existente = ClienteFacturacion.objects.filter(
            tipo_documento=tipo_doc_obj,
            numero_documento=tercero_numero_documento,
            activo=True
        ).first()

        if cliente_existente:
            # Actualizar datos si han cambiado
            actualizado = False
            if tercero_nombre and cliente_existente.nombre != tercero_nombre:
                cliente_existente.nombre = tercero_nombre
                actualizado = True
            if tercero_direccion and cliente_existente.direccion != tercero_direccion:
                cliente_existente.direccion = tercero_direccion
                actualizado = True
            if tercero_telefono and cliente_existente.telefono != tercero_telefono:
                cliente_existente.telefono = tercero_telefono
                actualizado = True
            if tercero_email and cliente_existente.email != tercero_email:
                cliente_existente.email = tercero_email
                actualizado = True

            if actualizado:
                cliente_existente.save()

            return cliente_existente
        else:
            # Crear nuevo cliente
            cliente = ClienteFacturacion.objects.create(
                nombre=tercero_nombre,
                tipo_documento=tipo_doc_obj,
                numero_documento=tercero_numero_documento,
                direccion=tercero_direccion or '',
                telefono=tercero_telefono or '',
                email=tercero_email or '',
                persona=persona,
                activo=True
            )
            return cliente

    # Opción 3: Crear cliente desde Persona
    if persona:
        # Determinar datos desde la persona
        if hasattr(persona, 'personajuridica'):
            nombre = persona.razon_social
            tipo_doc_obj = persona.tipo_documento
            numero_doc = getattr(persona, 'documento', 'S/N')
        else:
            nombre = f"{getattr(persona, 'nombre', '')} {getattr(persona, 'apellido', '')}".strip()
            tipo_doc_obj = persona.tipo_documento
            numero_doc = getattr(persona, 'documento', 'S/N')

        # Buscar si ya existe
        cliente_existente = ClienteFacturacion.objects.filter(
            tipo_documento=tipo_doc_obj,
            numero_documento=numero_doc,
            activo=True
        ).first()

        if cliente_existente:
            return cliente_existente

        # Crear nuevo
        cliente = ClienteFacturacion.objects.create(
            nombre=nombre,
            tipo_documento=tipo_doc_obj,
            numero_documento=numero_doc,
            direccion=getattr(persona, 'direccion', ''),
            telefono=getattr(persona, 'telefono', ''),
            email=getattr(persona, 'correo', getattr(persona, 'email', '')),
            persona=persona,
            activo=True
        )
        return cliente

    # No hay datos suficientes
    return None


# ---------- Funciones de validación para facturación dual ----------
def validar_factura_global(reserva):
    """
    Validaciones exhaustivas para emitir factura global.

    Args:
        reserva: Instancia de Reserva

    Raises:
        ValidationError: Si no cumple las condiciones para facturar
    """
    # 1. Modalidad de facturación debe estar definida
    if reserva.modalidad_facturacion is None:
        raise ValidationError(
            "La modalidad de facturación no ha sido definida. "
            "Debe confirmar la reserva y elegir la modalidad primero."
        )

    # 2. Modalidad debe ser 'global'
    if reserva.modalidad_facturacion != 'global':
        raise ValidationError(
            "Esta reserva está configurada para facturación individual. "
            "No se puede emitir factura global."
        )

    # 3. Condición de pago debe estar definida
    if reserva.condicion_pago is None:
        raise ValidationError(
            "La condición de pago no ha sido definida. "
            "Debe confirmar la reserva y elegir la condición de pago primero."
        )

    # 4. Estado de reserva y validación de pago según condición
    if reserva.condicion_pago == 'contado':
        # Para CONTADO: Debe estar finalizada y totalmente pagada
        if reserva.estado != 'finalizada':
            raise ValidationError(
                "La reserva debe estar en estado 'finalizada' para emitir factura al contado."
            )

        if reserva.monto_pagado < reserva.costo_total_estimado:
            saldo_pendiente = reserva.costo_total_estimado - reserva.monto_pagado
            raise ValidationError(
                f"La reserva tiene saldo pendiente de {saldo_pendiente}. "
                f"Debe pagar el total antes de facturar al contado."
            )
    elif reserva.condicion_pago == 'credito':
        # Para CRÉDITO: Debe estar al menos confirmada (no requiere pago total)
        if reserva.estado not in ['confirmada', 'finalizada']:
            raise ValidationError(
                "La reserva debe estar en estado 'confirmada' o 'finalizada' para emitir factura a crédito."
            )

    # 5. No tener factura global previa
    if reserva.facturas.filter(tipo_facturacion='total', activo=True).exists():
        raise ValidationError(
            "Ya existe una factura global para esta reserva."
        )

    # 6. No existir facturas individuales
    if reserva.facturas.filter(tipo_facturacion='por_pasajero', activo=True).exists():
        raise ValidationError(
            "Ya existen facturas individuales para esta reserva. "
            "No se puede emitir factura global."
        )

def validar_factura_individual(reserva, pasajero):
    """
    Validaciones para emitir factura individual de un pasajero.
    """
    # --- Validaciones generales ---
    if reserva.modalidad_facturacion is None:
        raise ValidationError("Debe definir la modalidad de facturación primero.")

    if reserva.modalidad_facturacion != 'individual':
        raise ValidationError("Esta reserva está configurada para facturación global.")

    if reserva.estado not in ['confirmada', 'finalizada']:
        raise ValidationError("La reserva debe estar confirmada o finalizada para facturar.")

    # --- Validación por pasajero ---
    if not pasajero.esta_totalmente_pagado:
        raise ValidationError("El pasajero no ha completado su pago, no puede generar factura.")

    if pasajero.por_asignar:
        raise ValidationError("El pasajero aún no está asignado, no puede generar factura.")

    # --- Validaciones de facturas existentes ---
    if reserva.facturas.filter(tipo_facturacion='total', activo=True).exists():
        raise ValidationError("Ya existe una factura global, no se pueden emitir individuales.")

    if reserva.facturas.filter(tipo_facturacion='por_pasajero', pasajero=pasajero, activo=True).exists():
        raise ValidationError("El pasajero ya tiene una factura individual activa.")

# ---------- Función para generar factura desde reserva (LEGACY - mantenida por compatibilidad) ----------
@transaction.atomic
def generar_factura_desde_reserva(reserva, subtipo_impuesto_id=None):
    """
    Genera una factura electrónica a partir de una reserva.

    Args:
        reserva: Instancia de Reserva
        subtipo_impuesto_id: ID del subtipo de impuesto a aplicar (ej: IVA 10%)

    Returns:
        FacturaElectronica: La factura generada

    Raises:
        ValidationError: Si la reserva no está en estado válido o falta configuración
    """
    from apps.reserva.models import Reserva

    # Validaciones
    if reserva.estado not in ['confirmada', 'finalizada']:
        raise ValidationError(
            f"La reserva debe estar confirmada o finalizada para facturar. Estado actual: {reserva.estado}"
        )

    # Verificar si ya tiene factura
    if reserva.facturas.exists():
        raise ValidationError("Esta reserva ya tiene una factura generada")

    # Obtener configuración de facturación
    configuracion = FacturaElectronica.objects.filter(
        es_configuracion=True,
        activo=True
    ).first()

    if not configuracion:
        raise ValidationError("No existe configuración de facturación en el sistema")

    # Determinar subtipo de impuesto
    if subtipo_impuesto_id:
        subtipo_impuesto = SubtipoImpuesto.objects.get(id=subtipo_impuesto_id)
    else:
        subtipo_impuesto = configuracion.subtipo_impuesto

    if not subtipo_impuesto:
        raise ValidationError("Debe especificar un subtipo de impuesto")

    # Obtener punto de expedición activo
    punto_expedicion = PuntoExpedicion.objects.filter(
        establecimiento=configuracion.establecimiento,
        activo=True
    ).first()

    if not punto_expedicion:
        raise ValidationError("No hay punto de expedición activo configurado")

    # Obtener datos del titular
    titular = reserva.titular
    if not titular:
        raise ValidationError("La reserva no tiene titular asignado")

    # Determinar tipo de documento
    if hasattr(titular, 'ci_numero') and titular.ci_numero:
        cliente_tipo_documento = 'CI'
        cliente_numero_documento = titular.ci_numero
    else:
        cliente_tipo_documento = 'Otro'
        cliente_numero_documento = 'S/N'

    # Crear la factura
    factura = FacturaElectronica.objects.create(
        empresa=configuracion.empresa,
        establecimiento=configuracion.establecimiento,
        punto_expedicion=punto_expedicion,
        timbrado=configuracion.timbrado,
        tipo_impuesto=configuracion.tipo_impuesto,
        subtipo_impuesto=subtipo_impuesto,
        reserva=reserva,
        fecha_emision=timezone.now(),
        es_configuracion=False,

        # Datos del cliente
        cliente_tipo_documento=cliente_tipo_documento,
        cliente_numero_documento=cliente_numero_documento,
        cliente_nombre=f"{titular.nombre} {titular.apellido}",
        cliente_direccion=getattr(titular, 'direccion', ''),
        cliente_telefono=getattr(titular, 'telefono', ''),
        cliente_email=getattr(titular, 'correo', ''),

        # Condiciones
        condicion_venta='contado',
        moneda=reserva.paquete.moneda,
    )

    # El número de factura se genera automáticamente en el save()

    # Crear detalles de la factura
    item_numero = 1

    # Detalle principal: Paquete turístico
    paquete = reserva.paquete
    cantidad_pasajeros = reserva.cantidad_pasajeros or 1
    precio_unitario = reserva.precio_unitario or Decimal('0')
    subtotal_paquete = cantidad_pasajeros * precio_unitario

    # Calcular según el tipo de IVA
    porcentaje_iva = subtipo_impuesto.porcentaje or Decimal('10')

    if porcentaje_iva == Decimal('0'):
        # Exenta
        monto_exenta = subtotal_paquete
        monto_gravada_5 = Decimal('0')
        monto_gravada_10 = Decimal('0')
    elif porcentaje_iva == Decimal('5'):
        monto_exenta = Decimal('0')
        monto_gravada_5 = subtotal_paquete
        monto_gravada_10 = Decimal('0')
    else:  # 10%
        monto_exenta = Decimal('0')
        monto_gravada_5 = Decimal('0')
        monto_gravada_10 = subtotal_paquete

    DetalleFactura.objects.create(
        factura=factura,
        numero_item=item_numero,
        descripcion=f"Paquete Turístico: {paquete.nombre}",
        cantidad=cantidad_pasajeros,
        precio_unitario=precio_unitario,
        monto_exenta=monto_exenta,
        monto_gravada_5=monto_gravada_5,
        monto_gravada_10=monto_gravada_10,
        subtotal=subtotal_paquete
    )
    item_numero += 1

    # Agregar servicios adicionales si los hay
    for servicio_adicional in reserva.servicios_adicionales.all():
        servicio = servicio_adicional.servicio
        precio_servicio = servicio_adicional.precio or Decimal('0')

        if porcentaje_iva == Decimal('0'):
            monto_exenta = precio_servicio
            monto_gravada_5 = Decimal('0')
            monto_gravada_10 = Decimal('0')
        elif porcentaje_iva == Decimal('5'):
            monto_exenta = Decimal('0')
            monto_gravada_5 = precio_servicio
            monto_gravada_10 = Decimal('0')
        else:
            monto_exenta = Decimal('0')
            monto_gravada_5 = Decimal('0')
            monto_gravada_10 = precio_servicio

        DetalleFactura.objects.create(
            factura=factura,
            numero_item=item_numero,
            descripcion=f"Servicio Adicional: {servicio.nombre}",
            cantidad=1,
            precio_unitario=precio_servicio,
            monto_exenta=monto_exenta,
            monto_gravada_5=monto_gravada_5,
            monto_gravada_10=monto_gravada_10,
            subtotal=precio_servicio
        )
        item_numero += 1

    # Calcular totales de la factura
    factura.calcular_totales()

    return factura


# ---------- Nuevas funciones para facturación dual ----------
@transaction.atomic
def generar_factura_global(
    reserva,
    subtipo_impuesto_id=None,
    cliente_facturacion_id=None,
    tercero_nombre=None,
    tercero_tipo_documento=None,
    tercero_numero_documento=None,
    tercero_direccion=None,
    tercero_telefono=None,
    tercero_email=None
):
    """
    Genera una factura global para toda la reserva.

    Args:
        reserva: Instancia de Reserva
        subtipo_impuesto_id: ID del subtipo de impuesto a aplicar (ej: IVA 10%)
        cliente_facturacion_id: ID de ClienteFacturacion existente (tercero)
        tercero_nombre: Nombre del tercero (si se crea on-the-fly)
        tercero_tipo_documento: Tipo de documento del tercero
        tercero_numero_documento: Número de documento del tercero
        tercero_direccion: Dirección del tercero (opcional)
        tercero_telefono: Teléfono del tercero (opcional)
        tercero_email: Email del tercero (opcional)

    Returns:
        FacturaElectronica: La factura generada

    Raises:
        ValidationError: Si la reserva no cumple las condiciones
    """
    # Validar que se puede facturar
    validar_factura_global(reserva)

    # Obtener configuración de facturación
    configuracion = FacturaElectronica.objects.filter(
        es_configuracion=True,
        activo=True
    ).first()

    if not configuracion:
        raise ValidationError("No existe configuración de facturación en el sistema")

    # Determinar subtipo de impuesto
    if subtipo_impuesto_id:
        subtipo_impuesto = SubtipoImpuesto.objects.get(id=subtipo_impuesto_id)
    else:
        subtipo_impuesto = configuracion.subtipo_impuesto

    if not subtipo_impuesto:
        raise ValidationError("Debe especificar un subtipo de impuesto")

    # Obtener punto de expedición activo
    punto_expedicion = PuntoExpedicion.objects.filter(
        establecimiento=configuracion.establecimiento,
        activo=True
    ).first()

    if not punto_expedicion:
        raise ValidationError("No hay punto de expedición activo configurado")

    # --- 🔹 Determinar cliente de facturación (tercero o titular) ---
    cliente_facturacion = None
    titular = reserva.titular
    if not titular:
        raise ValidationError("La reserva no tiene titular asignado")

    # Prioridad 1: Intentar obtener/crear cliente de facturación (tercero completo)
    if cliente_facturacion_id or (tercero_nombre and tercero_tipo_documento and tercero_numero_documento):
        cliente_facturacion = obtener_o_crear_cliente_facturacion(
            cliente_facturacion_id=cliente_facturacion_id,
            tercero_nombre=tercero_nombre,
            tercero_tipo_documento=tercero_tipo_documento,
            tercero_numero_documento=tercero_numero_documento,
            tercero_direccion=tercero_direccion,
            tercero_telefono=tercero_telefono,
            tercero_email=tercero_email,
            persona=None  # No vinculamos a persona si es tercero explícito
        )

    # Prioridad 2: Si SOLO se cambió el documento (tipo y/o número), crear ClienteFacturacion con datos del titular
    elif tercero_tipo_documento or tercero_numero_documento:
        # El usuario quiere usar el titular pero con documento diferente
        # Obtener datos del titular
        persona = titular

        # Determinar tipo de persona y extraer datos base
        if hasattr(persona, 'personajuridica'):
            nombre_base = persona.razon_social
            tipo_doc_base = persona.tipo_documento
            num_doc_base = getattr(persona, 'ruc', getattr(persona, 'documento', 'S/N'))
        else:
            nombre_base = f"{getattr(persona, 'nombre', '')} {getattr(persona, 'apellido', '')}".strip()
            tipo_doc_base = persona.tipo_documento
            num_doc_base = getattr(persona, 'documento', getattr(persona, 'ci_numero', 'S/N'))

        # Usar documento override si se proporciona, sino usar el original
        tipo_doc_final = tercero_tipo_documento if tercero_tipo_documento else tipo_doc_base
        num_doc_final = tercero_numero_documento if tercero_numero_documento else num_doc_base

        # Crear/buscar ClienteFacturacion con el documento modificado pero mismo nombre
        cliente_facturacion = obtener_o_crear_cliente_facturacion(
            cliente_facturacion_id=None,
            tercero_nombre=nombre_base,
            tercero_tipo_documento=tipo_doc_final,
            tercero_numero_documento=num_doc_final,
            tercero_direccion=getattr(persona, 'direccion', ''),
            tercero_telefono=getattr(persona, 'telefono', ''),
            tercero_email=getattr(persona, 'correo', getattr(persona, 'email', '')),
            persona=titular  # Vinculamos a la persona original
        )

    # Si hay cliente de facturación (tercero o titular con documento modificado), usar sus datos
    if cliente_facturacion:
        cliente_nombre = cliente_facturacion.nombre
        cliente_tipo_documento = cliente_facturacion.tipo_documento.nombre
        cliente_numero_documento = cliente_facturacion.numero_documento
        cliente_direccion = cliente_facturacion.direccion or ''
        cliente_telefono = cliente_facturacion.telefono or ''
        cliente_email = cliente_facturacion.email or ''
    else:
        # Prioridad 3: Usar datos del titular de la reserva sin modificaciones
        persona = titular
        # Determinar tipo de persona y documento
        if hasattr(persona, 'personajuridica'):
            # Persona jurídica
            cliente_nombre = persona.razon_social
            cliente_tipo_documento = persona.tipo_documento.nombre
            cliente_numero_documento = getattr(persona, 'ruc', getattr(persona, 'documento', 'S/N'))
        else:
            # Persona física
            cliente_nombre = f"{getattr(persona, 'nombre', '')} {getattr(persona, 'apellido', '')}".strip()
            cliente_tipo_documento = persona.tipo_documento.nombre
            cliente_numero_documento = getattr(persona, 'documento', getattr(persona, 'ci_numero', 'S/N'))

        cliente_direccion = getattr(persona, 'direccion', '')
        cliente_telefono = getattr(persona, 'telefono', '')
        cliente_email = getattr(persona, 'correo', getattr(persona, 'email', ''))

    # --- Determinar condición de venta y calcular fecha de vencimiento ---
    condicion_venta = reserva.condicion_pago or 'contado'
    fecha_vencimiento_calculada = None

    if condicion_venta == 'credito':
        # Si es crédito, calcular fecha de vencimiento: fecha_salida - 15 días
        if not reserva.salida or not reserva.salida.fecha_salida:
            raise ValidationError(
                "No se puede generar factura a crédito sin fecha de salida definida"
            )

        from datetime import timedelta
        fecha_vencimiento_calculada = reserva.salida.fecha_salida - timedelta(days=15)

        # Validar que la fecha de vencimiento no sea en el pasado
        if fecha_vencimiento_calculada < timezone.now().date():
            raise ValidationError(
                f"La fecha de vencimiento calculada ({fecha_vencimiento_calculada}) ya pasó. "
                f"La salida es el {reserva.salida.fecha_salida} y el vencimiento debe ser 15 días antes."
            )

    # --- Crear factura ---
    factura = FacturaElectronica.objects.create(
        empresa=configuracion.empresa,
        establecimiento=configuracion.establecimiento,
        punto_expedicion=punto_expedicion,
        timbrado=configuracion.timbrado,
        tipo_impuesto=configuracion.tipo_impuesto,
        subtipo_impuesto=subtipo_impuesto,
        reserva=reserva,
        tipo_facturacion='total',
        pasajero=None,
        cliente_facturacion=cliente_facturacion,  # NUEVO: Vincular cliente de facturación
        fecha_emision=timezone.now(),
        es_configuracion=False,

        cliente_tipo_documento=cliente_tipo_documento,
        cliente_numero_documento=cliente_numero_documento,
        cliente_nombre=cliente_nombre,
        cliente_direccion=cliente_direccion,
        cliente_telefono=cliente_telefono,
        cliente_email=cliente_email,

        condicion_venta=condicion_venta,  # Usar condición de pago de la reserva
        fecha_vencimiento=fecha_vencimiento_calculada,  # Solo si es crédito (fecha_salida - 15 días)
        moneda=reserva.paquete.moneda,
    )


    # Crear detalles de la factura
    item_numero = 1

    # Detalle principal: Paquete turístico
    paquete = reserva.paquete
    cantidad_pasajeros = reserva.cantidad_pasajeros or 1
    precio_unitario = reserva.precio_unitario or Decimal('0')
    subtotal_paquete = cantidad_pasajeros * precio_unitario

    # Calcular según el tipo de IVA
    porcentaje_iva = subtipo_impuesto.porcentaje or Decimal('10')

    if porcentaje_iva == Decimal('0'):
        monto_exenta = subtotal_paquete
        monto_gravada_5 = Decimal('0')
        monto_gravada_10 = Decimal('0')
    elif porcentaje_iva == Decimal('5'):
        monto_exenta = Decimal('0')
        monto_gravada_5 = subtotal_paquete
        monto_gravada_10 = Decimal('0')
    else:  # 10%
        monto_exenta = Decimal('0')
        monto_gravada_5 = Decimal('0')
        monto_gravada_10 = subtotal_paquete

    DetalleFactura.objects.create(
        factura=factura,
        numero_item=item_numero,
        descripcion=f"Paquete Turístico: {paquete.nombre}",
        cantidad=cantidad_pasajeros,
        precio_unitario=precio_unitario,
        monto_exenta=monto_exenta,
        monto_gravada_5=monto_gravada_5,
        monto_gravada_10=monto_gravada_10,
        subtotal=subtotal_paquete
    )
    item_numero += 1

    # Agregar servicios adicionales si los hay
    for servicio_adicional in reserva.servicios_adicionales.filter(activo=True):
        subtotal_servicio = servicio_adicional.subtotal

        if porcentaje_iva == Decimal('0'):
            monto_exenta = subtotal_servicio
            monto_gravada_5 = Decimal('0')
            monto_gravada_10 = Decimal('0')
        elif porcentaje_iva == Decimal('5'):
            monto_exenta = Decimal('0')
            monto_gravada_5 = subtotal_servicio
            monto_gravada_10 = Decimal('0')
        else:
            monto_exenta = Decimal('0')
            monto_gravada_5 = Decimal('0')
            monto_gravada_10 = subtotal_servicio

        DetalleFactura.objects.create(
            factura=factura,
            numero_item=item_numero,
            descripcion=f"Servicio Adicional: {servicio_adicional.servicio.nombre}",
            cantidad=servicio_adicional.cantidad,
            precio_unitario=servicio_adicional.precio_unitario,
            monto_exenta=monto_exenta,
            monto_gravada_5=monto_gravada_5,
            monto_gravada_10=monto_gravada_10,
            subtotal=subtotal_servicio
        )
        item_numero += 1

    # Calcular totales de la factura
    factura.calcular_totales()

    return factura

@transaction.atomic
def generar_factura_individual(
    reserva,
    pasajero,
    subtipo_impuesto_id=None,
    cliente_facturacion_id=None,
    tercero_nombre=None,
    tercero_tipo_documento=None,
    tercero_numero_documento=None,
    tercero_direccion=None,
    tercero_telefono=None,
    tercero_email=None
):
    """
    Genera una factura electrónica para un pasajero específico dentro de una reserva.
    La factura se emite a nombre del pasajero.persona o de un tercero si se especifica.

    Args:
        reserva: Instancia de Reserva
        pasajero: Instancia de Pasajero
        subtipo_impuesto_id: ID del subtipo de impuesto a aplicar
        cliente_facturacion_id: ID de ClienteFacturacion existente (tercero)
        tercero_nombre: Nombre del tercero (si se crea on-the-fly)
        tercero_tipo_documento: Tipo de documento del tercero
        tercero_numero_documento: Número de documento del tercero
        tercero_direccion: Dirección del tercero (opcional)
        tercero_telefono: Teléfono del tercero (opcional)
        tercero_email: Email del tercero (opcional)

    Returns:
        FacturaElectronica: La factura generada
    """
    from decimal import Decimal
    from django.utils import timezone
    from django.core.exceptions import ValidationError

    validar_factura_individual(reserva, pasajero)

    configuracion = FacturaElectronica.objects.filter(
        es_configuracion=True,
        activo=True
    ).first()

    if not configuracion:
        raise ValidationError("No existe configuración de facturación en el sistema")

    # Determinar subtipo de impuesto
    if subtipo_impuesto_id:
        subtipo_impuesto = SubtipoImpuesto.objects.get(id=subtipo_impuesto_id)
    else:
        subtipo_impuesto = configuracion.subtipo_impuesto

    if not subtipo_impuesto:
        raise ValidationError("Debe especificar un subtipo de impuesto")

    punto_expedicion = PuntoExpedicion.objects.filter(
        establecimiento=configuracion.establecimiento,
        activo=True
    ).first()

    if not punto_expedicion:
        raise ValidationError("No hay punto de expedición activo configurado")

    # --- 🔹 Determinar cliente de facturación (tercero o pasajero) ---
    cliente_facturacion = None
    persona = pasajero.persona

    # Prioridad 1: Intentar obtener/crear cliente de facturación (tercero completo)
    if cliente_facturacion_id or (tercero_nombre and tercero_tipo_documento and tercero_numero_documento):
        cliente_facturacion = obtener_o_crear_cliente_facturacion(
            cliente_facturacion_id=cliente_facturacion_id,
            tercero_nombre=tercero_nombre,
            tercero_tipo_documento=tercero_tipo_documento,
            tercero_numero_documento=tercero_numero_documento,
            tercero_direccion=tercero_direccion,
            tercero_telefono=tercero_telefono,
            tercero_email=tercero_email,
            persona=None  # No vinculamos a persona si es tercero explícito
        )

    # Prioridad 2: Si SOLO se cambió el documento (tipo y/o número), crear ClienteFacturacion con datos del pasajero
    elif tercero_tipo_documento or tercero_numero_documento:
        # El usuario quiere usar el pasajero pero con documento diferente
        # Determinar tipo de persona y extraer datos base
        if hasattr(persona, 'personajuridica'):
            nombre_base = persona.razon_social
            tipo_doc_base = persona.tipo_documento
            num_doc_base = persona.documento
        else:
            nombre_base = f"{getattr(persona, 'nombre', '')} {getattr(persona, 'apellido', '')}".strip()
            tipo_doc_base = persona.tipo_documento
            num_doc_base = persona.documento

        # Usar documento override si se proporciona, sino usar el original
        tipo_doc_final = tercero_tipo_documento if tercero_tipo_documento else tipo_doc_base
        num_doc_final = tercero_numero_documento if tercero_numero_documento else num_doc_base

        # Crear/buscar ClienteFacturacion con el documento modificado pero mismo nombre
        cliente_facturacion = obtener_o_crear_cliente_facturacion(
            cliente_facturacion_id=None,
            tercero_nombre=nombre_base,
            tercero_tipo_documento=tipo_doc_final,
            tercero_numero_documento=num_doc_final,
            tercero_direccion=getattr(persona, 'direccion', ''),
            tercero_telefono=getattr(persona, 'telefono', ''),
            tercero_email=getattr(persona, 'email', ''),
            persona=persona  # Vinculamos a la persona original
        )

    # Si hay cliente de facturación (tercero o pasajero con documento modificado), usar sus datos
    if cliente_facturacion:
        cliente_nombre = cliente_facturacion.nombre
        cliente_tipo_documento = cliente_facturacion.tipo_documento.nombre
        cliente_numero_documento = cliente_facturacion.numero_documento
        cliente_direccion = cliente_facturacion.direccion or ''
        cliente_telefono = cliente_facturacion.telefono or ''
        cliente_email = cliente_facturacion.email or ''
    else:
        # Prioridad 3: Usar datos del pasajero sin modificaciones
        if hasattr(persona, 'personajuridica'):
            # Persona jurídica
            cliente_nombre = persona.razon_social
            cliente_tipo_documento = persona.tipo_documento.nombre
            cliente_numero_documento = persona.documento
        else:
            # Persona física
            cliente_nombre = f"{getattr(persona, 'nombre', '')} {getattr(persona, 'apellido', '')}".strip()
            cliente_tipo_documento = persona.tipo_documento.nombre
            cliente_numero_documento = persona.documento

        cliente_direccion = getattr(persona, 'direccion', '')
        cliente_telefono = getattr(persona, 'telefono', '')
        cliente_email = getattr(persona, 'email', '')

    # --- Crear factura ---
    factura = FacturaElectronica.objects.create(
        empresa=configuracion.empresa,
        establecimiento=configuracion.establecimiento,
        punto_expedicion=punto_expedicion,
        timbrado=configuracion.timbrado,
        tipo_impuesto=configuracion.tipo_impuesto,
        subtipo_impuesto=subtipo_impuesto,
        reserva=reserva,
        pasajero=pasajero,
        cliente_facturacion=cliente_facturacion,  # NUEVO: Vincular cliente de facturación
        tipo_facturacion='por_pasajero',
        fecha_emision=timezone.now(),
        es_configuracion=False,

        cliente_tipo_documento=cliente_tipo_documento,
        cliente_numero_documento=cliente_numero_documento,
        cliente_nombre=cliente_nombre,
        cliente_direccion=cliente_direccion,
        cliente_telefono=cliente_telefono,
        cliente_email=cliente_email,

        condicion_venta='contado',
        moneda=reserva.paquete.moneda,
    )

    # --- 🔹 Detalle principal ---
    paquete = reserva.paquete
    precio_unitario = reserva.precio_unitario or Decimal('0')
    subtotal = precio_unitario
    porcentaje_iva = subtipo_impuesto.porcentaje or Decimal('10')

    if porcentaje_iva == Decimal('0'):
        monto_exenta = subtotal
        monto_gravada_5 = Decimal('0')
        monto_gravada_10 = Decimal('0')
    elif porcentaje_iva == Decimal('5'):
        monto_exenta = Decimal('0')
        monto_gravada_5 = subtotal
        monto_gravada_10 = Decimal('0')
    else:
        monto_exenta = Decimal('0')
        monto_gravada_5 = Decimal('0')
        monto_gravada_10 = subtotal

    DetalleFactura.objects.create(
        factura=factura,
        numero_item=1,
        descripcion=f"Paquete Turístico: {paquete.nombre}",
        cantidad=1,  # ✅ Solo un pasajero
        precio_unitario=precio_unitario,
        monto_exenta=monto_exenta,
        monto_gravada_5=monto_gravada_5,
        monto_gravada_10=monto_gravada_10,
        subtotal=subtotal
    )

    factura.calcular_totales()
    return factura


@transaction.atomic
def generar_todas_facturas_pasajeros(reserva, subtipo_impuesto_id=None):
    """
    Genera facturas individuales para todos los pasajeros que cumplan las condiciones.

    Args:
        reserva: Instancia de Reserva
        subtipo_impuesto_id: ID del subtipo de impuesto a aplicar (ej: IVA 10%)

    Returns:
        dict: Diccionario con facturas generadas y pasajeros omitidos
            {
                'facturas_generadas': [list of dict],
                'pasajeros_omitidos': [list of dict]
            }

    Raises:
        ValidationError: Si la reserva no está configurada para facturación individual
    """
    # Verificar modalidad
    if reserva.modalidad_facturacion is None:
        raise ValidationError(
            "La modalidad de facturación no ha sido definida. "
            "Debe confirmar la reserva y elegir la modalidad primero."
        )

    if reserva.modalidad_facturacion != 'individual':
        raise ValidationError(
            "Esta reserva no está configurada para facturación individual."
        )

    facturas_generadas = []
    pasajeros_omitidos = []

    # Iterar sobre todos los pasajeros
    for pasajero in reserva.pasajeros.all():
        try:
            # Intentar generar factura
            factura = generar_factura_individual(pasajero, subtipo_impuesto_id)
            facturas_generadas.append({
                'pasajero_id': pasajero.id,
                'pasajero_nombre': f"{pasajero.persona.nombre} {pasajero.persona.apellido}",
                'factura_numero': factura.numero_factura,
                'monto': str(factura.total_general)
            })
        except ValidationError as e:
            # Si falla, agregar a omitidos con la razón
            pasajeros_omitidos.append({
                'pasajero_id': pasajero.id,
                'pasajero_nombre': f"{pasajero.persona.nombre} {pasajero.persona.apellido}" if not pasajero.por_asignar else f"PENDIENTE_{pasajero.id}",
                'razon': str(e)
            })

    return {
        'facturas_generadas': facturas_generadas,
        'pasajeros_omitidos': pasajeros_omitidos
    }


# ========================================
# NOTAS DE CRÉDITO
# ========================================

class NotaCreditoElectronica(models.Model):
    """
    Nota de crédito que anula total o parcialmente una factura electrónica.
    Sigue las normativas de la SET de Paraguay.
    """

    TIPO_NOTA_CHOICES = (
        ('total', 'Anulación Total'),
        ('parcial', 'Anulación Parcial'),
    )

    # Códigos oficiales SIFEN - Campo E401 (iMotEmi)
    MOTIVO_CHOICES = (
        ('1', 'Devolución y Ajuste de precios'),
        ('2', 'Devolución'),
        ('3', 'Descuento'),
        ('4', 'Bonificación'),
        ('5', 'Crédito incobrable'),
        ('6', 'Recupero de costo'),
        ('7', 'Recupero de gasto'),
        ('8', 'Ajuste de precio'),
    )

    # Relación con factura original (PROTEGIDA - no se puede borrar factura con NC)
    factura_afectada = models.ForeignKey(
        'FacturaElectronica',
        on_delete=models.PROTECT,
        related_name='notas_credito',
        help_text="Factura que se está anulando (total o parcialmente)"
    )

    # Datos de la empresa (heredados de factura, no se puede cambiar punto de expedición)
    empresa = models.ForeignKey('Empresa', on_delete=models.PROTECT)
    establecimiento = models.ForeignKey('Establecimiento', on_delete=models.PROTECT)
    punto_expedicion = models.ForeignKey('PuntoExpedicion', on_delete=models.PROTECT)
    timbrado = models.ForeignKey('Timbrado', on_delete=models.PROTECT)

    # Número de nota de crédito (formato: XXX-XXX-XXXXXXX) - Correlativo INDEPENDIENTE de facturas
    numero_nota_credito = models.CharField(
        max_length=15,
        editable=False,
        help_text="Número correlativo de la nota de crédito (formato: XXX-XXX-XXXXXXX)"
    )

    # Información general
    fecha_emision = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de emisión de la nota de crédito"
    )

    tipo_nota = models.CharField(
        max_length=20,
        choices=TIPO_NOTA_CHOICES,
        help_text="Tipo de anulación: total (100% de la factura) o parcial (monto menor)"
    )

    motivo = models.CharField(
        max_length=1,
        choices=MOTIVO_CHOICES,
        verbose_name='Motivo de emisión',
        help_text="Código según campo E401 (iMotEmi) de SIFEN. Este valor se enviará directamente en el XML"
    )

    observaciones = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones adicionales sobre la nota de crédito"
    )

    # Datos del cliente (copiados de factura afectada - garantiza trazabilidad)
    cliente_tipo_documento = models.CharField(max_length=50)
    cliente_numero_documento = models.CharField(max_length=20)
    cliente_nombre = models.CharField(max_length=200)
    cliente_direccion = models.CharField(max_length=200, blank=True)
    cliente_telefono = models.CharField(max_length=20, blank=True)
    cliente_email = models.EmailField(blank=True)

    # Impuesto (igual que factura afectada)
    tipo_impuesto = models.ForeignKey('TipoImpuesto', on_delete=models.PROTECT)
    subtipo_impuesto = models.ForeignKey('SubtipoImpuesto', on_delete=models.PROTECT)

    # Moneda (igual que factura afectada)
    moneda = models.ForeignKey('moneda.Moneda', on_delete=models.PROTECT)

    # Totales (pueden ser menores que factura si es parcial)
    total_exenta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total de operaciones exentas acreditadas"
    )
    total_gravada_5 = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total gravado IVA 5% acreditado"
    )
    total_gravada_10 = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total gravado IVA 10% acreditado"
    )
    total_iva_5 = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="IVA 5% acreditado"
    )
    total_iva_10 = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="IVA 10% acreditado"
    )
    total_iva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total IVA acreditado"
    )
    total_general = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total general acreditado (monto que se resta de la factura)"
    )

    # PDF generado
    pdf_generado = models.FileField(
        upload_to='facturas/notas_credito/pdf/',
        blank=True,
        null=True,
        help_text="PDF de la nota de crédito"
    )

    # Metadata
    activo = models.BooleanField(
        default=True,
        help_text="Indica si la nota de crédito está activa"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nota_credito_electronica'
        unique_together = ('establecimiento', 'punto_expedicion', 'numero_nota_credito')
        ordering = ['-fecha_emision']
        verbose_name = 'Nota de Crédito Electrónica'
        verbose_name_plural = 'Notas de Crédito Electrónicas'

    def __str__(self):
        return f"NC {self.numero_nota_credito} - Afecta: {self.factura_afectada.numero_factura}"

    def save(self, *args, **kwargs):
        """Genera número de nota de crédito si no existe"""
        if not self.pk and not self.numero_nota_credito:
            self.numero_nota_credito = self.generar_numero_nota_credito()
        super().save(*args, **kwargs)

    def generar_numero_nota_credito(self):
        """
        Genera número correlativo INDEPENDIENTE de facturas: XXX-XXX-XXXXXXX
        Ej: 001-001-0000001 (primera NC del punto de expedición)
        """
        ultima_nota = NotaCreditoElectronica.objects.filter(
            establecimiento=self.establecimiento,
            punto_expedicion=self.punto_expedicion
        ).aggregate(max_num=Max('numero_nota_credito'))['max_num']

        if ultima_nota:
            try:
                # Extraer el número correlativo (último segmento)
                ultimo_numero = int(ultima_nota.split('-')[2])
                nuevo_numero = ultimo_numero + 1
            except:
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        # Formato: XXX-XXX-XXXXXXX
        correlativo_str = str(nuevo_numero).zfill(7)
        return f"{self.establecimiento.codigo}-{self.punto_expedicion.codigo}-{correlativo_str}"

    def calcular_totales(self):
        """Calcula los totales sumando los detalles de la nota de crédito"""
        from django.db.models import Sum

        totales = self.detalles.aggregate(
            exenta=Sum('monto_exenta'),
            gravada_5=Sum('monto_gravada_5'),
            gravada_10=Sum('monto_gravada_10')
        )

        self.total_exenta = totales['exenta'] or Decimal('0')
        self.total_gravada_5 = totales['gravada_5'] or Decimal('0')
        self.total_gravada_10 = totales['gravada_10'] or Decimal('0')

        # Calcular IVA (extraído del monto gravado)
        self.total_iva_5 = (self.total_gravada_5 * Decimal('5')) / Decimal('105')
        self.total_iva_10 = (self.total_gravada_10 * Decimal('10')) / Decimal('110')
        self.total_iva = self.total_iva_5 + self.total_iva_10

        # Total general
        self.total_general = self.total_exenta + self.total_gravada_5 + self.total_gravada_10

    @property
    def saldo_factura_restante(self):
        """
        Calcula el saldo que queda de la factura afectada después de esta nota de crédito.
        """
        return self.factura_afectada.saldo_neto

    def generar_pdf(self):
        """
        Genera PDF de la nota de crédito.
        Similar a la factura pero con título "NOTA DE CRÉDITO ELECTRÓNICA"
        y referenciando la factura afectada.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from django.core.files.base import ContentFile
        from django.conf import settings
        import io
        import os

        # Crear buffer para el PDF
        buffer = io.BytesIO()

        # Crear documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        elements = []
        styles = getSampleStyleSheet()

        # Estilos personalizados
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT
        )

        # ===== ENCABEZADO =====
        logo_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'logo_group_tours.png')

        if os.path.exists(logo_path):
            logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
            empresa_info = Paragraph(f'''
                <b>{self.empresa.nombre}</b><br/>
                {self.empresa.direccion or ''}<br/>
                Teléfono: {self.empresa.telefono or 'N/A'}<br/>
                {self.empresa.correo or ''}
            ''', small_style)

            datos_fiscales = Paragraph(f'''
                <b>RUC:</b> {self.empresa.ruc}<br/>
                <b>Timbrado N°:</b> {self.timbrado.numero}<br/>
                <b>Fecha Inicio Vigencia:</b> {self.timbrado.inicio_vigencia.strftime('%d/%m/%Y')}<br/>
                <br/>
                <b><font color="red">NOTA DE CRÉDITO ELECTRÓNICA</font></b><br/>
                <b>{self.numero_nota_credito}</b><br/>
                <br/>
                <b>Factura Afectada:</b><br/>
                {self.factura_afectada.numero_factura}
            ''', small_style)

            header_table = Table([[logo, empresa_info, datos_fiscales]],
                                colWidths=[1.5*inch, 3.0*inch, 2.0*inch])
        else:
            empresa_info = Paragraph(f'''
                <b>{self.empresa.nombre}</b><br/>
                {self.empresa.direccion or ''}<br/>
                RUC: {self.empresa.ruc}
            ''', small_style)

            datos_fiscales = Paragraph(f'''
                <b><font color="red">NOTA DE CRÉDITO ELECTRÓNICA</font></b><br/>
                <b>{self.numero_nota_credito}</b><br/>
                <br/>
                <b>Factura Afectada:</b> {self.factura_afectada.numero_factura}
            ''', small_style)

            header_table = Table([[empresa_info, datos_fiscales]],
                                colWidths=[4.5*inch, 2.0*inch])

        header_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 0.15*inch))

        # ===== DATOS DE LA NOTA DE CRÉDITO =====
        transaccion_data = [
            [
                Paragraph(f'<b>Fecha de Emisión:</b> {self.fecha_emision.strftime("%d-%m-%Y %H:%M:%S")}', small_style),
                Paragraph(f'<b>Cliente:</b> {self.cliente_nombre}', small_style)
            ],
            [
                Paragraph(f'<b>Tipo:</b> {self.get_tipo_nota_display()}', small_style),
                Paragraph(f'<b>Documento:</b> {self.cliente_numero_documento}', small_style)
            ],
            [
                Paragraph(f'<b>Motivo:</b> {self.get_motivo_display()}', small_style),
                Paragraph(f'<b>Moneda:</b> {self.moneda.nombre.upper()}', small_style)
            ],
        ]

        if self.observaciones:
            transaccion_data.append([
                Paragraph(f'<b>Observaciones:</b> {self.observaciones[:100]}', small_style),
                Paragraph('', small_style)
            ])

        transaccion_table = Table(transaccion_data, colWidths=[3.25*inch, 3.25*inch])
        transaccion_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        elements.append(transaccion_table)
        elements.append(Spacer(1, 0.15*inch))

        # ===== TABLA DE DETALLES =====
        detalle_header = ['#', 'Descripción', 'Cant.', 'Precio Unit.', 'Exentas', '5%', '10%']
        detalle_data = [detalle_header]

        for detalle in self.detalles.all():
            exenta_val = f"{int(detalle.monto_exenta):,}" if detalle.monto_exenta > 0 else "0"
            iva5_val = f"{int(detalle.monto_gravada_5):,}" if detalle.monto_gravada_5 > 0 else "0"
            iva10_val = f"{int(detalle.monto_gravada_10):,}" if detalle.monto_gravada_10 > 0 else "0"

            detalle_data.append([
                str(detalle.numero_item),
                str(detalle.descripcion)[:40],
                str(int(detalle.cantidad)),
                f"{int(detalle.precio_unitario):,}",
                exenta_val,
                iva5_val,
                iva10_val
            ])

        # Llenar filas vacías
        while len(detalle_data) < 6:
            detalle_data.append(['', '', '', '', '', '', ''])

        detalle_table = Table(detalle_data,
                            colWidths=[0.4*inch, 2.5*inch, 0.6*inch, 0.9*inch, 0.8*inch, 0.7*inch, 0.7*inch])
        detalle_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(detalle_table)
        elements.append(Spacer(1, 0.1*inch))

        # ===== TOTALES =====
        totales_data = [
            ['SUBTOTAL:', '', '', f"{int(self.total_general):,}"],
            ['TOTAL ACREDITADO:', '', '', f"{int(self.total_general):,}"],
            ['LIQUIDACIÓN IVA:', f"(5%) {int(self.total_iva_5):,}", f"(10%) {int(self.total_iva_10):,}", f"{int(self.total_iva):,}"]
        ]

        totales_table = Table(totales_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.0*inch])
        totales_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(totales_table)
        elements.append(Spacer(1, 0.15*inch))

        # ===== PIE DE PÁGINA =====
        footer_text = Paragraph(
            f'''
            <b>NOTA DE CRÉDITO ELECTRÓNICA</b><br/>
            <b>Documento que anula {self.get_tipo_nota_display().lower()} la Factura N° {self.factura_afectada.numero_factura}</b><br/>
            <br/>
            Este documento es una representación gráfica de una Nota de Crédito Electrónica.<br/>
            Saldo restante de la factura: {int(self.saldo_factura_restante):,} {self.moneda.codigo}
            ''',
            small_style
        )
        elements.append(footer_text)

        # Construir PDF
        doc.build(elements)

        # Guardar el PDF
        buffer.seek(0)
        filename = f"nota_credito_{self.numero_nota_credito.replace('-', '_')}.pdf"
        self.pdf_generado.save(filename, ContentFile(buffer.read()), save=True)

        return self.pdf_generado.path


class DetalleNotaCredito(models.Model):
    """
    Detalle de items que se están acreditando (anulando) en una nota de crédito.
    Cada detalle corresponde a un item de la factura afectada.
    """

    nota_credito = models.ForeignKey(
        'NotaCreditoElectronica',
        on_delete=models.CASCADE,
        related_name='detalles',
        help_text="Nota de crédito a la que pertenece este detalle"
    )

    numero_item = models.PositiveIntegerField(
        help_text="Número de línea en la nota de crédito"
    )

    # Descripción del item que se acredita
    descripcion = models.CharField(
        max_length=250,
        help_text="Descripción del producto/servicio que se está acreditando"
    )

    # Cantidades
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cantidad a acreditar"
    )

    precio_unitario = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Precio unitario del item acreditado"
    )

    # Montos según IVA (distribuidos según subtipo_impuesto)
    monto_exenta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Monto exento de IVA acreditado"
    )

    monto_gravada_5 = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Monto gravado IVA 5% acreditado"
    )

    monto_gravada_10 = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Monto gravado IVA 10% acreditado"
    )

    # Subtotal = cantidad * precio_unitario
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Subtotal del item (cantidad * precio_unitario)"
    )

    # Referencia al detalle de factura original (opcional pero recomendado para trazabilidad)
    detalle_factura_afectado = models.ForeignKey(
        'DetalleFactura',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detalles_nota_credito',
        help_text="Detalle de factura que se está acreditando (opcional)"
    )

    class Meta:
        db_table = 'detalle_nota_credito'
        unique_together = ('nota_credito', 'numero_item')
        ordering = ['numero_item']
        verbose_name = 'Detalle de Nota de Crédito'
        verbose_name_plural = 'Detalles de Nota de Crédito'

    def __str__(self):
        return f"NC {self.nota_credito.numero_nota_credito} - Item {self.numero_item}: {self.descripcion}"

    def save(self, *args, **kwargs):
        """Calcula el subtotal automáticamente"""
        self.subtotal = Decimal(str(self.cantidad)) * Decimal(str(self.precio_unitario))
        super().save(*args, **kwargs)


# ========================================
# FUNCIONES PARA NOTAS DE CRÉDITO
# ========================================

def validar_nota_credito(factura_afectada, tipo_nota, detalles_a_acreditar):
    """
    Validaciones exhaustivas antes de generar una nota de crédito.

    Args:
        factura_afectada: Instancia de FacturaElectronica
        tipo_nota: 'total' o 'parcial'
        detalles_a_acreditar: Lista de dict con {'subtotal': Decimal}

    Raises:
        ValidationError: Si no cumple las condiciones
    """
    # 1. La factura debe existir y estar activa
    if not factura_afectada.activo:
        raise ValidationError("La factura está inactiva")

    # 2. No se puede acreditar una factura de configuración
    if factura_afectada.es_configuracion:
        raise ValidationError("No se puede acreditar una factura de configuración")

    # 3. Verificar que no exceda el saldo disponible
    total_acreditado = factura_afectada.total_acreditado
    total_nuevo = sum(Decimal(str(detalle['subtotal'])) for detalle in detalles_a_acreditar)

    saldo_disponible = factura_afectada.total_general - total_acreditado

    if total_acreditado + total_nuevo > factura_afectada.total_general:
        raise ValidationError(
            f"El monto a acreditar ({total_nuevo}) supera el saldo disponible ({saldo_disponible})"
        )

    # 4. Si es nota total, verificar que no haya notas previas
    if tipo_nota == 'total' and factura_afectada.notas_credito.filter(activo=True).exists():
        raise ValidationError(
            "No se puede generar nota de crédito total si ya existen notas parciales. "
            "Use una nota parcial por el saldo restante."
        )

    # 5. Si es nota total, el monto debe ser igual al saldo disponible
    if tipo_nota == 'total' and total_nuevo != saldo_disponible:
        raise ValidationError(
            f"La nota de crédito total debe acreditar el saldo completo ({saldo_disponible})"
        )

    return True


@transaction.atomic
def generar_nota_credito_total(factura_id, motivo, observaciones=''):
    """
    Anula completamente una factura (o su saldo restante si hay NC previas).

    Args:
        factura_id: ID de la factura a acreditar
        motivo: Motivo de la nota de crédito (de MOTIVO_CHOICES)
        observaciones: Texto adicional (opcional)

    Returns:
        NotaCreditoElectronica: La nota de crédito generada

    Raises:
        ValidationError: Si la factura no se puede acreditar
    """
    factura = FacturaElectronica.objects.get(id=factura_id)

    # Validar posibilidad
    puede_nc, mensaje = factura.puede_generar_nota_credito()
    if not puede_nc:
        raise ValidationError(mensaje)

    # Calcular saldo a acreditar (puede ser menor que total si hay NC previas)
    saldo_a_acreditar = factura.saldo_neto

    # Validar
    validar_nota_credito(
        factura_afectada=factura,
        tipo_nota='total',
        detalles_a_acreditar=[{'subtotal': saldo_a_acreditar}]
    )

    # Crear nota de crédito
    nota_credito = NotaCreditoElectronica.objects.create(
        factura_afectada=factura,
        empresa=factura.empresa,
        establecimiento=factura.establecimiento,
        punto_expedicion=factura.punto_expedicion,
        timbrado=factura.timbrado,
        tipo_nota='total',
        motivo=motivo,
        observaciones=observaciones,

        # Copiar datos del cliente
        cliente_tipo_documento=factura.cliente_tipo_documento,
        cliente_numero_documento=factura.cliente_numero_documento,
        cliente_nombre=factura.cliente_nombre,
        cliente_direccion=factura.cliente_direccion,
        cliente_telefono=factura.cliente_telefono,
        cliente_email=factura.cliente_email,

        # Impuestos y moneda
        tipo_impuesto=factura.tipo_impuesto,
        subtipo_impuesto=factura.subtipo_impuesto,
        moneda=factura.moneda,

        # Totales (copiar saldo restante)
        total_exenta=factura.total_exenta,
        total_gravada_5=factura.total_gravada_5,
        total_gravada_10=factura.total_gravada_10,
        total_iva_5=factura.total_iva_5,
        total_iva_10=factura.total_iva_10,
        total_iva=factura.total_iva,
        total_general=saldo_a_acreditar,
    )

    # Copiar todos los detalles de la factura
    for detalle_factura in factura.detalles.all():
        DetalleNotaCredito.objects.create(
            nota_credito=nota_credito,
            numero_item=detalle_factura.numero_item,
            descripcion=detalle_factura.descripcion,
            cantidad=detalle_factura.cantidad,
            precio_unitario=detalle_factura.precio_unitario,
            monto_exenta=detalle_factura.monto_exenta,
            monto_gravada_5=detalle_factura.monto_gravada_5,
            monto_gravada_10=detalle_factura.monto_gravada_10,
            subtotal=detalle_factura.subtotal,
            detalle_factura_afectado=detalle_factura
        )

    # Generar PDF
    try:
        nota_credito.generar_pdf()
    except Exception as e:
        # No fallar si el PDF no se genera
        print(f"Error generando PDF de NC: {e}")

    return nota_credito


@transaction.atomic
def generar_nota_credito_parcial(factura_id, items_a_acreditar, motivo, observaciones=''):
    """
    Anula parcialmente una factura acreditando items específicos.

    Args:
        factura_id: ID de la factura a acreditar
        items_a_acreditar: Lista de dicts con estructura:
            [
                {
                    'descripcion': 'Descripción del item',
                    'cantidad': Decimal('2'),
                    'precio_unitario': Decimal('1000.00'),
                    'detalle_factura_id': 123  # Opcional
                },
                ...
            ]
        motivo: Motivo de la nota de crédito
        observaciones: Texto adicional (opcional)

    Returns:
        NotaCreditoElectronica: La nota de crédito generada

    Raises:
        ValidationError: Si los datos son inválidos
    """
    factura = FacturaElectronica.objects.get(id=factura_id)

    # Validar posibilidad
    puede_nc, mensaje = factura.puede_generar_nota_credito()
    if not puede_nc:
        raise ValidationError(mensaje)

    # Calcular totales de items a acreditar
    detalles_calculados = []
    total_a_acreditar = Decimal('0')

    for item in items_a_acreditar:
        cantidad = Decimal(str(item['cantidad']))
        precio_unitario = Decimal(str(item['precio_unitario']))
        subtotal = cantidad * precio_unitario
        total_a_acreditar += subtotal
        detalles_calculados.append({'subtotal': subtotal})

    # Validar
    validar_nota_credito(
        factura_afectada=factura,
        tipo_nota='parcial',
        detalles_a_acreditar=detalles_calculados
    )

    # Crear nota de crédito
    nota_credito = NotaCreditoElectronica.objects.create(
        factura_afectada=factura,
        empresa=factura.empresa,
        establecimiento=factura.establecimiento,
        punto_expedicion=factura.punto_expedicion,
        timbrado=factura.timbrado,
        tipo_nota='parcial',
        motivo=motivo,
        observaciones=observaciones,

        # Copiar cliente
        cliente_tipo_documento=factura.cliente_tipo_documento,
        cliente_numero_documento=factura.cliente_numero_documento,
        cliente_nombre=factura.cliente_nombre,
        cliente_direccion=factura.cliente_direccion,
        cliente_telefono=factura.cliente_telefono,
        cliente_email=factura.cliente_email,

        # Impuestos
        tipo_impuesto=factura.tipo_impuesto,
        subtipo_impuesto=factura.subtipo_impuesto,
        moneda=factura.moneda,
    )

    # Crear detalles y calcular totales
    porcentaje_iva = nota_credito.subtipo_impuesto.porcentaje or Decimal('10')

    for idx, item in enumerate(items_a_acreditar, 1):
        cantidad = Decimal(str(item['cantidad']))
        precio_unitario = Decimal(str(item['precio_unitario']))
        subtotal = cantidad * precio_unitario

        # Distribuir según IVA
        if porcentaje_iva == Decimal('0'):
            monto_exenta = subtotal
            monto_gravada_5 = Decimal('0')
            monto_gravada_10 = Decimal('0')
        elif porcentaje_iva == Decimal('5'):
            monto_exenta = Decimal('0')
            monto_gravada_5 = subtotal
            monto_gravada_10 = Decimal('0')
        else:  # 10%
            monto_exenta = Decimal('0')
            monto_gravada_5 = Decimal('0')
            monto_gravada_10 = subtotal

        DetalleNotaCredito.objects.create(
            nota_credito=nota_credito,
            numero_item=idx,
            descripcion=item['descripcion'],
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            monto_exenta=monto_exenta,
            monto_gravada_5=monto_gravada_5,
            monto_gravada_10=monto_gravada_10,
            subtotal=subtotal,
            detalle_factura_afectado_id=item.get('detalle_factura_id')
        )

    # Calcular totales de la nota
    nota_credito.calcular_totales()
    nota_credito.save()

    # Generar PDF
    try:
        nota_credito.generar_pdf()
    except Exception as e:
        print(f"Error generando PDF de NC: {e}")

    return nota_credito