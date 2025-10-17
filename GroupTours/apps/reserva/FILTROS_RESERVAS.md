# 🔍 Filtros Disponibles para Reservas

## API Endpoint
```
GET /api/reservas/
```

## 📋 Filtros Disponibles

### **1. Filtros de Estado**

#### `estado` - Estado de la reserva
```
GET /api/reservas/?estado=pendiente
GET /api/reservas/?estado=confirmada
GET /api/reservas/?estado=finalizada
GET /api/reservas/?estado=cancelada
```

**Valores posibles:**
- `pendiente` - Sin pago o pago insuficiente
- `confirmada` - Seña pagada, cupo asegurado
- `finalizada` - Pago total completo
- `cancelada` - Reserva cancelada

---

#### `datos_completos` - Estado de los datos de pasajeros
```
GET /api/reservas/?datos_completos=true
GET /api/reservas/?datos_completos=false
```

**Valores posibles:**
- `true` - Todos los pasajeros están registrados
- `false` - Faltan datos de pasajeros

---

### **2. Combinación de Filtros** (✨ Nuevo)

#### Confirmadas sin datos completos (requieren atención)
```
GET /api/reservas/?estado=confirmada&datos_completos=false
```

#### Confirmadas listas para viajar
```
GET /api/reservas/?estado=confirmada&datos_completos=true
```

#### Finalizadas sin datos completos (casos edge)
```
GET /api/reservas/?estado=finalizada&datos_completos=false
```

---

### **3. Filtros de Búsqueda**

#### `titular` - Por nombre del titular
```
GET /api/reservas/?titular=juan
```

#### `paquete` - Por nombre del paquete
```
GET /api/reservas/?paquete=cancun
```

#### `codigo` - Por código de reserva
```
GET /api/reservas/?codigo=RSV-2025-001
```

#### `documento` - Por documento del titular
```
GET /api/reservas/?documento=12345678
```

#### `busqueda` - Búsqueda general (código, titular, documento, paquete)
```
GET /api/reservas/?busqueda=juan
```

---

### **4. Filtros de Fecha**

#### `fecha_reserva_desde` - Desde fecha
```
GET /api/reservas/?fecha_reserva_desde=2025-01-01
```

#### `fecha_reserva_hasta` - Hasta fecha
```
GET /api/reservas/?fecha_reserva_hasta=2025-12-31
```

#### Rango de fechas
```
GET /api/reservas/?fecha_reserva_desde=2025-01-01&fecha_reserva_hasta=2025-12-31
```

---

### **5. Otros Filtros**

#### `activo` - Reservas activas/inactivas
```
GET /api/reservas/?activo=true
GET /api/reservas/?activo=false
```

#### `observacion` - Por texto en observaciones
```
GET /api/reservas/?observacion=urgente
```

---

## 🎯 Ejemplos de Uso Combinado

### Dashboard de atención al cliente
```
# Reservas que requieren completar datos
GET /api/reservas/?page=1&page_size=10&estado=confirmada&datos_completos=false&activo=true
```

### Reporte de reservas finalizadas del mes
```
GET /api/reservas/?estado=finalizada&fecha_reserva_desde=2025-01-01&fecha_reserva_hasta=2025-01-31
```

### Buscar reserva por documento del titular
```
GET /api/reservas/?documento=12345678&activo=true
```

### Reservas confirmadas listas para facturar
```
GET /api/reservas/?estado=confirmada&datos_completos=true
```

---

## 📊 Respuesta del API

```json
{
  "totalItems": 100,
  "pageSize": 10,
  "totalPages": 10,
  "next": "http://localhost:8000/api/reservas/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "codigo": "RSV-2025-001",
      "estado": "confirmada",
      "datos_completos": false,
      "estado_display": "Confirmada - Faltan datos de pasajeros",
      "titular": {
        "id": 1,
        "nombre": "Juan",
        "apellido": "Pérez",
        "documento": "12345678"
      },
      "paquete": {
        "id": 1,
        "nombre": "Cancún 5 días"
      },
      "cantidad_pasajeros": 2,
      "pasajeros_cargados": 1,
      "monto_pagado": "500.00",
      "costo_total_estimado": "5000.00",
      "seña_total": "500.00",
      // ... otros campos
    }
  ]
}
```

---

## 🔔 Casos de Uso Recomendados

### **Alertas en Dashboard**
```javascript
// Obtener reservas que requieren atención
fetch('/api/reservas/?estado=confirmada&datos_completos=false&activo=true')
  .then(res => res.json())
  .then(data => {
    const badge = data.totalItems;
    // Mostrar badge con cantidad de reservas pendientes
  });
```

### **Vista de Administración**
```javascript
// Filtrar por estado + paginación
const url = `/api/reservas/?page=${page}&page_size=10&estado=${estadoSeleccionado}&datos_completos=${datosCompletos}&activo=true`;
```

### **Búsqueda Rápida**
```javascript
// Búsqueda general
const url = `/api/reservas/?busqueda=${searchTerm}&activo=true`;
```

---

## ✅ Ventajas del Nuevo Sistema

1. **Filtros eficientes en BD** - No calcula en memoria
2. **Paginación correcta** - Filtra antes de paginar
3. **Combinación flexible** - Múltiples filtros simultáneos
4. **Performance optimizada** - Queries indexadas
5. **UI/UX mejorada** - Estados claros y descriptivos
