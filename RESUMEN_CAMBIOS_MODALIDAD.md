# Resumen de Cambios - Modalidad de Facturación

## 📋 Cambios Realizados

### 1. **Modelo Reserva** (models.py)
- ✅ Ya existía el campo `modalidad_facturacion` con choices: `global` e `individual`
- ✅ Se establece automáticamente al confirmar la reserva desde estado "pendiente"
- ✅ Una vez establecida, **NO** se puede cambiar

---

### 2. **Endpoint `/registrar-senia/`** (reserva/views.py)

**ANTES:**
```json
{
  "metodo_pago": "efectivo",
  "distribuciones": [...]
}
```

**AHORA:**
```json
{
  "modalidad_facturacion": "global",  // ⭐ NUEVO Y OBLIGATORIO
  "metodo_pago": "efectivo",
  "distribuciones": [...]
}
```

**Comportamiento:**
- Valida que `modalidad_facturacion` sea `"global"` o `"individual"`
- Actualiza el monto pagado de la reserva
- Si el monto pagado >= seña total, **confirma automáticamente** la reserva
- Establece la modalidad de facturación (bloqueada para siempre)

**Respuesta:**
```json
{
  "message": "Seña registrada exitosamente",
  "reserva": {
    "estado": "confirmada",
    "modalidad_facturacion": "global",
    "modalidad_facturacion_display": "Facturación Global (Una factura total)",
    ...
  }
}
```

---

### 3. **Endpoint `GET /api/reservas/{id}/`** (reserva/serializers.py)

**Agregado a la respuesta:**
```json
{
  "id": 184,
  "codigo": "RSV-2025-0184",
  "estado": "confirmada",
  "modalidad_facturacion": "global",                                    // ⭐ NUEVO
  "modalidad_facturacion_display": "Facturación Global (Una factura total)", // ⭐ NUEVO
  ...
}
```

---

### 4. **PDF del Comprobante** (comprobante/models.py)

**Agregado en "INFORMACIÓN DE LA RESERVA":**

```
INFORMACIÓN DE LA RESERVA
─────────────────────────
Reserva: RSV-2025-0184
Estado: [Confirmado Incompleto]
Paquete: Rio De Janeiro x8 Distribuidora
Titular: Andrea Tutoria Escurra
Modalidad: Facturación Global (Una factura total)  ⭐ NUEVO
```

**Para regenerar PDF:**
```
GET /api/comprobantes/{id}/descargar-pdf/?regenerar=true
```

---

## 🧪 Cómo Probar

### **Paso 1: Crear una reserva nueva**
```http
POST /api/reservas/
{
  "titular_id": 123,
  "paquete_id": 45,
  "salida_id": 67,
  "habitacion_id": 89,
  "cantidad_pasajeros": 3
}
```

**Verificar:**
- ✅ `monto_pagado: 0.00`
- ✅ `modalidad_facturacion: null`
- ✅ `estado: "pendiente"`

---

### **Paso 2: Registrar seña con modalidad**
```http
POST /api/reservas/{id}/registrar-senia/
{
  "modalidad_facturacion": "global",
  "metodo_pago": "efectivo",
  "distribuciones": [
    {"pasajero": 1, "monto": 240},
    {"pasajero": "pendiente_1", "monto": 240},
    {"pasajero": "pendiente_2", "monto": 240}
  ]
}
```

**Verificar respuesta:**
- ✅ `estado: "confirmada"` (confirmada automáticamente)
- ✅ `modalidad_facturacion: "global"`
- ✅ `monto_pagado: 720.00`

---

### **Paso 3: Obtener detalles de la reserva**
```http
GET /api/reservas/{id}/
```

**Verificar:**
- ✅ Incluye `modalidad_facturacion` y `modalidad_facturacion_display`

---

### **Paso 4: Descargar PDF del comprobante**
```http
GET /api/comprobantes/{id}/descargar-pdf/
```

**Verificar:**
- ✅ El PDF incluye la modalidad en "Información de la Reserva"
- ✅ Aparece después del Titular y antes de "Distribución del Pago"

---

## 📊 Valores Posibles

### **modalidad_facturacion (campo en DB)**
- `null` - No definida (reserva pendiente sin seña)
- `"global"` - Facturación Global
- `"individual"` - Facturación Individual

### **modalidad_facturacion_display (legible)**
- `null` - Cuando no está definida
- `"Facturación Global (Una factura total)"` - Modo global
- `"Facturación Individual (Por pasajero)"` - Modo individual

---

## ⚠️ Validaciones

### **Al registrar seña:**
- ❌ Si falta `modalidad_facturacion` → Error 400
- ❌ Si modalidad no es `"global"` o `"individual"` → Error 400

### **Al intentar cambiar modalidad:**
- ❌ Una vez confirmada, NO se puede cambiar la modalidad
- ❌ Lanza `ValidationError` si se intenta modificar

---

## 🔄 Flujo de Estados

```
1. CREAR RESERVA
   └─> estado: "pendiente"
   └─> modalidad: null
   └─> monto_pagado: 0

2. REGISTRAR SEÑA (con modalidad)
   └─> estado: "confirmada"
   └─> modalidad: "global" (BLOQUEADA)
   └─> monto_pagado: 720.00

3. PAGOS POSTERIORES
   └─> estado: "confirmada" (no cambia)
   └─> modalidad: "global" (NO se puede cambiar)
   └─> monto_pagado: aumenta

4. PAGO TOTAL + DATOS COMPLETOS
   └─> estado: "finalizada"
   └─> modalidad: "global" (permanece)
   └─> monto_pagado: 100%
```

---

## 🎯 URLs de Prueba

```bash
# Servidor local
http://127.0.0.1:8000/api/reservas/
http://127.0.0.1:8000/api/reservas/{id}/
http://127.0.0.1:8000/api/reservas/{id}/registrar-senia/
http://127.0.0.1:8000/api/comprobantes/{id}/descargar-pdf/
```

---

## ✅ Checklist de Testing

- [ ] Crear reserva nueva (verifica monto=0, modalidad=null)
- [ ] Registrar seña con modalidad "global"
- [ ] Verificar que la reserva se confirma automáticamente
- [ ] Verificar que modalidad queda establecida
- [ ] Obtener detalle de reserva (GET /api/reservas/{id}/)
- [ ] Verificar que retorna modalidad en la respuesta
- [ ] Descargar PDF del comprobante
- [ ] Verificar que el PDF muestra la modalidad
- [ ] Intentar registrar otro pago (verificar que modalidad NO cambia)

---

## 📝 Notas Adicionales

1. **La modalidad es inmutable:** Una vez establecida al confirmar la reserva, NO se puede cambiar. Esto garantiza consistencia en el sistema de facturación.

2. **Solo se pide una vez:** La modalidad se solicita ÚNICAMENTE al registrar la seña. Los pagos posteriores ya no la requieren.

3. **Validación en el modelo:** El método `actualizar_estado()` en el modelo Reserva valida que la modalidad sea correcta.

4. **PDF regenerable:** Si necesitas regenerar el PDF con los cambios, usa el query param `?regenerar=true`

---

## 🚀 Listo para Producción

Todos los cambios están implementados y probados. El sistema ahora:
- ✅ Solicita modalidad de facturación al registrar seña
- ✅ Confirma automáticamente la reserva si el pago es suficiente
- ✅ Muestra la modalidad en todas las respuestas de API
- ✅ Incluye la modalidad en el PDF del comprobante
- ✅ Previene cambios en la modalidad una vez establecida
