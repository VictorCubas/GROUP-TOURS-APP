# Sistema Multi-Moneda en Paquetes

## Descripción General

El sistema soporta paquetes y salidas en **USD** y **PYG** (guaraníes), permitiendo que habitaciones y salidas estén en diferentes monedas y convirtiendo automáticamente según la moneda de la salida.

---

## Principio Fundamental

> **Los precios de una salida se almacenan en LA MONEDA DE LA SALIDA**

- Si la salida es en **PYG**: todos los precios se guardan en guaraníes
- Si la salida es en **USD**: todos los precios se guardan en dólares
- Las habitaciones en moneda diferente se **convierten automáticamente**

---

## Casos de Uso

### Caso 1: Salida en PYG con habitaciones mixtas

```python
# Datos de entrada
salida.moneda = PYG
habitaciones = [
    Hab1: 100 USD/noche
    Hab2: 730,000 Gs/noche
]

# Proceso automático (cotización: 1 USD = 7,300 Gs)
Hab1: 100 USD → 730,000 Gs
Hab2: 730,000 Gs → 730,000 Gs

# Resultado guardado
salida.precio_actual = 730,000 Gs
salida.moneda = PYG
```

### Caso 2: Salida en USD con habitaciones mixtas

```python
# Datos de entrada
salida.moneda = USD
habitaciones = [
    Hab1: 100 USD/noche
    Hab2: 730,000 Gs/noche
]

# Proceso automático (cotización: 1 USD = 7,300 Gs)
Hab1: 100 USD → 100 USD
Hab2: 730,000 Gs → 100 USD

# Resultado guardado
salida.precio_actual = 100 USD
salida.moneda = USD
```

---

## Mostrar Precios al Cliente

El sistema permite mostrar precios en **ambas monedas** para atender consultas:

### API Response Example

```json
{
  "id": 123,
  "paquete": "Tour Miami",
  "moneda": "USD",
  "precio_actual": 500,
  "precio_final": 600,

  // Precios en la moneda alternativa (PYG en este caso)
  "precio_moneda_alternativa": {
    "moneda": "PYG",
    "precio_actual": 3650000,
    "precio_final": 4380000,
    "cotizacion": 7300,
    "fecha_cotizacion": "2025-11-10"
  }
}
```

### Flujo de Conversación

**Escenario A: Paquete en USD**
```
Cliente: "¿Cuánto cuesta el paquete?"
Agente: "El paquete cuesta USD 500"
Cliente: "¿Y en guaraníes?"
Agente: "Al cambio de hoy (Gs 7,300), serían Gs 3,650,000"
```

**Escenario B: Paquete en PYG**
```
Cliente: "¿Cuánto cuesta el paquete?"
Agente: "El paquete cuesta Gs 3,650,000"
Cliente: "¿Y en dólares?"
Agente: "Al cambio de hoy (Gs 7,300), equivale a USD 500"
```

---

## Uso Programático

### Crear una Salida

```python
from apps.paquete.models import create_salida_paquete

data = {
    "paquete_id": 1,
    "fecha_salida": "2025-12-01",
    "fecha_regreso": "2025-12-05",
    "moneda_id": 1,  # USD o PYG
    "hoteles_ids": [1, 2, 3],
    "cupo": 40,
    "ganancia": 15,  # 15%
}

# La conversión de habitaciones se hace automáticamente
salida = create_salida_paquete(data)
```

### Obtener Precio en Moneda Alternativa

```python
# Desde el modelo
salida = SalidaPaquete.objects.get(id=123)

# Obtener precio en la otra moneda
precio_alt = salida.obtener_precio_en_moneda_alternativa()

print(f"Moneda: {precio_alt['moneda_alternativa']}")
print(f"Precio: {precio_alt['precio_min']}")
print(f"Cotización: {precio_alt['cotizacion_aplicada']}")
```

### Convertir Montos Manualmente

```python
from apps.paquete.utils import convertir_entre_monedas
from apps.moneda.models import Moneda

usd = Moneda.objects.get(codigo='USD')
pyg = Moneda.objects.get(codigo='PYG')

# Convertir 100 USD a PYG
monto_pyg = convertir_entre_monedas(
    monto=100,
    moneda_origen=usd,
    moneda_destino=pyg,
    fecha='2025-11-10'
)
# Resultado: 730,000 (si cotización es 7,300)

# Convertir 730,000 PYG a USD
monto_usd = convertir_entre_monedas(
    monto=730000,
    moneda_origen=pyg,
    moneda_destino=usd,
    fecha='2025-11-10'
)
# Resultado: 100
```

---

## Facturación

Las facturas **SIEMPRE** se emiten en **PYG** (guaraníes).

La conversión se maneja automáticamente:

```python
# Si la salida/reserva es en USD
reserva.salida.moneda = USD
reserva.monto_total = 500 USD

# Al facturar (cotización: 7,300)
factura.moneda = PYG
factura.total = 3,650,000 Gs
factura.moneda_original = USD
factura.total_moneda_original = 500
factura.cotizacion_aplicada = 7300
```

Esto garantiza:
- ✅ Trazabilidad de la conversión
- ✅ Auditoría completa
- ✅ Cumplimiento legal (facturas en moneda local)

---

## Cotizaciones

Las cotizaciones se registran en el modelo `CotizacionMoneda`:

```python
from apps.moneda.models import CotizacionMoneda, Moneda

usd = Moneda.objects.get(codigo='USD')

# Registrar cotización
CotizacionMoneda.objects.create(
    moneda=usd,
    valor_en_guaranies=7300,  # 1 USD = 7,300 Gs
    fecha_vigencia='2025-11-10',
    usuario_registro=request.user,
    observaciones='Cotización del día'
)
```

**Importante:**
- Solo puede haber **1 cotización por moneda por día**
- La cotización vigente es la más reciente con `fecha_vigencia <= fecha_consulta`
- Si no hay cotización, las conversiones fallan con error claro

---

## Validaciones y Errores

### Error: Sin Cotización Vigente

```python
# Si intentas crear una salida sin cotización
ValidationError:
"No existe cotización de USD vigente para 10/11/2025.
Por favor registre una cotización antes de continuar."
```

**Solución:** Registrar una cotización antes de crear la salida.

### Error: Moneda No Soportada

```python
# Si intentas usar EUR (no soportado)
ValidationError:
"Conversión no soportada entre EUR y PYG.
Solo se admiten conversiones entre USD y PYG."
```

**Solución:** Solo usar USD y PYG.

---

## Arquitectura Técnica

### Archivos Involucrados

```
apps/paquete/
├── models.py
│   ├── SalidaPaquete.obtener_precio_en_moneda_alternativa()
│   └── create_salida_paquete()  [MODIFICADO]
├── utils.py  [NUEVO]
│   └── convertir_entre_monedas()
└── serializers.py
    └── SalidaPaqueteSerializer.precio_moneda_alternativa  [NUEVO]

apps/moneda/
└── models.py
    ├── CotizacionMoneda
    └── CotizacionMoneda.convertir_a_guaranies()  [EXISTENTE]

apps/facturacion/
└── models.py
    └── preparar_datos_factura_con_conversion()  [EXISTENTE]
```

### Flujo de Conversión

```
1. Usuario crea salida con moneda = USD
2. Sistema obtiene habitaciones de hoteles
3. Para cada habitación:
   - Si habitación.moneda == USD → usar precio directo
   - Si habitación.moneda == PYG → convertir a USD
4. Guardar salida.precio_actual en USD
5. Al mostrar al cliente:
   - Mostrar precio en USD (guardado)
   - Calcular precio en PYG (usando cotización actual)
6. Al facturar:
   - Convertir de USD a PYG
   - Guardar trazabilidad de conversión
```

---

## Migración de Datos Existentes

Si ya tienes salidas creadas antes de este sistema:

```python
# Script de migración (ejecutar en Django shell)
from apps.paquete.models import SalidaPaquete
from apps.moneda.models import Moneda

# Asignar moneda PYG a salidas sin moneda
pyg = Moneda.objects.get(codigo='PYG')
SalidaPaquete.objects.filter(moneda__isnull=True).update(moneda=pyg)

# Verificar que todas las habitaciones tengan moneda
from apps.hotel.models import Habitacion
habitaciones_sin_moneda = Habitacion.objects.filter(moneda__isnull=True)
print(f"Habitaciones sin moneda: {habitaciones_sin_moneda.count()}")
```

---

## Preguntas Frecuentes

### ¿Qué pasa si cambio la cotización del dólar?

Los precios de las **salidas existentes NO cambian** (están guardados en su moneda).
Pero al mostrar en moneda alternativa, se usa la cotización actual.

### ¿Puedo tener paquetes en EUR?

No. El sistema solo soporta USD y PYG.

### ¿Las facturas pueden estar en USD?

No. Por regulación, las facturas siempre son en PYG (guaraníes).

### ¿Cómo se manejan las reservas en USD?

Las reservas guardan el monto en la moneda de la salida.
Al facturar, se convierte a PYG automáticamente con la cotización del día.

---

## Soporte

Para consultas o reportar problemas:
- Verificar cotizaciones registradas
- Revisar logs de conversión
- Contactar al equipo de desarrollo
