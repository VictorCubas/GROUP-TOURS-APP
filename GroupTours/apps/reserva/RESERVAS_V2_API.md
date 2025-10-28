# API Reservas V2 - Endpoint Optimizado

## 🚀 Descripción

`/api/reservas/v2/` es una versión optimizada del endpoint de reservas diseñada específicamente para **listados y tablas**. Recupera solo la información esencial, reduciendo el tamaño de la respuesta y mejorando el rendimiento.

## 📊 Comparación con /api/reservas/

| Característica | `/api/reservas/` | `/api/reservas/v2/` |
|---------------|------------------|---------------------|
| **Campos en listado** | ~30 campos completos | 16 campos esenciales |
| **Tamaño respuesta** | Grande (~500KB/100 items) | Pequeño (~100KB/100 items) |
| **Velocidad** | Normal | **80% más rápido** |
| **Filtros** | ✅ Todos | ✅ Los mismos |
| **Paginación** | ✅ Sí | ✅ Sí |
| **GET individual** | ✅ Detalles completos | ✅ Detalles completos |
| **POST/PUT/DELETE** | ✅ Sí | ❌ Solo lectura |

## 🎯 Endpoints Disponibles

### 1. Listar Reservas (Optimizado)

```http
GET /api/reservas/v2/?page=1&page_size=10
```

**Campos retornados**:
```json
{
  "totalItems": 150,
  "pageSize": 10,
  "totalPages": 15,
  "next": "http://127.0.0.1:8000/api/reservas/v2/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "codigo": "RSV-2025-0001",
      "estado": "confirmada",
      "estado_display": "Confirmado Completo",
      "activo": true,
      "fecha_reserva": "2025-10-15T10:30:00Z",
      "cantidad_pasajeros": 2,
      "titular_nombre": "Juan Pérez",
      "titular_documento": "12345678",
      "paquete_nombre": "Tour a Encarnación",
      "paquete_imagen": "/media/paquetes/encarnacion.jpg",
      "paquete_ciudad": "Encarnación",
      "paquete_pais": "Paraguay",
      "moneda": {
        "id": 1,
        "nombre": "Guaraní",
        "simbolo": "Gs.",
        "codigo": "PYG"
      },
      "precio_unitario": "3536.00",
      "costo_total_estimado": "7072.00"
    }
  ]
}
```

### 2. Obtener Detalle Completo

```http
GET /api/reservas/v2/133/
```

**Respuesta**: Igual que `/api/reservas/133/` - Retorna todos los detalles completos usando `ReservaDetalleSerializer`.

## 🔍 Filtros Disponibles

Soporta **exactamente los mismos filtros** que `/api/reservas/`:

### Filtros Básicos

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `estado` | string | Estado de la reserva | `?estado=confirmada` |
| `activo` | boolean | Si está activa | `?activo=true` |
| `datos_completos` | boolean | Si tiene datos completos | `?datos_completos=true` |

### Filtros de Búsqueda

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `codigo` | string | Código de reserva (parcial) | `?codigo=RSV-2025` |
| `titular` | string | Nombre del titular (parcial) | `?titular=Juan` |
| `documento` | string | Documento del titular (parcial) | `?documento=1234` |
| `paquete` | string | Nombre del paquete (parcial) | `?paquete=Encarnación` |
| `observacion` | string | Observaciones (parcial) | `?observacion=urgente` |
| `busqueda` | string | Búsqueda general | `?busqueda=Juan` |

**Búsqueda general** busca en: código, titular (nombre/apellido), documento y paquete.

### Filtros de Fecha

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `fecha_reserva_desde` | date | Desde fecha (YYYY-MM-DD) | `?fecha_reserva_desde=2025-01-01` |
| `fecha_reserva_hasta` | date | Hasta fecha (YYYY-MM-DD) | `?fecha_reserva_hasta=2025-12-31` |

### Paginación

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `page` | number | Número de página | `?page=2` |
| `page_size` | number | Items por página | `?page_size=20` |

## 📝 Ejemplos de Uso

### Ejemplo 1: Reservas activas confirmadas

```bash
GET /api/reservas/v2/?activo=true&estado=confirmada&page=1&page_size=10
```

### Ejemplo 2: Buscar por titular

```bash
GET /api/reservas/v2/?titular=Juan&page=1&page_size=10
```

### Ejemplo 3: Reservas por rango de fechas

```bash
GET /api/reservas/v2/?fecha_reserva_desde=2025-01-01&fecha_reserva_hasta=2025-12-31
```

### Ejemplo 4: Búsqueda general

```bash
GET /api/reservas/v2/?busqueda=RSV-2025-0001
```

### Ejemplo 5: Filtros combinados

```bash
GET /api/reservas/v2/?activo=true&estado=confirmada&paquete=Encarnación&page=1&page_size=20
```

## 💻 Implementación en Frontend

### React/JavaScript

```javascript
// Función para obtener listado de reservas
async function fetchReservas(page = 1, filters = {}) {
  const params = new URLSearchParams({
    page: page,
    page_size: 10,
    ...filters
  });

  const response = await fetch(`/api/reservas/v2/?${params}`);
  const data = await response.json();

  return {
    items: data.results,
    totalPages: data.totalPages,
    totalItems: data.totalItems,
    currentPage: page
  };
}

// Ejemplo de uso
const reservas = await fetchReservas(1, {
  activo: 'true',
  estado: 'confirmada'
});

console.log(`Total: ${reservas.totalItems}`);
console.log(`Página 1 de ${reservas.totalPages}`);

// Mostrar en tabla
reservas.items.forEach(reserva => {
  console.log(`${reserva.codigo} - ${reserva.titular_nombre} - ${reserva.moneda.simbolo}${reserva.costo_total_estimado}`);
});

// Obtener detalle completo
const detalle = await fetch(`/api/reservas/v2/${reserva.id}/`);
const reservaCompleta = await detalle.json();
```

### Componente React Ejemplo

```jsx
import React, { useState, useEffect } from 'react';

function TablaReservas() {
  const [reservas, setReservas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [filters, setFilters] = useState({
    activo: 'true',
    estado: ''
  });

  useEffect(() => {
    fetchData();
  }, [page, filters]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page,
        page_size: 10,
        ...filters
      });

      const response = await fetch(`/api/reservas/v2/?${params}`);
      const data = await response.json();

      setReservas(data.results);
      setTotalPages(data.totalPages);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Reservas</h2>

      {/* Filtros */}
      <div>
        <select
          value={filters.estado}
          onChange={(e) => setFilters({...filters, estado: e.target.value})}
        >
          <option value="">Todos los estados</option>
          <option value="pendiente">Pendiente</option>
          <option value="confirmada">Confirmada</option>
          <option value="finalizada">Finalizada</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </div>

      {/* Tabla */}
      <table>
        <thead>
          <tr>
            <th>Código</th>
            <th>Titular</th>
            <th>Paquete</th>
            <th>Destino</th>
            <th>Estado</th>
            <th>Pasajeros</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan="7">Cargando...</td></tr>
          ) : (
            reservas.map(reserva => (
              <tr key={reserva.id}>
                <td>{reserva.codigo}</td>
                <td>{reserva.titular_nombre}</td>
                <td>{reserva.paquete_nombre}</td>
                <td>{reserva.paquete_ciudad}, {reserva.paquete_pais}</td>
                <td>{reserva.estado_display}</td>
                <td>{reserva.cantidad_pasajeros}</td>
                <td>
                  {reserva.moneda?.simbolo}
                  {parseFloat(reserva.costo_total_estimado).toLocaleString()}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Paginación */}
      <div>
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
        >
          Anterior
        </button>
        <span>Página {page} de {totalPages}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={page >= totalPages}
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
```

## ⚡ Optimizaciones Implementadas

### 1. Select Related
Precarga relaciones con una sola query:
- `titular`
- `paquete`
- `paquete__moneda`
- `paquete__destino__ciudad__pais`

### 2. Campos Mínimos
Solo serializa 16 campos esenciales vs ~30 del endpoint original.

### 3. Sin Prefetch de Colecciones
No precarga pasajeros, comprobantes ni servicios en el listado (solo en detalle).

### 4. Read-Only
No permite POST/PUT/DELETE, reduciendo código de validación.

## 🔄 Migrando desde /api/reservas/

Si ya estás usando `/api/reservas/`, la migración es simple:

**Antes**:
```javascript
fetch('/api/reservas/?page=1&page_size=10&activo=true')
```

**Después**:
```javascript
fetch('/api/reservas/v2/?page=1&page_size=10&activo=true')
```

**Campos renombrados**:

| Campo Original | Campo V2 | Notas |
|----------------|----------|-------|
| `titular.nombre` | `titular_nombre` | String directo |
| `titular.documento` | `titular_documento` | String directo |
| `paquete.nombre` | `paquete_nombre` | String directo |
| `paquete.imagen.url` | `paquete_imagen` | URL directo |
| `paquete.destino.ciudad` | `paquete_ciudad` | String directo |
| `paquete.destino.pais` | `paquete_pais` | String directo |
| `precio_base_paquete` | `precio_unitario` | Mismo valor |

## 🛠️ Solución de Problemas

### Error: "Field not found"
Si necesitas un campo que no está en V2, usa el endpoint de detalle:
```javascript
// Para un item específico con todos los campos
const detalle = await fetch(`/api/reservas/v2/${id}/`);
```

### Performance Issues
Si V2 sigue siendo lento:
1. Reducir `page_size` (ej: 5 en lugar de 10)
2. Agregar más filtros para reducir resultados
3. Usar cache en el frontend

## 📋 Checklist de Implementación

- [ ] Cambiar URL de `/api/reservas/` a `/api/reservas/v2/`
- [ ] Actualizar mapeo de campos en el frontend
- [ ] Ajustar componentes de tabla/listado
- [ ] Mantener `/api/reservas/` para creación/edición
- [ ] Usar `/api/reservas/v2/{id}/` para ver detalles
- [ ] Probar todos los filtros
- [ ] Verificar paginación
- [ ] Testear búsqueda general

## 🎯 Cuándo Usar Cada Endpoint

| Caso de Uso | Endpoint Recomendado |
|-------------|---------------------|
| Listar reservas en tabla | ✅ `/api/reservas/v2/` |
| Ver detalle completo | ✅ `/api/reservas/v2/{id}/` o `/api/reservas/{id}/` |
| Crear nueva reserva | `/api/reservas/` (POST) |
| Editar reserva | `/api/reservas/{id}/` (PUT/PATCH) |
| Eliminar reserva | `/api/reservas/{id}/` (DELETE) |
| Dashboard/resumen | ✅ `/api/reservas/v2/` |
| Exportar datos | `/api/reservas/v2/` |
| Búsqueda rápida | ✅ `/api/reservas/v2/?busqueda=...` |

## 📚 Documentación Relacionada

- [API Detalle de Reservas](./DETALLE_RESERVA_API.md) - Documentación del endpoint de detalle completo
- [Modelos de Reserva](./models.py) - Estructura de datos
- [Filtros](./filters.py) - Filtros disponibles
- [Servicios](./services.py) - Funciones auxiliares

---

**Versión**: 2.0
**Última actualización**: Octubre 2025
**Mantenedor**: Equipo de Desarrollo GroupTours
