# Documentación: Sistema de Facturación por Modalidades (Global e Individual)

## 📋 Resumen

El sistema soporta dos modalidades de facturación:

1. **Modalidad GLOBAL**: Una factura única para toda la reserva
   - Campo: `puede_descargar_factura_global` (en la reserva)

2. **Modalidad INDIVIDUAL**: Una factura por cada pasajero
   - Campo: `puede_descargar_factura` (en cada pasajero)

**Ambos campos se actualizan automáticamente** después de:
- ✅ Registrar pagos (`POST /api/reserva/{id}/registrar-pago/`)
- ✅ Asignar persona real (`PATCH /api/pasajeros/{id}/`)
- ✅ Cualquier consulta al detalle de reserva (`GET /api/reserva/{id}/`)

## 📊 Comparación de Modalidades

| Característica | MODALIDAD GLOBAL | MODALIDAD INDIVIDUAL |
|----------------|------------------|----------------------|
| **Campo indicador** | `puede_descargar_factura_global` | `puede_descargar_factura` |
| **Ubicación** | En la `Reserva` | En cada `Pasajero` |
| **Una factura por** | Toda la reserva | Cada pasajero |
| **Se actualiza tras pago** | ✅ Sí | ✅ Sí |
| **Se actualiza tras asignar pasajero** | ✅ Sí (indirectamente) | ✅ Sí (directamente) |

## 🎯 Condiciones para Habilitar Facturación

### Modalidad GLOBAL

Para que `puede_descargar_factura_global = true`, la reserva debe cumplir:

1. ✅ **Reserva en modalidad `'global'`**
2. ✅ **Reserva en estado `'finalizada'`**
3. ✅ **Reserva totalmente pagada** (`esta_totalmente_pagada() = true`)

### Modalidad INDIVIDUAL

Para que `puede_descargar_factura = true`, **cada pasajero** debe cumplir:

1. ✅ **Reserva en modalidad `'individual'`**
2. ✅ **Reserva en estado `'confirmada'` o `'finalizada'`**
3. ✅ **Pasajero totalmente pagado** (`esta_totalmente_pagado = true`)
4. ✅ **Pasajero con datos reales** (`por_asignar = false`)

## 📊 Escenarios de Uso

### Escenario 1: Registro de Pago con Pasajero Real

**Situación:** El pasajero ya tiene sus datos cargados desde el inicio.

```json
// Estado inicial
{
  "id": 1,
  "persona": {
    "id": 5,
    "nombre": "Juan",
    "apellido": "Pérez"
  },
  "por_asignar": false,          // ✅ Tiene datos reales
  "precio_asignado": 5000.00,
  "monto_pagado": 0.00,
  "puede_descargar_factura": false  // ❌ No pagado
}

// Después de registrar pago completo
POST /api/reserva/1/registrar-pago/
{
  "tipo": "pago_total",
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": 1, "monto": 5000.00}
  ]
}

// Estado final
{
  "id": 1,
  "persona": {...},
  "por_asignar": false,
  "precio_asignado": 5000.00,
  "monto_pagado": 5000.00,           // ✅ Pagado completo
  "esta_totalmente_pagado": true,     // ✅
  "puede_descargar_factura": true     // ✅ Botón habilitado
}
```

### Escenario 2: Pago Primero, Asignación Después

**Situación:** Se registra el pago para un pasajero temporal "Por Asignar", y luego se asigna la persona real.

#### Paso 1: Pago a pasajero temporal

```json
// Estado inicial - Pasajero temporal
{
  "id": 3,
  "persona": {
    "id": 10,
    "nombre": "Por Asignar 1",
    "documento": "12345678_PEND_1"
  },
  "por_asignar": true,              // ❌ Es temporal
  "precio_asignado": 5000.00,
  "monto_pagado": 0.00,
  "puede_descargar_factura": false
}

// Registro de pago
POST /api/reserva/1/registrar-pago/
{
  "tipo": "pago_total",
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": "pendiente_1", "monto": 5000.00}
  ]
}

// Estado después del pago
{
  "id": 3,
  "persona": {
    "id": 10,
    "nombre": "Por Asignar 1",
    "documento": "12345678_PEND_1"
  },
  "por_asignar": true,              // ❌ Sigue siendo temporal
  "precio_asignado": 5000.00,
  "monto_pagado": 5000.00,          // ✅ Pagado completo
  "esta_totalmente_pagado": true,   // ✅
  "puede_descargar_factura": false  // ❌ No tiene datos reales
}
```

#### Paso 2: Asignación de persona real

```json
// Actualización del pasajero con persona real
PATCH /api/pasajeros/3/
{
  "persona_id": 25  // ID de la PersonaFisica real
}

// ⚡ El sistema automáticamente:
// 1. Detecta que se asignó una persona real
// 2. Cambia por_asignar de true a false
// 3. Recalcula puede_descargar_factura

// Estado final (respuesta del PATCH)
{
  "id": 3,
  "persona": {
    "id": 25,
    "nombre": "María",
    "apellido": "González",
    "documento": "87654321"
  },
  "por_asignar": false,             // ✅ Cambiado automáticamente
  "precio_asignado": 5000.00,
  "monto_pagado": 5000.00,          // ✅ Ya estaba pagado
  "esta_totalmente_pagado": true,   // ✅
  "puede_descargar_factura": true   // ✅ ¡Ahora está habilitado!
}
```

## 🔄 Flujo Completo de Facturación Individual

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Crear Reserva con modalidad 'individual'                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Registrar Pago (seña o total)                           │
│    - Puede ser para pasajero real o "por asignar"          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3a. Si pasajero es REAL + pagado 100%                      │
│     → puede_descargar_factura = true ✅                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3b. Si pasajero es TEMPORAL + pagado 100%                  │
│     → puede_descargar_factura = false ❌                    │
│     → Asignar persona real (PATCH /api/pasajeros/{id}/)    │
│     → por_asignar cambia a false automáticamente            │
│     → puede_descargar_factura cambia a true ✅              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Frontend muestra botón "Generar y Descargar Factura"    │
│    (solo si puede_descargar_factura = true)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Usuario hace clic en el botón                           │
│    → Llama al endpoint de generación de factura individual │
│    → Se genera la factura PDF                               │
│    → factura_id obtiene un valor                            │
└─────────────────────────────────────────────────────────────┘
```

## 🔍 Verificación de Estados

### Consultar detalle de reserva

```http
GET /api/reserva/1/
```

**Respuesta:**

```json
{
  "id": 1,
  "codigo": "RSV-2025-0001",
  "estado": "confirmada",
  "modalidad_facturacion": "individual",
  "pasajeros": [
    {
      "id": 1,
      "persona": {"nombre": "Juan", "apellido": "Pérez"},
      "por_asignar": false,
      "monto_pagado": 5000.00,
      "esta_totalmente_pagado": true,
      "puede_descargar_factura": true,  // ✅ Listo para generar
      "factura_id": null  // null = no generada aún
    },
    {
      "id": 2,
      "persona": {"nombre": "María", "apellido": "González"},
      "por_asignar": false,
      "monto_pagado": 3000.00,
      "esta_totalmente_pagado": false,
      "puede_descargar_factura": false,  // ❌ Falta pago
      "factura_id": null
    },
    {
      "id": 3,
      "persona": {"nombre": "Por Asignar 3"},
      "por_asignar": true,
      "monto_pagado": 5000.00,
      "esta_totalmente_pagado": true,
      "puede_descargar_factura": false,  // ❌ Falta asignar persona
      "factura_id": null
    }
  ]
}
```

## 🎨 Guía para el Frontend

### Mostrar estado del botón

```javascript
function renderBotonFactura(pasajero) {
  if (pasajero.puede_descargar_factura) {
    if (pasajero.factura_id) {
      // Ya tiene factura generada
      return (
        <Button onClick={() => descargarFactura(pasajero.factura_id)}>
          📄 Descargar Factura
        </Button>
      );
    } else {
      // Puede generar la factura
      return (
        <Button onClick={() => generarYDescargarFactura(pasajero.id)}>
          ✨ Generar y Descargar Factura
        </Button>
      );
    }
  } else {
    // Mostrar por qué no puede generar
    const motivos = [];

    if (pasajero.por_asignar) {
      motivos.push("Falta asignar pasajero real");
    }
    if (!pasajero.esta_totalmente_pagado) {
      motivos.push(`Saldo pendiente: ${pasajero.saldo_pendiente}`);
    }
    if (pasajero.reserva.modalidad_facturacion !== 'individual') {
      motivos.push("Reserva en modalidad global");
    }

    return (
      <Button disabled title={motivos.join(", ")}>
        🔒 Factura No Disponible
      </Button>
    );
  }
}
```

### Flujo de asignación de pasajero

```javascript
async function asignarPasajeroReal(pasajeroId, personaId) {
  // 1. Actualizar el pasajero
  const response = await fetch(`/api/pasajeros/${pasajeroId}/`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({persona_id: personaId})
  });

  const pasajeroActualizado = await response.json();

  // 2. Verificar si ahora puede generar factura
  if (pasajeroActualizado.puede_descargar_factura) {
    // ✅ El pasajero ahora cumple las condiciones
    // Mostrar notificación al usuario
    showNotification(
      'success',
      '✅ Pasajero asignado. Factura disponible para generar.'
    );

    // Habilitar el botón de factura
    actualizarUI(pasajeroActualizado);
  }
}
```

## 📌 Notas Importantes

1. **Campo calculado:** `puede_descargar_factura` es un SerializerMethodField que se calcula dinámicamente en cada consulta. No es un campo de la base de datos.

2. **Actualización automática:** Cuando se asigna una persona real a un pasajero "por asignar", el sistema automáticamente:
   - Cambia `por_asignar` a `false`
   - Recalcula `puede_descargar_factura` en la respuesta

3. **No hay auto-generación:** Las facturas NO se generan automáticamente al registrar pagos. El usuario debe hacer clic en el botón cuando lo necesite.

4. **Factura única:** Un pasajero solo puede tener una factura individual activa. Si ya existe, no se puede generar otra.

5. **Consulta actualizada:** Después de asignar un pasajero o registrar un pago, el frontend puede:
   - Usar la respuesta directa del endpoint (que incluye el campo actualizado)
   - Hacer una nueva consulta a `/api/reserva/{id}/` para obtener todos los pasajeros actualizados

## 🔗 Endpoints Relacionados

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/reserva/{id}/` | GET | Detalle completo de reserva con pasajeros |
| `/api/reserva/{id}/registrar-pago/` | POST | Registrar pago (seña o total) |
| `/api/pasajeros/{id}/` | PATCH | Actualizar pasajero (asignar persona real) |
| `/api/pasajeros/{id}/estado-cuenta/` | GET | Estado de cuenta detallado del pasajero |

## 🔄 Actualización Automática de Campos

### ¿Cuándo se actualizan los campos?

Los campos `puede_descargar_factura` y `puede_descargar_factura_global` son **campos calculados dinámicamente** (SerializerMethodField). Esto significa que:

1. **NO se guardan en la base de datos**
2. **Se calculan en cada consulta**
3. **Siempre reflejan el estado actual**

### Ejemplo: Modalidad Global

```json
// ANTES del último pago
GET /api/reserva/1/

{
  "id": 1,
  "estado": "confirmada",
  "modalidad_facturacion": "global",
  "monto_pagado": 14000.00,
  "costo_total_estimado": 15000.00,
  "esta_totalmente_pagada": false,
  "puede_descargar_factura_global": false  // ❌ No pagado completo
}

// Registrar último pago
POST /api/reserva/1/registrar-pago/
{ "tipo": "pago_total", "metodo_pago": "transferencia",
  "distribuciones": [{"pasajero": 1, "monto": 1000.00}] }

// DESPUÉS del último pago
GET /api/reserva/1/

{
  "id": 1,
  "estado": "finalizada",  // ✅ Cambió automáticamente
  "modalidad_facturacion": "global",
  "monto_pagado": 15000.00,
  "costo_total_estimado": 15000.00,
  "esta_totalmente_pagada": true,  // ✅
  "puede_descargar_factura_global": true  // ✅ Ahora está habilitado!
}
```

### Ejemplo: Modalidad Individual

```json
// ANTES de asignar persona
GET /api/reserva/1/

{
  "modalidad_facturacion": "individual",
  "pasajeros": [
    {
      "id": 3,
      "por_asignar": true,
      "monto_pagado": 5000.00,
      "esta_totalmente_pagado": true,
      "puede_descargar_factura": false  // ❌ Es temporal
    }
  ]
}

// Asignar persona real
PATCH /api/pasajeros/3/
{ "persona_id": 25 }

// Respuesta del PATCH (automáticamente actualizado)
{
  "id": 3,
  "por_asignar": false,  // ✅ Cambió automáticamente
  "monto_pagado": 5000.00,
  "esta_totalmente_pagado": true,
  "puede_descargar_factura": true  // ✅ Ahora está habilitado!
}

// También se ve reflejado en GET /api/reserva/1/
{
  "pasajeros": [
    {
      "id": 3,
      "por_asignar": false,
      "puede_descargar_factura": true  // ✅
    }
  ]
}
```

## 🎨 Implementación Frontend - Ambas Modalidades

```javascript
function renderBotonFactura(reserva) {
  if (reserva.modalidad_facturacion === 'global') {
    // MODALIDAD GLOBAL: Un botón para toda la reserva
    if (reserva.puede_descargar_factura_global) {
      return (
        <Button onClick={() => generarFacturaGlobal(reserva.id)}>
          {reserva.factura_global_id
            ? "📄 Descargar Factura Global"
            : "✨ Generar Factura Global"}
        </Button>
      );
    } else {
      return (
        <Button disabled title={motivoDeshabilitado(reserva)}>
          🔒 Factura Global No Disponible
        </Button>
      );
    }
  } else if (reserva.modalidad_facturacion === 'individual') {
    // MODALIDAD INDIVIDUAL: Un botón por cada pasajero
    return (
      <div>
        {reserva.pasajeros.map(pasajero => (
          <div key={pasajero.id}>
            <span>{pasajero.persona.nombre}</span>
            {pasajero.puede_descargar_factura ? (
              <Button onClick={() => generarFacturaIndividual(pasajero.id)}>
                {pasajero.factura_id
                  ? "📄 Descargar"
                  : "✨ Generar Factura"}
              </Button>
            ) : (
              <Button disabled title={motivoDeshabilitado(pasajero)}>
                🔒 No Disponible
              </Button>
            )}
          </div>
        ))}
      </div>
    );
  }
}

function motivoDeshabilitado(obj) {
  const motivos = [];

  if (obj.modalidad_facturacion === 'global') {
    // Verificación para factura global
    if (obj.estado !== 'finalizada') {
      motivos.push(`Estado: ${obj.estado} (debe estar finalizada)`);
    }
    if (!obj.esta_totalmente_pagada) {
      motivos.push(`Saldo pendiente: ${obj.saldo_pendiente}`);
    }
  } else {
    // Verificación para factura individual (pasajero)
    if (obj.por_asignar) {
      motivos.push("Falta asignar pasajero real");
    }
    if (!obj.esta_totalmente_pagado) {
      motivos.push(`Saldo pendiente: ${obj.saldo_pendiente}`);
    }
    if (obj.reserva.estado === 'pendiente') {
      motivos.push("Reserva no confirmada");
    }
  }

  return motivos.join(" | ");
}
```

## ✅ Checklist de Implementación Frontend

### Para ambas modalidades:
- [ ] Detectar `modalidad_facturacion` de la reserva
- [ ] Mostrar UI diferente según la modalidad

### Para Modalidad Global:
- [ ] Mostrar botón "Generar Factura Global" si `puede_descargar_factura_global = true`
- [ ] Verificar `factura_global_id` para cambiar texto (generar vs descargar)
- [ ] Deshabilitar botón con tooltip si no cumple condiciones

### Para Modalidad Individual:
- [ ] Mostrar botón "Generar Factura" por cada pasajero si `puede_descargar_factura = true`
- [ ] Cambiar texto del botón según `factura_id` (generar vs descargar)
- [ ] Deshabilitar botón con tooltip explicativo si no cumple condiciones
- [ ] Actualizar UI después de asignar pasajero real
- [ ] Manejar el caso de pasajeros "Por Asignar" pagados completamente
- [ ] Mostrar indicadores visuales del estado de pago por pasajero
- [ ] Permitir generar facturas independientemente (no todas a la vez)
