# 📝 Management Commands - Dashboard

## Comandos Disponibles

### `populate_database`

Puebla la base de datos con datos dummy coherentes y realistas para desarrollo y testing.

#### Uso Básico

```bash
python manage.py populate_database
```

#### Opciones

- `--clear`: Elimina todos los datos antes de poblar (requiere confirmación)

```bash
python manage.py populate_database --clear
```

#### Características

✨ **Datos Realistas y Coherentes**
- Hoteles reales con precios de mercado
- Destinos turísticos populares
- Monedas con cotizaciones actualizadas
- Relaciones consistentes entre entidades

🎯 **Cobertura Completa**
- 7 niveles de datos (desde maestros hasta transaccionales)
- 6 reservas con estados diversos
- 5 paquetes turísticos (propios y de distribuidoras)
- 5 usuarios del sistema con roles diferenciados

🔄 **Idempotente**
- Se puede ejecutar múltiples veces
- Usa `get_or_create` para evitar duplicados
- Maneja errores gracefully

📊 **Información Detallada**
- Muestra progreso por nivel
- Resumen final con estadísticas
- Tabla visual de datos creados

#### Estructura de Datos

```
NIVEL 1: Datos Maestros Base
├── Zonas Geográficas (7)
├── Nacionalidades (10)
├── Ciudades (37)
├── Monedas (5)
├── Cotizaciones (~200)
└── Tipos de Documento (5)

NIVEL 2: Servicios y Recursos
├── Tipos de Paquetes (3)
├── Distribuidoras (5)
├── Servicios (24)
├── Hoteles (9)
├── Habitaciones (31)
├── Personas Físicas (16)
└── Empleados (5)

NIVEL 3: Usuarios y Destinos
├── Módulos (8)
├── Permisos (40)
├── Roles (4)
├── Usuarios (5)
└── Destinos (5)

NIVEL 4: Paquetes
├── Temporadas (4)
├── Paquetes (5)
└── Salidas (7)

NIVEL 5: Reservas
├── Reservas (6)
└── Pasajeros (20)

NIVEL 6: Comprobantes
└── Estructura preparada

NIVEL 7: Facturación
├── Empresa (1)
├── Establecimiento (1)
├── Punto de Expedición (1)
├── Timbrado (1)
└── Aperturas de Caja (2)
```

#### Ejemplos de Datos Creados

**Usuarios de Prueba:**
```
admin / admin123 (Administrador)
diego.romero / vendedor123 (Vendedor)
sofia.acosta / contador123 (Contador)
marcos.vendedor / vendedor123 (Vendedor)
carmen.supervisor / supervisor123 (Supervisor)
```

**Reservas Ejemplo:**
- `RSV-2025-0001`: Río de Janeiro - FINALIZADA (pagado 100%)
- `RSV-2025-0002`: Buenos Aires - CONFIRMADA INCOMPLETA
- `RSV-2025-0003`: Miami - CONFIRMADA (faltan 2 pasajeros)
- `RSV-2025-0004`: Cancún - PENDIENTE
- `RSV-2025-0005`: Río de Janeiro - CANCELADA
- `RSV-2025-0006`: Bariloche - CONFIRMADA COMPLETA

#### Verificación

```python
# Ejecutar después de poblar
python manage.py shell

from apps.reserva.models import Reserva
print(f"Total reservas: {Reserva.objects.count()}")

from apps.paquete.models import Paquete
print(f"Total paquetes: {Paquete.objects.count()}")

from apps.usuario.models import Usuario
print(f"Total usuarios: {Usuario.objects.count()}")
```

#### Troubleshooting

**Error: No existe cotización de USD**
```python
from apps.moneda.models import Moneda, CotizacionMoneda
from datetime import date
from decimal import Decimal

usd = Moneda.objects.get(codigo='USD')
CotizacionMoneda.objects.create(
    moneda=usd,
    fecha_vigencia=date.today(),
    valor_en_guaranies=Decimal('7300')
)
```

**Error: Duplicate key**
```bash
# Limpiar todo y repoblar
python manage.py populate_database --clear
```

#### Documentación Completa

- Ver: `GroupTours/apps/dashboard/DATOS_DUMMY_DOCUMENTACION.md`
- Quick Start: `GroupTours/QUICK_START_DATOS_DUMMY.md`

#### Mantenimiento

Para actualizar el comando:
1. Editar: `populate_database.py`
2. Seguir el orden de dependencias
3. Usar `@transaction.atomic` para consistencia
4. Mostrar progreso con `self.stdout.write()`
5. Documentar cambios en este README

#### Autor

Sistema GroupTours - Noviembre 2025

---

**Nota**: Este comando es solo para desarrollo y testing. NO ejecutar en producción con datos reales.

