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

    # 3. Estado de reserva
    if reserva.estado != 'finalizada':
        raise ValidationError(
            "La reserva debe estar en estado 'finalizada' para emitir factura global."
        )

    # 4. Saldo de la reserva
    if reserva.monto_pagado < reserva.costo_total_estimado:
        saldo_pendiente = reserva.costo_total_estimado - reserva.monto_pagado
        raise ValidationError(
            f"La reserva tiene saldo pendiente de {saldo_pendiente}. "
            f"Debe pagar el total antes de facturar."
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


def validar_factura_individual(pasajero):
    """
    Validaciones exhaustivas para emitir factura individual por pasajero.

    Args:
        pasajero: Instancia de Pasajero

    Raises:
        ValidationError: Si no cumple las condiciones para facturar
    """
    reserva = pasajero.reserva

    # 1. Modalidad de facturación debe estar definida
    if reserva.modalidad_facturacion is None:
        raise ValidationError(
            "La modalidad de facturación no ha sido definida. "
            "Debe confirmar la reserva y elegir la modalidad primero."
        )

    # 2. Modalidad debe ser 'individual'
    if reserva.modalidad_facturacion != 'individual':
        raise ValidationError(
            "Esta reserva está configurada para facturación global. "
            "No se pueden emitir facturas individuales."
        )

    # 3. Estado de reserva
    if reserva.estado not in ['confirmada', 'finalizada']:
        raise ValidationError(
            f"La reserva debe estar confirmada o finalizada. "
            f"Estado actual: {reserva.estado}"
        )

    # 4. Pasajero con datos reales (NO temporal)
    if pasajero.por_asignar:
        raise ValidationError(
            "No se puede facturar. El pasajero está marcado como 'por asignar'. "
            "Debe asignar un pasajero real con datos completos antes de emitir la factura."
        )

    # 5. Saldo del pasajero
    if not pasajero.esta_totalmente_pagado:
        raise ValidationError(
            f"El pasajero {pasajero.persona.nombre} {pasajero.persona.apellido} "
            f"tiene saldo pendiente de {pasajero.saldo_pendiente}. "
            f"Debe pagar el total antes de facturar."
        )

    # 6. No tener factura individual previa
    if pasajero.facturas.filter(tipo_facturacion='por_pasajero', activo=True).exists():
        raise ValidationError(
            f"El pasajero ya tiene una factura individual generada."
        )

    # 7. No existir factura global
    if reserva.facturas.filter(tipo_facturacion='total', activo=True).exists():
        raise ValidationError(
            "Ya existe una factura global para esta reserva. "
            "No se pueden emitir facturas individuales."
        )


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
def generar_factura_global(reserva, subtipo_impuesto_id=None):
    """
    Genera una factura global para toda la reserva.

    Args:
        reserva: Instancia de Reserva
        subtipo_impuesto_id: ID del subtipo de impuesto a aplicar (ej: IVA 10%)

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
        tipo_facturacion='total',  # NUEVO
        pasajero=None,  # NUEVO
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
def generar_factura_individual(pasajero, subtipo_impuesto_id=None):
    """
    Genera una factura individual para un pasajero específico.

    Args:
        pasajero: Instancia de Pasajero
        subtipo_impuesto_id: ID del subtipo de impuesto a aplicar (ej: IVA 10%)

    Returns:
        FacturaElectronica: La factura generada

    Raises:
        ValidationError: Si el pasajero no cumple las condiciones
    """
    # Validar que se puede facturar
    validar_factura_individual(pasajero)

    reserva = pasajero.reserva

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

    # Obtener datos del pasajero
    persona = pasajero.persona
    if not persona:
        raise ValidationError("El pasajero no tiene persona asignada")

    # Determinar tipo de documento
    if hasattr(persona, 'ci_numero') and persona.ci_numero:
        cliente_tipo_documento = 'CI'
        cliente_numero_documento = persona.ci_numero
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
        tipo_facturacion='por_pasajero',  # NUEVO
        pasajero=pasajero,  # NUEVO
        fecha_emision=timezone.now(),
        es_configuracion=False,

        # Datos del cliente (el pasajero)
        cliente_tipo_documento=cliente_tipo_documento,
        cliente_numero_documento=cliente_numero_documento,
        cliente_nombre=f"{persona.nombre} {persona.apellido}",
        cliente_direccion=getattr(persona, 'direccion', ''),
        cliente_telefono=getattr(persona, 'telefono', ''),
        cliente_email=getattr(persona, 'correo', ''),

        # Condiciones
        condicion_venta='contado',
        moneda=reserva.paquete.moneda,
    )

    # Crear detalles de la factura
    item_numero = 1

    # Detalle principal: Paquete turístico para 1 pasajero
    paquete = reserva.paquete
    precio_unitario = pasajero.precio_asignado or Decimal('0')
    subtotal_paquete = precio_unitario

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
        descripcion=f"Paquete Turístico: {paquete.nombre} - {persona.nombre} {persona.apellido}",
        cantidad=1,
        precio_unitario=precio_unitario,
        monto_exenta=monto_exenta,
        monto_gravada_5=monto_gravada_5,
        monto_gravada_10=monto_gravada_10,
        subtotal=subtotal_paquete
    )

    # Calcular totales de la factura
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