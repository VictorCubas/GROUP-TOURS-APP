# Facturación a Nombre de Terceros

## 📋 Resumen

Se implementó la funcionalidad para generar facturas (globales e individuales) a nombre de terceros, permitiendo que la factura se emita a un cliente diferente al titular de la reserva o al pasajero.

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

### Caso 4: Factura individual a nombre de tercero

```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &tercero_nombre=María López
  &tercero_tipo_documento=1
  &tercero_numero_documento=1234567
```

→ Factura del pasajero 45 emitida a "María López"
→ `tercero_tipo_documento=1` referencia al TipoDocumento con ID 1 (CI)

**Alternativa con nombre:**
```http
GET /api/reservas/123/descargar-factura-individual/
  ?pasajero_id=45
  &tercero_nombre=María López
  &tercero_tipo_documento=CI
  &tercero_numero_documento=1234567
```

---

## 🔄 Flujo de Decisión

```
┌─────────────────────────────────────────────┐
│ ¿Se proporcionó cliente_facturacion_id?     │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
       SÍ            NO
        │             │
        ▼             ▼
   Buscar por ID   ¿Se proporcionaron datos de tercero?
        │             │
        │      ┌──────┴──────┐
        │      │             │
        │     SÍ            NO
        │      │             │
        │      ▼             ▼
        │   Buscar/Crear   Usar Titular/
        │   por documento   Pasajero
        │      │             │
        └──────┴─────────────┘
               │
               ▼
        Usar datos encontrados
        para la factura
```

---

## ✅ Ventajas de la Implementación

1. **✨ Reutilización:** Clientes frecuentes se guardan automáticamente
2. **🔄 Actualización inteligente:** Datos se mantienen actualizados
3. **↔️ Backward compatible:** No afecta facturas existentes
4. **🎯 Flexible:** Acepta ID o datos completos
5. **📊 Trazabilidad:** Vinculación clara entre facturas y terceros
6. **🔗 Dual:** Funciona para facturas globales e individuales

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

**Última actualización:** 2025-01-03
**Versión:** 1.1
