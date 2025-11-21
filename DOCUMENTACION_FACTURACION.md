# Sistema de Facturación - Documentación

## Descripción General

Sistema de facturación electrónica integrado con el módulo de reservas, diseñado para simular la emisión de facturas según normativas paraguayas. El sistema está preparado para futuras integraciones con el sistema de la SET (Subsecretaría de Estado de Tributación).

---

## Diagrama de Relaciones del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SISTEMA DE FACTURACIÓN                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   Empresa    │ (1) - Solo una empresa en el sistema
│              │
│ - ruc        │
│ - nombre     │
│ - direccion  │
│ - telefono   │
│ - correo     │
└──────┬───────┘
       │
       │ (1:N)
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌──────────────┐   ┌──────────────┐
│Establecimiento│   │  Timbrado   │
│              │   │              │
│- codigo (001)│   │- numero      │
│- nombre      │   │- inicio_vig  │
│- direccion   │   │- fin_vig     │
└──────┬───────┘   └──────────────┘
       │
       │ (1:N)
       │
       ▼
┌──────────────────┐
│ PuntoExpedicion  │
│                  │
│ - codigo (001)   │
│ - nombre         │
│ - descripcion    │
└──────────────────┘


┌──────────────────┐
│  TipoImpuesto    │ (Ej: IVA, IRP, ISC)
│                  │
│ - nombre         │
│ - descripcion    │
└──────┬───────────┘
       │
       │ (1:N)
       │
       ▼
┌──────────────────┐
│SubtipoImpuesto   │ (Ej: IVA 10%, IVA 5%, IVA 0%)
│                  │
│ - nombre         │
│ - porcentaje     │
└──────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                    FacturaElectronica                               │
│                  (Dual Purpose Model)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  es_configuracion = True         │   es_configuracion = False      │
│  ────────────────────────        │   ──────────────────────        │
│  CONFIGURACIÓN BASE              │   FACTURA REAL                  │
│                                  │                                 │
│  ✓ Empresa (FK)                  │   ✓ Empresa (FK)                │
│  ✓ Establecimiento (FK)          │   ✓ Establecimiento (FK)        │
│  ✗ PuntoExpedicion (null)        │   ✓ PuntoExpedicion (FK) ✱      │
│  ✓ Timbrado (FK)                 │   ✓ Timbrado (FK)               │
│  ✓ TipoImpuesto (FK)             │   ✓ TipoImpuesto (FK)           │
│  ✓ SubtipoImpuesto (FK)          │   ✓ SubtipoImpuesto (FK)        │
│  ✗ Reserva (null)                │   ✓ Reserva (FK) ✱              │
│  ✗ numero_factura (null)         │   ✓ numero_factura (auto) ✱     │
│  ✗ fecha_emision (null)          │   ✓ fecha_emision (auto) ✱      │
│  ✗ cliente_* (null)              │   ✓ cliente_* (del titular) ✱   │
│  ✗ totales (0)                   │   ✓ totales (calculados) ✱      │
│  ✗ detalles                      │   ✓ detalles (N) ✱              │
│                                  │                                 │
└──────────────────────────────────┴─────────────┬───────────────────┘
                                                  │
                                                  │ (1:N)
                                                  │
                                        ┌─────────▼─────────────┐
                                        │  DetalleFactura       │
                                        │                       │
                                        │ - numero_item         │
                                        │ - descripcion         │
                                        │ - cantidad            │
                                        │ - precio_unitario     │
                                        │ - monto_exenta        │
                                        │ - monto_gravada_5     │
                                        │ - monto_gravada_10    │
                                        │ - subtotal (auto)     │
                                        └───────────────────────┘


┌──────────────────────────────────────────────────────────────────┐
│                   Módulo de Reservas                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐          ┌──────────────────┐                 │
│  │   Reserva    │◄─────────│  PersonaFisica   │                 │
│  │              │  titular │   (Titular)      │                 │
│  │- codigo      │          │                  │                 │
│  │- estado      │          │- nombre          │                 │
│  │- paquete     │          │- apellido        │                 │
│  │- cantidad    │          │- ci_numero       │                 │
│  │- precio_unit │          │- direccion       │                 │
│  │- monto_pagado│          │- telefono        │                 │
│  └──────┬───────┘          └──────────────────┘                 │
│         │                                                        │
│         │ (1:N)                                                  │
│         │                                                        │
│         └─────────────► FacturaElectronica                       │
│                         (es_configuracion=False)                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

✱ = Campos requeridos solo para facturas reales

Leyenda:
─────────
(1)   = Uno
(N)   = Muchos
(FK)  = Foreign Key (Clave Foránea)
(auto)= Generado automáticamente
```

---

## Diagrama de Flujo de Generación de Factura

```
                    ┌─────────────────────────┐
                    │  Usuario/Sistema        │
                    │  solicita generar       │
                    │  factura para Reserva   │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ POST /api/facturacion/  │
                    │ generar-factura/{id}/   │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Validar estado reserva  │
                    │ ¿confirmada/finalizada? │
                    └───────────┬─────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                     NO │               │ SÍ
                        ▼               ▼
            ┌──────────────────┐   ┌──────────────────┐
            │ Error 400:       │   │ Verificar si ya  │
            │ "Debe estar      │   │ tiene factura    │
            │ confirmada..."   │   └────────┬─────────┘
            └──────────────────┘            │
                                    ┌───────┴───────┐
                                    │               │
                                 SÍ │               │ NO
                                    ▼               ▼
                        ┌──────────────────┐   ┌──────────────────┐
                        │ Error 400:       │   │ Obtener config   │
                        │ "Ya tiene        │   │ de facturación   │
                        │ factura"         │   │ (es_config=True) │
                        └──────────────────┘   └────────┬─────────┘
                                                        │
                                                        ▼
                                            ┌──────────────────┐
                                            │ ¿Existe config?  │
                                            └────────┬─────────┘
                                                     │
                                            ┌────────┴────────┐
                                            │                 │
                                         NO │                 │ SÍ
                                            ▼                 ▼
                                ┌──────────────────┐   ┌──────────────────┐
                                │ Error 400:       │   │ Obtener punto    │
                                │ "No existe       │   │ expedición activo│
                                │ configuración"   │   └────────┬─────────┘
                                └──────────────────┘            │
                                                                ▼
                                                    ┌──────────────────┐
                                                    │ Extraer datos    │
                                                    │ del titular      │
                                                    └────────┬─────────┘
                                                             │
                                                             ▼
                                        ┌────────────────────────────────────┐
                                        │ TRANSACCIÓN ATÓMICA INICIA         │
                                        └────────────────────────────────────┘
                                                             │
                                                             ▼
                                        ┌────────────────────────────────────┐
                                        │ Crear FacturaElectronica           │
                                        │ - es_configuracion = False         │
                                        │ - fecha_emision = now()            │
                                        │ - cliente_* = datos del titular    │
                                        │ - moneda = moneda del paquete      │
                                        └────────────┬───────────────────────┘
                                                     │
                                                     ▼
                                        ┌────────────────────────────────────┐
                                        │ save() genera numero_factura       │
                                        │ Formato: 001-001-0000001           │
                                        └────────────┬───────────────────────┘
                                                     │
                                                     ▼
                                        ┌────────────────────────────────────┐
                                        │ Crear DetalleFactura #1            │
                                        │ - Paquete Turístico                │
                                        │ - cantidad = pasajeros             │
                                        │ - precio = precio_unitario         │
                                        │ - desglose IVA según porcentaje    │
                                        └────────────┬───────────────────────┘
                                                     │
                                                     ▼
                                        ┌────────────────────────────────────┐
                                        │ ¿Tiene servicios adicionales?      │
                                        └────────────┬───────────────────────┘
                                                     │
                                            ┌────────┴────────┐
                                            │                 │
                                         SÍ │                 │ NO
                                            ▼                 ▼
                            ┌──────────────────────┐     ┌────────────────┐
                            │ Para cada servicio:  │     │                │
                            │ Crear DetalleFactura │     │    (continuar) │
                            │ #2, #3, #4...        │     │                │
                            └──────────┬───────────┘     └────────┬───────┘
                                       │                          │
                                       └──────────┬───────────────┘
                                                  │
                                                  ▼
                                    ┌──────────────────────────────┐
                                    │ factura.calcular_totales()   │
                                    │ - Suma monto_exenta          │
                                    │ - Suma monto_gravada_5       │
                                    │ - Suma monto_gravada_10      │
                                    │ - Calcula IVA 5%             │
                                    │ - Calcula IVA 10%            │
                                    │ - Calcula total general      │
                                    └──────────────┬───────────────┘
                                                   │
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │ TRANSACCIÓN COMMIT           │
                                    │ Guardar todos los cambios    │
                                    └──────────────┬───────────────┘
                                                   │
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │ Response 201 Created         │
                                    │ {                            │
                                    │   "mensaje": "Factura        │
                                    │   generada exitosamente",    │
                                    │   "factura": {...}           │
                                    │ }                            │
                                    └──────────────────────────────┘


Cálculo de IVA:
───────────────
  Base Gravada incluye IVA

  IVA 5%:  base_gravada_5% × (5/105)  = IVA extraído
  IVA 10%: base_gravada_10% × (10/110) = IVA extraído

  Total = exenta + gravada_5% + gravada_10%
```

---

## Flujo de Configuración Inicial

```
                        ┌────────────────────┐
                        │  SETUP INICIAL     │
                        │  (Una sola vez)    │
                        └──────────┬─────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │ 1. Crear Empresa │  │ 2. Crear         │  │ 3. Crear         │
    │    (única)       │  │    Establecimiento│  │    Timbrado      │
    │                  │  │    y Punto       │  │                  │
    │ - RUC            │  │    Expedición    │  │ - Número         │
    │ - Nombre         │  │                  │  │ - Vigencias      │
    │ - Dirección      │  │ - Código (001)   │  │                  │
    └──────────────────┘  └──────────────────┘  └──────────────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ 4. Crear TipoImpuesto│
                        │    y Subtipos        │
                        │                      │
                        │ IVA:                 │
                        │  - IVA 0% (exenta)   │
                        │  - IVA 5%            │
                        │  - IVA 10%           │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ 5. Guardar Config    │
                        │    de Facturación    │
                        │                      │
                        │ POST /api/facturacion│
                        │ /guardar-config/     │
                        │                      │
                        │ Crea registro con:   │
                        │ es_configuracion=True│
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ SISTEMA LISTO PARA   │
                        │ GENERAR FACTURAS     │
                        └──────────────────────┘
```

---

## Estado de Reserva y Facturación

```
    ESTADOS DE RESERVA
    ──────────────────

    ┌─────────────┐
    │  pendiente  │  ← Reserva creada, sin pago
    └──────┬──────┘
           │ (pago de seña)
           ▼
    ┌─────────────┐
    │ confirmada  │  ✓ Puede facturarse
    └──────┬──────┘
           │ (completar datos)
           ▼
    ┌─────────────┐
    │ finalizada  │  ✓ Puede facturarse
    └──────┬──────┘
           │
           │
           ▼
    ┌─────────────┐
    │  cancelada  │  ✗ No puede facturarse
    └─────────────┘


    PROCESO DE FACTURACIÓN
    ──────────────────────

    Reserva              Factura           Admin
    ─────────            ─────────         ─────────

    confirmada  ─────►  Generar   ─────►  Ver en
       o                Factura           Django Admin
    finalizada          (POST API)
                            │
                            ▼
                        Número auto:
                        001-001-0000001
                            │
                            ▼
                        Detalles:
                        - Paquete
                        - Servicios
                            │
                            ▼
                        Totales:
                        - Calculados
                        - IVA
                            │
                            ▼
                        Estado:
                        ✓ Facturada
```

---

## Modelo Entidad-Relación (ERD)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ENTIDAD-RELACIÓN                                 │
└─────────────────────────────────────────────────────────────────────────┘

 Empresa ──────┬───── tiene muchos ──────► Establecimiento
    │          │
    │          └───── tiene muchos ──────► Timbrado
    │
    └────────────── tiene muchos ──────► FacturaElectronica
                                                    │
                                                    │
 Establecimiento ─── tiene muchos ──────► PuntoExpedicion
                                                    │
                                                    │
 TipoImpuesto ──── tiene muchos ──────► SubtipoImpuesto
                                                    │
                                                    │
                            ┌───────────────────────┘
                            │
                            ▼
                    FacturaElectronica ──────┬──── pertenece a ───► Empresa
                            │                │
                            │                ├──── pertenece a ───► Establecimiento
                            │                │
                            │                ├──── pertenece a ───► PuntoExpedicion
                            │                │
                            │                ├──── pertenece a ───► Timbrado
                            │                │
                            │                ├──── pertenece a ───► TipoImpuesto
                            │                │
                            │                ├──── pertenece a ───► SubtipoImpuesto
                            │                │
                            │                ├──── vinculada a ───► Reserva (opcional)
                            │                │
                            │                └──── usa ───────────► Moneda (opcional)
                            │
                            └──── tiene muchos ──────► DetalleFactura


 Reserva ──────┬──── tiene un ──────► PersonaFisica (Titular)
               │
               ├──── pertenece a ───► Paquete
               │
               ├──── tiene una (0..1) ─► FacturaElectronica
               │
               └──── tiene muchos ───► ServicioAdicional


Cardinalidades:
───────────────
1      = Exactamente uno
0..1   = Cero o uno (opcional)
1..*   = Uno o muchos
0..*   = Cero o muchos

Restricciones:
──────────────
- Solo puede existir UNA Empresa en el sistema
- FacturaElectronica.numero_factura es UNIQUE por (establecimiento, punto_expedicion)
- Si es_configuracion=True, entonces punto_expedicion=NULL y numero_factura=NULL
- Si es_configuracion=False, entonces punto_expedicion es REQUERIDO
- Una Reserva puede tener máximo UNA factura
```

## Componentes Implementados

### 1. Modelos de Datos

#### **TipoImpuesto y SubtipoImpuesto**
- Manejo jerárquico de tipos de impuestos (IVA, IRP, ISC)
- Subtipos con porcentajes específicos (IVA 10%, 5%, 0%)

#### **Empresa**
- Solo puede existir UNA empresa en el sistema (validación automática)
- Datos: RUC, nombre, dirección, teléfono, correo, actividades

#### **Establecimiento**
- Múltiples establecimientos por empresa
- Código de 3 dígitos (ej: "001")

#### **PuntoExpedicion**
- Múltiples puntos de expedición por establecimiento
- Código de 3 dígitos (ej: "001")

#### **Timbrado**
- Número de timbrado con fechas de vigencia
- Vinculado a la empresa

#### **FacturaElectronica**
- **Dual purpose**: Puede ser configuración (`es_configuracion=True`) o factura real (`es_configuracion=False`)
- Generación automática de número de factura: `XXX-XXX-XXXXXXX` (establecimiento-punto-correlativo)
- Relación con Reserva
- Datos del cliente (tipo documento, número, nombre, dirección, etc.)
- Totales calculados automáticamente
- Campos de moneda y condición de venta

#### **DetalleFactura**
- Ítems/líneas de la factura
- Desglose por tipo de gravamen (exenta, IVA 5%, IVA 10%)
- Cálculo automático de subtotales

### 2. Funcionalidad de Generación

#### **Función `generar_factura_desde_reserva()`**

Genera automáticamente una factura a partir de una reserva. Incluye:

- ✅ Validaciones de estado de reserva (debe estar confirmada o finalizada)
- ✅ Validación de factura única por reserva
- ✅ Extracción de datos del titular como cliente
- ✅ Creación de detalles de factura:
  - Paquete turístico
  - Servicios adicionales (si los hay)
- ✅ Cálculo automático de totales e impuestos
- ✅ Transacción atómica (todo o nada)

**Cálculo de IVA:**
```python
# La base gravada incluye el IVA
IVA 5%  = base_gravada_5% * 5/105
IVA 10% = base_gravada_10% * 10/110
Total   = exenta + gravada_5% + gravada_10%
```

## API Endpoints

### Configuración

#### `GET /api/facturacion/empresa/`
Obtiene la información de la empresa única del sistema.

#### `GET /api/facturacion/establecimientos/todos/`
Lista todos los establecimientos activos.

#### `GET /api/facturacion/puntos-expedicion/todos/`
Lista todos los puntos de expedición activos.

#### `GET /api/facturacion/tipos-impuesto/todos/`
Lista todos los tipos de impuesto con sus subtipos.

#### `GET /api/facturacion/timbrados/todos/`
Lista todos los timbrados activos.

#### `POST /api/facturacion/guardar-config/`
Guarda o actualiza la configuración de facturación.

**Request Body:**
```json
{
  "empresa": {
    "ruc": "80012345-6",
    "nombre": "Mi Empresa S.A.",
    "direccion": "Av. Principal 123",
    "telefono": "021-123456",
    "correo": "contacto@miempresa.com",
    "actividades": "Servicios turísticos"
  },
  "factura": {
    "establecimiento": 1,
    "timbrado": 1,
    "tipo_impuesto": 1,
    "subtipo_impuesto": 3
  }
}
```

#### `GET /api/facturacion/obtener-config/`
Obtiene la configuración actual de facturación.

---

### Generación y Consulta de Facturas

#### `POST /api/facturacion/generar-factura/<reserva_id>/`
Genera una factura electrónica a partir de una reserva.

**Request Body (opcional):**
```json
{
  "subtipo_impuesto_id": 3
}
```

**Response (201 Created):**
```json
{
  "mensaje": "Factura generada exitosamente",
  "factura": {
    "id": 1,
    "numero_factura": "001-001-0000001",
    "fecha_emision": "2025-10-31T14:30:00Z",
    "cliente_nombre": "Juan Pérez",
    "cliente_tipo_documento": "CI",
    "cliente_numero_documento": "1234567",
    "condicion_venta": "contado",
    "total_exenta": "0.00",
    "total_gravada_5": "0.00",
    "total_gravada_10": "1500000.00",
    "total_iva_5": "0.00",
    "total_iva_10": "136363.64",
    "total_iva": "136363.64",
    "total_general": "1500000.00",
    "detalles": [
      {
        "numero_item": 1,
        "descripcion": "Paquete Turístico: Viaje a Encarnación",
        "cantidad": "2.00",
        "precio_unitario": "750000.00",
        "monto_exenta": "0.00",
        "monto_gravada_5": "0.00",
        "monto_gravada_10": "1500000.00",
        "subtotal": "1500000.00"
      }
    ],
    "empresa": {...},
    "establecimiento": {...},
    "punto_expedicion": {...},
    "timbrado": {...}
  }
}
```

**Errores posibles:**
- `400` - La reserva debe estar confirmada o finalizada
- `400` - Esta reserva ya tiene una factura generada
- `400` - No existe configuración de facturación
- `404` - Reserva no encontrada

#### `GET /api/facturacion/factura-reserva/<reserva_id>/`
Obtiene la factura asociada a una reserva específica.

**Response (200 OK):**
```json
{
  "id": 1,
  "numero_factura": "001-001-0000001",
  "fecha_emision": "2025-10-31T14:30:00Z",
  ...
}
```

**Errores posibles:**
- `404` - Esta reserva no tiene factura generada

#### `GET /api/facturacion/facturas/`
Lista todas las facturas generadas (no incluye configuraciones).

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "numero_factura": "001-001-0000001",
    "cliente_nombre": "Juan Pérez",
    "total_general": "1500000.00",
    "fecha_emision": "2025-10-31T14:30:00Z",
    "reserva_codigo": "RSV-2025-00001",
    ...
  },
  ...
]
```

#### `GET /api/facturacion/facturas/<factura_id>/`
Obtiene el detalle completo de una factura por su ID.

**Response (200 OK):**
```json
{
  "id": 1,
  "numero_factura": "001-001-0000001",
  "detalles": [...],
  "empresa": {...},
  ...
}
```

#### `GET /api/facturacion/descargar-pdf/<factura_id>/`
Descarga el PDF de una factura. Si el PDF no existe, lo genera automáticamente.

**Query Parameters:**
- `regenerar` (opcional): `true` o `false` (default: `false`) - Fuerza la regeneración del PDF aunque ya exista.

**Response:**
- Archivo PDF con `Content-Type: application/pdf`
- Nombre del archivo: `factura_{numero_factura}.pdf`

**Ejemplo de uso:**
```bash
# Descargar PDF (genera si no existe)
GET /api/facturacion/descargar-pdf/1/

# Forzar regeneración del PDF
GET /api/facturacion/descargar-pdf/1/?regenerar=true
```

**Características del PDF:**
- ✅ Formato profesional con diseño limpio
- ✅ Encabezado con datos de la empresa y factura
- ✅ Información completa del cliente
- ✅ Tabla de detalles con todos los ítems
- ✅ Desglose completo de impuestos
- ✅ Total general destacado
- ✅ Código de reserva en el pie de página
- ✅ Colores corporativos personalizables

**Errores posibles:**
- `404` - Factura no encontrada
- `500` - Error al generar PDF

---

## Flujo de Uso

### 1. Configuración Inicial (Una sola vez)

```bash
# Crear tipos de impuesto
POST /api/facturacion/tipos-impuesto/
{
  "nombre": "IVA",
  "descripcion": "Impuesto al Valor Agregado"
}

# Crear subtipos de impuesto
POST /api/facturacion/subtipos-impuesto/
{
  "tipo_impuesto": 1,
  "nombre": "IVA 10%",
  "porcentaje": 10
}

# Crear timbrado
POST /api/facturacion/timbrados/
{
  "empresa": 1,
  "numero": "12345678",
  "inicio_vigencia": "2025-01-01",
  "fin_vigencia": "2025-12-31"
}

# Guardar configuración completa
POST /api/facturacion/guardar-config/
{
  "empresa": {...},
  "factura": {...}
}
```

### 2. Generar Factura para una Reserva

```bash
# 1. Verificar que la reserva esté confirmada o finalizada
GET /api/reservas/<reserva_id>/

# 2. Generar la factura
POST /api/facturacion/generar-factura/<reserva_id>/
{
  "subtipo_impuesto_id": 3  # Opcional, usa la config por defecto si no se especifica
}

# 3. Obtener la factura generada
GET /api/facturacion/factura-reserva/<reserva_id>/
```

### 3. Consultar Facturas

```bash
# Listar todas las facturas
GET /api/facturacion/facturas/

# Obtener detalle de una factura específica
GET /api/facturacion/facturas/<factura_id>/
```

---

## Reglas de Negocio

### Validaciones al Generar Factura

1. ✅ La reserva debe estar en estado `confirmada` o `finalizada`
2. ✅ La reserva no puede tener una factura previamente generada
3. ✅ Debe existir una configuración de facturación activa
4. ✅ Debe haber al menos un punto de expedición activo
5. ✅ La reserva debe tener un titular asignado
6. ✅ El subtipo de impuesto debe ser válido

### Generación Automática

- **Número de factura**: Se genera automáticamente con formato `XXX-XXX-XXXXXXX`
- **Fecha de emisión**: Se asigna la fecha y hora actual
- **Cliente**: Se extraen los datos del titular de la reserva
- **Detalles**: Se generan automáticamente desde el paquete y servicios adicionales
- **Totales**: Se calculan automáticamente según el IVA aplicado

---

## Integración Futura con SET

El sistema está diseñado para facilitar la integración futura con el sistema de la SET:

### Datos preparados para SET:
- ✅ Número de timbrado
- ✅ Establecimiento y punto de expedición
- ✅ Número de factura correlativo
- ✅ Datos del emisor (empresa)
- ✅ Datos del receptor (cliente)
- ✅ Detalles de la operación
- ✅ Desglose de impuestos (exenta, 5%, 10%)
- ✅ Totales calculados

### Campos adicionales que podrían agregarse:
- CDC (Código de Control)
- QR de validación
- URL de consulta en SET
- Estado de envío a SET
- Fecha de envío/aprobación
- Motivo de anulación (si aplica)

---

## Panel de Administración

El sistema incluye administración completa en Django Admin:

- **Empresa**: Ver/editar datos de la empresa
- **Establecimientos**: Gestionar establecimientos
- **Puntos de Expedición**: Gestionar puntos de expedición
- **Timbrados**: Gestionar timbrados con vigencias
- **Tipos de Impuesto**: Gestionar tipos y subtipos
- **Facturas**: Ver facturas con detalles inline
- **Detalles de Factura**: Gestión independiente si es necesario

---

## Ejemplos de Uso

### Ejemplo 1: Generar factura para reserva existente

```python
import requests

# URL base del API
base_url = "http://localhost:8000/api"

# ID de la reserva
reserva_id = 1

# Generar factura
response = requests.post(
    f"{base_url}/facturacion/generar-factura/{reserva_id}/",
    json={"subtipo_impuesto_id": 3}
)

if response.status_code == 201:
    factura = response.json()["factura"]
    print(f"Factura generada: {factura['numero_factura']}")
    print(f"Total: {factura['total_general']}")
else:
    print(f"Error: {response.json()['error']}")
```

### Ejemplo 2: Listar todas las facturas

```python
response = requests.get(f"{base_url}/facturacion/facturas/")
facturas = response.json()

for factura in facturas:
    print(f"{factura['numero_factura']} - {factura['cliente_nombre']} - {factura['total_general']}")
```

### Ejemplo 3: Consultar factura de una reserva

```python
reserva_id = 1
response = requests.get(f"{base_url}/facturacion/factura-reserva/{reserva_id}/")

if response.status_code == 200:
    factura = response.json()
    print(f"Factura: {factura['numero_factura']}")
    print(f"Cliente: {factura['cliente_nombre']}")
    print(f"Total: {factura['total_general']}")
    print("\nDetalles:")
    for detalle in factura['detalles']:
        print(f"  - {detalle['descripcion']}: {detalle['subtotal']}")
else:
    print("Esta reserva no tiene factura generada")
```

---

## Estructura de la Base de Datos

```
Empresa (1)
  └── Establecimiento (N)
        └── PuntoExpedicion (N)

Empresa (1)
  └── Timbrado (N)

TipoImpuesto (N)
  └── SubtipoImpuesto (N)

FacturaElectronica (N)
  ├── Empresa (FK)
  ├── Establecimiento (FK)
  ├── PuntoExpedicion (FK)
  ├── Timbrado (FK)
  ├── TipoImpuesto (FK)
  ├── SubtipoImpuesto (FK)
  ├── Reserva (FK)
  ├── Moneda (FK)
  └── DetalleFactura (N)
        └── FacturaElectronica (FK)
```

---

## Notas Importantes

1. **Solo una empresa**: El sistema está diseñado para manejar una única empresa. Intentar crear más de una generará un error.

2. **Configuración vs Factura**: El modelo `FacturaElectronica` sirve tanto para guardar la configuración (`es_configuracion=True`) como para las facturas reales (`es_configuracion=False`).

3. **Transacciones atómicas**: La generación de facturas usa transacciones atómicas para garantizar consistencia de datos.

4. **Cálculo de IVA**: El sistema asume que los precios ya incluyen IVA, por lo que extrae el impuesto de la base gravada.

5. **Servicios adicionales**: Si una reserva tiene servicios adicionales, estos se agregan automáticamente como líneas separadas en la factura.

6. **Permisos**: Actualmente los endpoints tienen `AllowAny`, pero en producción deberían tener permisos apropiados según roles.

---

## Funcionalidades Implementadas

### ✅ Generación de PDF
**Estado: IMPLEMENTADO**

El sistema genera automáticamente PDFs profesionales de las facturas utilizando ReportLab.

**Características:**
- Generación automática al solicitar descarga
- Almacenamiento en `media/facturas/pdf/`
- Diseño profesional con:
  - Encabezado de empresa y factura
  - Información del cliente
  - Tabla de detalles
  - Totales e impuestos
  - Código de reserva
- Opción de regenerar PDF
- Cache automático (no regenera si ya existe)

**Endpoint:** `GET /api/facturacion/descargar-pdf/<factura_id>/`

**Ubicación del código:**
- Función: `FacturaElectronica.generar_pdf()` en `apps/facturacion/models.py:331`
- Vista: `descargar_pdf_factura()` en `apps/facturacion/views.py:435`

---

### ✅ Anulación de Facturas
**Estado: IMPLEMENTADO**

El sistema permite la anulación de facturas electrónicas cumpliendo con las normativas de la SET (Subsecretaría de Estado de Tributación).

**Características:**
- Anulación solo el mismo día de emisión
- Requiere permisos de administrador
- Registro de motivo, fecha y usuario que anula
- Validación de notas de crédito previas
- Motivos estandarizados según normativa SET (código dMotEmi)

**Endpoint:** `POST /api/facturacion/facturas/<factura_id>/anular/`

**Request Body:**
```json
{
  "motivo": "1"
}
```

**Motivos de Anulación (código dMotEmi):**
| Código | Descripción                        |
|--------|-----------------------------------|
| 1      | Error en datos de emisor          |
| 2      | Error en datos del receptor       |
| 3      | Error en datos de la operación    |
| 4      | Operación no realizada            |
| 5      | Por acuerdo entre las partes      |

**Validaciones:**
- ✅ Solo se puede anular el mismo día de emisión
- ✅ Solo usuarios administradores pueden anular
- ✅ La factura no debe estar ya anulada
- ✅ No debe ser una factura de configuración
- ✅ No debe tener notas de crédito emitidas
- ✅ El motivo debe ser uno de los códigos válidos (1-5)

**Response (200 OK):**
```json
{
  "mensaje": "Factura anulada exitosamente",
  "factura": {
    "id": 1,
    "numero_factura": "001-001-0000001",
    "activo": false,
    "fecha_anulacion": "2025-11-20T18:30:00Z",
    "motivo_anulacion": "1",
    "usuario_anulacion": {
      "id": 1,
      "username": "admin"
    }
  }
}
```

**Errores posibles:**
- `400` - La factura ya está anulada
- `400` - No se puede anular una factura que tiene notas de crédito emitidas
- `400` - Solo los administradores pueden anular facturas
- `400` - Solo se puede anular una factura el mismo día de su emisión
- `400` - El motivo de anulación es requerido
- `404` - Factura no encontrada

**Ubicación del código:**
- Método: `FacturaElectronica.anular()` en `apps/facturacion/models.py:460`
- Vista: `anular_factura()` en `apps/facturacion/views.py:286`

---

## Próximos Pasos Sugeridos

1. ~~**Generación de PDF**~~: ✅ **COMPLETADO** - Implementado con ReportLab
2. ~~**Anulación de facturas**~~: ✅ **COMPLETADO** - Implementado con motivos estandarizados según normativa SET
3. **Envío por email**: Enviar la factura automáticamente al cliente
4. **Notas de crédito**: Implementar emisión de notas de crédito
5. **Reportes**: Agregar reportes de facturación por período
6. **Integración SET**: Conectar con el sistema de la SET para facturación electrónica oficial
7. **Permisos**: Implementar sistema de permisos apropiado
8. **Auditoría**: Agregar logs de auditoría para todas las operaciones de facturación

---

## Soporte

Para más información sobre el sistema, consultar:
- Código fuente: `apps/facturacion/`
- Modelos: `apps/facturacion/models.py`
- API: `apps/facturacion/views.py`
- URLs: `apps/facturacion/urls.py`
