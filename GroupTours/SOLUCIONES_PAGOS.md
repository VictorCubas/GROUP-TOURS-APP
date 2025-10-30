# Soluciones a Problemas de Pagos

## Problema 1: Identificar detalles del pago en la respuesta

### ✅ SOLUCIONADO

**Cambios realizados:**
Se agregó un nuevo campo `distribuciones_detalle` en la respuesta de los endpoints:
- `POST /api/reservas/{id}/registrar-pago/`
- `POST /api/reservas/{id}/registrar-senia/`

**Respuesta mejorada:**

Ahora cuando registras un pago, la respuesta incluye:

```json
{
  "message": "Pago registrado exitosamente",
  "comprobante": {
    "id": 15,
    "numero_comprobante": "CPG-2025-0015",
    "tipo": "pago_parcial",
    "monto": 100.00,
    "distribuciones": [
      {
        "id": 45,
        "pasajero": 293,
        "pasajero_nombre": "Juan",
        "pasajero_apellido": "Pérez",
        "monto": 100.00
      }
    ]
  },
  "distribuciones_detalle": [  // ⭐ NUEVO CAMPO PARA LA VISTA
    {
      "id": 45,
      "pasajero_id": 293,
      "pasajero_nombre": "Juan Pérez",
      "pasajero_documento": "12345678",
      "es_titular": false,
      "monto": 100.0,
      "observaciones": null
    }
  ],
  "reserva": {
    "id": 178,
    "codigo": "RSV-2025-0178",
    "estado": "confirmado",
    "monto_pagado": 100.0,
    "saldo_pendiente": 4900.0
  },
  "titular": {
    "id": 50,
    "nombre": "María",
    "apellido": "González",
    "documento": "87654321"
  }
}
```

**Cómo usar esta información en tu vista:**

```javascript
// Ejemplo en JavaScript/React
fetch('http://127.0.0.1:8000/api/reservas/178/registrar-pago/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    metodo_pago: "efectivo",
    distribuciones: [
      { pasajero: 293, monto: 100 }
    ],
    tipo: "pago_parcial"
  })
})
.then(response => response.json())
.then(data => {
  // Mostrar detalles del pago
  console.log('Pago registrado:', data.comprobante.numero_comprobante);

  // Mostrar distribuciones de manera clara
  data.distribuciones_detalle.forEach(dist => {
    console.log(`Pasajero: ${dist.pasajero_nombre} (${dist.pasajero_documento})`);
    console.log(`Monto: ${dist.monto}`);
    console.log(`Es titular: ${dist.es_titular ? 'Sí' : 'No'}`);
  });

  // Mostrar estado de la reserva
  console.log(`Estado: ${data.reserva.estado_display}`);
  console.log(`Saldo pendiente: ${data.reserva.saldo_pendiente}`);
});
```

---

## Problema 2: Error 404 en endpoint de estado de cuenta

### ✅ IDENTIFICADO Y CORREGIDO

**Problema:**
Intentaste usar: `http://127.0.0.1:8000/api/pasajeros/293/estado-cuenta/` ❌

**Solución:**
La URL correcta es: `http://127.0.0.1:8000/api/reservas/pasajeros/293/estado-cuenta/` ✅

**Explicación:**
El endpoint de pasajeros está anidado dentro de la ruta `/api/reservas/`, no directamente en `/api/`.

**Rutas correctas para pasajeros:**

```
GET    /api/reservas/pasajeros/                    - Listar todos los pasajeros
GET    /api/reservas/pasajeros/{id}/               - Detalle de un pasajero
GET    /api/reservas/pasajeros/{id}/estado-cuenta/ - Estado de cuenta del pasajero
POST   /api/reservas/pasajeros/                    - Crear pasajero
PUT    /api/reservas/pasajeros/{id}/               - Actualizar pasajero
DELETE /api/reservas/pasajeros/{id}/               - Eliminar pasajero
```

**Ejemplo de uso:**

```bash
# Ver estado de cuenta del pasajero 293
curl http://127.0.0.1:8000/api/reservas/pasajeros/293/estado-cuenta/

# Respuesta:
{
  "id": 293,
  "reserva_codigo": "RSV-2025-0178",
  "paquete_nombre": "Tour a Encarnación",
  "persona": {
    "id": 150,
    "nombre": "Juan",
    "apellido": "Pérez",
    "documento": "12345678"
  },
  "es_titular": false,
  "precio_asignado": 5000.0,
  "monto_pagado": 100.0,
  "saldo_pendiente": 4900.0,
  "porcentaje_pagado": 2.0,
  "tiene_sena_pagada": false,
  "esta_totalmente_pagado": false,
  "historial_pagos": [
    {
      "fecha_pago": "2025-10-30T12:30:00Z",
      "numero_comprobante": "CPG-2025-0015",
      "tipo": "pago_parcial",
      "tipo_display": "Pago Parcial",
      "metodo_pago": "efectivo",
      "metodo_pago_display": "Efectivo",
      "monto_distribuido": 100.0,
      "comprobante_activo": true
    }
  ]
}
```

---

## Endpoints relacionados con pagos

### Registrar pagos

```bash
# Registrar seña
POST /api/reservas/{id}/registrar-senia/
Body: {
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": 293, "monto": 210},
    {"pasajero": 294, "monto": 210}
  ]
}

# Registrar pago parcial
POST /api/reservas/{id}/registrar-pago/
Body: {
  "tipo": "pago_parcial",
  "metodo_pago": "efectivo",
  "distribuciones": [
    {"pasajero": 293, "monto": 100}
  ]
}

# Registrar pago total
POST /api/reservas/{id}/registrar-pago/
Body: {
  "tipo": "pago_total",
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": 293, "monto": 4900}
  ]
}
```

### Consultar información de pagos

```bash
# Ver detalles completos de la reserva con todos los pagos
GET /api/reservas/{id}/

# Ver solo los comprobantes de una reserva
GET /api/reservas/{id}/detalle-comprobantes/

# Ver solo los pasajeros y sus pagos
GET /api/reservas/{id}/detalle-pasajeros/

# Ver estado de cuenta de un pasajero específico
GET /api/reservas/pasajeros/{id}/estado-cuenta/

# Listar todos los comprobantes del sistema
GET /api/comprobantes/

# Ver un comprobante específico
GET /api/comprobantes/{id}/

# Ver distribuciones de un comprobante
GET /api/distribuciones/?comprobante={id}
```

---

## Cómo identificar pagos por pasajero

### Opción 1: Usar el campo `distribuciones_detalle` en la respuesta del pago

Cuando registras un pago, la respuesta ahora incluye `distribuciones_detalle` con toda la información necesaria.

### Opción 2: Consultar el estado de cuenta del pasajero

```bash
GET /api/reservas/pasajeros/293/estado-cuenta/
```

Esto te da el historial completo de pagos de ese pasajero específico.

### Opción 3: Consultar los comprobantes de la reserva

```bash
GET /api/reservas/178/detalle-comprobantes/
```

Esto te da todos los comprobantes con sus distribuciones.

### Opción 4: Filtrar distribuciones por pasajero

```bash
GET /api/distribuciones/?pasajero=293
```

Esto te da todas las distribuciones asociadas a ese pasajero.

---

## Modelo de datos

```
ComprobantePago (un pago registrado)
├── id: 15
├── numero_comprobante: "CPG-2025-0015"
├── monto: 100.00
├── tipo: "pago_parcial"
└── distribuciones: [
    ComprobantePagoDistribucion
    ├── id: 45
    ├── pasajero_id: 293
    ├── monto: 100.00
    └── pasajero:
        ├── id: 293
        ├── persona:
        │   ├── nombre: "Juan"
        │   ├── apellido: "Pérez"
        │   └── documento: "12345678"
        └── reserva_id: 178
]
```

La relación entre tablas es:
- 1 ComprobantePago → N ComprobantePagoDistribucion
- 1 ComprobantePagoDistribucion → 1 Pasajero
- 1 Pasajero → 1 Reserva

---

## Resumen

✅ **Problema 1 resuelto:** Ahora la respuesta de `registrar-pago` incluye el campo `distribuciones_detalle` con información clara y lista para mostrar en la vista.

✅ **Problema 2 resuelto:** La URL correcta para el estado de cuenta es `/api/reservas/pasajeros/{id}/estado-cuenta/`

**Archivos modificados:**
- `apps/reserva/views.py` (líneas 712-738 y 978-1004)
- `apps/comprobante/serializers.py` (líneas 8-74)
- `apps/comprobante/models.py` (líneas 278-343)

---

## ACTUALIZACIÓN: Mejora en la información financiera de distribuciones

### ✅ Cambios implementados

Se agregó información financiera completa en ambas respuestas:
1. **`comprobante.distribuciones`** - Mejorado el serializer
2. **`distribuciones_detalle`** - Mejorado en los endpoints

**Nuevos campos agregados:**
- `precio_asignado`: Precio total que debe pagar el pasajero
- `monto_pagado_total`: Total pagado por el pasajero hasta el momento (sumando todos sus pagos)
- `saldo_pendiente`: Cuánto le falta pagar al pasajero
- `porcentaje_pagado`: Porcentaje del precio asignado que ya pagó

### Respuesta mejorada del endpoint registrar-pago:

```json
{
  "message": "Pago registrado exitosamente",
  "comprobante": {
    "id": 15,
    "numero_comprobante": "CPG-2025-0015",
    "tipo": "pago_parcial",
    "monto": 100.00,
    "distribuciones": [
      {
        "id": 45,
        "pasajero": 293,
        "pasajero_nombre": "Juan",
        "pasajero_apellido": "Pérez",
        "pasajero_documento": "12345678",
        "es_titular": false,
        "monto": 100.0,
        "precio_asignado": "5000.00",         // ⭐ NUEVO
        "monto_pagado_total": 100.0,          // ⭐ NUEVO (incluye este pago)
        "saldo_pendiente": 4900.0,            // ⭐ NUEVO
        "porcentaje_pagado": 2.0              // ⭐ NUEVO
      }
    ]
  },
  "distribuciones_detalle": [
    {
      "id": 45,
      "pasajero_id": 293,
      "pasajero_nombre": "Juan Pérez",
      "pasajero_documento": "12345678",
      "es_titular": false,
      "monto": 100.0,
      "observaciones": null,
      "precio_asignado": 5000.0,              // ⭐ NUEVO
      "monto_pagado_total": 100.0,            // ⭐ NUEVO
      "saldo_pendiente": 4900.0,              // ⭐ NUEVO
      "porcentaje_pagado": 2.0                // ⭐ NUEVO
    }
  ],
  "reserva": {
    "id": 178,
    "codigo": "RSV-2025-0178",
    "estado": "confirmado",
    "monto_pagado": 100.0,
    "saldo_pendiente": 4900.0
  }
}
```

### Ejemplo de uso en tu vista de resumen:

```javascript
// Después de registrar el pago
fetch('http://127.0.0.1:8000/api/reservas/178/registrar-pago/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    metodo_pago: "efectivo",
    distribuciones: [{ pasajero: 293, monto: 100 }],
    tipo: "pago_parcial"
  })
})
.then(response => response.json())
.then(data => {
  // Mostrar resumen de pagos
  console.log('Comprobante:', data.comprobante.numero_comprobante);

  // Opción 1: Usar comprobante.distribuciones
  data.comprobante.distribuciones.forEach(dist => {
    console.log(`
      Pasajero: ${dist.pasajero_nombre} ${dist.pasajero_apellido}
      Documento: ${dist.pasajero_documento}

      Monto de este pago: $${dist.monto}
      Total pagado: $${dist.monto_pagado_total}
      Precio asignado: $${dist.precio_asignado}
      Saldo pendiente: $${dist.saldo_pendiente}
      Progreso: ${dist.porcentaje_pagado}%
    `);
  });

  // Opción 2: Usar distribuciones_detalle (más directo)
  data.distribuciones_detalle.forEach(dist => {
    console.log(`
      ${dist.pasajero_nombre} - ${dist.pasajero_documento}
      Pagó: $${dist.monto} | Total pagado: $${dist.monto_pagado_total}
      Deuda: $${dist.precio_asignado} | Saldo: $${dist.saldo_pendiente}
      ${dist.porcentaje_pagado}% completado
    `);
  });
});
```

---

## ACTUALIZACIÓN: Mejora en el PDF del comprobante

### ✅ Cambios en el PDF

El PDF descargable ahora incluye 5 columnas en la sección "DISTRIBUCIÓN DEL PAGO":

| Pasajero | Documento | Monto Pago | Total Pagado | Saldo Pdte. |
|----------|-----------|------------|--------------|-------------|
| Juan Pérez | 12345678 | $100.00 | $100.00 | $4,900.00 |
| María López | 87654321 | $200.00 | $500.00 | $4,500.00 |

**Columnas:**
1. **Pasajero**: Nombre completo del pasajero
2. **Documento**: Número de documento
3. **Monto Pago**: Monto de este pago específico (del comprobante actual)
4. **Total Pagado**: Total acumulado pagado por el pasajero hasta el momento
5. **Saldo Pdte.**: Saldo pendiente que le falta pagar al pasajero

### Endpoint para descargar el PDF:

```bash
# Descargar PDF del comprobante
GET http://127.0.0.1:8000/api/comprobantes/{id}/descargar-pdf/

# Forzar regeneración del PDF
GET http://127.0.0.1:8000/api/comprobantes/{id}/descargar-pdf/?regenerar=true
```

El PDF se genera automáticamente con toda la información financiera actualizada de cada pasajero.
