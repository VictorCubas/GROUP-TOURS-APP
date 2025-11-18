# Guía de Integración Frontend - Pagos y Movimientos de Caja

## Resumen

Esta guía describe cómo integrar la funcionalidad de pagos con movimientos de caja desde el frontend. El sistema ahora genera automáticamente movimientos de caja cuando se registran pagos, siempre que el empleado tenga una caja abierta.

---

## Endpoints Disponibles

### 1. Verificar Estado de Caja del Empleado

**Endpoint:**
```
GET /api/arqueo-caja/aperturas/tengo-caja-abierta/
```

**Autenticación:** Requerida (JWT Token)

**Descripción:**
Verifica si el empleado autenticado tiene una caja abierta y devuelve información detallada sobre el estado actual.

**Response con Caja Abierta:**
```json
{
  "tiene_caja_abierta": true,
  "apertura_id": 123,
  "codigo_apertura": "APR-2025-0001",
  "caja_id": 1,
  "caja_nombre": "Caja Principal",
  "fecha_hora_apertura": "2025-11-16T08:00:00Z",
  "monto_inicial": "500000.00",
  "monto_inicial_alternativo": "71.43",
  "saldo_actual": "1500000.00",
  "total_ingresos": "1200000.00",
  "total_egresos": "200000.00",
  "cantidad_movimientos": 15,
  "notificacion": "Caja activa con 15 movimiento(s) registrado(s)."
}
```

**Response sin Caja Abierta:**
```json
{
  "tiene_caja_abierta": false,
  "notificacion": "No tienes una caja abierta. Los pagos se registrarán sin movimiento de caja."
}
```

**Campos Importantes:**
- `tiene_caja_abierta`: Indica si el empleado puede generar movimientos de caja
- `saldo_actual`: Saldo en tiempo real de la caja
- `total_ingresos`: Total de ingresos desde la apertura
- `total_egresos`: Total de egresos desde la apertura
- `cantidad_movimientos`: Cantidad de movimientos registrados
- `notificacion`: Mensaje informativo para mostrar al usuario

---

### 2. Registrar Comprobante de Pago

**Endpoint:**
```
POST /api/comprobantes/
```

**Autenticación:** Requerida (JWT Token)

**Body:**
```json
{
  "reserva": 456,
  "tipo": "sena",
  "monto": "300000.00",
  "metodo_pago": "efectivo",
  "empleado": 789,
  "referencia": "REF123456",
  "observaciones": "Pago inicial del cliente"
}
```

**Response:**
```json
{
  "id": 1234,
  "numero_comprobante": "CPG-2025-0001",
  "reserva": 456,
  "tipo": "sena",
  "monto": "300000.00",
  "metodo_pago": "efectivo",
  "empleado": 789,
  "fecha_pago": "2025-11-16T10:30:00Z",
  "activo": true,
  "pdf_generado": "/media/comprobantes/pdf/comprobante_CPG-2025-0001.pdf"
}
```

**Comportamiento Automático:**
- Si el empleado tiene caja abierta → se crea automáticamente un MovimientoCaja
- Si el empleado NO tiene caja abierta → el pago se registra igual, pero sin movimiento

**Tipos de Comprobante:**
- `sena`: Seña/Anticipo
- `pago_parcial`: Pago Parcial
- `pago_total`: Pago Total
- `devolucion`: Devolución (genera egreso)

**Métodos de Pago:**
- `efectivo`: Efectivo
- `tarjeta_debito`: Tarjeta de Débito
- `tarjeta_credito`: Tarjeta de Crédito
- `transferencia`: Transferencia Bancaria
- `cheque`: Cheque
- `qr`: Pago QR
- `otro`: Otro

---

### 3. Listar Movimientos de Caja

**Endpoint:**
```
GET /api/arqueo-caja/movimientos/?apertura_caja={apertura_id}
```

**Autenticación:** Requerida (JWT Token)

**Query Parameters:**
- `apertura_caja`: ID de la apertura (filtro)
- `tipo_movimiento`: `ingreso` o `egreso` (filtro)
- `concepto`: Concepto del movimiento (filtro)
- `comprobante`: ID del comprobante asociado (filtro)
- `activo`: `true` o `false` (filtro)

**Response:**
```json
{
  "count": 25,
  "next": "http://api.../movimientos/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "numero_movimiento": "MOV-2025-0001",
      "apertura_caja": {
        "id": 123,
        "codigo_apertura": "APR-2025-0001",
        "caja_nombre": "Caja Principal"
      },
      "tipo_movimiento": "ingreso",
      "concepto": "venta_efectivo",
      "monto": "300000.00",
      "metodo_pago": "efectivo",
      "referencia": "CPG-2025-0001",
      "descripcion": "Pago de reserva RSV-2025-0123 - Comprobante CPG-2025-0001",
      "comprobante": {
        "id": 1234,
        "numero_comprobante": "CPG-2025-0001"
      },
      "usuario_registro": {
        "id": 789,
        "nombre_completo": "Juan Pérez"
      },
      "fecha_hora_movimiento": "2025-11-16T10:30:00Z",
      "activo": true
    }
  ]
}
```

---

## Flujo de Trabajo Recomendado para el Frontend

### 1. Al Cargar la Pantalla de Pagos

```javascript
// Verificar estado de caja del empleado
async function verificarEstadoCaja() {
  try {
    const response = await fetch('/api/arqueo-caja/aperturas/tengo-caja-abierta/', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const data = await response.json();

    if (data.tiene_caja_abierta) {
      // Mostrar badge verde: "Caja abierta"
      mostrarIndicadorCajaAbierta({
        cajaName: data.caja_nombre,
        saldo: data.saldo_actual,
        movimientos: data.cantidad_movimientos
      });
    } else {
      // Mostrar alerta informativa
      mostrarAlerta({
        tipo: 'info',
        mensaje: data.notificacion,
        accion: 'Abrir Caja'
      });
    }

    return data;
  } catch (error) {
    console.error('Error verificando estado de caja:', error);
  }
}
```

### 2. Al Registrar un Pago

```javascript
async function registrarPago(datosComprobante) {
  try {
    // Registrar el comprobante
    const response = await fetch('/api/comprobantes/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(datosComprobante)
    });

    if (response.ok) {
      const comprobante = await response.json();

      // Actualizar estado de caja (refrescar saldo)
      const estadoCaja = await verificarEstadoCaja();

      // Mostrar mensaje de éxito
      if (estadoCaja.tiene_caja_abierta) {
        mostrarMensaje({
          tipo: 'success',
          titulo: 'Pago registrado exitosamente',
          mensaje: `Comprobante ${comprobante.numero_comprobante} creado. Movimiento de caja generado automáticamente.`
        });
      } else {
        mostrarMensaje({
          tipo: 'warning',
          titulo: 'Pago registrado sin movimiento de caja',
          mensaje: `Comprobante ${comprobante.numero_comprobante} creado. No tienes caja abierta.`
        });
      }

      return comprobante;
    }
  } catch (error) {
    console.error('Error registrando pago:', error);
    mostrarError('Error al registrar el pago');
  }
}
```

### 3. Componente de Indicador de Estado de Caja

```jsx
// React Component Example
function IndicadorEstadoCaja({ estadoCaja }) {
  if (!estadoCaja) return null;

  if (estadoCaja.tiene_caja_abierta) {
    return (
      <div className="alert alert-success d-flex align-items-center">
        <i className="bi bi-cash-coin me-2"></i>
        <div className="flex-grow-1">
          <strong>{estadoCaja.caja_nombre}</strong> - Abierta
          <br />
          <small>
            Saldo: Gs. {formatNumber(estadoCaja.saldo_actual)} |
            Movimientos: {estadoCaja.cantidad_movimientos}
          </small>
        </div>
        <button
          className="btn btn-sm btn-outline-success"
          onClick={() => verDetallesCaja(estadoCaja.apertura_id)}
        >
          Ver detalles
        </button>
      </div>
    );
  }

  return (
    <div className="alert alert-warning d-flex align-items-center">
      <i className="bi bi-exclamation-triangle me-2"></i>
      <div className="flex-grow-1">
        {estadoCaja.notificacion}
      </div>
      <button
        className="btn btn-sm btn-warning"
        onClick={() => navegarAbrirCaja()}
      >
        Abrir Caja
      </button>
    </div>
  );
}
```

---

## Indicadores Visuales Recomendados

### 1. Badge de Estado de Caja (Header/Navbar)

```html
<!-- Con caja abierta -->
<span class="badge bg-success">
  <i class="bi bi-cash-coin"></i>
  Caja: Caja Principal (Gs. 1,500,000)
</span>

<!-- Sin caja abierta -->
<span class="badge bg-warning">
  <i class="bi bi-exclamation-triangle"></i>
  Sin caja abierta
</span>
```

### 2. Alert Informativo en Formulario de Pagos

```html
<!-- Con caja abierta -->
<div class="alert alert-info alert-dismissible fade show" role="alert">
  <i class="bi bi-info-circle"></i>
  <strong>Información:</strong> Los pagos se registrarán automáticamente como movimientos de caja.
  <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>

<!-- Sin caja abierta -->
<div class="alert alert-warning alert-dismissible fade show" role="alert">
  <i class="bi bi-exclamation-triangle"></i>
  <strong>Atención:</strong> No tienes una caja abierta. Los pagos se registrarán sin movimiento de caja.
  <a href="/cajas/abrir" class="alert-link">Abrir caja ahora</a>
  <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
```

### 3. Toast de Confirmación

```javascript
function mostrarToastPagoRegistrado(comprobante, tieneCajaAbierta) {
  const mensaje = tieneCajaAbierta
    ? `✅ Pago ${comprobante.numero_comprobante} registrado. Movimiento de caja generado.`
    : `⚠️ Pago ${comprobante.numero_comprobante} registrado sin movimiento de caja.`;

  mostrarToast({
    tipo: tieneCajaAbierta ? 'success' : 'warning',
    mensaje: mensaje,
    duracion: 5000
  });
}
```

---

## Validaciones en el Frontend

### 1. Antes de Registrar un Pago

```javascript
async function validarAntesDeRegistrarPago() {
  const estadoCaja = await verificarEstadoCaja();

  if (!estadoCaja.tiene_caja_abierta) {
    const confirmar = await mostrarConfirmacion({
      titulo: 'Sin caja abierta',
      mensaje: 'No tienes una caja abierta. ¿Deseas continuar registrando el pago sin movimiento de caja?',
      botones: {
        confirmar: 'Sí, continuar',
        cancelar: 'No, abrir caja primero'
      }
    });

    if (!confirmar) {
      // Redirigir a abrir caja
      navegarAbrirCaja();
      return false;
    }
  }

  return true;
}
```

### 2. Mostrar Saldo en Tiempo Real

```javascript
// Componente que se actualiza automáticamente
function SaldoCajaEnVivo() {
  const [saldo, setSaldo] = useState(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      const estado = await verificarEstadoCaja();
      if (estado.tiene_caja_abierta) {
        setSaldo(estado.saldo_actual);
      }
    }, 30000); // Actualizar cada 30 segundos

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card">
      <div className="card-body">
        <h6>Saldo Actual</h6>
        <h3>Gs. {formatNumber(saldo)}</h3>
      </div>
    </div>
  );
}
```

---

## Manejo de Errores

### Errores Comunes

1. **Usuario sin empleado asociado**
```json
{
  "tiene_caja_abierta": false,
  "error": "Usuario no tiene empleado asociado"
}
```
**Solución:** Mostrar mensaje al usuario para que contacte al administrador.

2. **Token expirado**
```json
{
  "detail": "Token has expired"
}
```
**Solución:** Redirigir al login.

3. **Error al crear comprobante**
```json
{
  "error": "Error creating payment voucher",
  "details": {...}
}
```
**Solución:** Mostrar mensaje de error y permitir reintentar.

---

## Mapeo de Métodos de Pago a Conceptos

El frontend no necesita preocuparse por el mapeo, pero es útil saber cómo se categorizan:

| Método de Pago | Concepto en MovimientoCaja | Tipo |
|----------------|---------------------------|------|
| efectivo | venta_efectivo | ingreso |
| tarjeta_debito | venta_tarjeta | ingreso |
| tarjeta_credito | venta_tarjeta | ingreso |
| transferencia | transferencia_recibida | ingreso |
| cheque | otro_ingreso | ingreso |
| qr | otro_ingreso | ingreso |
| otro | otro_ingreso | ingreso |
| (devolución) | devolucion | egreso |

---

## Reporte de Movimientos (Dashboard)

### Endpoint para Resumen de Apertura

```
GET /api/arqueo-caja/aperturas/{apertura_id}/resumen/
```

**Response:**
```json
{
  "apertura": {
    "id": 123,
    "codigo_apertura": "APR-2025-0001",
    "caja_nombre": "Caja Principal",
    "fecha_hora_apertura": "2025-11-16T08:00:00Z",
    "monto_inicial": "500000.00"
  },
  "movimientos": [
    {
      "numero_movimiento": "MOV-2025-0001",
      "tipo_movimiento": "ingreso",
      "monto": "300000.00",
      "concepto": "venta_efectivo",
      "fecha_hora_movimiento": "2025-11-16T10:30:00Z"
    }
  ],
  "totales": {
    "monto_inicial": "500000.00",
    "total_ingresos": "1200000.00",
    "total_egresos": "200000.00",
    "saldo_calculado": "1500000.00",
    "cantidad_movimientos": 15
  }
}
```

### Componente de Resumen

```jsx
function ResumenCaja({ aperturaId }) {
  const [resumen, setResumen] = useState(null);

  useEffect(() => {
    fetch(`/api/arqueo-caja/aperturas/${aperturaId}/resumen/`)
      .then(res => res.json())
      .then(data => setResumen(data));
  }, [aperturaId]);

  if (!resumen) return <Loading />;

  return (
    <div className="card">
      <div className="card-header">
        <h5>Resumen de Caja - {resumen.apertura.codigo_apertura}</h5>
      </div>
      <div className="card-body">
        <div className="row">
          <div className="col-md-3">
            <h6>Monto Inicial</h6>
            <p>Gs. {formatNumber(resumen.totales.monto_inicial)}</p>
          </div>
          <div className="col-md-3">
            <h6>Total Ingresos</h6>
            <p className="text-success">+ Gs. {formatNumber(resumen.totales.total_ingresos)}</p>
          </div>
          <div className="col-md-3">
            <h6>Total Egresos</h6>
            <p className="text-danger">- Gs. {formatNumber(resumen.totales.total_egresos)}</p>
          </div>
          <div className="col-md-3">
            <h6>Saldo Actual</h6>
            <p className="fw-bold">Gs. {formatNumber(resumen.totales.saldo_calculado)}</p>
          </div>
        </div>

        <hr />

        <h6>Últimos Movimientos</h6>
        <table className="table">
          <thead>
            <tr>
              <th>Número</th>
              <th>Tipo</th>
              <th>Concepto</th>
              <th>Monto</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody>
            {resumen.movimientos.map(mov => (
              <tr key={mov.numero_movimiento}>
                <td>{mov.numero_movimiento}</td>
                <td>
                  <span className={`badge ${mov.tipo_movimiento === 'ingreso' ? 'bg-success' : 'bg-danger'}`}>
                    {mov.tipo_movimiento}
                  </span>
                </td>
                <td>{mov.concepto}</td>
                <td>Gs. {formatNumber(mov.monto)}</td>
                <td>{formatFecha(mov.fecha_hora_movimiento)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## Casos de Uso Especiales

### 1. Empleado registra pago sin caja abierta

**Comportamiento:**
- El ComprobantePago se crea normalmente
- NO se crea MovimientoCaja
- La reserva se actualiza normalmente
- El frontend muestra un warning informativo

**Implementación:**
```javascript
// Después de registrar el pago
if (!estadoCaja.tiene_caja_abierta) {
  mostrarAlerta({
    tipo: 'warning',
    titulo: 'Pago registrado sin movimiento de caja',
    mensaje: 'El pago fue registrado exitosamente, pero no se generó movimiento de caja porque no tienes una caja abierta.',
    accion: {
      texto: 'Abrir caja ahora',
      callback: () => navegarAbrirCaja()
    }
  });
}
```

### 2. Actualización en Tiempo Real del Saldo

**Usando WebSockets (opcional):**
```javascript
// Establecer conexión WebSocket
const ws = new WebSocket('ws://api.../ws/caja/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.tipo === 'movimiento_caja') {
    // Actualizar saldo en UI
    actualizarSaldoCaja(data.nuevo_saldo);
  }
};
```

**Usando Polling:**
```javascript
// Actualizar cada 30 segundos
setInterval(async () => {
  const estado = await verificarEstadoCaja();
  actualizarInterfaz(estado);
}, 30000);
```

---

## Testing Frontend

### Test de Integración

```javascript
describe('Registro de Pagos con Caja', () => {
  test('debe mostrar indicador de caja abierta', async () => {
    // Mock API response
    mockAPI('/api/arqueo-caja/aperturas/tengo-caja-abierta/', {
      tiene_caja_abierta: true,
      caja_nombre: 'Caja Principal',
      saldo_actual: '1500000.00'
    });

    render(<FormularioPagos />);

    expect(screen.getByText(/Caja Principal/i)).toBeInTheDocument();
    expect(screen.getByText(/1,500,000/i)).toBeInTheDocument();
  });

  test('debe mostrar alerta si no hay caja abierta', async () => {
    mockAPI('/api/arqueo-caja/aperturas/tengo-caja-abierta/', {
      tiene_caja_abierta: false,
      notificacion: 'No tienes una caja abierta'
    });

    render(<FormularioPagos />);

    expect(screen.getByText(/No tienes una caja abierta/i)).toBeInTheDocument();
    expect(screen.getByText(/Abrir Caja/i)).toBeInTheDocument();
  });
});
```

---

## Checklist de Implementación

- [ ] Agregar llamada a `/tengo-caja-abierta/` al cargar pantallas de pagos
- [ ] Mostrar indicador visual del estado de caja (badge en navbar)
- [ ] Mostrar alert informativo en formulario de pagos
- [ ] Agregar confirmación si se registra pago sin caja abierta
- [ ] Actualizar saldo en tiempo real después de registrar pago
- [ ] Agregar botón "Abrir Caja" en alertas
- [ ] Mostrar toast de confirmación tras registrar pago
- [ ] Implementar vista de resumen de movimientos de caja
- [ ] Agregar tests de integración
- [ ] Documentar flujo en manual de usuario

---

## Conclusión

La integración entre pagos y movimientos de caja es completamente automática en el backend. El frontend solo necesita:

1. **Verificar** el estado de caja antes de registrar pagos
2. **Informar** al usuario sobre el estado de su caja
3. **Facilitar** la apertura de caja si no está abierta
4. **Actualizar** la interfaz después de registrar pagos

El sistema está diseñado para ser **flexible** (permite pagos sin caja abierta) pero **transparente** (siempre informa al usuario qué está pasando).
