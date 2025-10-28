# API para Obtener Detalles de Reservas

Este documento describe los servicios y endpoints disponibles para obtener información detallada de reservas.

## ⚠️ Campos Disponibles por Modelo

### Paquete
- ✅ nombre
- ✅ tipo_paquete (id, nombre)
- ✅ destino (id, ciudad, país)
- ✅ moneda (id, nombre, símbolo, código)
- ✅ modalidad (flexible/fijo)
- ✅ propio
- ✅ personalizado
- ✅ cantidad_pasajeros
- ✅ distribuidora (id, nombre)
- ✅ imagen (URL)
- ❌ descripcion (no existe en el modelo)

### SalidaPaquete
- ✅ fecha_salida, fecha_regreso
- ✅ precio_actual, precio_final
- ✅ precio_venta_sugerido_min, precio_venta_sugerido_max
- ✅ senia, cupo
- ✅ ganancia, comision
- ✅ temporada (id, nombre, fecha_inicio, fecha_fin)
- ✅ moneda (id, nombre, símbolo, código)
- ❌ observaciones (no existe en el modelo)

### Hotel
- ✅ nombre, direccion, descripcion
- ✅ estrellas
- ✅ cadena (id, nombre)
- ✅ ciudad (id, nombre)
- ❌ telefono, email (no existen en el modelo)

### Habitacion
- ✅ numero, tipo, tipo_display
- ✅ capacidad, precio_noche
- ✅ moneda (id, nombre, símbolo, código)
- ❌ descripcion (no existe en el modelo)

### PaqueteServicio
- ✅ servicio (id, nombre, descripcion, tipo)
- ✅ precio
- ❌ incluido, observaciones, activo (no existen en el modelo)

## Endpoints Disponibles

### 1. GET /api/reservas/{id}/

**Descripción**: Obtiene todos los detalles completos de una reserva (endpoint estándar de Django REST).

**Serializer utilizado**: `ReservaDetalleSerializer`

**Respuesta**: Incluye toda la información de la reserva:
- Información del titular (nombre, documento, email, teléfono)
- Información completa del paquete (nombre, descripción, tipo, destino, moneda, modalidad, imagen)
- Información de la salida (fechas, precios, seña, cupo, ganancia/comisión, temporada)
- Información del hotel y habitación seleccionados
- Lista completa de pasajeros con sus datos de pago (monto pagado, saldo pendiente, porcentajes)
- Servicios base incluidos en el paquete
- Servicios adicionales contratados
- Historial completo de comprobantes de pago con distribuciones
- Cálculos de costos (precio base, servicios adicionales, total, seña, saldo pendiente)
- Estado de la reserva y validaciones

**Ejemplo de uso**:
```bash
GET /api/reservas/1/
```

**Optimización**: Este endpoint precarga todas las relaciones necesarias para minimizar consultas a la base de datos.

---

### 2. GET /api/reservas/{id}/detalle-resumen/

**Descripción**: Obtiene un resumen simplificado de la reserva con datos clave.

**Servicio utilizado**: `obtener_resumen_reserva()`

**Ideal para**: Dashboards, listados, vistas previas.

**Respuesta incluye**:
- Código y estado de la reserva
- Información básica del titular
- Nombre del paquete y destino
- Fechas de salida y regreso
- Cantidad de pasajeros
- Resumen de costos (precio unitario, total, pagado, saldo, seña)
- Validaciones (puede confirmarse, está totalmente pagada, datos completos)

**Ejemplo de uso**:
```bash
GET /api/reservas/1/detalle-resumen/
```

**Respuesta ejemplo**:
```json
{
    "id": 1,
    "codigo": "RSV-2025-0001",
    "estado": "confirmada",
    "estado_display": "Confirmado Completo",
    "fecha_reserva": "2025-10-15T10:30:00Z",
    "titular": {
        "id": 5,
        "nombre_completo": "Juan Pérez",
        "documento": "12345678",
        "email": "juan@example.com",
        "telefono": "0981123456"
    },
    "paquete": {
        "id": 3,
        "nombre": "Tour a Encarnación",
        "destino": {
            "ciudad": "Encarnación",
            "pais": "Paraguay"
        }
    },
    "fechas": {
        "salida": "2025-12-01",
        "regreso": "2025-12-05"
    },
    "cantidad_pasajeros": 2,
    "costos": {
        "precio_unitario": 3536.0,
        "costo_total": 7072.0,
        "monto_pagado": 420.0,
        "saldo_pendiente": 6652.0,
        "seña_total": 420.0,
        "moneda": {
            "simbolo": "Gs.",
            "codigo": "PYG"
        }
    },
    "validaciones": {
        "puede_confirmarse": true,
        "esta_totalmente_pagada": false,
        "datos_completos": true
    }
}
```

---

### 3. GET /api/reservas/{id}/detalle-pasajeros/

**Descripción**: Obtiene solo la lista de pasajeros con información detallada de pagos.

**Servicio utilizado**: `obtener_pasajeros_reserva()`

**Ideal para**: Módulos de gestión de pasajeros, seguimiento de pagos por persona.

**Respuesta incluye** (por cada pasajero):
- ID y datos personales
- Si es titular
- Precio asignado
- Monto pagado y saldo pendiente
- Porcentaje pagado
- Seña requerida y si está pagada
- Tickets y vouchers

**Ejemplo de uso**:
```bash
GET /api/reservas/1/detalle-pasajeros/
```

---

### 4. GET /api/reservas/{id}/detalle-comprobantes/

**Descripción**: Obtiene todos los comprobantes de pago de una reserva.

**Servicio utilizado**: `obtener_comprobantes_reserva()`

**Ideal para**: Módulos de caja, historial de pagos, auditoría.

**Respuesta incluye** (por cada comprobante):
- Número de comprobante
- Fecha de pago
- Tipo (seña, pago parcial, pago total)
- Método de pago
- Monto total
- Distribuciones por pasajero
- Empleado que registró el pago
- URL del PDF (si existe)

**Ejemplo de uso**:
```bash
GET /api/reservas/1/detalle-comprobantes/
```

---

### 5. GET /api/reservas/{id}/detalle-servicios/

**Descripción**: Obtiene todos los servicios (base y adicionales) de una reserva.

**Servicio utilizado**: `obtener_servicios_reserva()`

**Ideal para**: Módulos de gestión de servicios, cálculos de costos.

**Respuesta incluye**:
- Servicios base incluidos en el paquete
- Servicios adicionales contratados
- Costo total de servicios adicionales

**Ejemplo de uso**:
```bash
GET /api/reservas/1/detalle-servicios/
```

---

## Servicios Python (Backend)

Además de los endpoints REST, también están disponibles las siguientes funciones de servicio que pueden ser utilizadas directamente en el código Python:

### `obtener_detalle_reserva(reserva_id)`

Obtiene una instancia de Reserva con todas sus relaciones precargadas.

```python
from apps.reserva.services import obtener_detalle_reserva

reserva = obtener_detalle_reserva(1)
print(reserva.codigo)  # RSV-2025-0001
print(reserva.paquete.nombre)  # Tour a Encarnación
```

### `obtener_resumen_reserva(reserva_id)`

Obtiene un diccionario con resumen de la reserva.

```python
from apps.reserva.services import obtener_resumen_reserva

resumen = obtener_resumen_reserva(1)
print(resumen['codigo'])  # RSV-2025-0001
print(resumen['estado'])  # confirmada
```

### `obtener_pasajeros_reserva(reserva_id)`

Obtiene lista de diccionarios con información de pasajeros.

```python
from apps.reserva.services import obtener_pasajeros_reserva

pasajeros = obtener_pasajeros_reserva(1)
for pasajero in pasajeros:
    print(f"{pasajero['persona']['nombre_completo']}: ${pasajero['monto_pagado']}")
```

### `obtener_comprobantes_reserva(reserva_id)`

Obtiene lista de diccionarios con comprobantes de pago.

```python
from apps.reserva.services import obtener_comprobantes_reserva

comprobantes = obtener_comprobantes_reserva(1)
for comp in comprobantes:
    print(f"{comp['numero_comprobante']}: ${comp['monto']}")
```

### `obtener_servicios_reserva(reserva_id)`

Obtiene diccionario con servicios base y adicionales.

```python
from apps.reserva.services import obtener_servicios_reserva

servicios = obtener_servicios_reserva(1)
print(f"Servicios base: {len(servicios['servicios_base'])}")
print(f"Servicios adicionales: {len(servicios['servicios_adicionales'])}")
print(f"Costo adicional: ${servicios['costo_servicios_adicionales']}")
```

---

## Manejo de Errores

Todos los endpoints y servicios manejan los siguientes errores:

1. **Reserva no encontrada** (404):
```json
{
    "error": "No existe una reserva con ID {id}"
}
```

2. **Error del servidor** (500):
```json
{
    "error": "Error al obtener [tipo de datos]: {mensaje de error}"
}
```

---

## Optimización de Queries

El endpoint principal (`GET /api/reservas/{id}/`) y todos los servicios utilizan `select_related` y `prefetch_related` para minimizar el número de consultas a la base de datos. Esto mejora significativamente el rendimiento al obtener información completa de una reserva.

**Relaciones precargadas**:
- Titular
- Paquete (con tipo, destino, moneda, distribuidora)
- Salida (con temporada)
- Habitación (con hotel, cadena, ciudad)
- Pasajeros (con persona y distribuciones de pago)
- Servicios (base y adicionales)
- Comprobantes (con empleado y distribuciones)

---

## Ubicación de Archivos

- **Serializer**: `apps/reserva/serializers.py` - `ReservaDetalleSerializer`
- **Views**: `apps/reserva/views.py` - `ReservaViewSet`
- **Servicios**: `apps/reserva/services.py`
- **Modelos**: `apps/reserva/models.py`

---

## Ejemplos de Uso en Frontend

### React/JavaScript

```javascript
// Obtener detalle completo
const response = await fetch('/api/reservas/1/');
const reserva = await response.json();

// Obtener solo resumen
const resumenResponse = await fetch('/api/reservas/1/detalle-resumen/');
const resumen = await resumenResponse.json();

// Obtener solo pasajeros
const pasajerosResponse = await fetch('/api/reservas/1/detalle-pasajeros/');
const pasajeros = await pasajerosResponse.json();

// Obtener solo comprobantes
const comprobantesResponse = await fetch('/api/reservas/1/detalle-comprobantes/');
const comprobantes = await comprobantesResponse.json();

// Obtener solo servicios
const serviciosResponse = await fetch('/api/reservas/1/detalle-servicios/');
const servicios = await serviciosResponse.json();
```

### Python/Requests

```python
import requests

# Obtener detalle completo
response = requests.get('http://localhost:8000/api/reservas/1/')
reserva = response.json()

# Obtener solo resumen
response = requests.get('http://localhost:8000/api/reservas/1/detalle-resumen/')
resumen = response.json()
```

---

## Notas Adicionales

1. **Autenticación**: Actualmente los endpoints no requieren autenticación (`permission_classes = []`). Ajustar según necesidades de seguridad.

2. **Paginación**: El endpoint de listado (`GET /api/reservas/`) está paginado, pero los endpoints de detalle no.

3. **Filtros**: El endpoint de listado soporta filtros a través de `ReservaFilter`.

4. **Formato de respuesta**: Todos los endpoints retornan JSON.

5. **Campos calculados**: Los costos y estados son calculados dinámicamente desde el modelo `Reserva`.
