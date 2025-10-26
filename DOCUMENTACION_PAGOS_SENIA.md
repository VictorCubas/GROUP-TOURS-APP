# Documentación de Endpoints de Pagos y Seña

## 📋 Tabla de Contenidos
1. [Nuevo Endpoint: Registrar Seña](#registrar-seña)
2. [Nuevo Endpoint: Registrar Pago](#registrar-pago)
3. [Pasajeros Pendientes](#pasajeros-pendientes)
4. [Endpoint Existente: Comprobantes](#comprobantes)
5. [Comparación de Endpoints](#comparación)
6. [Ejemplos de Uso](#ejemplos)

---

## 🆕 Registrar Seña

### `POST /api/reservas/{id}/registrar-senia/`

Registra el pago de seña inicial para una reserva. Crea automáticamente un ComprobantePago de tipo 'sena'.

#### Request Body:
```json
{
  "metodo_pago": "transferencia",     // REQUERIDO: efectivo, transferencia, tarjeta_debito, tarjeta_credito, cheque, qr, otro
  "referencia": "TRF-20251026-001",   // OPCIONAL: Número de referencia del banco/comprobante
  "observaciones": "Seña inicial",    // OPCIONAL: Notas adicionales
  "empleado": 1,                      // OPCIONAL: ID del empleado que registra (usa el primero si no se especifica)
  "distribuciones": [
    {
      "pasajero": 1,                  // ID del pasajero ya cargado (número)
      "monto": 210.00
    },
    {
      "pasajero": "pendiente_1",      // ⭐ Especial: pasajero aún no cargado (string)
      "monto": 210.00
    },
    {
      "pasajero": "pendiente_2",      // ⭐ Otro pasajero pendiente
      "monto": 210.00
    }
  ]
}
```

#### Respuesta Exitosa (201 Created):
```json
{
  "message": "Seña registrada exitosamente",
  "comprobante": {
    "id": 15,
    "numero_comprobante": "CPG-2025-0015",
    "reserva": 1,
    "reserva_codigo": "RSV-2025-0001",
    "fecha_pago": "2025-10-26T10:30:00Z",
    "tipo": "sena",
    "tipo_display": "Seña",
    "monto": "420.00",
    "metodo_pago": "transferencia",
    "metodo_pago_display": "Transferencia Bancaria",
    "referencia": "TRF-20251026-001",
    "observaciones": "Seña inicial",
    "empleado": 1,
    "empleado_nombre": "Juan",
    "empleado_apellido": "Pérez",
    "pdf_generado": null,
    "activo": true,
    "distribuciones": [
      {
        "id": 25,
        "pasajero": 1,
        "pasajero_nombre": "María",
        "pasajero_apellido": "González",
        "pasajero_documento": "12345678",
        "monto": "210.00",
        "observaciones": null,
        "fecha_creacion": "2025-10-26T10:30:00Z"
      },
      {
        "id": 26,
        "pasajero": 2,
        "pasajero_nombre": "Carlos",
        "pasajero_apellido": "López",
        "pasajero_documento": "87654321",
        "monto": "210.00",
        "observaciones": null,
        "fecha_creacion": "2025-10-26T10:30:00Z"
      }
    ],
    "fecha_creacion": "2025-10-26T10:30:00Z",
    "fecha_modificacion": "2025-10-26T10:30:00Z"
  },
  "reserva": {
    "id": 1,
    "codigo": "RSV-2025-0001",
    "estado": "confirmada",              // ✅ Estado actualizado automáticamente
    "monto_pagado": 420.00,
    "saldo_pendiente": 6652.00,
    "puede_confirmarse": true
  }
}
```

#### Errores Posibles:
```json
// 400 Bad Request - Falta metodo_pago
{
  "error": "El campo metodo_pago es requerido"
}

// 400 Bad Request - Faltan distribuciones
{
  "error": "Debe especificar las distribuciones de pago para cada pasajero"
}

// 400 Bad Request - Pasajero no pertenece a la reserva
{
  "error": "El pasajero con ID 5 no pertenece a esta reserva"
}

// 400 Bad Request - Monto inválido
{
  "error": "Monto inválido: abc"
}

// 400 Bad Request - Reserva sin pasajeros
{
  "error": "La reserva no tiene pasajeros registrados"
}
```

#### Notas Importantes:
- ⚠️ **La distribución NO es validada contra la seña mínima**. Un pasajero puede recibir menos de su seña requerida.
- ✅ Si algún pasajero no tiene su seña completa, la reserva **NO pasará a estado "confirmada"**.
- ✅ El estado se actualiza automáticamente según la lógica de `Reserva.puede_confirmarse()`.
- 💡 El monto total se calcula automáticamente sumando las distribuciones.

---

## 🆕 Registrar Pago

### `POST /api/reservas/{id}/registrar-pago/`

Registra un pago parcial o completo posterior a la seña. Crea un ComprobantePago con el tipo especificado.

#### Request Body:
```json
{
  "tipo": "pago_parcial",              // REQUERIDO: "pago_parcial" o "pago_total"
  "metodo_pago": "efectivo",           // REQUERIDO
  "referencia": "REC-001",             // OPCIONAL
  "observaciones": "Segundo pago",     // OPCIONAL
  "empleado": 1,                       // OPCIONAL
  "distribuciones": [                  // REQUERIDO
    {
      "pasajero": 1,
      "monto": 1000.00
    },
    {
      "pasajero": 2,
      "monto": 1500.00
    }
  ]
}
```

#### Respuesta Exitosa (201 Created):
```json
{
  "message": "Pago registrado exitosamente",
  "comprobante": {
    "id": 16,
    "numero_comprobante": "CPG-2025-0016",
    "tipo": "pago_parcial",
    "monto": "2500.00",
    // ... similar a registrar-senia
  },
  "reserva": {
    "id": 1,
    "codigo": "RSV-2025-0001",
    "estado": "finalizada",              // ✅ Puede cambiar a "finalizada" si pago completo
    "monto_pagado": 2920.00,
    "saldo_pendiente": 4152.00,
    "esta_totalmente_pagada": false
  }
}
```

#### Errores Posibles:
```json
// 400 Bad Request - Tipo inválido
{
  "error": "El tipo debe ser \"pago_parcial\" o \"pago_total\""
}

// 400 Bad Request - Falta campo tipo
{
  "error": "El campo tipo es requerido (pago_parcial o pago_total)"
}

// ... Resto de errores similares a registrar-senia
```

---

## 👤 Pasajeros Pendientes

### ¿Qué es un pasajero "pendiente"?

Cuando creas una reserva, no siempre tienes todos los datos de los pasajeros inmediatamente. El sistema permite usar `{"pasajero": "pendiente", "monto": 210.00}` para asignar pagos a pasajeros que aún no han sido cargados.

### Cómo funciona:

1. **Se crean automáticamente** pasajeros especiales con documento `'PENDIENTE'`, `'PENDIENTE_1'`, `'PENDIENTE_2'`, etc.
2. **Son únicos por reserva** - si ya existe, se reutiliza
3. **Los pagos se asignan** a estos pasajeros temporales
4. **Más adelante** se puede reasignar el pago cuando se carguen los pasajeros reales

### Formatos soportados:

**IMPORTANTE**: Los pasajeros pendientes usan los datos de contacto del **TITULAR** (email, teléfono) para que las comunicaciones lleguen correctamente.

| Valor en API | Documento | Nombre | Email | Teléfono |
|--------------|-----------|--------|-------|----------|
| `"pendiente"` | `{doc_titular}_PEND` | `Por Asignar` | Email del titular | Tel. del titular |
| `"pendiente_1"` | `{doc_titular}_PEND_1` | `Por Asignar 1` | Email del titular | Tel. del titular |
| `"pendiente_2"` | `{doc_titular}_PEND_2` | `Por Asignar 2` | Email del titular | Tel. del titular |
| `"pendiente_3"` | `{doc_titular}_PEND_3` | `Por Asignar 3` | Email del titular | Tel. del titular |

**Ejemplo**: Si titular tiene documento `"12345678"`:
- Pendiente 1 → Documento: `"12345678_PEND_1"`
- Pendiente 2 → Documento: `"12345678_PEND_2"`

### Información del pasajero pendiente (ejemplo):

**Titular de la reserva:**
```json
{
  "id": 5,
  "nombre": "Juan",
  "apellido": "Pérez",
  "documento": "12345678",
  "email": "juan@example.com",
  "telefono": "+595981123456"
}
```

**Pasajero pendiente creado:**
```json
{
  "id": 123,  // ID autogenerado
  "persona": {
    "id": 50,
    "nombre": "Por Asignar 1",                  // ✅ Genérico (claro que falta cargar)
    "apellido": "",
    "documento": "12345678_PEND_1",             // ✅ Basado en titular (único)
    "email": "juan@example.com",                // ✅ Del titular (comunicaciones)
    "telefono": "+595981123456"                 // ✅ Del titular (comunicaciones)
  },
  "es_titular": false,
  "precio_asignado": 5000.00,  // Toma precio_unitario de la reserva
  "monto_pagado": 210.00,      // Suma de pagos asignados a este pasajero
  "seña_requerida": 210.00,
  "tiene_sena_pagada": true
}
```

**Ventajas:**
- ✅ Nombre claro: "Por Asignar 1" indica que falta cargar datos
- ✅ Emails/SMS llegan al titular (email y teléfono reales)
- ✅ Documento único: No hay conflictos con múltiples pendientes
- ✅ Trazabilidad: Se puede identificar a qué reserva/titular pertenece

### Casos de uso:

#### **Caso 1: Titular NO viaja, 2 pasajeros sin cargar**
```json
// 1. Crear reserva
POST /api/reservas/
{
  "titular_id": 1,
  "cantidad_pasajeros": 2,
  "titular_como_pasajero": false,  // Titular NO viaja
  // ...
}

// 2. Pagar seña sin pasajeros cargados
POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": "pendiente_1", "monto": 210.00},  // ⭐ Pasajero pendiente 1
    {"pasajero": "pendiente_2", "monto": 210.00}   // ⭐ Pasajero pendiente 2
  ]
}
// ✅ RESULTADO: Se crean 2 pasajeros pendientes diferentes:
//    - Documento: "PENDIENTE_1", Nombre: "Por Asignar 1"
//    - Documento: "PENDIENTE_2", Nombre: "Por Asignar 2"
```

#### **Caso 2: Titular viaja + 1 acompañante sin cargar**
```json
// 1. Crear reserva (titular se agrega automáticamente como pasajero)
POST /api/reservas/
{
  "titular_id": 1,
  "cantidad_pasajeros": 2,
  "titular_como_pasajero": true,  // Titular SÍ viaja (default)
  // ...
}
// Se crea automáticamente: Pasajero 1 (titular)

// 2. Pagar seña
POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": 1, "monto": 210.00},             // Titular (ya existe)
    {"pasajero": "pendiente_1", "monto": 210.00}  // Acompañante por cargar
  ]
}
```

#### **Caso 3: Titular NO viaja, 3 pasajeros sin cargar**
```json
POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "efectivo",
  "distribuciones": [
    {"pasajero": "pendiente_1", "monto": 210.00},
    {"pasajero": "pendiente_2", "monto": 210.00},
    {"pasajero": "pendiente_3", "monto": 210.00}
  ]
}
// ✅ RESULTADO: Se crean 3 pasajeros pendientes diferentes
```

#### **Caso 4: Pago total sin distribuir (un solo pendiente)**
```json
POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": "pendiente", "monto": 420.00}  // Sin sufijo, usa "PENDIENTE"
  ]
}
// ⚠️ NOTA: Crea UN solo pasajero "PENDIENTE" que recibe $420
```

### ⚠️ Importante:

- **Pasajeros pendientes numerados**: Usa `"pendiente_1"`, `"pendiente_2"`, etc. para crear múltiples pasajeros distintos
- **Sin número = un solo pendiente**: `"pendiente"` sin sufijo crea/usa un único pasajero con documento `"PENDIENTE"`
- **Cada uno es independiente**: Cada `"pendiente_X"` tiene su propio `monto_pagado`, `seña_requerida`, etc.
- **No afecta la confirmación**: La reserva puede confirmarse si `monto_pagado >= seña_total` (validación a nivel reserva cuando `datos_completos = false`)
- **Reasignación futura**: Cuando cargues los pasajeros reales, puedes crear un endpoint para reasignar pagos

---

## 📦 Comprobantes (Endpoint Existente)

### `POST /api/comprobantes/`

Endpoint genérico para crear comprobantes. Más flexible pero requiere más campos.

#### Request Body:
```json
{
  "reserva": 1,                        // REQUERIDO
  "tipo": "sena",                      // REQUERIDO: sena, pago_parcial, pago_total, devolucion
  "monto": 420.00,                     // REQUERIDO
  "metodo_pago": "transferencia",      // REQUERIDO
  "referencia": "TRF-001",             // OPCIONAL
  "observaciones": "",                 // OPCIONAL
  "empleado": 1,                       // REQUERIDO
  "distribuciones": [                  // REQUERIDO
    {"pasajero": 1, "monto": 210.00},
    {"pasajero": 2, "monto": 210.00}
  ]
}
```

#### Respuesta Exitosa:
```json
{
  "id": 15,
  "numero_comprobante": "CPG-2025-0015",
  "tipo": "sena",
  "monto": "420.00",
  // ... resto de campos del comprobante
}
```

---

## 🔍 Comparación de Endpoints

| Característica | `/api/comprobantes/` | `/api/reservas/{id}/registrar-senia/` | `/api/reservas/{id}/registrar-pago/` |
|----------------|---------------------|---------------------------------------|--------------------------------------|
| **Uso principal** | Gestión administrativa | Registrar seña inicial | Pagos posteriores |
| **Campo `reserva`** | ✅ Requerido | ❌ En la URL | ❌ En la URL |
| **Campo `tipo`** | ✅ Requerido | ✅ Automático (`sena`) | ✅ Requerido |
| **Campo `monto`** | ✅ Requerido | ✅ Calculado automático | ✅ Calculado automático |
| **Campo `empleado`** | ✅ Requerido | ⚠️ Opcional (usa primero) | ⚠️ Opcional (usa primero) |
| **Validación seña mínima** | ❌ No | ❌ No | ❌ No |
| **Retorna estado reserva** | ❌ No | ✅ Sí | ✅ Sí |
| **Contexto específico** | ❌ Genérico | ✅ Específico para seña | ✅ Específico para pagos |

---

## 💡 Ejemplos de Uso

### Caso 1: Registrar Seña Completa (todos pagan lo mínimo)

```bash
POST /api/reservas/1/registrar-senia/
Content-Type: application/json

{
  "metodo_pago": "transferencia",
  "referencia": "TRF-001",
  "distribuciones": [
    {"pasajero": 1, "monto": 210.00},  // Seña mínima
    {"pasajero": 2, "monto": 210.00}   // Seña mínima
  ]
}
```
**Resultado**: Reserva pasa a estado `"confirmada"` ✅

---

### Caso 2: Registrar Seña Parcial (un pasajero paga menos)

```bash
POST /api/reservas/1/registrar-senia/
Content-Type: application/json

{
  "metodo_pago": "efectivo",
  "distribuciones": [
    {"pasajero": 1, "monto": 210.00},  // Seña completa
    {"pasajero": 2, "monto": 100.00}   // Menos que la seña ($210)
  ]
}
```
**Resultado**: Reserva se mantiene en `"pendiente"` ⚠️ (pasajero 2 no tiene seña completa)

---

### Caso 3: Titular paga toda la seña (sin distribuir)

```bash
POST /api/reservas/1/registrar-senia/
Content-Type: application/json

{
  "metodo_pago": "tarjeta_credito",
  "referencia": "AUTH-123456",
  "distribuciones": [
    {"pasajero": "pendiente", "monto": 420.00}  // Toda la seña sin asignar
  ]
}
```
**Resultado**: Reserva pasa a `"confirmada"` ✅ (monto_pagado >= seña_total)

---

### Caso 4: Pago Parcial Posterior

```bash
POST /api/reservas/1/registrar-pago/
Content-Type: application/json

{
  "tipo": "pago_parcial",
  "metodo_pago": "transferencia",
  "referencia": "TRF-002",
  "distribuciones": [
    {"pasajero": 1, "monto": 1500.00},
    {"pasajero": 2, "monto": 1500.00}
  ]
}
```
**Resultado**: Si alcanza el total, pasa a `"finalizada"` ✅

---

### Caso 5: Pago Total

```bash
POST /api/reservas/1/registrar-pago/
Content-Type: application/json

{
  "tipo": "pago_total",
  "metodo_pago": "efectivo",
  "observaciones": "Pago completo del saldo restante",
  "distribuciones": [
    {"pasajero": 1, "monto": 2790.00},  // Saldo completo
    {"pasajero": 2, "monto": 2790.00}   // Saldo completo
  ]
}
```
**Resultado**: Reserva pasa a `"finalizada"` ✅

---

## 🔄 Flujo Completo de Pagos

```
1. Crear Reserva
   POST /api/reservas/
   Estado inicial: "pendiente"

2. Registrar Seña
   POST /api/reservas/1/registrar-senia/
   {
     "metodo_pago": "transferencia",
     "distribuciones": [
       {"pasajero": 1, "monto": 210.00},
       {"pasajero": 2, "monto": 210.00}
     ]
   }
   ✅ Estado → "confirmada"

3. Primer Pago Parcial
   POST /api/reservas/1/registrar-pago/
   {
     "tipo": "pago_parcial",
     "metodo_pago": "efectivo",
     "distribuciones": [
       {"pasajero": 1, "monto": 1500.00},
       {"pasajero": 2, "monto": 1500.00}
     ]
   }
   Estado: "confirmada" (aún falta saldo)

4. Segundo Pago Parcial (saldo final)
   POST /api/reservas/1/registrar-pago/
   {
     "tipo": "pago_parcial",
     "metodo_pago": "transferencia",
     "distribuciones": [
       {"pasajero": 1, "monto": 1290.00},
       {"pasajero": 2, "monto": 1290.00}
     ]
   }
   ✅ Estado → "finalizada"
```

---

## 📊 Estados de Reserva

| Estado | Descripción | Condición |
|--------|-------------|-----------|
| `pendiente` | Sin pago suficiente | `monto_pagado < seña_total` |
| `confirmada` | Seña pagada | Todos los pasajeros tienen `seña_requerida` pagada |
| `finalizada` | Pago completo | `monto_pagado >= costo_total_estimado` |
| `cancelada` | Cancelada | Manual |

---

## 🎯 Recomendaciones

1. **Para frontend**: Usar `/api/reservas/{id}/registrar-senia/` y `/api/reservas/{id}/registrar-pago/`
   - Más simple
   - Retorna info completa de la reserva
   - Menos propenso a errores

2. **Para backoffice/admin**: Usar `/api/comprobantes/`
   - Más control
   - Permite casos especiales
   - Gestión administrativa

3. **Validar en frontend** antes de enviar:
   - Cada pasajero debe tener monto >= 0
   - La suma debe ser > 0
   - Verificar que todos los pasajeros estén incluidos

4. **Descargar PDF del comprobante**:
   ```bash
   GET /api/comprobantes/{comprobante_id}/descargar-pdf/
   ```

---

**Fecha**: 26 de Octubre, 2025
**Versión**: 1.0.0
**Autor**: Claude Code Assistant
