# 📝 Changelog - GroupTours

Todas las modificaciones notables del proyecto se documentarán en este archivo.

---

## [1.2.0] - 2025-11-09

### ✨ Nuevo: Sistema de Conversión de Moneda en Facturación

Implementación completa de registro de cotizaciones diarias y conversión automática de moneda extranjera a guaraníes en facturación, cumpliendo con requisitos legales de Paraguay.

#### Agregado

**Modelos:**
- ✅ `CotizacionMoneda` - Registro de cotizaciones diarias con validaciones
  - Una cotización por moneda por día (`unique_together`)
  - Métodos: `obtener_cotizacion_vigente()`, `convertir_a_guaranies()`
  - No permite cotizaciones futuras
- ✅ `FacturaCotizacion` - Auditoría de conversiones realizadas
  - Relación OneToOne con FacturaElectronica
  - Trazabilidad completa de conversión

**Campos Nuevos en FacturaElectronica:**
- ✅ `moneda_original` (FK) - Moneda del paquete antes de conversión
- ✅ `total_original` (Decimal) - Monto en moneda original
- ✅ `tasa_conversion_aplicada` (Decimal) - Tasa de conversión usada

**Métodos Nuevos en SalidaPaquete:**
- ✅ `obtener_precio_en_guaranies()` - Consulta precio convertido sin facturar
- ✅ `precio_en_guaranies` (property) - Acceso rápido al precio convertido

**Funciones Auxiliares:**
- ✅ `preparar_datos_factura_con_conversion()` - Detecta necesidad de conversión
- ✅ `convertir_monto_a_guaranies()` - Convierte montos según cotización
- ✅ `registrar_conversion_factura()` - Crea registro de auditoría

**Modificaciones en Funciones Existentes:**
- ✅ `generar_factura_desde_reserva()` - Ahora convierte automáticamente
- ✅ `generar_factura_global()` - Ahora convierte automáticamente
- ✅ `generar_factura_individual()` - Ahora convierte automáticamente

**Serializers:**
- ✅ Actualizado `FacturaElectronicaSerializer` con campos:
  - `moneda_original_nombre`
  - `moneda_original_codigo`
  - `moneda_original_simbolo`

**Validaciones:**
- ✅ No se puede facturar sin cotización vigente para moneda extranjera
- ✅ El valor de cotización debe ser mayor a cero
- ✅ No se permiten cotizaciones futuras
- ✅ Solo una cotización por moneda por día

**Características:**
- ✅ **Conversión automática** - Todas las facturas se generan en guaraníes (PYG)
- ✅ **Historial de cotizaciones** - Registro completo de todas las cotizaciones
- ✅ **Auditoría completa** - FacturaCotizacion registra cada conversión
- ✅ **Compatibilidad 100%** - No rompe código existente del frontend
- ✅ **Campos opcionales** - El frontend puede mostrar info de conversión si quiere

**Migraciones:**
- ✅ `moneda.0002_cotizacionmoneda_and_more` - Modelo CotizacionMoneda
- ✅ `facturacion.0017_facturacotizacion` - Modelo FacturaCotizacion
- ✅ `facturacion.0018_facturaelectronica_moneda_original_and_more` - Campos de conversión

**Archivos Modificados:**
- `apps/moneda/models.py` - +127 líneas (modelo CotizacionMoneda)
- `apps/paquete/models.py` - +54 líneas (métodos de conversión)
- `apps/facturacion/models.py` - +179 líneas (FacturaCotizacion + funciones auxiliares + modificaciones)
- `apps/facturacion/serializers.py` - +3 líneas (campos de conversión)

#### Casos de Uso Soportados

1. 💵 **Paquete en Guaraníes** (Sin conversión)
   - Paquete con precio en PYG
   - Factura generada en PYG directamente
   - Campos de conversión: NULL

2. 💱 **Paquete en Dólares** (Con conversión automática)
   - Paquete con precio en USD ($1,200)
   - Sistema busca cotización vigente (ej: 7,300 Gs)
   - Convierte automáticamente: $1,200 → 8,760,000 Gs
   - Factura generada en PYG
   - Campos guardados: moneda_original=USD, total_original=1200, tasa=7300
   - FacturaCotizacion creada para auditoría

3. 📊 **Consulta de Precio sin Facturar**
   - Salida en USD puede consultar su equivalente en Gs
   - Usa `salida.obtener_precio_en_guaranies()`
   - No crea factura, solo muestra información

#### Base de Datos

**Nuevas Tablas:**
- `cotizacion_moneda` - Cotizaciones diarias
- `factura_cotizacion` - Auditoría de conversiones

**Campos Agregados:**
- `FacturaElectronica.moneda_original` (nullable)
- `FacturaElectronica.total_original` (nullable)
- `FacturaElectronica.tasa_conversion_aplicada` (nullable)

#### Frontend - Uso de Campos Nuevos

```javascript
// Ejemplo de respuesta del API
{
  "moneda_codigo": "PYG",  // Siempre guaraníes
  "total_final": "8760000.00",

  // NUEVOS: Info de conversión (null si no hubo)
  "moneda_original_codigo": "USD",
  "total_original": "1200.00",
  "tasa_conversion_aplicada": "7300.00"
}
```

---

## [1.1.0] - 2025-11-06

### ✨ Nuevo: Sistema de Notas de Crédito Electrónicas

Implementación completa del sistema de Notas de Crédito para anular facturas emitidas, cumpliendo con las normativas de la SET de Paraguay.

#### Agregado

**Modelos:**
- ✅ `NotaCreditoElectronica` - Modelo principal de NC con numeración correlativa independiente
- ✅ `DetalleNotaCredito` - Detalles de items acreditados
- ✅ Propiedades calculadas en `FacturaElectronica`:
  - `total_acreditado` - Suma de NC activas
  - `saldo_neto` - Saldo restante de la factura
  - `esta_totalmente_acreditada` - Flag de anulación total
  - `esta_parcialmente_acreditada` - Flag de anulación parcial
  - `puede_generar_nota_credito()` - Método de validación

**API Endpoints:**
- ✅ `POST /api/facturacion/generar-nota-credito-total/{factura_id}/` - Anulación total
- ✅ `POST /api/facturacion/generar-nota-credito-parcial/{factura_id}/` - Anulación parcial
- ✅ `GET /api/facturacion/notas-credito/` - Listar NC (con filtros)
- ✅ `GET /api/facturacion/notas-credito/{nota_credito_id}/` - Detalle de NC
- ✅ `GET /api/facturacion/notas-credito-factura/{factura_id}/` - NC de una factura
- ✅ `GET /api/facturacion/descargar-pdf-nota-credito/{nota_credito_id}/` - Descargar PDF

**Funciones de Negocio:**
- ✅ `validar_nota_credito()` - Validaciones exhaustivas
- ✅ `generar_nota_credito_total()` - Generación de NC total (transacción atómica)
- ✅ `generar_nota_credito_parcial()` - Generación de NC parcial con items específicos

**Serializers:**
- ✅ `NotaCreditoElectronicaSerializer` - Serializer básico
- ✅ `NotaCreditoElectronicaDetalladaSerializer` - Serializer con info completa
- ✅ `DetalleNotaCreditoSerializer` - Serializer de detalles
- ✅ Actualizado `FacturaElectronicaSerializer` con campos calculados de NC

**Django Admin:**
- ✅ Registro de `NotaCreditoElectronica` con inline de detalles
- ✅ Registro de `DetalleNotaCredito`
- ✅ Registro de `ClienteFacturacion` (que faltaba)
- ✅ Filtros por tipo, motivo, empresa, establecimiento, fecha
- ✅ Búsqueda por número, cliente, documento, observaciones

**Validaciones:**
- ✅ No se puede acreditar factura inactiva
- ✅ No se puede acreditar factura de configuración
- ✅ No se puede exceder saldo disponible
- ✅ NC total requiere 100% del saldo
- ✅ No se puede generar NC total si existen NC parciales
- ✅ Validación de estructura de items en NC parciales

**Características:**
- ✅ Generación automática de número correlativo (XXX-XXX-XXXXXXX)
- ✅ Cálculo automático de totales e IVA
- ✅ Generación de PDF con formato oficial SET Paraguay
- ✅ Soporte para 6 motivos de emisión
- ✅ Trazabilidad completa con factura afectada
- ✅ Protección de datos (PROTECT en ForeignKey)

**Documentación:**
- ✅ Documentación completa en `/docs/NOTAS_DE_CREDITO.md`
- ✅ Quick Start Guide en `/docs/NOTAS_DE_CREDITO_QUICKSTART.md`
- ✅ Ejemplos de uso con JavaScript/React y Python
- ✅ API Reference completo
- ✅ Guía de troubleshooting
- ✅ Consultas SQL útiles

**Migraciones:**
- ✅ `0015_notacreditoelectronica_detallenotacredito` - Creación de tablas

**Archivos Modificados:**
- `apps/facturacion/models.py` - +800 líneas (modelos y funciones)
- `apps/facturacion/serializers.py` - +90 líneas (serializers)
- `apps/facturacion/views.py` - +290 líneas (endpoints API)
- `apps/facturacion/urls.py` - +6 rutas
- `apps/facturacion/admin.py` - +90 líneas (admin NC + ClienteFacturacion)
- `apps/facturacion/migrations/0015_*.py` - Nueva migración

#### Casos de Uso Soportados

1. ✈️ **Cancelación Total de Reserva**
   - Cliente cancela completamente
   - NC total por el 100% del monto
   - Factura queda totalmente anulada

2. 👥 **Reducción de Pasajeros**
   - Algunos pasajeros cancelan
   - NC parcial por los pasajeros que cancelan
   - Factura queda parcialmente acreditada

3. 🎁 **Descuentos Posteriores**
   - Se aplica descuento después de facturar
   - NC parcial por el monto del descuento

4. ❗ **Error en Facturación**
   - Corrección de datos erróneos
   - NC total + nueva factura correcta

5. 🔄 **Cambio de Cliente**
   - Factura emitida a nombre equivocado
   - NC total + nueva factura al cliente correcto

#### Base de Datos

**Nuevas Tablas:**
- `nota_credito_electronica` - Notas de crédito
- `detalle_nota_credito` - Detalles de NC

**Campos Agregados:** Ninguno en tablas existentes (solo propiedades calculadas)

---

## [1.0.0] - 2025-10-XX

### Sistema Base

#### Características Principales

**Gestión de Paquetes:**
- Paquetes flexibles y fijos
- Salidas con fechas específicas
- Temporadas y precios por temporada
- Habitaciones y cupos

**Gestión de Reservas:**
- Estados: pendiente, confirmada, incompleta, finalizada, cancelada
- Pasajeros vinculados
- Pagos y señas
- Validación de capacidad

**Facturación Electrónica:**
- Facturación global (por reserva completa)
- Facturación individual (por pasajero)
- Condiciones: contado y crédito
- Facturación a terceros
- Generación de PDF

**Gestión de Usuarios:**
- Sistema de roles y permisos
- Empleados vinculados a personas
- Autenticación JWT

**Otras Funcionalidades:**
- Hoteles con cadenas
- Servicios
- Destinos y ciudades
- Monedas múltiples
- Tipos de documento

---

## 🔗 Enlaces Útiles

- **Documentación NC:** [docs/NOTAS_DE_CREDITO.md](docs/NOTAS_DE_CREDITO.md)
- **Quick Start NC:** [docs/NOTAS_DE_CREDITO_QUICKSTART.md](docs/NOTAS_DE_CREDITO_QUICKSTART.md)
- **Setup Project:** [README.md](README.md)
- **Project Guidelines:** [CLAUDE.md](CLAUDE.md)

---

## 📋 Formato del Changelog

Este changelog sigue el formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y el proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

### Tipos de Cambios

- **Agregado** - Para nuevas funcionalidades
- **Cambiado** - Para cambios en funcionalidades existentes
- **Deprecated** - Para funcionalidades que serán removidas
- **Removido** - Para funcionalidades removidas
- **Corregido** - Para corrección de bugs
- **Seguridad** - Para cambios de seguridad

---

**Última actualización:** 2025-11-09
