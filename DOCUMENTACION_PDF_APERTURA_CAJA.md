# 📄 Documentación: PDF de Apertura de Caja

## Resumen
Esta funcionalidad permite generar y descargar un PDF con los datos de una apertura de caja.

---

## 🔗 Endpoints Disponibles

### 1. Crear Apertura de Caja
```
POST /api/arqueo-caja/aperturas/
```

**Request:**
```json
{
  "caja": 1,
  "fecha_hora_apertura": "2025-11-17T15:42:00.000Z",
  "monto_inicial": "1000000.00",
  "observaciones_apertura": "Apertura del turno mañana"
}
```

**Response:**
```json
{
  "id": 5,
  "codigo_apertura": "APR-2025-0005",
  "caja": 1,
  "caja_nombre": "Caja Principal",
  "responsable": 1,
  "responsable_nombre": "Juan Pérez",
  "fecha_hora_apertura": "2025-11-17T15:42:00.000Z",
  "monto_inicial": "1000000.00",
  "observaciones_apertura": "Apertura del turno mañana",
  "esta_abierta": true,
  "activo": true
}
```

### 2. Descargar PDF de Apertura
```
GET /api/arqueo-caja/aperturas/{id}/pdf/
```

**Parámetros:**
- `{id}`: ID de la apertura (obtenido del POST anterior)

**Response:**
- Archivo PDF descargable

---

## 💻 Implementación en el Frontend

### Opción 1: JavaScript Vanilla

```javascript
// 1. Crear apertura y obtener el ID
async function crearYDescargarApertura() {
  const token = localStorage.getItem('token'); // Tu token JWT

  try {
    // Crear apertura
    const response = await fetch('http://127.0.0.1:8000/api/arqueo-caja/aperturas/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        caja: 1,
        fecha_hora_apertura: new Date().toISOString(),
        monto_inicial: "1000000.00",
        observaciones_apertura: ""
      })
    });

    const apertura = await response.json();
    console.log('✅ Apertura creada:', apertura);

    // Descargar PDF automáticamente
    descargarPDF(apertura.id);

    return apertura;

  } catch (error) {
    console.error('❌ Error:', error);
  }
}

// 2. Función para descargar el PDF
function descargarPDF(aperturaId) {
  const token = localStorage.getItem('token');
  const pdfUrl = `http://127.0.0.1:8000/api/arqueo-caja/aperturas/${aperturaId}/pdf/`;

  // Abrir PDF en nueva pestaña (se descarga automáticamente)
  window.open(pdfUrl + `?token=${token}`, '_blank');
}
```

### Opción 2: Descargar con Fetch (más control)

```javascript
async function descargarPDFConFetch(aperturaId) {
  const token = localStorage.getItem('token');

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/arqueo-caja/aperturas/${aperturaId}/pdf/`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    if (!response.ok) {
      throw new Error('Error al descargar PDF');
    }

    // Convertir respuesta a blob
    const blob = await response.blob();

    // Crear URL temporal
    const url = window.URL.createObjectURL(blob);

    // Crear link de descarga
    const a = document.createElement('a');
    a.href = url;
    a.download = `apertura_${aperturaId}.pdf`;
    document.body.appendChild(a);
    a.click();

    // Limpiar
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    console.log('✅ PDF descargado exitosamente');

  } catch (error) {
    console.error('❌ Error al descargar PDF:', error);
  }
}
```

### Opción 3: React

```jsx
import { useState } from 'react';

function AperturaCaja() {
  const [loading, setLoading] = useState(false);
  const [apertura, setApertura] = useState(null);

  const crearApertura = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/arqueo-caja/aperturas/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          caja: 1,
          fecha_hora_apertura: new Date().toISOString(),
          monto_inicial: "1000000.00",
          observaciones_apertura: ""
        })
      });

      const data = await response.json();
      setApertura(data);

      // Descargar PDF automáticamente
      descargarPDF(data.id);

    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const descargarPDF = async (aperturaId) => {
    const token = localStorage.getItem('token');

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/arqueo-caja/aperturas/${aperturaId}/pdf/`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `apertura_${aperturaId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error('Error al descargar PDF:', error);
    }
  };

  return (
    <div>
      <button onClick={crearApertura} disabled={loading}>
        {loading ? 'Creando...' : 'Crear Apertura y Descargar PDF'}
      </button>

      {apertura && (
        <div>
          <p>✅ Apertura creada: {apertura.codigo_apertura}</p>
          <button onClick={() => descargarPDF(apertura.id)}>
            📄 Re-descargar PDF
          </button>
        </div>
      )}
    </div>
  );
}

export default AperturaCaja;
```

### Opción 4: Axios (React/Vue)

```javascript
import axios from 'axios';

// Configurar axios con el token
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
});

// Crear apertura
async function crearApertura() {
  try {
    const response = await api.post('/arqueo-caja/aperturas/', {
      caja: 1,
      fecha_hora_apertura: new Date().toISOString(),
      monto_inicial: "1000000.00",
      observaciones_apertura: ""
    });

    const apertura = response.data;
    console.log('✅ Apertura creada:', apertura);

    // Descargar PDF
    await descargarPDF(apertura.id);

    return apertura;

  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
  }
}

// Descargar PDF con Axios
async function descargarPDF(aperturaId) {
  try {
    const response = await api.get(`/arqueo-caja/aperturas/${aperturaId}/pdf/`, {
      responseType: 'blob' // Importante para PDFs
    });

    // Crear URL del blob
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `apertura_${aperturaId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    console.log('✅ PDF descargado');

  } catch (error) {
    console.error('❌ Error al descargar PDF:', error);
  }
}
```

---

## 🎯 Casos de Uso

### Caso 1: Crear apertura y descargar inmediatamente
```javascript
// Al hacer clic en "Abrir Caja"
async function abrirCaja(cajaId, montoInicial) {
  const apertura = await crearApertura(cajaId, montoInicial);
  descargarPDF(apertura.id);
  alert('✅ Caja abierta. PDF descargado.');
}
```

### Caso 2: Botón para re-descargar PDF desde lista
```javascript
// En un listado de aperturas
function ListaAperturas({ aperturas }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Código</th>
          <th>Caja</th>
          <th>Fecha</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        {aperturas.map(apertura => (
          <tr key={apertura.id}>
            <td>{apertura.codigo_apertura}</td>
            <td>{apertura.caja_nombre}</td>
            <td>{new Date(apertura.fecha_hora_apertura).toLocaleString()}</td>
            <td>
              <button onClick={() => descargarPDF(apertura.id)}>
                📄 Descargar PDF
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### Caso 3: Mostrar vista previa del PDF (iframe)
```javascript
function VisualizarPDF({ aperturaId }) {
  const token = localStorage.getItem('token');
  const pdfUrl = `http://127.0.0.1:8000/api/arqueo-caja/aperturas/${aperturaId}/pdf/?token=${token}`;

  return (
    <div>
      <h3>Vista Previa del PDF</h3>
      <iframe
        src={pdfUrl}
        width="100%"
        height="600px"
        title="PDF Apertura de Caja"
      />
    </div>
  );
}
```

---

## 📋 Contenido del PDF

El PDF generado incluye:

- ✅ **Encabezado**: "APERTURA DE CAJA"
- ✅ **Código de Apertura**: APR-2025-XXXX
- ✅ **Fecha y Hora**: dd/mm/yyyy HH:MM
- ✅ **Información de la Caja**:
  - Nombre de la caja
  - Número de caja
  - Punto de expedición
  - Dirección del establecimiento
- ✅ **Estado**: Badge con color (ABIERTA/CERRADA)
- ✅ **Responsable**: Nombre y documento del empleado
- ✅ **Montos Iniciales**: Tabla con monto en Guaraníes
- ✅ **Observaciones**: Si hay observaciones registradas
- ✅ **Pie de Página**: Fecha de generación y sistema

---

## ⚠️ Notas Importantes

1. **Autenticación**: Todos los endpoints requieren token JWT en el header:
   ```javascript
   'Authorization': `Bearer ${token}`
   ```

2. **Campo responsable**: Si se envía `null`, el backend asigna automáticamente el empleado del usuario autenticado.

3. **Formato de fecha**: Usar ISO 8601: `new Date().toISOString()`

4. **Manejo de errores**: Siempre validar respuestas y manejar errores:
   ```javascript
   if (!response.ok) {
     const error = await response.json();
     console.error('Error:', error);
     alert(error.error || 'Error al crear apertura');
   }
   ```

5. **CORS**: Asegúrate de que tu dominio esté permitido en el backend.

---

## 🔧 Troubleshooting

### Problema: "Error de autenticación"
**Solución**: Verificar que el token esté presente y sea válido:
```javascript
const token = localStorage.getItem('token');
if (!token) {
  alert('Debes iniciar sesión');
  return;
}
```

### Problema: "El PDF no se descarga"
**Solución**: Verificar que el navegador no esté bloqueando pop-ups. Usar la opción de descarga con fetch en lugar de `window.open()`.

### Problema: "Error 404 al descargar PDF"
**Solución**: Verificar que el ID de la apertura sea correcto:
```javascript
console.log('ID de apertura:', apertura.id);
```

---

## 📞 Soporte

Para más información, consultar:
- Backend: `GroupTours/apps/arqueo_caja/views.py`
- Modelos: `GroupTours/apps/arqueo_caja/models.py`
- Documentación de diseño: `GroupTours/docs/DISEÑO_ARQUEO_CAJA.md`
