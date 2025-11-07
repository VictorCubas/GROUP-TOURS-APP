# 📊 GroupTours - Resumen del Proyecto

> Estado actual del sistema al 06 de Noviembre de 2025

---

## 🎯 Descripción General

**GroupTours** es una aplicación Django REST Framework para la gestión integral de paquetes turísticos, reservas, facturación electrónica y administración de una agencia de viajes.

### Stack Tecnológico

- **Backend:** Django 4.2 + Django REST Framework 3.14.0
- **Base de Datos:** PostgreSQL (psycopg2)
- **Autenticación:** JWT (djangorestframework-simplejwt)
- **Documentos:** ReportLab (generación de PDF)
- **Otros:** Django Polymorphic, Django CORS Headers, python-dotenv

---

## 📦 Módulos Principales

### 1. **Paquetes Turísticos** (`apps/paquete/`)

✅ **Funcionalidades:**
- Creación de paquetes flexibles y fijos
- Salidas con fechas específicas (SalidaPaquete)
- Temporadas y variación de precios
- Cupos por habitación (CupoHabitacionSalida)
- Historial de precios
- Cálculo automático de precios de venta

✅ **Características:**
- Modalidad flexible/fijo
- Tipo terrestre/aéreo
- Precio actual, final, y de venta
- Ganancia/comisión configurable

---

### 2. **Reservas** (`apps/reserva/`)

✅ **Estados de Reserva:**
```
pendiente → confirmada → incompleta → finalizada
                ↓
            cancelada
```

✅ **Funcionalidades:**
- Gestión de titular y pasajeros
- Modalidad de facturación (global/individual)
- Condición de pago (contado/crédito)
- Validación de capacidad
- Generación automática de código (RSV-YYYY-XXXXX)
- Máquina de estados con validaciones

✅ **Pasajeros:**
- Vinculación con PersonaFisica
- Datos de ticket/voucher
- Flag de titular
- Estado de pago individual

---

### 3. **Facturación Electrónica** (`apps/facturacion/`) 🆕

✅ **Tipos de Factura:**
- **Global:** Una factura por toda la reserva
- **Individual:** Una factura por cada pasajero

✅ **Modalidades de Pago:**
- **Contado:** Pago inmediato
- **Crédito:** Pago a plazo (con fecha de vencimiento)

✅ **Facturación a Terceros:**
- ClienteFacturacion independiente
- Emisión a nombre de tercero sin afectar titular

✅ **Características:**
- Numeración correlativa automática (XXX-XXX-XXXXXXX)
- Cálculo automático de IVA (5%, 10%, Exento)
- Generación de PDF con formato SET Paraguay
- Timbrado y punto de expedición
- Validaciones exhaustivas

#### 🆕 **Notas de Crédito** (Versión 1.1.0)

✅ **Tipos:**
- **Total:** Anula 100% de la factura
- **Parcial:** Anula items específicos o montos parciales

✅ **Motivos:**
- Cancelación de reserva
- Devolución
- Descuento/Bonificación
- Error en facturación
- Ajuste de precio
- Otro

✅ **Características:**
- Numeración correlativa independiente
- Cálculo automático de totales e IVA
- Generación de PDF
- Trazabilidad completa con factura afectada
- Propiedades calculadas en factura (total_acreditado, saldo_neto)
- Validaciones de saldo disponible

✅ **API Completa:**
- Generación NC total/parcial
- Listado con filtros
- Consulta por factura
- Descarga de PDF

**📚 Documentación:**
- [NOTAS_DE_CREDITO.md](./NOTAS_DE_CREDITO.md) - Documentación completa
- [NOTAS_DE_CREDITO_QUICKSTART.md](./NOTAS_DE_CREDITO_QUICKSTART.md) - Guía rápida

---

### 4. **Hoteles** (`apps/hotel/`)

✅ **Estructura:**
- CadenaHotelera → Hotel → Habitacion
- Servicios por hotel y por habitación
- Tipos de habitación (single, doble, triple, suite, premium)
- Precios por noche con moneda

---

### 5. **Usuarios y Permisos** (`apps/usuario/`, `apps/rol/`, `apps/permiso/`)

✅ **Sistema de Autenticación:**
- Custom User Model (AUTH_USER_MODEL)
- JWT con lifetime de 1 día
- Vinculación con Empleado → PersonaFisica

✅ **Roles y Permisos:**
- Sistema granular de permisos
- Roles con múltiples permisos
- Vinculación con Módulos

---

### 6. **Personas** (`apps/persona/`)

✅ **Modelo Polimórfico:**
- **PersonaFisica:** Personas naturales (edad calculada)
- **PersonaJuridica:** Empresas/organizaciones

---

### 7. **Otras Entidades**

- **Destino** - Destinos turísticos
- **Ciudad** - Ciudades (vinculadas a hoteles)
- **Zona Geográfica** - Zonas geográficas
- **Moneda** - Soporte multi-moneda
- **Tipo Documento** - CI, RUC, Pasaporte, etc.
- **Nacionalidad** - Nacionalidades
- **Empleado** - Empleados con puestos
- **Distribuidora** - Distribuidoras de paquetes

---

## 🌐 API REST

### Base URL
```
http://localhost:8000/api/
```

### Endpoints Principales

#### Autenticación
```
POST /api/login/
```

#### Paquetes
```
GET    /api/paquete/
POST   /api/paquete/
GET    /api/paquete/{id}/
PUT    /api/paquete/{id}/
DELETE /api/paquete/{id}/
```

#### Reservas
```
GET    /api/reservas/
POST   /api/reservas/
GET    /api/reservas/{id}/
PUT    /api/reservas/{id}/
```

#### Facturación
```
POST   /api/facturacion/guardar-config/
GET    /api/facturacion/obtener-config/
POST   /api/facturacion/generar-factura-total/{reserva_id}/
POST   /api/facturacion/generar-factura-pasajero/{pasajero_id}/
GET    /api/facturacion/facturas-reserva/{reserva_id}/
GET    /api/facturacion/descargar-pdf/{factura_id}/
```

#### 🆕 Notas de Crédito
```
POST   /api/facturacion/generar-nota-credito-total/{factura_id}/
POST   /api/facturacion/generar-nota-credito-parcial/{factura_id}/
GET    /api/facturacion/notas-credito/
GET    /api/facturacion/notas-credito/{nota_credito_id}/
GET    /api/facturacion/notas-credito-factura/{factura_id}/
GET    /api/facturacion/descargar-pdf-nota-credito/{nota_credito_id}/
```

---

## 🗄️ Base de Datos

### Tablas Principales

**Núcleo:**
- `usuario` - Usuarios del sistema
- `empleado` - Empleados
- `persona` - Personas (polimórfico)
- `persona_fisica` - Personas físicas
- `persona_juridica` - Personas jurídicas

**Paquetes:**
- `paquete` - Paquetes turísticos
- `salida_paquete` - Salidas específicas
- `cupo_habitacion_salida` - Cupos por habitación
- `temporada` - Temporadas
- `historial_precio_paquete` - Historial de precios

**Reservas:**
- `reserva` - Reservas
- `pasajero` - Pasajeros

**Facturación:**
- `empresa` - Empresa emisora (única)
- `establecimiento` - Establecimientos
- `punto_expedicion` - Puntos de expedición
- `timbrado` - Timbrados
- `factura_electronica` - Facturas
- `detalle_factura` - Detalles de factura
- `cliente_facturacion` - Clientes de facturación (terceros)
- 🆕 `nota_credito_electronica` - Notas de crédito
- 🆕 `detalle_nota_credito` - Detalles de NC

**Hoteles:**
- `cadena_hotelera` - Cadenas
- `hotel` - Hoteles
- `habitacion` - Habitaciones

**Otras:**
- `destino`, `ciudad`, `zona_geografica`, `moneda`, `tipo_documento`, `nacionalidad`, etc.

---

## 🔒 Seguridad

✅ **Implementado:**
- Autenticación JWT
- Permisos granulares
- Validaciones de negocio
- Soft deletes (campo `activo`)
- Protección CSRF
- CORS configurado

---

## 📊 Métricas del Proyecto

### Estadísticas de Código

- **26 Apps Django**
- **~15,000 líneas de código Python**
- **150+ modelos de datos**
- **100+ endpoints API**
- **Django Admin completo**

### Funcionalidades Clave

✅ Gestión de Paquetes
✅ Sistema de Reservas
✅ Facturación Electrónica (Global/Individual)
✅ **Notas de Crédito (Nuevo en v1.1.0)**
✅ Gestión de Hoteles
✅ Sistema de Permisos
✅ Multi-moneda
✅ Generación de PDF
✅ API REST completa

---

## 🚀 Próximos Pasos Sugeridos

### Funcionalidades Futuras

1. **Reportes Avanzados**
   - Dashboard con métricas
   - Reportes de ventas
   - Reportes de NC por período
   - Análisis de cancelaciones

2. **Notificaciones**
   - Email automático de facturas
   - Email de NC
   - Notificaciones de cambios de estado

3. **Integración SET**
   - Envío de facturas a la SET
   - Envío de NC a la SET
   - Sincronización automática

4. **Frontend**
   - Tab de Facturas en Detalle de Reserva
   - Modal de generación de NC
   - Dashboard de facturación

5. **Mejoras**
   - Historial de cambios (audit log)
   - Exportación a Excel
   - Integración con sistemas de pago
   - WhatsApp notifications

---

## 📁 Estructura del Proyecto

```
GroupTours/
├── apps/
│   ├── paquete/          # Paquetes turísticos
│   ├── reserva/          # Reservas y pasajeros
│   ├── facturacion/      # Facturas y NC
│   ├── hotel/            # Hoteles y habitaciones
│   ├── usuario/          # Usuarios
│   ├── persona/          # Personas (polimórfico)
│   ├── empleado/         # Empleados
│   ├── rol/              # Roles
│   ├── permiso/          # Permisos
│   └── ... (17 apps más)
├── GroupTours/           # Settings del proyecto
├── media/                # Archivos multimedia
│   ├── facturas/pdf/
│   ├── facturas/notas_credito/pdf/
│   └── logos/
├── docs/                 # Documentación
│   ├── NOTAS_DE_CREDITO.md
│   ├── NOTAS_DE_CREDITO_QUICKSTART.md
│   └── RESUMEN_PROYECTO.md
├── requirements.txt      # Dependencias
├── manage.py
├── README.md
├── CHANGELOG.md
└── CLAUDE.md            # Guía para Claude Code
```

---

## 🛠️ Comandos Útiles

### Desarrollo

```bash
# Iniciar servidor
python manage.py runserver

# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Django shell
python manage.py shell

# Verificar sistema
python manage.py check
```

### Testing

```bash
# Ejecutar tests
python manage.py test

# Tests específicos
python manage.py test apps.facturacion.tests
```

---

## 📚 Documentación Disponible

| Documento | Descripción |
|-----------|-------------|
| [README.md](../README.md) | Instalación y setup |
| [CLAUDE.md](../CLAUDE.md) | Guía del proyecto para Claude Code |
| [CHANGELOG.md](../CHANGELOG.md) | Historial de cambios |
| [NOTAS_DE_CREDITO.md](./NOTAS_DE_CREDITO.md) | Doc completa de NC |
| [NOTAS_DE_CREDITO_QUICKSTART.md](./NOTAS_DE_CREDITO_QUICKSTART.md) | Guía rápida NC |
| [RESUMEN_PROYECTO.md](./RESUMEN_PROYECTO.md) | Este archivo |

---

## 👥 Equipo y Contacto

**Desarrollado para:** GroupTours
**Tecnología:** Django REST Framework
**Versión Actual:** 1.1.0
**Última Actualización:** 2025-11-06

---

## 📜 Licencia

Propiedad de GroupTours. Todos los derechos reservados.

---

**Estado del Proyecto:** ✅ En Desarrollo Activo
**Cobertura de Tests:** 🔄 En progreso
**Documentación:** ✅ Completa
**API:** ✅ Funcional
