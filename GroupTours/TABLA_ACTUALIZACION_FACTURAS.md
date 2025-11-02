# Tabla de Actualización de Campos de Facturación

## 📊 Matriz de Actualización Automática

Esta tabla muestra cómo se actualizan los campos `puede_descargar_factura_global` y `puede_descargar_factura` según los eventos del sistema.

| Evento | Modalidad Global<br>`puede_descargar_factura_global` | Modalidad Individual<br>`puede_descargar_factura` | Observaciones |
|--------|------------------------------------------------------|--------------------------------------------------|---------------|
| **Crear Reserva** | ❌ False<br>(sin pagos) | ❌ False<br>(sin pagos o sin datos) | Valores iniciales |
| **Registrar Seña** | ❌ False<br>(pago parcial) | ❌ False<br>(pago parcial) | Aún no está completo |
| **Registrar Pago Parcial** | ❌ False<br>(no 100%) | Variable<br>✅ Si pasajero al 100%<br>❌ Si pasajero < 100% | Se evalúa por pasajero |
| **Registrar Pago Total<br>(último pago)** | ✅ True<br>(si estado=finalizada) | ✅ True<br>(para pasajeros con datos reales y 100% pagado) | Se recalcula automáticamente |
| **Asignar Persona Real<br>(PATCH pasajero)** | 🔄 Indirecto<br>(puede cambiar estado a finalizada) | ✅ True<br>(si ya estaba 100% pagado) | Actualización directa del campo |
| **Actualizar Estado<br>(confirmada → finalizada)** | ✅ True<br>(si ya está 100% pagado) | Sin cambio<br>(depende de cada pasajero) | Cambio de estado automático |

---

## 🔍 Escenarios Detallados

### Escenario 1: Modalidad Global - Flujo Completo

```
Evento                          | puede_descargar_factura_global | Estado Reserva | Observación
-------------------------------|-------------------------------|----------------|------------------
1. Crear reserva               | ❌ False                       | pendiente      | Sin pagos
2. Registrar seña (30%)        | ❌ False                       | confirmada     | Pago parcial
3. Registrar pago parcial (40%)| ❌ False                       | confirmada     | Total: 70%
4. Registrar último pago (30%) | ✅ True                        | finalizada     | ¡100% pagado!
5. Consultar GET /api/reserva/ | ✅ True                        | finalizada     | Campo actualizado
```

**Resultado:** El botón "Generar Factura Global" se habilita automáticamente después del último pago.

---

### Escenario 2: Modalidad Individual - Pago Primero

```
Pasajero | Evento                  | por_asignar | monto_pagado | puede_descargar_factura | Acción
---------|------------------------|-------------|--------------|------------------------|--------
Juan     | Crear con datos reales | ❌ False     | 0            | ❌ False                | -
Juan     | Pagar 100%             | ❌ False     | 5000 (100%)  | ✅ True                 | Habilitar botón
María    | Crear temporal         | ✅ True      | 0            | ❌ False                | -
María    | Pagar 100%             | ✅ True      | 5000 (100%)  | ❌ False                | Aún es temporal
María    | Asignar persona real   | ❌ False     | 5000 (100%)  | ✅ True                 | ¡Habilitar botón!
```

**Resultado:** El campo se actualiza inmediatamente después de asignar la persona real.

---

### Escenario 3: Modalidad Individual - Asignación Primero

```
Pasajero | Evento                  | por_asignar | monto_pagado | puede_descargar_factura | Acción
---------|------------------------|-------------|--------------|------------------------|--------
Pedro    | Crear temporal         | ✅ True      | 0            | ❌ False                | -
Pedro    | Asignar persona real   | ❌ False     | 0            | ❌ False                | Sin pago aún
Pedro    | Pagar 50%              | ❌ False     | 2500 (50%)   | ❌ False                | Pago parcial
Pedro    | Pagar 50% restante     | ❌ False     | 5000 (100%)  | ✅ True                 | ¡Habilitar botón!
```

**Resultado:** El botón se habilita cuando se completa el pago (ya tenía datos reales).

---

## 🎯 Reglas de Negocio

### Para `puede_descargar_factura_global` (Modalidad Global)

```
puede_descargar_factura_global =
    modalidad == 'global'
    AND estado == 'finalizada'
    AND monto_pagado >= costo_total_estimado
```

### Para `puede_descargar_factura` (Modalidad Individual)

```
puede_descargar_factura (por pasajero) =
    modalidad == 'individual'
    AND estado IN ['confirmada', 'finalizada']
    AND pasajero.por_asignar == False
    AND pasajero.monto_pagado >= pasajero.precio_asignado
```

---

## 🔄 Flujo de Actualización Técnica

### Cuando se registra un pago:

1. Se crea el `ComprobantePago` con distribuciones
2. Se llama a `comprobante.actualizar_monto_reserva()`
3. Se actualiza `reserva.monto_pagado`
4. Se llama a `reserva.actualizar_estado()`
5. Si está totalmente pagada → `estado = 'finalizada'`
6. **En la siguiente consulta:**
   - `puede_descargar_factura_global` se recalcula (SerializerMethodField)
   - `puede_descargar_factura` se recalcula por cada pasajero

### Cuando se asigna un pasajero:

1. Se ejecuta `PATCH /api/pasajeros/{id}/` con `persona_id`
2. `PasajeroViewSet.perform_update()` detecta el cambio
3. Si `por_asignar == True` → cambia a `False` automáticamente
4. Se guarda el pasajero
5. Se llama a `reserva.actualizar_estado()`
6. **En la respuesta del PATCH:**
   - `puede_descargar_factura` se recalcula (SerializerMethodField)
   - Si ya estaba pagado al 100%, ahora será `True`

---

## 💡 Importante

### Los campos son calculados dinámicamente

- ✅ NO se guardan en la base de datos
- ✅ Se calculan en cada serialización
- ✅ Siempre reflejan el estado actual
- ✅ No requieren actualización manual

### Frontend debe:

1. **Después de registrar pago:**
   - Hacer `GET /api/reserva/{id}/` para ver el estado actualizado
   - Verificar `puede_descargar_factura_global` (global)
   - Verificar `puede_descargar_factura` por cada pasajero (individual)

2. **Después de asignar pasajero:**
   - Usar directamente la respuesta del `PATCH /api/pasajeros/{id}/`
   - O hacer `GET /api/reserva/{id}/` para ver todos los pasajeros actualizados

3. **En cualquier momento:**
   - Los campos siempre estarán actualizados en cada consulta
   - No hay necesidad de "refrescar" manualmente
