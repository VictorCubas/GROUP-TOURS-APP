# Solución: Generación Automática de Vouchers

## Problema Identificado

Los vouchers no se generaban automáticamente cuando:
1. Se registraba un pago completo (100%) para un pasajero con datos reales
2. Se actualizaba un pasajero de "Por Asignar" a datos reales Y tenía pago completo

### Causa Raíz

El signal `crear_voucher_para_pasajero` solo se disparaba en el evento `post_save` del modelo `Pasajero`. Sin embargo, cuando se registraba un pago:

- Se creaba un `ComprobantePago`
- Se creaban `ComprobantePagoDistribucion` vinculadas al pasajero
- Se actualizaba `reserva.monto_pagado`
- **PERO NO se guardaba el modelo `Pasajero`**, por lo que el signal nunca se ejecutaba

El cálculo de `monto_pagado` y `esta_totalmente_pagado` son propiedades calculadas del pasajero que leen las distribuciones, pero como el pasajero no se guardaba, el signal no se disparaba.

## Solución Implementada

### 1. Nueva Función Auxiliar

Se creó la función `generar_voucher_si_cumple_condiciones(pasajero)` que centraliza la lógica de verificación y generación de vouchers. Esta función:

- Verifica que el pasajero cumpla ambas condiciones:
  - `por_asignar=False` (tiene datos reales)
  - `esta_totalmente_pagado=True` (pagó el 100%)
- Verifica que no exista un voucher previo
- Crea el voucher y genera el código QR automáticamente
- Actualiza el campo `voucher_codigo` en el pasajero

### 2. Signal para Pasajero (Mejorado)

```python
@receiver(post_save, sender=Pasajero)
def crear_voucher_para_pasajero_al_guardar(sender, instance, created, **kwargs):
```

Se ejecuta cuando:
- Se crea un pasajero nuevo con datos completos y pago total
- Se actualiza un pasajero (ej: cambiar de `por_asignar=True` a `False`)

**Casos de uso:**
- Cuando se asigna una persona real a un pasajero que estaba "Por Asignar"
- Cuando se actualiza la información de un pasajero mediante `PUT /api/pasajeros/{id}/`

### 3. Signal para ComprobantePagoDistribucion (NUEVO)

```python
@receiver(post_save, sender=ComprobantePagoDistribucion)
def crear_voucher_para_pasajero_al_pagar(sender, instance, created, **kwargs):
```

Se ejecuta cuando:
- Se crea una nueva distribución de pago (registro de pago parcial o total)
- Se actualiza una distribución existente

**Casos de uso:**
- `POST /api/reservas/{id}/registrar-senia/`
- `POST /api/reservas/{id}/registrar-pago/`
- Cualquier otro flujo que cree distribuciones de pago

## Flujos de Generación Automática

### Flujo 1: Pago Total para Pasajero con Datos Reales

```
1. Pasajero ID 296 ya existe con datos reales (por_asignar=False)
2. Cliente hace POST /api/reservas/179/registrar-pago/
   {
     "metodo_pago": "efectivo",
     "distribuciones": [{"pasajero": 296, "monto": 730}],
     "tipo": "pago_total"
   }
3. Se crea ComprobantePago
4. Se crea ComprobantePagoDistribucion para pasajero 296
5. ✨ Signal "crear_voucher_para_pasajero_al_pagar" se dispara
6. Verifica: por_asignar=False ✓ y esta_totalmente_pagado=True ✓
7. Genera Voucher automáticamente con código QR
8. Actualiza pasajero.voucher_codigo
```

### Flujo 2: Asignar Datos Reales a Pasajero con Pago Completo

```
1. Pasajero ID 300 existe como "Por Asignar 3" (por_asignar=True)
2. Ya tiene pago completo registrado: monto_pagado = precio_asignado
3. Se hace PUT /api/pasajeros/300/
   {
     "persona_id": 150  // Asignar persona real
   }
4. PasajeroViewSet.perform_update() detecta el cambio
5. Cambia por_asignar a False automáticamente
6. Guarda el pasajero
7. ✨ Signal "crear_voucher_para_pasajero_al_guardar" se dispara
8. Verifica: por_asignar=False ✓ y esta_totalmente_pagado=True ✓
9. Genera Voucher automáticamente con código QR
10. Actualiza pasajero.voucher_codigo
```

### Flujo 3: Pagos Parciales que Completan el 100%

```
1. Pasajero ID 296 con datos reales ya tiene 50% pagado
2. Se registra pago parcial adicional del 50%
3. POST /api/reservas/179/registrar-pago/
   {
     "metodo_pago": "efectivo",
     "distribuciones": [{"pasajero": 296, "monto": 365}],
     "tipo": "pago_parcial"
   }
4. Se crea ComprobantePagoDistribucion
5. ✨ Signal se dispara
6. Ahora esta_totalmente_pagado=True (50% + 50% = 100%)
7. Genera Voucher automáticamente
```

## Condiciones para Generación Automática

El voucher se genera **ÚNICAMENTE** cuando se cumplen **AMBAS** condiciones:

1. **Datos Reales Completos**: `pasajero.por_asignar = False`
   - El pasajero tiene nombre, apellido, documento válidos
   - NO es un pasajero "Por Asignar X"

2. **Pago Completo**: `pasajero.esta_totalmente_pagado = True`
   - La suma de todas las distribuciones de pago activas es >= precio_asignado
   - `pasajero.saldo_pendiente <= 0`

## Verificación del Voucher en el API

El endpoint de detalles de reserva incluye automáticamente el voucher:

```
GET /api/reservas/179/
```

Respuesta (extracto):
```json
{
  "pasajeros": [
    {
      "id": 296,
      "persona": {
        "nombre": "Juan",
        "apellido": "Pérez"
      },
      "por_asignar": false,
      "esta_totalmente_pagado": true,
      "voucher_codigo": "RSV-2025-0179-PAX-296-VOUCHER",
      "voucher_id": 42
    }
  ]
}
```

## Endpoints para Descargar Voucher

Una vez generado, el voucher puede descargarse:

```bash
# Descargar PDF del voucher individual
GET /api/vouchers/{voucher_id}/descargar-pdf/

# Descargar todos los vouchers de una reserva en ZIP
GET /api/reservas/{reserva_id}/descargar-vouchers/
```

## Logs del Sistema

El sistema genera logs informativos:

```
[INFO] Pago registrado para pasajero 296. Verificando condiciones para voucher...
[OK] Voucher generado: RSV-2025-0179-PAX-296-VOUCHER para pasajero Juan Pérez
```

O si ya existe:
```
[INFO] Voucher ya existe para pasajero 296: RSV-2025-0179-PAX-296-VOUCHER
```

## Archivos Modificados

1. **`GroupTours/apps/comprobante/signals.py`**
   - Agregada función `generar_voucher_si_cumple_condiciones()`
   - Mejorado signal `crear_voucher_para_pasajero_al_guardar()`
   - Nuevo signal `crear_voucher_para_pasajero_al_pagar()`

## Pruebas Recomendadas

### Caso 1: Pago Total Directo
```bash
POST /api/reservas/179/registrar-pago/
{
  "metodo_pago": "efectivo",
  "distribuciones": [{"pasajero": 296, "monto": 730}],
  "tipo": "pago_total"
}

# Verificar:
GET /api/reservas/179/
# Debe mostrar voucher_id y voucher_codigo en el pasajero 296
```

### Caso 2: Asignar Pasajero con Pago Completo
```bash
# 1. Crear reserva con pasajero "Por Asignar"
# 2. Registrar pago total
POST /api/reservas/179/registrar-pago/
{
  "metodo_pago": "efectivo",
  "distribuciones": [{"pasajero": "pendiente_1", "monto": 730}],
  "tipo": "pago_total"
}

# 3. Asignar datos reales al pasajero
PUT /api/pasajeros/{pasajero_id}/
{
  "persona_id": 150
}

# Verificar:
GET /api/pasajeros/{pasajero_id}/estado-cuenta/
# Debe mostrar voucher_id y voucher_codigo
```

### Caso 3: Pagos Parciales Acumulativos
```bash
# 1. Registrar seña (30%)
POST /api/reservas/179/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [{"pasajero": 296, "monto": 219}]
}

# 2. Pago parcial (50%)
POST /api/reservas/179/registrar-pago/
{
  "metodo_pago": "efectivo",
  "distribuciones": [{"pasajero": 296, "monto": 365}],
  "tipo": "pago_parcial"
}

# 3. Pago final (20%)
POST /api/reservas/179/registrar-pago/
{
  "metodo_pago": "efectivo",
  "distribuciones": [{"pasajero": 296, "monto": 146}],
  "tipo": "pago_parcial"
}

# Verificar después del último pago:
GET /api/reservas/179/
# Debe mostrar voucher generado
```

## Notas Importantes

1. **No se genera duplicado**: Si el pasajero ya tiene un voucher, no se crea otro aunque se registren más pagos.

2. **El QR se genera automáticamente**: Al crear el voucher, se genera el código QR con la información del pasajero y reserva.

3. **Pasajeros "Por Asignar" NO generan voucher**: Aunque tengan pago completo, necesitan datos reales primero.

4. **Comprobantes anulados no cuentan**: El signal solo verifica distribuciones de comprobantes con `activo=True`.

5. **El campo `voucher_codigo` se actualiza**: Se copia el código del voucher al campo `voucher_codigo` del pasajero para consultas rápidas.

## Resolución del Problema Original

Tu caso específico:
- **Reserva 179, Pasajero 296**
- Ya tenía datos reales (`por_asignar=False`)
- Registraste pago total de 730

Con esta solución, al hacer:
```
POST /api/reservas/179/registrar-pago/
{
  "metodo_pago": "efectivo",
  "distribuciones": [{"pasajero": 296, "monto": 730}],
  "tipo": "pago_total"
}
```

El sistema automáticamente:
1. ✅ Crea el comprobante
2. ✅ Crea la distribución para pasajero 296
3. ✅ Dispara el signal
4. ✅ Verifica que cumple las condiciones
5. ✅ Genera el voucher con código QR
6. ✅ Lo incluye en el endpoint `GET /api/reservas/179/`
