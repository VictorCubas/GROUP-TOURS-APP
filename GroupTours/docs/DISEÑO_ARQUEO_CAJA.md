# DISEÑO TÉCNICO - APP ARQUEO DE CAJA

## Índice
1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Análisis de Arquitectura Actual](#análisis-de-arquitectura-actual)
3. [Diseño de Modelos](#diseño-de-modelos)
4. [Diagrama de Relaciones](#diagrama-de-relaciones)
5. [API Endpoints](#api-endpoints)
6. [Integración con Apps Existentes](#integración-con-apps-existentes)
7. [Flujo de Implementación](#flujo-de-implementación)
8. [Consideraciones de Seguridad](#consideraciones-de-seguridad)

---

## Resumen Ejecutivo

### Objetivo
Implementar una app Django independiente para gestionar el **Arqueo de Caja**, que permita:
- Apertura y cierre de cajas
- Registro de movimientos (ingresos/egresos)
- Arqueo de efectivo con detección de diferencias
- Generación de reportes financieros
- Integración con el módulo de comprobantes existente

### Stack Tecnológico
- **Framework**: Django 5.x + Django REST Framework
- **Base de datos**: PostgreSQL
- **Autenticación**: JWT (Simple JWT)
- **Filtros**: django-filter
- **Validación**: DRF Serializers

### Ubicación de la App
```
apps/arqueo_caja/
```

---

## Análisis de Arquitectura Actual

### Patrón Identificado en el Proyecto

#### 1. Estructura de Apps
```
apps/
├── comprobante/       # Comprobantes de pago (CRUD)
├── facturacion/       # Facturas electrónicas
├── reserva/           # Reservaciones
├── empleado/          # Gestión de empleados
├── persona/           # Personas (físicas/jurídicas)
├── usuario/           # Custom User Model
└── ... (25+ apps)
```

#### 2. Patrón de Vistas
**ModelViewSet con serializer dinámico:**
```python
class MyViewSet(viewsets.ModelViewSet):
    queryset = Model.objects.select_related(...).prefetch_related(...)
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['campo1', 'campo2']
    permission_classes = []  # O [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ListSerializer
        elif self.action in ['create', 'update']:
            return WriteSerializer
        return DetailSerializer

    @action(detail=True, methods=['post'])
    def custom_action(self, request, pk=None):
        # Lógica personalizada
        pass
```

#### 3. Patrón de Modelos
**Características estándar:**
- Campos de auditoría: `fecha_creacion`, `fecha_modificacion`, `activo`
- Códigos auto-generados en `save()`: `XXX-YYYY-NNNN`
- Métodos de negocio dentro del modelo
- `select_related` y `prefetch_related` en queryset para optimización
- Validaciones en `clean()` y en serializers

**Ejemplo de código auto-generado:**
```python
def save(self, *args, **kwargs):
    if not self.numero_comprobante:
        year = now().year
        last_id = ComprobantePago.objects.filter(
            fecha_pago__year=year
        ).count() + 1
        self.numero_comprobante = f"CPG-{year}-{last_id:04d}"
    super().save(*args, **kwargs)
```

#### 4. Relaciones entre Apps
**Mediante Foreign Keys directas:**
```python
# apps/comprobante/models.py
class ComprobantePago(models.Model):
    reserva = models.ForeignKey(
        'reserva.Reserva',
        on_delete=models.PROTECT,
        related_name='comprobantes'
    )
    empleado = models.ForeignKey(
        'empleado.Empleado',
        on_delete=models.PROTECT,
        related_name='comprobantes_emitidos'
    )
```

#### 5. Configuración de URLs
**Router centralizado:**
```python
# apps/api/urls.py
urlpatterns = [
    path('reservas/', include('apps.reserva.urls')),
    path('facturacion/', include('apps.facturacion.urls')),
    path('', include('apps.comprobante.urls')),  # Incluye comprobantes/vouchers
    # Nuestra nueva app:
    path('arqueo-caja/', include('apps.arqueo_caja.urls')),
]
```

---

## Diseño de Modelos

### Modelo 1: Caja

Representa un punto de venta físico donde se manejan transacciones.

```python
# apps/arqueo_caja/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from decimal import Decimal

class Caja(models.Model):
    """
    Representa un punto de venta (caja registradora).
    """

    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo (ej: Caja Principal, Caja 1)"
    )

    numero_caja = models.PositiveIntegerField(
        unique=True,
        help_text="Número único de la caja"
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
        return f"{self.nombre} (#{self.numero_caja})"

    def puede_abrir(self):
        """Verifica si la caja puede ser abierta"""
        return self.estado_actual == 'cerrada' and self.activo

    def puede_cerrar(self):
        """Verifica si la caja puede ser cerrada"""
        return self.estado_actual == 'abierta'
```

---

### Modelo 2: AperturaCaja

Representa la apertura de una caja al inicio del turno.

```python
class AperturaCaja(models.Model):
    """
    Registro de apertura de caja (inicio de turno).
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
            self.caja.save(update_fields=['estado_actual'])

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

        # El monto inicial debe ser positivo
        if self.monto_inicial < 0:
            raise ValidationError("El monto inicial no puede ser negativo")
```

---

### Modelo 3: MovimientoCaja

Representa ingresos y egresos de la caja durante el turno.

```python
class MovimientoCaja(models.Model):
    """
    Registra todos los movimientos (ingresos/egresos) de una caja abierta.
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

        if self.tipo_movimiento == 'ingreso':
            caja.saldo_actual += self.monto
        elif self.tipo_movimiento == 'egreso':
            caja.saldo_actual -= self.monto

        caja.save(update_fields=['saldo_actual'])
```

---

### Modelo 4: CierreCaja

Representa el cierre de caja y el arqueo final.

```python
class CierreCaja(models.Model):
    """
    Registro de cierre de caja (fin de turno con arqueo).
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

    # === REPORTE ===

    pdf_reporte = models.FileField(
        upload_to='cierres_caja/pdf/',
        null=True,
        blank=True,
        help_text="PDF del reporte de cierre"
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
            self.diferencia_efectivo = self.saldo_real_efectivo - self.saldo_teorico_efectivo

            # Calcular porcentaje
            if self.saldo_teorico_efectivo != 0:
                self.diferencia_porcentaje = (
                    (self.diferencia_efectivo / self.saldo_teorico_efectivo) * 100
                )

            # Determinar si requiere autorización (umbral: ±2%)
            if abs(self.diferencia_porcentaje or 0) > 2:
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
        from django.db.models import Sum, Q

        movimientos = self.apertura_caja.movimientos.filter(activo=True)

        # Ingresos por método de pago
        ingresos = movimientos.filter(tipo_movimiento='ingreso')

        self.total_efectivo = (
            ingresos.filter(metodo_pago='efectivo')
            .aggregate(total=Sum('monto'))['total'] or Decimal('0')
        )

        self.total_tarjetas = (
            ingresos.filter(metodo_pago__in=['tarjeta_debito', 'tarjeta_credito'])
            .aggregate(total=Sum('monto'))['total'] or Decimal('0')
        )

        self.total_transferencias = (
            ingresos.filter(metodo_pago='transferencia')
            .aggregate(total=Sum('monto'))['total'] or Decimal('0')
        )

        self.total_cheques = (
            ingresos.filter(metodo_pago='cheque')
            .aggregate(total=Sum('monto'))['total'] or Decimal('0')
        )

        self.total_otros_ingresos = (
            ingresos.filter(metodo_pago__in=['qr', 'otro'])
            .aggregate(total=Sum('monto'))['total'] or Decimal('0')
        )

        # Egresos
        self.total_egresos = (
            movimientos.filter(tipo_movimiento='egreso')
            .aggregate(total=Sum('monto'))['total'] or Decimal('0')
        )

        # Calcular saldos teóricos
        self.saldo_teorico_efectivo = (
            self.apertura_caja.monto_inicial +
            self.total_efectivo -
            self.total_egresos
        )

        self.saldo_teorico_total = (
            self.apertura_caja.monto_inicial +
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
        return {
            'codigo_cierre': self.codigo_cierre,
            'caja': self.apertura_caja.caja.nombre,
            'responsable': f"{self.apertura_caja.responsable.persona.nombre} {self.apertura_caja.responsable.persona.apellido}",
            'fecha_apertura': self.apertura_caja.fecha_hora_apertura.strftime('%d/%m/%Y %H:%M'),
            'fecha_cierre': self.fecha_hora_cierre.strftime('%d/%m/%Y %H:%M'),
            'duracion_turno': str(self.fecha_hora_cierre - self.apertura_caja.fecha_hora_apertura),

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
                'saldo_teorico': str(self.saldo_teorico_efectivo),
                'saldo_real': str(self.saldo_real_efectivo),
                'diferencia': str(self.diferencia_efectivo),
                'diferencia_porcentaje': str(self.diferencia_porcentaje),
            },

            'requiere_autorizacion': self.requiere_autorizacion,
            'observaciones': self.observaciones_cierre,
        }
```

---

## Diagrama de Relaciones

```
┌─────────────────────────────────────────────────────────────────┐
│                      APPS EXISTENTES                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐        ┌──────────────────┐              │
│  │   Empleado       │        │   Comprobante    │              │
│  │   (empleado)     │        │   (comprobante)  │              │
│  └────────┬─────────┘        └────────┬─────────┘              │
│           │                           │                         │
│           │ FK                        │ FK                      │
│           │                           │                         │
└───────────┼───────────────────────────┼─────────────────────────┘
            │                           │
            │                           │
            ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APP: ARQUEO_CAJA                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                           │
│  │      Caja        │                                           │
│  │  (Punto de venta)│                                           │
│  │  - numero_caja   │                                           │
│  │  - nombre        │                                           │
│  │  - estado_actual │                                           │
│  │  - saldo_actual  │                                           │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           │ 1:N                                                  │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────┐                                       │
│  │   AperturaCaja       │◄────┐                                 │
│  │  (Apertura de turno) │     │                                 │
│  │  - codigo_apertura   │     │ FK: responsable                 │
│  │  - monto_inicial     │     │ (Empleado)                      │
│  │  - fecha_apertura    │◄────┘                                 │
│  │  - esta_abierta      │                                       │
│  └────────┬─────────────┘                                       │
│           │                                                      │
│           │ 1:N                                                  │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────────┐                                   │
│  │   MovimientoCaja         │◄────┐                             │
│  │  (Ingresos/Egresos)      │     │                             │
│  │  - numero_movimiento     │     │ FK: comprobante             │
│  │  - tipo_movimiento       │     │ (ComprobantePago)           │
│  │  - concepto              │◄────┘                             │
│  │  - monto                 │◄────┐                             │
│  │  - metodo_pago           │     │ FK: usuario_registro        │
│  │  - referencia            │     │ (Empleado)                  │
│  │  - descripcion           │◄────┘                             │
│  └──────────────────────────┘                                   │
│           │                                                      │
│           │ Arqueo final                                         │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────────────┐                                   │
│  │    CierreCaja            │◄────┐                             │
│  │  (Cierre y Arqueo)       │     │ 1:1                         │
│  │  - codigo_cierre         │─────┘ FK: apertura_caja           │
│  │  - total_efectivo        │◄────┐                             │
│  │  - total_tarjetas        │     │ FK: autorizado_por          │
│  │  - total_egresos         │     │ (Empleado - Supervisor)     │
│  │  - saldo_teorico         │◄────┘                             │
│  │  - saldo_real            │                                   │
│  │  - diferencia            │                                   │
│  │  - requiere_autorizacion │                                   │
│  │  - pdf_reporte           │                                   │
│  └──────────────────────────┘                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

RELACIONES:
- Caja 1:N AperturaCaja
- AperturaCaja 1:1 CierreCaja
- AperturaCaja 1:N MovimientoCaja
- MovimientoCaja N:1 ComprobantePago (opcional)
- AperturaCaja/MovimientoCaja/CierreCaja N:1 Empleado
```

---

## API Endpoints

### Estructura de URLs

```python
# apps/arqueo_caja/urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'cajas', CajaViewSet, basename='caja')
router.register(r'aperturas', AperturaCajaViewSet, basename='apertura')
router.register(r'movimientos', MovimientoCajaViewSet, basename='movimiento')
router.register(r'cierres', CierreCajaViewSet, basename='cierre')

# URLs resultantes:
# GET    /api/arqueo-caja/cajas/
# POST   /api/arqueo-caja/cajas/
# GET    /api/arqueo-caja/cajas/{id}/
# ...
```

### Endpoints por Recurso

#### 1. Cajas
```
GET    /api/arqueo-caja/cajas/
POST   /api/arqueo-caja/cajas/
GET    /api/arqueo-caja/cajas/{id}/
PUT    /api/arqueo-caja/cajas/{id}/
PATCH  /api/arqueo-caja/cajas/{id}/
DELETE /api/arqueo-caja/cajas/{id}/

# Acciones custom:
GET    /api/arqueo-caja/cajas/{id}/estado/          # Estado actual de la caja
GET    /api/arqueo-caja/cajas/{id}/historial/       # Historial de aperturas/cierres
```

#### 2. Aperturas
```
GET    /api/arqueo-caja/aperturas/
POST   /api/arqueo-caja/aperturas/
GET    /api/arqueo-caja/aperturas/{id}/
PUT    /api/arqueo-caja/aperturas/{id}/
PATCH  /api/arqueo-caja/aperturas/{id}/

# Acciones custom:
GET    /api/arqueo-caja/aperturas/activas/          # Listar aperturas activas (sin cerrar)
POST   /api/arqueo-caja/aperturas/{id}/anular/      # Anular apertura (solo si no hay movimientos)
GET    /api/arqueo-caja/aperturas/{id}/resumen/     # Resumen de la apertura con movimientos
```

#### 3. Movimientos
```
GET    /api/arqueo-caja/movimientos/
POST   /api/arqueo-caja/movimientos/
GET    /api/arqueo-caja/movimientos/{id}/
PUT    /api/arqueo-caja/movimientos/{id}/
DELETE /api/arqueo-caja/movimientos/{id}/

# Filtros:
GET    /api/arqueo-caja/movimientos/?apertura_caja={id}
GET    /api/arqueo-caja/movimientos/?tipo_movimiento=ingreso
GET    /api/arqueo-caja/movimientos/?metodo_pago=efectivo

# Acciones custom:
GET    /api/arqueo-caja/movimientos/estadisticas/   # Estadísticas por tipo/método
POST   /api/arqueo-caja/movimientos/registrar_venta/  # Crear movimiento desde comprobante
```

#### 4. Cierres
```
GET    /api/arqueo-caja/cierres/
POST   /api/arqueo-caja/cierres/
GET    /api/arqueo-caja/cierres/{id}/
PUT    /api/arqueo-caja/cierres/{id}/

# Acciones custom:
POST   /api/arqueo-caja/cierres/{id}/calcular_totales/  # Recalcular desde movimientos
POST   /api/arqueo-caja/cierres/{id}/registrar_arqueo/ # Registrar conteo físico
POST   /api/arqueo-caja/cierres/{id}/autorizar/        # Autorizar cierre con diferencia
GET    /api/arqueo-caja/cierres/{id}/resumen/          # Resumen detallado
GET    /api/arqueo-caja/cierres/{id}/pdf/              # Descargar PDF del reporte
```

### Ejemplos de Requests/Responses

#### Crear Apertura de Caja
```http
POST /api/arqueo-caja/aperturas/
Content-Type: application/json
Authorization: Bearer {token}

{
  "caja": 1,
  "responsable": 5,
  "monto_inicial": 500000.00,
  "observaciones_apertura": "Apertura turno mañana"
}

Response 201 Created:
{
  "id": 1,
  "codigo_apertura": "APR-2025-0001",
  "caja": {
    "id": 1,
    "nombre": "Caja Principal",
    "numero_caja": 1
  },
  "responsable": {
    "id": 5,
    "nombre": "Juan Pérez",
    "puesto": "Cajero"
  },
  "fecha_hora_apertura": "2025-11-12T08:00:00Z",
  "monto_inicial": "500000.00",
  "esta_abierta": true,
  "observaciones_apertura": "Apertura turno mañana"
}
```

#### Registrar Movimiento (Ingreso)
```http
POST /api/arqueo-caja/movimientos/
Content-Type: application/json
Authorization: Bearer {token}

{
  "apertura_caja": 1,
  "tipo_movimiento": "ingreso",
  "concepto": "venta_efectivo",
  "monto": 250000.00,
  "metodo_pago": "efectivo",
  "referencia": "Factura 001-001-0000123",
  "descripcion": "Venta de paquete turístico a Iguazú",
  "usuario_registro": 5,
  "comprobante": 45
}

Response 201 Created:
{
  "id": 1,
  "numero_movimiento": "MOV-2025-0001",
  "apertura_caja": 1,
  "tipo_movimiento": "ingreso",
  "concepto": "venta_efectivo",
  "concepto_display": "Venta en Efectivo",
  "monto": "250000.00",
  "metodo_pago": "efectivo",
  "metodo_pago_display": "Efectivo",
  "referencia": "Factura 001-001-0000123",
  "descripcion": "Venta de paquete turístico a Iguazú",
  "fecha_hora_movimiento": "2025-11-12T10:30:00Z",
  "usuario_registro": {
    "id": 5,
    "nombre": "Juan Pérez"
  },
  "comprobante": {
    "id": 45,
    "numero_comprobante": "CPG-2025-0045"
  }
}
```

#### Crear Cierre con Arqueo
```http
POST /api/arqueo-caja/cierres/
Content-Type: application/json
Authorization: Bearer {token}

{
  "apertura_caja": 1,
  "saldo_real_efectivo": 780500.00,
  "detalle_billetes": {
    "100000": 5,
    "50000": 4,
    "20000": 9,
    "10000": 0,
    "5000": 1,
    "monedas": 500
  },
  "observaciones_cierre": "Cierre turno mañana",
  "justificacion_diferencia": "Cliente no esperó vuelto de 500"
}

Response 201 Created:
{
  "id": 1,
  "codigo_cierre": "CIE-2025-0001",
  "apertura_caja": {
    "id": 1,
    "codigo_apertura": "APR-2025-0001",
    "caja": "Caja Principal",
    "responsable": "Juan Pérez",
    "monto_inicial": "500000.00"
  },
  "fecha_hora_cierre": "2025-11-12T18:00:00Z",

  "total_efectivo": "1200000.00",
  "total_tarjetas": "600000.00",
  "total_transferencias": "0.00",
  "total_cheques": "0.00",
  "total_otros_ingresos": "0.00",
  "total_egresos": "300000.00",

  "saldo_teorico_efectivo": "780000.00",
  "saldo_teorico_total": "1800000.00",
  "saldo_real_efectivo": "780500.00",

  "diferencia_efectivo": "500.00",
  "diferencia_porcentaje": "0.06",

  "requiere_autorizacion": false,
  "observaciones_cierre": "Cierre turno mañana",
  "justificacion_diferencia": "Cliente no esperó vuelto de 500"
}
```

#### Obtener Resumen de Cierre
```http
GET /api/arqueo-caja/cierres/1/resumen/
Authorization: Bearer {token}

Response 200 OK:
{
  "codigo_cierre": "CIE-2025-0001",
  "caja": "Caja Principal",
  "responsable": "Juan Pérez",
  "fecha_apertura": "12/11/2025 08:00",
  "fecha_cierre": "12/11/2025 18:00",
  "duracion_turno": "10:00:00",

  "monto_inicial": "500000.00",

  "ingresos": {
    "efectivo": "1200000.00",
    "tarjetas": "600000.00",
    "transferencias": "0.00",
    "cheques": "0.00",
    "otros": "0.00",
    "total": "1800000.00"
  },

  "egresos": {
    "total": "300000.00"
  },

  "arqueo": {
    "saldo_teorico": "780000.00",
    "saldo_real": "780500.00",
    "diferencia": "500.00",
    "diferencia_porcentaje": "0.06"
  },

  "requiere_autorizacion": false,
  "observaciones": "Cierre turno mañana"
}
```

---

## Integración con Apps Existentes

### 1. Integración con `comprobante.ComprobantePago`

Cuando se crea un comprobante de pago, automáticamente se debe crear un movimiento de caja.

#### Opción A: Signal en la app comprobante
```python
# apps/comprobante/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ComprobantePago

@receiver(post_save, sender=ComprobantePago)
def crear_movimiento_caja(sender, instance, created, **kwargs):
    """Crear movimiento de caja automáticamente al crear un comprobante"""
    if created:
        from apps.arqueo_caja.models import AperturaCaja, MovimientoCaja

        # Buscar la apertura activa para la caja actual (si existe)
        # Por ahora, asumimos que hay una caja por defecto
        try:
            apertura_activa = AperturaCaja.objects.filter(
                esta_abierta=True,
                activo=True
            ).latest('fecha_hora_apertura')

            # Crear movimiento
            MovimientoCaja.objects.create(
                apertura_caja=apertura_activa,
                comprobante=instance,
                tipo_movimiento='ingreso',
                concepto=f'venta_{instance.metodo_pago}',
                monto=instance.monto,
                metodo_pago=instance.metodo_pago,
                referencia=instance.numero_comprobante,
                descripcion=f"Pago de reserva {instance.reserva.codigo}",
                usuario_registro=instance.empleado
            )
        except AperturaCaja.DoesNotExist:
            # Si no hay caja abierta, no crear movimiento
            pass
```

#### Opción B: Método explícito en el ViewSet de Comprobante
```python
# apps/comprobante/views.py

class ComprobantePagoViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        comprobante = serializer.save()

        # Crear movimiento de caja si hay una caja abierta
        from apps.arqueo_caja.services import registrar_movimiento_desde_comprobante
        registrar_movimiento_desde_comprobante(comprobante)
```

### 2. Integración con `empleado.Empleado`

Los empleados son responsables de:
- Abrir cajas
- Registrar movimientos
- Cerrar cajas
- Autorizar cierres con diferencia

**No requiere cambios en la app empleado**, solo Foreign Keys en arqueo_caja.

### 3. Servicio Reutilizable

```python
# apps/arqueo_caja/services.py

from decimal import Decimal
from .models import AperturaCaja, MovimientoCaja, CierreCaja
from apps.comprobante.models import ComprobantePago

def obtener_caja_abierta_actual():
    """
    Retorna la apertura de caja activa más reciente.
    """
    try:
        return AperturaCaja.objects.filter(
            esta_abierta=True,
            activo=True
        ).select_related('caja', 'responsable').latest('fecha_hora_apertura')
    except AperturaCaja.DoesNotExist:
        return None

def registrar_movimiento_desde_comprobante(comprobante):
    """
    Crea un movimiento de caja a partir de un comprobante de pago.
    """
    apertura = obtener_caja_abierta_actual()

    if not apertura:
        # No hay caja abierta, no registrar
        return None

    # Mapear tipo de comprobante a concepto
    concepto_map = {
        'sena': 'venta_efectivo',
        'pago_parcial': 'venta_efectivo',
        'pago_total': 'venta_efectivo',
        'devolucion': 'devolucion',
    }

    concepto = concepto_map.get(comprobante.tipo, 'venta_efectivo')
    tipo_movimiento = 'egreso' if comprobante.tipo == 'devolucion' else 'ingreso'

    movimiento = MovimientoCaja.objects.create(
        apertura_caja=apertura,
        comprobante=comprobante,
        tipo_movimiento=tipo_movimiento,
        concepto=concepto,
        monto=comprobante.monto,
        metodo_pago=comprobante.metodo_pago,
        referencia=comprobante.numero_comprobante,
        descripcion=f"Pago de reserva {comprobante.reserva.codigo}",
        usuario_registro=comprobante.empleado
    )

    return movimiento

def calcular_saldo_actual_caja(apertura_caja):
    """
    Calcula el saldo actual de una caja basado en sus movimientos.
    """
    from django.db.models import Sum

    movimientos = apertura_caja.movimientos.filter(activo=True)

    total_ingresos = movimientos.filter(
        tipo_movimiento='ingreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    total_egresos = movimientos.filter(
        tipo_movimiento='egreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    saldo = apertura_caja.monto_inicial + total_ingresos - total_egresos

    return {
        'monto_inicial': apertura_caja.monto_inicial,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'saldo_actual': saldo,
    }
```

---

## Flujo de Implementación

### Fase 1: Modelos y Migraciones
```bash
# 1. Crear la app
python manage.py startapp arqueo_caja
# Mover a apps/arqueo_caja/

# 2. Agregar a INSTALLED_APPS en settings.py
INSTALLED_APPS = [
    # ...
    'apps.arqueo_caja',
]

# 3. Crear modelos (Caja, AperturaCaja, MovimientoCaja, CierreCaja)

# 4. Crear migraciones
python manage.py makemigrations arqueo_caja

# 5. Aplicar migraciones
python manage.py migrate
```

### Fase 2: Serializers
```python
# apps/arqueo_caja/serializers.py
- CajaSerializer
- AperturaCajaListSerializer
- AperturaCajaDetailSerializer
- AperturaCajaCreateSerializer
- MovimientoCajaSerializer
- CierreCajaSerializer
- CierreCajaDetailSerializer
```

### Fase 3: ViewSets
```python
# apps/arqueo_caja/views.py
- CajaViewSet
- AperturaCajaViewSet
- MovimientoCajaViewSet
- CierreCajaViewSet
```

### Fase 4: URLs y Routing
```python
# apps/arqueo_caja/urls.py
# apps/api/urls.py (agregar arqueo_caja)
```

### Fase 5: Admin
```python
# apps/arqueo_caja/admin.py
```

### Fase 6: Integración con Comprobantes
```python
# apps/arqueo_caja/services.py
# Crear función: registrar_movimiento_desde_comprobante()
```

### Fase 7: Tests (Opcional pero recomendado)
```python
# apps/arqueo_caja/tests.py
```

---

## Consideraciones de Seguridad

### Permisos
- **Abrir caja**: Solo usuarios con rol "Cajero" o superior
- **Registrar movimientos**: Solo en cajas abiertas por el usuario o por usuarios con permiso
- **Cerrar caja**: Solo el responsable de la apertura o un supervisor
- **Autorizar diferencias**: Solo usuarios con rol "Supervisor" o "Administrador"

### Auditoría
- Todos los modelos tienen campos `fecha_creacion` y `fecha_modificacion`
- Movimientos no se pueden eliminar, solo desactivar (`activo=False`)
- Historial completo de quién abrió, registró y cerró cada caja

### Validaciones
- No permitir movimientos en cajas cerradas
- No permitir montos negativos
- No permitir cerrar una caja sin hacer arqueo
- Diferencias mayores a umbral requieren autorización

---

## Próximos Pasos

1. **Revisar y aprobar este diseño**
2. **Crear los modelos** en `apps/arqueo_caja/models.py`
3. **Ejecutar migraciones**
4. **Crear serializers y vistas**
5. **Configurar URLs**
6. **Integrar con ComprobantePago**
7. **Probar endpoints con Postman**
8. **Generar reportes PDF** (opcional, fase posterior)

---

**Fecha de elaboración**: 12/11/2025
**Versión**: 1.0
**Estado**: Diseño inicial - Pendiente aprobación
