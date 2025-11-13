# 📚 DOCUMENTACIÓN FRONTEND - ABM DE CAJAS

## Índice
1. [Resumen General](#resumen-general)
2. [Estructura de Navegación](#estructura-de-navegación)
3. [Vista Principal: Listado de Cajas](#vista-principal-listado-de-cajas)
4. [Modal: Nueva Caja](#modal-nueva-caja)
5. [Modal: Ver Detalle](#modal-ver-detalle)
6. [Modal: Editar Caja](#modal-editar-caja)
7. [Modal: Confirmar Eliminación](#modal-confirmar-eliminación)
8. [Endpoints API](#endpoints-api)
9. [Modelos de Datos](#modelos-de-datos)
10. [Estados y Validaciones](#estados-y-validaciones)
11. [Ejemplos de Código](#ejemplos-de-código)

---

## Resumen General

### Objetivo
Gestionar las **Cajas** (puntos de venta) del sistema, permitiendo crear, visualizar, editar y eliminar cajas, así como monitorear su estado actual (abierta/cerrada) y saldo.

### Ubicación
La vista se encuentra dentro del módulo **"Arqueo de Caja"** en el sidebar principal.

### Características Principales
- ✅ Listado con filtros dinámicos
- ✅ Resumen estadístico en tiempo real
- ✅ Conversión automática de moneda (Gs ↔ USD)
- ✅ Modales para todas las operaciones CRUD
- ✅ Validación de datos en tiempo real
- ✅ Indicadores visuales de estado

---

## Estructura de Navegación

```
SIDEBAR (Colapsable)
│
├─ 🏠 Dashboard
├─ 👥 Usuarios
├─ 📦 Paquetes
├─ 🏨 Hoteles
├─ 📋 Reservas
├─ 💰 Arqueo de Caja ◄─── MÓDULO PRINCIPAL
│   ├─ 🏪 Cajas ◄─────────── VISTA ACTUAL
│   ├─ 📂 Aperturas
│   ├─ 💸 Movimientos
│   └─ 🔒 Cierres
└─ 📊 Reportes
```

### Breadcrumb
```
Inicio > Arqueo de Caja > Cajas
```

---

## Vista Principal: Listado de Cajas

### Diseño Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏪 GESTIÓN DE CAJAS                                    [+ Nueva Caja]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📊 RESUMEN RÁPIDO                                                      │
│  ┌────────────┬────────────┬────────────┬────────────┬─────────────┐   │
│  │ Total: 5   │ Abiertas:1 │ Cerradas:4 │ Activas:5  │ Facturas:4  │   │
│  └────────────┴────────────┴────────────┴────────────┴─────────────┘   │
│                                                                          │
│  🔍 FILTROS                                                             │
│  [▼ Estado  ] [▼ Activo  ] [▼ Factura ] [🔍 Buscar...           ]     │
│                                                                          │
│  📋 TABLA DE CAJAS                                                      │
│  ┌─────┬──────────────┬─────────┬────────────┬─────────┬──────────┐   │
│  │  #  │ Nombre       │ Estado  │ Saldo (Gs) │ Saldo $ │ Acciones │   │
│  ├─────┼──────────────┼─────────┼────────────┼─────────┼──────────┤   │
│  │  1  │ Caja Princ.  │🟢ABIERTA│ 2,500,000  │ 342.47  │[Ver][X]  │   │
│  ├─────┼──────────────┼─────────┼────────────┼─────────┼──────────┤   │
│  │  2  │ Caja 1       │🔴CERRADA│     0      │  0.00   │[Ver][↑]  │   │
│  ├─────┼──────────────┼─────────┼────────────┼─────────┼──────────┤   │
│  │  3  │ Caja 2       │🔴CERRADA│     0      │  0.00   │[Ver][↑]  │   │
│  ├─────┼──────────────┼─────────┼────────────┼─────────┼──────────┤   │
│  │  4  │ Caja Secund. │🔴CERRADA│     0      │  0.00   │[Ver][↑]  │   │
│  ├─────┼──────────────┼─────────┼────────────┼─────────┼──────────┤   │
│  │  5  │ Caja Aux     │🔴CERRADA│     0      │  0.00   │[Ver][↑]  │   │
│  └─────┴──────────────┴─────────┴────────────┴─────────┴──────────┘   │
│                                                                          │
│  ◄ Anterior  [1] 2 3  Siguiente ►                    5 cajas en total  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Componentes

#### 1. Header
- **Título**: "🏪 GESTIÓN DE CAJAS"
- **Botón Principal**: "+ Nueva Caja" (abre modal de creación)

#### 2. Resumen Estadístico
Tarjetas con métricas en tiempo real:

| Métrica | Descripción | Endpoint |
|---------|-------------|----------|
| **Total** | Total de cajas en el sistema | `GET /api/arqueo-caja/cajas/resumen/` |
| **Abiertas** | Cajas con estado "abierta" | `GET /api/arqueo-caja/cajas/resumen/` |
| **Cerradas** | Cajas con estado "cerrada" | `GET /api/arqueo-caja/cajas/resumen/` |
| **Activas** | Cajas con activo=true | `GET /api/arqueo-caja/cajas/resumen/` |
| **Facturas** | Cajas que emiten facturas | `GET /api/arqueo-caja/cajas/resumen/` |

**Endpoint**: `GET /api/arqueo-caja/cajas/resumen/`

**Respuesta**:
```json
[
  { "texto": "Total Cajas", "valor": "5" },
  { "texto": "Activas", "valor": "5" },
  { "texto": "Inactivas", "valor": "0" },
  { "texto": "Abiertas Ahora", "valor": "1" },
  { "texto": "Cerradas", "valor": "4" },
  { "texto": "Emiten Facturas", "valor": "4" },
  { "texto": "Saldo Total en Cajas Abiertas", "valor": "Gs 2,500,000" },
  { "texto": "Nuevas últimos 30 días", "valor": "2" }
]
```

#### 3. Filtros

| Campo | Tipo | Opciones | Query Param |
|-------|------|----------|-------------|
| **Estado** | Select | Todas / Abierta / Cerrada | `?estado_actual=abierta` |
| **Activo** | Select | Todas / Activo / Inactivo | `?activo=true` |
| **Factura** | Select | Todas / Sí / No | `?emite_facturas=true` |
| **Búsqueda** | Input | Texto libre | `?search=caja` |

**Ejemplo de URL con filtros**:
```
GET /api/arqueo-caja/cajas/?estado_actual=abierta&activo=true&emite_facturas=true
```

#### 4. Tabla de Cajas

**Columnas**:

| Columna | Descripción | Origen |
|---------|-------------|--------|
| **#** | Número de caja | `numero_caja` |
| **Nombre** | Nombre de la caja | `nombre` |
| **Estado** | Abierta/Cerrada con indicador visual | `estado_actual` |
| **Saldo (Gs)** | Saldo en Guaraníes | `saldo_actual` |
| **Saldo $** | Saldo en Dólares | `saldo_actual_alternativo` |
| **Acciones** | Botones de acción contextual | - |

**Indicadores de Estado**:
- 🟢 **ABIERTA**: Color verde, texto "ABIERTA"
- 🔴 **CERRADA**: Color rojo, texto "CERRADA"
- ⚪ **INACTIVA**: Color gris, texto "INACTIVA" (si `activo=false`)

**Botones de Acción** (según estado):

| Estado | Botones Disponibles |
|--------|---------------------|
| **Abierta** | `[Ver]` `[Editar]` `[Cerrar]` |
| **Cerrada** | `[Ver]` `[Editar]` `[Abrir]` `[Eliminar]` |
| **Inactiva** | `[Ver]` |

#### 5. Paginación

- **Items por página**: 10 (configurable)
- **Navegación**: Anterior / Números de página / Siguiente
- **Total**: Mostrar "X cajas en total"

---

## Modal: Nueva Caja

### Diseño Visual

``` 001
┌─────────────────────────────────────────────────────────────────────────┐
│  ✏️ NUEVA CAJA                                          [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📝 INFORMACIÓN BÁSICA                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  * Número de Caja                                                │  │
│  │  [______________]                                                │  │
│  │  ℹ️  Debe ser único en el sistema                                │  │
│  │                                                                   │  │
│  │  * Nombre de la Caja                                             │  │
│  │  [_____________________________________________________________] │  │
│  │                                                                   │  │
│  │  Ubicación                                                       │  │
│  │  [_____________________________________________________________] │  │
│  │  Ej: Planta Baja - Recepción                                    │  │
│  │                                                                   │  │
│  │  Descripción                                                     │  │
│  │  [_____________________________________________________________] │  │
│  │  [_____________________________________________________________] │  │
│  │                                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  🧾 CONFIGURACIÓN DE FACTURACIÓN                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  [ ✓ ] Emite Facturas Electrónicas                              │  │
│  │                                                                   │  │
│  │  * Punto de Expedición                                           │  │
│  │  [▼ Seleccione un punto de expedición...                      ] │  │
│  │                                                                   │  │
│  │  ℹ️  Si la caja emite facturas, debe tener un punto de          │  │
│  │     expedición asociado.                                         │  │
│  │                                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ⚙️  ESTADO                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  [ ✓ ] Activo                                                    │  │
│  │  ℹ️  Las cajas inactivas no pueden ser abiertas                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│                                      [Cancelar]  [💾 Guardar Caja]     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Campos del Formulario

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| **numero_caja** | Number | ✅ Sí | Único, mayor a 0 |
| **nombre** | Text | ✅ Sí | Máx 100 caracteres |
| **ubicacion** | Text | ❌ No | Máx 200 caracteres |
| **descripcion** | Textarea | ❌ No | Libre |
| **emite_facturas** | Checkbox | ❌ No | Boolean (default: true) |
| **punto_expedicion** | Select | ⚠️ Condicional* | Required si `emite_facturas=true` |
| **activo** | Checkbox | ❌ No | Boolean (default: true) |

*⚠️ **Validación importante**: Si `emite_facturas=true`, entonces `punto_expedicion` es obligatorio.

### Endpoint

**POST** `/api/arqueo-caja/cajas/`

**Request Body**:
```json
{
  "nombre": "Caja Sucursal 1",
  "ubicacion": "Planta Baja - Ventanilla 1",
  "descripcion": "Caja para atención al público",
  "emite_facturas": true,
  "punto_expedicion": 1,
  "activo": true
}
```

**Response 201 Created**:
```json
{
  "id": 6,
  "nombre": "Caja Sucursal 1",
  "numero_caja": 6,
  "punto_expedicion": 1,
  "punto_expedicion_nombre": "001-001 Sede Principal",
  "emite_facturas": true,
  "ubicacion": "Planta Baja - Ventanilla 1",
  "estado_actual": "cerrada",
  "saldo_actual": "0.00",
  "saldo_actual_alternativo": "0.00",
  "moneda_alternativa": "USD",
  "activo": true
}
```

**Errores Posibles**:

```json
// 400 - Número de caja duplicado
{
  "numero_caja": ["Caja con este numero caja ya existe."]
}

// 400 - Emite facturas sin punto de expedición
{
  "non_field_errors": [
    "Una caja que emite facturas debe tener un punto de expedición asociado"
  ]
}
```

### Flujo UX

1. Usuario hace clic en "+ Nueva Caja"
2. Se abre modal con formulario vacío
3. Usuario completa campos obligatorios
4. **Si marca "Emite Facturas"**: Campo "Punto de Expedición" se vuelve obligatorio
5. Usuario hace clic en "Guardar Caja"
6. Sistema valida datos
7. Si OK: Modal se cierra, tabla se recarga, se muestra notificación de éxito
8. Si Error: Se muestran mensajes de error en los campos correspondientes

---

## Modal: Ver Detalle

### Diseño Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📄 CAJA #1 - Caja Principal                            [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📌 INFORMACIÓN GENERAL                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Número:           #1                                            │  │
│  │  Nombre:           Caja Principal                                │  │
│  │  Ubicación:        Planta Baja - Recepción                       │  │
│  │  Descripción:      Caja principal para atención al público       │  │
│  │  Estado:           🟢 ABIERTA                                    │  │
│  │  Saldo Actual:     Gs 2,500,000 (USD 342.47)                     │  │
│  │  Emite Facturas:   ✓ Sí                                          │  │
│  │  Punto Exp.:       001-001 - Sede Principal                      │  │
│  │  Activo:           ✓ Sí                                          │  │
│  │  Creado:           10/11/2025 14:30                              │  │
│  │  Modificado:       12/11/2025 08:00                              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  📂 APERTURA ACTUAL                                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Código:           APR-2025-0001                                 │  │
│  │  Responsable:      Juan Pérez (Cajero)                           │  │
│  │  Apertura:         12/11/2025 08:00                              │  │
│  │  Monto Inicial:    Gs 500,000                                    │  │
│  │  Duración:         4h 30m                                        │  │
│  │  Movimientos:      21 registros                                  │  │
│  │  Ingresos:         Gs 3,200,000                                  │  │
│  │  Egresos:          Gs 1,200,000                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  📜 HISTORIAL RECIENTE (Últimos 5 movimientos)                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  APR-2025-0001 │ 12/11/25 08:00 │ Juan Pérez   │ 🟢 Abierta    │  │
│  │  CIE-2025-0145 │ 11/11/25 18:00 │ María García │ ✓ Cerrada     │  │
│  │  APR-2024-0145 │ 11/11/25 08:00 │ María García │ ✓ Cerrada     │  │
│  │  CIE-2024-0144 │ 10/11/25 18:00 │ Pedro López  │ ✓ Cerrada     │  │
│  │  APR-2024-0144 │ 10/11/25 08:00 │ Pedro López  │ ✓ Cerrada     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  [📝 Editar]  [Ver Historial Completo]  [Ver Movimientos]  [🔒 Cerrar] │
└─────────────────────────────────────────────────────────────────────────┘
```

### Endpoints Utilizados

#### 1. Información General de la Caja
**GET** `/api/arqueo-caja/cajas/{id}/`

**Response**:
```json
{
  "id": 1,
  "nombre": "Caja Principal",
  "numero_caja": 1,
  "punto_expedicion": 1,
  "punto_expedicion_nombre": "001-001 Sede Principal",
  "emite_facturas": true,
  "descripcion": "Caja principal para atención al público",
  "ubicacion": "Planta Baja - Recepción",
  "estado_actual": "abierta",
  "saldo_actual": "2500000.00",
  "saldo_actual_alternativo": "342.47",
  "moneda_alternativa": "USD",
  "activo": true,
  "fecha_creacion": "2025-11-10T14:30:00Z",
  "fecha_modificacion": "2025-11-12T08:00:00Z"
}
```

#### 2. Estado Actual y Apertura
**GET** `/api/arqueo-caja/cajas/{id}/estado/`

**Response**:
```json
{
  "caja": {
    "id": 1,
    "nombre": "Caja Principal",
    "numero_caja": 1,
    "estado_actual": "abierta",
    "saldo_actual": "2500000.00"
  },
  "estado": "abierta",
  "saldo_actual": "2500000.00",
  "apertura_activa": {
    "id": 1,
    "codigo_apertura": "APR-2025-0001",
    "caja": 1,
    "responsable": {
      "id": 5,
      "nombre": "Juan",
      "apellido": "Pérez",
      "puesto": "Cajero"
    },
    "fecha_hora_apertura": "2025-11-12T08:00:00Z",
    "monto_inicial": "500000.00",
    "esta_abierta": true,
    "movimientos_count": 21
  }
}
```

#### 3. Historial de Aperturas/Cierres
**GET** `/api/arqueo-caja/cajas/{id}/historial/`

**Response**:
```json
[
  {
    "apertura": {
      "id": 1,
      "codigo_apertura": "APR-2025-0001",
      "caja": 1,
      "caja_nombre": "Caja Principal",
      "responsable": 5,
      "responsable_nombre": "Juan Pérez",
      "fecha_hora_apertura": "2025-11-12T08:00:00Z",
      "monto_inicial": "500000.00",
      "esta_abierta": true
    },
    "cierre": null
  },
  {
    "apertura": {
      "id": 145,
      "codigo_apertura": "APR-2024-0145",
      "fecha_hora_apertura": "2025-11-11T08:00:00Z",
      "monto_inicial": "500000.00",
      "esta_abierta": false
    },
    "cierre": {
      "id": 145,
      "codigo_cierre": "CIE-2025-0145",
      "fecha_hora_cierre": "2025-11-11T18:00:00Z",
      "saldo_teorico_efectivo": "780000.00",
      "saldo_real_efectivo": "780500.00",
      "diferencia_efectivo": "500.00"
    }
  }
]
```

### Acciones Disponibles

| Botón | Acción | Condición |
|-------|--------|-----------|
| **📝 Editar** | Abre modal de edición | Siempre disponible |
| **Ver Historial Completo** | Navega a vista de historial | Siempre disponible |
| **Ver Movimientos** | Navega a vista de movimientos | Solo si está abierta |
| **🔒 Cerrar** | Navega a proceso de cierre | Solo si está abierta |

---

## Modal: Editar Caja

### Diseño Visual

Idéntico al modal de "Nueva Caja", pero con los campos pre-poblados con los datos actuales.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📝 EDITAR CAJA #1 - Caja Principal                     [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│  [Mismo formulario que "Nueva Caja" pero con datos pre-cargados]       │
│                                                                          │
│                                      [Cancelar]  [💾 Guardar Cambios]  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Endpoint

**PUT/PATCH** `/api/arqueo-caja/cajas/{id}/`

**Request Body** (igual que POST):
```json
{
  "numero_caja": 1,
  "nombre": "Caja Principal - Actualizada",
  "ubicacion": "Planta Baja - Recepción Principal",
  "descripcion": "Caja principal actualizada",
  "emite_facturas": true,
  "punto_expedicion": 1,
  "activo": true
}
```

**Response 200 OK**: (mismo formato que el GET)

### Restricciones

- ⚠️ **No se puede cambiar el `numero_caja` a uno ya existente**
- ⚠️ **No se puede desactivar `emite_facturas` si hay un `punto_expedicion` asignado**
- ⚠️ **No se puede editar una caja mientras está abierta** (validación de negocio opcional)

---

## Modal: Confirmar Eliminación

### Diseño Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ⚠️  CONFIRMAR ELIMINACIÓN                              [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ¿Está seguro que desea eliminar la siguiente caja?                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Caja:   #2 - Caja 1                                             │  │
│  │  Estado: Cerrada                                                 │  │
│  │  Saldo:  Gs 0                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ⚠️  ADVERTENCIA:                                                       │
│  • Esta acción marcará la caja como INACTIVA                           │
│  • No se podrán registrar nuevas aperturas                             │
│  • El historial de movimientos se mantendrá                            │
│  • Esta acción NO es reversible desde esta vista                       │
│                                                                          │
│                                      [Cancelar]  [🗑️ Eliminar]          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Endpoint

**DELETE** `/api/arqueo-caja/cajas/{id}/`

**Response 204 No Content** (sin body)

### Validaciones

- ❌ **No se puede eliminar una caja que está abierta**
- ⚠️ La eliminación es un "soft delete" (cambia `activo=false`)

**Error 400**:
```json
{
  "error": "No se puede eliminar una caja que está abierta. Cierre la caja primero."
}
```

---

## Endpoints API

### Resumen de Endpoints

| Acción | Método | Endpoint | Descripción |
|--------|--------|----------|-------------|
| **Listar** | GET | `/api/arqueo-caja/cajas/` | Lista todas las cajas con filtros |
| **Resumen** | GET | `/api/arqueo-caja/cajas/resumen/` | Estadísticas resumidas |
| **Ver Detalle** | GET | `/api/arqueo-caja/cajas/{id}/` | Detalle completo de una caja |
| **Estado** | GET | `/api/arqueo-caja/cajas/{id}/estado/` | Estado actual y apertura |
| **Historial** | GET | `/api/arqueo-caja/cajas/{id}/historial/` | Historial de aperturas/cierres |
| **Crear** | POST | `/api/arqueo-caja/cajas/` | Crear nueva caja |
| **Actualizar** | PUT/PATCH | `/api/arqueo-caja/cajas/{id}/` | Actualizar caja existente |
| **Eliminar** | DELETE | `/api/arqueo-caja/cajas/{id}/` | Eliminar (desactivar) caja |

### Filtros Disponibles (Query Parameters)

```
GET /api/arqueo-caja/cajas/?estado_actual={valor}&activo={valor}&emite_facturas={valor}&punto_expedicion={id}
```

| Parámetro | Valores Posibles | Ejemplo |
|-----------|------------------|---------|
| `estado_actual` | `abierta`, `cerrada` | `?estado_actual=abierta` |
| `activo` | `true`, `false` | `?activo=true` |
| `emite_facturas` | `true`, `false` | `?emite_facturas=true` |
| `punto_expedicion` | ID numérico | `?punto_expedicion=1` |

---

## Modelos de Datos

### Objeto Caja (Resumen)

```typescript
interface Caja {
  id: number;
  nombre: string;
  numero_caja: number;
  punto_expedicion: number | null;
  punto_expedicion_nombre: string | null;
  emite_facturas: boolean;
  ubicacion: string | null;
  estado_actual: 'abierta' | 'cerrada';
  saldo_actual: string;  // Decimal como string
  saldo_actual_alternativo: string | null;  // Decimal como string
  moneda_alternativa: 'USD';
  activo: boolean;
}
```

### Objeto Caja (Detalle Completo)

```typescript
interface CajaDetalle extends Caja {
  descripcion: string | null;
  fecha_creacion: string;  // ISO 8601
  fecha_modificacion: string;  // ISO 8601
  punto_expedicion: {
    id: number;
    nombre: string;
    codigo: string;
    // ... otros campos
  } | null;
}
```

### Objeto Apertura

```typescript
interface Apertura {
  id: number;
  codigo_apertura: string;
  caja: number;
  caja_nombre: string;
  responsable: number;
  responsable_nombre: string;
  fecha_hora_apertura: string;  // ISO 8601
  monto_inicial: string;  // Decimal
  esta_abierta: boolean;
  observaciones_apertura: string | null;
  activo: boolean;
  movimientos_count?: number;
}
```

### Objeto Resumen

```typescript
interface ResumenItem {
  texto: string;
  valor: string;
}

type Resumen = ResumenItem[];
```

---

## Estados y Validaciones

### Estados de Caja

| Estado | Color | Descripción | Acciones Permitidas |
|--------|-------|-------------|---------------------|
| **🟢 ABIERTA** | Verde | Tiene apertura activa | Ver, Editar, Cerrar |
| **🔴 CERRADA** | Rojo | Sin apertura activa | Ver, Editar, Abrir, Eliminar |
| **⚪ INACTIVA** | Gris | `activo=false` | Ver |

### Validaciones del Formulario

#### Cliente (Frontend)

```typescript
const validaciones = {
  numero_caja: {
    required: true,
    min: 1,
    pattern: /^\d+$/,
    mensaje: "Debe ser un número entero positivo"
  },
  nombre: {
    required: true,
    maxLength: 100,
    mensaje: "Máximo 100 caracteres"
  },
  ubicacion: {
    maxLength: 200,
    mensaje: "Máximo 200 caracteres"
  },
  punto_expedicion: {
    requiredIf: (form) => form.emite_facturas === true,
    mensaje: "Requerido si emite facturas"
  }
};
```

#### Servidor (Backend)

- ✅ Número de caja único
- ✅ Si `emite_facturas=true`, entonces `punto_expedicion` es obligatorio
- ✅ No se puede eliminar caja abierta
- ✅ Campos requeridos: `numero_caja`, `nombre`

---

## Ejemplos de Código

### 1. Cargar Listado de Cajas

```javascript
// Función para cargar cajas con filtros
async function cargarCajas(filtros = {}) {
  const params = new URLSearchParams();

  if (filtros.estado_actual) params.append('estado_actual', filtros.estado_actual);
  if (filtros.activo !== undefined) params.append('activo', filtros.activo);
  if (filtros.emite_facturas !== undefined) params.append('emite_facturas', filtros.emite_facturas);

  const url = `/api/arqueo-caja/cajas/?${params.toString()}`;

  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) throw new Error('Error al cargar cajas');

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}

// Uso
cargarCajas({ estado_actual: 'abierta', activo: true })
  .then(cajas => {
    console.log('Cajas abiertas:', cajas);
  });
```

### 2. Cargar Resumen Estadístico

```javascript
async function cargarResumen() {
  try {
    const response = await fetch('/api/arqueo-caja/cajas/resumen/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) throw new Error('Error al cargar resumen');

    const resumen = await response.json();
    // resumen es un array de { texto, valor }

    return resumen;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

### 3. Crear Nueva Caja

```javascript
async function crearCaja(datos) {
  try {
    const response = await fetch('/api/arqueo-caja/cajas/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(datos)
    });

    if (!response.ok) {
      const error = await response.json();
      throw error;
    }

    const caja = await response.json();
    return caja;
  } catch (error) {
    console.error('Error al crear caja:', error);
    throw error;
  }
}

// Uso
const nuevaCaja = {
  numero_caja: 6,
  nombre: "Caja Sucursal 1",
  ubicacion: "Planta Baja",
  emite_facturas: true,
  punto_expedicion: 1,
  activo: true
};

crearCaja(nuevaCaja)
  .then(caja => {
    console.log('Caja creada:', caja);
    // Recargar listado
    cargarCajas();
  })
  .catch(error => {
    // Mostrar errores de validación
    if (error.numero_caja) {
      alert(error.numero_caja[0]);
    }
  });
```

### 4. Obtener Detalle de Caja

```javascript
async function obtenerDetalleCaja(id) {
  try {
    // Cargar datos en paralelo
    const [caja, estado, historial] = await Promise.all([
      fetch(`/api/arqueo-caja/cajas/${id}/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json()),

      fetch(`/api/arqueo-caja/cajas/${id}/estado/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json()),

      fetch(`/api/arqueo-caja/cajas/${id}/historial/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json())
    ]);

    return { caja, estado, historial };
  } catch (error) {
    console.error('Error al cargar detalle:', error);
    throw error;
  }
}

// Uso
obtenerDetalleCaja(1)
  .then(({ caja, estado, historial }) => {
    console.log('Detalle de caja:', caja);
    console.log('Estado actual:', estado);
    console.log('Historial:', historial);
  });
```

### 5. Actualizar Caja

```javascript
async function actualizarCaja(id, datos) {
  try {
    const response = await fetch(`/api/arqueo-caja/cajas/${id}/`, {
      method: 'PATCH',  // o 'PUT' para actualización completa
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(datos)
    });

    if (!response.ok) {
      const error = await response.json();
      throw error;
    }

    const caja = await response.json();
    return caja;
  } catch (error) {
    console.error('Error al actualizar caja:', error);
    throw error;
  }
}

// Uso
actualizarCaja(1, { nombre: "Caja Principal - Actualizada" })
  .then(caja => {
    console.log('Caja actualizada:', caja);
  });
```

### 6. Eliminar Caja

```javascript
async function eliminarCaja(id) {
  try {
    const response = await fetch(`/api/arqueo-caja/cajas/${id}/`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      if (response.status === 400) {
        const error = await response.json();
        throw new Error(error.error || 'No se puede eliminar la caja');
      }
      throw new Error('Error al eliminar caja');
    }

    return true;
  } catch (error) {
    console.error('Error al eliminar caja:', error);
    throw error;
  }
}

// Uso con confirmación
if (confirm('¿Está seguro que desea eliminar esta caja?')) {
  eliminarCaja(2)
    .then(() => {
      alert('Caja eliminada exitosamente');
      cargarCajas();
    })
    .catch(error => {
      alert(error.message);
    });
}
```

### 7. Formatear Saldo con Moneda

```javascript
function formatearSaldo(caja) {
  const saldoGs = parseFloat(caja.saldo_actual);
  const saldoUsd = caja.saldo_actual_alternativo
    ? parseFloat(caja.saldo_actual_alternativo)
    : 0;

  return {
    guaranies: `Gs ${saldoGs.toLocaleString('es-PY', { minimumFractionDigits: 0 })}`,
    dolares: `USD ${saldoUsd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  };
}

// Uso
const caja = {
  saldo_actual: "2500000.00",
  saldo_actual_alternativo: "342.47",
  moneda_alternativa: "USD"
};

const saldos = formatearSaldo(caja);
console.log(saldos.guaranies);  // "Gs 2,500,000"
console.log(saldos.dolares);    // "USD 342.47"
```

---

## Componentes React (Ejemplo)

### ListadoCajas.jsx

```jsx
import React, { useState, useEffect } from 'react';

const ListadoCajas = () => {
  const [cajas, setCajas] = useState([]);
  const [resumen, setResumen] = useState([]);
  const [filtros, setFiltros] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cargarDatos();
  }, [filtros]);

  const cargarDatos = async () => {
    setLoading(true);
    try {
      const [cajasData, resumenData] = await Promise.all([
        cargarCajas(filtros),
        cargarResumen()
      ]);
      setCajas(cajasData);
      setResumen(resumenData);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({ ...prev, [campo]: valor }));
  };

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="gestion-cajas">
      <header>
        <h1>🏪 Gestión de Cajas</h1>
        <button onClick={() => abrirModalNueva()}>+ Nueva Caja</button>
      </header>

      {/* Resumen */}
      <ResumenEstadistico data={resumen} />

      {/* Filtros */}
      <Filtros onChange={handleFiltroChange} />

      {/* Tabla */}
      <TablaCajas cajas={cajas} onReload={cargarDatos} />
    </div>
  );
};

export default ListadoCajas;
```

---

## Notas Finales

### Consideraciones de UX

1. **Feedback Visual**: Mostrar loaders durante las peticiones
2. **Mensajes de Error**: Mostrar errores de validación en los campos correspondientes
3. **Confirmaciones**: Pedir confirmación antes de eliminar
4. **Notificaciones**: Toast/Snackbar para éxito/error de operaciones
5. **Responsive**: Adaptar tabla a dispositivos móviles (cards en lugar de tabla)

### Optimizaciones

- **Debounce** en el campo de búsqueda (300-500ms)
- **Cache** de datos de resumen (actualizar cada 30 segundos)
- **Paginación** del lado del servidor para grandes volúmenes
- **Lazy loading** del historial en el modal de detalle

### Accesibilidad

- Labels descriptivos en todos los campos
- Atributos ARIA en elementos interactivos
- Navegación por teclado en modales
- Contraste de colores adecuado para indicadores de estado

---

**Fecha de creación**: 12/11/2025
**Versión**: 1.0
**Mantenedores**: Equipo Backend - GroupTours
