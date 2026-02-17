from django.db import migrations


TIPOS_BASE = [
    {"nombre": "Single",    "capacidad": 1},
    {"nombre": "Doble",     "capacidad": 2},
    {"nombre": "Triple",    "capacidad": 3},
    {"nombre": "Cuádruple", "capacidad": 4},
    {"nombre": "Suite",     "capacidad": 2},
    {"nombre": "Premium",   "capacidad": 2},
]

PREFIJO_A_BASE = [
    ("single",  "Single"),
    ("doble",   "Doble"),
    ("double",  "Doble"),
    ("triple",  "Triple"),
    ("cuadru",  "Cuádruple"),
    ("cuádru",  "Cuádruple"),
    ("suite",   "Suite"),
    ("premium", "Premium"),
]


def _resolver_base(nombre):
    """Dado un nombre como 'Doble 102', retorna 'Doble'."""
    nombre_lower = nombre.lower().strip()
    for prefijo, base in PREFIJO_A_BASE:
        if nombre_lower.startswith(prefijo):
            return base
    return None


def _reasignar_y_eliminar(apps, loser, winner):
    """
    Reasigna todas las referencias de `loser` a `winner` y luego elimina `loser`.
    Maneja correctamente los modelos con PROTECT y los unique_together.
    """
    Reserva = apps.get_model("reserva", "Reserva")
    CupoHabitacionSalida = apps.get_model("paquete", "CupoHabitacionSalida")
    PrecioCatalogoHabitacion = apps.get_model("paquete", "PrecioCatalogoHabitacion")
    HistorialPrecioHabitacion = apps.get_model("paquete", "HistorialPrecioHabitacion")
    SalidaPaquete = apps.get_model("paquete", "SalidaPaquete")

    # 1. Reservas (on_delete=PROTECT — crítico, reasignar antes de eliminar)
    Reserva.objects.filter(habitacion=loser).update(habitacion=winner)

    # 2. CupoHabitacionSalida (unique_together: salida + habitacion)
    for cupo_loser in CupoHabitacionSalida.objects.filter(habitacion=loser):
        cupo_winner = CupoHabitacionSalida.objects.filter(
            salida=cupo_loser.salida, habitacion=winner
        ).first()
        if cupo_winner:
            # Sumar cupos y borrar el del loser
            cupo_winner.cupo += cupo_loser.cupo
            cupo_winner.save(update_fields=["cupo"])
            cupo_loser.delete()
        else:
            # Reasignar al winner
            cupo_loser.habitacion = winner
            cupo_loser.save(update_fields=["habitacion"])

    # 3. PrecioCatalogoHabitacion (unique_together: salida + habitacion)
    for precio_loser in PrecioCatalogoHabitacion.objects.filter(habitacion=loser):
        precio_winner = PrecioCatalogoHabitacion.objects.filter(
            salida=precio_loser.salida, habitacion=winner
        ).first()
        if precio_winner:
            # El winner ya tiene precio para esa salida → eliminar el del loser
            precio_loser.delete()
        else:
            # Reasignar al winner
            precio_loser.habitacion = winner
            precio_loser.save(update_fields=["habitacion"])

    # 4. HistorialPrecioHabitacion (on_delete=CASCADE, sin unique_together relevante)
    HistorialPrecioHabitacion.objects.filter(habitacion=loser).update(habitacion=winner)

    # 5. SalidaPaquete.habitacion_fija (on_delete=SET_NULL — no es crítico pero mejor conservar)
    SalidaPaquete.objects.filter(habitacion_fija=loser).update(habitacion_fija=winner)

    # 6. Eliminar el loser (ahora seguro: PROTECT liberado, CASCADE sin datos)
    loser.delete()


def simplificar_tipos(apps, schema_editor):
    TipoHabitacion = apps.get_model("hotel", "TipoHabitacion")
    Habitacion = apps.get_model("hotel", "Habitacion")
    Reserva = apps.get_model("reserva", "Reserva")

    # ── 1. Crear los 6 tipos base ──
    tipos_base_obj = {}
    for data in TIPOS_BASE:
        obj, _ = TipoHabitacion.objects.get_or_create(
            nombre=data["nombre"],
            defaults={"capacidad": data["capacidad"], "activo": True},
        )
        tipos_base_obj[data["nombre"]] = obj

    nombres_base = set(tipos_base_obj.keys())

    # ── 2. Detectar conflictos: hoteles con >1 habitación del mismo tipo base ──
    from collections import defaultdict
    hotel_base_habs = defaultdict(list)

    for hab in Habitacion.objects.select_related("tipo_habitacion", "hotel").all():
        base = _resolver_base(hab.tipo_habitacion.nombre)
        if base:
            hotel_base_habs[(hab.hotel_id, base)].append(hab)

    # ── 3. Para cada conflicto, conservar la que tiene más reservas (o menor id) ──
    for (hotel_id, base), habs in hotel_base_habs.items():
        if len(habs) > 1:
            habs_ordenadas = sorted(
                habs,
                key=lambda h: (-Reserva.objects.filter(habitacion_id=h.id).count(), h.id)
            )
            winner = habs_ordenadas[0]
            for loser in habs_ordenadas[1:]:
                _reasignar_y_eliminar(apps, loser, winner)

    # ── 4. Reasignar habitaciones restantes al tipo base ──
    for hab in Habitacion.objects.select_related("tipo_habitacion").all():
        nombre_actual = hab.tipo_habitacion.nombre
        if nombre_actual in nombres_base:
            continue

        base = _resolver_base(nombre_actual)
        if base and base in tipos_base_obj:
            hab.tipo_habitacion = tipos_base_obj[base]
            hab.save(update_fields=["tipo_habitacion"])

    # ── 5. Eliminar tipos viejos sin habitaciones ──
    TipoHabitacion.objects.exclude(
        nombre__in=list(nombres_base)
    ).filter(
        habitaciones__isnull=True
    ).delete()

    # ── 6. Desactivar tipos viejos que aún tengan relaciones ──
    TipoHabitacion.objects.exclude(
        nombre__in=list(nombres_base)
    ).update(activo=False)


def revertir(apps, schema_editor):
    """Reverse: no-op, no se pueden reconstruir los nombres originales."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("hotel", "0014_eliminar_campos_legacy_habitacion"),
        ("reserva", "0001_initial"),
        ("paquete", "0016_preciocatalogohotel"),
    ]

    operations = [
        migrations.RunPython(simplificar_tipos, revertir),
    ]
