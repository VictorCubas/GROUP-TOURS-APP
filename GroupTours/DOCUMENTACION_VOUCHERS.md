# Sistema de Vouchers - Documentación

## Descripción General

El sistema de vouchers de GroupTours genera vouchers individuales para cada pasajero que completa su pago y tiene sus datos reales cargados. Este documento describe el funcionamiento del sistema actualizado.

## Arquitectura del Sistema

### Modelo de Datos

El modelo `Voucher` está relacionado con `Pasajero` mediante una relación `OneToOneField`:

```python
class Voucher(models.Model):
    pasajero = models.OneToOneField(
        'reserva.Pasajero',
        on_delete=models.PROTECT,
        related_name='voucher'
    )
    codigo_voucher = models.CharField(max_length=50, unique=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='vouchers/qr/', null=True, blank=True)
    pdf_generado = models.FileField(upload_to='vouchers/pdf/', null=True, blank=True)
    instrucciones_especiales = models.TextField(null=True, blank=True)
    contacto_emergencia = models.CharField(max_length=100, default='+595 981 123 456')
    url_publica = models.CharField(max_length=200, null=True, blank=True)
    activo = models.BooleanField(default=True)
```

### Relación con Pasajero

- **Relación**: `OneToOne` - Cada pasajero puede tener máximo un voucher
- **Related name**: `pasajero.voucher` - Acceso al voucher desde el pasajero
- **Protección**: `PROTECT` - No se puede eliminar un pasajero que tiene voucher

## Condiciones para Generación de Vouchers

Un voucher se genera **automáticamente** cuando un pasajero cumple **AMBAS** condiciones:

### 1. Tiene Datos Reales Cargados
```python
pasajero.por_asignar == False
```
- El pasajero NO debe estar marcado como "por asignar"
- Debe tener sus datos personales completos cargados

### 2. Ha Pagado el 100% de su Precio Asignado
```python
pasajero.esta_totalmente_pagado == True
```
- El saldo pendiente del pasajero debe ser $0
- Se calcula como: `precio_asignado - monto_pagado <= 0`

## Generación Automática

### Signal post_save en Pasajero

La generación automática se activa mediante una señal de Django:

**Archivo**: `apps/comprobante/signals.py`

```python
@receiver(post_save, sender=Pasajero)
def crear_voucher_para_pasajero(sender, instance, created, **kwargs):
    """
    Crea automáticamente un voucher cuando el pasajero cumple:
    1. por_asignar=False (datos reales)
    2. esta_totalmente_pagado=True (100% pagado)
    """
    if not instance.por_asignar and instance.esta_totalmente_pagado:
        if not hasattr(instance, 'voucher'):
            voucher = Voucher.objects.create(pasajero=instance)
            voucher.generar_qr()
            voucher.save()
```

### Cuándo se Dispara

La generación de vouchers se dispara cuando:

1. **Se registra un pago** que completa el 100% del precio del pasajero
2. **Se actualiza el pasajero** de "por asignar" a datos reales (y ya tiene pago completo)
3. **Se actualiza el precio asignado** y el monto pagado ya cubre el 100%

## Código del Voucher

### Formato

```
{CODIGO_RESERVA}-PAX-{ID_PASAJERO:03d}-VOUCHER
```

### Ejemplos

- `RSV-2025-0005-PAX-003-VOUCHER` - Pasajero ID 3 de reserva RSV-2025-0005
- `RSV-2025-0180-PAX-299-VOUCHER` - Pasajero ID 299 de reserva RSV-2025-0180

### Generación Automática

El código se genera en el método `save()` del modelo `Voucher`:

```python
def save(self, *args, **kwargs):
    if not self.codigo_voucher and self.pasajero:
        reserva_codigo = self.pasajero.reserva.codigo
        pasajero_id = self.pasajero.id
        self.codigo_voucher = f"{reserva_codigo}-PAX-{pasajero_id:03d}-VOUCHER"
    super().save(*args, **kwargs)
```

## Código QR

### Contenido del QR

El código QR contiene la siguiente información:

```
VOUCHER:{codigo_voucher}|RESERVA:{codigo_reserva}|PASAJERO:{nombre_completo}
```

### Ejemplo

```
VOUCHER:RSV-2025-0005-PAX-003-VOUCHER|RESERVA:RSV-2025-0005|PASAJERO:Andrea Tutoria Escurra
```

### Generación

```python
voucher.generar_qr()  # Genera el QR y lo guarda en voucher.qr_code
```

**Nota**: Requiere la librería `qrcode[pil]` instalada:
```bash
pip install qrcode[pil]
```

## PDF del Voucher

### Generación de PDF

Los vouchers pueden generarse en formato PDF con toda la información completa del viaje.

```python
voucher.generar_pdf()  # Genera el PDF y lo guarda en voucher.pdf_generado
```

### Contenido del PDF

El PDF incluye todas las secciones siguientes:

1. **Encabezado**: Título "VOUCHER DE VIAJE" con líneas decorativas
2. **Información del Voucher**: Código y fecha de emisión con QR code integrado
3. **Información del Pasajero**:
   - Nombre completo (con badge "TITULAR" si aplica)
   - Documento de identidad
   - Email
   - Teléfono
4. **Información de la Reserva**:
   - Código de reserva
   - Estado
   - Fecha de reserva
5. **Información del Paquete**:
   - Nombre del paquete (destacado)
   - Descripción (hasta 3 líneas)
   - Destino
   - Tipo de paquete
   - Modalidad (flexible/fijo)
6. **Información de la Salida**:
   - Fecha de salida
   - Fecha de regreso
   - Duración del viaje (calculada automáticamente)
7. **Alojamiento**:
   - Nombre del hotel
   - Dirección
   - Ciudad
   - Categoría (estrellas)
   - Tipo y número de habitación
   - Capacidad
8. **Servicios Incluidos**: Lista de todos los servicios del paquete (hasta 10)
9. **Información Financiera**:
   - Precio asignado
   - Monto pagado
   - Saldo pendiente (destacado en verde si está pagado, rojo si tiene deuda)
10. **Instrucciones Especiales**: Si las hay
11. **Contacto de Emergencia 24/7**: Número de contacto destacado
12. **Pie de página**: Información del sistema y fecha de generación

### Características del PDF

- **Formato**: A4
- **Diseño**: Profesional con colores corporativos
- **QR Code**: Incluido en la esquina superior derecha (si existe)
- **Estado**: Marca de agua "ANULADO" si el voucher está inactivo
- **Multipágina**: Automático si el contenido es extenso
- **Colores**:
  - Encabezados: #2c3e50 (azul oscuro)
  - Títulos: #3498db (azul)
  - Titular badge: #27ae60 (verde)
  - Saldo pagado: #27ae60 (verde)
  - Saldo pendiente: #e74c3c (rojo)
  - Emergencia: #e74c3c (rojo)

**Nota**: Requiere la librería `reportlab` instalada:
```bash
pip install reportlab
```

## API Endpoints

### Listar Todos los Vouchers

```http
GET /api/vouchers/
```

**Query params opcionales**:
- `reserva_id` - Filtrar por reserva (muestra todos los vouchers de pasajeros de esa reserva)
- `pasajero_id` - Filtrar por pasajero específico
- `activo` - Filtrar por estado (`true`/`false`)

### Obtener Detalle de un Voucher

```http
GET /api/vouchers/{id}/
```

### Vouchers de una Reserva Específica

```http
GET /api/reservas/{reserva_id}/vouchers/
```

**Respuesta cuando existen vouchers**:
```json
{
  "count": 3,
  "vouchers": [
    {
      "id": 1,
      "codigo_voucher": "RSV-2025-0005-PAX-003-VOUCHER",
      "pasajero_id": 3,
      "pasajero_nombre": "Andrea",
      "pasajero_apellido": "Escurra",
      "pasajero_documento": "1234567",
      "es_titular": true,
      "reserva_codigo": "RSV-2025-0005",
      "paquete_nombre": "Tour a Buenos Aires",
      "fecha_salida": "2025-12-15",
      "fecha_regreso": "2025-12-20",
      "hotel_nombre": "Hotel Plaza",
      "habitacion_numero": "101",
      "habitacion_tipo": "Doble",
      "precio_asignado": "2000.00",
      "monto_pagado": "2000.00",
      "fecha_emision": "2025-10-30T22:15:00Z",
      "qr_code": "/media/vouchers/qr/voucher_RSV-2025-0005-PAX-003-VOUCHER.png",
      "activo": true
    }
  ]
}
```

**Respuesta cuando NO existen vouchers**:
```json
{
  "message": "Esta reserva no tiene vouchers generados aún",
  "info": "Los vouchers se generan automáticamente cuando cada pasajero tiene datos reales y paga el 100%"
}
```

### Regenerar Código QR

```http
POST /api/vouchers/{id}/regenerar_qr/
```

### Descargar PDF del Voucher

```http
GET /api/vouchers/{id}/descargar-pdf/
GET /api/vouchers/{id}/descargar-pdf/?regenerar=true
```

**Query params opcionales**:
- `regenerar=true` - Fuerza la regeneración del PDF incluso si ya existe

**Respuesta**:
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="voucher_RSV-2025-0005-PAX-003-VOUCHER.pdf"`
- Descarga directa del archivo PDF

**Comportamiento**:
1. Si el PDF ya existe, lo retorna inmediatamente
2. Si no existe, lo genera automáticamente y luego lo retorna
3. Si `regenerar=true`, regenera el PDF sin importar si existe
4. Si el archivo físico fue eliminado, lo regenera automáticamente

## Flujo de Generación de Vouchers

### Escenario 1: Pago Completo Primero

1. Usuario crea reserva con pasajeros "por asignar" (por_asignar=True)
2. Usuario registra pago del 100% para un pasajero "por asignar"
3. Usuario actualiza los datos del pasajero (por_asignar → False)
4. ✅ **Signal dispara**: Se genera el voucher automáticamente

### Escenario 2: Datos Reales Primero

1. Usuario crea reserva con pasajeros con datos reales (por_asignar=False)
2. Usuario registra pagos parciales (50%, 75%, etc.)
3. Usuario registra el último pago que completa el 100%
4. ✅ **Signal dispara**: Se genera el voucher automáticamente

### Escenario 3: Ambos al Mismo Tiempo

1. Usuario crea pasajero con datos reales y registra pago del 100% al mismo tiempo
2. ✅ **Signal dispara**: Se genera el voucher automáticamente

## Migración de Datos

### Vouchers Legacy (Por Reserva)

Los vouchers antiguos que estaban asociados a reservas (no a pasajeros individuales) fueron:

1. **Desactivados** (`activo=False`) durante la migración `0003_migrar_vouchers_a_pasajeros`
2. Permanecen en la base de datos como registro histórico
3. Ya no se utilizan en el sistema actual

### Script de Generación Masiva

Para generar vouchers de pasajeros existentes que ya cumplen las condiciones:

```bash
python generar_vouchers_existentes.py
```

Este script:
- Busca todos los pasajeros con `por_asignar=False`
- Verifica si tienen `esta_totalmente_pagado=True`
- Genera vouchers para los que cumplan ambas condiciones
- Actualiza el campo `pasajero.voucher_codigo` para referencia rápida

## Campos del Pasajero

El modelo `Pasajero` tiene un campo de referencia rápida:

```python
class Pasajero(models.Model):
    voucher_codigo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Código de voucher asignado (si aplica)"
    )
```

Este campo se actualiza automáticamente cuando se genera el voucher.

## Verificación de Estado

### Desde el Pasajero

```python
# Verificar si un pasajero tiene voucher
if hasattr(pasajero, 'voucher'):
    print(f"Voucher: {pasajero.voucher.codigo_voucher}")
else:
    print("Sin voucher generado")

# Verificar si puede tener voucher
puede_tener = not pasajero.por_asignar and pasajero.esta_totalmente_pagado
```

### Desde la Reserva

```python
# Obtener todos los vouchers de una reserva
vouchers = Voucher.objects.filter(pasajero__reserva=reserva)

# Contar pasajeros con voucher vs total
pasajeros_totales = reserva.pasajeros.filter(por_asignar=False).count()
vouchers_generados = vouchers.count()
porcentaje = (vouchers_generados / pasajeros_totales * 100) if pasajeros_totales > 0 else 0
```

## Panel de Administración

### Listado de Vouchers

En el panel de administración (`/admin/comprobante/voucher/`):

- **Columnas mostradas**: Código, Pasajero, Reserva, Es Titular, Fecha Emisión, Activo
- **Filtros**: Activo, Fecha de Emisión, Es Titular
- **Búsqueda**: Por código de voucher, código de reserva, nombre/apellido del pasajero

### Acciones Masivas

- **Generar códigos QR**: Regenera los códigos QR de los vouchers seleccionados

## Consideraciones Importantes

### 1. No se Pueden Crear Vouchers Manualmente

Los vouchers solo deben crearse automáticamente mediante la señal. Crear vouchers manualmente puede causar inconsistencias.

### 2. Un Pasajero = Un Voucher

La relación OneToOne garantiza que cada pasajero tenga máximo un voucher. Si se intenta crear un segundo voucher para el mismo pasajero, se lanzará un error de integridad.

### 3. Protección de Datos

No se puede eliminar un pasajero que tiene un voucher generado (relación PROTECT). Primero se debe eliminar el voucher.

### 4. Vouchers Inactivos

Si un voucher necesita ser invalidado:
```python
voucher.activo = False
voucher.save()
```

Los vouchers inactivos permanecen en la base de datos pero se pueden filtrar en las consultas.

## Ejemplo Completo de Uso

```python
from apps.reserva.models import Reserva, Pasajero
from apps.persona.models import PersonaFisica
from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion

# 1. Crear reserva
reserva = Reserva.objects.get(codigo="RSV-2025-0180")

# 2. Crear pasajero con datos reales
persona = PersonaFisica.objects.create(
    nombre="Juan",
    apellido="Pérez",
    documento="12345678",
    fecha_nacimiento="1990-01-01"
)

pasajero = Pasajero.objects.create(
    reserva=reserva,
    persona=persona,
    es_titular=True,
    por_asignar=False,  # Datos reales
    precio_asignado=2000.00
)

# 3. Registrar pago del 100%
comprobante = ComprobantePago.objects.create(
    reserva=reserva,
    tipo='pago_total',
    monto=2000.00,
    metodo_pago='transferencia',
    empleado=empleado
)

ComprobantePagoDistribucion.objects.create(
    comprobante=comprobante,
    pasajero=pasajero,
    monto=2000.00
)

# El comprobante actualiza el monto_pagado de la reserva y el estado
comprobante.actualizar_monto_reserva()

# 4. ✅ El voucher se genera automáticamente vía signal
# Verificar:
if hasattr(pasajero, 'voucher'):
    print(f"Voucher generado: {pasajero.voucher.codigo_voucher}")
    print(f"QR disponible: {bool(pasajero.voucher.qr_code)}")
```

## Solución de Problemas

### El voucher no se generó automáticamente

**Verificar**:
1. ¿El pasajero tiene `por_asignar=False`?
2. ¿El pasajero tiene `esta_totalmente_pagado=True`?
3. ¿Las señales están habilitadas en la app?
4. ¿Ya existe un voucher para este pasajero?

### Error al generar QR

**Solución**: Instalar la librería qrcode
```bash
pip install qrcode[pil]
```

### Voucher con datos incorrectos

**No editar** el voucher manualmente. En su lugar:
1. Desactivar el voucher actual: `voucher.activo = False; voucher.save()`
2. Corregir los datos del pasajero
3. El sistema generará un nuevo voucher automáticamente si cumple las condiciones

## Resumen

El sistema de vouchers individuales por pasajero permite:

- ✅ Control granular del estado de pago de cada pasajero
- ✅ Generación automática cuando se cumplen las condiciones
- ✅ Trazabilidad completa del proceso de pago
- ✅ Vouchers individuales con QR único por pasajero
- ✅ Compatibilidad con el sistema de comprobantes y distribuciones de pago
- ✅ API REST completa para integración con frontend
