# Guía de Uso: API de Vouchers

## Descripción General

Esta guía muestra cómo usar los endpoints de la API para obtener información de reservas y descargar los vouchers en PDF de los pasajeros.

---

## Flujo de Uso

### Paso 1: Obtener detalles de una reserva

**Endpoint:** `GET /api/reservas/{reserva_id}/`

**Ejemplo:** `GET http://127.0.0.1:8000/api/reservas/179/`

**Respuesta (fragmento relevante):**

```json
{
  "id": 179,
  "codigo": "RSV-2025-0179",
  "estado": "confirmada",
  "cantidad_pasajeros": 2,
  "pasajeros": [
    {
      "id": 295,
      "persona": {
        "id": 10,
        "nombre": "Victor",
        "apellido": "Cubas",
        "documento": "4028760",
        "email": "vhcubas@gmail.com"
      },
      "es_titular": false,
      "por_asignar": false,
      "precio_asignado": "2340.00",
      "monto_pagado": "2340.00",
      "saldo_pendiente": "0.00",
      "esta_totalmente_pagado": true,
      "voucher_codigo": "RSV-2025-0179-PAX-295-VOUCHER",
      "voucher_id": 153
    },
    {
      "id": 296,
      "persona": {
        "id": 11,
        "nombre": "Andrea Tutoria",
        "apellido": "Escurra",
        "documento": "5123456",
        "email": "andrea@example.com"
      },
      "es_titular": false,
      "por_asignar": false,
      "precio_asignado": "2340.00",
      "monto_pagado": "1500.00",
      "saldo_pendiente": "840.00",
      "esta_totalmente_pagado": false,
      "voucher_codigo": null,
      "voucher_id": null
    }
  ]
}
```

---

### Paso 2: Identificar pasajeros con voucher disponible

En la respuesta anterior, puedes identificar qué pasajeros tienen voucher generado revisando:

- **`voucher_id`**: Si tiene un valor numérico (ej: 153), el pasajero tiene voucher
- **`voucher_codigo`**: El código único del voucher (ej: "RSV-2025-0179-PAX-295-VOUCHER")
- **`esta_totalmente_pagado`**: Debe ser `true` para tener voucher

**En el ejemplo:**
- ✅ **Pasajero 295 (Victor Cubas)**: Tiene `voucher_id: 153` → **PUEDE DESCARGAR VOUCHER**
- ❌ **Pasajero 296 (Andrea Tutoria)**: Tiene `voucher_id: null` → **NO TIENE VOUCHER** (aún tiene saldo pendiente)

---

### Paso 3: Descargar el PDF del voucher

Una vez que tienes el `voucher_id`, puedes descargar el PDF del voucher.

**Endpoint:** `GET /api/vouchers/{voucher_id}/descargar-pdf/`

**Ejemplo:** `GET http://127.0.0.1:8000/api/vouchers/153/descargar-pdf/`

**Query params opcionales:**
- `regenerar=true` : Fuerza la regeneración del PDF incluso si ya existe

**Ejemplos de uso:**

```bash
# Descargar el PDF existente (o generarlo si no existe)
curl -O -J http://127.0.0.1:8000/api/vouchers/153/descargar-pdf/

# Forzar regeneración del PDF
curl -O -J "http://127.0.0.1:8000/api/vouchers/153/descargar-pdf/?regenerar=true"
```

**Respuesta:**
- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="voucher_RSV-2025-0179-PAX-295-VOUCHER.pdf"`
- **Cuerpo:** Archivo PDF descargable

---

## Condiciones para Generación de Vouchers

Un voucher se genera automáticamente cuando un pasajero cumple **AMBAS** condiciones:

1. ✅ **Tiene datos reales cargados** (`por_asignar = false`)
2. ✅ **Ha pagado el 100% de su precio asignado** (`esta_totalmente_pagado = true`)

Si un pasajero no cumple estas condiciones, tendrá `voucher_id: null` y `voucher_codigo: null`.

---

## Casos de Uso

### Caso 1: Mostrar botón "Descargar Voucher" en Frontend

```javascript
// Iterar sobre los pasajeros de la reserva
pasajeros.forEach(pasajero => {
  if (pasajero.voucher_id) {
    // Mostrar botón de descarga
    const downloadUrl = `/api/vouchers/${pasajero.voucher_id}/descargar-pdf/`;

    // <button onclick="window.open('${downloadUrl}')">
    //   Descargar Voucher - ${pasajero.voucher_codigo}
    // </button>
  } else {
    // Mostrar mensaje de voucher no disponible
    if (!pasajero.esta_totalmente_pagado) {
      // "Voucher no disponible: Saldo pendiente $${pasajero.saldo_pendiente}"
    } else if (pasajero.por_asignar) {
      // "Voucher no disponible: Datos del pasajero pendientes"
    }
  }
});
```

---

### Caso 2: Enviar voucher por email

```python
from apps.comprobante.models import Voucher
from django.core.mail import EmailMessage

def enviar_voucher_por_email(pasajero_id):
    """
    Envía el voucher de un pasajero por email
    """
    pasajero = Pasajero.objects.get(id=pasajero_id)

    # Verificar que tenga voucher
    if not hasattr(pasajero, 'voucher'):
        raise ValueError("El pasajero no tiene voucher generado")

    voucher = pasajero.voucher

    # Generar PDF si no existe
    if not voucher.pdf_generado:
        voucher.generar_pdf()
        voucher.save()

    # Enviar email
    email = EmailMessage(
        subject=f'Voucher - {voucher.codigo_voucher}',
        body=f'Estimado/a {pasajero.persona.nombre},\n\nAdjuntamos su voucher de viaje.',
        from_email='noreply@grouptours.com',
        to=[pasajero.persona.email],
    )

    email.attach_file(voucher.pdf_generado.path)
    email.send()

    print(f"[OK] Voucher enviado a {pasajero.persona.email}")
```

---

## Endpoints Relacionados

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/reservas/{id}/` | GET | Obtener detalles completos de una reserva (incluye pasajeros con voucher_id) |
| `/api/vouchers/` | GET | Listar todos los vouchers |
| `/api/vouchers/?reserva_id={id}` | GET | Listar vouchers de una reserva específica |
| `/api/vouchers/?pasajero_id={id}` | GET | Obtener voucher de un pasajero específico |
| `/api/vouchers/{id}/` | GET | Obtener detalles de un voucher |
| `/api/vouchers/{id}/descargar-pdf/` | GET | Descargar PDF del voucher |
| `/api/vouchers/{id}/regenerar_qr/` | POST | Regenerar código QR del voucher |

---

## Ejemplo Completo: Python Script

```python
"""
Script de ejemplo para descargar vouchers de una reserva
"""
import requests
import os

API_BASE_URL = "http://127.0.0.1:8000/api"
RESERVA_ID = 179
OUTPUT_DIR = "vouchers_descargados"

def descargar_vouchers_de_reserva(reserva_id):
    """
    Descarga todos los vouchers disponibles de una reserva
    """
    # Crear directorio de salida
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Paso 1: Obtener detalles de la reserva
    print(f"\n[INFO] Obteniendo detalles de reserva {reserva_id}...")
    response = requests.get(f"{API_BASE_URL}/reservas/{reserva_id}/")
    response.raise_for_status()
    reserva = response.json()

    print(f"[OK] Reserva: {reserva['codigo']}")
    print(f"[OK] Cantidad de pasajeros: {reserva['cantidad_pasajeros']}")

    # Paso 2: Iterar sobre los pasajeros
    vouchers_descargados = 0
    for pasajero in reserva['pasajeros']:
        nombre = f"{pasajero['persona']['nombre']} {pasajero['persona']['apellido']}"
        voucher_id = pasajero.get('voucher_id')

        if voucher_id:
            print(f"\n[INFO] Descargando voucher para {nombre}...")

            # Paso 3: Descargar el PDF del voucher
            pdf_url = f"{API_BASE_URL}/vouchers/{voucher_id}/descargar-pdf/"
            pdf_response = requests.get(pdf_url)
            pdf_response.raise_for_status()

            # Guardar el archivo
            filename = f"voucher_{pasajero['voucher_codigo']}.pdf"
            filepath = os.path.join(OUTPUT_DIR, filename)

            with open(filepath, 'wb') as f:
                f.write(pdf_response.content)

            print(f"[OK] Voucher guardado: {filepath}")
            vouchers_descargados += 1
        else:
            razon = "Saldo pendiente" if not pasajero['esta_totalmente_pagado'] else "Datos incompletos"
            print(f"\n[WARN] {nombre}: No tiene voucher ({razon})")

    print(f"\n" + "="*80)
    print(f"[RESUMEN] {vouchers_descargados} voucher(s) descargado(s)")
    print("="*80 + "\n")

if __name__ == '__main__':
    descargar_vouchers_de_reserva(RESERVA_ID)
```

---

## Notas Importantes

1. **Relación Pasajero-Voucher:** Cada pasajero puede tener UN solo voucher (relación OneToOne)

2. **Generación Automática:** Los vouchers se generan automáticamente cuando el pasajero cumple las condiciones. No es necesario crearlos manualmente.

3. **PDF Caching:** El PDF se genera una vez y se cachea. Si necesitas regenerarlo (por ejemplo, después de actualizar datos), usa el parámetro `?regenerar=true`

4. **Código QR:** Cada voucher incluye un código QR con el formato:
   ```
   VOUCHER:{codigo_voucher}
   PASAJERO:{nombre_completo}
   PAQUETE:{nombre_paquete}
   ```

5. **Contenido del PDF:** El voucher incluye toda la información del viaje:
   - Datos del pasajero
   - Información del paquete y tipo (Terrestre/Aéreo)
   - Fechas de salida y regreso
   - Hotel y tipo de habitación (sin número de habitación)
   - Servicios incluidos
   - Estado de pago
   - Aviso importante sobre extras del hotel

---

## Soporte

Para más información sobre el sistema de vouchers, consultar:
- `DOCUMENTACION_VOUCHERS.md` - Documentación completa del sistema
- `apps/comprobante/models.py:656` - Implementación del modelo Voucher
- `apps/comprobante/views.py:281` - Endpoint de descarga de PDF
