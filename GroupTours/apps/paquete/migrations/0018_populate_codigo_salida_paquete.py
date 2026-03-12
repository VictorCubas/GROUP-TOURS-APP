from django.db import migrations


def generar_codigos(apps, schema_editor):
    SalidaPaquete = apps.get_model("paquete", "SalidaPaquete")

    salidas_sin_codigo = SalidaPaquete.objects.filter(codigo__isnull=True).order_by("fecha_creacion", "id")

    for salida in salidas_sin_codigo:
        year = salida.fecha_creacion.year
        ultimo_num = SalidaPaquete.objects.filter(
            fecha_creacion__year=year,
            codigo__startswith=f"SAL-{year}-"
        ).count() + 1
        salida.codigo = f"SAL-{year}-{ultimo_num:04d}"
        salida.save(update_fields=["codigo"])


def revertir_codigos(apps, schema_editor):
    SalidaPaquete = apps.get_model("paquete", "SalidaPaquete")
    SalidaPaquete.objects.update(codigo=None)


class Migration(migrations.Migration):

    dependencies = [
        ("paquete", "0017_add_codigo_to_salida_paquete"),
    ]

    operations = [
        migrations.RunPython(generar_codigos, revertir_codigos),
    ]
