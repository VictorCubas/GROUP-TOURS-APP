# Documentación: Pasajeros Pendientes

## 📋 Índice
1. [Introducción](#introducción)
2. [¿Por qué existen?](#por-qué-existen)
3. [Cómo Funcionan](#cómo-funcionan)
4. [Estructura Técnica](#estructura-técnica)
5. [Casos de Uso](#casos-de-uso)
6. [Ejemplos de API](#ejemplos-de-api)
7. [Flujo Completo](#flujo-completo)
8. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## 🎯 Introducción

Los **Pasajeros Pendientes** son un mecanismo que permite registrar pagos de seña para una reserva **antes de tener todos los datos de los pasajeros reales**.

### Problema que resuelven:

En el flujo real de una agencia de turismo:
1. El **titular** hace la reserva para 3 personas
2. El titular **paga la seña** inmediatamente
3. Los **datos de los otros 2 pasajeros** se cargan después (pueden tardar días o semanas)

**Pregunta**: ¿Cómo registramos el pago de seña si no tenemos los pasajeros cargados?

**Respuesta**: Usando **pasajeros pendientes** (`"pendiente_1"`, `"pendiente_2"`, etc.)

---

## 💡 ¿Por qué existen?

### **Flujo Tradicional** (sin pasajeros pendientes):
```
❌ Problema:
1. Crear reserva (3 pasajeros)
2. ⚠️ No puedo pagar seña → No hay pasajeros cargados
3. Cargar datos de los 3 pasajeros
4. Pagar seña
```

### **Flujo con Pasajeros Pendientes**:
```
✅ Solución:
1. Crear reserva (3 pasajeros)
2. ✅ Pagar seña con "pendiente_1", "pendiente_2", "pendiente_3"
3. Reserva pasa a "confirmada"
4. Cargar datos reales más adelante
5. (Opcional) Reasignar pagos pendientes
```

---

## ⚙️ Cómo Funcionan

### **Concepto Clave**:

Un pasajero pendiente es una **PersonaFisica temporal** que:
- ✅ Tiene **nombre genérico**: `"Por Asignar 1"`, `"Por Asignar 2"`, etc.
- ✅ Usa **datos de contacto del titular**: Email y teléfono reales
- ✅ Tiene **documento único**: Basado en el titular + sufijo (`12345678_PEND_1`)
- ✅ Puede **recibir pagos** como cualquier otro pasajero
- ✅ Se **reutiliza** si ya existe para la reserva

---

## 🏗️ Estructura Técnica

### **Modelo de Datos**

#### **Titular de la Reserva:**
```json
{
  "id": 5,
  "nombre": "Juan",
  "apellido": "Pérez",
  "documento": "12345678",
  "email": "juan@example.com",
  "telefono": "+595981123456",
  "tipo_documento_id": 1,
  "nacionalidad_id": 1
}
```

#### **Pasajero Pendiente 1:**
```json
{
  "id": 50,
  "reserva_id": 1,
  "persona": {
    "id": 100,
    "nombre": "Por Asignar 1",           // ⭐ Genérico
    "apellido": "",
    "documento": "12345678_PEND_1",      // ⭐ Titular + sufijo
    "email": "juan@example.com",         // ⭐ Del titular
    "telefono": "+595981123456",         // ⭐ Del titular
    "tipo_documento_id": 1,              // ⭐ Del titular
    "nacionalidad_id": 1,                // ⭐ Del titular
    "fecha_nacimiento": "1990-01-15",    // ⭐ Del titular
    "sexo": "M"                          // ⭐ Del titular
  },
  "es_titular": false,
  "precio_asignado": 5000.00,
  "monto_pagado": 210.00,
  "seña_requerida": 210.00,
  "tiene_sena_pagada": true
}
```

---

## 📝 Casos de Uso

### **Caso 1: Titular NO viaja, 3 pasajeros sin datos**

**Escenario:**
- Una empresa reserva un viaje para 3 empleados
- El gerente (titular) paga la seña
- Los datos de los 3 empleados se cargan después

**Solución:**
```json
POST /api/reservas/
{
  "titular_id": 5,
  "cantidad_pasajeros": 3,
  "titular_como_pasajero": false,
  "paquete_id": 10,
  "salida_id": 15,
  "habitacion_id": 2
}

POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": "pendiente_1", "monto": 210.00},
    {"pasajero": "pendiente_2", "monto": 210.00},
    {"pasajero": "pendiente_3", "monto": 210.00}
  ]
}
```

**Resultado:**
- 3 pasajeros pendientes creados
- Reserva confirmada
- Emails de confirmación van a `juan@example.com`

---

### **Caso 2: Titular viaja + 2 acompañantes sin datos**

**Escenario:**
- Juan viaja con 2 amigos
- Juan paga la seña de todos
- Los datos de los amigos se cargan después

**Solución:**
```json
POST /api/reservas/
{
  "titular_id": 5,
  "cantidad_pasajeros": 3,
  "titular_como_pasajero": true,  // ✅ Juan SÍ viaja
  "paquete_id": 10,
  "salida_id": 15,
  "habitacion_id": 2
}
// Se crea automáticamente: Pasajero 1 (Juan, titular)

POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": 1, "monto": 210.00},             // Juan (ya existe)
    {"pasajero": "pendiente_1", "monto": 210.00}, // Amigo 1
    {"pasajero": "pendiente_2", "monto": 210.00}  // Amigo 2
  ]
}
```

**Resultado:**
- Pasajero 1: Juan (titular, datos completos)
- Pasajero 2: "Por Asignar 1" (pendiente)
- Pasajero 3: "Por Asignar 2" (pendiente)

---

### **Caso 3: Pago total sin distribuir**

**Escenario:**
- Pagan toda la seña sin especificar por pasajero
- Se distribuirá cuando se carguen los datos

**Solución:**
```json
POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "efectivo",
  "distribuciones": [
    {"pasajero": "pendiente", "monto": 630.00}  // Sin sufijo
  ]
}
```

**Resultado:**
- 1 pasajero pendiente con `monto_pagado = 630.00`
- ⚠️ **Nota**: Este pasajero tiene MÁS de su seña requerida

---

### **Caso 4: Distribución parcial**

**Escenario:**
- 3 pasajeros, solo pagan la seña de 2

**Solución:**
```json
POST /api/reservas/1/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": "pendiente_1", "monto": 210.00},
    {"pasajero": "pendiente_2", "monto": 210.00}
    // Pasajero 3 no paga nada aún
  ]
}
```

**Resultado:**
- 2 pasajeros pendientes creados
- `reserva.monto_pagado = 420.00`
- `reserva.estado = "pendiente"` (falta seña del 3er pasajero)

---

## 🔌 Ejemplos de API

### **Endpoint: Registrar Seña**

```http
POST /api/reservas/{id}/registrar-senia/
Content-Type: application/json

{
  "metodo_pago": "transferencia",
  "referencia": "TRF-20251026-001",
  "observaciones": "Seña inicial",
  "empleado": 1,
  "distribuciones": [
    {"pasajero": "pendiente_1", "monto": 210.00},
    {"pasajero": "pendiente_2", "monto": 210.00},
    {"pasajero": "pendiente_3", "monto": 210.00}
  ]
}
```

**Respuesta:**
```json
{
  "message": "Seña registrada exitosamente",
  "comprobante": {
    "id": 15,
    "numero_comprobante": "CPG-2025-0015",
    "tipo": "sena",
    "monto": "630.00",
    "distribuciones": [
      {
        "id": 25,
        "pasajero": 101,
        "pasajero_nombre": "Por Asignar 1",
        "pasajero_documento": "12345678_PEND_1",
        "monto": "210.00"
      },
      {
        "id": 26,
        "pasajero": 102,
        "pasajero_nombre": "Por Asignar 2",
        "pasajero_documento": "12345678_PEND_2",
        "monto": "210.00"
      },
      {
        "id": 27,
        "pasajero": 103,
        "pasajero_nombre": "Por Asignar 3",
        "pasajero_documento": "12345678_PEND_3",
        "monto": "210.00"
      }
    ]
  },
  "reserva": {
    "id": 1,
    "codigo": "RSV-2025-0001",
    "estado": "confirmada",
    "monto_pagado": 630.00,
    "saldo_pendiente": 14370.00,
    "puede_confirmarse": true
  }
}
```

---

### **Endpoint: Consultar Pasajeros de una Reserva**

```http
GET /api/reservas/pasajeros/?reserva_id=1
```

**Respuesta:**
```json
[
  {
    "id": 101,
    "persona": {
      "id": 100,
      "nombre": "Por Asignar 1",
      "apellido": "",
      "documento": "12345678_PEND_1",
      "email": "juan@example.com",
      "telefono": "+595981123456"
    },
    "es_titular": false,
    "precio_asignado": "5000.00",
    "monto_pagado": "210.00",
    "saldo_pendiente": "4790.00",
    "seña_requerida": "210.00",
    "tiene_sena_pagada": true,
    "esta_totalmente_pagado": false
  },
  {
    "id": 102,
    "persona": {
      "nombre": "Por Asignar 2",
      "documento": "12345678_PEND_2",
      "email": "juan@example.com",
      "telefono": "+595981123456"
    },
    "monto_pagado": "210.00",
    "tiene_sena_pagada": true
  },
  {
    "id": 103,
    "persona": {
      "nombre": "Por Asignar 3",
      "documento": "12345678_PEND_3",
      "email": "juan@example.com"
    },
    "monto_pagado": "210.00",
    "tiene_sena_pagada": true
  }
]
```

---

## 🔄 Flujo Completo

### **1. Creación de Reserva**
```javascript
const reserva = await api.post('/api/reservas/', {
  titular_id: 5,
  cantidad_pasajeros: 3,
  titular_como_pasajero: false,
  paquete_id: 10,
  salida_id: 15,
  habitacion_id: 2,
  precio_unitario: 5000.00
});

console.log(reserva.estado);  // "pendiente"
console.log(reserva.seña_total);  // 630.00 (210 × 3)
```

---

### **2. Pago de Seña con Pendientes**
```javascript
const pago = await api.post(`/api/reservas/${reserva.id}/registrar-senia/`, {
  metodo_pago: 'transferencia',
  referencia: 'TRF-001',
  distribuciones: [
    { pasajero: 'pendiente_1', monto: 210.00 },
    { pasajero: 'pendiente_2', monto: 210.00 },
    { pasajero: 'pendiente_3', monto: 210.00 }
  ]
});

console.log(pago.reserva.estado);  // "confirmada" ✅
```

---

### **3. Consultar Pasajeros Pendientes**
```javascript
const pasajeros = await api.get(`/api/reservas/pasajeros/?reserva_id=${reserva.id}`);

pasajeros.forEach(p => {
  console.log(`${p.persona.nombre} - ${p.persona.documento}`);
});

// Output:
// Por Asignar 1 - 12345678_PEND_1
// Por Asignar 2 - 12345678_PEND_2
// Por Asignar 3 - 12345678_PEND_3
```

---

### **4. (Futuro) Cargar Datos Reales y Reasignar**
```javascript
// Cargar pasajero real
const pasajeroReal = await api.post('/api/reservas/pasajeros/', {
  reserva_id: reserva.id,
  persona_id: 20,  // María López
  precio_asignado: 5000.00
});

// TODO: Endpoint futuro para reasignar pagos
// POST /api/reservas/pasajeros/{id}/reasignar-pagos/
// Body: { pasajero_origen: 101, pasajero_destino: pasajeroReal.id }
```

---

## ❓ Preguntas Frecuentes

### **1. ¿Cuántos pasajeros pendientes puedo crear?**
No hay límite técnico. Puedes usar `pendiente_1`, `pendiente_2`, ..., `pendiente_N`.

---

### **2. ¿Qué pasa si uso "pendiente" múltiples veces?**
```json
{
  "distribuciones": [
    {"pasajero": "pendiente", "monto": 210.00},
    {"pasajero": "pendiente", "monto": 210.00}
  ]
}
```
**Resultado**: Se crea/reutiliza **UN SOLO** pasajero pendiente que recibe **$420** en total.

**Recomendación**: Usa siempre sufijos (`pendiente_1`, `pendiente_2`) para múltiples pasajeros.

---

### **3. ¿Puedo mezclar pasajeros reales y pendientes?**
**Sí, completamente.**

```json
{
  "distribuciones": [
    {"pasajero": 1, "monto": 210.00},             // Pasajero real
    {"pasajero": "pendiente_1", "monto": 210.00}, // Pendiente
    {"pasajero": "pendiente_2", "monto": 210.00}  // Pendiente
  ]
}
```

---

### **4. ¿Los pasajeros pendientes afectan la confirmación de la reserva?**

Depende del modo de validación:

**Sin datos completos** (`datos_completos = false`):
- Validación a **nivel reserva**: `monto_pagado >= seña_total`
- No importa la distribución individual

**Con datos completos** (`datos_completos = true`):
- Validación **individual**: Cada pasajero debe tener `tiene_sena_pagada = true`

---

### **5. ¿Por qué usan el email/teléfono del titular?**

Para que las **comunicaciones lleguen correctamente**:
- ✅ Email de confirmación de reserva
- ✅ SMS de recordatorio
- ✅ WhatsApp con estado del viaje
- ✅ Notificaciones de pagos

El titular es el responsable de la reserva, por eso recibe todas las notificaciones.

---

### **6. ¿Qué pasa cuando cargo los datos reales del pasajero?**

**Actualmente**: Los pasajeros pendientes y reales coexisten.

**Futuro**: Se puede implementar un endpoint para:
1. Reasignar los pagos del pendiente al real
2. Eliminar/desactivar el pasajero pendiente

---

### **7. ¿Puedo eliminar un pasajero pendiente?**

**Sí**, pero ten cuidado:
- Si tiene pagos asignados, perderás la trazabilidad
- Mejor: Crear el pasajero real y reasignar los pagos

---

### **8. ¿Cómo identifico visualmente un pasajero pendiente?**

**Por el nombre**:
- `"Por Asignar 1"` → Pendiente
- `"Juan Pérez"` → Real

**Por el documento**:
- `"12345678_PEND_1"` → Pendiente
- `"12345678"` → Real

---

### **9. ¿Puedo cambiar el email/teléfono de un pasajero pendiente?**

**No es recomendable** porque se crean a partir del titular.

Si necesitas cambiar los datos de contacto, mejor:
1. Actualiza los datos del titular
2. Los nuevos pasajeros pendientes usarán los datos actualizados

---

### **10. ¿Hay un límite en el sufijo?**

**No técnicamente**, pero por convención:
- Usa números: `pendiente_1`, `pendiente_2`, ..., `pendiente_N`
- Evita: `pendiente_abc`, `pendiente_especial` (pueden causar confusión)

---

## 🎯 Mejores Prácticas

### ✅ **Hacer:**
1. Usar sufijos numerados: `pendiente_1`, `pendiente_2`, etc.
2. Verificar `cantidad_pasajeros` antes de crear pendientes
3. Mostrar claramente en la UI que son "Por Asignar"
4. Pedir al titular que complete los datos pronto

### ❌ **Evitar:**
1. Usar `"pendiente"` sin sufijo para múltiples pasajeros
2. Crear más pendientes de los necesarios
3. Dejar pasajeros pendientes por mucho tiempo sin actualizar
4. Confundir al usuario mostrando el documento técnico (`12345678_PEND_1`)

---

## 📚 Referencias

- **Endpoint Registrar Seña**: `POST /api/reservas/{id}/registrar-senia/`
- **Endpoint Registrar Pago**: `POST /api/reservas/{id}/registrar-pago/`
- **Código Helper**: `GroupTours/apps/reserva/views.py:19-87`
- **Documentación Pagos**: `DOCUMENTACION_PAGOS_SENIA.md`

---

**Fecha**: 26 de Octubre, 2025
**Versión**: 1.0.0
**Autor**: Claude Code Assistant
