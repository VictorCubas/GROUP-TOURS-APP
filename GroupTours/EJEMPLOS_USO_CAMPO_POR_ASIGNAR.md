# Guía de Uso: Campo `por_asignar` en Pasajeros

## 📋 Descripción

El campo `por_asignar` es un booleano que identifica de forma eficiente si un pasajero está pendiente de asignación o tiene datos reales.

**Valores:**
- `true`: Pasajero pendiente de asignación (placeholder "Por Asignar")
- `false`: Pasajero con datos reales de una persona

---

## 🎯 Casos de Uso

### 1. Obtener detalles de una reserva

**Endpoint:**
```http
GET /api/reservas/180/
```

**Respuesta:**
```json
{
  "id": 180,
  "codigo": "RSV-2025-0180",
  "estado": "confirmada",
  "estado_display": "Confirmado Incompleto",
  "cantidad_pasajeros": 4,
  "pasajeros": [
    {
      "id": 450,
      "persona": {
        "id": 5,
        "nombre": "Juan",
        "apellido": "Pérez",
        "documento": "12345678"
      },
      "es_titular": true,
      "por_asignar": false,  // ✅ Pasajero con datos reales
      "precio_asignado": 3536.00,
      "monto_pagado": 220.00
    },
    {
      "id": 451,
      "persona": {
        "id": 23,
        "nombre": "Por Asignar 2",
        "apellido": "",
        "documento": "12345678_PEND_2"
      },
      "es_titular": false,
      "por_asignar": true,  // ⚠️ Pendiente de asignación
      "precio_asignado": 3536.00,
      "monto_pagado": 220.00
    },
    {
      "id": 452,
      "persona": {
        "id": 24,
        "nombre": "Por Asignar 3",
        "apellido": "",
        "documento": "12345678_PEND_3"
      },
      "es_titular": false,
      "por_asignar": true,  // ⚠️ Pendiente de asignación
      "precio_asignado": 3536.00,
      "monto_pagado": 220.00
    },
    {
      "id": 453,
      "persona": {
        "id": 25,
        "nombre": "Por Asignar 4",
        "apellido": "",
        "documento": "12345678_PEND_4"
      },
      "es_titular": false,
      "por_asignar": true,  // ⚠️ Pendiente de asignación
      "precio_asignado": 3536.00,
      "monto_pagado": 220.00
    }
  ]
}
```

---

### 2. Filtrar pasajeros en el frontend

**JavaScript/TypeScript:**
```typescript
// Obtener reserva
const response = await fetch('/api/reservas/180/');
const reserva = await response.json();

// Filtrar pasajeros pendientes
const pasajerosPendientes = reserva.pasajeros.filter(p => p.por_asignar === true);
console.log(`Hay ${pasajerosPendientes.length} pasajeros pendientes de asignación`);

// Filtrar pasajeros con datos reales
const pasajerosReales = reserva.pasajeros.filter(p => p.por_asignar === false);
console.log(`Hay ${pasajerosReales.length} pasajeros con datos completos`);
```

**Salida:**
```
Hay 3 pasajeros pendientes de asignación
Hay 1 pasajeros con datos completos
```

---

### 3. Mostrar badge en UI según estado

**React:**
```tsx
function PasajeroItem({ pasajero }) {
  return (
    <div className="pasajero-card">
      <div className="pasajero-info">
        <h3>{pasajero.persona.nombre} {pasajero.persona.apellido}</h3>
        <p>Documento: {pasajero.persona.documento}</p>

        {/* Badge según estado */}
        {pasajero.por_asignar ? (
          <span className="badge badge-warning">
            ⚠️ Pendiente de asignación
          </span>
        ) : (
          <span className="badge badge-success">
            ✓ Datos completos
          </span>
        )}
      </div>

      <div className="pasajero-acciones">
        {pasajero.por_asignar && (
          <button onClick={() => asignarPasajero(pasajero.id)}>
            Asignar Persona
          </button>
        )}
      </div>
    </div>
  );
}
```

---

### 4. Validar si la reserva está completa

**JavaScript:**
```javascript
function validarReservaCompleta(reserva) {
  const tienePasajerosPendientes = reserva.pasajeros.some(p => p.por_asignar === true);

  if (tienePasajerosPendientes) {
    const cantidadPendientes = reserva.pasajeros.filter(p => p.por_asignar).length;
    return {
      completa: false,
      mensaje: `Faltan ${cantidadPendientes} pasajeros por asignar`,
      pendientes: reserva.pasajeros.filter(p => p.por_asignar)
    };
  }

  return {
    completa: true,
    mensaje: 'Todos los pasajeros están asignados'
  };
}

// Uso
const resultado = validarReservaCompleta(reserva);
console.log(resultado.mensaje);
// Output: "Faltan 3 pasajeros por asignar"
```

---

### 5. Actualizar un pasajero "Por Asignar"

**Flujo completo:**

#### Paso 1: Obtener pasajeros pendientes
```http
GET /api/reservas/180/detalle-pasajeros/
```

**Respuesta:**
```json
[
  {
    "id": 451,
    "persona": {
      "nombre": "Por Asignar 2",
      "documento": "12345678_PEND_2"
    },
    "por_asignar": true
  }
]
```

#### Paso 2: Crear o seleccionar PersonaFisica real
```http
POST /api/personas/
{
  "nombre": "María",
  "apellido": "González",
  "documento": "87654321",
  "tipo_documento": 1,
  "email": "maria@email.com",
  "telefono": "0991234567",
  "nacionalidad": 1,
  "fecha_nacimiento": "1990-05-15",
  "sexo": "F"
}
```

**Respuesta:**
```json
{
  "id": 15,
  "nombre": "María",
  "documento": "87654321"
}
```

#### Paso 3: Asignar la persona al pasajero
```http
PATCH /api/reservas/pasajeros/451/
{
  "persona_id": 15
}
```

**Respuesta:**
```json
{
  "id": 451,
  "persona": {
    "id": 15,
    "nombre": "María",
    "apellido": "González",
    "documento": "87654321"
  },
  "por_asignar": false,  // ✅ Se actualizó automáticamente
  "monto_pagado": 220.00
}
```

---

### 6. Mostrar progreso de asignación

**React:**
```tsx
function ProgresoPasajeros({ pasajeros }) {
  const total = pasajeros.length;
  const asignados = pasajeros.filter(p => !p.por_asignar).length;
  const porcentaje = (asignados / total) * 100;

  return (
    <div className="progreso-pasajeros">
      <h4>Progreso de Asignación de Pasajeros</h4>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${porcentaje}%` }}
        >
          {asignados} / {total}
        </div>
      </div>
      <p>
        {asignados === total
          ? '✓ Todos los pasajeros asignados'
          : `Faltan ${total - asignados} pasajeros por asignar`
        }
      </p>
    </div>
  );
}
```

---

### 7. Listar solo pasajeros pendientes

**Python (en views o servicios):**
```python
from apps.reserva.models import Pasajero

# Obtener solo pasajeros pendientes de una reserva
pasajeros_pendientes = Pasajero.objects.filter(
    reserva_id=180,
    por_asignar=True
)

print(f"Pasajeros pendientes: {pasajeros_pendientes.count()}")
for pasajero in pasajeros_pendientes:
    print(f"  - ID: {pasajero.id} | {pasajero.persona.nombre}")
```

**Salida:**
```
Pasajeros pendientes: 3
  - ID: 451 | Por Asignar 2
  - ID: 452 | Por Asignar 3
  - ID: 453 | Por Asignar 4
```

---

### 8. Dashboard con estadísticas

**JavaScript:**
```javascript
function calcularEstadisticasReserva(reserva) {
  const stats = {
    total: reserva.cantidad_pasajeros,
    asignados: 0,
    pendientes: 0,
    porcentajeCompletado: 0
  };

  reserva.pasajeros.forEach(pasajero => {
    if (pasajero.por_asignar) {
      stats.pendientes++;
    } else {
      stats.asignados++;
    }
  });

  stats.porcentajeCompletado = (stats.asignados / stats.total) * 100;

  return stats;
}

// Uso
const stats = calcularEstadisticasReserva(reserva);
console.log(`
Estadísticas de Reserva ${reserva.codigo}:
- Total pasajeros: ${stats.total}
- Asignados: ${stats.asignados}
- Pendientes: ${stats.pendientes}
- Progreso: ${stats.porcentajeCompletado.toFixed(1)}%
`);
```

**Salida:**
```
Estadísticas de Reserva RSV-2025-0180:
- Total pasajeros: 4
- Asignados: 1
- Pendientes: 3
- Progreso: 25.0%
```

---

## 🔄 Flujo Automático

### Al crear pasajero "Por Asignar":
```python
# Automático en obtener_o_crear_pasajero_pendiente()
pasajero = Pasajero.objects.create(
    reserva=reserva,
    persona=persona_pendiente,
    por_asignar=True  # ← Se marca automáticamente
)
```

### Al actualizar con persona real:
```python
# Automático en perform_update() del PasajeroViewSet
PATCH /api/reservas/pasajeros/451/
{
  "persona_id": 15  # Persona real
}

# Resultado:
# - por_asignar cambia de True → False automáticamente
# - Se recalcula estado de la reserva
# - Se actualiza datos_completos
```

---

## 📊 Comparación: Antes vs Después

### Antes (sin campo `por_asignar`):

```javascript
// Forma antigua: verificar el documento
function esPasajeroPendiente(pasajero) {
  return pasajero.persona.documento.includes('_PEND');
}

// Problemas:
// ❌ Búsqueda de cadenas (menos eficiente)
// ❌ Depende de convención de nomenclatura
// ❌ Difícil de entender en código
```

### Después (con campo `por_asignar`):

```javascript
// Forma nueva: usar el campo booleano
function esPasajeroPendiente(pasajero) {
  return pasajero.por_asignar;
}

// Ventajas:
// ✅ Más eficiente
// ✅ Más claro y explícito
// ✅ No depende de convenciones
// ✅ Fácil de filtrar en queries
```

---

## 🎨 Ejemplos de UI

### Card de Pasajero con Estado Visual

```html
<div class="pasajero-card">
  <div class="pasajero-header">
    <h3>María González</h3>
    <span class="badge badge-success">Datos completos</span>
  </div>
  <div class="pasajero-body">
    <p><strong>Documento:</strong> 87654321</p>
    <p><strong>Monto pagado:</strong> Gs. 220.000</p>
    <p><strong>Saldo:</strong> Gs. 3.316.000</p>
  </div>
</div>

<!-- VS -->

<div class="pasajero-card pasajero-pendiente">
  <div class="pasajero-header">
    <h3>Por Asignar 2</h3>
    <span class="badge badge-warning">⚠️ Pendiente</span>
  </div>
  <div class="pasajero-body">
    <p><strong>Estado:</strong> Sin asignar</p>
    <p><strong>Monto pagado:</strong> Gs. 220.000</p>
    <button class="btn btn-primary">
      Asignar Persona
    </button>
  </div>
</div>
```

---

## 🔍 Queries Útiles

### Django ORM

```python
from apps.reserva.models import Reserva, Pasajero

# Obtener todas las reservas con pasajeros pendientes
reservas_con_pendientes = Reserva.objects.filter(
    pasajeros__por_asignar=True
).distinct()

# Contar pasajeros pendientes en una reserva
reserva = Reserva.objects.get(id=180)
pendientes_count = reserva.pasajeros.filter(por_asignar=True).count()

# Obtener reservas completamente asignadas
reservas_completas = Reserva.objects.exclude(
    pasajeros__por_asignar=True
)

# Estadísticas generales
from django.db.models import Count, Q

stats = Pasajero.objects.aggregate(
    total=Count('id'),
    asignados=Count('id', filter=Q(por_asignar=False)),
    pendientes=Count('id', filter=Q(por_asignar=True))
)
```

---

## 📝 Notas Importantes

1. **Actualización Automática**: El campo `por_asignar` se actualiza automáticamente a `False` cuando se asigna una persona real mediante PATCH/PUT.

2. **Retrocompatibilidad**: El campo también funciona con la identificación por documento (`_PEND`), pero ahora es más eficiente usar `por_asignar`.

3. **Validación de Estado**: Cuando se actualiza `por_asignar` a `False`, automáticamente se recalcula el estado de la reserva (`datos_completos`, `estado`).

4. **Queries Optimizadas**: Usar `por_asignar` en filtros es más eficiente que buscar por patrones en el documento.

---

## 🚀 Migración de Código Existente

Si tienes código que verifica el documento con `_PEND`, puedes migrarlo fácilmente:

### Antes:
```javascript
// Frontend
const pendientes = pasajeros.filter(p =>
  p.persona.documento.includes('_PEND')
);
```

### Después:
```javascript
// Frontend (más eficiente y claro)
const pendientes = pasajeros.filter(p => p.por_asignar);
```

### Antes:
```python
# Backend
pasajeros_pendientes = reserva.pasajeros.filter(
    persona__documento__contains='_PEND'
)
```

### Después:
```python
# Backend (más eficiente)
pasajeros_pendientes = reserva.pasajeros.filter(por_asignar=True)
```

---

## 📅 Fecha de Creación

**Fecha:** 30 de Octubre de 2025
**Versión:** 1.0
**Autor:** Sistema GroupTours
