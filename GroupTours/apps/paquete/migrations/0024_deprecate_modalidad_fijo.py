from django.db import migrations


def normalizar_modalidad(apps, schema_editor):
    Paquete = apps.get_model("paquete", "Paquete")
    SalidaPaquete = apps.get_model("paquete", "SalidaPaquete")

    actualizados = Paquete.objects.filter(modalidad="fijo").update(modalidad="flexible")
    nulleados = SalidaPaquete.objects.filter(
        habitacion_fija__isnull=False
    ).update(habitacion_fija=None)

    print(f"\n  [0024] Paquetes fijo → flexible: {actualizados}")
    print(f"  [0024] Salidas habitacion_fija → null: {nulleados}")


def revertir_normalizar_modalidad(apps, schema_editor):
    # No se puede revertir de forma segura — los datos originales se pierden.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("paquete", "0023_alter_codigo_tipo_costo_salida_not_null"),
    ]

    operations = [
        migrations.RunPython(
            normalizar_modalidad,
            revertir_normalizar_modalidad,
        ),
    ]
