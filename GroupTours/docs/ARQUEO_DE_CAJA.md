# ARQUEO DE CAJA - Conceptos Fundamentales

## Índice
1. [Introducción](#introducción)
2. [Apertura de Caja](#apertura-de-caja)
3. [Movimientos de Caja](#movimientos-de-caja)
4. [Arqueo de Caja](#arqueo-de-caja)
5. [Cierre de Caja](#cierre-de-caja)
6. [Flujo Completo](#flujo-completo)
7. [Casos de Uso](#casos-de-uso)

---

## Introducción

El **arqueo de caja** es un proceso fundamental en la gestión financiera que permite controlar y verificar el efectivo y otros medios de pago manejados en un punto de venta o caja registradora.

### Objetivos principales:
- Garantizar la **transparencia** en el manejo del efectivo
- Detectar **diferencias** (faltantes o sobrantes)
- Generar **reportes** de movimientos diarios
- Establecer **responsabilidades** por turno/cajero
- Facilitar la **conciliación contable**

---

## Apertura de Caja

### ¿Qué es?
La **apertura de caja** es el proceso inicial que marca el inicio de operaciones de una caja en un turno o día específico. Sin una caja abierta, no se pueden realizar transacciones.

### Información requerida:
- **Fecha y hora de apertura**: Marca el inicio del turno
- **Monto inicial**: Efectivo con el que se inicia (fondo de cambio)
- **Responsable**: Usuario/cajero asignado a la caja
- **Punto de venta**: Ubicación física o identificador de la caja
- **Observaciones**: Notas adicionales (opcional)

### Estados de una caja:
- **ABIERTA**: Caja operativa, puede recibir transacciones
- **CERRADA**: Caja finalizada, no permite más operaciones

### Ejemplo práctico:
```
Cajero: Juan Pérez
Fecha apertura: 12/11/2025 - 08:00 AM
Monto inicial: $500.000
Punto de venta: Caja Principal
Estado: ABIERTA
```

### Reglas de negocio:
- ✅ Solo puede haber **una caja abierta** por punto de venta al mismo tiempo
- ✅ El monto inicial debe ser **mayor a 0**
- ✅ El responsable debe estar **autenticado** en el sistema
- ❌ No se puede abrir una caja si ya existe una abierta para ese punto de venta

---

## Movimientos de Caja

### ¿Qué son?
Los **movimientos de caja** son todas las transacciones que afectan el saldo durante el turno. Se clasifican en **ingresos** y **egresos**.

### Tipos de Movimientos

#### 1. INGRESOS (Aumentan el saldo)

##### a) Ventas
- **Venta en efectivo**: Pago inmediato en dinero físico
- **Venta con tarjeta**: Débito/crédito (puede ir a una cuenta bancaria)
- **Venta mixta**: Combinación de efectivo + tarjeta

##### b) Cobros
- **Cobro de cuentas por cobrar**: Recuperación de deudas de clientes
- **Cobro de servicios**: Pagos por servicios prestados

##### c) Otros ingresos
- **Depósitos**: Aportes adicionales de efectivo
- **Transferencias recibidas**: Ingresos por transferencia bancaria
- **Ajustes positivos**: Correcciones que aumentan el saldo

#### 2. EGRESOS (Disminuyen el saldo)

##### a) Pagos
- **Pago a proveedores**: Liquidación de facturas de compras
- **Pago de servicios**: Gastos operativos (luz, agua, etc.)

##### b) Gastos
- **Gastos operativos**: Viáticos, transporte, etc.
- **Compras menores**: Insumos, materiales

##### c) Otros egresos
- **Retiros de efectivo**: Extracción de dinero de la caja
- **Devoluciones**: Reintegros a clientes
- **Ajustes negativos**: Correcciones que disminuyen el saldo

### Estructura de un movimiento:
```
Tipo: INGRESO / EGRESO
Concepto: Venta de servicios / Pago a proveedor / etc.
Monto: $150.000
Método de pago: EFECTIVO / TARJETA / TRANSFERENCIA
Referencia: Factura N° 001-001-0000123
Fecha y hora: 12/11/2025 - 10:30 AM
Observaciones: Venta de tour a Iguazú
```

---

## Arqueo de Caja

### ¿Qué es?
El **arqueo de caja** es el proceso de **verificación física** del efectivo y otros valores presentes en la caja, comparándolo con lo que el sistema indica que debería haber (saldo teórico).

### ¿Cuándo se realiza?
- Al **cierre del turno** (obligatorio)
- Durante el día (arqueos intermedios - opcional)
- Cuando hay **cambio de cajero**
- Por **auditoría** o supervisión

### Proceso de arqueo:

#### 1. Cálculo del Saldo Teórico
```
Saldo Teórico = Monto Inicial + Total Ingresos - Total Egresos
```

**Ejemplo:**
```
Monto inicial:     $500.000
+ Ingresos:        $2.300.000
- Egresos:         $800.000
---------------------------
Saldo Teórico:     $2.000.000
```

#### 2. Conteo Físico (Saldo Real)
El cajero cuenta manualmente:
- Billetes por denominación
- Monedas
- Cheques (si aplica)
- Vales o documentos

**Ejemplo de conteo:**
```
20 billetes de $100.000 = $2.000.000
10 billetes de $50.000  = $500.000
15 billetes de $20.000  = $300.000
Monedas varias          = $8.500
---------------------------
Saldo Real Total:         $2.808.500
```

#### 3. Comparación y Diferencias
```
Diferencia = Saldo Real - Saldo Teórico
```

**Casos posibles:**
- **Diferencia = 0**: ✅ Cuadra perfectamente
- **Diferencia > 0**: 💰 Sobrante (hay más dinero del esperado)
- **Diferencia < 0**: ⚠️ Faltante (hay menos dinero del esperado)

#### 4. Registro de diferencias
```
Saldo Teórico:  $2.000.000
Saldo Real:     $2.008.500
---------------------------
Diferencia:     +$8.500 (SOBRANTE)

Observación: "Cliente pagó $100.000 por un servicio de $91.500
             y no esperó el vuelto"
```

### Información del arqueo:
- Fecha y hora del arqueo
- Usuario que realiza el arqueo
- Detalle del conteo físico por denominación
- Saldo teórico vs. saldo real
- Diferencia (sobrante/faltante)
- Justificación u observaciones
- Autorización (si la diferencia supera un umbral)

---

## Cierre de Caja

### ¿Qué es?
El **cierre de caja** es el proceso final que **finaliza las operaciones** del turno y congela todos los registros. Una vez cerrada, la caja no permite más transacciones.

### Proceso de cierre:

#### 1. Pre-cierre
- Verificar que no haya transacciones pendientes
- Revisar que todos los documentos estén registrados

#### 2. Arqueo final
- Realizar el conteo físico obligatorio
- Registrar diferencias si las hay
- Documentar observaciones

#### 3. Cierre definitivo
- Cambiar estado de la caja: **ABIERTA** → **CERRADA**
- Registrar fecha y hora de cierre
- Generar usuario que cierra

#### 4. Resumen del cierre
```
═══════════════════════════════════════════════
            RESUMEN DE CIERRE DE CAJA
═══════════════════════════════════════════════

Punto de venta:     Caja Principal
Responsable:        Juan Pérez
Fecha apertura:     12/11/2025 - 08:00 AM
Fecha cierre:       12/11/2025 - 18:00 PM
Duración turno:     10 horas

───────────────────────────────────────────────
MOVIMIENTOS DEL TURNO
───────────────────────────────────────────────
Monto inicial:              $500.000

INGRESOS:
  Ventas efectivo:          $1.500.000
  Ventas tarjeta:           $600.000
  Cobros cuentas:           $200.000
  ─────────────────────────────────
  Total ingresos:           $2.300.000

EGRESOS:
  Pagos proveedores:        $500.000
  Gastos operativos:        $200.000
  Retiros:                  $100.000
  ─────────────────────────────────
  Total egresos:            $800.000

───────────────────────────────────────────────
ARQUEO FINAL
───────────────────────────────────────────────
Saldo teórico:              $2.000.000
Saldo real contado:         $2.008.500
  ─────────────────────────────────
Diferencia:                 +$8.500 (SOBRANTE)

Observación: Cliente no esperó vuelto

───────────────────────────────────────────────
ESTADO: CERRADA ✓
═══════════════════════════════════════════════
```

### Reglas de negocio del cierre:
- ✅ Solo se puede cerrar una caja **ABIERTA**
- ✅ Debe realizarse **arqueo obligatorio** antes del cierre
- ✅ Si hay diferencia mayor al umbral, requiere **autorización de supervisor**
- ❌ Una vez cerrada, **no se puede reabrir** la misma caja
- ❌ No se pueden agregar o modificar movimientos después del cierre

---

## Flujo Completo

### Diagrama de estados:
```
┌─────────────┐
│   INICIO    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ APERTURA CAJA   │ ◄── Registrar monto inicial
│ Estado: ABIERTA │     Asignar responsable
└────────┬────────┘
         │
         │ ┌──────────────────────────┐
         ├─┤ REGISTRAR MOVIMIENTOS    │
         │ │ - Ventas                 │
         │ │ - Cobros                 │
         │ │ - Pagos                  │
         │ │ - Gastos                 │
         │ └──────────────────────────┘
         │          │
         │          │ (Se repite durante el turno)
         │          │
         ▼          ▼
┌─────────────────────────┐
│ ARQUEO DE CAJA          │
│ - Contar efectivo real  │
│ - Comparar con teórico  │
│ - Registrar diferencias │
└───────────┬─────────────┘
            │
            ▼
      ¿Diferencia?
       /        \
      SÍ         NO
     /            \
    ▼              ▼
┌─────────┐   ┌─────────┐
│Registrar│   │Continuar│
│Justif.  │   │         │
└────┬────┘   └────┬────┘
     │             │
     └──────┬──────┘
            │
            ▼
┌─────────────────┐
│  CIERRE CAJA    │
│ Estado: CERRADA │
│ - Generar       │
│   reporte final │
└─────────────────┘
```

### Secuencia temporal:
```
08:00 AM  │ ✓ Apertura de caja: $500.000
          │
10:30 AM  │ + Venta en efectivo: $150.000
11:45 AM  │ + Venta con tarjeta: $200.000
12:30 PM  │ - Pago proveedor: $300.000
14:00 PM  │ + Cobro cuenta: $100.000
15:30 PM  │ + Venta efectivo: $180.000
16:00 PM  │ - Gasto operativo: $50.000
          │
18:00 PM  │ ⚡ Arqueo de caja
          │   Teórico: $780.000
          │   Real: $780.000
          │   Diferencia: $0 ✓
          │
18:00 PM  │ ✓ Cierre de caja
```

---

## Casos de Uso

### Caso 1: Turno sin diferencias (Ideal)
```
Apertura:      $300.000
Ventas:        +$1.200.000
Gastos:        -$150.000
Teórico:       $1.350.000
Real:          $1.350.000
Diferencia:    $0 ✓
Acción:        Cierre exitoso
```

### Caso 2: Sobrante menor
```
Apertura:      $300.000
Ventas:        +$1.200.000
Gastos:        -$150.000
Teórico:       $1.350.000
Real:          $1.355.000
Diferencia:    +$5.000 (0.37%)
Observación:   "Propinas no registradas"
Acción:        Registrar y cerrar
```

### Caso 3: Faltante significativo
```
Apertura:      $300.000
Ventas:        +$1.200.000
Gastos:        -$150.000
Teórico:       $1.350.000
Real:          $1.300.000
Diferencia:    -$50.000 (3.7%) ⚠️
Observación:   "Se registró mal una venta"
Acción:        Requiere autorización de supervisor
               + Investigación interna
```

### Caso 4: Cambio de cajero
```
08:00 AM - Apertura Turno Mañana
  └─ Cajero: María López
  └─ Monto inicial: $500.000

14:00 PM - Arqueo intermedio
  └─ Teórico: $1.200.000
  └─ Real: $1.200.000 ✓
  └─ Cierre turno mañana

14:05 PM - Apertura Turno Tarde
  └─ Cajero: Carlos Gómez
  └─ Monto inicial: $1.200.000 (saldo anterior)

20:00 PM - Cierre turno tarde
```

### Caso 5: Múltiples métodos de pago
```
Venta total: $500.000
  - Efectivo:      $200.000 → Va a caja física
  - Tarjeta:       $250.000 → Va a cuenta bancaria
  - Transferencia: $50.000  → Va a cuenta bancaria

Arqueo efectivo:
  Teórico: $200.000
  Real: $200.000 ✓
```

---

## Consideraciones Técnicas

### Integridad de datos:
- Todos los movimientos deben estar **asociados a una caja abierta**
- No permitir eliminar movimientos una vez registrados (solo anular)
- Mantener **auditoría completa** (quién, cuándo, qué)

### Seguridad:
- Permisos diferenciados: abrir caja, registrar movimientos, cerrar caja
- Autorización de supervisor para diferencias grandes
- Logs de todas las operaciones

### Reportes generados:
- Resumen de cierre de caja
- Detalle de movimientos por tipo
- Comparativo de cajas por período
- Ranking de diferencias por cajero
- Movimientos por método de pago

---

## Glosario

- **Fondo de cambio**: Monto inicial para dar vuelto
- **Saldo teórico**: Lo que el sistema dice que debería haber
- **Saldo real**: Lo que físicamente se cuenta
- **Sobrante**: Diferencia positiva (hay más dinero)
- **Faltante**: Diferencia negativa (hay menos dinero)
- **Turno**: Período de operación de una caja
- **Punto de venta**: Ubicación física de la caja
- **Arqueo intermedio**: Conteo durante el turno (no cierra la caja)
- **Arqueo final**: Conteo al cierre (cierra la caja)

---

**Fecha de elaboración**: 12/11/2025
**Versión**: 1.0
