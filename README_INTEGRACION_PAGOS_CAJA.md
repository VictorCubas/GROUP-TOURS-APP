# Integración Automática: Pagos → Movimientos de Caja

## 🎯 Objetivo

Automatizar el registro de movimientos de caja cuando se registran pagos (ComprobantePago), manteniendo la trazabilidad completa del flujo de dinero en las cajas.

---

## ✅ Estado: COMPLETADO

Todos los componentes han sido implementados y probados.

---

## 📦 Archivos Modificados/Creados

### Archivos de Código

1. **`GroupTours/apps/comprobante/models.py`** ✅
   - Modificado el método `save()` para generar MovimientoCaja automáticamente
   - Agregado `_obtener_apertura_activa_empleado()`
   - Agregado `_mapear_metodo_pago_a_concepto()`
   - Agregado `_generar_movimiento_caja()`
   - Modificado `anular()` para anular también el movimiento
   - Agregado `_anular_movimiento_caja()`

2. **`GroupTours/apps/arqueo_caja/models.py`** ✅
   - Mejorado `actualizar_saldo_caja()` para recalcular desde cero

3. **`GroupTours/apps/arqueo_caja/views.py`** ✅
   - Mejorado endpoint `tengo-caja-abierta` con información adicional de movimientos

### Scripts y Herramientas

4. **`GroupTours/migrar_comprobantes_a_movimientos.py`** ✅
   - Script para migrar ComprobantePago históricos a MovimientoCaja
   - Soporta modo `--dry-run` para verificar sin ejecutar
   - Soporta modo `--verbose` para logs detallados

5. **`GroupTours/apps/comprobante/tests_movimientos_caja.py`** ✅
   - Suite completa de tests unitarios
   - Cubre todos los casos de uso principales

### Documentación

6. **`INTEGRACION_PAGOS_MOVIMIENTOS_CAJA.md`** ✅
   - Documentación técnica completa
   - Conceptos, implementación, ejemplos

7. **`GUIA_FRONTEND_PAGOS_CAJA.md`** ✅
   - Guía de integración para el frontend
   - Endpoints, flujos, componentes recomendados

8. **`README_INTEGRACION_PAGOS_CAJA.md`** ✅ (Este archivo)
   - Instrucciones de uso y despliegue

---

## 🚀 Instrucciones de Despliegue

### Paso 1: Ejecutar Tests

```bash
cd GroupTours
python manage.py test apps.comprobante.tests_movimientos_caja
```

**Resultado esperado:** Todos los tests pasan ✅

### Paso 2: Verificar Migraciones

```bash
python manage.py makemigrations
```

**Resultado esperado:** "No changes detected" (no se necesitan migraciones adicionales)

### Paso 3: Migrar Datos Históricos (OPCIONAL)

Si tienes ComprobantePago existentes que quieres asociar con MovimientoCaja:

```bash
# Primero, ejecutar en modo dry-run para verificar
python migrar_comprobantes_a_movimientos.py --dry-run --verbose

# Si todo está OK, ejecutar la migración real
python migrar_comprobantes_a_movimientos.py --verbose
```

**Nota:** Solo migrará comprobantes que tenían una apertura activa en el momento del pago.

### Paso 4: Verificar Funcionamiento

1. Abrir una caja como empleado
2. Registrar un ComprobantePago
3. Verificar que se creó el MovimientoCaja correspondiente

```bash
# En Django shell
python manage.py shell

>>> from apps.comprobante.models import ComprobantePago
>>> from apps.arqueo_caja.models import MovimientoCaja
>>>
>>> # Obtener último comprobante
>>> comprobante = ComprobantePago.objects.last()
>>>
>>> # Verificar que tiene movimiento asociado
>>> MovimientoCaja.objects.filter(comprobante=comprobante).exists()
True
```

---

## 📊 Diagrama de Flujo

```
┌─────────────────────┐
│  Empleado registra  │
│  ComprobantePago    │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│ ¿Tiene caja abierta?│
└──────────┬──────────┘
           │
      ┌────┴────┐
      │         │
     SÍ        NO
      │         │
      v         v
┌─────────┐  ┌──────────────────┐
│ Crear   │  │ Solo registrar   │
│ Mov.Caja│  │ ComprobantePago  │
└─────────┘  └──────────────────┘
      │
      v
┌─────────────────────┐
│ Actualizar saldo    │
│ de la caja          │
└─────────────────────┘
```

---

## 🔑 Características Clave

### ✅ Generación Automática
- Los MovimientoCaja se crean automáticamente al registrar un ComprobantePago
- No requiere intervención manual del usuario

### ✅ Validación Estricta
- Solo se genera movimiento si el empleado tiene caja abierta
- La caja debe estar a nombre del mismo empleado

### ✅ Flexibilidad
- Si no hay caja abierta, el pago se registra igual (sin error)
- Permite operaciones normales incluso sin caja abierta

### ✅ Trazabilidad
- Relación bidireccional ComprobantePago ↔ MovimientoCaja
- Auditoría completa de todos los movimientos

### ✅ Integridad
- El saldo se recalcula desde cero considerando solo movimientos activos
- Las anulaciones no dejan saldos incorrectos

### ✅ Mapeo Automático
- Métodos de pago se mapean automáticamente a conceptos
- Efectivo → venta_efectivo
- Tarjetas → venta_tarjeta
- Transferencia → transferencia_recibida
- Etc.

---

## 📋 Casos de Uso

### Caso 1: Pago con Caja Abierta (Normal)

1. Empleado abre caja (monto_inicial: 500,000)
2. Empleado registra pago de 300,000 en efectivo
3. Sistema crea ComprobantePago
4. Sistema crea MovimientoCaja automáticamente
5. Saldo de caja se actualiza: 800,000

### Caso 2: Pago sin Caja Abierta (Flexible)

1. Empleado NO tiene caja abierta
2. Empleado registra pago de 300,000
3. Sistema crea ComprobantePago
4. Sistema NO crea MovimientoCaja (sin error)
5. Pago se registra normalmente en la reserva

### Caso 3: Anulación de Pago

1. Se anula un ComprobantePago existente
2. Sistema marca ComprobantePago como inactivo
3. Sistema marca MovimientoCaja asociado como inactivo
4. Saldo se recalcula automáticamente (excluyendo el movimiento anulado)

### Caso 4: Devolución

1. Empleado registra ComprobantePago tipo "devolucion"
2. Sistema crea MovimientoCaja tipo "egreso"
3. Saldo de caja disminuye

---

## 🧪 Tests Incluidos

### Tests Unitarios (15 tests)

1. ✅ Comprobante con caja abierta genera movimiento
2. ✅ Comprobante sin caja abierta NO genera movimiento
3. ✅ Comprobante con caja de otro empleado NO genera movimiento
4. ✅ Comprobante con tarjeta mapea concepto correcto
5. ✅ Comprobante con transferencia mapea concepto correcto
6. ✅ Devolución genera egreso
7. ✅ Anular comprobante anula movimiento
8. ✅ Múltiples pagos actualizan saldo correctamente
9. ✅ Anular uno de varios pagos recalcula correctamente
10. ✅ Referencia contiene número de comprobante
11. ✅ Descripción incluye información de reserva
12. ✅ Recálculo con movimientos mixtos
13. ✅ Recálculo ignora movimientos inactivos
14. ✅ Saldo con múltiples ingresos y egresos
15. ✅ Anulaciones múltiples

**Ejecutar tests:**
```bash
python manage.py test apps.comprobante.tests_movimientos_caja
```

---

## 📡 Endpoints API Mejorados

### GET /api/arqueo-caja/aperturas/tengo-caja-abierta/

**Nuevo en esta versión:**
- Agregado `saldo_actual`
- Agregado `total_ingresos`
- Agregado `total_egresos`
- Agregado `cantidad_movimientos`
- Agregado `notificacion` (mensaje informativo)

**Response con caja abierta:**
```json
{
  "tiene_caja_abierta": true,
  "apertura_id": 123,
  "codigo_apertura": "APR-2025-0001",
  "caja_id": 1,
  "caja_nombre": "Caja Principal",
  "saldo_actual": "1500000.00",
  "total_ingresos": "1200000.00",
  "total_egresos": "200000.00",
  "cantidad_movimientos": 15,
  "notificacion": "Caja activa con 15 movimiento(s) registrado(s)."
}
```

---

## 🛠️ Herramientas para Desarrolladores

### Script de Migración

```bash
# Ver qué se haría sin ejecutar
python migrar_comprobantes_a_movimientos.py --dry-run --verbose

# Ejecutar la migración
python migrar_comprobantes_a_movimientos.py --verbose

# Ejecutar silenciosamente
python migrar_comprobantes_a_movimientos.py
```

### Django Shell - Verificar Datos

```python
# Verificar comprobantes con movimientos
from apps.comprobante.models import ComprobantePago
from apps.arqueo_caja.models import MovimientoCaja

total_comprobantes = ComprobantePago.objects.filter(activo=True).count()
con_movimiento = MovimientoCaja.objects.filter(comprobante__isnull=False).count()

print(f"Total comprobantes: {total_comprobantes}")
print(f"Con movimiento: {con_movimiento}")
print(f"Sin movimiento: {total_comprobantes - con_movimiento}")
```

```python
# Ver último pago y su movimiento
ultimo_pago = ComprobantePago.objects.last()
movimiento = MovimientoCaja.objects.filter(comprobante=ultimo_pago).first()

print(f"Comprobante: {ultimo_pago.numero_comprobante}")
print(f"Monto: {ultimo_pago.monto}")
print(f"Empleado: {ultimo_pago.empleado}")

if movimiento:
    print(f"Movimiento: {movimiento.numero_movimiento}")
    print(f"Tipo: {movimiento.tipo_movimiento}")
    print(f"Concepto: {movimiento.concepto}")
else:
    print("Sin movimiento de caja")
```

---

## ⚠️ Consideraciones Importantes

### 1. Migraciones de Datos Históricos

- Solo se migrarán comprobantes que tenían una apertura activa en su fecha
- Los comprobantes sin apertura quedarán sin MovimientoCaja asociado
- Esto es NORMAL y esperado (algunos pagos se registraron sin caja abierta)

### 2. Saldos de Caja

- Los saldos se recalculan SIEMPRE desde cero
- Esto garantiza precisión incluso con anulaciones
- El recálculo puede tardar unos milisegundos en cajas con muchos movimientos

### 3. Rendimiento

- El recálculo de saldo usa agregaciones SQL (eficiente)
- No hay impacto notable en el rendimiento
- Para cajas con +1000 movimientos, considerar indexación adicional

### 4. Consistencia

- La relación ComprobantePago → MovimientoCaja es opcional
- Es VÁLIDO tener comprobantes sin movimiento
- Es INVÁLIDO tener movimientos sin comprobante (si el movimiento fue generado automáticamente)

---

## 🔄 Flujo de Trabajo Recomendado

### Para Empleados

1. Abrir caja al inicio del turno
2. Registrar pagos normalmente
3. Verificar movimientos al cierre de caja
4. Realizar arqueo y cerrar caja

### Para Administradores

1. Monitorear cajas abiertas
2. Revisar reportes de movimientos
3. Validar cierres de caja
4. Auditar diferencias (si existen)

---

## 📚 Documentación Relacionada

1. **INTEGRACION_PAGOS_MOVIMIENTOS_CAJA.md**
   - Documentación técnica completa
   - Detalles de implementación
   - Casos de uso técnicos

2. **GUIA_FRONTEND_PAGOS_CAJA.md**
   - Guía para desarrolladores frontend
   - Endpoints disponibles
   - Componentes React recomendados

3. **GroupTours/docs/ARQUEO_DE_CAJA.md**
   - Documentación del módulo de arqueo de caja
   - Conceptos y funcionalidades

---

## 🐛 Troubleshooting

### Problema: No se generan movimientos de caja

**Causa posible:**
- El empleado no tiene caja abierta

**Verificación:**
```python
from apps.arqueo_caja.models import AperturaCaja
apertura = AperturaCaja.objects.filter(
    responsable=empleado,
    esta_abierta=True,
    activo=True
).first()

if not apertura:
    print("El empleado no tiene caja abierta")
```

**Solución:** Abrir caja primero

---

### Problema: Saldo de caja incorrecto

**Causa posible:**
- Error en el recálculo

**Verificación:**
```python
from decimal import Decimal
from django.db.models import Sum
from apps.arqueo_caja.models import MovimientoCaja

apertura_id = 123  # ID de la apertura

movimientos = MovimientoCaja.objects.filter(
    apertura_caja_id=apertura_id,
    activo=True
)

ingresos = movimientos.filter(tipo_movimiento='ingreso').aggregate(Sum('monto'))['monto__sum'] or Decimal('0')
egresos = movimientos.filter(tipo_movimiento='egreso').aggregate(Sum('monto'))['monto__sum'] or Decimal('0')

monto_inicial = Decimal('500000')  # Obtener de la apertura
saldo_calculado = monto_inicial + ingresos - egresos

print(f"Saldo calculado: {saldo_calculado}")
```

**Solución:**
```python
# Forzar recálculo
ultimo_movimiento = movimientos.last()
if ultimo_movimiento:
    ultimo_movimiento.actualizar_saldo_caja()
```

---

### Problema: Tests fallan

**Causa posible:**
- Datos de prueba incompletos
- Migraciones pendientes

**Solución:**
```bash
# Resetear base de datos de tests
python manage.py test apps.comprobante.tests_movimientos_caja --keepdb=false

# Verificar migraciones
python manage.py showmigrations
```

---

## 📞 Soporte

Para reportar bugs o solicitar mejoras:
1. Revisar esta documentación
2. Verificar los logs de Django
3. Ejecutar tests para reproducir el problema
4. Contactar al equipo de desarrollo

---

## 📝 Changelog

### Versión 1.0 (2025-11-16)

**Agregado:**
- Generación automática de MovimientoCaja al crear ComprobantePago
- Método `_obtener_apertura_activa_empleado()`
- Método `_mapear_metodo_pago_a_concepto()`
- Método `_generar_movimiento_caja()`
- Método `_anular_movimiento_caja()`
- Script de migración de datos históricos
- Suite completa de tests unitarios
- Endpoint mejorado `tengo-caja-abierta`
- Documentación completa (técnica y frontend)

**Modificado:**
- Método `ComprobantePago.save()` para generar movimientos
- Método `ComprobantePago.anular()` para anular movimientos
- Método `MovimientoCaja.actualizar_saldo_caja()` para recalcular desde cero

---

## ✅ Checklist de Verificación

Antes de considerar la implementación completa, verificar:

- [x] Código implementado en `comprobante/models.py`
- [x] Código implementado en `arqueo_caja/models.py`
- [x] Endpoint mejorado en `arqueo_caja/views.py`
- [x] Tests unitarios creados y pasando
- [x] Script de migración creado
- [x] Documentación técnica completa
- [x] Guía de frontend completa
- [x] README de instrucciones creado
- [x] Verificación manual realizada
- [ ] Migración de datos históricos ejecutada (si aplica)
- [ ] Frontend integrado (pendiente)
- [ ] Testing en producción (pendiente)

---

## 🎉 Conclusión

La integración entre pagos y movimientos de caja está **100% funcional** y lista para usar.

El sistema es:
- ✅ Automático
- ✅ Flexible
- ✅ Seguro
- ✅ Auditable
- ✅ Fácil de usar

**Próximos pasos:**
1. Integrar en el frontend
2. Ejecutar migración de datos históricos (si se desea)
3. Capacitar a los usuarios
4. Monitorear en producción
