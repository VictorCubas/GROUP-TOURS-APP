# 📊 ENDPOINTS DE RESUMEN - ARQUEO DE CAJA

Estos endpoints proporcionan estadísticas resumidas para cada módulo del sistema de Arqueo de Caja, similares al endpoint `/api/usuarios/resumen/`.

---

## 🏪 1. RESUMEN DE CAJAS

### **GET** `/api/arqueo-caja/cajas/resumen/`

Obtiene estadísticas resumidas de todas las cajas del sistema.

**Headers:**
```http
Authorization: Bearer {token}
Content-Type: application/json
```

**Response 200 OK:**
```json
[
  {
    "texto": "Total Cajas",
    "valor": "5"
  },
  {
    "texto": "Activas",
    "valor": "5"
  },
  {
    "texto": "Inactivas",
    "valor": "0"
  },
  {
    "texto": "Abiertas Ahora",
    "valor": "1"
  },
  {
    "texto": "Cerradas",
    "valor": "4"
  },
  {
    "texto": "Emiten Facturas",
    "valor": "4"
  },
  {
    "texto": "Saldo Total en Cajas Abiertas",
    "valor": "Gs 2,500,000"
  },
  {
    "texto": "Nuevas últimos 30 días",
    "valor": "2"
  }
]
```

**Uso en Frontend:**
```javascript
const obtenerResumenCajas = async () => {
  const response = await fetch('/api/arqueo-caja/cajas/resumen/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return await response.json();
};
```

---

## 📂 2. RESUMEN DE APERTURAS

### **GET** `/api/arqueo-caja/aperturas/resumen/`

Obtiene estadísticas resumidas de todas las aperturas de caja.

**Headers:**
```http
Authorization: Bearer {token}
Content-Type: application/json
```

**Response 200 OK:**
```json
[
  {
    "texto": "Total Aperturas",
    "valor": "150"
  },
  {
    "texto": "Activas",
    "valor": "148"
  },
  {
    "texto": "Inactivas",
    "valor": "2"
  },
  {
    "texto": "Abiertas Ahora",
    "valor": "1"
  },
  {
    "texto": "Cerradas",
    "valor": "147"
  },
  {
    "texto": "Monto Inicial Total (Abiertas)",
    "valor": "Gs 500,000"
  },
  {
    "texto": "Movimientos en Aperturas Activas",
    "valor": "21"
  },
  {
    "texto": "Aperturas Hoy",
    "valor": "1"
  },
  {
    "texto": "Nuevas últimos 30 días",
    "valor": "30"
  }
]
```

**Uso en Frontend:**
```javascript
const obtenerResumenAperturas = async () => {
  const response = await fetch('/api/arqueo-caja/aperturas/resumen/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return await response.json();
};
```

---

## 📋 3. RESUMEN DE MOVIMIENTOS

### **GET** `/api/arqueo-caja/movimientos/resumen/`

Obtiene estadísticas resumidas de todos los movimientos de caja.

**Headers:**
```http
Authorization: Bearer {token}
Content-Type: application/json
```

**Response 200 OK:**
```json
[
  {
    "texto": "Total Movimientos",
    "valor": "3500"
  },
  {
    "texto": "Ingresos",
    "valor": "2800"
  },
  {
    "texto": "Egresos",
    "valor": "700"
  },
  {
    "texto": "Total Ingresos (Monto)",
    "valor": "Gs 450,000,000"
  },
  {
    "texto": "Total Egresos (Monto)",
    "valor": "Gs 80,000,000"
  },
  {
    "texto": "Ingresos en Efectivo",
    "valor": "Gs 250,000,000"
  },
  {
    "texto": "Ingresos con Tarjetas",
    "valor": "Gs 150,000,000"
  },
  {
    "texto": "Movimientos Hoy",
    "valor": "45"
  },
  {
    "texto": "Ingresos Hoy (Monto)",
    "valor": "Gs 8,500,000"
  },
  {
    "texto": "Nuevos últimos 30 días",
    "valor": "850"
  }
]
```

**Uso en Frontend:**
```javascript
const obtenerResumenMovimientos = async () => {
  const response = await fetch('/api/arqueo-caja/movimientos/resumen/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return await response.json();
};
```

---

## 🔒 4. RESUMEN DE CIERRES

### **GET** `/api/arqueo-caja/cierres/resumen-general/`

⚠️ **Nota:** Este endpoint usa `resumen-general` en lugar de `resumen` porque el endpoint `/cierres/{id}/resumen/` ya existe para obtener el resumen detallado de un cierre específico.

Obtiene estadísticas resumidas de todos los cierres de caja.

**Headers:**
```http
Authorization: Bearer {token}
Content-Type: application/json
```

**Response 200 OK:**
```json
[
  {
    "texto": "Total Cierres",
    "valor": "145"
  },
  {
    "texto": "Con Diferencias",
    "valor": "12"
  },
  {
    "texto": "Sin Diferencias",
    "valor": "133"
  },
  {
    "texto": "Requieren Autorización",
    "valor": "3"
  },
  {
    "texto": "Autorizados",
    "valor": "2"
  },
  {
    "texto": "Diferencia Total Acumulada",
    "valor": "Gs 45,000"
  },
  {
    "texto": "Promedio Diferencia por Cierre",
    "valor": "Gs 310"
  },
  {
    "texto": "Cierres Hoy",
    "valor": "0"
  },
  {
    "texto": "Nuevos últimos 30 días",
    "valor": "28"
  }
]
```

**Uso en Frontend:**
```javascript
const obtenerResumenCierres = async () => {
  const response = await fetch('/api/arqueo-caja/cierres/resumen-general/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return await response.json();
};
```

---

## 📊 COMPARACIÓN CON ENDPOINT DE USUARIOS

### Endpoint de Usuarios (Referencia)

**GET** `/api/usuarios/resumen/`

```json
[
  {
    "texto": "Total",
    "valor": "50"
  },
  {
    "texto": "Activos",
    "valor": "45"
  },
  {
    "texto": "Inactivos",
    "valor": "5"
  },
  {
    "texto": "Nuevos últimos 30 días",
    "valor": "8"
  }
]
```

### Formato Consistente

Todos los endpoints de resumen siguen el mismo formato:
- Retornan un array de objetos
- Cada objeto tiene dos propiedades: `texto` y `valor`
- `texto`: Etiqueta descriptiva del dato
- `valor`: Valor como string (incluso números, para mantener formato)
- No requieren paginación (`pagination_class=None`)
- Retornan estadísticas generales del sistema

---

## 🔧 EJEMPLO DE USO COMPLETO EN REACT

```javascript
import { useState, useEffect } from 'react';
import axios from 'axios';

const ResumenArqueoCaja = () => {
  const [resumenCajas, setResumenCajas] = useState([]);
  const [resumenAperturas, setResumenAperturas] = useState([]);
  const [resumenMovimientos, setResumenMovimientos] = useState([]);
  const [resumenCierres, setResumenCierres] = useState([]);
  const [loading, setLoading] = useState(true);

  const api = axios.create({
    baseURL: '/api/arqueo-caja',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
      'Content-Type': 'application/json'
    }
  });

  useEffect(() => {
    const cargarResumenes = async () => {
      try {
        setLoading(true);

        const [cajas, aperturas, movimientos, cierres] = await Promise.all([
          api.get('/cajas/resumen/'),
          api.get('/aperturas/resumen/'),
          api.get('/movimientos/resumen/'),
          api.get('/cierres/resumen-general/')
        ]);

        setResumenCajas(cajas.data);
        setResumenAperturas(aperturas.data);
        setResumenMovimientos(movimientos.data);
        setResumenCierres(cierres.data);
      } catch (error) {
        console.error('Error cargando resúmenes:', error);
      } finally {
        setLoading(false);
      }
    };

    cargarResumenes();
  }, []);

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="resumen-arqueo-caja">
      <h1>Dashboard - Arqueo de Caja</h1>

      <section className="resumen-section">
        <h2>🏪 Cajas</h2>
        <div className="stats-grid">
          {resumenCajas.map((stat, index) => (
            <div key={index} className="stat-card">
              <span className="stat-label">{stat.texto}</span>
              <span className="stat-value">{stat.valor}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="resumen-section">
        <h2>📂 Aperturas</h2>
        <div className="stats-grid">
          {resumenAperturas.map((stat, index) => (
            <div key={index} className="stat-card">
              <span className="stat-label">{stat.texto}</span>
              <span className="stat-value">{stat.valor}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="resumen-section">
        <h2>📋 Movimientos</h2>
        <div className="stats-grid">
          {resumenMovimientos.map((stat, index) => (
            <div key={index} className="stat-card">
              <span className="stat-label">{stat.texto}</span>
              <span className="stat-value">{stat.valor}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="resumen-section">
        <h2>🔒 Cierres</h2>
        <div className="stats-grid">
          {resumenCierres.map((stat, index) => (
            <div key={index} className="stat-card">
              <span className="stat-label">{stat.texto}</span>
              <span className="stat-value">{stat.valor}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default ResumenArqueoCaja;
```

---

## 📑 RESUMEN DE TODOS LOS ENDPOINTS

| Módulo | Endpoint | Descripción |
|--------|----------|-------------|
| **Cajas** | `GET /api/arqueo-caja/cajas/resumen/` | Estadísticas de cajas |
| **Aperturas** | `GET /api/arqueo-caja/aperturas/resumen/` | Estadísticas de aperturas |
| **Movimientos** | `GET /api/arqueo-caja/movimientos/resumen/` | Estadísticas de movimientos |
| **Cierres** | `GET /api/arqueo-caja/cierres/resumen-general/` | Estadísticas de cierres |

---

## ✅ CARACTERÍSTICAS COMUNES

Todos los endpoints de resumen comparten:

1. **Sin paginación**: Retornan todos los datos de una vez
2. **Formato consistente**: Array de objetos `{texto, valor}`
3. **Autenticación requerida**: Requieren token JWT
4. **Sin parámetros**: No aceptan query parameters
5. **Respuesta rápida**: Optimizados con agregaciones SQL
6. **Estadísticas en tiempo real**: Calculan datos actualizados al momento de la consulta

---

## 🎯 MÉTRICAS INCLUIDAS POR MÓDULO

### 🏪 Cajas
- Total de cajas
- Activas/Inactivas
- Abiertas/Cerradas ahora
- Cajas que emiten facturas
- Saldo total en cajas abiertas
- Nuevas últimos 30 días

### 📂 Aperturas
- Total de aperturas
- Activas/Inactivas
- Abiertas/Cerradas
- Monto inicial total
- Movimientos en aperturas activas
- Aperturas de hoy
- Nuevas últimos 30 días

### 📋 Movimientos
- Total de movimientos
- Ingresos/Egresos (cantidad)
- Total ingresos/egresos (monto)
- Ingresos por método de pago
- Movimientos e ingresos de hoy
- Nuevos últimos 30 días

### 🔒 Cierres
- Total de cierres
- Con/Sin diferencias
- Requieren autorización
- Autorizados
- Diferencia total acumulada
- Promedio de diferencia
- Cierres de hoy
- Nuevos últimos 30 días

---

**Fecha de creación:** 12/11/2025
**Versión:** 1.0
