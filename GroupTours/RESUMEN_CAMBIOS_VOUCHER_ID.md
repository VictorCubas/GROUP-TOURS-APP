# Resumen de Cambios: Agregado voucher_id en API de Reservas

## Fecha
31 de Octubre de 2025

## Objetivo
Agregar el campo `voucher_id` en la respuesta del endpoint `/api/reservas/{id}/` para facilitar la descarga directa de vouchers en PDF sin necesidad de hacer consultas adicionales.

---

## Cambios Realizados

### 1. Modificación en `apps/reserva/serializers.py`

#### PasajeroSerializer (líneas 84-125)

**Agregado:**
- Campo `voucher_id` (SerializerMethodField)
- Método `get_voucher_id()` para obtener el ID del voucher asociado al pasajero

```python
# Información del voucher
voucher_id = serializers.SerializerMethodField(
    help_text="ID del voucher asociado al pasajero (si existe)"
)

def get_voucher_id(self, obj):
    """
    Obtiene el ID del voucher asociado al pasajero.
    Retorna None si el pasajero no tiene voucher generado.
    """
    if hasattr(obj, 'voucher') and obj.voucher:
        return obj.voucher.id
    return None
```

**Campos en Meta.fields:**
```python
fields = [
    # ... campos existentes ...
    "voucher_codigo",  # Ya existía
    "voucher_id",      # ← NUEVO
    "fecha_registro",
]
```

#### PasajeroEstadoCuentaSerializer (líneas 452-489)

Se agregó el mismo campo `voucher_id` para mantener consistencia en todos los serializers de Pasajero.

---

## Estructura de la Respuesta del Endpoint

### GET /api/reservas/{id}/

**Antes del cambio:**
```json
{
  "pasajeros": [
    {
      "id": 295,
      "persona": { ... },
      "esta_totalmente_pagado": true,
      "voucher_codigo": "RSV-2025-0179-PAX-295-VOUCHER"
      // ❌ Faltaba voucher_id
    }
  ]
}
```

**Después del cambio:**
```json
{
  "pasajeros": [
    {
      "id": 295,
      "persona": { ... },
      "esta_totalmente_pagado": true,
      "voucher_codigo": "RSV-2025-0179-PAX-295-VOUCHER",
      "voucher_id": 153  // ✅ NUEVO CAMPO
    }
  ]
}
```

---

## Flujo de Uso

### Paso 1: Obtener información de la reserva
```
GET /api/reservas/179/
```

**Respuesta (fragmento):**
```json
{
  "id": 179,
  "codigo": "RSV-2025-0179",
  "pasajeros": [
    {
      "id": 295,
      "persona": {
        "nombre": "Victor",
        "apellido": "Cubas"
      },
      "esta_totalmente_pagado": true,
      "voucher_codigo": "RSV-2025-0179-PAX-295-VOUCHER",
      "voucher_id": 153
    },
    {
      "id": 296,
      "persona": {
        "nombre": "Andrea Tutoria",
        "apellido": "Escurra"
      },
      "esta_totalmente_pagado": false,
      "voucher_codigo": null,
      "voucher_id": null
    }
  ]
}
```

### Paso 2: Descargar voucher directamente
```
GET /api/vouchers/153/descargar-pdf/
```

---

## Beneficios

### Antes del cambio:
1. ❌ Obtener reserva: `GET /api/reservas/{id}/`
2. ❌ Buscar voucher por código: `GET /api/vouchers/?codigo_voucher={codigo}`
3. ❌ Extraer voucher_id de la respuesta
4. ❌ Descargar PDF: `GET /api/vouchers/{voucher_id}/descargar-pdf/`

**Total: 3 requests**

### Después del cambio:
1. ✅ Obtener reserva con voucher_id incluido: `GET /api/reservas/{id}/`
2. ✅ Descargar PDF directamente: `GET /api/vouchers/{voucher_id}/descargar-pdf/`

**Total: 2 requests (33% menos requests)**

---

## Condiciones de Disponibilidad del Voucher

El campo `voucher_id` tendrá un valor cuando:
- ✅ `por_asignar = false` (pasajero con datos reales)
- ✅ `esta_totalmente_pagado = true` (sin saldo pendiente)

En caso contrario, `voucher_id` será `null`.

---

## Ejemplo de Implementación en Frontend

```javascript
// React/JavaScript ejemplo
function DescargarVoucherButton({ pasajero }) {
  if (!pasajero.voucher_id) {
    // No tiene voucher
    return (
      <div className="alert alert-warning">
        {pasajero.esta_totalmente_pagado
          ? "Datos del pasajero pendientes"
          : `Saldo pendiente: $${pasajero.saldo_pendiente}`
        }
      </div>
    );
  }

  // Tiene voucher - mostrar botón de descarga
  const handleDescargar = () => {
    const url = `/api/vouchers/${pasajero.voucher_id}/descargar-pdf/`;
    window.open(url, '_blank');
  };

  return (
    <button onClick={handleDescargar} className="btn btn-primary">
      <i className="fas fa-download"></i>
      Descargar Voucher
      <small>{pasajero.voucher_codigo}</small>
    </button>
  );
}
```

---

## Archivos de Documentación Creados

1. **`EJEMPLO_USO_VOUCHER_API.md`**
   - Guía completa de uso de los endpoints de vouchers
   - Ejemplos de código en JavaScript y Python
   - Casos de uso prácticos

2. **`test_descargar_vouchers_reserva.py`**
   - Script de prueba que simula el flujo completo
   - Muestra cómo obtener vouchers de una reserva
   - Genera PDFs de los vouchers disponibles

---

## Testing

### Prueba realizada:

**Reserva de prueba:** ID 179 (RSV-2025-0179)

**Pasajeros:**
1. **Victor Cubas** (ID: 295)
   - ✅ Totalmente pagado: $1,690.00 / $1,690.00
   - ✅ Voucher ID: 153
   - ✅ PDF generado: 4.13 KB

2. **Andrea Tutoria Escurra** (ID: 296)
   - ❌ Pago parcial: $960.00 / $1,690.00
   - ❌ Saldo pendiente: $730.00
   - ❌ Sin voucher (voucher_id: null)

**Resultado:** ✅ Funciona correctamente

---

## Endpoints Relacionados

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/reservas/{id}/` | GET | **Incluye voucher_id en cada pasajero** |
| `/api/vouchers/{id}/descargar-pdf/` | GET | Descarga el PDF del voucher |
| `/api/vouchers/?reserva_id={id}` | GET | Lista vouchers de una reserva |
| `/api/vouchers/?pasajero_id={id}` | GET | Obtiene voucher de un pasajero |

---

## Compatibilidad

✅ **Retrocompatible:** Este cambio NO rompe ninguna funcionalidad existente
- Solo agrega un nuevo campo a la respuesta
- No modifica campos existentes
- No cambia comportamiento de endpoints

---

## Referencias

- Archivo modificado: `apps/reserva/serializers.py`
- Documentación completa: `DOCUMENTACION_VOUCHERS.md`
- Guía de uso: `EJEMPLO_USO_VOUCHER_API.md`
- Script de prueba: `test_descargar_vouchers_reserva.py`
- Modelo Voucher: `apps/comprobante/models.py:656`
- Vista de descarga: `apps/comprobante/views.py:281`
