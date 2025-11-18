# 📚 DOCUMENTACIÓN FRONTEND - ABM DE APERTURAS DE CAJA

## Índice
1. [Resumen General](#resumen-general)
2. [Estructura de Navegación](#estructura-de-navegación)
3. [Vista Principal: Listado de Aperturas](#vista-principal-listado-de-aperturas)
4. [Modal: Nueva Apertura](#modal-nueva-apertura)
5. [Modal: Ver Detalle](#modal-ver-detalle)
6. [Modal: Editar Apertura](#modal-editar-apertura)
7. [Modal: Confirmar Cierre](#modal-confirmar-cierre)
8. [Endpoints API](#endpoints-api)
9. [Modelos de Datos](#modelos-de-datos)
10. [Estados y Validaciones](#estados-y-validaciones)
11. [Ejemplos de Código](#ejemplos-de-código)

---

## Resumen General

### Objetivo
Gestionar las **Aperturas de Caja** del sistema, permitiendo crear aperturas, visualizar detalles, editar información y controlar el estado de cada sesión de caja abierta.

### Ubicación
La vista se encuentra dentro del módulo **"Arqueo de Caja"** en el sidebar principal.

### Características Principales
- ✅ Listado con filtros dinámicos
- ✅ Resumen estadístico en tiempo real
- ✅ Conversión automática de moneda (Gs ↔ USD)
- ✅ Modales para todas las operaciones
- ✅ Validación de datos en tiempo real
- ✅ Indicadores visuales de estado (abierta/cerrada)
- ✅ Seguimiento de responsables
- ✅ Control de montos iniciales

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
│   ├─ 🏪 Cajas
│   ├─ 📂 Aperturas ◄─────────── VISTA ACTUAL
│   ├─ 💸 Movimientos
│   └─ 🔒 Cierres
└─ 📊 Reportes
```

### Breadcrumb
```
Inicio > Arqueo de Caja > Aperturas
```

---

## Vista Principal: Listado de Aperturas

### Diseño Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📂 GESTIÓN DE APERTURAS DE CAJA                    [+ Nueva Apertura]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📊 RESUMEN RÁPIDO                                                      │
│  ┌────────────┬────────────┬────────────┬────────────┬─────────────┐   │
│  │ Total: 145 │ Abiertas:2 │ Cerradas:143│ Hoy: 5    │ Semana: 28  │   │
│  └────────────┴────────────┴────────────┴────────────┴─────────────┘   │
│                                                                          │
│  🔍 FILTROS                                                             │
│  [▼ Estado  ] [▼ Caja    ] [▼ Responsable] [📅 Desde] [📅 Hasta]      │
│  [🔍 Buscar código...                                               ]   │
│                                                                          │
│  📋 TABLA DE APERTURAS                                                  │
│  ┌──────────┬──────────┬──────────┬──────────┬────────────┬──────────┐ │
│  │ Código   │ Caja     │ Resp.    │ Apertura │ Monto Inic.│ Estado   │ │
│  ├──────────┼──────────┼──────────┼──────────┼────────────┼──────────┤ │
│  │ APR-0001 │ Caja 1   │ J.Pérez  │ 12/11 08h│ Gs 500,000 │🟢ABIERTA │ │
│  ├──────────┼──────────┼──────────┼──────────┼────────────┼──────────┤ │
│  │ APR-0002 │ Caja Aux │ M.García │ 12/11 08h│ Gs 300,000 │🟢ABIERTA │ │
│  ├──────────┼──────────┼──────────┼──────────┼────────────┼──────────┤ │
│  │ APR-0145 │ Caja 2   │ P.López  │ 11/11 08h│ Gs 500,000 │🔴CERRADA │ │
│  ├──────────┼──────────┼──────────┼──────────┼────────────┼──────────┤ │
│  │ APR-0144 │ Caja 1   │ J.Pérez  │ 11/11 08h│ Gs 500,000 │🔴CERRADA │ │
│  ├──────────┼──────────┼──────────┼──────────┼────────────┼──────────┤ │
│  │ APR-0143 │ Caja Aux │ M.García │ 10/11 08h│ Gs 300,000 │🔴CERRADA │ │
│  └──────────┴──────────┴──────────┴──────────┴────────────┴──────────┘ │
│                                                                          │
│  ◄ Anterior  [1] 2 3 ... 15  Siguiente ►          145 aperturas total  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Componentes

#### 1. Header
- **Título**: "📂 GESTIÓN DE APERTURAS DE CAJA"
- **Botón Principal**: "+ Nueva Apertura" (abre modal de creación)

#### 2. Resumen Estadístico
Tarjetas con métricas en tiempo real:

| Métrica | Descripción | Endpoint |
|---------|-------------|----------|
| **Total** | Total de aperturas en el sistema | `GET /api/arqueo-caja/aperturas/resumen/` |
| **Abiertas** | Aperturas actualmente abiertas | `GET /api/arqueo-caja/aperturas/resumen/` |
| **Cerradas** | Aperturas ya cerradas | `GET /api/arqueo-caja/aperturas/resumen/` |
| **Hoy** | Aperturas creadas hoy | `GET /api/arqueo-caja/aperturas/resumen/` |
| **Semana** | Aperturas de la última semana | `GET /api/arqueo-caja/aperturas/resumen/` |

**Endpoint**: `GET /api/arqueo-caja/aperturas/resumen/`

**Respuesta**:
```json
[
  { "texto": "Total Aperturas", "valor": "145" },
  { "texto": "Abiertas Actualmente", "valor": "2" },
  { "texto": "Cerradas", "valor": "143" },
  { "texto": "Aperturas Hoy", "valor": "5" },
  { "texto": "Última Semana", "valor": "28" },
  { "texto": "Monto Total Inicial (Abiertas)", "valor": "Gs 800,000" },
  { "texto": "Promedio Monto Inicial", "valor": "Gs 450,000" },
  { "texto": "Duración Promedio", "valor": "8.5 horas" }
]
```

#### 3. Filtros

| Campo | Tipo | Opciones | Query Param |
|-------|------|----------|-------------|
| **Estado** | Select | Todas / Abierta / Cerrada | `?esta_abierta=true` |
| **Caja** | Select | Todas / Lista de cajas | `?caja=1` |
| **Responsable** | Select | Todos / Lista de usuarios | `?responsable=5` |
| **Fecha Desde** | DatePicker | Selección de fecha | `?fecha_desde=2025-11-01` |
| **Fecha Hasta** | DatePicker | Selección de fecha | `?fecha_hasta=2025-11-30` |
| **Búsqueda** | Input | Texto libre (código) | `?search=APR-0001` |

**Ejemplo de URL con filtros**:
```
GET /api/arqueo-caja/aperturas/?esta_abierta=true&caja=1&fecha_desde=2025-11-01
```

#### 4. Tabla de Aperturas

**Columnas**:

| Columna | Descripción | Origen |
|---------|-------------|--------|
| **Código** | Código único de apertura | `codigo_apertura` |
| **Caja** | Nombre de la caja | `caja_nombre` |
| **Responsable** | Nombre del responsable | `responsable_nombre` |
| **Apertura** | Fecha y hora de apertura | `fecha_hora_apertura` |
| **Monto Inicial** | Monto inicial en Guaraníes | `monto_inicial` |
| **Estado** | Abierta/Cerrada con indicador | `esta_abierta` |
| **Acciones** | Botones de acción contextual | - |

**Indicadores de Estado**:
- 🟢 **ABIERTA**: Color verde, texto "ABIERTA"
- 🔴 **CERRADA**: Color rojo, texto "CERRADA"
- ⏱️ **Duración**: Mostrar tiempo transcurrido para aperturas abiertas

**Botones de Acción** (según estado):

| Estado | Botones Disponibles |
|--------|---------------------|
| **Abierta** | `[Ver]` `[Editar]` `[Ver Movimientos]` `[Cerrar Caja]` |
| **Cerrada** | `[Ver]` `[Ver Cierre]` `[Ver Movimientos]` |

#### 5. Paginación

- **Items por página**: 10 (configurable)
- **Navegación**: Anterior / Números de página / Siguiente
- **Total**: Mostrar "X aperturas en total"

---

## Modal: Nueva Apertura

### Diseño Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ✏️ NUEVA APERTURA DE CAJA                              [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📝 INFORMACIÓN BÁSICA                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  * Caja                                                           │  │
│  │  [▼ Seleccione una caja...                                     ] │  │
│  │  ℹ️  Solo se muestran cajas cerradas y activas                  │  │
│  │                                                                   │  │
│  │  * Responsable                                                   │  │
│  │  [▼ Seleccione un responsable...                               ] │  │
│  │  ℹ️  Usuario que se hará cargo de la caja                       │  │
│  │                                                                   │  │
│  │  * Fecha y Hora de Apertura                                      │  │
│  │  [12/11/2025] [08:00]                                            │  │
│  │  ℹ️  Por defecto: fecha y hora actual                           │  │
│  │                                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  💰 MONTO INICIAL                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  * Monto en Guaraníes (Gs)                                       │  │
│  │  [________________]                                              │  │
│  │  ℹ️  Debe ser mayor o igual a 0                                 │  │
│  │                                                                   │  │
│  │  Monto en Dólares (USD) - Opcional                               │  │
│  │  [________________]                                              │  │
│  │  ℹ️  Si se ingresa, debe ser mayor o igual a 0                  │  │
│  │                                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  📋 OBSERVACIONES                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  Observaciones de Apertura (Opcional)                            │  │
│  │  [_____________________________________________________________] │  │
│  │  [_____________________________________________________________] │  │
│  │  [_____________________________________________________________] │  │
│  │  Ej: Caja abierta con fondo de cambio habitual                  │  │
│  │                                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│                                      [Cancelar]  [💾 Abrir Caja]       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Campos del Formulario

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| **caja** | Select | ✅ Sí | Debe estar cerrada y activa |
| **responsable** | Select | ✅ Sí | Usuario válido del sistema |
| **fecha_hora_apertura** | DateTime | ✅ Sí | No puede ser futura |
| **monto_inicial** | Decimal | ✅ Sí | >= 0, máx 2 decimales |
| **monto_inicial_alternativo** | Decimal | ❌ No | >= 0 si se proporciona |
| **observaciones_apertura** | Textarea | ❌ No | Libre |

### Endpoint

**POST** `/api/arqueo-caja/aperturas/`

**Request Body**:
```json
{
  "caja": 1,
  "responsable": 5,
  "fecha_hora_apertura": "2025-11-12T08:00:00Z",
  "monto_inicial": "500000.00",
  "monto_inicial_alternativo": "68.49",
  "observaciones_apertura": "Caja abierta con fondo de cambio habitual"
}
```

**Response 201 Created**:
```json
{
  "id": 1,
  "codigo_apertura": "APR-2025-0001",
  "caja": 1,
  "caja_nombre": "Caja Principal",
  "caja_numero": 1,
  "responsable": 5,
  "responsable_nombre": "Juan Pérez",
  "responsable_puesto": "Cajero",
  "fecha_hora_apertura": "2025-11-12T08:00:00Z",
  "monto_inicial": "500000.00",
  "monto_inicial_alternativo": "68.49",
  "esta_abierta": true,
  "observaciones_apertura": "Caja abierta con fondo de cambio habitual",
  "activo": true,
  "movimientos_count": 0
}
```

**Errores Posibles**:

```json
// 400 - Caja ya está abierta
{
  "non_field_errors": [
    "La caja seleccionada ya tiene una apertura activa"
  ]
}

// 400 - Caja inactiva
{
  "caja": [
    "No se puede abrir una caja inactiva"
  ]
}

// 400 - Monto negativo
{
  "monto_inicial": [
    "El monto inicial debe ser mayor o igual a 0"
  ]
}

// 400 - Fecha futura
{
  "fecha_hora_apertura": [
    "La fecha de apertura no puede ser futura"
  ]
}
```

### Flujo UX

1. Usuario hace clic en "+ Nueva Apertura"
2. Se abre modal con formulario
3. Sistema carga lista de cajas disponibles (cerradas y activas)
4. Sistema carga lista de responsables (usuarios con permiso)
5. Fecha y hora se pre-llenan con valores actuales
6. Usuario completa campos obligatorios
7. Usuario hace clic en "Abrir Caja"
8. Sistema valida datos
9. Si OK:
   - Se crea la apertura
   - La caja cambia a estado "abierta"
   - Modal se cierra
   - Tabla se recarga
   - Notificación de éxito
10. Si Error: Se muestran mensajes de error en los campos correspondientes

---

## Modal: Ver Detalle

### Diseño Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📄 APERTURA APR-2025-0001                              [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📌 INFORMACIÓN GENERAL                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Código:           APR-2025-0001                                 │  │
│  │  Estado:           🟢 ABIERTA                                    │  │
│  │  Caja:             #1 - Caja Principal                           │  │
│  │  Responsable:      Juan Pérez (Cajero)                           │  │
│  │  Apertura:         12/11/2025 08:00                              │  │
│  │  Duración:         4h 30m (abierta actualmente)                  │  │
│  │  Activo:           ✓ Sí                                          │  │
│  │  Creado:           12/11/2025 08:00                              │  │
│  │  Modificado:       12/11/2025 08:05                              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  💰 MONTOS                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Monto Inicial (Gs):    Gs 500,000                               │  │
│  │  Monto Inicial (USD):   USD 68.49                                │  │
│  │  Saldo Actual (Gs):     Gs 2,500,000                             │  │
│  │  Saldo Actual (USD):    USD 342.47                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  📊 MOVIMIENTOS                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Total Movimientos:     21                                        │  │
│  │  Ingresos:              Gs 3,200,000 (15 movimientos)            │  │
│  │  Egresos:               Gs 1,200,000 (6 movimientos)             │  │
│  │  Balance:               Gs 2,000,000                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  📋 OBSERVACIONES                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Caja abierta con fondo de cambio habitual                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  📜 ÚLTIMOS MOVIMIENTOS (5 más recientes)                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  MOV-001 │ 12/11 12:30 │ Ingreso  │ Cobro Reserva  │ Gs 800,000 │  │
│  │  MOV-002 │ 12/11 11:45 │ Egreso   │ Cambio         │ Gs 50,000  │  │
│  │  MOV-003 │ 12/11 10:30 │ Ingreso  │ Cobro Servicio │ Gs 450,000 │  │
│  │  MOV-004 │ 12/11 09:15 │ Ingreso  │ Anticipo       │ Gs 300,000 │  │
│  │  MOV-005 │ 12/11 08:45 │ Egreso   │ Vuelto         │ Gs 25,000  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  [📝 Editar]  [Ver Todos los Movimientos]  [🔒 Cerrar Caja]            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Endpoints Utilizados

#### 1. Información General de la Apertura
**GET** `/api/arqueo-caja/aperturas/{id}/`

**Response**:
```json
{
  "id": 1,
  "codigo_apertura": "APR-2025-0001",
  "caja": 1,
  "caja_nombre": "Caja Principal",
  "caja_numero": 1,
  "responsable": 5,
  "responsable_nombre": "Juan Pérez",
  "responsable_puesto": "Cajero",
  "fecha_hora_apertura": "2025-11-12T08:00:00Z",
  "monto_inicial": "500000.00",
  "monto_inicial_alternativo": "68.49",
  "esta_abierta": true,
  "observaciones_apertura": "Caja abierta con fondo de cambio habitual",
  "activo": true,
  "fecha_creacion": "2025-11-12T08:00:00Z",
  "fecha_modificacion": "2025-11-12T08:05:00Z",
  "movimientos_count": 21
}
```

#### 2. Estado y Saldo Actual
**GET** `/api/arqueo-caja/cajas/{caja_id}/estado/`

**Response**:
```json
{
  "caja": {
    "id": 1,
    "nombre": "Caja Principal",
    "estado_actual": "abierta",
    "saldo_actual": "2500000.00"
  },
  "estado": "abierta",
  "saldo_actual": "2500000.00",
  "apertura_activa": {
    "id": 1,
    "codigo_apertura": "APR-2025-0001",
    "movimientos_count": 21
  }
}
```

#### 3. Movimientos de la Apertura
**GET** `/api/arqueo-caja/movimientos/?apertura={id}&ordering=-fecha_hora&limit=5`

**Response**:
```json
{
  "count": 21,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "codigo_movimiento": "MOV-001",
      "tipo": "ingreso",
      "concepto": "Cobro Reserva",
      "monto": "800000.00",
      "fecha_hora": "2025-11-12T12:30:00Z"
    }
    // ... más movimientos
  ]
}
```

### Acciones Disponibles

| Botón | Acción | Condición |
|-------|--------|-----------|
| **📝 Editar** | Abre modal de edición | Solo si está abierta |
| **Ver Todos los Movimientos** | Navega a vista de movimientos | Siempre disponible |
| **🔒 Cerrar Caja** | Navega a proceso de cierre | Solo si está abierta |

---

## Modal: Editar Apertura

### Diseño Visual

Idéntico al modal de "Nueva Apertura", pero con los campos pre-poblados con los datos actuales.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📝 EDITAR APERTURA APR-2025-0001                       [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│  [Mismo formulario que "Nueva Apertura" pero con datos pre-cargados]   │
│                                                                          │
│  ⚠️  NOTA: Solo se pueden editar aperturas que están abiertas           │
│                                                                          │
│                                      [Cancelar]  [💾 Guardar Cambios]  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Endpoint

**PUT/PATCH** `/api/arqueo-caja/aperturas/{id}/`

**Request Body**:
```json
{
  "responsable": 7,
  "monto_inicial": "550000.00",
  "monto_inicial_alternativo": "75.34",
  "observaciones_apertura": "Caja abierta con fondo de cambio actualizado"
}
```

**Response 200 OK**: (mismo formato que el GET)

### Restricciones

- ⚠️ **No se puede cambiar la caja** una vez creada la apertura
- ⚠️ **No se puede cambiar la fecha de apertura** si hay movimientos asociados
- ⚠️ **No se puede editar una apertura cerrada**
- ⚠️ **El monto inicial solo se puede editar si no hay movimientos**

**Error 400**:
```json
{
  "non_field_errors": [
    "No se puede editar una apertura que ya está cerrada"
  ]
}

// O

{
  "monto_inicial": [
    "No se puede modificar el monto inicial si ya existen movimientos registrados"
  ]
}
```

---

## Modal: Confirmar Cierre

### Diseño Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🔒 CONFIRMAR CIERRE DE CAJA                            [X] Cerrar      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ¿Está seguro que desea cerrar la siguiente apertura?                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Apertura:       APR-2025-0001                                   │  │
│  │  Caja:           #1 - Caja Principal                             │  │
│  │  Responsable:    Juan Pérez                                      │  │
│  │  Apertura:       12/11/2025 08:00                                │  │
│  │  Duración:       4h 30m                                          │  │
│  │  Movimientos:    21 registros                                    │  │
│  │  Saldo Actual:   Gs 2,500,000                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ℹ️  INFORMACIÓN:                                                       │
│  • Se iniciará el proceso de cierre de caja                            │
│  • Deberá contar el efectivo y registrar los montos                    │
│  • Se calcularán las diferencias automáticamente                       │
│  • La caja quedará cerrada hasta una nueva apertura                    │
│                                                                          │
│                                      [Cancelar]  [🔒 Proceder a Cierre] │
└─────────────────────────────────────────────────────────────────────────┘
```

### Flujo

1. Usuario hace clic en "Cerrar Caja"
2. Sistema muestra modal de confirmación con información de la apertura
3. Usuario confirma el cierre
4. Sistema redirige a la vista de **Cierre de Caja** donde:
   - Se registran los montos reales
   - Se calculan diferencias
   - Se completa el cierre

**NOTA**: Este modal NO cierra directamente la caja, solo confirma y redirige al proceso de cierre.

---

## Endpoints API

### Resumen de Endpoints

| Acción | Método | Endpoint | Descripción |
|--------|--------|----------|-------------|
| **Listar** | GET | `/api/arqueo-caja/aperturas/` | Lista todas las aperturas con filtros |
| **Resumen** | GET | `/api/arqueo-caja/aperturas/resumen/` | Estadísticas resumidas |
| **Ver Detalle** | GET | `/api/arqueo-caja/aperturas/{id}/` | Detalle completo de una apertura |
| **Cajas Disponibles** | GET | `/api/arqueo-caja/cajas/?estado_actual=cerrada&activo=true` | Cajas disponibles para abrir |
| **Responsables por Rol** | GET | `/api/usuarios/responsables/?roles=Cajero,Admin` | **⭐ RECOMENDADO**: Lista de empleados con roles específicos (cajero/admin) |
| **Responsables** | GET | `/api/empleados/?activo=true` | Lista de empleados activos para asignar como responsables |
| **Responsables (sin paginación)** | GET | `/api/empleados/todos/` | Lista simplificada de empleados activos sin usuario asignado |
| **Crear** | POST | `/api/arqueo-caja/aperturas/` | Crear nueva apertura |
| **Actualizar** | PUT/PATCH | `/api/arqueo-caja/aperturas/{id}/` | Actualizar apertura existente |
| **Movimientos** | GET | `/api/arqueo-caja/movimientos/?apertura={id}` | Movimientos de una apertura |

### Filtros Disponibles (Query Parameters)

```
GET /api/arqueo-caja/aperturas/?esta_abierta={valor}&caja={id}&responsable={id}&fecha_desde={fecha}&fecha_hasta={fecha}
```

| Parámetro | Valores Posibles | Ejemplo |
|-----------|------------------|---------|
| `esta_abierta` | `true`, `false` | `?esta_abierta=true` |
| `caja` | ID numérico | `?caja=1` |
| `responsable` | ID numérico | `?responsable=5` |
| `fecha_desde` | YYYY-MM-DD | `?fecha_desde=2025-11-01` |
| `fecha_hasta` | YYYY-MM-DD | `?fecha_hasta=2025-11-30` |
| `search` | Texto libre | `?search=APR-0001` |

---

## Modelos de Datos

### Objeto Apertura (Listado)

```typescript
interface AperturaListado {
  id: number;
  codigo_apertura: string;
  caja: number;
  caja_nombre: string;
  caja_numero: number;
  responsable: number;
  responsable_nombre: string;
  responsable_puesto: string;
  fecha_hora_apertura: string;  // ISO 8601
  monto_inicial: string;  // Decimal como string
  monto_inicial_alternativo: string | null;  // Decimal como string
  esta_abierta: boolean;
  activo: boolean;
  movimientos_count: number;
}
```

### Objeto Apertura (Detalle Completo)

```typescript
interface AperturaDetalle extends AperturaListado {
  observaciones_apertura: string | null;
  fecha_creacion: string;  // ISO 8601
  fecha_modificacion: string;  // ISO 8601
  responsable: {
    id: number;
    nombre: string;
    apellido: string;
    email: string;
    puesto: string;
  };
  caja: {
    id: number;
    nombre: string;
    numero_caja: number;
    estado_actual: 'abierta' | 'cerrada';
    saldo_actual: string;
  };
}
```

### Objeto Caja Disponible

```typescript
interface CajaDisponible {
  id: number;
  nombre: string;
  numero_caja: number;
  ubicacion: string | null;
  estado_actual: 'cerrada';
  activo: true;
}
```

### Objeto Responsable

```typescript
interface Responsable {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  puesto: string | null;
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

### Estados de Apertura

| Estado | Color | Descripción | Acciones Permitidas |
|--------|-------|-------------|---------------------|
| **🟢 ABIERTA** | Verde | Apertura activa | Ver, Editar, Ver Movimientos, Cerrar |
| **🔴 CERRADA** | Rojo | Apertura cerrada | Ver, Ver Cierre, Ver Movimientos |

### Validaciones del Formulario

#### Cliente (Frontend)

```typescript
const validaciones = {
  caja: {
    required: true,
    mensaje: "Debe seleccionar una caja"
  },
  responsable: {
    required: true,
    mensaje: "Debe seleccionar un responsable"
  },
  fecha_hora_apertura: {
    required: true,
    maxDate: new Date(),
    mensaje: "La fecha no puede ser futura"
  },
  monto_inicial: {
    required: true,
    min: 0,
    pattern: /^\d+(\.\d{1,2})?$/,
    mensaje: "Debe ser un número positivo con máximo 2 decimales"
  },
  monto_inicial_alternativo: {
    min: 0,
    pattern: /^\d+(\.\d{1,2})?$/,
    mensaje: "Debe ser un número positivo con máximo 2 decimales"
  }
};
```

#### Servidor (Backend)

- ✅ Caja debe estar cerrada y activa
- ✅ No puede haber otra apertura activa para la misma caja
- ✅ Fecha de apertura no puede ser futura
- ✅ Monto inicial >= 0
- ✅ Monto inicial alternativo >= 0 (si se proporciona)
- ✅ Responsable debe ser un usuario válido
- ✅ Solo se pueden editar aperturas abiertas
- ✅ No se puede cambiar monto inicial si hay movimientos

---

## Ejemplos de Código

### 1. Cargar Listado de Aperturas

```javascript
// Función para cargar aperturas con filtros
async function cargarAperturas(filtros = {}) {
  const params = new URLSearchParams();

  if (filtros.esta_abierta !== undefined) params.append('esta_abierta', filtros.esta_abierta);
  if (filtros.caja) params.append('caja', filtros.caja);
  if (filtros.responsable) params.append('responsable', filtros.responsable);
  if (filtros.fecha_desde) params.append('fecha_desde', filtros.fecha_desde);
  if (filtros.fecha_hasta) params.append('fecha_hasta', filtros.fecha_hasta);
  if (filtros.search) params.append('search', filtros.search);

  const url = `/api/arqueo-caja/aperturas/?${params.toString()}`;

  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) throw new Error('Error al cargar aperturas');

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}

// Uso
cargarAperturas({ esta_abierta: true, caja: 1 })
  .then(aperturas => {
    console.log('Aperturas abiertas:', aperturas);
  });
```

### 2. Cargar Resumen Estadístico

```javascript
async function cargarResumen() {
  try {
    const response = await fetch('/api/arqueo-caja/aperturas/resumen/', {
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

### 3. Cargar Cajas Disponibles

```javascript
async function cargarCajasDisponibles() {
  try {
    const response = await fetch(
      '/api/arqueo-caja/cajas/?estado_actual=cerrada&activo=true',
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) throw new Error('Error al cargar cajas');

    const cajas = await response.json();
    return cajas;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

### 3.1. Cargar Responsables (Empleados con Roles Específicos)

**⭐ OPCIÓN RECOMENDADA: Endpoint dedicado para responsables de caja**

```javascript
async function cargarResponsables() {
  try {
    const response = await fetch(
      '/api/usuarios/responsables/?roles=Cajero,Admin',
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) throw new Error('Error al cargar responsables');

    const responsables = await response.json();

    /*
    Retorna:
    [
      {
        "empleado_id": 5,
        "usuario_id": 10,
        "nombre_completo": "Juan Pérez",
        "puesto": "Cajero",
        "email": "juan@example.com",
        "telefono": "0981234567",
        "roles": ["Cajero"]
      },
      ...
    ]
    */

    return responsables;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

**Query Parameters del endpoint `/api/usuarios/responsables/`:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `roles` | string | `"Cajero,Admin"` | Lista de roles separados por coma |
| `activo` | boolean | `true` | Filtrar solo usuarios activos |

**Ejemplos de uso:**

```javascript
// Solo cajeros
fetch('/api/usuarios/responsables/?roles=Cajero')

// Solo admins
fetch('/api/usuarios/responsables/?roles=Admin')

// Cajeros y admins (default)
fetch('/api/usuarios/responsables/?roles=Cajero,Admin')

// Múltiples roles personalizados
fetch('/api/usuarios/responsables/?roles=Cajero,Supervisor,Gerente')

// Incluir usuarios inactivos
fetch('/api/usuarios/responsables/?roles=Cajero&activo=false')
```

**OPCIONES ALTERNATIVAS:**

**Opción 2: Todos los empleados activos (sin filtro de rol)**
```javascript
async function cargarTodosLosEmpleados() {
  const response = await fetch('/api/empleados/todos/');
  const empleados = await response.json();
  // Retorna: [{ id: 5, nombre_completo: "Juan Pérez" }, ...]
  return empleados;
}
```

**Opción 3: Empleados con paginación y detalles completos**
```javascript
async function cargarEmpleadosDetallado() {
  const response = await fetch('/api/empleados/?activo=true');
  const data = await response.json();
  return data.results; // Incluye persona, puesto, salario, etc.
}
```

### 4. Obtener Responsables con Roles Específicos (⭐ Nuevo Endpoint)

**GET** `/api/usuarios/responsables/`

**⭐ ENDPOINT RECOMENDADO PARA APERTURAS DE CAJA**

Este endpoint especializado devuelve empleados que tienen roles específicos (ej: Cajero, Admin) y pueden ser asignados como responsables de una apertura de caja.

**Características:**
- ✅ Filtra usuarios por roles específicos
- ✅ Solo retorna usuarios activos con empleado asignado
- ✅ Respuesta optimizada para `<select>` en formularios
- ✅ Sin paginación (lista completa)
- ✅ Incluye información de puesto, email y teléfono

**Query Parameters:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `roles` | string | `"Cajero,Admin"` | Lista de roles separados por coma |
| `activo` | boolean | `"true"` | Filtrar solo usuarios activos |

**Ejemplos de Requests:**

```bash
# Cajeros y admins (default)
GET /api/usuarios/responsables/?roles=Cajero,Admin

# Solo cajeros
GET /api/usuarios/responsables/?roles=Cajero

# Solo administradores
GET /api/usuarios/responsables/?roles=Admin

# Múltiples roles personalizados
GET /api/usuarios/responsables/?roles=Cajero,Supervisor,Gerente

# Incluir usuarios inactivos
GET /api/usuarios/responsables/?roles=Cajero&activo=false
```

**Response 200 OK:**
```json
[
  {
    "empleado_id": 5,
    "usuario_id": 10,
    "nombre_completo": "Juan Pérez",
    "puesto": "Cajero",
    "email": "juan.perez@example.com",
    "telefono": "0981234567",
    "roles": ["Cajero"]
  },
  {
    "empleado_id": 7,
    "usuario_id": 12,
    "nombre_completo": "María García",
    "puesto": "Supervisor",
    "email": "maria.garcia@example.com",
    "telefono": "0987654321",
    "roles": ["Admin", "Supervisor"]
  },
  {
    "empleado_id": 8,
    "usuario_id": 15,
    "nombre_completo": "Carlos López",
    "puesto": "Cajero",
    "email": "carlos.lopez@example.com",
    "telefono": "0981111111",
    "roles": ["Cajero"]
  }
]
```

**Campos de la Respuesta:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `empleado_id` | integer | **ID del empleado** - Usar este valor en el campo `responsable` de la apertura |
| `usuario_id` | integer | ID del usuario (referencia) |
| `nombre_completo` | string | Nombre y apellido concatenados |
| `puesto` | string\|null | Nombre del puesto del empleado |
| `email` | string\|null | Email del empleado |
| `telefono` | string\|null | Teléfono del empleado |
| `roles` | array | Lista de nombres de roles asignados |

**IMPORTANTE:**
- El campo `responsable` en `AperturaCaja` es una ForeignKey a `Empleado`, NO a `Usuario`
- Al crear una apertura, debes enviar el valor de `empleado_id`, NO el `usuario_id`
- Este endpoint solo retorna empleados que tienen al menos un usuario asignado con los roles especificados

**Ejemplo de uso en formulario:**
```javascript
const responsables = await fetch('/api/usuarios/responsables/?roles=Cajero,Admin')
  .then(r => r.json());

// En el POST de la apertura, usar empleado_id:
const nuevaApertura = {
  caja: 1,
  responsable: responsables[0].empleado_id,  // ⭐ Usar empleado_id
  monto_inicial: "500000.00",
  // ...
};
```

### 5. Crear Nueva Apertura

```javascript
async function crearApertura(datos) {
  try {
    const response = await fetch('/api/arqueo-caja/aperturas/', {
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

    const apertura = await response.json();
    return apertura;
  } catch (error) {
    console.error('Error al crear apertura:', error);
    throw error;
  }
}

// Uso
const nuevaApertura = {
  caja: 1,
  responsable: 5,
  fecha_hora_apertura: new Date().toISOString(),
  monto_inicial: "500000.00",
  monto_inicial_alternativo: "68.49",
  observaciones_apertura: "Caja abierta con fondo de cambio habitual"
};

crearApertura(nuevaApertura)
  .then(apertura => {
    console.log('Apertura creada:', apertura);
    // Recargar listado
    cargarAperturas();
  })
  .catch(error => {
    // Mostrar errores de validación
    if (error.caja) {
      alert(error.caja[0]);
    }
    if (error.non_field_errors) {
      alert(error.non_field_errors[0]);
    }
  });
```

### 5. Obtener Detalle de Apertura

```javascript
async function obtenerDetalleApertura(id) {
  try {
    // Cargar datos en paralelo
    const [apertura, movimientos] = await Promise.all([
      fetch(`/api/arqueo-caja/aperturas/${id}/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json()),

      fetch(`/api/arqueo-caja/movimientos/?apertura=${id}&limit=5&ordering=-fecha_hora`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json())
    ]);

    // Si está abierta, obtener saldo actual de la caja
    let saldoActual = null;
    if (apertura.esta_abierta) {
      const estadoCaja = await fetch(
        `/api/arqueo-caja/cajas/${apertura.caja}/estado/`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      ).then(r => r.json());

      saldoActual = estadoCaja.saldo_actual;
    }

    return { apertura, movimientos, saldoActual };
  } catch (error) {
    console.error('Error al cargar detalle:', error);
    throw error;
  }
}

// Uso
obtenerDetalleApertura(1)
  .then(({ apertura, movimientos, saldoActual }) => {
    console.log('Detalle de apertura:', apertura);
    console.log('Movimientos recientes:', movimientos);
    console.log('Saldo actual:', saldoActual);
  });
```

### 6. Actualizar Apertura

```javascript
async function actualizarApertura(id, datos) {
  try {
    const response = await fetch(`/api/arqueo-caja/aperturas/${id}/`, {
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

    const apertura = await response.json();
    return apertura;
  } catch (error) {
    console.error('Error al actualizar apertura:', error);
    throw error;
  }
}

// Uso
actualizarApertura(1, {
  observaciones_apertura: "Observaciones actualizadas"
})
  .then(apertura => {
    console.log('Apertura actualizada:', apertura);
  })
  .catch(error => {
    if (error.non_field_errors) {
      alert(error.non_field_errors[0]);
    }
  });
```

### 7. Formatear Fecha y Hora

```javascript
function formatearFechaHora(isoString) {
  const fecha = new Date(isoString);

  const dia = fecha.getDate().toString().padStart(2, '0');
  const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
  const año = fecha.getFullYear();
  const hora = fecha.getHours().toString().padStart(2, '0');
  const minutos = fecha.getMinutes().toString().padStart(2, '0');

  return {
    fecha: `${dia}/${mes}/${año}`,
    hora: `${hora}:${minutos}`,
    completo: `${dia}/${mes}/${año} ${hora}:${minutos}`
  };
}

// Uso
const apertura = {
  fecha_hora_apertura: "2025-11-12T08:00:00Z"
};

const formato = formatearFechaHora(apertura.fecha_hora_apertura);
console.log(formato.completo);  // "12/11/2025 08:00"
```

### 8. Calcular Duración

```javascript
function calcularDuracion(fechaApertura, fechaCierre = null) {
  const inicio = new Date(fechaApertura);
  const fin = fechaCierre ? new Date(fechaCierre) : new Date();

  const diffMs = fin - inicio;
  const diffHoras = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutos = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  return {
    horas: diffHoras,
    minutos: diffMinutos,
    texto: `${diffHoras}h ${diffMinutos}m`,
    estaAbierta: !fechaCierre
  };
}

// Uso
const apertura = {
  fecha_hora_apertura: "2025-11-12T08:00:00Z",
  esta_abierta: true
};

const duracion = calcularDuracion(apertura.fecha_hora_apertura);
console.log(duracion.texto);  // "4h 30m"
console.log(duracion.estaAbierta ? "(abierta actualmente)" : "");
```

### 9. Formatear Monto

```javascript
function formatearMonto(monto, moneda = 'PYG') {
  const valor = parseFloat(monto);

  if (moneda === 'PYG') {
    return `Gs ${valor.toLocaleString('es-PY', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    })}`;
  } else if (moneda === 'USD') {
    return `USD ${valor.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`;
  }

  return valor.toLocaleString();
}

// Uso
console.log(formatearMonto("500000.00", "PYG"));  // "Gs 500,000"
console.log(formatearMonto("68.49", "USD"));      // "USD 68.49"
```

---

## Componentes React (Ejemplo)

### ListadoAperturas.jsx

```jsx
import React, { useState, useEffect } from 'react';

const ListadoAperturas = () => {
  const [aperturas, setAperturas] = useState([]);
  const [resumen, setResumen] = useState([]);
  const [filtros, setFiltros] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cargarDatos();
  }, [filtros]);

  const cargarDatos = async () => {
    setLoading(true);
    try {
      const [aperturasData, resumenData] = await Promise.all([
        cargarAperturas(filtros),
        cargarResumen()
      ]);
      setAperturas(aperturasData);
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

  const handleNuevaApertura = () => {
    // Abrir modal de nueva apertura
    abrirModalNuevaApertura();
  };

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="gestion-aperturas">
      <header>
        <h1>📂 Gestión de Aperturas de Caja</h1>
        <button onClick={handleNuevaApertura}>+ Nueva Apertura</button>
      </header>

      {/* Resumen */}
      <ResumenEstadistico data={resumen} />

      {/* Filtros */}
      <FiltrosAperturas onChange={handleFiltroChange} />

      {/* Tabla */}
      <TablaAperturas aperturas={aperturas} onReload={cargarDatos} />
    </div>
  );
};

export default ListadoAperturas;
```

### ModalNuevaApertura.jsx

```jsx
import React, { useState, useEffect } from 'react';

const ModalNuevaApertura = ({ isOpen, onClose, onSuccess }) => {
  const [cajasDisponibles, setCajasDisponibles] = useState([]);
  const [responsables, setResponsables] = useState([]);
  const [formData, setFormData] = useState({
    caja: '',
    responsable: '',
    fecha_hora_apertura: new Date().toISOString().slice(0, 16),
    monto_inicial: '',
    monto_inicial_alternativo: '',
    observaciones_apertura: ''
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      cargarDatosIniciales();
    }
  }, [isOpen]);

  const cargarDatosIniciales = async () => {
    try {
      const [cajas, responsables] = await Promise.all([
        cargarCajasDisponibles(),
        cargarResponsables() // Usa /api/usuarios/responsables/?roles=Cajero,Admin
      ]);
      setCajasDisponibles(cajas);
      setResponsables(responsables); // Array de { empleado_id, nombre_completo, ... }
    } catch (error) {
      console.error('Error al cargar datos:', error);
    }
  };

  const handleChange = (campo, valor) => {
    setFormData(prev => ({ ...prev, [campo]: valor }));
    // Limpiar error del campo al cambiar
    if (errors[campo]) {
      setErrors(prev => ({ ...prev, [campo]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrors({});

    try {
      const apertura = await crearApertura(formData);
      onSuccess(apertura);
      onClose();
    } catch (error) {
      setErrors(error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal">
      <div className="modal-content">
        <header>
          <h2>✏️ Nueva Apertura de Caja</h2>
          <button onClick={onClose}>✕</button>
        </header>

        <form onSubmit={handleSubmit}>
          {/* Caja */}
          <div className="form-group">
            <label>* Caja</label>
            <select
              value={formData.caja}
              onChange={(e) => handleChange('caja', e.target.value)}
              required
            >
              <option value="">Seleccione una caja...</option>
              {cajasDisponibles.map(caja => (
                <option key={caja.id} value={caja.id}>
                  #{caja.numero_caja} - {caja.nombre}
                </option>
              ))}
            </select>
            {errors.caja && <span className="error">{errors.caja[0]}</span>}
          </div>

          {/* Responsable */}
          <div className="form-group">
            <label>* Responsable</label>
            <select
              value={formData.responsable}
              onChange={(e) => handleChange('responsable', e.target.value)}
              required
            >
              <option value="">Seleccione un responsable...</option>
              {responsables.map(resp => (
                <option key={resp.empleado_id} value={resp.empleado_id}>
                  {resp.nombre_completo} {resp.puesto && `- ${resp.puesto}`}
                </option>
              ))}
            </select>
            {errors.responsable && <span className="error">{errors.responsable[0]}</span>}
            <small className="form-hint">
              ℹ️ Solo se muestran empleados con rol de Cajero o Admin
            </small>
          </div>

          {/* Fecha y hora */}
          <div className="form-group">
            <label>* Fecha y Hora de Apertura</label>
            <input
              type="datetime-local"
              value={formData.fecha_hora_apertura}
              onChange={(e) => handleChange('fecha_hora_apertura', e.target.value)}
              max={new Date().toISOString().slice(0, 16)}
              required
            />
            {errors.fecha_hora_apertura && (
              <span className="error">{errors.fecha_hora_apertura[0]}</span>
            )}
          </div>

          {/* Monto inicial */}
          <div className="form-group">
            <label>* Monto Inicial (Gs)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.monto_inicial}
              onChange={(e) => handleChange('monto_inicial', e.target.value)}
              placeholder="0.00"
              required
            />
            {errors.monto_inicial && (
              <span className="error">{errors.monto_inicial[0]}</span>
            )}
          </div>

          {/* Monto inicial alternativo */}
          <div className="form-group">
            <label>Monto Inicial (USD) - Opcional</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.monto_inicial_alternativo}
              onChange={(e) => handleChange('monto_inicial_alternativo', e.target.value)}
              placeholder="0.00"
            />
          </div>

          {/* Observaciones */}
          <div className="form-group">
            <label>Observaciones</label>
            <textarea
              value={formData.observaciones_apertura}
              onChange={(e) => handleChange('observaciones_apertura', e.target.value)}
              rows="3"
              placeholder="Observaciones opcionales..."
            />
          </div>

          {/* Errores generales */}
          {errors.non_field_errors && (
            <div className="error-general">
              {errors.non_field_errors[0]}
            </div>
          )}

          {/* Botones */}
          <footer>
            <button type="button" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" disabled={loading}>
              {loading ? 'Abriendo...' : '💾 Abrir Caja'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
};

export default ModalNuevaApertura;
```

---

## Notas Finales

### Consideraciones de UX

1. **Feedback Visual**: Mostrar loaders durante las peticiones
2. **Mensajes de Error**: Mostrar errores de validación en los campos correspondientes
3. **Confirmaciones**: Pedir confirmación antes de cerrar una caja
4. **Notificaciones**: Toast/Snackbar para éxito/error de operaciones
5. **Responsive**: Adaptar tabla a dispositivos móviles (cards en lugar de tabla)
6. **Tiempo Real**: Mostrar duración actualizada para aperturas abiertas
7. **Auto-refresh**: Actualizar listado cada cierto tiempo para reflejar cambios

### Optimizaciones

- **Debounce** en el campo de búsqueda (300-500ms)
- **Cache** de datos de resumen (actualizar cada 30 segundos)
- **Paginación** del lado del servidor para grandes volúmenes
- **Lazy loading** de movimientos en el modal de detalle
- **WebSockets** (opcional) para actualizaciones en tiempo real de estado de cajas

### Accesibilidad

- Labels descriptivos en todos los campos
- Atributos ARIA en elementos interactivos
- Navegación por teclado en modales
- Contraste de colores adecuado para indicadores de estado
- Mensajes de error claramente identificables

### Seguridad

- Validar permisos del usuario antes de permitir crear/editar aperturas
- Solo mostrar cajas y usuarios a los que el usuario tiene acceso
- Registrar auditoría de todas las operaciones (creación, edición)
- Proteger endpoints con autenticación y autorización adecuadas

### Notas sobre el Modelo de Datos

**¿Por qué el responsable es un Empleado y no un Usuario?**

El sistema utiliza `Empleado` como responsable de las aperturas por las siguientes razones:

1. **Separación de Conceptos**:
   - `Empleado`: Persona que trabaja en la empresa (datos laborales: puesto, salario, fecha de ingreso)
   - `Usuario`: Cuenta del sistema con permisos y roles de acceso

2. **Flexibilidad**:
   - No todos los empleados necesitan tener acceso al sistema
   - Un empleado puede ser responsable de caja sin necesitar login
   - Ejemplo: Cajero temporal que solo trabaja físicamente

3. **Relación del Modelo**:
   ```
   Usuario (1) -----> (0..1) Empleado
   ```
   - Un Usuario puede tener UN Empleado asociado (OneToOne opcional)
   - Un Empleado puede existir sin Usuario

4. **Implementación Actual**:
   - `AperturaCaja.responsable` → ForeignKey a `Empleado`
   - El endpoint `/api/usuarios/responsables/` filtra por roles de Usuario
   - Retorna `empleado_id` para usar en el campo `responsable`

**Flujo Completo**:
1. Usuario frontend consulta `/api/usuarios/responsables/?roles=Cajero,Admin`
2. Backend filtra usuarios por rol que tengan empleado asignado
3. Respuesta incluye `empleado_id` + datos del empleado
4. Frontend usa `empleado_id` en el POST de la apertura
5. Backend valida y crea apertura con `responsable = empleado_id`

---

**Fecha de creación**: 13/11/2025
**Última actualización**: 13/11/2025
**Versión**: 1.1
**Cambios v1.1**:
- Agregado endpoint `/api/usuarios/responsables/` para filtrar por roles
- Documentada la relación Usuario ↔ Empleado
- Ejemplos actualizados con el nuevo endpoint

**Mantenedores**: Equipo Backend - GroupTours
