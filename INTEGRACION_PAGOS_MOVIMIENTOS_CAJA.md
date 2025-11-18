# Integración de Pagos con Movimientos de Caja

## Resumen

Este documento describe la implementación de la integración automática entre los **ComprobantePago** y los **MovimientoCaja**, permitiendo que cada pago registrado en el sistema genere automáticamente un movimiento en la caja del empleado responsable.

---

## Conceptos Clave

### Diferencia entre Factura y Pago

**Importante:** Es fundamental entender que una factura NO es lo mismo que un pago:

- **Factura (FacturaElectronica)**:
  - Documento fiscal/tributario
  - Documenta la obligación de pago
  - Puede ser a crédito (sin movimiento inmediato de dinero)
  - **NO genera movimiento de caja**

- **Pago (ComprobantePago)**:
  - Movimiento real de dinero
  - Ingreso efectivo a la caja
  - **SÍ genera movimiento de caja**

### Flujos de Negocio

#### Caso 1: Factura de Contado
```
1. Cliente paga → ComprobantePago → MovimientoCaja (ingreso)
2. Se emite factura → FacturaElectronica (solo documento)
```

#### Caso 2: Factura a Crédito
```
1. Se emite factura → FacturaElectronica (sin movimiento de caja)
2. [30 días después]
3. Cliente paga → ComprobantePago → MovimientoCaja (ingreso)
```

#### Caso 3: Seña/Anticipo
```
1. Cliente paga seña → ComprobantePago → MovimientoCaja (ingreso)
2. [Al finalizar reserva]
3. Cliente paga saldo → ComprobantePago → MovimientoCaja (ingreso)
4. Se emite factura → FacturaElectronica (documento final)
```

---

## Implementación

### 1. Generación Automática de Movimientos

Cuando se crea un **ComprobantePago**, el sistema automáticamente:

1. Verifica si el empleado tiene una **AperturaCaja activa**
2. Si existe, crea un **MovimientoCaja** asociado
3. Si no existe, el pago se registra igual pero **sin movimiento de caja**

#### Validaciones Importantes

✅ **Condiciones para generar MovimientoCaja:**
- El ComprobantePago debe ser **nuevo** (no una edición)
- El ComprobantePago debe estar **activo**
- Debe existir una **AperturaCaja abierta** para el empleado
- La apertura debe estar a nombre del **mismo empleado** que registra el pago

❌ **NO se genera MovimientoCaja si:**
- El empleado no tiene ninguna caja abierta
- La caja está a nombre de otro empleado
- El comprobante está inactivo/anulado

### 2. Mapeo de Métodos de Pago a Conceptos

El sistema mapea automáticamente los métodos de pago a conceptos de MovimientoCaja:

#### Pagos Normales (Ingresos)

| Método de Pago | Concepto MovimientoCaja |
|----------------|-------------------------|
| efectivo | venta_efectivo |
| tarjeta_debito | venta_tarjeta |
| tarjeta_credito | venta_tarjeta |
| transferencia | transferencia_recibida |
| cheque | otro_ingreso |
| qr | otro_ingreso |
| otro | otro_ingreso |

#### Devoluciones (Egresos)

| Método de Pago | Concepto MovimientoCaja |
|----------------|-------------------------|
| Todos | devolucion |

### 3. Información Registrada en MovimientoCaja

Cada MovimientoCaja generado incluye:

- **apertura_caja**: La apertura activa del empleado
- **comprobante**: Referencia al ComprobantePago
- **tipo_movimiento**: 'ingreso' o 'egreso' (según tipo de comprobante)
- **concepto**: Mapeado según método de pago
- **monto**: Monto del comprobante
- **metodo_pago**: Mismo método del comprobante
- **referencia**: Número del comprobante (CPG-2025-XXXX)
- **descripcion**:
  ```
  Pago de reserva RSV-2025-XXXX - Comprobante CPG-2025-XXXX
  Obs: [observaciones del comprobante si existen]
  ```
- **usuario_registro**: El empleado que registró el pago

---

## Anulaciones

### Proceso de Anulación

Cuando se anula un **ComprobantePago** mediante el método `anular()`:

1. El comprobante se marca como **activo=False**
2. Se busca el **MovimientoCaja** asociado
3. Si existe, se anula también (activo=False)
4. Se agrega el motivo de anulación a la descripción
5. Se **recalcula el saldo de la caja** automáticamente

### Recálculo de Saldo

El método `actualizar_saldo_caja()` recalcula el saldo desde cero:

```python
saldo_actual = monto_inicial + sum(ingresos_activos) - sum(egresos_activos)
```

Esto asegura que:
- Los movimientos anulados NO afectan el saldo
- El saldo siempre es correcto
- No hay errores acumulativos

---

## Métodos Implementados

### En ComprobantePago

#### `_obtener_apertura_activa_empleado()`
```python
"""
Obtiene la apertura de caja activa del empleado que registra el pago.

Returns:
    AperturaCaja o None si no hay apertura activa para el empleado
"""
```

**Criterios de búsqueda:**
- `responsable = self.empleado`
- `esta_abierta = True`
- `activo = True`

---

#### `_mapear_metodo_pago_a_concepto()`
```python
"""
Mapea el método de pago del comprobante al concepto de MovimientoCaja.

Returns:
    str: Concepto para MovimientoCaja
"""
```

**Lógica:**
- Si `tipo = 'devolucion'` → usa mapeo de egresos
- Si no → usa mapeo de ingresos
- Fallback a 'otro_ingreso' o 'otro_egreso' si no encuentra match

---

#### `_generar_movimiento_caja()`
```python
"""
Genera automáticamente un MovimientoCaja cuando se registra un pago.
Solo se genera si el empleado tiene una caja abierta.

Returns:
    MovimientoCaja o None si no hay caja abierta
"""
```

**Proceso:**
1. Busca apertura activa del empleado
2. Si no existe, retorna None (sin error)
3. Determina tipo de movimiento (ingreso/egreso)
4. Mapea concepto según método de pago
5. Crea descripción detallada
6. Crea y guarda el MovimientoCaja
7. El saldo se actualiza automáticamente en el save()

---

#### `_anular_movimiento_caja(motivo=None)`
```python
"""
Anula el movimiento de caja asociado a este comprobante.

Args:
    motivo: Motivo de la anulación
"""
```

**Proceso:**
1. Busca MovimientoCaja con `comprobante=self` y `activo=True`
2. Lo marca como `activo=False`
3. Agrega el motivo a la descripción
4. Guarda (el save() recalcula el saldo automáticamente)

---

#### Modificación en `save()`
```python
def save(self, *args, **kwargs):
    es_nuevo = self._state.adding  # True si es un nuevo comprobante

    # ... generación de número ...

    super().save(*args, **kwargs)

    # Generar movimiento de caja automáticamente si es nuevo y activo
    if es_nuevo and self.activo:
        self._generar_movimiento_caja()
```

---

#### Modificación en `anular(motivo=None)`
```python
def anular(self, motivo=None):
    """
    Anula el comprobante y actualiza el monto de la reserva.
    También anula el movimiento de caja asociado si existe.
    """
    self.activo = False
    if motivo:
        self.observaciones = f"ANULADO: {motivo}\n{self.observaciones or ''}"
    self.save()

    # NUEVO: Anular movimiento de caja asociado
    self._anular_movimiento_caja(motivo)

    self.actualizar_monto_reserva()
```

---

### En MovimientoCaja

#### `actualizar_saldo_caja()` - Mejorado
```python
"""
Recalcula el saldo de la caja desde cero basándose en todos los movimientos activos.
Esto asegura que el saldo sea correcto incluso después de anulaciones.
"""
```

**Cambio principal:**
- Antes: Sumaba/restaba el monto del movimiento actual
- Ahora: **Recalcula todo desde cero** considerando solo movimientos activos

**Ventajas:**
- ✅ Maneja correctamente las anulaciones
- ✅ No hay errores acumulativos
- ✅ El saldo siempre es preciso
- ✅ Permite auditorías y correcciones

**Fórmula:**
```
saldo_actual = monto_inicial + Σ(ingresos_activos) - Σ(egresos_activos)
```

---

## Ejemplos de Uso

### Ejemplo 1: Pago en Efectivo con Caja Abierta

```python
# El empleado tiene una caja abierta
apertura = AperturaCaja.objects.create(
    caja=caja_principal,
    responsable=empleado_juan,
    monto_inicial=500000
)

# Se registra un pago
comprobante = ComprobantePago.objects.create(
    reserva=reserva,
    tipo='sena',
    monto=1000000,
    metodo_pago='efectivo',
    empleado=empleado_juan
)

# ✅ Automáticamente se crea:
# MovimientoCaja:
#   - apertura_caja = apertura
#   - tipo_movimiento = 'ingreso'
#   - concepto = 'venta_efectivo'
#   - monto = 1000000
#   - comprobante = comprobante

# El saldo de la caja se actualiza:
# saldo_actual = 500000 + 1000000 = 1500000
```

---

### Ejemplo 2: Pago sin Caja Abierta

```python
# El empleado NO tiene caja abierta

comprobante = ComprobantePago.objects.create(
    reserva=reserva,
    tipo='sena',
    monto=1000000,
    metodo_pago='efectivo',
    empleado=empleado_pedro
)

# ✅ El comprobante se registra normalmente
# ❌ NO se crea MovimientoCaja (el empleado no tiene caja abierta)
# ℹ️  No hay error, el sistema continúa normalmente
```

---

### Ejemplo 3: Anulación de Pago

```python
# Anular un comprobante existente
comprobante.anular(motivo="Pago duplicado por error")

# ✅ El comprobante se marca como activo=False
# ✅ El MovimientoCaja asociado se marca como activo=False
# ✅ El saldo se recalcula automáticamente (excluyendo el movimiento anulado)
# ✅ El monto_pagado de la reserva se actualiza
```

---

### Ejemplo 4: Devolución

```python
# Registrar una devolución
comprobante_devolucion = ComprobantePago.objects.create(
    reserva=reserva,
    tipo='devolucion',
    monto=200000,
    metodo_pago='efectivo',
    empleado=empleado_juan
)

# ✅ Se crea MovimientoCaja:
#   - tipo_movimiento = 'egreso'
#   - concepto = 'devolucion'
#   - monto = 200000

# El saldo de la caja se reduce:
# saldo_actual = saldo_anterior - 200000
```

---

## Consideraciones de Seguridad y Trazabilidad

### 1. Responsabilidad Individual
- Cada empleado solo puede registrar movimientos en **su propia caja**
- No se pueden registrar movimientos en la caja de otro empleado
- Garantiza la responsabilidad individual del efectivo

### 2. Auditoría Completa
- Todos los movimientos quedan registrados
- Se mantiene la relación `MovimientoCaja → ComprobantePago`
- Se puede rastrear el origen de cada movimiento

### 3. Integridad de Datos
- El saldo se recalcula siempre desde los movimientos activos
- No hay posibilidad de descuadres por operaciones parciales
- Las anulaciones no dejan saldos incorrectos

### 4. Validaciones
- No se permite registrar movimientos en cajas cerradas
- El monto debe ser mayor a cero
- El concepto debe ser válido según el tipo de movimiento

---

## Próximos Pasos Sugeridos

### 1. Reportes
- Reporte de movimientos por caja
- Reporte de pagos sin movimiento de caja (empleado sin caja abierta)
- Comparación entre comprobantes y movimientos

### 2. Validaciones Adicionales
- Alertar al empleado si intenta registrar un pago sin caja abierta
- Validar que el método de pago sea consistente con la caja

### 3. Interfaz de Usuario
- Mostrar el estado de la caja al registrar un pago
- Indicar visualmente si se generará o no un movimiento de caja
- Permitir abrir caja directamente desde el formulario de pago

---

## Migración de Datos

Si ya existen **ComprobantePago** en la base de datos:

**⚠️ Importante:** Los comprobantes existentes NO generarán MovimientoCaja automáticamente porque ya están guardados. Solo los nuevos comprobantes generarán movimientos.

Si se desea crear movimientos para pagos históricos, se puede ejecutar un script de migración que:
1. Identifique ComprobantePago activos sin MovimientoCaja asociado
2. Para cada uno, busque la apertura activa del empleado en esa fecha
3. Si existe, cree el MovimientoCaja correspondiente

---

## Archivo Modificado

### `GroupTours/apps/comprobante/models.py`
- ✅ Método `save()` modificado
- ✅ Método `_obtener_apertura_activa_empleado()` agregado
- ✅ Método `_mapear_metodo_pago_a_concepto()` agregado
- ✅ Método `_generar_movimiento_caja()` agregado
- ✅ Método `anular()` modificado
- ✅ Método `_anular_movimiento_caja()` agregado

### `GroupTours/apps/arqueo_caja/models.py`
- ✅ Método `actualizar_saldo_caja()` mejorado (recálculo completo)

---

## Testing Recomendado

### Casos de Prueba

1. **Pago normal con caja abierta**
   - ✅ Se crea MovimientoCaja
   - ✅ El saldo se actualiza correctamente

2. **Pago sin caja abierta**
   - ✅ El pago se registra
   - ✅ NO se crea MovimientoCaja
   - ✅ No hay error

3. **Anulación de pago**
   - ✅ El comprobante se anula
   - ✅ El movimiento se anula
   - ✅ El saldo se recalcula correctamente

4. **Devolución**
   - ✅ Se crea MovimientoCaja tipo 'egreso'
   - ✅ El saldo disminuye

5. **Múltiples pagos y anulaciones**
   - ✅ El saldo final es correcto
   - ✅ Solo cuenta movimientos activos

---

## Conclusión

La integración automática entre **ComprobantePago** y **MovimientoCaja** permite:

✅ **Trazabilidad completa** de los ingresos/egresos de caja
✅ **Automatización** del registro de movimientos
✅ **Responsabilidad individual** por empleado
✅ **Integridad** de los saldos mediante recálculo completo
✅ **Flexibilidad** para registrar pagos sin caja abierta
✅ **Auditoría** completa de todas las operaciones

El sistema ahora refleja fielmente el flujo real de dinero en las cajas, manteniendo la consistencia entre los pagos registrados y los movimientos de efectivo.
