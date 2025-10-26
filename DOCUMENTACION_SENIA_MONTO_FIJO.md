# Corrección: Seña como Monto Fijo (No Porcentaje)

## ✅ CAMBIO REALIZADO

Se corrigió el cálculo de seña para que use el **monto fijo** definido en `SalidaPaquete.senia` en lugar de calcular un porcentaje del precio.

---

## 📋 ARCHIVO MODIFICADO

### `GroupTours/apps/reserva/models.py`

**Modelo:** `Pasajero` (línea 541-552)

**Antes:**
```python
@property
def seña_requerida(self):
    """
    Monto de seña requerido para este pasajero.
    Se calcula como porcentaje del precio_asignado.
    """
    from decimal import Decimal
    if not self.precio_asignado or not self.reserva or not self.reserva.salida:
        return Decimal("0")

    # Obtener porcentaje de seña de la salida (si no existe, usar 30%)
    porcentaje_sena = getattr(self.reserva.salida, 'porcentaje_sena', None) or Decimal("30")
    return (self.precio_asignado * porcentaje_sena) / Decimal("100")
```

**Después:**
```python
@property
def seña_requerida(self):
    """
    Monto de seña requerido para este pasajero.
    La seña es un MONTO FIJO por pasajero definido en SalidaPaquete.senia
    """
    from decimal import Decimal
    if not self.reserva or not self.reserva.salida:
        return Decimal("0")

    # Retornar el monto fijo de seña de la salida
    return self.reserva.salida.senia or Decimal("0")
```

---

## 🧪 VALIDACIÓN

Se ejecutó el script de prueba `test_senia_monto_fijo.py` con los siguientes resultados:

### Ejemplo de Reserva Probada:

```
Salida de Paquete: VICTOR HUGO - 2025-10-01
   - Paquete: VICTOR HUGO
   - Fecha salida: 2025-10-01
   - Seña (monto fijo por pasajero): $210.00

Reserva: RSV-2025-0004
   - Estado: confirmada
   - Cantidad de pasajeros: 2
   - Precio total: $7,072.00

CÁLCULO DE SEÑA TOTAL:
   - Seña por pasajero: $210.00
   - Cantidad pasajeros: 2
   - Seña total calculada: $420.00
   - Seña total (propiedad): $420.00
   [OK] CORRECTO: seña_total coincide

ESTADO DE PAGO:
   - Monto pagado: $1,500.00
   - Seña requerida: $420.00
   - Saldo pendiente: $5,572.00
   - Puede confirmarse: True

DESGLOSE POR PASAJERO:

   Pasajero 1: Victor Cubas
   - Seña requerida (FIJA): $210.00
   [OK] CORRECTO: seña_requerida = $210.00 (monto fijo)

   Pasajero 2: Andrea Tutoria Escurra
   - Precio asignado: $5,000.00
   - Seña requerida (FIJA): $210.00
   - Monto pagado: $1,500.00
   - Saldo pendiente: $3,500.00
   - Tiene seña pagada: SI
   - Porcentaje pagado: 30.00%
   [OK] CORRECTO: seña_requerida = $210.00 (monto fijo)
```

---

## 📊 CÓMO FUNCIONA AHORA

### 1. **Configuración de Seña en SalidaPaquete**

```python
# Ejemplo: Configurar seña de $1,500 por pasajero
salida = SalidaPaquete.objects.get(id=1)
salida.senia = Decimal("1500.00")
salida.save()
```

### 2. **Cálculo Automático en Reserva**

```python
# Al crear una reserva con 2 pasajeros
reserva = Reserva.objects.create(
    salida=salida,
    cantidad_pasajeros=2,
    precio_unitario=5000.00
)

# Cálculos automáticos:
reserva.seña_total  # 1500 × 2 = 3000.00
```

### 3. **Cálculo por Pasajero**

```python
# Cada pasajero tiene su seña individual
pasajero = Pasajero.objects.create(
    reserva=reserva,
    persona=persona,
    precio_asignado=5000.00
)

# Cálculos automáticos:
pasajero.seña_requerida  # 1500.00 (monto fijo de salida.senia)
pasajero.tiene_sena_pagada  # True si monto_pagado >= 1500.00
```

---

## 🎯 FLUJO RECOMENDADO PARA FRONTEND

### **Paso 1: Obtener datos de la salida**

```javascript
// GET /api/paquete/salidas/{id}/
const salida = {
  id: 1,
  paquete: "Rio de Janeiro",
  fecha_salida: "2025-10-25",
  senia: 1500.00,  // ⭐ MONTO FIJO por pasajero
  precio_venta_sugerido_min: 5000.00,
  precio_venta_sugerido_max: 6000.00
}
```

### **Paso 2: Calcular seña total en el frontend**

```javascript
// Usuario selecciona cantidad de pasajeros
const cantidadPasajeros = 2;
const precioUnitario = 5000.00;

// Cálculos para mostrar al usuario:
const seniaPorPasajero = salida.senia;  // 1500.00
const seniaTotal = seniaPorPasajero * cantidadPasajeros;  // 3000.00
const precioTotal = precioUnitario * cantidadPasajeros;  // 10000.00
const saldoDespuesSenia = precioTotal - seniaTotal;  // 7000.00

// Mostrar en UI:
{
  "precio_por_persona": 5000.00,
  "seña_por_persona": 1500.00,  // ⭐ Monto fijo
  "cantidad_pasajeros": 2,
  "seña_total_a_pagar": 3000.00,
  "precio_total": 10000.00,
  "saldo_pendiente_despues_seña": 7000.00
}
```

### **Paso 3: Vista de Resumen en el Frontend**

```
┌──────────────────────────────────┐
│  RESUMEN DE RESERVA              │
├──────────────────────────────────┤
│  Paquete: Rio de Janeiro         │
│  Salida: 25/10/2025              │
│  Habitación: Doble               │
│  Pasajeros: 2 personas           │
├──────────────────────────────────┤
│  DESGLOSE DE COSTOS:             │
│                                  │
│  Precio por persona: $5,000      │
│  Seña por persona: $1,500        │
│  ─────────────────────────       │
│  Subtotal pasajeros: $10,000     │
│                                  │
│  SEÑA A PAGAR HOY:               │
│  $1,500 × 2 = $3,000             │
│                                  │
│  Saldo a pagar antes del viaje:  │
│  $7,000                          │
└──────────────────────────────────┘
```

---

## 📡 ENDPOINTS RELEVANTES

### **1. Obtener datos de salida con seña**

```http
GET /api/paquete/salidas/{id}/
```

**Respuesta:**
```json
{
  "id": 1,
  "paquete": {
    "id": 1,
    "nombre": "Rio de Janeiro"
  },
  "fecha_salida": "2025-10-25",
  "fecha_regreso": "2025-11-08",
  "senia": 1500.00,
  "precio_venta_sugerido_min": 5000.00,
  "precio_venta_sugerido_max": 6000.00,
  "cupo": 20
}
```

### **2. Crear reserva**

```http
POST /api/reservas/
```

**Request:**
```json
{
  "paquete": 1,
  "salida": 1,
  "habitacion": 2,
  "cantidad_pasajeros": 2,
  "precio_unitario": 5000.00,
  "titular": {
    "nombre": "Juan",
    "apellido": "Pérez",
    "documento": "1234567",
    "email": "juan@example.com",
    "telefono": "+595981123456"
  }
}
```

**Respuesta:**
```json
{
  "id": 1,
  "codigo": "RSV-2025-0001",
  "estado": "pendiente",
  "cantidad_pasajeros": 2,
  "precio_unitario": 5000.00,
  "costo_total_estimado": 10000.00,
  "seña_total": 3000.00,  // ⭐ 1500 × 2
  "monto_pagado": 0.00,
  "puede_confirmarse": false
}
```

### **3. Registrar pago de seña**

```http
POST /api/comprobantes/
```

**Request:**
```json
{
  "reserva": 1,
  "tipo": "sena",
  "monto": 3000.00,
  "metodo_pago": "transferencia",
  "referencia": "TRF-20251025-001",
  "empleado": 1,
  "distribuciones": [
    {
      "pasajero": 1,
      "monto": 1500.00
    },
    {
      "pasajero": 2,
      "monto": 1500.00
    }
  ]
}
```

**Respuesta:**
```json
{
  "id": 1,
  "numero_comprobante": "CPG-2025-0001",
  "tipo": "sena",
  "monto": 3000.00,
  "metodo_pago": "transferencia",
  "pdf_url": "/api/comprobantes/1/pdf/"
}
```

### **4. Consultar estado de cuenta de un pasajero**

```http
GET /api/reservas/pasajeros/{id}/estado-cuenta/
```

**Respuesta:**
```json
{
  "id": 1,
  "reserva_codigo": "RSV-2025-0001",
  "persona": {
    "nombre": "Juan",
    "apellido": "Pérez",
    "documento": "1234567"
  },
  "es_titular": true,
  "precio_asignado": 5000.00,
  "seña_requerida": 1500.00,  // ⭐ Monto fijo
  "monto_pagado": 1500.00,
  "saldo_pendiente": 3500.00,
  "tiene_sena_pagada": true,
  "porcentaje_pagado": 30.00,
  "historial_pagos": [
    {
      "fecha_pago": "2025-10-25T10:30:00Z",
      "numero_comprobante": "CPG-2025-0001",
      "tipo": "sena",
      "monto_distribuido": 1500.00
    }
  ]
}
```

---

## 🔍 VERIFICACIÓN

Para verificar que todo funciona correctamente:

1. **Ejecutar el script de prueba:**
   ```bash
   cd GroupTours
   python test_senia_monto_fijo.py
   ```

2. **Verificar en Django Shell:**
   ```python
   from apps.reserva.models import Reserva, Pasajero
   from decimal import Decimal

   # Obtener una reserva
   reserva = Reserva.objects.first()

   # Verificar seña total
   print(f"Seña por pasajero: {reserva.salida.senia}")
   print(f"Cantidad pasajeros: {reserva.cantidad_pasajeros}")
   print(f"Seña total: {reserva.seña_total}")
   # Debe mostrar: seña_total = salida.senia × cantidad_pasajeros

   # Verificar seña de un pasajero
   pasajero = reserva.pasajeros.first()
   print(f"Seña requerida del pasajero: {pasajero.seña_requerida}")
   # Debe mostrar: seña_requerida = salida.senia (monto fijo)
   ```

---

## ✅ CHECKLIST FINAL

- [x] Modificado `Pasajero.seña_requerida` para usar monto fijo
- [x] `Reserva.seña_total` ya estaba correcto (usa monto fijo)
- [x] Script de prueba creado y ejecutado exitosamente
- [x] Validación con datos reales del sistema
- [x] Documentación actualizada

---

## 📝 NOTAS IMPORTANTES

1. **La seña es un monto fijo por pasajero**, no un porcentaje del precio
2. **Se configura en `SalidaPaquete.senia`** al crear la salida del paquete
3. **La seña total de la reserva** = `salida.senia × cantidad_pasajeros`
4. **Cada pasajero** tiene la misma seña requerida (el monto fijo de la salida)
5. **No se requiere migración** ya que solo se modificó el cálculo de una propiedad

---

**Fecha:** 25 de Octubre, 2025
**Autor:** Claude Code Assistant
**Versión:** 1.0.0
