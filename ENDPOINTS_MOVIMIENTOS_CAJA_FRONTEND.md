# API Endpoints - Movimientos de Caja para Frontend

## 📋 Resumen

Esta documentación describe todos los endpoints disponibles para gestionar y visualizar **Movimientos de Caja** desde el frontend. Los movimientos se generan automáticamente al registrar pagos (ComprobantePago) cuando el empleado tiene una caja abierta.

---

## 🔗 Endpoints Disponibles

### 1. Listar Movimientos

**Endpoint:**
```
GET /api/arqueo-caja/movimientos/
```

**Autenticación:** Requerida (JWT Token)

**Paginación:** Sí (10 items por página por defecto)

**Filtros Query Parameters:**
- `apertura_caja`: Filtrar por ID de apertura
- `tipo_movimiento`: `ingreso` o `egreso`
- `concepto`: Concepto específico (ej: `venta_efectivo`, `venta_tarjeta`)
- `metodo_pago`: Método de pago utilizado
- `usuario_registro`: ID del empleado que registró
- `comprobante`: ID del comprobante asociado
- `activo`: `true` o `false` (para ver movimientos anulados)
- `page`: Número de página
- `page_size`: Tamaño de página (máx 100)

**Ordenamiento:**
- Por defecto: más recientes primero (`-fecha_hora_movimiento`)

**Request Example:**
```javascript
GET /api/arqueo-caja/movimientos/?apertura_caja=123&tipo_movimiento=ingreso&page=1
```

**Response Example:**
```json

{
  "count": 45,
  "next": "http://api.../movimientos/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "numero_movimiento": "MOV-2025-0001",
      "apertura_caja": 123,
      "apertura_codigo": "APR-2025-0001",
      "caja_nombre": "Caja Principal",
      "comprobante": 456,
      "comprobante_numero": "CPG-2025-0001",
      "tiene_comprobante": true,
      "tipo_movimiento": "ingreso",
      "tipo_movimiento_display": "Ingreso",
      "concepto": "venta_efectivo",
      "concepto_display": "Venta en Efectivo",
      "monto": "300000.00",
      "metodo_pago": "efectivo",
      "metodo_pago_display": "Efectivo",
      "referencia": "CPG-2025-0001",
      "descripcion": "Pago de reserva RSV-2025-0123 - Comprobante CPG-2025-0001",
      "fecha_hora_movimiento": "2025-11-16T10:30:00Z",
      "usuario_registro": 789,
      "usuario_nombre": "Juan Pérez",
      "activo": true
    },
    {
      "id": 2,
      "numero_movimiento": "MOV-2025-0002",
      "apertura_caja": 123,
      "apertura_codigo": "APR-2025-0001",
      "caja_nombre": "Caja Principal",
      "comprobante": 457,
      "comprobante_numero": "CPG-2025-0002",
      "tiene_comprobante": true,
      "tipo_movimiento": "ingreso",
      "tipo_movimiento_display": "Ingreso",
      "concepto": "venta_tarjeta",
      "concepto_display": "Venta con Tarjeta",
      "monto": "500000.00",
      "metodo_pago": "tarjeta_debito",
      "metodo_pago_display": "Tarjeta de Débito",
      "referencia": "CPG-2025-0002",
      "descripcion": "Pago de reserva RSV-2025-0124 - Comprobante CPG-2025-0002",
      "fecha_hora_movimiento": "2025-11-16T11:00:00Z",
      "usuario_registro": 789,
      "usuario_nombre": "Juan Pérez",
      "activo": true
    }
  ]
}
```

**Campos Importantes:**
- `tiene_comprobante`: `true` si fue generado automáticamente por un pago, `false` si es manual
- `comprobante_numero`: Número del comprobante asociado (CPG-XXXX-XXXX)
- `concepto_display`: Nombre legible del concepto
- `descripcion`: Descripción detallada del movimiento

---

### 2. Ver Detalle de Movimiento

**Endpoint:**
```
GET /api/arqueo-caja/movimientos/{id}/
```

**Autenticación:** Requerida (JWT Token)

**Request Example:**
```javascript
GET /api/arqueo-caja/movimientos/1/
```

**Response Example:**
```json
{
  "id": 1,
  "numero_movimiento": "MOV-2025-0001",
  "apertura_caja": {
    "id": 123,
    "codigo_apertura": "APR-2025-0001",
    "caja": {
      "id": 1,
      "nombre": "Caja Principal",
      "numero_caja": "001-001"
    },
    "responsable": {
      "id": 789,
      "codigo_empleado": "EMP001",
      "persona": {
        "nombre": "Juan",
        "apellido": "Pérez"
      }
    },
    "fecha_hora_apertura": "2025-11-16T08:00:00Z",
    "monto_inicial": "500000.00"
  },
  "comprobante": {
    "id": 456,
    "numero_comprobante": "CPG-2025-0001",
    "reserva": {
      "codigo": "RSV-2025-0123"
    }
  },
  "tipo_movimiento": "ingreso",
  "tipo_movimiento_display": "Ingreso",
  "concepto": "venta_efectivo",
  "monto": "300000.00",
  "metodo_pago": "efectivo",
  "metodo_pago_display": "Efectivo",
  "referencia": "CPG-2025-0001",
  "descripcion": "Pago de reserva RSV-2025-0123 - Comprobante CPG-2025-0001",
  "fecha_hora_movimiento": "2025-11-16T10:30:00Z",
  "usuario_registro": {
    "id": 789,
    "codigo_empleado": "EMP001",
    "persona": {
      "nombre": "Juan",
      "apellido": "Pérez"
    }
  },
  "activo": true,
  "fecha_creacion": "2025-11-16T10:30:00Z",
  "fecha_modificacion": "2025-11-16T10:30:00Z"
}
```

---

### 3. Resumen General de Movimientos

**Endpoint:**
```
GET   /
```

**Autenticación:** Requerida (JWT Token)

**Descripción:**
Obtiene estadísticas generales de todos los movimientos de caja del sistema. Útil para dashboards y reportes generales.

**Request Example:**
```javascript
GET /api/arqueo-caja/movimientos/resumen-general/
```

**Response Example:**
```json
[
  {
    "texto": "Total Movimientos",
    "valor": "1234"
  },
  {
    "texto": "Movimientos Inactivos/Anulados",
    "valor": "12"
  },
  {
    "texto": "Total Ingresos (Cantidad)",
    "valor": "1100"
  },
  {
    "texto": "Total Egresos (Cantidad)",
    "valor": "134"
  },
  {
    "texto": "Total Ingresos (Monto)",
    "valor": "Gs 125,000,000"
  },
  {
    "texto": "Total Egresos (Monto)",
    "valor": "Gs 5,000,000"
  },
  {
    "texto": "Balance Neto",
    "valor": "Gs 120,000,000"
  },
  {
    "texto": "Ingresos en Efectivo",
    "valor": "Gs 80,000,000"
  },
  {
    "texto": "Ingresos con Tarjetas",
    "valor": "Gs 35,000,000"
  },
  {
    "texto": "Ingresos por Transferencia",
    "valor": "Gs 10,000,000"
  },
  {
    "texto": "Con Comprobante de Pago",
    "valor": "1150"
  },
  {
    "texto": "Sin Comprobante (Manuales)",
    "valor": "84"
  },
  {
    "texto": "Movimientos Hoy",
    "valor": "45"
  },
  {
    "texto": "Ingresos Hoy",
    "valor": "Gs 5,000,000"
  },
  {
    "texto": "Egresos Hoy",
    "valor": "Gs 200,000"
  },
  {
    "texto": "Nuevos últimos 30 días",
    "valor": "567"
  },
  {
    "texto": "Ingresos últimos 30 días",
    "valor": "Gs 45,000,000"
  }
]
```

**Uso en Frontend:**
```javascript
// Ejemplo de uso en React
function ResumenMovimientos() {
  const [resumen, setResumen] = useState([]);

  useEffect(() => {
    fetch('/api/arqueo-caja/movimientos/resumen-general/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setResumen(data));
  }, []);

  return (
    <div className="row">
      {resumen.map((item, idx) => (
        <div key={idx} className="col-md-3 mb-3">
          <div className="card">
            <div className="card-body">
              <h6 className="text-muted">{item.texto}</h6>
              <h4>{item.valor}</h4>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

### 4. Estadísticas de Movimientos

**Endpoint:**
```
GET /api/arqueo-caja/movimientos/estadisticas/
```

**Autenticación:** Requerida (JWT Token)

**Filtros Query Parameters:**
- `apertura_caja`: ID de apertura (opcional)
- `fecha_desde`: Fecha desde (formato: YYYY-MM-DD)
- `fecha_hasta`: Fecha hasta (formato: YYYY-MM-DD)

**Request Example:**
```javascript
GET /api/arqueo-caja/movimientos/estadisticas/?fecha_desde=2025-11-01&fecha_hasta=2025-11-30
```

**Response Example:**
```json
{
  "por_tipo": [
    {
      "tipo_movimiento": "ingreso",
      "total": "125000000.00",
      "cantidad": 1100
    },
    {
      "tipo_movimiento": "egreso",
      "total": "5000000.00",
      "cantidad": 134
    }
  ],
  "por_metodo": [
    {
      "metodo_pago": "efectivo",
      "total": "80000000.00",
      "cantidad": 650
    },
    {
      "metodo_pago": "tarjeta_debito",
      "total": "20000000.00",
      "cantidad": 280
    },
    {
      "metodo_pago": "tarjeta_credito",
      "total": "15000000.00",
      "cantidad": 100
    },
    {
      "metodo_pago": "transferencia",
      "total": "10000000.00",
      "cantidad": 70
    }
  ],
  "por_concepto": [
    {
      "concepto": "venta_efectivo",
      "tipo_movimiento": "ingreso",
      "total": "80000000.00",
      "cantidad": 650
    },
    {
      "concepto": "venta_tarjeta",
      "tipo_movimiento": "ingreso",
      "total": "35000000.00",
      "cantidad": 380
    },
    {
      "concepto": "transferencia_recibida",
      "tipo_movimiento": "ingreso",
      "total": "10000000.00",
      "cantidad": 70
    },
    {
      "concepto": "devolucion",
      "tipo_movimiento": "egreso",
      "total": "5000000.00",
      "cantidad": 134
    }
  ]
}
```

---

### 5. Crear Movimiento Manual

**Endpoint:**
```
POST /api/arqueo-caja/movimientos/
```

**Autenticación:** Requerida (JWT Token)

**Descripción:**
Permite crear movimientos de caja manuales (que no provienen de un ComprobantePago).

**Request Body:**
```json
{
  "apertura_caja": 123,
  "tipo_movimiento": "egreso",
  "concepto": "retiro_efectivo",
  "monto": "100000.00",
  "metodo_pago": "efectivo",
  "referencia": "RETIRO-001",
  "descripcion": "Retiro para gastos operativos",
  "usuario_registro": 789
}
```

**Conceptos Válidos:**

**Para Ingresos:**
- `venta_efectivo`
- `venta_tarjeta`
- `cobro_cuenta`
- `deposito`
- `transferencia_recibida`
- `ajuste_positivo`
- `otro_ingreso`

**Para Egresos:**
- `pago_proveedor`
- `pago_servicio`
- `gasto_operativo`
- `retiro_efectivo`
- `devolucion`
- `ajuste_negativo`
- `otro_egreso`

**Métodos de Pago Válidos:**
- `efectivo`
- `tarjeta_debito`
- `tarjeta_credito`
- `transferencia`
- `cheque`
- `qr`
- `otro`

**Response:**
```json
{
  "id": 5,
  "numero_movimiento": "MOV-2025-0005",
  "apertura_caja": 123,
  "comprobante": null,
  "tipo_movimiento": "egreso",
  "concepto": "retiro_efectivo",
  "monto": "100000.00",
  "metodo_pago": "efectivo",
  "referencia": "RETIRO-001",
  "descripcion": "Retiro para gastos operativos",
  "fecha_hora_movimiento": "2025-11-16T14:30:00Z",
  "usuario_registro": 789,
  "activo": true
}
```

**Validaciones:**
- La apertura debe estar abierta
- El monto debe ser mayor a cero
- El concepto debe ser válido según el tipo
- El empleado debe ser el responsable de la apertura

---

## 🎨 Ejemplos de Uso en Frontend

### Tabla de Movimientos (React)

```jsx
import React, { useState, useEffect } from 'react';
import { Badge, Table, Pagination } from 'react-bootstrap';

function TablaMovimientos({ aperturaId = null }) {
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    fetchMovimientos();
  }, [page, aperturaId]);

  const fetchMovimientos = async () => {
    setLoading(true);

    let url = `/api/arqueo-caja/movimientos/?page=${page}`;
    if (aperturaId) {
      url += `&apertura_caja=${aperturaId}`;
    }

    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const data = await response.json();
    setMovimientos(data.results);
    setTotalPages(Math.ceil(data.count / 10));
    setLoading(false);
  };

  const getBadgeColor = (tipo) => {
    return tipo === 'ingreso' ? 'success' : 'danger';
  };

  const formatMonto = (monto, tipo) => {
    const formatted = Number(monto).toLocaleString('es-PY');
    return tipo === 'ingreso' ? `+ Gs. ${formatted}` : `- Gs. ${formatted}`;
  };

  if (loading) {
    return <div>Cargando...</div>;
  }

  return (
    <>
      <Table striped bordered hover responsive>
        <thead>
          <tr>
            <th>Número</th>
            <th>Fecha</th>
            <th>Tipo</th>
            <th>Concepto</th>
            <th>Método</th>
            <th>Monto</th>
            <th>Comprobante</th>
            <th>Usuario</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {movimientos.map(mov => (
            <tr key={mov.id} className={!mov.activo ? 'table-secondary' : ''}>
              <td>
                <small className="text-muted">{mov.numero_movimiento}</small>
              </td>
              <td>
                {new Date(mov.fecha_hora_movimiento).toLocaleString('es-PY')}
              </td>
              <td>
                <Badge bg={getBadgeColor(mov.tipo_movimiento)}>
                  {mov.tipo_movimiento_display}
                </Badge>
              </td>
              <td>
                <small>{mov.concepto_display}</small>
              </td>
              <td>
                <small>{mov.metodo_pago_display}</small>
              </td>
              <td className={mov.tipo_movimiento === 'ingreso' ? 'text-success' : 'text-danger'}>
                <strong>{formatMonto(mov.monto, mov.tipo_movimiento)}</strong>
              </td>
              <td>
                {mov.tiene_comprobante ? (
                  <a href={`/comprobantes/${mov.comprobante}`}>
                    {mov.comprobante_numero}
                  </a>
                ) : (
                  <Badge bg="secondary">Manual</Badge>
                )}
              </td>
              <td>
                <small>{mov.usuario_nombre}</small>
              </td>
              <td>
                {mov.activo ? (
                  <Badge bg="success">Activo</Badge>
                ) : (
                  <Badge bg="secondary">Anulado</Badge>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      <Pagination>
        <Pagination.Prev
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
        />
        <Pagination.Item active>{page}</Pagination.Item>
        <Pagination.Next
          onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          disabled={page === totalPages}
        />
      </Pagination>
    </>
  );
}

export default TablaMovimientos;
```

---

### Filtros Avanzados (React)

```jsx
function FiltrosMovimientos({ onFilter }) {
  const [filtros, setFiltros] = useState({
    tipo_movimiento: '',
    metodo_pago: '',
    activo: 'true',
    fecha_desde: '',
    fecha_hasta: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onFilter(filtros);
  };

  return (
    <form onSubmit={handleSubmit} className="row g-3 mb-4">
      <div className="col-md-3">
        <label className="form-label">Tipo de Movimiento</label>
        <select
          className="form-select"
          value={filtros.tipo_movimiento}
          onChange={e => setFiltros({...filtros, tipo_movimiento: e.target.value})}
        >
          <option value="">Todos</option>
          <option value="ingreso">Ingresos</option>
          <option value="egreso">Egresos</option>
        </select>
      </div>

      <div className="col-md-3">
        <label className="form-label">Método de Pago</label>
        <select
          className="form-select"
          value={filtros.metodo_pago}
          onChange={e => setFiltros({...filtros, metodo_pago: e.target.value})}
        >
          <option value="">Todos</option>
          <option value="efectivo">Efectivo</option>
          <option value="tarjeta_debito">Tarjeta Débito</option>
          <option value="tarjeta_credito">Tarjeta Crédito</option>
          <option value="transferencia">Transferencia</option>
        </select>
      </div>

      <div className="col-md-2">
        <label className="form-label">Fecha Desde</label>
        <input
          type="date"
          className="form-control"
          value={filtros.fecha_desde}
          onChange={e => setFiltros({...filtros, fecha_desde: e.target.value})}
        />
      </div>

      <div className="col-md-2">
        <label className="form-label">Fecha Hasta</label>
        <input
          type="date"
          className="form-control"
          value={filtros.fecha_hasta}
          onChange={e => setFiltros({...filtros, fecha_hasta: e.target.value})}
        />
      </div>

      <div className="col-md-2 d-flex align-items-end">
        <button type="submit" className="btn btn-primary w-100">
          Filtrar
        </button>
      </div>
    </form>
  );
}
```

---

### Gráfico de Movimientos (Chart.js)

```jsx
import { Line } from 'react-chartjs-2';

function GraficoMovimientos() {
  const [estadisticas, setEstadisticas] = useState(null);

  useEffect(() => {
    fetch('/api/arqueo-caja/movimientos/estadisticas/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setEstadisticas(data));
  }, []);

  if (!estadisticas) return <div>Cargando...</div>;

  const chartData = {
    labels: estadisticas.por_metodo.map(m => m.metodo_pago),
    datasets: [{
      label: 'Monto por Método de Pago',
      data: estadisticas.por_metodo.map(m => m.total),
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      borderColor: 'rgba(75, 192, 192, 1)',
      borderWidth: 1
    }]
  };

  return (
    <div className="card">
      <div className="card-body">
        <h5>Ingresos por Método de Pago</h5>
        <Line data={chartData} />
      </div>
    </div>
  );
}
```

---

## 🔐 Permisos y Seguridad

### Restricciones
- Solo usuarios autenticados pueden acceder
- Los movimientos manuales solo pueden ser creados por el responsable de la apertura
- No se pueden editar movimientos generados automáticamente (tienen comprobante)
- Solo se pueden anular movimientos si se anula el comprobante asociado

### Buenas Prácticas
- Siempre filtrar por `activo=true` para listados normales
- Usar `activo=false` solo para auditorías
- Verificar permisos antes de permitir crear movimientos manuales
- Validar que la apertura esté abierta antes de crear movimientos

---

## 📱 Responsive Design

### Mobile-First
```jsx
// Versión mobile de la tabla
function TablaMovimientosMobile({ movimientos }) {
  return (
    <div className="d-md-none">
      {movimientos.map(mov => (
        <div key={mov.id} className="card mb-2">
          <div className="card-body">
            <div className="d-flex justify-content-between">
              <div>
                <Badge bg={mov.tipo_movimiento === 'ingreso' ? 'success' : 'danger'}>
                  {mov.tipo_movimiento_display}
                </Badge>
                <p className="mb-0">{mov.concepto_display}</p>
                <small className="text-muted">{mov.numero_movimiento}</small>
              </div>
              <div className="text-end">
                <h5 className={mov.tipo_movimiento === 'ingreso' ? 'text-success' : 'text-danger'}>
                  {formatMonto(mov.monto)}
                </h5>
                <small>{new Date(mov.fecha_hora_movimiento).toLocaleDateString()}</small>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## ✅ Checklist de Implementación

- [ ] Crear componente de tabla de movimientos
- [ ] Implementar filtros avanzados
- [ ] Agregar paginación
- [ ] Mostrar badge de estado (activo/anulado)
- [ ] Diferenciar visualmente ingresos vs egresos
- [ ] Vincular con comprobantes de pago
- [ ] Agregar vista de resumen general
- [ ] Implementar gráficos de estadísticas
- [ ] Agregar versión mobile responsive
- [ ] Probar todos los filtros

---

## 🎯 Resumen

Con estos endpoints puedes:
1. **Listar** todos los movimientos con filtros avanzados
2. **Ver detalles** de movimientos individuales
3. **Obtener resumen general** con estadísticas
4. **Generar reportes** por tipo, método de pago y concepto
5. **Crear movimientos manuales** cuando sea necesario

Todos los movimientos generados automáticamente desde ComprobantePago estarán disponibles en estas vistas.
