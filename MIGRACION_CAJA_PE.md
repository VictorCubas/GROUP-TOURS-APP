# Plan de Migración: Caja → Relación 1:1 con PuntoExpedicion

## Cambios Realizados

### 1. Modelo Caja
- ✅ Cambiado `ForeignKey` → `OneToOneField`
- ✅ Cambiado `related_name='cajas'` → `related_name='caja'`
- ✅ Cambiado `on_delete=SET_NULL` → `on_delete=PROTECT`
- ✅ Eliminado campo `emite_facturas` (todas las cajas emiten facturas)
- ✅ Eliminado campo `ubicacion` (no necesario)
- ✅ Campo `punto_expedicion` ahora es OBLIGATORIO (no nullable)

### 2. Validaciones
- ✅ Validación de que punto_expedicion no esté usado por otra caja
- ✅ Validación de que punto_expedicion sea obligatorio

### 3. Serializers
- ✅ Eliminado `emite_facturas` de fields
- ✅ Eliminado `ubicacion` de fields
- ✅ Agregada validación de unicidad de PE en `CajaCreateSerializer`

### 4. Views
- ✅ Eliminado `emite_facturas` de filtros
- ⚠️ Falta agregar endpoint `puntos-expedicion-disponibles`

### 5. Admin
- ✅ Eliminado `emite_facturas` y `ubicacion` de list_display y fieldsets
- ✅ Agregado `numero_caja` a readonly_fields

## Migración de Datos Necesaria

### Paso 1: Preparar datos existentes

Antes de ejecutar las migraciones, necesitas asegurar que:
1. **Todas las cajas tengan un punto de expedición asignado**
2. **No haya dos cajas usando el mismo PE**

### Paso 2: Script de preparación

```bash
cd GroupTours
python manage.py shell
```

```python
from apps.arqueo_caja.models import Caja
from apps.facturacion.models import PuntoExpedicion, Establecimiento

# Verificar cajas sin PE
cajas_sin_pe = Caja.objects.filter(punto_expedicion__isnull=True)
print(f"Cajas sin PE: {cajas_sin_pe.count()}")

# Verificar PEs compartidos
from django.db.models import Count
pes_compartidos = Caja.objects.filter(
    punto_expedicion__isnull=False
).values('punto_expedicion').annotate(
    num_cajas=Count('id')
).filter(num_cajas__gt=1)

print(f"PEs compartidos: {len(list(pes_compartidos))}")

# Si hay cajas sin PE, crearles uno
if cajas_sin_pe.exists():
    establecimiento = Establecimiento.objects.first()

    for caja in cajas_sin_pe:
        # Crear PE con el mismo código que la caja
        pe = PuntoExpedicion.objects.create(
            nombre=f"PE {caja.nombre}",
            establecimiento=establecimiento,
            codigo=caja.numero_caja,
            descripcion=f"Auto-generado para {caja.nombre}"
        )
        caja.punto_expedicion = pe
        caja.save()
        print(f"✅ Creado PE {pe.codigo} para Caja {caja.numero_caja}")

# Si hay PEs compartidos, crear nuevos PEs
for pe_data in pes_compartidos:
    pe_id = pe_data['punto_expedicion']
    cajas_compartidas = Caja.objects.filter(punto_expedicion_id=pe_id)

    # Mantener la primera caja con el PE original
    primera_caja = cajas_compartidas.first()
    print(f"ℹ️  Caja {primera_caja.numero_caja} mantiene PE {primera_caja.punto_expedicion.codigo}")

    # Crear nuevos PEs para las demás
    for caja in cajas_compartidas.exclude(pk=primera_caja.pk):
        nuevo_pe = PuntoExpedicion.objects.create(
            nombre=f"PE {caja.nombre}",
            establecimiento=caja.punto_expedicion.establecimiento,
            codigo=caja.numero_caja,
            descripcion=f"Auto-generado para {caja.nombre}"
        )
        caja.punto_expedicion = nuevo_pe
        caja.save()
        print(f"✅ Creado PE {nuevo_pe.codigo} para Caja {caja.numero_caja}")

print("✅ Datos preparados para migración")
```

### Paso 3: Ejecutar migraciones

```bash
python manage.py makemigrations arqueo_caja
python manage.py migrate arqueo_caja
```

## Endpoint Faltante

Necesitas agregar este endpoint en `views.py`:

```python
@action(detail=False, methods=['get'], url_path='puntos-expedicion-disponibles', pagination_class=None)
def puntos_expedicion_disponibles(self, request):
    """
    Retorna la lista de Puntos de Expedición que NO tienen una caja asignada.
    """
    from apps.facturacion.models import PuntoExpedicion
    from apps.facturacion.serializers import PuntoExpedicionSerializer

    pes_disponibles = PuntoExpedicion.objects.filter(
        activo=True
    ).exclude(
        caja__isnull=False
    ).select_related('establecimiento')

    serializer = PuntoExpedicionSerializer(pes_disponibles, many=True)
    return Response(serializer.data)
```

## Frontend - Cambios Necesarios

### API Response (antes):
```json
{
  "nombre": "Caja Principal",
  "punto_expedicion": 3,
  "emite_facturas": true,
  "ubicacion": "Mostrador 1",
  "descripcion": "..."
}
```

### API Response (después):
```json
{
  "nombre": "Caja Principal",
  "punto_expedicion": 3,
  "descripcion": "..."
}
```

### Cambios en formulario:
1. ✅ Eliminar campo `emite_facturas` (todas emiten)
2. ✅ Eliminar campo `ubicacion`
3. ✅ Campo `punto_expedicion` es OBLIGATORIO
4. ⚠️ Cargar solo PEs disponibles: `GET /api/cajas/puntos-expedicion-disponibles/`

### Ejemplo de carga de PEs disponibles:
```javascript
// ANTES: Cargar todos
const response = await api.get('/api/puntos-expedicion/');

// DESPUÉS: Cargar solo disponibles
const response = await api.get('/api/cajas/puntos-expedicion-disponibles/');
```

## Validaciones

- ✅ No se puede crear caja sin punto_expedicion
- ✅ No se puede asignar un PE que ya tiene otra caja
- ✅ No se puede eliminar un PE si tiene una caja asignada (PROTECT)
- ✅ Al actualizar caja, validar que el nuevo PE esté disponible

## Testing

1. Crear nueva caja → debe tener PE obligatorio
2. Intentar asignar mismo PE a dos cajas → debe fallar
3. Listar PEs disponibles → no debe mostrar los que tienen caja
4. Intentar eliminar PE con caja → debe fallar
