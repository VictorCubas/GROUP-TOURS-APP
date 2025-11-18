# Generated manually - Data migration
from django.db import migrations


def crear_modulos_y_permisos(apps, schema_editor):
    """
    Crea los módulos faltantes (Aperturas, Cierres, Movimientos, Paquetes)
    y asigna los permisos correspondientes al rol 'Cajero'
    """
    Modulo = apps.get_model('modulo', 'Modulo')
    Permiso = apps.get_model('permiso', 'Permiso')
    Rol = apps.get_model('rol', 'Rol')
    RolesPermisos = apps.get_model('rol', 'RolesPermisos')

    # Definición de módulos a crear
    modulos_data = [
        {
            'nombre': 'Aperturas',
            'descripcion': 'Gestión de aperturas de caja',
            'permisos': ['R', 'C', 'E']  # Leer, Crear, Exportar
        },
        {
            'nombre': 'Cierres',
            'descripcion': 'Gestión de cierres de caja',
            'permisos': ['R', 'C', 'E']  # Leer, Crear, Exportar
        },
        {
            'nombre': 'Movimientos',
            'descripcion': 'Registro de movimientos de efectivo',
            'permisos': ['R', 'C', 'E']  # Leer, Crear, Exportar
        },
        {
            'nombre': 'Paquetes',
            'descripcion': 'Consulta de información de paquetes de viajes',
            'permisos': ['R']  # Solo Leer
        }
    ]

    # Mapeo de tipos de permisos a nombres descriptivos
    tipo_permiso_nombres = {
        'C': 'Creacion',
        'R': 'Lectura',
        'U': 'Modificacion',
        'D': 'Eliminacion',
        'E': 'Exportar'
    }

    # Obtener o crear el rol Cajero
    rol_cajero, created = Rol.objects.get_or_create(
        nombre='Cajero',
        defaults={
            'descripcion': 'Rol para gestión de cajas y operaciones de efectivo',
            'activo': True,
            'es_admin': False,
            'en_uso': False
        }
    )

    if created:
        print(f"[OK] Rol 'Cajero' creado")
    else:
        print(f"[OK] Rol 'Cajero' ya existe")

    # Procesar cada módulo
    for modulo_data in modulos_data:
        # Crear o obtener el módulo
        modulo, modulo_created = Modulo.objects.get_or_create(
            nombre=modulo_data['nombre'],
            defaults={
                'descripcion': modulo_data['descripcion'],
                'activo': True,
                'en_uso': False
            }
        )

        if modulo_created:
            print(f"[OK] Modulo '{modulo_data['nombre']}' creado")
        else:
            print(f"[OK] Modulo '{modulo_data['nombre']}' ya existe")

        # Crear todos los permisos para este módulo (C, R, U, D, E)
        for tipo_permiso, nombre_tipo in tipo_permiso_nombres.items():
            permiso_nombre = f"{modulo_data['nombre']}_{nombre_tipo}"

            permiso, permiso_created = Permiso.objects.get_or_create(
                nombre=permiso_nombre,
                modulo=modulo,
                defaults={
                    'descripcion': f"{nombre_tipo} en {modulo_data['nombre']}",
                    'tipo': tipo_permiso,
                    'activo': True,
                    'en_uso': False
                }
            )

            if permiso_created:
                print(f"  [OK] Permiso '{permiso_nombre}' creado")

            # Si este permiso está en la lista de permisos a asignar al rol Cajero
            if tipo_permiso in modulo_data['permisos']:
                # Verificar si ya existe la relación
                relacion_existe = RolesPermisos.objects.filter(
                    rol=rol_cajero,
                    permiso=permiso
                ).exists()

                if not relacion_existe:
                    RolesPermisos.objects.create(
                        rol=rol_cajero,
                        permiso=permiso
                    )
                    print(f"    [OK] Permiso '{permiso_nombre}' asignado al rol Cajero")
                else:
                    print(f"    [OK] Permiso '{permiso_nombre}' ya estaba asignado al rol Cajero")

    print("\n[OK] Migracion completada exitosamente")


def revertir_modulos_y_permisos(apps, schema_editor):
    """
    Función de reversión: Elimina los permisos del rol Cajero y los módulos creados
    (solo si no están en uso)
    """
    Modulo = apps.get_model('modulo', 'Modulo')
    Permiso = apps.get_model('permiso', 'Permiso')
    Rol = apps.get_model('rol', 'Rol')
    RolesPermisos = apps.get_model('rol', 'RolesPermisos')

    modulos_nombres = ['Aperturas', 'Cierres', 'Movimientos', 'Paquetes']

    try:
        rol_cajero = Rol.objects.get(nombre='Cajero')

        # Eliminar relaciones de permisos para estos módulos
        for nombre_modulo in modulos_nombres:
            try:
                modulo = Modulo.objects.get(nombre=nombre_modulo)
                permisos = Permiso.objects.filter(modulo=modulo)

                # Eliminar relaciones con el rol Cajero
                RolesPermisos.objects.filter(
                    rol=rol_cajero,
                    permiso__in=permisos
                ).delete()

                print(f"[OK] Relaciones de permisos eliminadas para modulo '{nombre_modulo}'")

                # Eliminar permisos si no están en uso
                permisos.filter(en_uso=False).delete()

                # Eliminar módulo si no está en uso
                if not modulo.en_uso:
                    modulo.delete()
                    print(f"[OK] Modulo '{nombre_modulo}' eliminado")

            except Modulo.DoesNotExist:
                print(f"[ERROR] Modulo '{nombre_modulo}' no existe")

    except Rol.DoesNotExist:
        print("[ERROR] Rol 'Cajero' no existe")

    print("\n[OK] Reversion completada")


class Migration(migrations.Migration):

    dependencies = [
        ('modulo', '0006_modulo_en_uso'),
        ('permiso', '0013_alter_permiso_nombre'),
        ('rol', '0006_rol_es_admin'),
    ]

    operations = [
        migrations.RunPython(
            crear_modulos_y_permisos,
            reverse_code=revertir_modulos_y_permisos
        ),
    ]
