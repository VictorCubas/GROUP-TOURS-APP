# Facturación a Nombre de Terceros y Facturación a Crédito

## 📋 Resumen

Se implementó la funcionalidad para generar facturas (globales e individuales) a nombre de terceros, permitiendo que la factura se emita a un cliente diferente al titular de la reserva o al pasajero.

**NUEVO (v2.0):** Se agregó soporte para **facturas a crédito**, permitiendo emitir facturas globales antes del pago completo, con plazo de vencimiento configurable.

---

## 🏗️ Arquitectura

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                    Solicitud de Factura                         │
│          GET /api/reservas/{id}/descargar-factura-global/       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  ¿Datos de tercero?          │
              │  - cliente_facturacion_id?   │
              │  - tercero_nombre?           │
              └──────────┬───────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
    ✅ SÍ                             ❌ NO
         │                               │
         ▼                               ▼
┌────────────────────────┐    ┌──────────────────────┐
│ obtener_o_crear_       │    │ Usar datos del       │
│ cliente_facturacion()  │    │ Titular/Pasajero     │
│                        │    │ (comportamiento      │
│ Busca/Crea tercero     │    │  original)           │
└───────────┬────────────┘    └─────────┬────────────┘
            │                           │
            └────────────┬──────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Generar Factura     │
              │  con datos elegidos  │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Descargar PDF       │
              └──────────────────────┘
```

### Modelo de Datos

```
┌─────────────────────────┐
│   ClienteFacturacion    │
├─────────────────────────┤
│ id                      │
│ nombre                  │
│ tipo_documento          │
│ numero_documento        │
│ direccion               │
│ telefono                │
│ email                   │
│ persona_id (FK)         │◄──────┐
│ activo                  │       │
│ fecha_creacion          │       │
│ fecha_modificacion      │       │
└───────────┬─────────────┘       │
            │                     │
            │ 1:N                 │
            │                     │
            ▼                     │
┌─────────────────────────┐       │
│   FacturaElectronica    │       │
├─────────────────────────┤       │
│ id                      │       │
│ reserva_id (FK)         │       │
│ pasajero_id (FK)        │       │
│ cliente_facturacion_id  │───────┘
│ tipo_facturacion        │
│ cliente_nombre          │ ◄─── (Copiado de ClienteFacturacion
│ cliente_tipo_documento  │       o Titular/Pasajero)
│ cliente_numero_documento│
│ ...                     │
└─────────────────────────┘
```

---

## 🔧 Componentes Implementados

### 1. **Modelo `ClienteFacturacion`**

Almacena información de terceros para facturación.

**Campos principales:**
- `nombre`: Nombre completo o razón social
- `tipo_documento`: CI, RUC, PASAPORTE, OTRO
- `numero_documento`: Número de identificación
- `persona`: Vinculación opcional con el sistema de personas

**Ubicación:** `apps/facturacion/models.py`

---

### 2. **Función Helper `obtener_o_crear_cliente_facturacion()`**

Lógica híbrida inteligente que:

1. **Busca cliente existente** por ID o documento
2. **Actualiza datos** si hay cambios
3. **Crea nuevo cliente** si no existe
4. **Vincula a Persona** si es del sistema

**Ventajas:**
- Evita duplicados
- Mantiene datos actualizados
- Permite reutilización

---

### 3. **Funciones de Generación Actualizadas**

#### `generar_factura_global()`
- Genera factura para toda la reserva
- **Prioridad:** Tercero → Titular

#### `generar_factura_individual()`
- Genera factura para un pasajero específico
- **Prioridad:** Tercero → Pasajero

**Nuevos parámetros:**
```python
cliente_facturacion_id=None      # ID de cliente existente
tercero_nombre=None               # Datos del tercero
tercero_tipo_documento=None
tercero_numero_documento=None
tercero_direccion=None
tercero_telefono=None
tercero_email=None
```

---

## 📡 API Endpoints

### Factura Global

```http
GET /api/reservas/{id}/descargar-factura-global/
```

**Query Parameters (todos opcionales):**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `cliente_facturacion_id` | int | ID de cliente existente |
| `tercero_nombre` | string | Nombre del tercero |
| `tercero_tipo_documento` | int o string | **ID** del TipoDocumento (ej: `1` para CI, `4` para RUC) o **nombre** (ej: `"RUC"`) |
| `tercero_numero_documento` | string | Número de documento (con guion para RUC: `80012345-6`) |
| `tercero_direccion` | string | Dirección |
| `tercero_telefono` | string | Teléfono |
| `tercero_email` | string | Email |
| `regenerar_pdf` | boolean | Forzar regeneración del PDF |
| `subtipo_impuesto_id` | int | Tipo de IVA |

---

### Factura Individual

```http
GET /api/reservas/{id}/descargar-factura-individual/
```

**Query Parameters:**

- `pasajero_id` (requerido)
- Todos los parámetros de tercero mencionados arriba

---

## 📋 Tipos de Documento Disponibles

El sistema utiliza el módulo `TipoDocumento` para gestionar los tipos de documento. Los valores disponibles son:

| ID | Nombre | Descripción | Ejemplo de Número |
|----|--------|-------------|-------------------|
| 1  | CI | Cédula de Identidad | `1234567` |
| 2  | DNI | Documento Nacional de Identidad | `12345678` |
| 3  | PASAPORTE | Pasaporte | `AB123456` |
| 4  | RUC | RUC (con guion) | `80012345-6` |

**Importante:**
- El parámetro `tercero_tipo_documento` acepta **ID** (recomendado) o **nombre** (case-insensitive)
- Para RUC, el número debe incluir el **guion y dígito verificador**: `XXXXXXXX-Y`
- Para CI, solo números sin puntos ni guiones

---

## 💡 Ejemplos de Uso

### Caso 1: Factura a nombre del titular (comportamiento original)

```http
GET /api/reservas/123/descargar-factura-global/
```

→ Factura emitida a nombre del titular de la reserva
→ Usa el tipo de documento y número registrados en el sistema

---

### Caso 1B: Factura a nombre del titular pero con documento diferente (NUEVO ✨)

```http
GET /api/reservas/123/descargar-factura-global/
  ?tercero_tipo_documento=4
  &tercero_numero_documento=80012345-6
```

**Escenario:** El titular está registrado con CI 1234567, pero solicita factura con RUC 80012345-6

→ Factura emitida a nombre del titular (mismo nombre)
→ Pero con el tipo de documento y número especificados en los parámetros
→ Se crea automáticamente un ClienteFacturacion vinculado al titular
→ **NO modifica** los datos de la Persona en el sistema

**¿Cuándo usar este caso?**
- Cliente tiene CI pero solicita factura con RUC
- Cliente cambió de documento pero no actualizó su perfil
- Cliente tiene múltiples documentos (ej: CI y Pasaporte) y quiere usar el alternativo

**Variantes:**
- Solo cambiar tipo: `?tercero_tipo_documento=3` (mantiene número actual)
- Solo cambiar número: `?tercero_numero_documento=7654321` (mantiene tipo actual)
- Cambiar ambos: `?tercero_tipo_documento=4&tercero_numero_documento=80012345-6`

---

### Caso 2: Factura a nombre de tercero (cliente nuevo) - Opción A: Por ID

```http
GET /api/reservas/123/descargar-factura-global/
  ?tercero_nombre=Empresa ABC S.A.
  &tercero_tipo_documento=4
  &tercero_numero_documento=80012345-6
  &tercero_direccion=Av. España 1234
  &tercero_telefono=021-123456
  &tercero_email=facturacion@abc.com
```

→ Factura emitida a "Empresa ABC S.A."
→ ClienteFacturacion creado automáticamente
→ `tercero_tipo_documento=4` referencia al TipoDocumento con ID 4 (RUC)

---

### Caso 2B: Factura a nombre de tercero (cliente nuevo) - Opción B: Por nombre

```http
GET /api/reservas/123/descargar-factura-global/
  ?tercero_nombre=Empresa ABC S.A.
  &tercero_tipo_documento=RUC
  &tercero_numero_documento=80012345-6
  &tercero_direccion=Av. España 1234
  &tercero_telefono=021-123456
  &tercero_email=facturacion@abc.com
```

→ Factura emitida a "Empresa ABC S.A."
→ ClienteFacturacion creado automáticamente
→ `tercero_tipo_documento=RUC` busca el TipoDocumento por nombre (case-insensitive)

---

### Caso 3: Factura a nombre de tercero (cliente existente)

```http
GET /api/reservas/123/descargar-factura-global/
  ?cliente_facturacion_id=5
```

→ Reutiliza datos del ClienteFacturacion con ID=5

---

### Caso 4: Factura individual a nombre del pasajero (comportamiento original)

```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
```

→ Factura emitida a nombre del pasajero con ID 45
→ Usa los datos personales del pasajero registrado en la reserva
→ Usa el tipo de documento y número registrados en el sistema

---

### Caso 4B: Factura individual del pasajero pero con documento diferente (NUEVO ✨)

```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &tercero_tipo_documento=4
  &tercero_numero_documento=80067890-3
```

**Escenario:** El pasajero está registrado con CI, pero solicita factura con RUC de su empresa

→ Factura emitida a nombre del pasajero (mismo nombre)
→ Pero con el tipo de documento y número especificados
→ Se crea automáticamente un ClienteFacturacion vinculado al pasajero
→ **NO modifica** los datos de la Persona en el sistema

**¿Cuándo usar este caso?**
- Pasajero quiere factura con RUC de su empresa
- Pasajero tiene documento actualizado no reflejado en el sistema
- Pasajero viaja con pasaporte pero quiere factura con CI

**Variantes:**
- Solo cambiar tipo: `?pasajero_id=45&tercero_tipo_documento=3`
- Solo cambiar número: `?pasajero_id=45&tercero_numero_documento=7654321`
- Cambiar ambos: `?pasajero_id=45&tercero_tipo_documento=4&tercero_numero_documento=80067890-3`

---

### Caso 5: Factura individual a nombre de tercero (cliente nuevo) - Opción A: Por ID

```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &tercero_nombre=María López
  &tercero_tipo_documento=1
  &tercero_numero_documento=1234567
  &tercero_direccion=Calle Principal 456
  &tercero_telefono=0981-234567
  &tercero_email=maria.lopez@email.com
```

→ Factura del pasajero 45 emitida a "María López"
→ ClienteFacturacion creado automáticamente
→ `tercero_tipo_documento=1` referencia al TipoDocumento con ID 1 (CI)

---

### Caso 5B: Factura individual a nombre de tercero (cliente nuevo) - Opción B: Por nombre

```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &tercero_nombre=María López
  &tercero_tipo_documento=CI
  &tercero_numero_documento=1234567
  &tercero_direccion=Calle Principal 456
  &tercero_telefono=0981-234567
  &tercero_email=maria.lopez@email.com
```

→ Factura del pasajero 45 emitida a "María López"
→ ClienteFacturacion creado automáticamente
→ `tercero_tipo_documento=CI` busca el TipoDocumento por nombre (case-insensitive)

---

### Caso 6: Factura individual a nombre de tercero (cliente existente)

```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &cliente_facturacion_id=5
```

→ Factura del pasajero 45 emitida usando datos del ClienteFacturacion con ID=5
→ Reutiliza datos guardados previamente

---

### Caso 7: Factura individual a nombre de empresa (RUC)

```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &tercero_nombre=Empresa XYZ S.R.L.
  &tercero_tipo_documento=4
  &tercero_numero_documento=80067890-3
  &tercero_direccion=Zona Industrial, Lote 12
  &tercero_telefono=021-987654
  &tercero_email=contabilidad@xyz.com.py
```

→ Factura del pasajero 45 emitida a empresa "Empresa XYZ S.R.L."
→ `tercero_tipo_documento=4` referencia al TipoDocumento con ID 4 (RUC)
→ Número de RUC incluye guion y dígito verificador

**Alternativa con nombre:**
```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &tercero_nombre=Empresa XYZ S.R.L.
  &tercero_tipo_documento=RUC
  &tercero_numero_documento=80067890-3
  &tercero_direccion=Zona Industrial, Lote 12
  &tercero_telefono=021-987654
  &tercero_email=contabilidad@xyz.com.py
```

---

## 🔄 Flujo de Decisión (Actualizado v1.2)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Solicitud de Factura                         │
│          GET /api/reservas/{id}/descargar-factura-*             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  PRIORIDAD 1:                │
              │  ¿cliente_facturacion_id O   │
              │  (tercero_nombre + tipo +    │
              │   numero)?                   │
              └──────────┬───────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
    ✅ SÍ                             ❌ NO
         │                               │
         ▼                               ▼
┌────────────────────────┐    ┌──────────────────────────┐
│ Buscar/Crear           │    │  PRIORIDAD 2:            │
│ ClienteFacturacion     │    │  ¿Solo tercero_tipo O    │
│ (Tercero completo)     │    │   tercero_numero?        │
└───────────┬────────────┘    └─────────┬────────────────┘
            │                           │
            │              ┌────────────┴───────────┐
            │              │                        │
            │         ✅ SÍ                      ❌ NO
            │              │                        │
            │              ▼                        ▼
            │    ┌──────────────────────┐  ┌──────────────────┐
            │    │ Crear                │  │  PRIORIDAD 3:    │
            │    │ ClienteFacturacion   │  │  Usar datos      │
            │    │ con datos Titular/   │  │  originales del  │
            │    │ Pasajero pero        │  │  Titular/        │
            │    │ documento override   │  │  Pasajero        │
            │    │ (NUEVO ✨)           │  │  sin cambios     │
            │    └─────────┬────────────┘  └────────┬─────────┘
            │              │                        │
            └──────────────┴────────────────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │  Generar Factura     │
                │  con datos elegidos  │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │  Descargar PDF       │
                └──────────────────────┘
```

### 🎯 Prioridades de Datos del Cliente

El sistema determina los datos del cliente en la factura según estas **3 prioridades**:

#### **Prioridad 1: Tercero completo (tercero diferente al titular/pasajero)**
- **Se activa cuando:** Se proporciona `cliente_facturacion_id` **O** todos los datos completos del tercero (`tercero_nombre` + `tercero_tipo_documento` + `tercero_numero_documento`)
- **Comportamiento:** Crea/busca un `ClienteFacturacion` completamente independiente
- **Uso:** Facturar a nombre de otra persona/empresa diferente al titular/pasajero

#### **Prioridad 2: Override de documento (NUEVO ✨)**
- **Se activa cuando:** Se proporciona **SOLO** `tercero_tipo_documento` **Y/O** `tercero_numero_documento` (sin `tercero_nombre`)
- **Comportamiento:**
  - Usa el **nombre** del titular/pasajero
  - Usa el **documento** especificado en los parámetros
  - Crea un `ClienteFacturacion` vinculado al titular/pasajero original
- **Uso:** Mismo cliente pero con documento diferente (ej: CI → RUC)
- **NO modifica** la Persona en el sistema

#### **Prioridad 3: Datos originales (comportamiento por defecto)**
- **Se activa cuando:** No se proporciona ningún parámetro de tercero
- **Comportamiento:** Usa todos los datos del titular/pasajero tal cual están en el sistema
- **Uso:** Facturación estándar sin modificaciones

---

## ✅ Ventajas de la Implementación

1. **✨ Reutilización:** Clientes frecuentes se guardan automáticamente
2. **🔄 Actualización inteligente:** Datos se mantienen actualizados
3. **↔️ Backward compatible:** No afecta facturas existentes
4. **🎯 Flexible:** Acepta ID o datos completos
5. **📊 Trazabilidad:** Vinculación clara entre facturas y terceros
6. **🔗 Dual:** Funciona para facturas globales e individuales
7. **🆕 Override de documento:** Permite cambiar documento sin modificar la Persona (v1.2)

---

## 🗄️ Migraciones

```bash
# Migraciones creadas
apps/facturacion/migrations/0011_clientefacturacion_and_more.py
apps/facturacion/migrations/0012_rename_cliente_fac_numero__cf6242_idx_cliente_fac_numero__b6635b_idx_and_more.py

# Cambios:
- Tabla: cliente_facturacion
- Campo: facturaelectronica.cliente_facturacion_id
- Campo: clientefacturacion.tipo_documento (ForeignKey a TipoDocumento)
- Índices: numero_documento + tipo_documento, activo
```

**Aplicar migraciones:**
```bash
python manage.py migrate facturacion
```

---

## 📝 Notas Importantes

- Si no se especifican datos de tercero, el comportamiento es el **original** (titular/pasajero)
- Los datos del cliente se **copian** a la factura para inmutabilidad
- La vinculación a `ClienteFacturacion` es **opcional** pero recomendada
- La búsqueda de clientes es por **tipo + número de documento**
- Los clientes inactivos (`activo=False`) no se reutilizan
- **`tipo_documento` usa ForeignKey** a la tabla `TipoDocumento` para consistencia con el modelo `Persona`
- El parámetro `tercero_tipo_documento` acepta **ID** (recomendado) o **nombre** del tipo de documento
- Para **RUC**, el formato debe incluir guion y dígito verificador: `XXXXXXXX-Y`

### 🆕 Notas sobre Override de Documento (v1.2)

- **Propósito:** Permitir que la factura use un documento diferente al registrado en el sistema **sin modificar** los datos de la Persona
- **Activación:** Enviar solo `tercero_tipo_documento` y/o `tercero_numero_documento` (sin `tercero_nombre`)
- **Comportamiento:**
  - Se crea un `ClienteFacturacion` con el nombre del titular/pasajero original
  - Se usa el tipo/número de documento especificado en los parámetros
  - Se vincula al titular/pasajero mediante el campo `persona_id`
  - La Persona original NO se modifica
- **Casos de uso comunes:**
  - Cliente registrado con CI pero solicita factura con RUC
  - Pasajero viaja con pasaporte pero quiere factura con CI
  - Cliente actualizó su documento pero no su perfil
- **Importante:** Esta funcionalidad es diferente a facturar a nombre de un tercero completo (donde se proporciona `tercero_nombre`)

---

## 🔍 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `apps/facturacion/models.py` | + ClienteFacturacion (con FK a TipoDocumento)<br>+ obtener_o_crear_cliente_facturacion()<br>~ generar_factura_global()<br>~ generar_factura_individual()<br>~ FacturaElectronica.cliente_facturacion |
| `apps/reserva/views.py` | ~ descargar_factura_global()<br>~ descargar_factura_individual() |
| `apps/facturacion/migrations/` | + 0011_clientefacturacion_and_more.py<br>+ 0012_..._alter_tipo_documento.py |

---

## 🚀 Siguiente Paso (Opcional)

Si deseas gestionar clientes de facturación desde el frontend, puedes crear endpoints CRUD:

```http
GET    /api/clientes-facturacion/       # Listar
POST   /api/clientes-facturacion/       # Crear
GET    /api/clientes-facturacion/{id}/  # Detalle
PUT    /api/clientes-facturacion/{id}/  # Actualizar
DELETE /api/clientes-facturacion/{id}/  # Desactivar
```

---

## 🔄 Changelog

### v1.2 - 2025-01-05 (NUEVO ✨)
- ✨ **Añadido:** Override de documento sin cambiar datos de la Persona
- 🔧 **Mejorado:** `generar_factura_global()` con Prioridad 2 para override de documento
- 🔧 **Mejorado:** `generar_factura_individual()` con Prioridad 2 para override de documento
- 📖 **Documentado:** Nuevos casos de uso 1B y 4B en ejemplos
- 📖 **Actualizado:** Diagrama de flujo con las 3 prioridades
- 🎯 **Casos de uso:** Cliente con CI solicita factura con RUC sin modificar su perfil
- ✅ **No requiere migración:** Usa la estructura existente de ClienteFacturacion

### v1.1 - 2025-01-03
- ✅ **Cambiado:** `ClienteFacturacion.tipo_documento` de CharField con CHOICES a ForeignKey(TipoDocumento)
- ✅ **Actualizado:** `obtener_o_crear_cliente_facturacion()` acepta ID o nombre del TipoDocumento
- ✅ **Actualizado:** Funciones de generación de facturas para usar FK
- ✅ **Migración:** 0012 para convertir campo a ForeignKey
- ✅ **Consistencia:** Ahora usa el mismo modelo que `Persona`

### v1.0 - 2025-01-03
- 🎉 Implementación inicial de facturación a terceros
- ✨ Modelo `ClienteFacturacion`
- ✨ Soporte para facturación global e individual
- ✨ Reutilización automática de clientes

---

## 💳 Facturación a Crédito (NUEVO v2.0)

### Descripción

A partir de la versión 2.0, el sistema soporta **facturas a crédito** además de facturas al contado. Esta funcionalidad permite emitir facturas globales después de confirmar la reserva (pagando solo la seña), sin necesidad de pagar el total.

### Características Principales

| Característica | Contado | Crédito |
|----------------|---------|---------|
| **Momento de emisión** | Después del pago completo | Después de pagar seña (confirmada) |
| **Estado requerido** | finalizada | confirmada o finalizada |
| **Pago requerido** | 100% | Seña (monto mínimo) |
| **Modalidad** | Global o Individual | **Solo Global** |
| **Fecha de vencimiento** | N/A | **Fecha de salida - 15 días** |
| **Se puede emitir otra factura** | No | No |

### Reglas de Negocio

1. **Condición de pago se define al confirmar la reserva** (junto con modalidad de facturación)
2. **Facturas a crédito son SOLO para facturación GLOBAL**
   - Si se elige `modalidad_facturacion='individual'` y `condicion_pago='credito'` → Error de validación
3. **Una vez emitida una factura (contado o crédito), NO se puede emitir otra**
4. **Fecha de vencimiento automática: Fecha de salida - 15 días**
   - El cliente debe cancelar el pago completo 15 días antes de la fecha de salida
   - Ejemplo: Si la salida es el 1 de febrero, el vencimiento es el 17 de enero

---

### Flujo de Trabajo

#### Flujo para Factura CONTADO (comportamiento original)

```
1. Reserva creada → Estado: pendiente
2. Se paga seña → Confirmar reserva:
   - modalidad_facturacion = 'global'
   - condicion_pago = 'contado'
   → Estado: confirmada
3. Se pagan cuotas hasta completar el 100%
4. Reserva pasa a → Estado: finalizada
5. ✅ puede_descargar_factura_global = true
6. Se genera factura global al contado
```

#### Flujo para Factura CRÉDITO (NUEVO ✨)

```
1. Reserva creada → Estado: pendiente
2. Se paga seña → Confirmar reserva:
   - modalidad_facturacion = 'global'
   - condicion_pago = 'credito'
   → Estado: confirmada
3. ✅ puede_descargar_factura_global = true (inmediatamente después de confirmar)
4. Se genera factura global a crédito:
   - condicion_venta = 'credito'
   - Monto facturado: TOTAL de la reserva (costo_total_estimado)
   - fecha_vencimiento = fecha_salida_paquete - 15 días
   - Ejemplo: Si salida es 01/02/2025 → vencimiento es 17/01/2025
5. Cliente realiza pagos parciales (cuotas) antes del vencimiento:
   - Puede realizar múltiples pagos (ej: Cuota 1: $3,000, Cuota 2: $2,500, etc.)
   - El sistema acumula automáticamente en monto_pagado
   - Cada pago genera un comprobante independiente
   - El cliente puede consultar el saldo pendiente en cualquier momento
6. Cuando monto_pagado >= costo_total_estimado → Estado: finalizada
```

---

### Cambios en el Modelo de Datos

#### Modelo `Reserva`

**Nuevo campo:**
```python
condicion_pago = models.CharField(
    max_length=20,
    choices=[('contado', 'Contado'), ('credito', 'Crédito')],
    null=True,
    blank=True,
    help_text="Condición de pago elegida al confirmar la reserva"
)
```

#### Modelo `FacturaElectronica`

**Nuevo campo:**
```python
fecha_vencimiento = models.DateField(
    null=True,
    blank=True,
    help_text="Fecha de vencimiento del crédito. Para crédito: fecha_salida - 15 días"
)
```

---

### API: Confirmar Reserva

Al confirmar una reserva (pasar de `pendiente` a `confirmada`), ahora se debe especificar **ambos** parámetros:

**Endpoint:** `PUT/PATCH /api/reservas/{id}/`

**Body (ejemplo):**
```json
{
  "estado": "confirmada",
  "modalidad_facturacion": "global",
  "condicion_pago": "credito"
}
```

**Validaciones:**
- Si `modalidad_facturacion = 'individual'` y `condicion_pago = 'credito'` → **Error 400**
  - Mensaje: "Las facturas a crédito solo están disponibles para facturación global"
- Si se intenta cambiar `condicion_pago` después de confirmar → **Error 400**
  - Mensaje: "No se puede cambiar la condición de pago"

---

### API: Generar Factura Global

**Endpoint:** `GET /api/reservas/{id}/descargar-factura-global/`

**Query Parameters (opcionales):**

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `cliente_facturacion_id` | int | ID de cliente existente | `5` |
| `tercero_nombre` | string | Nombre del tercero | `"Empresa ABC S.A."` |
| `tercero_tipo_documento` | int/string | Tipo de documento | `4` o `"RUC"` |
| `tercero_numero_documento` | string | Número de documento | `"80012345-6"` |
| `regenerar_pdf` | boolean | Forzar regeneración | `true` |
| `subtipo_impuesto_id` | int | Tipo de IVA | `1` |

**Comportamiento:**
- Si `condicion_pago = 'credito'`:
  - `fecha_vencimiento` se calcula automáticamente: **fecha_salida - 15 días**
  - Ejemplo: Salida 15/02/2025 → Vencimiento 31/01/2025
- Si `condicion_pago = 'contado'`:
  - `fecha_vencimiento` es `null` (no aplica)

---

### Ejemplos de Uso

#### Ejemplo 1: Factura Global al Contado (comportamiento original)

```http
# Paso 1: Confirmar reserva al contado
PATCH /api/reservas/123/
Content-Type: application/json

{
  "modalidad_facturacion": "global",
  "condicion_pago": "contado"
}

# Paso 2: Pagar el 100% del costo
# (mediante endpoints de comprobantes)

# Paso 3: Verificar que puede_descargar_factura_global = true
GET /api/reservas/123/

# Paso 4: Generar factura
GET /api/reservas/123/descargar-factura-global/
```

→ Factura generada con `condicion_venta='contado'`

---

#### Ejemplo 2: Factura Global a Crédito (NUEVO ✨)

```http
# Paso 1: Confirmar reserva a crédito
PATCH /api/reservas/123/
Content-Type: application/json

{
  "modalidad_facturacion": "global",
  "condicion_pago": "credito"
}

# Paso 2: Verificar que puede_descargar_factura_global = true (inmediatamente)
GET /api/reservas/123/

# Respuesta:
{
  "id": 123,
  "estado": "confirmada",
  "modalidad_facturacion": "global",
  "condicion_pago": "credito",
  "puede_descargar_factura_global": true,  # ✅ Disponible inmediatamente
  "factura_global_generada": false,
  ...
}

# Paso 3: Generar factura a crédito
GET /api/reservas/123/descargar-factura-global/

# Paso 4 (opcional): Cliente va pagando a cuotas antes del vencimiento
```

→ Factura generada con:
- `condicion_venta='credito'`
- `fecha_vencimiento=fecha_salida - 15 días`
- Ejemplo: Si salida es 20/02/2025 → vencimiento es 05/02/2025

---

#### Ejemplo 3: Factura a Crédito a nombre de Tercero (RUC)

```http
# Paso 1: Confirmar reserva a crédito
PATCH /api/reservas/123/
Content-Type: application/json

{
  "modalidad_facturacion": "global",
  "condicion_pago": "credito"
}

# Paso 2: Generar factura a crédito a nombre de empresa
GET /api/reservas/123/descargar-factura-global/
  ?tercero_nombre=Empresa XYZ S.R.L.
  &tercero_tipo_documento=4
  &tercero_numero_documento=80067890-3
  &tercero_email=contabilidad@xyz.com.py
```

→ Factura generada con:
- `condicion_venta='credito'`
- `fecha_vencimiento=fecha_salida - 15 días`
- Ejemplo: Si salida es 10/03/2025 → vencimiento es 23/02/2025
- Cliente: "Empresa XYZ S.R.L." (RUC: 80067890-3)

---

#### Ejemplo 4: Flujo Completo con Pagos Parciales (CRÉDITO)

```http
# SITUACIÓN: Reserva de $10,000 con salida el 20/03/2025
# Fecha de vencimiento: 05/03/2025 (20/03 - 15 días)

# ========== PASO 1: Pagar seña y confirmar ==========
POST /api/comprobantes/
{
  "reserva_id": 123,
  "tipo": "seña",
  "monto": 2000.00,
  "metodo_pago": "transferencia"
}

PATCH /api/reservas/123/
{
  "modalidad_facturacion": "global",
  "condicion_pago": "credito"
}

# Estado actual:
# - monto_pagado: $2,000
# - saldo_pendiente: $8,000
# - estado: "confirmada"

# ========== PASO 2: Generar factura a crédito ==========
GET /api/reservas/123/descargar-factura-global/

# Factura emitida por: $10,000 (total)
# Vencimiento: 05/03/2025

# ========== PASO 3: Cliente paga cuota 1 (10/01/2025) ==========
POST /api/comprobantes/
{
  "reserva_id": 123,
  "tipo": "cuota",
  "monto": 3000.00,
  "metodo_pago": "efectivo"
}

# Estado actual:
# - monto_pagado: $5,000 ($2,000 + $3,000)
# - saldo_pendiente: $5,000
# - estado: "confirmada"

# ========== PASO 4: Cliente paga cuota 2 (25/01/2025) ==========
POST /api/comprobantes/
{
  "reserva_id": 123,
  "tipo": "cuota",
  "monto": 2500.00,
  "metodo_pago": "tarjeta"
}

# Estado actual:
# - monto_pagado: $7,500
# - saldo_pendiente: $2,500
# - estado: "confirmada"

# ========== PASO 5: Cliente paga saldo final (01/03/2025) ==========
POST /api/comprobantes/
{
  "reserva_id": 123,
  "tipo": "saldo",
  "monto": 2500.00,
  "metodo_pago": "transferencia"
}

# Estado final:
# - monto_pagado: $10,000
# - saldo_pendiente: $0
# - estado: "finalizada" ✅ (pago completo antes del vencimiento)

# ========== CONSULTAR ESTADO ==========
GET /api/reservas/123/

# Respuesta:
{
  "id": 123,
  "estado": "finalizada",
  "condicion_pago": "credito",
  "costo_total_estimado": 10000.00,
  "monto_pagado": 10000.00,
  "saldo_pendiente": 0.00,
  "comprobantes": [
    {
      "fecha_pago": "2024-12-20",
      "tipo": "Seña",
      "monto": 2000.00
    },
    {
      "fecha_pago": "2025-01-10",
      "tipo": "Cuota",
      "monto": 3000.00
    },
    {
      "fecha_pago": "2025-01-25",
      "tipo": "Cuota",
      "monto": 2500.00
    },
    {
      "fecha_pago": "2025-03-01",
      "tipo": "Saldo",
      "monto": 2500.00
    }
  ],
  "factura_global_generada": true,
  "factura_global_id": 789
}
```

**Resultado:**
- ✅ Factura emitida por $10,000 el día que se confirmó la reserva
- ✅ Cliente realizó 4 pagos parciales antes del vencimiento (05/03)
- ✅ Reserva pasó a estado "finalizada" al completar el pago
- ✅ Cada pago quedó registrado en el historial de comprobantes

---

### Campo `puede_descargar_factura_global` en el Serializer

Este campo del endpoint `GET /api/reservas/{id}/` se actualiza dinámicamente según la condición de pago:

| Condición | Estado Requerido | Pago Requerido | Vencimiento | `puede_descargar_factura_global` |
|-----------|------------------|----------------|-------------|----------------------------------|
| **contado** | finalizada | 100% | N/A | `true` si cumple ambos |
| **credito** | confirmada o finalizada | Seña (mínimo) | Fecha salida - 15 días | `true` si cumple estado |

**Código del serializer:**
```python
def get_puede_descargar_factura_global(self, obj):
    if obj.modalidad_facturacion != 'global':
        return False

    if not obj.condicion_pago:
        return False

    if obj.condicion_pago == 'contado':
        return obj.estado == 'finalizada' and obj.esta_totalmente_pagada()
    elif obj.condicion_pago == 'credito':
        return obj.estado in ['confirmada', 'finalizada']
```

---

### Validaciones del Sistema

#### Al Confirmar Reserva

```python
# apps/reserva/models.py → Reserva.actualizar_estado()

# Validación 1: Ambos campos son requeridos
if modalidad_facturacion is None or condicion_pago is None:
    raise ValidationError("Debe especificar modalidad y condición de pago")

# Validación 2: Crédito solo para facturación global
if modalidad_facturacion == 'individual' and condicion_pago == 'credito':
    raise ValidationError(
        "Las facturas a crédito solo están disponibles para facturación global"
    )

# Validación 3: No se puede cambiar después de confirmar
if self.condicion_pago and condicion_pago != self.condicion_pago:
    raise ValidationError("No se puede cambiar la condición de pago")
```

#### Al Generar Factura Global

```python
# apps/facturacion/models.py → validar_factura_global()

if reserva.condicion_pago == 'contado':
    # Requiere estado finalizada y pago completo
    if reserva.estado != 'finalizada':
        raise ValidationError("Debe estar finalizada para facturar al contado")
    if reserva.monto_pagado < reserva.costo_total_estimado:
        raise ValidationError("Debe pagar el total antes de facturar al contado")

elif reserva.condicion_pago == 'credito':
    # Solo requiere estado confirmada (NO requiere pago completo)
    if reserva.estado not in ['confirmada', 'finalizada']:
        raise ValidationError("Debe estar confirmada para facturar a crédito")

    # Validar que haya fecha de salida
    if not reserva.salida or not reserva.salida.fecha_salida:
        raise ValidationError("No se puede facturar a crédito sin fecha de salida")

    # Validar que el vencimiento (fecha_salida - 15 días) no sea en el pasado
    from datetime import timedelta
    fecha_vencimiento = reserva.salida.fecha_salida - timedelta(days=15)
    if fecha_vencimiento < timezone.now().date():
        raise ValidationError(f"La fecha de vencimiento ({fecha_vencimiento}) ya pasó")
```

---

### Migraciones Aplicadas

```bash
# Migración 1: Campo condicion_pago en Reserva
apps/reserva/migrations/0016_reserva_condicion_pago.py

# Migración 2: Campo fecha_vencimiento en FacturaElectronica
apps/facturacion/migrations/0013_facturaelectronica_fecha_vencimiento_and_more.py

# Migración 3: Ajuste de campo fecha_vencimiento (eliminación de plazo_credito_dias)
apps/facturacion/migrations/0014_remove_facturaelectronica_plazo_credito_dias_and_more.py
```

**Para aplicar:**
```bash
python manage.py migrate
```

---

### Consideraciones Importantes

1. **Una factura, un tipo:** Una vez emitida una factura (contado o crédito), no se puede emitir otra para la misma reserva
2. **Crédito solo global:** Las facturas individuales NO soportan crédito
3. **Factura por el TOTAL:** La factura a crédito se emite por el monto TOTAL de la reserva (costo_total_estimado)
   - Aunque el cliente solo haya pagado la seña
   - El saldo restante debe pagarse antes del vencimiento
4. **Pagos parciales permitidos:** El cliente puede realizar múltiples pagos (cuotas) antes del vencimiento
   - Cada pago genera un comprobante independiente
   - El sistema acumula automáticamente en `monto_pagado`
   - El `saldo_pendiente` se calcula dinámicamente: `costo_total_estimado - monto_pagado`
5. **Fecha de vencimiento automática:** Para crédito, siempre es **fecha_salida - 15 días**
   - No es configurable, es una regla fija del negocio
   - Ejemplo: Salida 20/03 → Vencimiento 05/03
   - El cliente debe completar el pago ANTES de esta fecha
6. **Validación de vencimiento:** No se puede generar factura a crédito si el vencimiento calculado ya pasó
7. **Inmutabilidad:** Los campos `modalidad_facturacion` y `condicion_pago` NO se pueden cambiar después de confirmar
8. **Estado de la reserva:**
   - Factura CONTADO: Requiere estado `finalizada`
   - Factura CRÉDITO: Disponible desde estado `confirmada`

---

### Roadmap Futuro (Opcional)

- [ ] Tracking de saldo de factura a crédito
- [ ] Alertas de vencimiento (email automático X días antes)
- [ ] Intereses por mora
- [ ] Dashboard de facturas vencidas
- [ ] Notas de crédito (para anulación/corrección de facturas)

---

**Última actualización:** 2025-01-05
**Versión:** 2.0
