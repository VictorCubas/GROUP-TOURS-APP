# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GroupTours is a Django REST Framework application for managing group tour packages, reservations, hotels, and related tourism business operations. The system handles package creation, pricing, seasonal variations, reservations with passengers, and includes a role-based permission system.

## Technology Stack

- Django 4.2
- Django REST Framework 3.14.0
- PostgreSQL (psycopg2)
- JWT Authentication (djangorestframework-simplejwt)
- Django Polymorphic 4.1.0
- Django CORS Headers 4.7.0
- Python-dotenv for environment configuration

## Development Setup

### Initial Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create PostgreSQL database named `GroupTours`

3. Create `.env` file in `GroupTours/` directory with:
   ```
   DBUSER=postgres
   DBPASS=your_password
   DATABASE_URL=postgresql://user:password@host:port/dbname
   SECRET_KEY=your_secret_key
   ```

4. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. Start development server:
   ```bash
   python manage.py runserver
   ```

### Common Commands

- Run migrations: `python manage.py makemigrations && python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`
- Run server: `python manage.py runserver`
- Django shell: `python manage.py shell`
- Check for issues: `python manage.py check`

## Architecture

### Application Structure

The project follows Django's app-based architecture with 26 specialized apps under `apps/`:

**Core Business Logic:**
- `paquete/` - Tour packages with flexible/fixed modalities, seasonality, departures (SalidaPaquete), room quotas (CupoHabitacionSalida)
- `reserva/` - Reservations with state machine (pendiente → confirmada → incompleta → finalizada → cancelada)
- `hotel/` - Hotels with chains (CadenaHotelera), rooms (Habitacion), and services
- `servicio/` - Services that can be associated with packages, hotels, and rooms

**Supporting Entities:**
- `persona/` - Polymorphic person model: PersonaFisica (physical) and PersonaJuridica (legal entity)
- `usuario/` - Custom user model extending AbstractUser, linked to Empleado
- `empleado/` - Employees with positions and remuneration types
- `rol/` and `permiso/` - Role-based permission system
- `moneda/` - Currency management for multi-currency support
- `destino/` - Travel destinations
- `ciudad/` - Cities linked to hotels
- `zona_geografica/` - Geographic zones

**Other Apps:**
- `distribuidora/`, `facturacion/`, `tipo_paquete/`, `tipo_documento/`, `nacionalidad/`, `puesto/`, `tipo_remuneracion/`, `modulo/`, `login/`, `login_token/`, `logout/`, `home/`

### Key Models and Relationships

**Package System:**
- `Paquete` → base package with tipo_paquete, destino, moneda, modalidad (flexible/fijo)
- `SalidaPaquete` → specific departure dates with pricing, seasons, hotels, and quotas
- `CupoHabitacionSalida` → room-specific quotas per departure (many-to-many through model)
- `PaqueteServicio` → services included in package with pricing
- `Temporada` → seasons affecting pricing
- `HistorialPrecioPaquete` and `HistorialPrecioHabitacion` → price history tracking

**Reservation System:**
- `Reserva` → has titular (PersonaFisica), paquete, cantidad_pasajeros, monto_pagado, estado
- `Pasajero` → links PersonaFisica to Reserva with ticket/voucher info
- Estado flow: pendiente (created) → confirmada (down payment) → incompleta (missing passenger data) → finalizada (complete)
- Validates capacity using `Reserva.clean()` method

**User and Permission System:**
- `Usuario` (custom AUTH_USER_MODEL) → extends AbstractUser, links to Empleado
- `Empleado` → links to PersonaFisica, has Puesto and TipoRemuneracion
- `Rol` → many-to-many with Usuario, has permissions
- `Permiso` → granular permissions linked to Modulo

**Hotel System:**
- `CadenaHotelera` → hotel chains
- `Hotel` → individual hotels with ciudad, cadena, servicios, estrellas
- `Habitacion` → rooms with tipo (single/doble/triple/suite/premium), precio_noche, moneda, servicios

### API Structure

All API endpoints are prefixed with `/api/` and defined in `apps/api/urls.py`:

- `/api/login/` - Authentication (JWT)
- `/api/roles/` - Role management
- `/api/permisos/` - Permission management
- `/api/personas/` - Person management (polymorphic)
- `/api/usuarios/` - User management
- `/api/empleados/` - Employee management
- `/api/paquete/` - Package CRUD
- `/api/hotel/` - Hotel and room management
- `/api/reservas/` - Reservation management
- `/api/moneda/` - Currency management
- `/api/destino/` - Destination management
- `/api/ciudad/` - City management
- `/api/zona_geografica/` - Geographic zone management

### Authentication and Permissions

- JWT tokens with 1-day lifetime (ACCESS_TOKEN_LIFETIME)
- All endpoints require authentication by default (`IsAuthenticated`)
- Auth header format: `Authorization: Bearer <token>`
- Custom user model at `apps.usuario.Usuario`

### Important Business Logic

**Package Pricing:**
- `SalidaPaquete.calcular_precio_venta()` - Calculates suggested sale price based on:
  - For propio packages: precio_actual * (1 + ganancia/100)
  - For non-propio: precio_actual * (1 + comision/100)
- Price ranges: `precio_actual` (min) to `precio_final` (max) based on room types
- `create_salida_paquete()` - Transaction-wrapped function that calculates price ranges from hotel rooms

**Price History:**
- `SalidaPaquete.change_price()` - Updates price and creates history entry
- Marks previous price as not vigente before creating new entry

**Reservation State Management:**
- `Reserva.actualizar_estado()` - Updates state based on payment and passenger data
- `Reserva.puede_confirmarse()` - Checks if seña total is paid
- Auto-generates reservation code: `RSV-{year}-{sequential}`

**Room Quotas:**
- `CupoHabitacionSalida` - Allows different quotas per room type in a departure
- For terrestre propio packages, also track global cupo on SalidaPaquete

### Database Configuration

- Uses `dj-database-url` for connection string parsing
- Production: `DATABASE_URL` environment variable
- Local development: Supports commented-out direct PostgreSQL config
- Includes AWS RDS configuration example (commented)

### Settings Notes

- Language: Spanish (`LANGUAGE_CODE = 'es'`)
- Timezone: `America/Asuncion`
- CORS enabled for `https://group-tours-gamma.vercel.app`
- Static files: Whitenoise for production with compression
- Media files: Stored in `media/` directory
- Email: SMTP configured with Gmail (credentials in settings.py - should be moved to env vars)
- Pagination: 5 items per page by default
- DEBUG mode: Disabled when `RENDER` env var is present

### File Uploads

- Package images: `media/paquetes/`
- Uses Pillow for image processing

## Development Guidelines

### When Creating Models

- All models should have `activo` boolean field (soft delete pattern)
- Include `fecha_creacion` and `fecha_modificacion` timestamps
- Use `related_name` on all foreign keys
- Add `help_text` to fields for documentation
- Use `db_table` in Meta for explicit table naming
- Use `verbose_name` and `verbose_name_plural` in Meta

### When Working with Packages

- Always use `create_salida_paquete()` function rather than creating SalidaPaquete directly
- Remember that SalidaPaquete can have either a single habitacion_fija OR multiple room quotas via CupoHabitacionSalida
- When updating prices, use `change_price()` method to maintain history
- Call `calcular_precio_venta()` after price changes

### When Working with Reservations

- Always call `Reserva.actualizar_estado()` after payment or passenger changes
- Check `Reserva.clean()` validates capacity before save
- Titular must be a PersonaFisica (not PersonaJuridica)
- Pasajeros are separate from titular; es_titular flag indicates if passenger is the titular

### Polymorphic Models

- `Persona` has two concrete types: `PersonaFisica` and `PersonaJuridica`
- Use Django Polymorphic library for queries
- PersonaFisica has edad property (calculated from fecha_nacimiento)

### Testing and Debugging

- Admin panel available at `/admin/`
- Use Django shell for quick model testing
- Check database directly for complex queries
- JWT tokens can be tested via browsable API in development

## Codebase Patterns

### Decimal Handling

Uses helper function for safe decimal conversion:
```python
def _to_decimal(value):
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
```

### State Machines

Reserva uses explicit state choices with business logic methods to transition states rather than direct field updates.

### Transaction Safety

Critical operations like `create_salida_paquete()` use `@transaction.atomic` decorator.

### Validation

- Model-level validation in `clean()` methods
- Use `ValidationError` from `django.core.exceptions`
- Validate business rules at model level, not just view/serializer level

## Known Considerations

- Email credentials are hardcoded in settings.py - should be moved to environment variables
- Some URL patterns in main urls.py are commented out but may be active through api/urls.py
- The system supports both DATABASE_URL (dj-database-url) and direct PostgreSQL config
- Package modalidad (flexible/fijo) affects how departures and rooms are handled
- Zona geografica is accessible as property on Paquete via destino relationship
