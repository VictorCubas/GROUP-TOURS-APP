# Guía de Integración Frontend - Sistema Multi-Moneda

## Response de la API

Cuando consultes una salida, la API ahora devuelve información en ambas monedas:

```javascript
// GET /api/paquete/salidas/7/

{
  "id": 7,
  "paquete": "VICTOR HUGO",
  "fecha_salida": "2025-09-21",
  "fecha_regreso": "2025-09-25",

  // Moneda principal de la salida
  "moneda": "USD",
  "moneda_id": 1,

  // Precios en la moneda principal
  "precio_actual": 2000.00,
  "precio_final": 2500.00,
  "precio_venta_sugerido_min": 2300.00,
  "precio_venta_sugerido_max": 2875.00,
  "senia": 500.00,

  // ✨ NUEVO: Precios en moneda alternativa
  "precio_moneda_alternativa": {
    "moneda": "PYG",              // La otra moneda
    "precio_actual": 14040000,     // Convertido
    "precio_final": 17550000,
    "precio_venta_min": 16146000,
    "precio_venta_max": 20180250,
    "senia": 3510000,
    "cotizacion": 7020.00,         // Tasa de cambio aplicada
    "fecha_cotizacion": "2025-11-09"
  },

  // También disponibles (conversión directa a guaraníes)
  "precio_actual_en_guaranies": 14040000,
  "senia_en_guaranies": 3510000,

  // Otros campos...
  "hoteles": [...],
  "cupo": 40,
  "activo": true
}
```

---

## Componentes React/Vue Sugeridos

### **Componente: Selector de Moneda**

```jsx
// React Example
import { useState } from 'react';

function PrecioConMoneda({ salida }) {
  const [mostrarMoneda, setMostrarMoneda] = useState(salida.moneda);

  const precioActual = mostrarMoneda === salida.moneda
    ? salida.precio_actual
    : salida.precio_moneda_alternativa?.precio_actual;

  const simbolo = mostrarMoneda === 'USD' ? '$' : 'Gs';

  return (
    <div className="precio-container">
      <div className="precio-valor">
        <span className="simbolo">{simbolo}</span>
        <span className="monto">{precioActual?.toLocaleString()}</span>
      </div>

      <button onClick={() => setMostrarMoneda(
        mostrarMoneda === 'USD' ? 'PYG' : 'USD'
      )}>
        Ver en {mostrarMoneda === 'USD' ? 'Guaraníes' : 'Dólares'}
      </button>

      {salida.precio_moneda_alternativa && (
        <div className="precio-referencia">
          Al cambio de hoy: {mostrarMoneda === 'USD' ? 'Gs' : '$'}
          {(mostrarMoneda === 'USD'
            ? salida.precio_moneda_alternativa.precio_actual
            : salida.precio_actual
          )?.toLocaleString()}
        </div>
      )}
    </div>
  );
}
```

### **Componente Vue**

```vue
<template>
  <div class="precio-container">
    <div class="precio-principal">
      <span class="simbolo">{{ simboloActual }}</span>
      <span class="monto">{{ montoFormateado }}</span>
      <span class="moneda">{{ monedaActual }}</span>
    </div>

    <button @click="toggleMoneda" class="btn-toggle">
      <i class="icon-refresh"></i>
      Ver en {{ monedaAlternativa }}
    </button>

    <div v-if="precioAlternativo" class="precio-referencia">
      <small>
        Al cambio del {{ fechaCotizacion }}:
        {{ simboloAlternativo }} {{ precioAlternativoFormateado }}
      </small>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    salida: Object
  },
  data() {
    return {
      monedaMostrada: this.salida.moneda
    };
  },
  computed: {
    monedaActual() {
      return this.monedaMostrada;
    },
    monedaAlternativa() {
      return this.salida.precio_moneda_alternativa?.moneda || 'N/A';
    },
    simboloActual() {
      return this.monedaMostrada === 'USD' ? '$' : 'Gs';
    },
    simboloAlternativo() {
      return this.monedaAlternativa === 'USD' ? '$' : 'Gs';
    },
    montoFormateado() {
      const monto = this.monedaMostrada === this.salida.moneda
        ? this.salida.precio_actual
        : this.salida.precio_moneda_alternativa?.precio_actual;
      return monto?.toLocaleString();
    },
    precioAlternativo() {
      return this.salida.precio_moneda_alternativa;
    },
    precioAlternativoFormateado() {
      const monto = this.monedaMostrada === this.salida.moneda
        ? this.precioAlternativo?.precio_actual
        : this.salida.precio_actual;
      return monto?.toLocaleString();
    },
    fechaCotizacion() {
      return this.precioAlternativo?.fecha_cotizacion;
    }
  },
  methods: {
    toggleMoneda() {
      this.monedaMostrada = this.monedaMostrada === 'USD' ? 'PYG' : 'USD';
    }
  }
};
</script>
```

---

## Casos de Uso en UI

### **1. Card de Paquete**

```jsx
<div className="paquete-card">
  <h3>{salida.paquete}</h3>

  <div className="precio-principal">
    <span className="desde">Desde</span>
    <span className="monto">
      {salida.moneda === 'USD' ? '$' : 'Gs'}
      {salida.precio_actual.toLocaleString()}
    </span>
  </div>

  {salida.precio_moneda_alternativa && (
    <div className="precio-secundario">
      <small>
        ≈ {salida.precio_moneda_alternativa.moneda === 'USD' ? '$' : 'Gs'}
        {salida.precio_moneda_alternativa.precio_actual.toLocaleString()}
      </small>
    </div>
  )}
</div>
```

### **2. Detalle de Paquete - Tabla de Precios**

```jsx
<table className="tabla-precios">
  <thead>
    <tr>
      <th>Concepto</th>
      <th>{salida.moneda}</th>
      <th>{salida.precio_moneda_alternativa?.moneda || 'N/A'}</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Precio base</td>
      <td>${salida.precio_actual.toLocaleString()}</td>
      <td>
        Gs {salida.precio_moneda_alternativa?.precio_actual.toLocaleString()}
      </td>
    </tr>
    <tr>
      <td>Precio de venta sugerido</td>
      <td>${salida.precio_venta_sugerido_min.toLocaleString()}</td>
      <td>
        Gs {salida.precio_moneda_alternativa?.precio_venta_min.toLocaleString()}
      </td>
    </tr>
    <tr>
      <td>Seña requerida</td>
      <td>${salida.senia?.toLocaleString()}</td>
      <td>
        Gs {salida.precio_moneda_alternativa?.senia?.toLocaleString()}
      </td>
    </tr>
  </tbody>
  <tfoot>
    <tr>
      <td colspan="3">
        <small>
          Cotización del {salida.precio_moneda_alternativa?.fecha_cotizacion}:
          1 USD = Gs {salida.precio_moneda_alternativa?.cotizacion}
        </small>
      </td>
    </tr>
  </tfoot>
</table>
```

### **3. Cotizador / Calculadora**

```jsx
function CalculadoraPrecio({ salida }) {
  const [moneda, setMoneda] = useState('USD');
  const [pasajeros, setPasajeros] = useState(1);

  const precioUnitario = moneda === salida.moneda
    ? salida.precio_venta_sugerido_min
    : salida.precio_moneda_alternativa?.precio_venta_min;

  const total = precioUnitario * pasajeros;
  const simbolo = moneda === 'USD' ? '$' : 'Gs';

  return (
    <div className="calculadora">
      <h4>Cotización</h4>

      <div className="selector-moneda">
        <button
          className={moneda === 'USD' ? 'active' : ''}
          onClick={() => setMoneda('USD')}
        >
          USD ($)
        </button>
        <button
          className={moneda === 'PYG' ? 'active' : ''}
          onClick={() => setMoneda('PYG')}
        >
          Guaraníes (Gs)
        </button>
      </div>

      <div className="input-pasajeros">
        <label>Cantidad de pasajeros</label>
        <input
          type="number"
          min="1"
          value={pasajeros}
          onChange={(e) => setPasajeros(parseInt(e.target.value))}
        />
      </div>

      <div className="resumen">
        <div className="linea">
          <span>Precio por persona:</span>
          <span>{simbolo} {precioUnitario?.toLocaleString()}</span>
        </div>
        <div className="linea">
          <span>Pasajeros:</span>
          <span>×{pasajeros}</span>
        </div>
        <div className="linea total">
          <span>Total:</span>
          <span className="monto-total">
            {simbolo} {total.toLocaleString()}
          </span>
        </div>
      </div>

      {salida.precio_moneda_alternativa && (
        <div className="nota-conversion">
          <small>
            * Cotización del {salida.precio_moneda_alternativa.fecha_cotizacion}:
            1 USD = Gs {salida.precio_moneda_alternativa.cotizacion.toLocaleString()}
          </small>
        </div>
      )}
    </div>
  );
}
```

---

## Manejo de Errores

```javascript
// Si no hay cotización disponible
if (!salida.precio_moneda_alternativa) {
  return (
    <div className="alerta-sin-cotizacion">
      <i className="icon-warning"></i>
      <p>Precio disponible solo en {salida.moneda}</p>
      <small>No hay cotización vigente para conversión</small>
    </div>
  );
}
```

---

## Filtros y Ordenamiento

### **Filtrar por Moneda**

```javascript
// En el componente de listado
const [filtroMoneda, setFiltroMoneda] = useState('TODAS');

const salidasFiltradas = salidas.filter(salida =>
  filtroMoneda === 'TODAS' || salida.moneda === filtroMoneda
);

// UI
<select onChange={(e) => setFiltroMoneda(e.target.value)}>
  <option value="TODAS">Todas las monedas</option>
  <option value="USD">Solo dólares</option>
  <option value="PYG">Solo guaraníes</option>
</select>
```

### **Ordenar por Precio (Normalizando a PYG)**

```javascript
// Para comparar precios entre diferentes monedas
const salidasOrdenadas = [...salidas].sort((a, b) => {
  const precioA = a.precio_actual_en_guaranies || a.precio_actual;
  const precioB = b.precio_actual_en_guaranies || b.precio_actual;
  return precioA - precioB; // Ascendente
});
```

---

## Estilos CSS Sugeridos

```css
.precio-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.precio-principal {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  font-size: 2rem;
  font-weight: bold;
}

.simbolo {
  color: #666;
  font-size: 1.5rem;
}

.precio-referencia {
  color: #666;
  font-size: 0.875rem;
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.btn-toggle {
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.3s;
}

.btn-toggle:hover {
  background: #0056b3;
}

.alerta-sin-cotizacion {
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
```

---

## LocalStorage para Preferencia de Moneda

```javascript
// Guardar preferencia del usuario
function usarPreferenciaMoneda() {
  const [moneda, setMoneda] = useState(() => {
    return localStorage.getItem('moneda_preferida') || 'USD';
  });

  const cambiarMoneda = (nuevaMoneda) => {
    setMoneda(nuevaMoneda);
    localStorage.setItem('moneda_preferida', nuevaMoneda);
  };

  return [moneda, cambiarMoneda];
}

// Uso
const [monedaPreferida, setMonedaPreferida] = usarPreferenciaMoneda();
```

---

## Notas Importantes

1. **Siempre validar** que `precio_moneda_alternativa` existe antes de usarlo
2. **Formatear números** según la moneda (separadores de miles, decimales)
3. **Mostrar fecha de cotización** para transparencia con el cliente
4. **Guardar preferencia** del usuario (USD vs PYG) en localStorage
5. **Indicar claramente** cuál es la moneda "oficial" del paquete

---

## Testing

```javascript
// Test básico
test('muestra precio en ambas monedas', () => {
  const salida = {
    moneda: 'USD',
    precio_actual: 500,
    precio_moneda_alternativa: {
      moneda: 'PYG',
      precio_actual: 3650000,
      cotizacion: 7300
    }
  };

  render(<PrecioConMoneda salida={salida} />);

  expect(screen.getByText(/500/)).toBeInTheDocument();
  expect(screen.getByText(/3650000/)).toBeInTheDocument();
});
```

---

¿Necesitas más ejemplos o código específico para tu framework?
