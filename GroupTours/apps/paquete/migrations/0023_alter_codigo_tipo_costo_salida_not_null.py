from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paquete', '0022_add_codigo_to_tipo_costo_salida'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tipocostosalida',
            name='codigo',
            field=models.CharField(
                max_length=50,
                unique=True,
                help_text='Código estable para identificar el tipo (ej: BUS, COORDINADOR). No debe cambiarse una vez creado.'
            ),
        ),
    ]
