# Análisis: Sistema de Facturación Dual (Global vs Individual)

**Fecha:** 31 de Octubre, 2025
**Estado:** Análisis Completo - PENDIENTE DE IMPLEMENTACIÓN
**Versión:** 1.0

---

## 📋 Resumen Ejecutivo

Se propone implementar un sistema de facturación con **dos modalidades excluyentes**:

1. **Facturación Global**: Una sola factura por toda la reserva
2. **Facturación Individual**: Una factura por cada pasajero

La modalidad se define **al crear la reserva** y no puede cambiar después.

---

## 🎯 Requerimientos Confirmados

### **Requisito 1: Modalidades de Facturación**

- Una reserva puede facturarse de **DOS formas distintas**:
  - **Global/Total**: Una factura que incluye todos los pasajeros
  - **Individual/Por Pasajero**: Una factura separada por cada pasajero

### **Requisito 2: Decisión al Confirmar Reserva**

- La modalidad se **pregunta al CONFIRMAR la reserva** (cuando se paga la seña)
- Se almacena en `Reserva.modalidad_facturacion`
- Opciones: `'global'` o `'individual'`
- **Mientras está en estado 'pendiente'**: modalidad puede ser `NULL` (sin decidir)
- **Al pasar a 'confirmada'**: modalidad DEBE definirse y queda FIJA
- **No puede cambiar después de confirmada**

### **Requisito 3: Validaciones para Factura Individual**

Un pasajero SOLO puede facturarse si cumple TODAS estas condiciones:

1. ✅ Reserva en estado `'confirmada'` o `'finalizada'`
2. ✅ Pasajero tiene **saldo pendiente = 0** (`esta_totalmente_pagado == True`)
3. ✅ Pasajero tiene **datos reales** (`por_asignar == False`)
4. ✅ Pasajero NO tiene factura previa
5. ✅ Reserva NO tiene factura global emitida

### **Requisito 4: Validaciones para Factura Global**

Una reserva SOLO puede facturarse globalmente si:

1. ✅ Reserva configurada con `modalidad_facturacion == 'global'`
2. ✅ Reserva en estado `'finalizada'`
3. ✅ Reserva tiene **saldo pendiente = 0**
4. ✅ Reserva NO tiene factura global previa
5. ✅ Reserva NO tiene facturas individuales emitidas

### **Requisito 5: Exclusividad**

- **Modalidades son EXCLUYENTES**: Una reserva puede tener O factura global O facturas individuales, NUNCA ambas
- Si ya existe factura global → PROHIBIR facturas individuales
- Si ya existen facturas individuales → PROHIBIR factura global

---

## 🏗️ Cambios en la Base de Datos

### **1. Modelo Reserva (NUEVO CAMPO)**

```python
class Reserva(models.Model):
    # ... campos existentes ...

    # NUEVO CAMPO
    modalidad_facturacion = models.CharField(
        max_length=20,
        choices=[
            ('global', 'Facturación Global (Una factura total)'),
            ('individual', 'Facturación Individual (Por pasajero)'),
        ],
        null=True,
        blank=True,
        help_text="Modalidad de facturación elegida al confirmar la reserva. NULL mientras esté pendiente."
    )
```

**Migración necesaria:** Agregar este campo a la tabla `Reserva`

### **2. Modelo FacturaElectronica (CAMPOS NUEVOS)**

```python
class FacturaElectronica(models.Model):
    # ... campos existentes ...

    # NUEVO CAMPO: Tipo de facturación
    tipo_facturacion = models.CharField(
        max_length=20,
        choices=[
            ('total', 'Factura Total (Reserva Completa)'),
            ('por_pasajero', 'Factura por Pasajero Individual'),
        ],
        default='total',
        null=True,
        blank=True,
        help_text="Modalidad de facturación: total o por pasajero"
    )

    # NUEVO CAMPO: Relación con Pasajero
    pasajero = models.ForeignKey(
        'reserva.Pasajero',
        on_delete=models.PROTECT,
        related_name='facturas',
        null=True,
        blank=True,
        help_text="Pasajero específico (solo si tipo_facturacion='por_pasajero')"
    )
```

**Migración necesaria:** Agregar estos dos campos a la tabla `FacturaElectronica`

### **3. Modelo Pasajero (YA EXISTE - No requiere cambios)**

Campos relevantes que ya existen:
- `por_asignar` (Boolean): Indica si es pasajero temporal
- `precio_asignado` (Decimal): Precio asignado a este pasajero
- `monto_pagado` (Property): Total pagado por el pasajero
- `saldo_pendiente` (Property): Saldo que le falta pagar
- `esta_totalmente_pagado` (Property): True si saldo == 0

---

## 🔄 Flujos de Trabajo

### **Flujo 1: Facturación Global (Familia)**

```
┌─────────────────────────────────────┐
│ DÍA 1: CREACIÓN DE RESERVA          │
└─────────────────────────────────────┘

Cliente: Familia Pérez (4 personas)

Sistema crea Reserva:
  RSV-2025-0001
  ├─ modalidad_facturacion: NULL ⏳ (sin decidir aún)
  ├─ titular: Juan Pérez
  ├─ cantidad_pasajeros: 4
  ├─ precio_unitario: 750,000 Gs
  ├─ costo_total: 3,000,000 Gs
  ├─ monto_pagado: 0 Gs
  └─ estado: 'pendiente'

┌─────────────────────────────────────┐
│ DÍA 5: PAGO DE SEÑA (CONFIRMAR)     │
└─────────────────────────────────────┘

Cliente paga seña: 900,000 Gs (30%)

Agencia: "¿Cómo desea facturar cuando termine de pagar?"
         [✓] Global - Una factura total
         [ ] Individual - Una factura por persona

Cliente elige: GLOBAL ✓

Reserva actualizada:
  ├─ monto_pagado: 900,000 Gs ✓
  ├─ modalidad_facturacion: 'global' ✓ (FIJO, ya no cambia)
  └─ estado: 'confirmada' ✓

┌─────────────────────────────────────┐
│ DÍA 15: PAGO COMPLETO               │
└─────────────────────────────────────┘

Cliente paga saldo: 2,100,000 Gs

Reserva actualizada:
  ├─ monto_pagado: 3,000,000 Gs ✓
  ├─ saldo_pendiente: 0 Gs ✓
  └─ estado: 'finalizada' ✓

┌─────────────────────────────────────┐
│ DÍA 16: EMISIÓN DE FACTURA          │
└─────────────────────────────────────┘

POST /api/facturacion/generar-factura-total/1/

Sistema valida:
  ✓ modalidad_facturacion == 'global'
  ✓ estado == 'finalizada'
  ✓ saldo_pendiente == 0
  ✓ No tiene factura previa
  ✓ No tiene facturas individuales

Factura generada:
  Nº 001-001-0000001
  Tipo: 'total'
  Cliente: Juan Pérez (CI: 1234567)

  Detalles:
    Item 1: Paquete Turístico x 4 = 3,000,000 Gs

  Total IVA 10%: 272,727.27 Gs
  Total General: 3,000,000 Gs
```

---

### **Flujo 2: Facturación Individual (Grupo de Amigos)**

```
┌─────────────────────────────────────┐
│ DÍA 1: CREACIÓN DE RESERVA          │
└─────────────────────────────────────┘

Cliente: Grupo de 4 amigos

Sistema crea Reserva:
  RSV-2025-0002
  ├─ modalidad_facturacion: NULL ⏳ (sin decidir aún)
  ├─ titular: María García
  ├─ cantidad_pasajeros: 4
  └─ estado: 'pendiente'

┌─────────────────────────────────────┐
│ DÍA 3: PAGO DE SEÑA (CONFIRMAR)     │
└─────────────────────────────────────┘

María paga seña: 900,000 Gs (30% del total)

Agencia: "¿Cómo desea facturar?"
         [ ] Global - Una factura total
         [✓] Individual - Una factura por persona

Cliente elige: INDIVIDUAL ✓

Reserva actualizada:
  ├─ modalidad_facturacion: 'individual' ✓ (FIJO, ya no cambia)
  ├─ monto_pagado: 900,000 Gs ✓
  └─ estado: 'confirmada' ✓

Sistema crea Pasajeros:
  Pasajero 1:
    ├─ persona: María García (titular)
    ├─ por_asignar: False ✓
    ├─ precio_asignado: 750,000 Gs
    ├─ monto_pagado: 0 Gs
    └─ saldo_pendiente: 750,000 Gs

  Pasajero 2:
    ├─ persona: PENDIENTE_002 (temporal)
    ├─ por_asignar: True ⚠️
    ├─ precio_asignado: 750,000 Gs
    └─ monto_pagado: 0 Gs

  Pasajero 3:
    ├─ persona: PENDIENTE_003 (temporal)
    ├─ por_asignar: True ⚠️
    └─ ...

  Pasajero 4:
    ├─ persona: PENDIENTE_004 (temporal)
    ├─ por_asignar: True ⚠️
    └─ ...

┌─────────────────────────────────────┐
│ DÍA 5: PEDRO LÓPEZ PAGA             │
└─────────────────────────────────────┘

Paso 1: Asignar datos reales
  PUT /api/pasajeros/2/
  {
    "persona_id": 456,  // Pedro López
    "por_asignar": false
  }

  Pasajero 2 actualizado:
    ├─ persona: Pedro López (CI: 7654321) ✓
    ├─ por_asignar: False ✓
    └─ precio_asignado: 750,000 Gs

Paso 2: Registrar pago
  POST /api/comprobantes/
  {
    "reserva": 2,
    "monto": 750000,
    "distribuciones": [
      {"pasajero": 2, "monto": 750000}
    ]
  }

  Pasajero 2 actualizado:
    ├─ monto_pagado: 750,000 Gs ✓
    ├─ saldo_pendiente: 0 Gs ✓
    └─ esta_totalmente_pagado: True ✓

Paso 3: Emitir factura individual
  POST /api/facturacion/generar-factura-pasajero/2/

  Sistema valida:
    ✓ reserva.modalidad_facturacion == 'individual'
    ✓ reserva.estado in ['confirmada', 'finalizada']
    ✓ pasajero.por_asignar == False
    ✓ pasajero.esta_totalmente_pagado == True
    ✓ pasajero no tiene factura previa
    ✓ reserva no tiene factura global

  Factura generada:
    Nº 001-001-0000002
    Tipo: 'por_pasajero'
    Pasajero: Pasajero 2
    Cliente: Pedro López (CI: 7654321)

    Detalles:
      Item 1: Paquete Turístico x 1 = 750,000 Gs

    Total: 750,000 Gs

┌─────────────────────────────────────┐
│ DÍA 8: ANA MARTÍNEZ PAGA            │
└─────────────────────────────────────┘

[Mismo proceso que Pedro]

Factura generada:
  Nº 001-001-0000003

┌─────────────────────────────────────┐
│ DÍA 10: INTENTO PASAJERO TEMPORAL   │
└─────────────────────────────────────┘

POST /api/facturacion/generar-factura-pasajero/3/

❌ ERROR 400:
{
  "error": "Pasajero temporal no puede ser facturado",
  "detalle": "El pasajero #3 está marcado como 'por asignar'. No tiene datos reales de una persona física.",
  "pasajero": {
    "id": 3,
    "por_asignar": true,
    "persona": "PENDIENTE_003"
  },
  "solucion": "Asigne un pasajero real (nombre, CI, etc.) antes de intentar facturar"
}

┌─────────────────────────────────────┐
│ DÍA 12: CARLOS (Pasajero 4) PAGA   │
│         SOLO LA MITAD               │
└─────────────────────────────────────┘

Pasajero 4 asignado: Carlos Ruiz
  ├─ por_asignar: False ✓
  ├─ precio_asignado: 750,000 Gs
  ├─ monto_pagado: 400,000 Gs ⚠️
  └─ saldo_pendiente: 350,000 Gs ⚠️

POST /api/facturacion/generar-factura-pasajero/4/

❌ ERROR 400:
{
  "error": "Saldo pendiente",
  "detalle": "El pasajero Carlos Ruiz tiene saldo pendiente de 350,000 Gs. Debe pagar el total antes de facturar.",
  "pasajero": {
    "nombre": "Carlos Ruiz",
    "precio_asignado": "750000.00",
    "monto_pagado": "400000.00",
    "saldo_pendiente": "350000.00",
    "porcentaje_pagado": 53.33
  },
  "solucion": "Complete el pago de los 350,000 Gs restantes"
}
```

---

## 🚫 Casos de Error

### **Error 1: Intento de facturar sin definir modalidad**

```json
POST /api/facturacion/generar-factura-total/1/

❌ 400 Bad Request
{
  "error": "Modalidad de facturación no definida",
  "detalle": "La modalidad de facturación aún no ha sido elegida. Debe confirmar la reserva y seleccionar si desea facturación global o individual.",
  "reserva": {
    "codigo": "RSV-2025-0001",
    "estado": "pendiente",
    "modalidad_facturacion": null
  },
  "solucion": "Confirme la reserva (pague la seña) y seleccione la modalidad de facturación"
}
```

### **Error 2: Intento de factura global en reserva individual**

```json
POST /api/facturacion/generar-factura-total/2/

❌ 400 Bad Request
{
  "error": "Modalidad de facturación incorrecta",
  "detalle": "Esta reserva (RSV-2025-0002) está configurada para facturación INDIVIDUAL. No se puede emitir una factura global.",
  "reserva": {
    "codigo": "RSV-2025-0002",
    "modalidad_facturacion": "individual"
  },
  "solucion": "Use /generar-factura-pasajero/{pasajero_id}/ para cada pasajero"
}
```

### **Error 3: Intento de factura individual en reserva global**

```json
POST /api/facturacion/generar-factura-pasajero/1/

❌ 400 Bad Request
{
  "error": "Modalidad de facturación incorrecta",
  "detalle": "Esta reserva (RSV-2025-0001) está configurada para facturación GLOBAL. No se pueden emitir facturas individuales.",
  "reserva": {
    "codigo": "RSV-2025-0001",
    "modalidad_facturacion": "global"
  },
  "solucion": "Use /generar-factura-total/{reserva_id}/ para facturar toda la reserva"
}
```

### **Error 4: Ya existe factura global, solicitan individual**

```json
POST /api/facturacion/generar-factura-pasajero/1/

❌ 400 Bad Request
{
  "error": "Conflicto: Ya existe factura global",
  "detalle": "Ya se emitió una factura global para esta reserva. No se pueden emitir facturas individuales.",
  "factura_existente": {
    "numero": "001-001-0000001",
    "tipo": "total",
    "fecha": "2025-10-30",
    "monto": "3000000.00"
  },
  "nota": "Si se emitió por error, contacte al administrador para anularla"
}
```

### **Error 5: Pasajero temporal (por asignar)**

```json
POST /api/facturacion/generar-factura-pasajero/3/

❌ 400 Bad Request
{
  "error": "Pasajero temporal no puede ser facturado",
  "detalle": "El pasajero #3 está marcado como 'por asignar'. No tiene datos reales de una persona física.",
  "pasajero": {
    "id": 3,
    "por_asignar": true,
    "persona": "PENDIENTE_003",
    "monto_pagado": "0.00"
  },
  "solucion": "Asigne un pasajero real (nombre, CI) antes de facturar"
}
```

### **Error 6: Pasajero con saldo pendiente**

```json
POST /api/facturacion/generar-factura-pasajero/4/

❌ 400 Bad Request
{
  "error": "Saldo pendiente",
  "detalle": "El pasajero Carlos Ruiz tiene saldo pendiente de 350,000 Gs. Debe pagar el total antes de facturar.",
  "pasajero": {
    "id": 4,
    "nombre": "Carlos Ruiz",
    "precio_asignado": "750000.00",
    "monto_pagado": "400000.00",
    "saldo_pendiente": "350000.00",
    "porcentaje_pagado": 53.33
  },
  "solucion": "Complete el pago de los 350,000 Gs restantes"
}
```

---

## 🔐 Validaciones Completas

### **Validación para Factura Global**

```python
def validar_factura_global(reserva):
    """
    Validaciones exhaustivas para emitir factura global
    """
    # 1. Modalidad de facturación debe estar definida
    if reserva.modalidad_facturacion is None:
        raise ValidationError(
            "La modalidad de facturación no ha sido definida. "
            "Debe confirmar la reserva y elegir la modalidad primero."
        )

    # 2. Modalidad debe ser 'global'
    if reserva.modalidad_facturacion != 'global':
        raise ValidationError(
            "Esta reserva está configurada para facturación individual. "
            "No se puede emitir factura global."
        )

    # 3. Estado de reserva
    if reserva.estado != 'finalizada':
        raise ValidationError(
            "La reserva debe estar en estado 'finalizada' para emitir factura global."
        )

    # 4. Saldo de la reserva
    if reserva.saldo_pendiente > 0:
        raise ValidationError(
            f"La reserva tiene saldo pendiente de {reserva.saldo_pendiente}. "
            f"Debe pagar el total antes de facturar."
        )

    # 5. No tener factura global previa
    if reserva.facturas.filter(tipo_facturacion='total', activo=True).exists():
        raise ValidationError(
            "Ya existe una factura global para esta reserva."
        )

    # 6. No existir facturas individuales
    if reserva.facturas.filter(tipo_facturacion='por_pasajero', activo=True).exists():
        raise ValidationError(
            "Ya existen facturas individuales para esta reserva. "
            "No se puede emitir factura global."
        )
```

### **Validación para Factura Individual**

```python
def validar_factura_individual(pasajero):
    """
    Validaciones exhaustivas para emitir factura individual
    """
    reserva = pasajero.reserva

    # 1. Modalidad de facturación debe estar definida
    if reserva.modalidad_facturacion is None:
        raise ValidationError(
            "La modalidad de facturación no ha sido definida. "
            "Debe confirmar la reserva y elegir la modalidad primero."
        )

    # 2. Modalidad debe ser 'individual'
    if reserva.modalidad_facturacion != 'individual':
        raise ValidationError(
            "Esta reserva está configurada para facturación global. "
            "No se pueden emitir facturas individuales."
        )

    # 3. Estado de reserva
    if reserva.estado not in ['confirmada', 'finalizada']:
        raise ValidationError(
            f"La reserva debe estar confirmada o finalizada. "
            f"Estado actual: {reserva.estado}"
        )

    # 4. Pasajero con datos reales (NO temporal)
    if pasajero.por_asignar:
        raise ValidationError(
            "No se puede facturar. El pasajero está marcado como 'por asignar'. "
            "Debe asignar un pasajero real con datos completos antes de emitir la factura."
        )

    # 5. Saldo del pasajero
    if not pasajero.esta_totalmente_pagado:
        raise ValidationError(
            f"El pasajero {pasajero.persona.nombre} {pasajero.persona.apellido} "
            f"tiene saldo pendiente de {pasajero.saldo_pendiente}. "
            f"Debe pagar el total antes de facturar."
        )

    # 6. No tener factura individual previa
    if pasajero.facturas.filter(tipo_facturacion='por_pasajero', activo=True).exists():
        raise ValidationError(
            f"El pasajero ya tiene una factura individual generada."
        )

    # 7. No existir factura global
    if reserva.facturas.filter(tipo_facturacion='total', activo=True).exists():
        raise ValidationError(
            "Ya existe una factura global para esta reserva. "
            "No se pueden emitir facturas individuales."
        )
```

---

## 🛠️ Endpoints a Implementar

### **1. Generar Factura Global**

```
POST /api/facturacion/generar-factura-total/{reserva_id}/

Body (opcional):
{
  "subtipo_impuesto_id": 3
}

Response 201:
{
  "mensaje": "Factura global generada exitosamente",
  "factura": {
    "id": 1,
    "numero_factura": "001-001-0000001",
    "tipo_facturacion": "total",
    "reserva": 1,
    "pasajero": null,
    "cliente_nombre": "Juan Pérez",
    "total_general": "3000000.00",
    "detalles": [...]
  }
}

Errores:
- 400: Modalidad incorrecta
- 400: Estado inválido
- 400: Saldo pendiente
- 400: Ya tiene factura
- 404: Reserva no encontrada
```

### **2. Generar Factura Individual por Pasajero**

```
POST /api/facturacion/generar-factura-pasajero/{pasajero_id}/

Body (opcional):
{
  "subtipo_impuesto_id": 3
}

Response 201:
{
  "mensaje": "Factura individual generada exitosamente",
  "factura": {
    "id": 2,
    "numero_factura": "001-001-0000002",
    "tipo_facturacion": "por_pasajero",
    "reserva": 2,
    "pasajero": 2,
    "cliente_nombre": "Pedro López",
    "total_general": "750000.00",
    "detalles": [...]
  }
}

Errores:
- 400: Modalidad incorrecta
- 400: Pasajero temporal (por_asignar=True)
- 400: Saldo pendiente
- 400: Ya tiene factura
- 400: Existe factura global
- 404: Pasajero no encontrado
```

### **3. Generar Todas las Facturas de una Reserva (Batch)**

```
POST /api/facturacion/generar-todas-facturas-pasajeros/{reserva_id}/

Descripción:
  Genera facturas para TODOS los pasajeros que cumplan las condiciones:
  - por_asignar == False
  - esta_totalmente_pagado == True
  - No tienen factura previa

Response 201:
{
  "mensaje": "Se generaron 3 facturas exitosamente",
  "facturas_generadas": [
    {
      "pasajero_id": 1,
      "pasajero_nombre": "María García",
      "factura_numero": "001-001-0000002",
      "monto": "750000.00"
    },
    {
      "pasajero_id": 2,
      "pasajero_nombre": "Pedro López",
      "factura_numero": "001-001-0000003",
      "monto": "750000.00"
    },
    {
      "pasajero_id": 3,
      "pasajero_nombre": "Ana Martínez",
      "factura_numero": "001-001-0000004",
      "monto": "750000.00"
    }
  ],
  "pasajeros_omitidos": [
    {
      "pasajero_id": 4,
      "pasajero_nombre": "Carlos Ruiz",
      "razon": "Saldo pendiente: 350,000 Gs"
    }
  ]
}

Errores:
- 400: Modalidad incorrecta (no es 'individual')
- 404: Reserva no encontrada
```

### **4. Consultar Facturas de una Reserva**

```
GET /api/facturacion/facturas-reserva/{reserva_id}/

Response 200:
{
  "reserva": {
    "id": 2,
    "codigo": "RSV-2025-0002",
    "modalidad_facturacion": "individual"
  },
  "factura_total": null,
  "facturas_por_pasajero": [
    {
      "id": 2,
      "numero_factura": "001-001-0000002",
      "pasajero_id": 2,
      "pasajero_nombre": "Pedro López",
      "fecha_emision": "2025-10-31T10:30:00Z",
      "total_general": "750000.00"
    },
    {
      "id": 3,
      "numero_factura": "001-001-0000003",
      "pasajero_id": 3,
      "pasajero_nombre": "Ana Martínez",
      "fecha_emision": "2025-10-31T14:20:00Z",
      "total_general": "750000.00"
    }
  ],
  "resumen": {
    "total_facturas": 2,
    "monto_facturado": "1500000.00",
    "pasajeros_sin_facturar": 2
  }
}
```

### **5. Consultar Facturas de un Pasajero**

```
GET /api/facturacion/facturas-pasajero/{pasajero_id}/

Response 200:
{
  "pasajero": {
    "id": 2,
    "nombre": "Pedro López",
    "reserva_codigo": "RSV-2025-0002"
  },
  "facturas": [
    {
      "id": 2,
      "numero_factura": "001-001-0000002",
      "fecha_emision": "2025-10-31T10:30:00Z",
      "total_general": "750000.00",
      "activo": true
    }
  ]
}
```

---

## 📊 Matriz de Decisión

| Escenario | ¿Permitido? | Validaciones |
|-----------|-------------|--------------|
| Facturar total cuando modalidad=NULL | ❌ NO | Modalidad no definida |
| Facturar total en reserva 'global' y 'finalizada' con saldo=0 | ✅ SÍ | Todas OK |
| Facturar total en reserva 'individual' | ❌ NO | Modalidad incorrecta |
| Facturar total cuando ya existe factura total | ❌ NO | Duplicación |
| Facturar total cuando existen facturas individuales | ❌ NO | Conflicto |
| Facturar pasajero cuando modalidad=NULL | ❌ NO | Modalidad no definida |
| Facturar pasajero en reserva 'individual', pagado 100%, datos reales | ✅ SÍ | Todas OK |
| Facturar pasajero en reserva 'global' | ❌ NO | Modalidad incorrecta |
| Facturar pasajero con `por_asignar=True` | ❌ NO | Pasajero temporal |
| Facturar pasajero con saldo pendiente | ❌ NO | Falta pago |
| Facturar pasajero cuando ya existe factura global | ❌ NO | Conflicto |
| Facturar pasajero cuando ya tiene su factura | ❌ NO | Duplicación |

---

## 🔄 Integración con el Sistema de Reservas

### **Actualización del Método `actualizar_estado()` de Reserva**

El método `Reserva.actualizar_estado()` debe modificarse para incluir la lógica de selección de modalidad:

```python
def actualizar_estado(self, modalidad_facturacion=None):
    """
    Actualiza el estado de la reserva basado en pagos y datos de pasajeros.

    Args:
        modalidad_facturacion: 'global' o 'individual' (requerido al confirmar)
    """
    # Estado actual: pendiente
    if self.estado == 'pendiente':
        if self.puede_confirmarse():  # seña total pagada
            # Al confirmar, DEBE definir modalidad
            if modalidad_facturacion is None:
                raise ValidationError(
                    "Debe seleccionar la modalidad de facturación al confirmar la reserva. "
                    "Opciones: 'global' (una factura total) o 'individual' (factura por pasajero)"
                )

            if modalidad_facturacion not in ['global', 'individual']:
                raise ValidationError(
                    "Modalidad inválida. Use 'global' o 'individual'"
                )

            # Establecer modalidad (FIJO después de esto)
            self.modalidad_facturacion = modalidad_facturacion
            self.estado = 'confirmada'
            self.save()
            return

    # Estado actual: confirmada
    elif self.estado == 'confirmada':
        # NO permitir cambiar modalidad
        if modalidad_facturacion is not None and modalidad_facturacion != self.modalidad_facturacion:
            raise ValidationError(
                f"No se puede cambiar la modalidad de facturación. "
                f"Ya está definida como '{self.modalidad_facturacion}'"
            )

        # Continuar con lógica normal de transición a 'incompleta' o 'finalizada'
        # ... (código existente)
```

### **Endpoint para Confirmar Reserva**

```python
# En views.py de reserva
@api_view(['POST'])
def confirmar_reserva(request, reserva_id):
    """
    Confirma una reserva y establece la modalidad de facturación.

    POST /api/reservas/{id}/confirmar/
    Body: {
        "modalidad_facturacion": "global"  // o "individual"
    }
    """
    try:
        reserva = Reserva.objects.get(id=reserva_id, activo=True)

        if reserva.estado != 'pendiente':
            return Response({
                "error": "Solo se pueden confirmar reservas en estado 'pendiente'"
            }, status=400)

        if not reserva.puede_confirmarse():
            return Response({
                "error": "Seña insuficiente",
                "detalle": f"Debe pagar al menos {reserva.senia_total} Gs para confirmar",
                "pagado": str(reserva.monto_pagado),
                "falta": str(reserva.senia_total - reserva.monto_pagado)
            }, status=400)

        modalidad = request.data.get('modalidad_facturacion')
        if not modalidad:
            return Response({
                "error": "Modalidad requerida",
                "detalle": "Debe especificar 'modalidad_facturacion': 'global' o 'individual'"
            }, status=400)

        # Actualizar estado y modalidad
        reserva.actualizar_estado(modalidad_facturacion=modalidad)

        serializer = ReservaSerializer(reserva)
        return Response({
            "mensaje": "Reserva confirmada exitosamente",
            "reserva": serializer.data,
            "modalidad_seleccionada": modalidad
        }, status=200)

    except ValidationError as e:
        return Response({"error": str(e)}, status=400)
    except Reserva.DoesNotExist:
        return Response({"error": "Reserva no encontrada"}, status=404)
```

---

## 📝 Tareas de Implementación

### **Fase 1: Modelos (Base de Datos)**

- [ ] Agregar campo `modalidad_facturacion` a modelo `Reserva`
- [ ] Agregar campo `tipo_facturacion` a modelo `FacturaElectronica`
- [ ] Agregar campo `pasajero` (FK) a modelo `FacturaElectronica`
- [ ] Crear migraciones
- [ ] Ejecutar migraciones

### **Fase 2: Lógica de Negocio (models.py)**

- [ ] Crear función `validar_factura_global(reserva)`
- [ ] Crear función `validar_factura_individual(pasajero)`
- [ ] Modificar función `generar_factura_desde_reserva()` para soportar tipo_facturacion
- [ ] Crear función `generar_factura_pasajero(pasajero, subtipo_impuesto_id=None)`
- [ ] Crear función `generar_todas_facturas_pasajeros(reserva)`

### **Fase 3: Serializers**

- [ ] Actualizar `FacturaElectronicaSerializer` con campos nuevos
- [ ] Agregar campo `pasajero_nombre` como campo de lectura
- [ ] Agregar campo `tipo_facturacion_display` como campo de lectura

### **Fase 4: Views y Endpoints**

- [ ] Endpoint: `generar_factura_total(reserva_id)`
- [ ] Endpoint: `generar_factura_pasajero(pasajero_id)`
- [ ] Endpoint: `generar_todas_facturas_pasajeros(reserva_id)`
- [ ] Endpoint: `facturas_reserva(reserva_id)`
- [ ] Endpoint: `facturas_pasajero(pasajero_id)`
- [ ] Actualizar endpoint existente `obtener_factura_reserva()` para manejar ambos tipos

### **Fase 5: URLs**

- [ ] Agregar rutas para los nuevos endpoints
- [ ] Actualizar documentación de URLs

### **Fase 6: Admin**

- [ ] Actualizar `FacturaElectronicaAdmin` para mostrar nuevos campos
- [ ] Agregar filtros por `tipo_facturacion`
- [ ] Agregar filtro por `modalidad_facturacion` en ReservaAdmin

### **Fase 7: Documentación**

- [ ] Actualizar `DOCUMENTACION_FACTURACION.md` con nuevas modalidades
- [ ] Agregar diagramas de flujo actualizados
- [ ] Documentar todos los endpoints nuevos
- [ ] Agregar ejemplos de uso

### **Fase 8: Testing**

- [ ] Probar creación de reserva (modalidad=NULL)
- [ ] Probar confirmación con modalidad 'global'
- [ ] Probar confirmación con modalidad 'individual'
- [ ] Probar intento de facturación sin modalidad definida (debe fallar)
- [ ] Probar intento de cambiar modalidad después de confirmar (debe fallar)
- [ ] Probar facturación global exitosa
- [ ] Probar facturación individual exitosa
- [ ] Probar todos los casos de error
- [ ] Probar batch de facturas individuales
- [ ] Probar endpoint `/api/reservas/{id}/confirmar/`

---

## 🎯 Próximos Pasos al Continuar

Cuando vuelvas, estos son los pasos sugeridos:

1. **Revisar este documento completo**
2. **Confirmar que el diseño es correcto**
3. **Comenzar implementación en este orden:**
   - Fase 1: Cambios en modelos y migraciones
   - Fase 2: Funciones de validación y generación
   - Fase 3-4: Serializers y Views
   - Fase 5: URLs
   - Fase 6-7: Admin y documentación
   - Fase 8: Testing

---

## 📞 Decisiones Confirmadas

✅ **Decisión 1: Momento de Selección de Modalidad**
- Se eligió **Opción C**: Modalidad se define al CONFIRMAR la reserva (al pagar seña)
- Mientras está `pendiente`: `modalidad_facturacion = NULL`
- Al pasar a `confirmada`: se DEBE elegir y queda FIJA

✅ **Decisión 2: Requisito de Estado para Facturación Individual**
- NO es necesario que la reserva esté `finalizada`
- Sí es necesario que esté al menos `confirmada`
- Lo crítico es que el pasajero específico tenga saldo=0

## 📞 Preguntas Pendientes

Si hay algo que aclarar o modificar al continuar:

1. ¿Servicios adicionales deben facturarse en facturas individuales o solo en global?
2. ¿Necesitas funcionalidad de anulación de facturas?
3. ¿Hay algún caso especial que no se haya contemplado?

---

**Estado:** ✅ ANÁLISIS COMPLETO Y VALIDADO - LISTO PARA IMPLEMENTAR

**Última actualización:** 31 de Octubre, 2025
**Versión:** 2.0 (Actualizado con Opción C - Modalidad al Confirmar)
