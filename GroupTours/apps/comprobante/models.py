from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from decimal import Decimal


class ComprobantePago(models.Model):
    """
    Registra todos los pagos asociados a una reserva.
    Un ComprobantePago representa UN pago específico (seña, pago parcial, pago total).
    Cada comprobante se distribuye entre los pasajeros mediante ComprobantePagoDistribucion.
    """

    TIPOS = [
        ('sena', 'Seña'),
        ('pago_parcial', 'Pago Parcial'),
        ('pago_total', 'Pago Total'),
        ('devolucion', 'Devolución'),
    ]

    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('cheque', 'Cheque'),
        ('qr', 'Pago QR'),
        ('otro', 'Otro'),
    ]

    reserva = models.ForeignKey(
        'reserva.Reserva',
        on_delete=models.PROTECT,
        related_name='comprobantes',
        help_text="Reserva asociada a este comprobante"
    )

    numero_comprobante = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Número único del comprobante (ej: CPG-2025-0001)"
    )

    fecha_pago = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora en que se registró el pago"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        help_text="Tipo de pago realizado"
    )

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monto total del comprobante"
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO,
        help_text="Método de pago utilizado"
    )

    referencia = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Número de referencia/comprobante del banco, cheque, etc."
    )

    observaciones = models.TextField(
        null=True,
        blank=True,
        help_text="Notas adicionales sobre el pago"
    )

    empleado = models.ForeignKey(
        'empleado.Empleado',
        on_delete=models.PROTECT,
        related_name='comprobantes_emitidos',
        help_text="Empleado que registró el pago"
    )

    pdf_generado = models.FileField(
        upload_to='comprobantes/pdf/',
        null=True,
        blank=True,
        help_text="PDF del comprobante generado"
    )

    activo = models.BooleanField(
        default=True,
        help_text="Indica si el comprobante está activo (no fue anulado)"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comprobante de Pago"
        verbose_name_plural = "Comprobantes de Pago"
        db_table = "ComprobantePago"
        ordering = ["-fecha_pago"]

    def __str__(self):
        return f"{self.numero_comprobante} - {self.reserva.codigo} - ${self.monto}"

    def save(self, *args, **kwargs):
        # Generar número único de comprobante
        if not self.numero_comprobante:
            year = now().year
            last_id = ComprobantePago.objects.filter(
                fecha_pago__year=year
            ).count() + 1
            self.numero_comprobante = f"CPG-{year}-{last_id:04d}"

        super().save(*args, **kwargs)

    def validar_distribuciones(self):
        """
        Valida que la suma de distribuciones sea igual al monto total del comprobante.
        """
        total_distribuido = sum(d.monto for d in self.distribuciones.all())
        if total_distribuido != self.monto:
            raise ValidationError(
                f"La suma de distribuciones (${total_distribuido}) no coincide "
                f"con el monto del comprobante (${self.monto})"
            )

    def actualizar_monto_reserva(self):
        """
        Recalcula el monto total pagado en la reserva sumando todos los comprobantes activos.
        """
        from django.db.models import Sum

        total_pagado = ComprobantePago.objects.filter(
            reserva=self.reserva,
            activo=True
        ).exclude(
            tipo='devolucion'  # Las devoluciones se restan
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        # Restar devoluciones
        total_devoluciones = ComprobantePago.objects.filter(
            reserva=self.reserva,
            activo=True,
            tipo='devolucion'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        self.reserva.monto_pagado = total_pagado - total_devoluciones
        self.reserva.save(update_fields=['monto_pagado'])

        # Actualizar estado de la reserva
        self.reserva.actualizar_estado()

    def anular(self, motivo=None):
        """
        Anula el comprobante y actualiza el monto de la reserva.
        """
        self.activo = False
        if motivo:
            self.observaciones = f"ANULADO: {motivo}\n{self.observaciones or ''}"
        self.save()
        self.actualizar_monto_reserva()

    def generar_pdf(self):
        """
        Genera un PDF del comprobante de pago con toda la información.
        Utiliza reportlab para crear el documento.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        from io import BytesIO
        from django.core.files import File

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
        c.drawString(50, y, "COMPROBANTE DE PAGO")

        # Línea decorativa
        c.setStrokeColor(colors.HexColor("#2c3e50"))
        c.setLineWidth(2)
        c.line(50, y - 10, width - 50, y - 10)

        y -= 50

        # INFORMACIÓN DEL COMPROBANTE
        c.setFont(title_font, 12)
        c.drawString(50, y, f"Numero: {self.numero_comprobante}")
        c.drawString(350, y, f"Fecha: {self.fecha_pago.strftime('%d/%m/%Y %H:%M')}")

        y -= 30
        c.setFont(normal_font, 10)
        c.drawString(50, y, f"Tipo: {self.get_tipo_display()}")
        c.drawString(350, y, f"Metodo: {self.get_metodo_pago_display()}")

        y -= 20
        if self.referencia:
            c.drawString(50, y, f"Referencia: {self.referencia}")
            y -= 20

        # INFORMACIÓN DE LA RESERVA
        y -= 20
        c.setFont(title_font, 12)
        c.drawString(50, y, "INFORMACION DE LA RESERVA")
        c.setLineWidth(1)
        c.line(50, y - 5, 250, y - 5)

        y -= 25
        c.setFont(normal_font, 10)
        c.drawString(50, y, f"Reserva: {self.reserva.codigo}")
        y -= 15

        # Badge de estado con color
        c.drawString(50, y, "Estado:")

        # Definir colores según el estado
        estado_colors = {
            'pendiente': colors.HexColor("#f39c12"),      # Naranja
            'confirmada': colors.HexColor("#3498db"),     # Azul
            'incompleta': colors.HexColor("#e67e22"),     # Naranja oscuro
            'finalizada': colors.HexColor("#27ae60"),     # Verde
            'cancelada': colors.HexColor("#e74c3c"),      # Rojo
        }

        # Usar estado_display personalizado que incluye "Incompleto" o "Completo"
        estado_text = self.reserva.estado_display
        estado_valor = self.reserva.estado
        badge_color = estado_colors.get(estado_valor, colors.grey)

        # Dibujar badge redondeado
        badge_x = 100
        badge_y = y - 3
        badge_width = len(estado_text) * 6 + 16  # Ancho dinámico según el texto
        badge_height = 16
        badge_radius = 4

        # Fondo del badge con bordes redondeados
        c.setFillColor(badge_color)
        c.roundRect(badge_x, badge_y, badge_width, badge_height, badge_radius, fill=1, stroke=0)

        # Texto del badge en blanco
        c.setFillColor(colors.white)
        c.setFont(title_font, 9)
        c.drawString(badge_x + 8, badge_y + 4, estado_text)

        # Restaurar color negro para el resto del texto
        c.setFillColor(colors.black)

        y -= 15
        c.setFont(normal_font, 10)
        c.drawString(50, y, f"Paquete: {self.reserva.paquete.nombre}")
        y -= 15
        if self.reserva.titular:
            c.drawString(50, y, f"Titular: {self.reserva.titular.nombre} {self.reserva.titular.apellido}")
            y -= 15

        # DISTRIBUCIÓN DEL PAGO
        y -= 20
        c.setFont(title_font, 12)
        c.drawString(50, y, "DISTRIBUCION DEL PAGO")
        c.line(50, y - 5, 250, y - 5)

        y -= 25

        # Crear tabla de distribuciones con información financiera completa
        distribuciones = self.distribuciones.all()

        # Datos de la tabla con columnas reorganizadas: Monto Pago al final
        data = [['Pasajero', 'Documento', 'Total Pagado', 'Saldo Pdte.', 'Monto Pago']]

        for dist in distribuciones:
            # Calcular monto total pagado por este pasajero hasta el momento
            from django.db.models import Sum
            monto_pagado_total = ComprobantePagoDistribucion.objects.filter(
                pasajero=dist.pasajero,
                comprobante__activo=True
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

            precio_asignado = dist.pasajero.precio_asignado or Decimal('0')
            saldo_pendiente = precio_asignado - monto_pagado_total

            data.append([
                f"{dist.pasajero.persona.nombre} {dist.pasajero.persona.apellido}",
                dist.pasajero.persona.documento or '-',
                f"${monto_pagado_total:,.2f}",
                f"${saldo_pendiente:,.2f}",
                f"${dist.monto:,.2f}"
            ])

        # Agregar fila de total (solo para el monto del pago actual en la última columna)
        data.append(['', '', '', '', f"${self.monto:,.2f}"])

        # Crear tabla con anchos ajustados para las 5 columnas
        table = Table(data, colWidths=[130, 75, 85, 85, 85])
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495e")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (4, -1), 'RIGHT'),  # Alinear a la derecha las columnas de montos
            ('FONTNAME', (0, 0), (-1, 0), title_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Contenido
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),

            # Fila de total
            ('FONTNAME', (0, -1), (-1, -1), title_font),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
            ('SPAN', (0, -1), (3, -1)),  # Fusionar las primeras 4 columnas en la fila de total
        ]))

        # Dibujar tabla
        table.wrapOn(c, width, height)
        table.drawOn(c, 50, y - (len(data) * 25))

        y -= (len(data) * 25) + 40

        # RESUMEN ECONÓMICO
        y -= 10
        c.setFont(title_font, 12)
        c.drawString(50, y, "RESUMEN ECONOMICO")
        c.line(50, y - 5, 250, y - 5)

        y -= 25

        # Calcular precio total y saldo pendiente
        precio_total = self.reserva.costo_total_estimado
        total_pagado = self.reserva.monto_pagado
        saldo_pendiente = precio_total - total_pagado

        # Crear tabla de resumen económico
        resumen_data = [
            ['Concepto', 'Monto'],
            ['Precio Total:', f"${precio_total:,.2f}"],
            ['Total Pagado:', f"${total_pagado:,.2f}"],
            ['Saldo Pendiente:', f"${saldo_pendiente:,.2f}"],
        ]

        resumen_table = Table(resumen_data, colWidths=[200, 150])
        resumen_table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), title_font),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Contenido
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

            # Fila de saldo pendiente (destacada)
            ('FONTNAME', (0, -1), (-1, -1), title_font),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e74c3c" if saldo_pendiente > 0 else "#27ae60")),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ]))

        # Dibujar tabla de resumen
        resumen_table.wrapOn(c, width, height)
        resumen_table.drawOn(c, 50, y - (len(resumen_data) * 25))

        y -= (len(resumen_data) * 25) + 40

        # EMPLEADO
        c.setFont(normal_font, 9)
        # Obtener PersonaFisica del empleado (modelo polimórfico)
        empleado_persona = self.empleado.persona
        if hasattr(empleado_persona, 'personafisica'):
            empleado_persona = empleado_persona.personafisica
        empleado_nombre = f"{empleado_persona.nombre} {empleado_persona.apellido}" if hasattr(empleado_persona, 'nombre') else str(empleado_persona)
        c.drawString(50, y, f"Emitido por: {empleado_nombre}")

        # OBSERVACIONES
        if self.observaciones:
            y -= 30
            c.setFont(title_font, 10)
            c.drawString(50, y, "Observaciones:")
            y -= 15
            c.setFont(normal_font, 9)

            # Dividir observaciones en líneas
            obs_lines = self.observaciones.split('\n')
            for line in obs_lines[:5]:  # Máximo 5 líneas
                if y < 100:  # Si no hay espacio, crear nueva página
                    c.showPage()
                    y = height - 50
                c.drawString(70, y, line[:80])  # Máximo 80 caracteres
                y -= 12

        # PIE DE PÁGINA
        c.setFont(normal_font, 8)
        c.setFillColor(colors.grey)
        c.drawCentredString(width / 2, 50, "GroupTours - Sistema de Gestion de Reservas")
        c.drawCentredString(width / 2, 35, f"Generado: {self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}")

        # Estado del comprobante
        if not self.activo:
            c.setFont(title_font, 40)
            c.setFillColor(colors.red)
            c.saveState()
            c.translate(width / 2, height / 2)
            c.rotate(45)
            c.drawCentredString(0, 0, "ANULADO")
            c.restoreState()

        # Finalizar PDF
        c.save()

        # Guardar en el campo del modelo
        buffer.seek(0)
        filename = f'comprobante_{self.numero_comprobante}.pdf'
        self.pdf_generado.save(filename, File(buffer), save=False)
        buffer.close()

        return self.pdf_generado


class ComprobantePagoDistribucion(models.Model):
    """
    Distribución de un pago entre pasajeros.
    Permite asignar partes de un comprobante a diferentes pasajeros.

    Ejemplo:
    - ComprobantePago de $2,000
    - Distribución 1: Pasajero Juan → $800
    - Distribución 2: Pasajero María → $700
    - Distribución 3: Pasajero Pedro → $300
    - Distribución 4: Pasajero Ana → $200
    Total: $2,000 ✓
    """

    comprobante = models.ForeignKey(
        ComprobantePago,
        on_delete=models.CASCADE,
        related_name='distribuciones',
        help_text="Comprobante de pago del cual se distribuye el monto"
    )

    pasajero = models.ForeignKey(
        'reserva.Pasajero',
        on_delete=models.PROTECT,
        related_name='distribuciones_pago',
        help_text="Pasajero al que se le asigna este monto"
    )

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monto de este comprobante asignado a este pasajero"
    )

    observaciones = models.TextField(
        null=True,
        blank=True,
        help_text="Notas sobre esta distribución específica"
        
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Distribución de Pago"
        verbose_name_plural = "Distribuciones de Pago"
        db_table = "ComprobantePagoDistribucion"
        unique_together = ("comprobante", "pasajero")

    def __str__(self):
        return f"{self.comprobante.numero_comprobante} → {self.pasajero.persona} (${self.monto})"

    def clean(self):
        """
        Validaciones de negocio para la distribución.
        """
        # Validar que el pasajero pertenece a la reserva del comprobante
        if self.pasajero.reserva != self.comprobante.reserva:
            raise ValidationError(
                "El pasajero no pertenece a la reserva del comprobante"
            )

        # Validar que el monto es positivo
        if self.monto <= 0:
            raise ValidationError("El monto de la distribución debe ser mayor a cero")

        # Validar que no se exceda el monto total del comprobante
        total_otras_distribuciones = sum(
            d.monto
            for d in self.comprobante.distribuciones.exclude(id=self.id)
        )
        if (total_otras_distribuciones + self.monto) > self.comprobante.monto:
            raise ValidationError(
                f"El total de distribuciones excede el monto del comprobante. "
                f"Disponible: ${self.comprobante.monto - total_otras_distribuciones}"
            )


class Voucher(models.Model):
    """
    Documento que confirma la reserva del cliente.
    Se genera automáticamente cuando la reserva pasa a estado 'confirmada'.
    """

    reserva = models.OneToOneField(
        'reserva.Reserva',
        on_delete=models.PROTECT,
        related_name='voucher',
        help_text="Reserva asociada a este voucher"
    )

    codigo_voucher = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Código único del voucher (ej: RSV-2025-0001-VOUCHER)"
    )

    fecha_emision = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de emisión del voucher"
    )

    qr_code = models.ImageField(
        upload_to='vouchers/qr/',
        null=True,
        blank=True,
        help_text="Código QR para validación rápida"
    )

    pdf_generado = models.FileField(
        upload_to='vouchers/pdf/',
        null=True,
        blank=True,
        help_text="PDF del voucher generado"
    )

    instrucciones_especiales = models.TextField(
        null=True,
        blank=True,
        help_text="Instrucciones adicionales para el cliente"
    )

    contacto_emergencia = models.CharField(
        max_length=100,
        default='+595 981 123 456',
        help_text="Teléfono de contacto de emergencia 24/7"
    )

    url_publica = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="URL pública para visualizar el voucher online"
    )

    activo = models.BooleanField(
        default=True,
        help_text="Indica si el voucher está activo"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Voucher"
        verbose_name_plural = "Vouchers"
        db_table = "Voucher"

    def __str__(self):
        return f"{self.codigo_voucher} - {self.reserva.codigo}"

    def save(self, *args, **kwargs):
        # Generar código único de voucher
        if not self.codigo_voucher:
            self.codigo_voucher = f"{self.reserva.codigo}-VOUCHER"

        super().save(*args, **kwargs)

    def generar_qr(self):
        """
        Genera el código QR con la información del voucher.
        Usa la librería qrcode.
        """
        try:
            import qrcode
            from io import BytesIO
            from django.core.files import File

            # Datos a incluir en el QR
            datos_qr = f"VOUCHER:{self.codigo_voucher}|RESERVA:{self.reserva.codigo}"

            # Generar QR
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(datos_qr)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Guardar en el campo
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            filename = f'voucher_{self.reserva.codigo}.png'
            self.qr_code.save(filename, File(buffer), save=False)
            buffer.close()

        except ImportError:
            raise ValidationError(
                "La librería 'qrcode' no está instalada. "
                "Instale con: pip install qrcode[pil]"
            )
