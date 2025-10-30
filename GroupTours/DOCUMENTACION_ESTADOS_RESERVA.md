# Documentación: Estados de Reserva y Gestión de Pasajeros

## 📋 Tabla de Contenidos

1. [Estados de Reserva](#estados-de-reserva)
2. [Propiedades Clave](#propiedades-clave)
3. [Lógica de Transición de Estados](#lógica-de-transición-de-estados)
4. [Pasajeros "Por Asignar"](#pasajeros-por-asignar)
5. [Escenarios de Actualización](#escenarios-de-actualización)
6. [API Endpoints](#api-endpoints)
7. [Ejemplos de Uso](#ejemplos-de-uso)

---

## Estados de Reserva

Una reserva puede tener **4 estados posibles**:

### 1. 🟡 PENDIENTE
**Condición:** No se ha pagado la seña requerida

```python
estado = "pendiente"
```

**Características:**
- Reserva creada pero sin pago suficiente
- `monto_pagado < seña_total`
- `datos_completos` puede ser `true` o `false`
- **Texto UI:** "Pendiente de seña"

**Transiciones posibles:**
- ➡️ CONFIRMADA (cuando se paga la seña)
- ➡️ CANCELADA (cuando se cancela)

---

### 2. 🟢 CONFIRMADA
**Condición:** Seña pagada, pero pago no está 100% completo

```python
estado = "confirmada"
```

**Características:**
- `monto_pagado >= seña_total`
- `monto_pagado < costo_total_estimado` (no está 100% pagado)
- Cupo asegurado
- Tiene dos sub-estados según `datos_completos`:

#### Confirmado Incompleto
```python
estado = "confirmada"
datos_completos = False
estado_display = "Confirmado Incompleto"
```
- Faltan datos de pasajeros por cargar
- Existen pasajeros "Por Asignar"

#### Confirmado Completo
```python
estado = "confirmada"
datos_completos = True
estado_display = "Confirmado Completo"
```
- Todos los pasajeros están cargados con datos reales
- No hay pasajeros "Por Asignar"
- Solo falta completar el pago

**Transiciones posibles:**
- ➡️ FINALIZADA (cuando se completa el pago 100% Y datos_completos=True)
- ➡️ PENDIENTE (si se anula un pago y cae por debajo de la seña)
- ➡️ CANCELADA (cuando se cancela)

---

### 3. ✅ FINALIZADA
**Condición:** Pago 100% completo Y todos los pasajeros cargados

```python
estado = "finalizada"
```

**Características:**
- `monto_pagado >= costo_total_estimado` (100% pagado)
- `datos_completos = True` (todos los pasajeros reales cargados)
- Reserva lista para el viaje
- **Texto UI:** "Finalizado"

**Transiciones posibles:**
- ➡️ CANCELADA (cuando se cancela)

---

### 4. ❌ CANCELADA
**Condición:** Reserva cancelada manualmente

```python
estado = "cancelada"
```

**Características:**
- Reserva cancelada, no se procesa más
- Estado terminal (no cambia más)
- **Texto UI:** "Cancelado"

**Transiciones posibles:**
- Ninguna (estado final)

---

## Propiedades Clave

### `cantidad_pasajeros` (Integer)
Cantidad total de pasajeros esperados en la reserva.

**Ejemplo:** Si una familia reserva para 4 personas, `cantidad_pasajeros = 4`

---

### `pasajeros_cargados` (Property)
Cantidad de pasajeros **REALES** registrados en la reserva.

**Cálculo:**
```python
@property
def pasajeros_cargados(self):
    """Excluye pasajeros pendientes (con _PEND en documento)"""
    return self.pasajeros.exclude(persona__documento__contains='_PEND').count()
```

**Diferencia con pasajeros totales:**
- **Pasajeros reales:** Personas con datos completos (ej: documento "12345678")
- **Pasajeros "Por Asignar":** Placeholders temporales (ej: documento "12345678_PEND_1")

---

### `faltan_datos_pasajeros` (Property)
Indica si faltan datos de pasajeros por cargar.

**Cálculo:**
```python
@property
def faltan_datos_pasajeros(self):
    return self.pasajeros_cargados < self.cantidad_pasajeros
```

**Ejemplo:**
```python
cantidad_pasajeros = 4
pasajeros_cargados = 3  # 3 reales + 1 "Por Asignar"
faltan_datos_pasajeros = True  # (3 < 4)
```

---

### `datos_completos` (Boolean)
Flag que indica si todos los pasajeros están cargados.

**Cálculo:**
```python
datos_completos = not self.faltan_datos_pasajeros
```

**Ejemplo:**
```python
# Caso 1: Faltan datos
cantidad_pasajeros = 4
pasajeros_cargados = 2
datos_completos = False

# Caso 2: Datos completos
cantidad_pasajeros = 4
pasajeros_cargados = 4
datos_completos = True
```

---

### `monto_pagado` (Decimal)
Monto total abonado hasta el momento.

Se actualiza automáticamente cuando se registran comprobantes de pago.

---

### `seña_total` (Property)
Seña total requerida según la cantidad de pasajeros.

**Cálculo:**
```python
@property
def seña_total(self):
    if self.salida and self.salida.senia:
        return self.salida.senia * self.cantidad_pasajeros
    return 0
```

**Ejemplo:**
```python
senia_por_pasajero = 220  # De SalidaPaquete
cantidad_pasajeros = 4
seña_total = 880  # (220 * 4)
```

---

### `costo_total_estimado` (Property)
Costo total de la reserva (incluye paquete + servicios adicionales).

**Cálculo:**
```python
@property
def costo_total_estimado(self):
    base = (self.precio_unitario or 0) * self.cantidad_pasajeros
    adicionales = self.costo_servicios_adicionales
    return base + adicionales
```

---

## Lógica de Transición de Estados

### Método `actualizar_estado()`

Este método es el corazón de la máquina de estados de las reservas.

```python
def actualizar_estado(self):
    """
    Actualiza el estado de la reserva según pago y carga de pasajeros.
    """
    # No modificar reservas canceladas
    if self.estado == "cancelada":
        return

    # 1. Actualizar flag de datos completos
    self.datos_completos = not self.faltan_datos_pasajeros

    # 2. Determinar nuevo estado según pago y datos
    if self.esta_totalmente_pagada() and self.datos_completos:
        # ✅ Pago 100% + todos los pasajeros → FINALIZADA
        self.estado = "finalizada"
    elif self.puede_confirmarse():
        # ✅ Seña pagada → CONFIRMADA
        self.estado = "confirmada"
    else:
        # ❌ Sin seña → PENDIENTE
        self.estado = "pendiente"

    # 3. Guardar cambios
    self.save(update_fields=["estado", "datos_completos"])
```

---

### Método `puede_confirmarse()`

Determina si la reserva puede estar en estado CONFIRMADA.

**Lógica con dos caminos:**

#### Camino 1: Faltan datos de pasajeros
```python
if self.faltan_datos_pasajeros:
    # Validar a nivel de reserva total
    return self.monto_pagado >= self.seña_total
```

**Validación:** Compara el monto total pagado vs la seña total requerida.

**Ejemplo:**
```python
seña_total = 880  # (220 * 4 pasajeros)
monto_pagado = 880
puede_confirmarse() = True  # ✅
```

---

#### Camino 2: Todos los pasajeros cargados
```python
else:
    # Validar individualmente cada pasajero real
    pasajeros_reales = self.pasajeros.exclude(persona__documento__contains='_PEND')
    return all(pasajero.tiene_sena_pagada for pasajero in pasajeros_reales)
```

**Validación:** TODOS los pasajeros reales deben tener su seña individual pagada.

**Ejemplo:**
```python
Pasajero 1: monto_pagado=220, seña_requerida=220 → tiene_sena_pagada=True ✅
Pasajero 2: monto_pagado=220, seña_requerida=220 → tiene_sena_pagada=True ✅
Pasajero 3: monto_pagado=150, seña_requerida=220 → tiene_sena_pagada=False ❌
Pasajero 4: monto_pagado=220, seña_requerida=220 → tiene_sena_pagada=True ✅

puede_confirmarse() = False  # ❌ (porque Pasajero 3 no tiene seña completa)
```

---

### Método `esta_totalmente_pagada()`

Determina si la reserva está 100% pagada.

**Lógica con dos caminos:**

#### Camino 1: Faltan datos de pasajeros
```python
if self.faltan_datos_pasajeros:
    # Validar a nivel de reserva total
    return self.monto_pagado >= self.costo_total_estimado
```

---

#### Camino 2: Todos los pasajeros cargados
```python
else:
    # Validar individualmente cada pasajero real
    pasajeros_reales = self.pasajeros.exclude(persona__documento__contains='_PEND')
    return all(pasajero.esta_totalmente_pagado for pasajero in pasajeros_reales)
```

**Validación:** TODOS los pasajeros reales deben tener `saldo_pendiente = 0`.

---

## Pasajeros "Por Asignar"

### ¿Qué son?

Los pasajeros "Por Asignar" son **placeholders temporales** que permiten:
- Registrar pagos antes de tener los datos completos de todos los pasajeros
- Asegurar cupos mientras se recolectan documentos
- Distribuir pagos por pasajero desde el inicio

### Características

```python
# Persona creada automáticamente para "Por Asignar 1"
PersonaFisica(
    nombre="Por Asignar 1",
    apellido="",
    documento="12345678_PEND_1",  # ← Clave: contiene _PEND
    email="titular@email.com",     # Email del titular
    telefono="0981123456",          # Teléfono del titular
    # ... otros campos del titular
)

# Pasajero asociado
Pasajero(
    reserva=reserva,
    persona=persona_pendiente,
    es_titular=False,
    por_asignar=True,  # ← Nuevo campo para identificar fácilmente
    precio_asignado=3536.00
)
```

### Campo `por_asignar` (Boolean)

**Propósito:** Identificar de forma rápida y eficiente si un pasajero está pendiente de asignación.

**Valores:**
- `True`: El pasajero está pendiente de asignación (placeholder temporal)
- `False`: El pasajero tiene datos reales de una persona

**Ventajas sobre verificar el documento:**
- ✅ Más eficiente (no requiere búsqueda de cadenas)
- ✅ Más claro en el código y frontend
- ✅ No depende de convenciones de nomenclatura
- ✅ Permite filtrar fácilmente en queries

**Uso en API:**
```json
{
  "id": 295,
  "persona": {
    "nombre": "Por Asignar 1",
    "documento": "12345678_PEND_1"
  },
  "por_asignar": true,  // ← Fácil de identificar en frontend
  "monto_pagado": 220.00
}
```

### Identificación

Los pasajeros "Por Asignar" se identifican por el patrón `_PEND` en el documento:

```python
# Excluir pasajeros "Por Asignar"
pasajeros_reales = reserva.pasajeros.exclude(persona__documento__contains='_PEND')

# Contar solo pasajeros reales
pasajeros_cargados = reserva.pasajeros.exclude(persona__documento__contains='_PEND').count()
```

### Nomenclatura

```python
# Primer pasajero sin asignar
documento = "12345678_PEND_1"
nombre = "Por Asignar 1"

# Segundo pasajero sin asignar
documento = "12345678_PEND_2"
nombre = "Por Asignar 2"

# Y así sucesivamente...
```

### Creación automática

Los pasajeros "Por Asignar" se crean automáticamente en dos momentos:

1. **Al obtener el detalle de una reserva (`GET /api/reservas/{id}/`):**
   - Si `pasajeros_cargados < cantidad_pasajeros`
   - Se crean automáticamente para completar la cantidad

2. **Al registrar seña o pagos:**
   - Si se especifica `"pasajero": "pendiente_1"` en las distribuciones
   - Se crean bajo demanda

---

## Escenarios de Actualización

### Escenario 1: Última persona por asignar (con seña pagada)

**Estado inicial:**
```json
{
  "reserva_id": 172,
  "cantidad_pasajeros": 4,
  "pasajeros_cargados": 3,
  "monto_pagado": 880,
  "seña_total": 880,
  "costo_total_estimado": 6760,
  "estado": "confirmada",
  "datos_completos": false,
  "estado_display": "Confirmado Incompleto"
}
```

**Pasajeros:**
```json
[
  {"id": 292, "persona": {"nombre": "Juan", "documento": "12345678"}},
  {"id": 293, "persona": {"nombre": "María", "documento": "87654321"}},
  {"id": 294, "persona": {"nombre": "Pedro", "documento": "11223344"}},
  {"id": 295, "persona": {"nombre": "Por Asignar 4", "documento": "12345678_PEND_4"}}
]
```

**Acción:**
```http
PATCH /api/reservas/pasajeros/295/
{
  "persona_id": 15
}
```

**Resultado:**
```json
{
  "reserva_id": 172,
  "cantidad_pasajeros": 4,
  "pasajeros_cargados": 4,  // ✅ Incrementó de 3 a 4
  "monto_pagado": 880,
  "estado": "confirmada",  // Sin cambio (falta pago total)
  "datos_completos": true,  // ✅ Cambió de false a true
  "estado_display": "Confirmado Completo"  // ✅ Cambió
}
```

**Transición:** `Confirmado Incompleto` → `Confirmado Completo`

---

### Escenario 2: Última persona por asignar (con pago 100%)

**Estado inicial:**
```json
{
  "reserva_id": 172,
  "cantidad_pasajeros": 4,
  "pasajeros_cargados": 3,
  "monto_pagado": 6760,  // 100% pagado
  "seña_total": 880,
  "costo_total_estimado": 6760,
  "estado": "confirmada",
  "datos_completos": false,
  "estado_display": "Confirmado Incompleto"
}
```

**Acción:**
```http
PATCH /api/reservas/pasajeros/295/
{
  "persona_id": 15
}
```

**Resultado:**
```json
{
  "reserva_id": 172,
  "cantidad_pasajeros": 4,
  "pasajeros_cargados": 4,  // ✅ Incrementó de 3 a 4
  "monto_pagado": 6760,
  "estado": "finalizada",  // ✅ Cambió de "confirmada" a "finalizada"
  "datos_completos": true,  // ✅ Cambió de false a true
  "estado_display": "Finalizado"  // ✅ Cambió
}
```

**Transición:** `Confirmado Incompleto` → `Finalizado` 🎉

---

### Escenario 3: Aún quedan personas por asignar

**Estado inicial:**
```json
{
  "reserva_id": 172,
  "cantidad_pasajeros": 4,
  "pasajeros_cargados": 2,
  "monto_pagado": 880,
  "estado": "confirmada",
  "datos_completos": false,
  "estado_display": "Confirmado Incompleto"
}
```

**Pasajeros:**
```json
[
  {"id": 292, "persona": {"nombre": "Juan", "documento": "12345678"}},
  {"id": 293, "persona": {"nombre": "María", "documento": "87654321"}},
  {"id": 294, "persona": {"nombre": "Por Asignar 3", "documento": "12345678_PEND_3"}},
  {"id": 295, "persona": {"nombre": "Por Asignar 4", "documento": "12345678_PEND_4"}}
]
```

**Acción:**
```http
PATCH /api/reservas/pasajeros/294/
{
  "persona_id": 15
}
```

**Resultado:**
```json
{
  "reserva_id": 172,
  "cantidad_pasajeros": 4,
  "pasajeros_cargados": 3,  // ✅ Incrementó de 2 a 3
  "monto_pagado": 880,
  "estado": "confirmada",  // Sin cambio
  "datos_completos": false,  // ❌ Aún false (falta 1 más)
  "estado_display": "Confirmado Incompleto"  // Sin cambio
}
```

**Transición:** Sin cambio (aún falta 1 pasajero)

---

## API Endpoints

### Actualizar un Pasajero

**Endpoint:**
```http
PATCH /api/reservas/pasajeros/{pasajero_id}/
PUT /api/reservas/pasajeros/{pasajero_id}/
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {token}
```

**Body (PATCH - actualización parcial):**
```json
{
  "persona_id": 15
}
```

**Body (PUT - actualización completa):**
```json
{
  "persona_id": 15,
  "es_titular": false,
  "precio_asignado": 3536.00
}
```

**Respuesta:**
```json
{
  "id": 295,
  "persona": {
    "id": 15,
    "nombre": "Nombre Real",
    "apellido": "Apellido Real",
    "documento": "9876543",
    "email": "persona@email.com",
    "telefono": "0991234567"
  },
  "es_titular": false,
  "precio_asignado": 3536.00,
  "monto_pagado": 220.00,
  "saldo_pendiente": 3316.00,
  "porcentaje_pagado": 6.22,
  "seña_requerida": 220.00,
  "tiene_sena_pagada": true,
  "esta_totalmente_pagado": false
}
```

**Efectos secundarios:**
- Se ejecuta `perform_update()` en el `PasajeroViewSet`
- Se llama a `reserva.actualizar_estado()`
- Se recalcula `datos_completos`
- Se actualiza el `estado` de la reserva si corresponde

---

### Obtener Pasajeros de una Reserva

**Endpoint:**
```http
GET /api/reservas/{reserva_id}/detalle-pasajeros/
```

**Respuesta:**
```json
[
  {
    "id": 292,
    "persona": {
      "nombre": "Juan",
      "documento": "12345678"
    },
    "monto_pagado": 220.00,
    "saldo_pendiente": 3316.00
  },
  {
    "id": 295,
    "persona": {
      "nombre": "Por Asignar 4",
      "documento": "12345678_PEND_4"
    },
    "monto_pagado": 220.00,
    "saldo_pendiente": 3316.00
  }
]
```

---

### Obtener Estado de una Reserva

**Endpoint:**
```http
GET /api/reservas/{reserva_id}/
```

**Respuesta:**
```json
{
  "id": 172,
  "codigo": "RSV-2025-0172",
  "estado": "confirmada",
  "estado_display": "Confirmado Incompleto",
  "datos_completos": false,
  "cantidad_pasajeros": 4,
  "pasajeros_cargados": 3,
  "monto_pagado": 880.00,
  "seña_total": 880.00,
  "costo_total_estimado": 6760.00,
  "saldo_pendiente": 5880.00
}
```

---

## Ejemplos de Uso

### Ejemplo 1: Actualizar el último pasajero "Por Asignar"

**Contexto:**
- Reserva para 4 personas
- 3 pasajeros ya cargados
- 1 "Por Asignar 4" (id: 295)
- Seña pagada, falta pago total

**Pasos:**

1. **Crear la PersonaFisica (si no existe):**
```http
POST /api/personas/
{
  "nombre": "Ana",
  "apellido": "López",
  "documento": "55667788",
  "tipo_documento": 1,
  "email": "ana@email.com",
  "telefono": "0991234567",
  "nacionalidad": 1,
  "fecha_nacimiento": "1985-03-20",
  "sexo": "F"
}
```

**Respuesta:**
```json
{
  "id": 15,
  "nombre": "Ana",
  "documento": "55667788"
}
```

2. **Actualizar el pasajero "Por Asignar":**
```http
PATCH /api/reservas/pasajeros/295/
{
  "persona_id": 15
}
```

**Respuesta:**
```json
{
  "id": 295,
  "persona": {
    "id": 15,
    "nombre": "Ana",
    "apellido": "López",
    "documento": "55667788"
  },
  "por_asignar": false,  // ← Cambió automáticamente de true a false
  "monto_pagado": 220.00
}
```

3. **Verificar el estado de la reserva:**
```http
GET /api/reservas/172/
```

**Respuesta:**
```json
{
  "id": 172,
  "estado": "confirmada",
  "estado_display": "Confirmado Completo",
  "datos_completos": true,  // ✅ Cambió automáticamente
  "pasajeros_cargados": 4
}
```

---

### Ejemplo 2: Flujo completo con múltiples pasajeros

**Escenario:** Reserva para familia de 4, se van cargando uno por uno.

#### Paso 1: Crear reserva
```http
POST /api/reservas/
{
  "titular": 5,
  "paquete": 10,
  "salida": 20,
  "habitacion": 30,
  "cantidad_pasajeros": 4
}
```

**Estado:** `pendiente`, `datos_completos: false`, 0 pasajeros cargados

---

#### Paso 2: Registrar seña
```http
POST /api/reservas/172/registrar-senia/
{
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": "pendiente_1", "monto": 220},
    {"pasajero": "pendiente_2", "monto": 220},
    {"pasajero": "pendiente_3", "monto": 220},
    {"pasajero": "pendiente_4", "monto": 220}
  ]
}
```

**Estado:** `confirmada`, `datos_completos: false`, `estado_display: "Confirmado Incompleto"`

Se crean 4 pasajeros "Por Asignar" automáticamente.

---

#### Paso 3: Asignar primer pasajero (titular)
```http
PATCH /api/reservas/pasajeros/292/
{
  "persona_id": 5
}
```

**Estado:** `confirmada`, `datos_completos: false`, pasajeros_cargados: 1

---

#### Paso 4: Asignar segundo pasajero
```http
PATCH /api/reservas/pasajeros/293/
{
  "persona_id": 12
}
```

**Estado:** `confirmada`, `datos_completos: false`, pasajeros_cargados: 2

---

#### Paso 5: Asignar tercer pasajero
```http
PATCH /api/reservas/pasajeros/294/
{
  "persona_id": 13
}
```

**Estado:** `confirmada`, `datos_completos: false`, pasajeros_cargados: 3

---

#### Paso 6: Asignar último pasajero
```http
PATCH /api/reservas/pasajeros/295/
{
  "persona_id": 15
}
```

**Estado:** `confirmada`, `datos_completos: true`, `estado_display: "Confirmado Completo"`, pasajeros_cargados: 4 ✅

---

#### Paso 7: Registrar pago completo
```http
POST /api/reservas/172/registrar-pago/
{
  "tipo": "pago_total",
  "metodo_pago": "transferencia",
  "distribuciones": [
    {"pasajero": 292, "monto": 1470},
    {"pasajero": 293, "monto": 1470},
    {"pasajero": 294, "monto": 1470},
    {"pasajero": 295, "monto": 1470}
  ]
}
```

**Estado:** `finalizada`, `datos_completos: true`, `estado_display: "Finalizado"` 🎉

---

## Diagrama de Transiciones de Estados

```
                    ┌─────────────┐
                    │  PENDIENTE  │
                    └──────┬──────┘
                           │
                      Pagar seña
                           │
                           ▼
                    ┌─────────────────────────┐
                    │     CONFIRMADA          │
                    │                         │
                    │  ┌──────────────────┐   │
                    │  │ Incompleto       │   │ Asignar todos
                    │  │ datos_completos: │───┼──→ los pasajeros
                    │  │ false            │   │
                    │  └──────────────────┘   │
                    │           │              │
                    │           ▼              │
                    │  ┌──────────────────┐   │
                    │  │ Completo         │   │
                    │  │ datos_completos: │   │
                    │  │ true             │   │
                    │  └──────────────────┘   │
                    └────────────┬─────────────┘
                                 │
                        Pagar 100% + datos completos
                                 │
                                 ▼
                          ┌─────────────┐
                          │ FINALIZADA  │
                          └─────────────┘
```

---

## Consideraciones Importantes

### ⚠️ Actualización automática del estado

El método `perform_update()` del `PasajeroViewSet` se encarga de:
1. Guardar los cambios en el pasajero
2. Llamar a `reserva.actualizar_estado()` automáticamente
3. Recalcular `datos_completos`
4. Actualizar el `estado` de la reserva según corresponda

**No es necesario** llamar manualmente a `actualizar_estado()` después de actualizar un pasajero.

---

### ⚠️ Validación de pagos

Hay **dos caminos de validación** según si faltan datos de pasajeros:

1. **Faltan datos:** Validación a nivel de reserva total
2. **Datos completos:** Validación individual por pasajero

Esto permite flexibilidad en el orden de las operaciones (primero pagar, después cargar pasajeros, o viceversa).

---

### ⚠️ Pasajeros "Por Asignar"

- Se identifican por el patrón `_PEND` en el documento
- Se crean automáticamente cuando es necesario
- No cuentan para `pasajeros_cargados`
- Mantienen los pagos asignados al actualizarse

---

### ⚠️ Transición a "finalizada"

Para que una reserva pase a estado **FINALIZADA**, se deben cumplir **AMBAS** condiciones:
1. ✅ `esta_totalmente_pagada() == True` (100% pagado)
2. ✅ `datos_completos == True` (todos los pasajeros reales cargados)

Si solo se cumple una, la reserva permanece en **CONFIRMADA**.

---

## Resumen de Cambios Implementados

### Archivo: `GroupTours/apps/reserva/models.py`

**Cambio 1:** Agregado campo `por_asignar` al modelo `Pasajero`

**Líneas 489-492:**
```python
por_asignar = models.BooleanField(
    default=False,
    help_text="Indica si este pasajero está pendiente de asignación (True) o tiene datos reales (False)"
)
```

**Propósito:** Identificar de forma eficiente si un pasajero está pendiente de asignación sin necesidad de verificar el documento.

---

### Archivo: `GroupTours/apps/reserva/migrations/0014_pasajero_por_asignar.py`

**Cambio:** Migración automática generada para agregar el campo `por_asignar`

**Comando ejecutado:**
```bash
python manage.py makemigrations reserva
```

---

### Archivo: `GroupTours/apps/reserva/serializers.py`

**Cambio 1:** Agregado campo `persona_id` al `PasajeroSerializer`

**Líneas 42-48:**
```python
persona_id = serializers.PrimaryKeyRelatedField(
    queryset=PersonaFisica.objects.all(),
    source='persona',
    write_only=True,
    required=False,
    help_text="ID de la PersonaFisica para asignar/actualizar al pasajero"
)
```

**Propósito:** Permitir actualizar el campo `persona` de un pasajero mediante PATCH/PUT.

**Cambio 2:** Agregado campo `por_asignar` a la lista de fields del `PasajeroSerializer`

**Línea 91:**
```python
fields = [
    "id",
    "persona",
    "persona_id",
    "es_titular",
    "por_asignar",  # ← Nuevo campo
    "precio_asignado",
    # ...
]
```

**Propósito:** Incluir el campo `por_asignar` en las respuestas de la API.

---

### Archivo: `GroupTours/apps/reserva/views.py`

**Cambio 1:** Actualizada función `obtener_o_crear_pasajero_pendiente()`

**Línea 94:**
```python
pasajero_pendiente = Pasajero.objects.create(
    reserva=reserva,
    persona=persona_pendiente,
    es_titular=False,
    por_asignar=True,  # ← Marcar como pendiente de asignación
    precio_asignado=reserva.precio_unitario or 0
)
```

**Propósito:** Marcar automáticamente como `por_asignar=True` al crear pasajeros pendientes.

**Cambio 2:** Agregado método `perform_update()` al `PasajeroViewSet`

**Líneas 1361-1394:**
```python
def perform_update(self, serializer):
    """
    Después de actualizar un pasajero, recalcular el estado de la reserva.

    Además, si se está actualizando el campo persona_id (asignando una persona real),
    automáticamente cambia por_asignar de True a False.
    """
    # Verificar si se está actualizando la persona (asignando datos reales)
    persona_id = serializer.validated_data.get('persona')
    pasajero_actual = self.get_object()

    # Si se está cambiando la persona Y el pasajero estaba por_asignar
    if persona_id and pasajero_actual.por_asignar:
        # Verificar que no sea una persona "pendiente" (con _PEND en el documento)
        if not persona_id.documento or '_PEND' not in persona_id.documento:
            # Cambiar por_asignar a False porque ahora tiene datos reales
            serializer.validated_data['por_asignar'] = False

    # Guardar el pasajero actualizado
    pasajero = serializer.save()

    # Actualizar el estado de la reserva asociada
    if pasajero.reserva:
        pasajero.reserva.actualizar_estado()
```

**Propósito:**
1. Recalcular automáticamente el estado de la reserva después de actualizar un pasajero
2. Cambiar automáticamente `por_asignar` de `True` a `False` cuando se asigna una persona real

---

## Fecha de Última Actualización

**Fecha:** 30 de Octubre de 2025
**Versión:** 1.1
**Autor:** Sistema GroupTours

**Changelog v1.1:**
- ✅ Agregado campo `por_asignar` al modelo Pasajero
- ✅ Actualización automática de `por_asignar` al asignar persona real
- ✅ Mejora en identificación de pasajeros pendientes en API
