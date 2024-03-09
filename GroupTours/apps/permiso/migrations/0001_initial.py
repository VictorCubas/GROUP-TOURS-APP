# Generated by Django 4.2 on 2024-03-09 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Permiso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50)),
                ('descripcion', models.CharField(default='', max_length=200)),
                ('tipo', models.CharField(default='', max_length=1)),
            ],
            options={
                'verbose_name': 'Permiso',
                'db_table': 'Permiso',
            },
        ),
    ]
