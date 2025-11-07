# 🚨 Análisis: Problema de Refacturación con Notas de Crédito

> **Fecha:** 07/11/2025
> **Estado:** PENDIENTE DE IMPLEMENTACIÓN
> **Prioridad:** ALTA

---

## 📌 PROMPT PARA CONTINUAR EN PRÓXIMA SESIÓN

```
Lee el archivo GroupTours/docs/ANALISIS_PROBLEMA_REFACTURACION.md y continuemos con la implementación de la Opción 3
```

---

## 🎯 Resumen Ejecutivo

**PROBLEMA IDENTIFICADO:**
Cuando se genera una Nota de Crédito Total que anula completamente una factura global, el sistema impide generar una nueva factura para esa misma reserva, incluso cuando:
- La reserva sigue activa
- Los pagos están registrados
- El cliente necesita una factura válida

**CAUSA RAÍZ:**
La validación en `models.py:1139-1142` verifica si existe una factura global con `activo=True`, sin considerar si esa factura está totalmente anulada por notas de crédito.

**IMPACTO:**
- ❌ Reservas bloqueadas para refacturación
- ❌ Clientes sin factura válida después de correcciones
- ❌ Imposibilidad de corregir errores de facturación
- ❌ Problemas con cancelaciones y reactivaciones

---

## 🔍 Problema Técnico Detallado

### Código Problemático

**Archivo:** `GroupTours/apps/facturacion/models.py`
**Líneas:** 1139-1142

```python
# 5. No tener factura global previa
if reserva.facturas.filter(tipo_facturacion='total', activo=True).exists():
    raise ValidationError(
        "Ya existe una factura global para esta reserva."
    )
```

### ¿Por qué es un problema?

Esta validación solo verifica que `activo=True`, pero **NO verifica** si la factura está totalmente anulada por una Nota de Crédito.

**Resultado:**
```python
Factura:
  - activo: True  ✅ (pasa la validación)
  - total_general: 12.000.000
  - total_acreditado: 12.000.000  ← COMPLETAMENTE ANULADA
  - saldo_neto: 0  ← SIN VALOR

Validación actual: "Ya existe una factura global" ❌
Validación correcta debería ser: "No existe factura vigente" ✅
```

---

## 📋 Escenarios Problemáticos

### Escenario 1: Error en Facturación

```
PASO 1: Generar factura con datos incorrectos
├─ Factura: 001-001-0000456
├─ Cliente: Juan Pérez (INCORRECTO)
└─ Monto: PYG 12.000.000

PASO 2: Detectar error y anular factura
├─ Generar NC Total
├─ Motivo: "Error en facturación"
├─ NC: 001-001-0000078
└─ Factura saldo_neto = 0 ✅

PASO 3: Intentar generar factura correcta
├─ Cliente correcto: María González
└─ ❌ ERROR: "Ya existe una factura global para esta reserva"

RESULTADO:
✅ Reserva: ACTIVA y PAGADA
❌ Cliente: SIN FACTURA VÁLIDA
🔴 BLOQUEADO para refacturación
```

### Escenario 2: Cancelación y Reactivación

```
PASO 1: Factura generada normalmente
└─ Factura: 001-001-0000457 | PYG 15.000.000

PASO 2: Cliente cancela el viaje
├─ Generar NC Total
├─ Motivo: "Cancelación de reserva"
└─ Factura anulada ✅

PASO 3: Cliente se arrepiente y reactiva
├─ Realiza nuevo pago
├─ Reserva estado: 'finalizada'
└─ Necesita nueva factura

PASO 4: Intentar facturar
└─ ❌ ERROR: "Ya existe una factura global para esta reserva"

RESULTADO:
✅ Reserva: ACTIVA y PAGADA
✅ Pagos: Registrados correctamente
❌ Cliente: Sin comprobante fiscal
🔴 BLOQUEADO para refacturación
```

### Escenario 3: Ajuste de Precio

```
PASO 1: Factura con precio original
└─ Factura: PYG 10.000.000

PASO 2: Aplicar descuento promocional 20%
├─ Precio correcto: PYG 8.000.000
├─ Generar NC Total para anular
└─ Motivo: "Ajuste de precio"

PASO 3: Intentar facturar con precio correcto
└─ ❌ ERROR: "Ya existe una factura global para esta reserva"

RESULTADO:
Cliente debería tener factura por PYG 8.000.000
Pero el sistema no permite generarla
```

---

## 🔗 Relación entre Pagos y Facturas

### Arquitectura Actual

```
┌─────────────────────────────────────┐
│          RESERVA                    │
│  ┌─────────────────────────────┐   │
│  │ monto_pagado: 12.000.000    │   │  ← Pagos del cliente
│  │ costo_total: 12.000.000     │   │
│  │ estado: 'finalizada'        │   │
│  └─────────────────────────────┘   │
│                                     │
│  Relación: reserva.facturas         │
│           ↓                         │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│     FACTURA ELECTRÓNICA             │
│  ┌─────────────────────────────┐   │
│  │ numero: 001-001-0000456     │   │
│  │ total_general: 12.000.000   │   │  ← Documento tributario
│  │ activo: True                │   │
│  └─────────────────────────────┘   │
│                                     │
│  Relación: factura.notas_credito    │
│           ↓                         │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│    NOTA DE CRÉDITO                  │
│  ┌─────────────────────────────┐   │
│  │ tipo: 'total'               │   │
│  │ total_general: 12.000.000   │   │  ← Anula la factura
│  │ activo: True                │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘

RESULTADO:
┌─────────────────────────────────────┐
│  Factura (calculado dinámicamente)  │
│  ┌─────────────────────────────┐   │
│  │ total_general: 12.000.000   │   │
│  │ total_acreditado: 12.000.000│   │  ← @property
│  │ saldo_neto: 0               │   │  ← @property
│  │ esta_totalmente_acreditada  │   │  ← @property
│  │   → True                    │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Punto Clave

**Los pagos NO se afectan por las Notas de Crédito:**

```python
# Antes de NC
reserva.monto_pagado = 12.000.000  ✅
factura.saldo_neto = 12.000.000    ✅

# Después de NC Total
reserva.monto_pagado = 12.000.000  ✅ (SIN CAMBIOS)
factura.saldo_neto = 0             ❌ (ANULADA)

# El cliente PAGÓ pero no tiene FACTURA VÁLIDA
```

---

## ✅ Soluciones Propuestas

### Opción 1: Cambiar Validación Directa ⭐

**Complejidad:** Baja
**Mantenibilidad:** Media

```python
# models.py - línea 1139
# ANTES:
if reserva.facturas.filter(tipo_facturacion='total', activo=True).exists():
    raise ValidationError("Ya existe una factura global para esta reserva.")

# DESPUÉS:
# Buscar facturas globales que NO estén totalmente anuladas
facturas_globales_activas = reserva.facturas.filter(
    tipo_facturacion='total',
    activo=True
)

# Filtrar las que tienen saldo > 0
facturas_vigentes = [
    f for f in facturas_globales_activas
    if not f.esta_totalmente_acreditada
]

if facturas_vigentes:
    factura = facturas_vigentes[0]
    raise ValidationError(
        f"Ya existe una factura global vigente ({factura.numero_factura}) "
        f"con saldo de {factura.saldo_neto}. "
        f"Para generar una nueva factura, primero anule la existente con una Nota de Crédito Total."
    )
```

**Pros:**
- ✅ Solución directa
- ✅ No requiere cambios en otros lugares

**Contras:**
- ⚠️ Código menos reutilizable
- ⚠️ Lógica duplicada si se necesita en otros lugares

---

### Opción 2: Marcar Factura como Inactiva

**Complejidad:** Media
**Mantenibilidad:** Baja

```python
# En generar_nota_credito_total() - después de crear la NC
def generar_nota_credito_total(factura_id, motivo, observaciones=''):
    # ... código existente ...

    nota_credito = NotaCreditoElectronica.objects.create(...)

    # NUEVO: Marcar factura como inactiva
    factura.activo = False
    factura.save()

    return nota_credito
```

**Pros:**
- ✅ Validación existente funciona sin cambios
- ✅ Consultas más simples

**Contras:**
- ❌ Factura desaparece de consultas por defecto
- ❌ Pérdida de trazabilidad
- ❌ Confusión contable (documento válido pero marcado inactivo)
- ❌ Dificulta auditorías

---

### Opción 3: Métodos Helper en Modelo Reserva ⭐⭐⭐ (RECOMENDADA)

**Complejidad:** Media
**Mantenibilidad:** Alta
**Reutilizabilidad:** Alta

#### Implementación Completa

**Paso 1: Agregar métodos al modelo Reserva**

```python
# apps/reserva/models.py
# Agregar estos métodos a la clase Reserva

def tiene_factura_global_vigente(self):
    """
    Verifica si existe una factura global vigente (no anulada totalmente).

    Una factura se considera "vigente" si:
    - Está activa (activo=True)
    - Es de tipo 'total' (factura global)
    - NO está totalmente anulada por notas de crédito (saldo_neto > 0)

    Returns:
        bool: True si existe al menos una factura global vigente

    Ejemplo:
        >>> reserva = Reserva.objects.get(id=1)
        >>> reserva.tiene_factura_global_vigente()
        False  # Todas las facturas están anuladas o no existen
    """
    facturas_globales = self.facturas.filter(
        tipo_facturacion='total',
        activo=True
    )

    for factura in facturas_globales:
        if not factura.esta_totalmente_acreditada:
            return True

    return False

def obtener_factura_global_vigente(self):
    """
    Obtiene la factura global vigente (si existe).

    Returns:
        FacturaElectronica | None: La factura vigente o None si no existe

    Ejemplo:
        >>> reserva = Reserva.objects.get(id=1)
        >>> factura = reserva.obtener_factura_global_vigente()
        >>> if factura:
        ...     print(f"Factura vigente: {factura.numero_factura}")
    """
    facturas_globales = self.facturas.filter(
        tipo_facturacion='total',
        activo=True
    )

    for factura in facturas_globales:
        if not factura.esta_totalmente_acreditada:
            return factura

    return None

def obtener_facturas_globales_anuladas(self):
    """
    Obtiene todas las facturas globales que están totalmente anuladas.

    Útil para:
    - Historial de facturas anuladas
    - Auditorías
    - Reportes

    Returns:
        list[FacturaElectronica]: Lista de facturas anuladas
    """
    facturas_globales = self.facturas.filter(
        tipo_facturacion='total',
        activo=True
    )

    return [
        factura for factura in facturas_globales
        if factura.esta_totalmente_acreditada
    ]

def puede_generar_factura_global(self):
    """
    Verifica si se puede generar una nueva factura global.

    Considera:
    - Facturas vigentes existentes
    - Estado de la reserva
    - Modalidad de facturación

    Returns:
        tuple: (puede_generar: bool, mensaje: str)

    Ejemplo:
        >>> puede, mensaje = reserva.puede_generar_factura_global()
        >>> if not puede:
        ...     print(f"Error: {mensaje}")
    """
    if self.tiene_factura_global_vigente():
        factura = self.obtener_factura_global_vigente()
        return (
            False,
            f"Ya existe una factura global vigente ({factura.numero_factura}) "
            f"con saldo de {factura.saldo_neto}. "
            f"Anule la factura existente antes de generar una nueva."
        )

    return True, "OK"
```

**Paso 2: Actualizar validación en facturación**

```python
# apps/facturacion/models.py
# Línea 1139 - Reemplazar validación existente

def validar_factura_global(reserva):
    """
    Validaciones exhaustivas para emitir factura global.
    """
    # ... validaciones 1-4 (sin cambios) ...

    # 5. No tener factura global vigente (ACTUALIZADO)
    puede_facturar, mensaje = reserva.puede_generar_factura_global()
    if not puede_facturar:
        raise ValidationError(mensaje)

    # 6. No existir facturas individuales (sin cambios)
    if reserva.facturas.filter(tipo_facturacion='por_pasajero', activo=True).exists():
        raise ValidationError(
            "Ya existen facturas individuales para esta reserva. "
            "No se puede emitir factura global."
        )
```

**Paso 3: Agregar endpoint de consulta (opcional)**

```python
# apps/facturacion/views.py
# Agregar nuevo endpoint

@api_view(['GET'])
@permission_classes([AllowAny])
def estado_facturacion_reserva(request, reserva_id):
    """
    Consulta el estado de facturación de una reserva.

    GET /api/facturacion/estado-facturacion/{reserva_id}/

    Retorna:
    {
        "puede_generar_factura_global": true/false,
        "mensaje": "...",
        "factura_vigente": {...} o null,
        "facturas_anuladas": [...],
        "resumen": {
            "total_facturas_activas": 2,
            "total_facturas_anuladas": 1,
            "total_facturas_vigentes": 1
        }
    }
    """
    try:
        reserva = get_object_or_404(Reserva, id=reserva_id, activo=True)

        puede_facturar, mensaje = reserva.puede_generar_factura_global()
        factura_vigente = reserva.obtener_factura_global_vigente()
        facturas_anuladas = reserva.obtener_facturas_globales_anuladas()

        return Response({
            "puede_generar_factura_global": puede_facturar,
            "mensaje": mensaje,
            "factura_vigente": FacturaElectronicaSerializer(factura_vigente).data if factura_vigente else None,
            "facturas_anuladas": FacturaElectronicaSerializer(facturas_anuladas, many=True).data,
            "resumen": {
                "total_facturas_activas": reserva.facturas.filter(activo=True).count(),
                "total_facturas_anuladas": len(facturas_anuladas),
                "total_facturas_vigentes": 1 if factura_vigente else 0
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": f"Error al consultar estado: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**Paso 4: Agregar ruta (opcional)**

```python
# apps/facturacion/urls.py
# Agregar a urlpatterns

path('estado-facturacion/<int:reserva_id>/', estado_facturacion_reserva, name='estado-facturacion-reserva'),
```

#### Ventajas de Opción 3

✅ **Reutilizable:** Los métodos se pueden usar en múltiples lugares
✅ **Mantenible:** Lógica centralizada en un solo lugar
✅ **Legible:** Código autodocumentado y expresivo
✅ **Testeable:** Fácil de probar unitariamente
✅ **Escalable:** Fácil agregar más validaciones
✅ **Informativo:** Mensajes de error más detallados
✅ **Trazabilidad completa:** No se pierde historial

#### Casos de Uso Adicionales

```python
# En la UI - antes de mostrar botón "Generar Factura"
puede_facturar, mensaje = reserva.puede_generar_factura_global()
if not puede_facturar:
    # Mostrar mensaje al usuario
    # Deshabilitar botón
    pass

# En reportes - obtener solo facturas vigentes
for reserva in Reserva.objects.all():
    factura = reserva.obtener_factura_global_vigente()
    if factura:
        # Incluir en reporte de facturación
        pass

# En auditorías - revisar facturas anuladas
facturas_anuladas = reserva.obtener_facturas_globales_anuladas()
for factura in facturas_anuladas:
    # Revisar NC asociadas
    for nc in factura.notas_credito.filter(activo=True):
        print(f"NC {nc.numero_nota_credito}: {nc.motivo}")
```

---

## 🎯 Recomendación Final

### ⭐⭐⭐ Implementar Opción 3

**Razones:**

1. **Mantenibilidad:** La lógica está centralizada y es fácil de mantener
2. **Claridad:** El código es autoexplicativo
3. **Flexibilidad:** Los métodos se pueden reutilizar en reportes, UI, APIs
4. **Robustez:** Valida correctamente el estado real de las facturas
5. **Trazabilidad:** Mantiene todo el historial sin perder documentos
6. **Escalabilidad:** Fácil agregar nuevas validaciones o lógica de negocio

---

## 📝 Plan de Implementación

### Fase 1: Modelo Reserva (30 min)
- [ ] Agregar `tiene_factura_global_vigente()`
- [ ] Agregar `obtener_factura_global_vigente()`
- [ ] Agregar `obtener_facturas_globales_anuladas()`
- [ ] Agregar `puede_generar_factura_global()`

### Fase 2: Validación Facturación (15 min)
- [ ] Actualizar `validar_factura_global()` en `models.py:1139`
- [ ] Probar con casos de prueba

### Fase 3: Endpoint de Consulta (15 min) [OPCIONAL]
- [ ] Crear `estado_facturacion_reserva()` en `views.py`
- [ ] Agregar ruta en `urls.py`
- [ ] Probar endpoint

### Fase 4: Pruebas (30 min)
- [ ] Caso 1: Factura normal → NC Total → Nueva factura ✅
- [ ] Caso 2: Error en facturación → Corregir
- [ ] Caso 3: Cancelación → Reactivación → Facturar
- [ ] Caso 4: Ajuste de precio

### Fase 5: Documentación (15 min)
- [ ] Actualizar CHANGELOG.md
- [ ] Documentar nuevo comportamiento
- [ ] Actualizar diagramas de flujo si es necesario

**Tiempo total estimado:** 1.5 - 2 horas

---

## 🧪 Casos de Prueba

### Test 1: Refacturación después de NC Total

```python
# Preparación
reserva = Reserva.objects.get(id=1)
reserva.modalidad_facturacion = 'global'
reserva.condicion_pago = 'contado'
reserva.estado = 'finalizada'
reserva.save()

# Paso 1: Generar factura inicial
factura1 = generar_factura_global(reserva)
assert factura1.numero_factura == '001-001-0000456'
assert factura1.total_general == Decimal('12000000')

# Paso 2: Verificar que no se puede generar otra
assert reserva.tiene_factura_global_vigente() == True
puede, msg = reserva.puede_generar_factura_global()
assert puede == False
assert 'Ya existe una factura global vigente' in msg

# Paso 3: Anular con NC Total
nc = generar_nota_credito_total(
    factura_id=factura1.id,
    motivo='error_facturacion',
    observaciones='Error en cliente'
)
assert nc.tipo_nota == 'total'
assert factura1.esta_totalmente_acreditada == True
assert factura1.saldo_neto == Decimal('0')

# Paso 4: Verificar que AHORA SÍ se puede facturar
assert reserva.tiene_factura_global_vigente() == False
puede, msg = reserva.puede_generar_factura_global()
assert puede == True

# Paso 5: Generar nueva factura
factura2 = generar_factura_global(reserva)
assert factura2.numero_factura == '001-001-0000457'
assert factura2.id != factura1.id

# Paso 6: Verificar que ambas facturas existen
facturas_activas = reserva.facturas.filter(activo=True)
assert facturas_activas.count() == 2

# Paso 7: Verificar estado de cada una
assert factura1.esta_totalmente_acreditada == True  # Anulada
assert factura2.esta_totalmente_acreditada == False  # Vigente

# Paso 8: Verificar método helper
assert reserva.obtener_factura_global_vigente() == factura2
facturas_anuladas = reserva.obtener_facturas_globales_anuladas()
assert factura1 in facturas_anuladas
assert factura2 not in facturas_anuladas
```

### Test 2: Múltiples NC Parciales seguidas de NC Total

```python
# Escenario: Varios descuentos parciales, luego anulación total

# Paso 1: Factura inicial
factura = generar_factura_global(reserva)
assert factura.total_general == Decimal('10000000')
assert factura.saldo_neto == Decimal('10000000')

# Paso 2: NC Parcial 1 (descuento)
nc1 = generar_nota_credito_parcial(
    factura_id=factura.id,
    items_a_acreditar=[{
        'descripcion': 'Descuento promocional',
        'cantidad': 1,
        'precio_unitario': 2000000
    }],
    motivo='descuento'
)
assert factura.saldo_neto == Decimal('8000000')
assert reserva.tiene_factura_global_vigente() == True

# Paso 3: NC Parcial 2 (más descuento)
nc2 = generar_nota_credito_parcial(
    factura_id=factura.id,
    items_a_acreditar=[{
        'descripcion': 'Descuento adicional',
        'cantidad': 1,
        'precio_unitario': 3000000
    }],
    motivo='descuento'
)
assert factura.saldo_neto == Decimal('5000000')
assert reserva.tiene_factura_global_vigente() == True

# Paso 4: NC Total (anula el saldo restante)
nc3 = generar_nota_credito_total(
    factura_id=factura.id,
    motivo='cancelacion_reserva'
)
assert factura.saldo_neto == Decimal('0')
assert factura.total_acreditado == Decimal('10000000')
assert reserva.tiene_factura_global_vigente() == False

# Paso 5: Ahora puede generar nueva factura
puede, msg = reserva.puede_generar_factura_global()
assert puede == True
```

---

## 📊 Impacto de la Solución

### Antes (Con el Bug)

```
Reserva con factura anulada:
├─ puede_generar_factura_global() → False ❌
├─ Mensaje: "Ya existe una factura global"
└─ BLOQUEADO para refacturación

Resultado:
❌ Cliente sin factura válida
❌ Imposible corregir errores
❌ Reserva bloqueada
```

### Después (Con el Fix)

```
Reserva con factura anulada:
├─ tiene_factura_global_vigente() → False ✅
├─ puede_generar_factura_global() → True ✅
└─ PERMITIDO refacturar

Resultado:
✅ Cliente obtiene factura válida
✅ Errores se pueden corregir
✅ Sistema flexible y robusto
```

---

## 🔧 Archivos a Modificar

### Archivo 1: `apps/reserva/models.py`
**Línea:** Agregar después de la clase `Reserva`
**Acción:** Agregar 4 métodos helper
**Líneas aprox:** +80 líneas

### Archivo 2: `apps/facturacion/models.py`
**Línea:** 1139-1142
**Acción:** Reemplazar validación
**Líneas aprox:** -5, +3 líneas

### Archivo 3: `apps/facturacion/views.py` [OPCIONAL]
**Línea:** Al final del archivo
**Acción:** Agregar endpoint de consulta
**Líneas aprox:** +40 líneas

### Archivo 4: `apps/facturacion/urls.py` [OPCIONAL]
**Línea:** En urlpatterns
**Acción:** Agregar ruta
**Líneas aprox:** +1 línea

---

## 💬 Preguntas Frecuentes

### ¿Por qué no marcar la factura como `activo=False`?

Porque una factura anulada por NC **sigue siendo un documento tributario válido**. Marcarla como inactiva:
- ❌ Dificulta auditorías
- ❌ Oculta el documento del historial
- ❌ Puede causar problemas legales/contables

### ¿Qué pasa con los pagos cuando se anula una factura?

**Los pagos NO se afectan.** La NC solo anula el documento tributario, no los registros de pago en la reserva. Los pagos siguen en `reserva.monto_pagado`.

### ¿Se pueden tener múltiples facturas anuladas?

**Sí.** El sistema permite:
- Factura #1 → NC Total → Factura #2 → NC Total → Factura #3
- Todas las facturas anuladas quedan en el historial
- Solo la última factura sin anular está "vigente"

### ¿Esto afecta facturas individuales?

**No.** Esta solución solo afecta facturas globales (`tipo_facturacion='total'`). Las facturas individuales por pasajero tienen su propia lógica.

### ¿Debería el motivo de la NC afectar la reserva?

**Depende del caso de negocio.** Actualmente el motivo NO afecta el estado de la reserva. Pero podrías implementar:

```python
if motivo == 'cancelacion_reserva':
    reserva.estado = 'cancelada'
    reserva.save()
```

---

## 📚 Referencias

### Código Relacionado

- `models.py:359-413` - Propiedades de FacturaElectronica
  - `total_acreditado`
  - `saldo_neto`
  - `esta_totalmente_acreditada`
  - `puede_generar_nota_credito()`

- `models.py:1086-1149` - Funciones de validación
  - `validar_factura_global()`
  - `validar_factura_individual()`

- `models.py:2440-2528` - Generación de NC
  - `generar_nota_credito_total()`
  - `generar_nota_credito_parcial()`

### Documentación

- `docs/FLUJO_VISTAS_NOTAS_CREDITO.md` - Flujos de usuario
- `CLAUDE.md` - Arquitectura del proyecto

---

## ✅ Checklist de Implementación

```markdown
## Pre-implementación
- [ ] Backup de la base de datos
- [ ] Crear rama: `fix/refacturacion-con-nc`
- [ ] Leer este documento completo

## Implementación
- [ ] Agregar métodos en `apps/reserva/models.py`
- [ ] Actualizar validación en `apps/facturacion/models.py:1139`
- [ ] [OPCIONAL] Agregar endpoint de consulta
- [ ] [OPCIONAL] Agregar ruta en urls.py

## Pruebas
- [ ] Test: Factura → NC Total → Nueva factura
- [ ] Test: Error en facturación → Corrección
- [ ] Test: Cancelación → Reactivación
- [ ] Test: Múltiples NC parciales → NC Total
- [ ] Verificar que facturas individuales no se afecten

## Post-implementación
- [ ] Actualizar CHANGELOG.md
- [ ] Migrar base de datos si es necesario
- [ ] Probar en ambiente de staging
- [ ] Documentar en confluence/wiki
- [ ] Merge a develop/main
```

---

## 🎬 Próximos Pasos

Cuando vuelvas a Claude Code, usa este prompt:

```
Lee el archivo GroupTours/docs/ANALISIS_PROBLEMA_REFACTURACION.md y continuemos con la implementación de la Opción 3
```

Claude Code:
1. Leerá este documento
2. Entenderá el contexto completo
3. Te preguntará por qué fase empezar
4. Implementará la solución paso a paso

---

**Documento creado:** 07/11/2025
**Última actualización:** 07/11/2025
**Autor:** Análisis conjunto Usuario + Claude Code
**Versión:** 1.0
