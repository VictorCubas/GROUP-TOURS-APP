# Documentación: Generación de PDF para Cierre de Caja

## Descripción General

Se ha implementado la funcionalidad de generación de PDF para los cierres de caja. El PDF incluye todos los datos del cierre y los movimientos realizados por el responsable durante el turno.

## Cambios Implementados

### 1. Modelo CierreCaja (`apps/arqueo_caja/models.py`)

Se agregó el método `generar_pdf()` que genera un PDF completo con:

- **Encabezado**: Código de cierre, fecha y hora
- **Información de la caja y responsable**: Nombre de caja, punto de expedición, nombre del responsable
- **Resumen del turno**:
  - Monto inicial
  - Total ingresos
  - Total egresos
- **Detalle de ingresos por método de pago**:
  - Efectivo
  - Tarjetas
  - Transferencias
  - Cheques
  - Otros
- **Arqueo de caja**:
  - Saldo teórico
  - Saldo real contado
  - Diferencia (con color verde si es positiva, rojo si es negativa)
  - Porcentaje de diferencia
  - Badge de autorización (si requiere)
- **Movimientos del turno**: Tabla con todos los movimientos registrados por el responsable
- **Observaciones**: Si existen observaciones o justificaciones de diferencia

#### Características del PDF:

- Tamaño: Carta (letter)
- Fuentes: Helvetica y Helvetica-Bold
- Tablas con estilo profesional y colores
- Manejo automático de paginación
- Formato de montos con separadores de miles
- Fechas en formato local (timezone)

### 2. Vista CierreCajaViewSet (`apps/arqueo_caja/views.py`)

#### Nuevo endpoint: `descargar_pdf()`

```python
GET /api/arqueo-caja/cierres/{id}/pdf/
```

**Descripción**: Genera y descarga el PDF del cierre de caja.

**Parámetros**:
- `id` (path): ID del cierre de caja

**Response**: Archivo PDF para descarga

**Ejemplo de uso**:
```bash
GET http://127.0.0.1:8000/api/arqueo-caja/cierres/1/pdf/
```

#### Modificación del endpoint: `cerrar-simple()`

Se modificó la respuesta para incluir:
- `id`: ID del cierre creado
- `pdf_url`: URL para descargar el PDF

**Request**:
```json
POST http://127.0.0.1:8000/api/arqueo-caja/cierres/cerrar-simple/
{
  "apertura_caja": 13,
  "saldo_real_efectivo": "400000.00",
  "observaciones": "Cierre del turno tarde" // opcional
}
```

**Response**:
```json
{
  "id": 1,
  "codigo_cierre": "CIE-2025-0001",
  "fecha_cierre": "2025-11-17T18:30:00.000Z",
  "monto_inicial": "1000000.00",
  "total_vendido": "500000.00",
  "total_gastado": "100000.00",
  "saldo_teorico": "1400000.00",
  "saldo_real": "400000.00",
  "diferencia": "-1000000.00",
  "diferencia_porcentaje": "-71.43",
  "requiere_autorizacion": true,
  "estado": "pendiente_autorizacion",
  "pdf_url": "/api/arqueo-caja/cierres/1/pdf/"
}
```

## Flujo de Uso

### Opción 1: Descargar PDF después de cerrar la caja

1. El frontend realiza el cierre de caja con `POST /api/arqueo-caja/cierres/cerrar-simple/`
2. Recibe la respuesta con el `id` y `pdf_url`
3. Puede descargar el PDF inmediatamente usando la URL: `GET /api/arqueo-caja/cierres/{id}/pdf/`

### Opción 2: Descargar PDF de un cierre existente

1. Obtener la lista de cierres: `GET /api/arqueo-caja/cierres/`
2. Seleccionar un cierre y obtener su `id`
3. Descargar el PDF: `GET /api/arqueo-caja/cierres/{id}/pdf/`

## Identificación del Usuario

El PDF identifica automáticamente al usuario responsable del cierre a través de:

1. **Relación con la apertura**: `CierreCaja.apertura_caja`
2. **Responsable de la apertura**: `AperturaCaja.responsable` (Empleado)
3. **Movimientos del usuario**: Filtra los movimientos donde `usuario_registro` es igual al responsable de la apertura

```python
# Código que identifica los movimientos del responsable
movimientos = self.apertura_caja.movimientos.filter(
    activo=True,
    usuario_registro=self.apertura_caja.responsable
).order_by('fecha_hora_movimiento')
```

**Nota**: No es necesario pasar el token o identificar al usuario manualmente, ya que el sistema lo hace automáticamente basándose en la relación entre el cierre, la apertura y el responsable.

## Ejemplo de Integración en Frontend

### React/JavaScript

```javascript
// 1. Cerrar la caja
const cerrarCaja = async (aperturaCajaId, saldoReal) => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/arqueo-caja/cierres/cerrar-simple/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        apertura_caja: aperturaCajaId,
        saldo_real_efectivo: saldoReal
      })
    });

    const data = await response.json();

    // 2. Descargar el PDF automáticamente
    if (data.pdf_url) {
      descargarPDF(data.id);
    }

    return data;
  } catch (error) {
    console.error('Error al cerrar caja:', error);
  }
};

// 3. Función para descargar el PDF
const descargarPDF = async (cierreId) => {
  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/arqueo-caja/cierres/${cierreId}/pdf/`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cierre_caja_${cierreId}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('Error al descargar PDF:', error);
  }
};
```

## Dependencias

El sistema utiliza la biblioteca `reportlab` que ya está instalada en el proyecto:

```
reportlab>=3.6.0
```

No se requieren instalaciones adicionales.

## Notas Técnicas

1. **Timezone**: El PDF convierte todas las fechas a la zona horaria local usando `timezone.localtime()`
2. **Formato de montos**: Se usa formato con separador de miles (ej: "Gs 1,000,000")
3. **Paginación**: El PDF maneja automáticamente el salto de página si el contenido es extenso
4. **Limitación de movimientos**: Se muestran hasta 15 movimientos en el PDF. Si hay más, se indica con "Más movimientos disponibles en el sistema"
5. **Colores**:
   - Verde (#27ae60): Diferencia positiva, estado autorizado
   - Rojo (#e74c3c): Diferencia negativa, requiere autorización
   - Azul (#3498db): Sección de arqueo
   - Gris (#95a5a6): Tabla de movimientos

## Testing

Para probar la funcionalidad:

```bash
# 1. Verificar que no hay errores en el proyecto
cd GroupTours
python manage.py check

# 2. Probar el endpoint de cierre con curl
curl -X POST http://127.0.0.1:8000/api/arqueo-caja/cierres/cerrar-simple/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"apertura_caja": 13, "saldo_real_efectivo": "400000.00"}'

# 3. Descargar el PDF (reemplazar {id} con el ID recibido)
curl -X GET http://127.0.0.1:8000/api/arqueo-caja/cierres/{id}/pdf/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output cierre.pdf
```

## Solución de Problemas

### Error: "No module named 'reportlab'"

```bash
pip install reportlab
```

### Error: "'MovimientoCaja' object has no attribute 'get_concepto_display'"

**Solución aplicada**: Se creó una función auxiliar `get_concepto_label()` dentro del método `generar_pdf()` que mapea el valor del concepto a su etiqueta legible usando los diccionarios `CONCEPTOS_INGRESO` y `CONCEPTOS_EGRESO`.

```python
def get_concepto_label(concepto_value, tipo_mov):
    """Obtiene la etiqueta legible del concepto"""
    if tipo_mov == 'ingreso':
        conceptos_dict = dict(MovimientoCaja.CONCEPTOS_INGRESO)
    else:
        conceptos_dict = dict(MovimientoCaja.CONCEPTOS_EGRESO)
    return conceptos_dict.get(concepto_value, concepto_value)
```

Esto es necesario porque el campo `concepto` es un `CharField` sin `choices` en el modelo, por lo que no tiene el método automático `get_concepto_display()` de Django.

### Error: "El PDF no se genera correctamente"

Verificar que:
1. El cierre tiene datos válidos
2. La apertura asociada existe
3. El responsable tiene una persona asociada

### El PDF no muestra movimientos

Verificar que:
1. Los movimientos tienen `activo=True`
2. El `usuario_registro` coincide con el responsable de la apertura
3. Los movimientos pertenecen a la apertura correcta

## Mantenimiento Futuro

### Para agregar más secciones al PDF:

1. Editar el método `generar_pdf()` en `apps/arqueo_caja/models.py`
2. Agregar la nueva sección antes del pie de página
3. Ajustar la variable `y` para manejar el espaciado

### Para cambiar el estilo:

1. Modificar los colores en `colors.HexColor("#codigo")`
2. Cambiar fuentes en `title_font` y `normal_font`
3. Ajustar tamaños con `inch` de `reportlab.lib.units`

---

**Fecha de implementación**: 17 de noviembre de 2025
**Versión**: 1.0
**Autor**: Sistema GroupTours
