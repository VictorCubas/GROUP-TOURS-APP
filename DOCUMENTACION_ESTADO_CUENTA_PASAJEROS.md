# 📊 Estado de Cuenta por Pasajero - Documentación

## ✅ IMPLEMENTACIÓN COMPLETADA

Se ha implementado exitosamente el sistema de **estado de cuenta individualizado por pasajero**, completando así el sistema de comprobantes y pagos.

---

## 🎯 FUNCIONALIDADES IMPLEMENTADAS

### 1. **Modelo de Datos (Ya existía)**
El modelo `Pasajero` ya contaba con todas las propiedades calculadas necesarias:

```python
# apps/reserva/models.py - Pasajero

@property
def monto_pagado(self):
    """Suma de todas las distribuciones de pago"""

@property
def saldo_pendiente(self):
    """Saldo que le falta pagar"""

@property
def porcentaje_pagado(self):
    """Porcentaje del precio que ha sido pagado (0-100)"""

@property
def seña_requerida(self):
    """Monto de seña requerido para este pasajero"""

@property
def tiene_sena_pagada(self):
    """Indica si tiene su seña completa pagada"""

@property
def esta_totalmente_pagado(self):
    """Indica si tiene el 100% de su precio pagado"""
```

### 2. **Serializers** ✨ NUEVO
Se crearon dos nuevos serializers:

#### `PasajeroEstadoCuentaSerializer`
Serializer completo para el estado de cuenta con historial de pagos.

**Ubicación:** `apps/reserva/serializers.py:373`

**Campos incluidos:**
- Información personal del pasajero
- Código de reserva y paquete
- Precio asignado
- Monto pagado
- Saldo pendiente
- Porcentaje pagado
- Seña requerida y estado
- Estado de pago completo
- **Historial completo de pagos** (distribuciones)

#### `PagoHistorialSerializer`
Serializer para representar cada pago en el historial.

**Ubicación:** `apps/reserva/serializers.py:349`

### 3. **ViewSet con Endpoint** ✨ NUEVO

#### `PasajeroViewSet`
**Ubicación:** `apps/reserva/views.py:148`

**Endpoints disponibles:**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/reservas/pasajeros/` | Listar todos los pasajeros |
| GET | `/api/reservas/pasajeros/{id}/` | Detalle de un pasajero |
| POST | `/api/reservas/pasajeros/` | Crear nuevo pasajero |
| PUT | `/api/reservas/pasajeros/{id}/` | Actualizar pasajero |
| DELETE | `/api/reservas/pasajeros/{id}/` | Eliminar pasajero |
| **GET** | **`/api/reservas/pasajeros/{id}/estado-cuenta/`** | **Estado de cuenta completo** 🎯 |

**Query params para filtrado:**
- `reserva_id` - Filtrar por reserva
- `persona_id` - Filtrar por persona
- `es_titular` - Filtrar solo titulares (true/false)

### 4. **URLs Registradas** ✨ NUEVO
**Ubicación:** `apps/reserva/urls.py:29-32`

```python
# Endpoints de Pasajeros
path('pasajeros/', PasajeroViewSet.as_view({'get': 'list', 'post': 'create'})),
path('pasajeros/<int:pk>/', PasajeroViewSet.as_view({'get': 'retrieve', ...})),
path('pasajeros/<int:pk>/estado-cuenta/', PasajeroViewSet.as_view({'get': 'estado_cuenta'})),
```

---

## 📡 USO DEL ENDPOINT

### Endpoint Principal: Estado de Cuenta

```http
GET /api/reservas/pasajeros/{id}/estado-cuenta/
Authorization: Bearer <token>
```

### Ejemplo de Respuesta

```json
{
  "id": 1,
  "reserva_codigo": "RSV-2025-0004",
  "paquete_nombre": "VICTOR HUGO",
  "persona": {
    "id": 21,
    "nombre": "Andrea Tutoria",
    "apellido": "Escurra",
    "documento": "888777666",
    "email": "vhcubas91@gmail.com",
    "telefono": "8643532143"
  },
  "es_titular": true,
  "precio_asignado": "5000.00",
  "monto_pagado": "1500.00",
  "saldo_pendiente": "3500.00",
  "porcentaje_pagado": "30.00",
  "seña_requerida": "1500.00",
  "tiene_sena_pagada": true,
  "esta_totalmente_pagado": false,
  "ticket_numero": null,
  "voucher_codigo": null,
  "fecha_registro": "2025-10-16T09:30:02+0000",
  "historial_pagos": [
    {
      "fecha_pago": "2025-10-23T16:23:39+0000",
      "numero_comprobante": "CPG-2025-0001",
      "tipo": "sena",
      "tipo_display": "Seña",
      "metodo_pago": "transferencia",
      "metodo_pago_display": "Transferencia Bancaria",
      "monto_distribuido": "1500.00",
      "comprobante_activo": true,
      "observaciones": "Seña del pasajero titular"
    }
  ]
}
```

### Casos de Uso

#### 1. Consultar estado de cuenta de un pasajero
```bash
GET /api/reservas/pasajeros/1/estado-cuenta/
```

#### 2. Listar todos los pasajeros de una reserva
```bash
GET /api/reservas/pasajeros/?reserva_id=5
```

#### 3. Listar solo pasajeros titulares
```bash
GET /api/reservas/pasajeros/?es_titular=true
```

#### 4. Ver historial de una persona específica
```bash
GET /api/reservas/pasajeros/?persona_id=21
```

---

## 🔗 INTEGRACIÓN CON COMPROBANTES

El sistema de estado de cuenta se integra perfectamente con el sistema de comprobantes:

### Flujo Completo de Pagos

```
1. CREAR COMPROBANTE
   POST /api/comprobantes/
   {
     "reserva": 1,
     "tipo": "sena",
     "monto": 3000.00,
     "metodo_pago": "transferencia",
     "empleado": 1,
     "distribuciones": [
       {
         "pasajero": 1,
         "monto": 1500.00
       },
       {
         "pasajero": 2,
         "monto": 1500.00
       }
     ]B
   }

2. CONSULTAR ESTADO DE CADA PASAJERO
   GET /api/reservas/pasajeros/1/estado-cuenta/
   GET /api/reservas/pasajeros/2/estado-cuenta/

   ↓ Automáticamente calculado:
   - monto_pagado actualizado
   - saldo_pendiente recalculado
   - historial_pagos incluye el nuevo pago
```

---

## 📋 CHECKLIST FINAL: SISTEMA DE COMPROBANTES COMPLETO

| # | Funcionalidad | Estado | Ubicación |
|---|---------------|--------|-----------|
| 1️⃣ | Modelo `ComprobantePago` | ✅ | `apps/comprobante/models.py:7` |
| 2️⃣ | Modelo `ComprobantePagoDistribucion` | ✅ | `apps/comprobante/models.py:171` |
| 3️⃣ | Modelo `Voucher` | ✅ | `apps/comprobante/models.py:248` |
| 4️⃣ | Signal para crear vouchers | ✅ | `apps/comprobante/signals.py:7` |
| 5️⃣ | Serializers de comprobantes | ✅ | `apps/comprobante/serializers.py` |
| 6️⃣ | ViewSets de comprobantes | ✅ | `apps/comprobante/views.py` |
| 7️⃣ | **Estado de cuenta por pasajero** | ✅ | `apps/reserva/views.py:148` |
| 8️⃣ | **Historial de pagos individual** | ✅ | `apps/reserva/serializers.py:430` |
| 9️⃣ | Endpoints API completos | ✅ | Ver sección URLs |
| 🔟 | Migraciones aplicadas | ✅ | `comprobante.0001_initial` |

---

## 🧪 TESTING

Se incluyó un script de prueba completo:

**Archivo:** `test_estado_cuenta.py`

**Ejecutar:**
```bash
python test_estado_cuenta.py
```

**Funciones del script:**
- Crea comprobante de ejemplo si no existe
- Crea distribución de pago a un pasajero
- Muestra estado de cuenta formateado
- Genera JSON completo para API

---

## 📊 ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────────────┐
│                       RESERVA                           │
│  - cantidad_pasajeros                                   │
│  - precio_unitario                                      │
│  - monto_pagado (calculado desde comprobantes)         │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
┌───────▼──────┐    ┌──────▼──────────┐
│  PASAJERO 1  │    │  PASAJERO 2     │
│  Precio: 5000│    │  Precio: 5000   │
└──────┬───────┘    └──────┬──────────┘
       │                   │
       │ DistribucionPago  │ DistribucionPago
       │ Monto: 1500       │ Monto: 1500
       │                   │
       └───────┬───────────┘
               │
     ┌─────────▼──────────┐
     │  COMPROBANTE PAGO  │
     │  CPG-2025-0001     │
     │  Monto total: 3000 │
     │  Tipo: Seña        │
     └────────────────────┘
```

**Propiedades calculadas por pasajero:**
- `monto_pagado` = Σ(distribuciones.monto)
- `saldo_pendiente` = precio_asignado - monto_pagado
- `porcentaje_pagado` = (monto_pagado / precio_asignado) × 100
- `tiene_sena_pagada` = monto_pagado >= seña_requerida
- `esta_totalmente_pagado` = saldo_pendiente <= 0

---

## 🚀 PRÓXIMOS PASOS SUGERIDOS

1. **Generar PDFs de estado de cuenta**
   - Crear vista para generar PDF del estado de cuenta
   - Incluir historial completo de pagos
   - Agregar logo y datos de la empresa

2. **Notificaciones por email**
   - Enviar estado de cuenta por email
   - Notificar cuando se registra un pago
   - Recordatorios de saldo pendiente

3. **Dashboard de pasajeros**
   - Vista resumida de todos los pasajeros
   - Filtros por estado de pago
   - Gráficos de pagos recibidos

4. **Reportes financieros**
   - Reporte de pagos por período
   - Análisis de deudas pendientes
   - Proyección de ingresos

---

## 📝 NOTAS TÉCNICAS

### Optimización de Queries
El ViewSet incluye `select_related` para optimizar consultas:

```python
queryset = Pasajero.objects.select_related(
    'persona',
    'reserva',
    'reserva__paquete',
    'reserva__salida'
)
```

### Transacciones Atómicas
Los comprobantes usan `@transaction.atomic` para garantizar consistencia.

### Validaciones
- Distribuciones deben sumar el monto total del comprobante
- Pasajero debe pertenecer a la reserva del comprobante
- Montos no pueden ser negativos

---

## 📧 SOPORTE

Para dudas o problemas:
- Revisar logs en consola Django
- Verificar migraciones aplicadas: `python manage.py showmigrations`
- Ejecutar tests: `python test_estado_cuenta.py`

---

**Fecha de implementación:** 23 de Octubre, 2025
**Autor:** Claude Code Assistant
**Versión:** 1.0.0
