# Generated by Django 4.2 on 2024-03-09 22:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permiso', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='permiso',
            name='formulario',
            field=models.CharField(default='', max_length=50),
        ),
    ]
