# ⚡ Notas de Crédito - Quick Start Guide

> Guía rápida para implementar Notas de Crédito en 5 minutos

## 🎯 TL;DR

```python
# Generar NC Total
from apps.facturacion.models import generar_nota_credito_total

nc = generar_nota_credito_total(
    factura_id=123,
    motivo='cancelacion_reserva',
    observaciones='Cliente canceló'
)

# Generar NC Parcial
from apps.facturacion.models import generar_nota_credito_parcial

nc = generar_nota_credito_parcial(
    factura_id=123,
    items_a_acreditar=[
        {'descripcion': 'Paquete', 'cantidad': 2, 'precio_unitario': 2500000}
    ],
    motivo='reduccion_pasajeros',
    observaciones='2 pasajeros cancelaron'
)
```

---

## 📡 Endpoints Principales

### 1. NC Total
```http
POST /api/facturacion/generar-nota-credito-total/123/
{
  "motivo": "cancelacion_reserva",
  "observaciones": "..."
}
```

### 2. NC Parcial
```http
POST /api/facturacion/generar-nota-credito-parcial/123/
{
  "motivo": "reduccion_pasajeros",
  "items": [
    {"descripcion": "...", "cantidad": 2, "precio_unitario": 2500000}
  ]
}
```

### 3. Consultar NC de Factura
```http
GET /api/facturacion/notas-credito-factura/123/
```

### 4. Descargar PDF
```http
GET /api/facturacion/descargar-pdf-nota-credito/456/
```

---

## 🔍 Propiedades Útiles

```javascript
// Factura con NC
{
  "total_general": "10000000.00",
  "total_acreditado": "3000000.00",
  "saldo_neto": "7000000.00",
  "esta_totalmente_acreditada": false,
  "esta_parcialmente_acreditada": true
}
```

---

## ⚙️ Motivos Disponibles

```python
MOTIVOS = [
    'cancelacion_reserva',    # Cancelación de Reserva
    'devolucion',             # Devolución
    'descuento',              # Descuento/Bonificación
    'error_facturacion',      # Error en Facturación
    'ajuste',                 # Ajuste de Precio
    'otro'                    # Otro
]
```

---

## ✅ Validaciones Clave

| Validación | Error |
|------------|-------|
| Factura inactiva | "Factura inactiva" |
| Saldo insuficiente | "El monto a acreditar (...) supera el saldo disponible (...)" |
| NC total con parciales | "No se puede generar NC total si ya existen notas parciales" |
| Factura totalmente acreditada | "Factura ya totalmente acreditada" |

---

## 🎨 Frontend - Ejemplo React

```jsx
const GenerarNC = ({ facturaId }) => {
  const handleNCTotal = async () => {
    const response = await fetch(
      `/api/facturacion/generar-nota-credito-total/${facturaId}/`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          motivo: 'cancelacion_reserva',
          observaciones: 'Cliente canceló'
        })
      }
    );

    if (response.ok) {
      const data = await response.json();
      alert(`NC ${data.nota_credito.numero_nota_credito} generada`);
    }
  };

  return <button onClick={handleNCTotal}>Generar NC Total</button>;
};
```

---

## 🐛 Debug

```python
# Django Shell - Verificar estado de factura
from apps.facturacion.models import FacturaElectronica

factura = FacturaElectronica.objects.get(id=123)
print(f"Total: {factura.total_general}")
print(f"Acreditado: {factura.total_acreditado}")
print(f"Saldo: {factura.saldo_neto}")
print(f"¿Puede NC? {factura.puede_generar_nota_credito()}")

# Ver NC existentes
for nc in factura.notas_credito.filter(activo=True):
    print(f"{nc.numero_nota_credito} - {nc.total_general}")
```

---

## 📄 Estructura de Respuesta

```json
{
  "nota_credito": {
    "id": 456,
    "numero_nota_credito": "001-001-0000078",
    "tipo_nota": "total",
    "motivo_display": "Cancelación de Reserva",
    "total_general": "12000000.00",
    "saldo_factura_restante": "0.00",
    "pdf_generado": "/media/.../nota_credito_001_001_0000078.pdf",
    "detalles": [...]
  }
}
```

---

## 🔗 Ver Documentación Completa

👉 [NOTAS_DE_CREDITO.md](./NOTAS_DE_CREDITO.md)

---

**¿Dudas?** Consulta la documentación completa o abre un issue.
