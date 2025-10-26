# 📄 Solución: PDFs en Producción (Render.com)

## ❌ Problema Actual

El método actual guarda PDFs en `media/comprobantes/pdf/`, lo cual **NO funciona en Render** porque:
- El sistema de archivos es efímero (se borra al reiniciar)
- No hay persistencia entre despliegues
- No funciona con múltiples instancias

---

## ✅ Solución 1: AWS S3 (Producción Real)

### Pasos:

1. **Instalar dependencias:**
```bash
pip install boto3 django-storages
```

2. **Actualizar `requirements.txt`:**
```
boto3==1.34.19
django-storages==1.14.2
```

3. **Crear bucket en AWS S3:**
   - Ir a console.aws.amazon.com
   - Crear bucket (ej: `grouptours-media`)
   - Configurar permisos públicos de lectura
   - Obtener Access Key y Secret Key

4. **Agregar al final de `settings.py`:**

```python
# ============================================
# CONFIGURACIÓN DE ALMACENAMIENTO DE ARCHIVOS
# ============================================

if os.getenv('RENDER'):  # Producción
    # Usar AWS S3 para archivos media
    INSTALLED_APPS += ['storages']

    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'grouptours-media')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

    # Configuración S3
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = 'public-read'
    AWS_LOCATION = 'media'

    # Backend de almacenamiento
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'

else:  # Desarrollo local
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

5. **Variables de entorno en Render:**
```
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_STORAGE_BUCKET_NAME=grouptours-media
AWS_S3_REGION_NAME=us-east-1
```

6. **¡Listo!** Django guardará automáticamente los PDFs en S3.

---

## ✅ Solución 2: PDF en Memoria (Temporal, sin guardar)

Si no quieres S3 por ahora, genera el PDF **en tiempo real** sin guardarlo:

### Modificar `apps/comprobante/views.py`:

```python
@action(detail=True, methods=['get'], url_path='descargar-pdf')
def descargar_pdf(self, request, pk=None):
    """
    Genera PDF en memoria sin guardarlo.
    Funciona en cualquier plataforma.
    """
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    from io import BytesIO

    comprobante = self.get_object()

    # Crear buffer en memoria
    buffer = BytesIO()

    # Generar PDF (mismo código que generar_pdf pero sin guardar)
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ... [todo el código de generación] ...

    c.save()

    # Retornar desde memoria
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f'comprobante_{comprobante.numero_comprobante}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
```

**Ventajas:**
- ✅ Funciona en Render sin configuración adicional
- ✅ No consume espacio de almacenamiento
- ✅ Siempre genera PDF actualizado

**Desventajas:**
- ❌ Más lento (genera cada vez)
- ❌ No se puede acceder directamente a la URL del PDF
- ❌ Mayor uso de CPU

---

## 🎯 Recomendación

### Para Desarrollo/MVP:
→ **Solución 2** (PDF en memoria)

### Para Producción Real:
→ **Solución 1** (AWS S3)

---

## 📊 Comparación

| Característica | Local (actual) | PDF en memoria | AWS S3 |
|---------------|----------------|----------------|--------|
| Funciona en Render | ❌ | ✅ | ✅ |
| Guarda archivos | ✅ | ❌ | ✅ |
| Requiere config | ❌ | ❌ | ✅ |
| Costo | Gratis | Gratis | ~$0.02/GB |
| Velocidad | ⚡⚡⚡ | ⚡⚡ | ⚡⚡⚡ |
| Escalable | ❌ | ✅ | ✅ |
| URLs persistentes | ✅ | ❌ | ✅ |

---

## 🚀 ¿Qué hacer ahora?

**Opción A: Quick Fix (5 min)**
→ Implementar Solución 2 (PDF en memoria)
→ Funciona inmediatamente en Render

**Opción B: Solución Definitiva (30 min)**
→ Configurar AWS S3
→ Mejor para producción a largo plazo

---

## 💡 Otras alternativas:

### Cloudinary
```bash
pip install cloudinary django-cloudinary-storage
```
- Más fácil que S3
- Capa gratuita: 25GB almacenamiento

### Backblaze B2
- Compatible con S3
- Más barato que AWS
- 10GB gratis

### PostgreSQL (para PDFs pequeños)
- Guardar PDF como bytea en la BD
- No recomendado para muchos archivos

---

## 📝 Resumen

**El método actual NO funciona en Render.**

**Solución rápida:**
```python
# Generar en memoria, no guardar
buffer = BytesIO()
# ... generar PDF ...
return HttpResponse(buffer, content_type='application/pdf')
```

**Solución definitiva:**
```bash
pip install boto3 django-storages
# Configurar S3 en settings.py
# Agregar variables de entorno en Render
```

---

Fecha: 23/10/2025
