# 📋 DOCUMENTACIÓN Y COMPROBANTES PARA RESERVAS

> **Objetivo:** Implementar el sistema de documentación completo para el flujo de reservas, desde la creación hasta la finalización.

---

## 📊 ESTADO ACTUAL

- ✅ Sistema de reservas: **80% completado**
- ✅ Modelo `Reserva` con estados y validaciones
- ✅ Sistema de facturación básico (`FacturaElectronica`)
- ⚠️ **FALTA:** Documentación de pagos y comprobantes

---

## 🎯 FLUJO DE DOCUMENTOS EN EL CICLO DE VIDA

```
CREACIÓN → CONFIRMACIÓN → FINALIZACIÓN → POST-VIAJE
   ↓           ↓              ↓              ↓
 Recibo     Voucher       Factura        Encuesta
  Seña                                   (opcional)
```

---

## 🔥 PRIORIDAD ALTA - IMPLEMENTACIÓN INMEDIATA

### 1. ComprobantePago

**Propósito:** Registrar todos los pagos realizados por el cliente (seña, pagos parciales, pago total)

**Ubicación:** `apps/reserva/models/comprobante.py`

#### Modelo propuesto:

```python
from django.db import models
from django.utils.timezone import now
from apps.reserva.models import Reserva
from apps.empleado.models import Empleado


class ComprobantePago(models.Model):
    """
    Registra todos los pagos asociados a una reserva.
    Un ComprobantePago representa UN pago específico (seña, pago parcial, pago total).
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
        Reserva,
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
        help_text="Monto pagado en este comprobante"
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
        Empleado,
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

        # Actualizar monto_pagado en la reserva
        self.actualizar_monto_reserva()

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
        ).aggregate(total=Sum('monto'))['total'] or 0

        # Restar devoluciones
        total_devoluciones = ComprobantePago.objects.filter(
            reserva=self.reserva,
            activo=True,
            tipo='devolucion'
        ).aggregate(total=Sum('monto'))['total'] or 0

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
```

#### Contenido del Comprobante (PDF):

```
┌─────────────────────────────────────────────────┐
│        COMPROBANTE DE PAGO #CPG-2025-0001       │
│                                                 │
│  Fecha: 22/10/2025  Hora: 14:30                │
│  Tipo: SEÑA                                     │
│                                                 │
│  DATOS DEL CLIENTE:                             │
│  • Titular: Juan Pérez                          │
│  • Documento: 1.234.567                         │
│  • Teléfono: +595 981 123456                    │
│  • Email: juan@example.com                      │
│                                                 │
│  DATOS DE LA RESERVA:                           │
│  • Código: RSV-2025-0001                        │
│  • Paquete: Río Aéreo Flexible x2               │
│  • Destino: Rio de Janeiro, Brasil              │
│  • Fecha salida: 25/10/2025                     │
│  • Fecha regreso: 08/11/2025                    │
│  • Habitación: Doble                            │
│  • Cantidad pasajeros: 2                        │
│                                                 │
│  DETALLE DEL PAGO:                              │
│  • Método: Transferencia Bancaria               │
│  • Referencia: TRF-20251022-001                 │
│  • Monto pagado: $1,000.00                      │
│                                                 │
│  RESUMEN ECONÓMICO:                             │
│  • Precio total: $3,250.00                      │
│  • Total pagado: $1,000.00                      │
│  • Saldo pendiente: $2,250.00                   │
│                                                 │
│  ⚠️ IMPORTANTE:                                 │
│  - Esta seña reserva su cupo                    │
│  - Complete los datos de pasajeros en 48hs     │
│  - Saldo vence el: 20/10/2025                   │
│                                                 │
│  Atendido por: María González                   │
│  Firma: _____________________                   │
│                                                 │
│  Agencia: GroupTours                            │
│  Tel: +595 21 123 4567                          │
│  Email: info@grouptours.com                     │
└─────────────────────────────────────────────────┘
```

---

### 2. Voucher

**Propósito:** Documento oficial que confirma la reserva y sirve para presentar en el hotel

**Ubicación:** `apps/reserva/models/voucher.py`

#### Modelo propuesto:

```python
from django.db import models
from apps.reserva.models import Reserva


class Voucher(models.Model):
    """
    Documento que confirma la reserva del cliente.
    Se genera automáticamente cuando la reserva pasa a estado 'confirmada'.
    """

    reserva = models.OneToOneField(
        Reserva,
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
```

#### Contenido del Voucher (PDF):

```
┌─────────────────────────────────────────────────┐
│              🎫 VOUCHER DE RESERVA              │
│         Código: RSV-2025-0001-VOUCHER           │
│                                                 │
│  ✓ CONFIRMADA  |  Emitido: 22/10/2025          │
│                                                 │
│  ═══════════════════════════════════════════   │
│  DATOS DEL TITULAR:                             │
│  • Nombre: Juan Pérez                           │
│  • Documento: CI 1.234.567                      │
│  • Teléfono: +595 981 123456                    │
│  • Email: juan@example.com                      │
│                                                 │
│  ═══════════════════════════════════════════   │
│  PASAJEROS:                                     │
│  1. Juan Pérez (CI: 1.234.567) - TITULAR       │
│  2. María López (CI: 7.654.321)                │
│                                                 │
│  ═══════════════════════════════════════════   │
│  ITINERARIO:                                    │
│  📅 Salida: 25 Octubre 2025 - 08:00           │
│  📅 Regreso: 08 Noviembre 2025 - 18:00        │
│  🌙 Duración: 14 noches                        │
│  📍 Destino: Rio de Janeiro, Brasil            │
│                                                 │
│  ═══════════════════════════════════════════   │
│  ALOJAMIENTO:                                   │
│  🏨 Hotel: Hard Rock Rio ⭐⭐⭐⭐               │
│  🛏️ Habitación: Doble (#101)                  │
│  📍 Dirección: Av. Atlántica 1500, Copacabana │
│  🔑 Check-in: 25 Oct, 15:00                    │
│  🔑 Check-out: 08 Nov, 12:00                   │
│                                                 │
│  ═══════════════════════════════════════════   │
│  SERVICIOS INCLUIDOS:                           │
│  ✓ Traslado aeropuerto-hotel-aeropuerto        │
│  ✓ Desayuno buffet                              │
│  ✓ Wi-Fi gratuito                               │
│  ✓ Acceso a piscina                             │
│                                                 │
│  ═══════════════════════════════════════════   │
│  📞 CONTACTO DE EMERGENCIA:                    │
│  Tel: +595 981 123 456 (24/7)                  │
│  Email: emergencias@grouptours.com              │
│                                                 │
│  ⚠️ IMPORTANTE:                                 │
│  • Presentar este voucher en el hotel          │
│  • Llevar documento de identidad vigente       │
│  • Check-in mínimo: 15:00                      │
│  • Check-out máximo: 12:00                     │
│                                                 │
│  💰 ESTADO DE PAGO:                            │
│  • Total pagado: $3,250.00                      │
│  • Saldo pendiente: $0.00                       │
│  • Estado: PAGADO                               │
│                                                 │
│  ═══════════════════════════════════════════   │
│                                                 │
│          [QR CODE]                              │
│                                                 │
│  Válido solo con presentación de documento     │
│  de identidad del titular                       │
│                                                 │
│  GroupTours - Tu agencia de confianza          │
│  www.grouptours.com                             │
└─────────────────────────────────────────────────┘
```

---

### 3. FacturaReserva

**Propósito:** Conectar el sistema de facturación existente con las reservas

**Ubicación:** `apps/reserva/models/factura.py`

#### Modelo propuesto:

```python
from django.db import models
from decimal import Decimal
from apps.reserva.models import Reserva
from apps.facturacion.models import FacturaElectronica


class FacturaReserva(models.Model):
    """
    Vincula una reserva con una factura electrónica oficial.
    Contiene el desglose detallado de los conceptos facturados.
    """

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        related_name='facturas',
        help_text="Reserva asociada a esta factura"
    )

    factura_electronica = models.ForeignKey(
        FacturaElectronica,
        on_delete=models.PROTECT,
        related_name='reservas_facturadas',
        help_text="Factura electrónica oficial generada"
    )

    fecha_emision = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de emisión de la factura"
    )

    # Desglose de conceptos
    monto_habitacion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monto correspondiente a la habitación"
    )

    monto_servicios_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto de servicios incluidos en el paquete base"
    )

    monto_servicios_adicionales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto de servicios adicionales contratados"
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Subtotal antes de impuestos"
    )

    monto_impuestos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto total de impuestos aplicados"
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total de la factura (subtotal + impuestos)"
    )

    observaciones = models.TextField(
        null=True,
        blank=True,
        help_text="Notas adicionales en la factura"
    )

    activo = models.BooleanField(
        default=True,
        help_text="Indica si la factura está activa"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Factura de Reserva"
        verbose_name_plural = "Facturas de Reservas"
        db_table = "FacturaReserva"
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"Factura {self.factura_electronica.numero_factura} - {self.reserva.codigo}"

    def calcular_montos(self):
        """
        Calcula automáticamente los montos basándose en la reserva.
        """
        # Precio unitario × cantidad de pasajeros
        self.subtotal = self.reserva.precio_unitario * self.reserva.cantidad_pasajeros

        # Aplicar impuestos según configuración de factura electrónica
        if self.factura_electronica.subtipo_impuesto:
            porcentaje_impuesto = self.factura_electronica.subtipo_impuesto.porcentaje
            self.monto_impuestos = (self.subtotal * porcentaje_impuesto) / Decimal('100')
        else:
            self.monto_impuestos = Decimal('0')

        self.total = self.subtotal + self.monto_impuestos
```

---

## 📦 ESTRUCTURA DE ARCHIVOS PROPUESTA

```
GroupTours/
├── apps/
│   └── reserva/
│       ├── models/
│       │   ├── __init__.py
│       │   ├── reserva.py          # Ya existe
│       │   ├── comprobante.py      # NUEVO ⭐
│       │   ├── voucher.py          # NUEVO ⭐
│       │   ├── factura.py          # NUEVO ⭐
│       │   └── servicio_adicional.py  # Futuro
│       ├── serializers/
│       │   ├── __init__.py
│       │   ├── comprobante.py      # NUEVO ⭐
│       │   ├── voucher.py          # NUEVO ⭐
│       │   └── factura.py          # NUEVO ⭐
│       ├── views/
│       │   ├── __init__.py
│       │   ├── comprobante.py      # NUEVO ⭐
│       │   ├── voucher.py          # NUEVO ⭐
│       │   └── factura.py          # NUEVO ⭐
│       ├── services/
│       │   ├── __init__.py
│       │   ├── pdf_generator.py    # NUEVO ⭐
│       │   ├── email_service.py    # NUEVO ⭐
│       │   └── qr_generator.py     # NUEVO ⭐
│       └── templates/
│           └── reserva/
│               ├── comprobante_pdf.html    # NUEVO ⭐
│               ├── voucher_pdf.html        # NUEVO ⭐
│               └── email_confirmacion.html # NUEVO ⭐
```

---

## 🔧 SERVICIOS AUXILIARES NECESARIOS

### 1. Generador de PDFs

**Ubicación:** `apps/reserva/services/pdf_generator.py`

**Librerías recomendadas:**
- `reportlab` (más control)
- `weasyprint` (desde HTML)
- `xhtml2pdf` (simple)

**Funciones principales:**
```python
def generar_comprobante_pdf(comprobante):
    """Genera PDF del comprobante de pago"""
    pass

def generar_voucher_pdf(voucher):
    """Genera PDF del voucher de reserva"""
    pass
```

### 2. Generador de QR Codes

**Ubicación:** `apps/reserva/services/qr_generator.py`

**Librería:** `qrcode`

**Instalación:**
```bash
pip install qrcode[pil]
```

### 3. Servicio de Email

**Ubicación:** `apps/reserva/services/email_service.py`

**Funciones principales:**
```python
def enviar_comprobante_email(comprobante, destinatario):
    """Envía comprobante por email"""
    pass

def enviar_voucher_email(voucher, destinatario):
    """Envía voucher por email"""
    pass

def enviar_recordatorio_pago(reserva):
    """Envía recordatorio de pago pendiente"""
    pass
```

---

## 🚀 PLAN DE IMPLEMENTACIÓN

### Fase 1: Comprobantes de Pago (1-2 días)

- [ ] Crear modelo `ComprobantePago`
- [ ] Crear serializer y viewset
- [ ] Implementar lógica de generación de número único
- [ ] Implementar actualización automática de `monto_pagado` en Reserva
- [ ] Crear template HTML para PDF
- [ ] Implementar generador de PDF
- [ ] Crear endpoint POST `/api/reservas/{id}/comprobantes/`
- [ ] Crear endpoint GET `/api/comprobantes/{id}/pdf/`
- [ ] Probar flujo completo

### Fase 2: Vouchers (1-2 días)

- [ ] Crear modelo `Voucher`
- [ ] Crear serializer y viewset
- [ ] Implementar generador de QR code
- [ ] Crear template HTML para PDF del voucher
- [ ] Implementar generador de PDF del voucher
- [ ] Crear trigger automático: cuando Reserva → "confirmada", crear Voucher
- [ ] Crear endpoint GET `/api/vouchers/{id}/pdf/`
- [ ] Crear vista pública `/vouchers/{codigo}/` (sin autenticación)
- [ ] Probar flujo completo

### Fase 3: Facturación de Reservas (1 día)

- [ ] Crear modelo `FacturaReserva`
- [ ] Crear serializer y viewset
- [ ] Implementar cálculo automático de montos
- [ ] Conectar con `FacturaElectronica` existente
- [ ] Crear endpoint POST `/api/reservas/{id}/facturar/`
- [ ] Actualizar estado de reserva a "finalizada" al facturar
- [ ] Probar flujo completo

### Fase 4: Servicios Auxiliares (1 día)

- [ ] Implementar servicio de email
- [ ] Configurar templates de email
- [ ] Implementar envío automático de comprobantes
- [ ] Implementar envío automático de vouchers
- [ ] Configurar recordatorios de pago
- [ ] Probar notificaciones

### Fase 5: Testing y Ajustes (1 día)

- [ ] Testing de generación de PDFs
- [ ] Testing de flujo completo de reserva
- [ ] Testing de emails
- [ ] Ajustes de diseño de documentos
- [ ] Documentación de APIs

---

## 📋 ENDPOINTS A CREAR

### Comprobantes de Pago

```
POST   /api/reservas/{id}/comprobantes/
GET    /api/comprobantes/
GET    /api/comprobantes/{id}/
GET    /api/comprobantes/{id}/pdf/
PUT    /api/comprobantes/{id}/anular/
```

### Vouchers

```
GET    /api/vouchers/
GET    /api/vouchers/{id}/
GET    /api/vouchers/{id}/pdf/
GET    /api/vouchers/{codigo}/publico/  # Sin autenticación
```

### Facturas

```
POST   /api/reservas/{id}/facturar/
GET    /api/facturas-reserva/
GET    /api/facturas-reserva/{id}/
```

---

## 🎨 LIBRERÍAS A INSTALAR

```bash
# Para PDFs
pip install reportlab
pip install weasyprint
# O
pip install xhtml2pdf

# Para QR Codes
pip install qrcode[pil]

# Para emails con templates
pip install django-templated-mail
```

---

## ⚙️ CONFIGURACIÓN NECESARIA

### settings.py

```python
# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # O tu servidor SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD')
DEFAULT_FROM_EMAIL = 'noreply@grouptours.com'

# Media files (para PDFs y QR codes)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Template directory para PDFs
TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'apps/reserva/templates'))
```

### .env

```
EMAIL_USER=tu_email@gmail.com
EMAIL_PASSWORD=tu_app_password
```

---

## 🧪 CASOS DE PRUEBA

### Caso 1: Reserva con Seña

1. Cliente crea reserva → estado: "pendiente"
2. Cliente paga seña 30% → se genera `ComprobantePago` tipo "seña"
3. Sistema actualiza `monto_pagado` en reserva
4. Cliente completa datos de pasajeros
5. Sistema cambia estado a "confirmada"
6. Sistema genera `Voucher` automáticamente
7. Sistema envía email con voucher adjunto

### Caso 2: Múltiples Pagos Parciales

1. Cliente paga 1er pago → `ComprobantePago` tipo "pago_parcial"
2. Cliente paga 2do pago → `ComprobantePago` tipo "pago_parcial"
3. Cliente paga saldo final → `ComprobantePago` tipo "pago_total"
4. Sistema verifica que `monto_pagado >= precio_total`
5. Sistema cambia estado a "finalizada"
6. Sistema genera `FacturaReserva`

### Caso 3: Anulación de Comprobante

1. Se registra pago por error
2. Empleado anula comprobante
3. Sistema recalcula `monto_pagado`
4. Sistema actualiza estado de reserva si es necesario

---

## 💡 MEJORAS FUTURAS (Post-MVP)

### Prioridad Media

- [ ] ServicioAdicional: Servicios extras que el cliente puede agregar
- [ ] HistorialEstadoReserva: Audit trail de cambios
- [ ] NotificacionCliente: Sistema de notificaciones automatizadas
- [ ] EncuestaPostventa: Feedback del cliente después del viaje

### Prioridad Baja

- [ ] Integración con pasarelas de pago (tarjetas de crédito)
- [ ] Sistema de recordatorios automáticos por WhatsApp
- [ ] Dashboard de seguimiento de pagos
- [ ] Reportes de facturación por período
- [ ] Integración con contabilidad

---

## 📞 CONTACTO Y SOPORTE

Si tienes dudas durante la implementación:
1. Revisar este documento
2. Consultar la documentación de Django REST Framework
3. Revisar `CLAUDE.md` en la raíz del proyecto

---

**Última actualización:** 22 de Octubre de 2025
**Versión:** 1.0
**Estado:** Documentación de recomendaciones
