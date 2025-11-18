# Generated manually - Data migration
from django.db import migrations


def crear_rol_contador_y_permisos(apps, schema_editor):
    """
    Crea el rol 'Contador', el módulo 'Cotizaciones' y asigna los permisos correspondientes.

    IMPORTANTE: El módulo 'Cotizaciones' es EXCLUSIVO del rol Contador.
    NO se debe asignar a ningún otro rol (incluido Admin/Gerente).
    """
    Modulo = apps.get_model('modulo', 'Modulo')
    Permiso = apps.get_model('permiso', 'Permiso')
    Rol = apps.get_model('rol', 'Rol')
    RolesPermisos = apps.get_model('rol', 'RolesPermisos')

    # Mapeo de tipos de permisos a nombres descriptivos
    tipo_permiso_nombres = {
        'C': 'Creacion',
        'R': 'Lectura',
        'U': 'Modificacion',
        'D': 'Eliminacion',
        'E': 'Exportar'
    }

    print("\n" + "="*80)
    print("CREACION DEL ROL CONTADOR Y MODULO COTIZACIONES")
    print("="*80 + "\n")

    # ===================================================================
    # 1. CREAR EL ROL "CONTADOR"
    # ===================================================================
    rol_contador, created = Rol.objects.get_or_create(
        nombre='Contador',
        defaults={
            'descripcion': 'Responsable de gestion financiera, contable y cotizaciones de monedas',
            'activo': True,
            'es_admin': False,
            'en_uso': False
        }
    )

    if created:
        print(f"[OK] Rol 'Contador' creado exitosamente")
    else:
        print(f"[OK] Rol 'Contador' ya existe")

    # ===================================================================
    # 2. CREAR EL MODULO "COTIZACIONES" (EXCLUSIVO DEL CONTADOR)
    # ===================================================================
    print("\n--- MODULO COTIZACIONES (EXCLUSIVO DEL CONTADOR) ---")

    modulo_cotizaciones, modulo_created = Modulo.objects.get_or_create(
        nombre='Cotizaciones',
        defaults={
            'descripcion': 'Gestion de cotizaciones de monedas (USD a Guaranies)',
            'activo': True,
            'en_uso': False
        }
    )

    if modulo_created:
        print(f"[OK] Modulo 'Cotizaciones' creado")
    else:
        print(f"[OK] Modulo 'Cotizaciones' ya existe")

    # Crear todos los permisos para el módulo Cotizaciones
    permisos_cotizaciones = ['R', 'C', 'U', 'E']  # Leer, Crear, Modificar, Exportar (NO eliminar)

    for tipo_permiso, nombre_tipo in tipo_permiso_nombres.items():
        permiso_nombre = f"Cotizaciones_{nombre_tipo}"

        permiso, permiso_created = Permiso.objects.get_or_create(
            nombre=permiso_nombre,
            modulo=modulo_cotizaciones,
            defaults={
                'descripcion': f"{nombre_tipo} en Cotizaciones",
                'tipo': tipo_permiso,
                'activo': True,
                'en_uso': False
            }
        )

        if permiso_created:
            print(f"  [OK] Permiso '{permiso_nombre}' creado")

        # Asignar SOLO al rol Contador los permisos especificados
        if tipo_permiso in permisos_cotizaciones:
            relacion_existe = RolesPermisos.objects.filter(
                rol=rol_contador,
                permiso=permiso
            ).exists()

            if not relacion_existe:
                RolesPermisos.objects.create(
                    rol=rol_contador,
                    permiso=permiso
                )
                print(f"    [OK] Permiso '{permiso_nombre}' asignado al rol Contador")
            else:
                print(f"    [OK] Permiso '{permiso_nombre}' ya estaba asignado al rol Contador")

    # ===================================================================
    # 3. ASIGNAR PERMISOS DE OTROS MODULOS AL ROL CONTADOR
    # ===================================================================

    # Definición de módulos y permisos a asignar al Contador
    modulos_permisos_contador = [
        {
            'nombre': 'Reservas',
            'descripcion': 'Gestion de reservas de paquetes turisticos',
            'permisos': ['R', 'E']  # Leer, Exportar
        },
        {
            'nombre': 'Paquetes',
            'descripcion': 'Consulta de informacion de paquetes de viajes',
            'permisos': ['R']  # Solo Leer
        },
        {
            'nombre': 'Cajas',
            'descripcion': 'Gestion de cajas de efectivo',
            'permisos': ['R', 'E']  # Leer, Exportar
        },
        {
            'nombre': 'Aperturas',
            'descripcion': 'Gestion de aperturas de caja',
            'permisos': ['R', 'E']  # Leer, Exportar
        },
        {
            'nombre': 'Cierres',
            'descripcion': 'Gestion de cierres de caja',
            'permisos': ['R', 'E']  # Leer, Exportar
        },
        {
            'nombre': 'Movimientos',
            'descripcion': 'Registro de movimientos de efectivo',
            'permisos': ['R', 'E']  # Leer, Exportar
        }
    ]

    print("\n--- ASIGNACION DE PERMISOS DE OTROS MODULOS AL CONTADOR ---")

    for modulo_data in modulos_permisos_contador:
        # Verificar si el módulo existe, si no, crearlo
        modulo, modulo_created = Modulo.objects.get_or_create(
            nombre=modulo_data['nombre'],
            defaults={
                'descripcion': modulo_data['descripcion'],
                'activo': True,
                'en_uso': False
            }
        )

        if modulo_created:
            print(f"\n[OK] Modulo '{modulo_data['nombre']}' creado")
        else:
            print(f"\n[OK] Modulo '{modulo_data['nombre']}' ya existe")

        # Crear todos los permisos para el módulo si no existen
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

            # Asignar SOLO los permisos especificados al Contador
            if tipo_permiso in modulo_data['permisos']:
                relacion_existe = RolesPermisos.objects.filter(
                    rol=rol_contador,
                    permiso=permiso
                ).exists()

                if not relacion_existe:
                    RolesPermisos.objects.create(
                        rol=rol_contador,
                        permiso=permiso
                    )
                    print(f"  [OK] Permiso '{permiso_nombre}' asignado al rol Contador")
                else:
                    print(f"  [OK] Permiso '{permiso_nombre}' ya estaba asignado al rol Contador")

    # ===================================================================
    # 4. VERIFICACION DE SEGURIDAD: VALIDAR QUE OTROS ROLES NO TIENEN
    #    ACCESO A COTIZACIONES
    # ===================================================================
    print("\n--- VERIFICACION DE SEGURIDAD ---")

    # Obtener todos los permisos del módulo Cotizaciones
    permisos_cotizaciones_obj = Permiso.objects.filter(modulo=modulo_cotizaciones)

    # Verificar que ningún otro rol tenga permisos de Cotizaciones
    roles_con_acceso = RolesPermisos.objects.filter(
        permiso__in=permisos_cotizaciones_obj
    ).exclude(rol=rol_contador).values_list('rol__nombre', flat=True).distinct()

    if roles_con_acceso:
        print(f"[ADVERTENCIA] Los siguientes roles tienen acceso a Cotizaciones: {', '.join(roles_con_acceso)}")
        print("[ADVERTENCIA] Considere remover estos permisos manualmente si es necesario")
    else:
        print("[OK] Ningun otro rol tiene acceso a Cotizaciones (correcto)")

    print("\n" + "="*80)
    print("[OK] MIGRACION COMPLETADA EXITOSAMENTE")
    print("="*80 + "\n")


def revertir_rol_contador_y_permisos(apps, schema_editor):
    """
    Función de reversión: Elimina los permisos del rol Contador y el módulo Cotizaciones
    (solo si no están en uso)
    """
    Modulo = apps.get_model('modulo', 'Modulo')
    Permiso = apps.get_model('permiso', 'Permiso')
    Rol = apps.get_model('rol', 'Rol')
    RolesPermisos = apps.get_model('rol', 'RolesPermisos')

    print("\n" + "="*80)
    print("REVERSION: ELIMINANDO ROL CONTADOR Y MODULO COTIZACIONES")
    print("="*80 + "\n")

    try:
        rol_contador = Rol.objects.get(nombre='Contador')

        # Eliminar todas las relaciones de permisos del Contador
        permisos_eliminados = RolesPermisos.objects.filter(rol=rol_contador).count()
        RolesPermisos.objects.filter(rol=rol_contador).delete()
        print(f"[OK] {permisos_eliminados} permisos eliminados del rol Contador")

        # Eliminar el rol Contador si no está en uso
        if not rol_contador.en_uso:
            rol_contador.delete()
            print(f"[OK] Rol 'Contador' eliminado")
        else:
            print(f"[ADVERTENCIA] Rol 'Contador' esta en uso, no se eliminara")

    except Rol.DoesNotExist:
        print("[ERROR] Rol 'Contador' no existe")

    # Eliminar el módulo Cotizaciones y sus permisos
    try:
        modulo_cotizaciones = Modulo.objects.get(nombre='Cotizaciones')

        # Eliminar permisos del módulo
        permisos = Permiso.objects.filter(modulo=modulo_cotizaciones)
        permisos_count = permisos.count()

        # Eliminar relaciones primero
        RolesPermisos.objects.filter(permiso__in=permisos).delete()

        # Eliminar permisos
        permisos.delete()
        print(f"[OK] {permisos_count} permisos del modulo Cotizaciones eliminados")

        # Eliminar módulo si no está en uso
        if not modulo_cotizaciones.en_uso:
            modulo_cotizaciones.delete()
            print(f"[OK] Modulo 'Cotizaciones' eliminado")
        else:
            print(f"[ADVERTENCIA] Modulo 'Cotizaciones' esta en uso, no se eliminara")

    except Modulo.DoesNotExist:
        print("[ERROR] Modulo 'Cotizaciones' no existe")

    print("\n" + "="*80)
    print("[OK] REVERSION COMPLETADA")
    print("="*80 + "\n")


class Migration(migrations.Migration):

    dependencies = [
        ('modulo', '0007_agregar_modulos_permisos_cajero'),
        ('permiso', '0013_alter_permiso_nombre'),
        ('rol', '0006_rol_es_admin'),
    ]

    operations = [
        migrations.RunPython(
            crear_rol_contador_y_permisos,
            reverse_code=revertir_rol_contador_y_permisos
        ),
    ]
