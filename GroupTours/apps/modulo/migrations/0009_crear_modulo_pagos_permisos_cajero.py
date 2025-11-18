# Generated manually - Data migration
from django.db import migrations


def crear_modulo_pagos_y_permisos(apps, schema_editor):
    """
    Crea el módulo 'Pagos' y asigna permisos SOLO al rol 'Cajero'.

    IMPORTANTE:
    - Solo el Cajero tiene permisos explícitos en Pagos (Crear, Leer, Exportar)
    - El Contador NO tiene permisos en Pagos
    - El Admin NO necesita permisos explícitos (es_admin=True bypasea validaciones)
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
    print("CREACION DEL MODULO PAGOS")
    print("="*80 + "\n")

    # ===================================================================
    # 1. VERIFICAR QUE EXISTE EL ROL "CAJERO"
    # ===================================================================
    try:
        rol_cajero = Rol.objects.get(nombre='Cajero')
        print(f"[OK] Rol 'Cajero' encontrado")
    except Rol.DoesNotExist:
        print("[ERROR] Rol 'Cajero' no existe. Debe ejecutar primero la migracion 0007")
        return

    # ===================================================================
    # 2. CREAR EL MODULO "PAGOS"
    # ===================================================================
    modulo_pagos, modulo_created = Modulo.objects.get_or_create(
        nombre='Pagos',
        defaults={
            'descripcion': 'Gestion de pagos y cobros de reservas',
            'activo': True,
            'en_uso': False
        }
    )

    if modulo_created:
        print(f"[OK] Modulo 'Pagos' creado")
    else:
        print(f"[OK] Modulo 'Pagos' ya existe")

    # ===================================================================
    # 3. CREAR TODOS LOS PERMISOS PARA EL MODULO PAGOS
    # ===================================================================
    print("\n--- CREACION DE PERMISOS DEL MODULO PAGOS ---")

    # Permisos que se asignarán al Cajero
    permisos_cajero = ['C', 'R', 'E']  # Crear, Leer, Exportar

    for tipo_permiso, nombre_tipo in tipo_permiso_nombres.items():
        permiso_nombre = f"Pagos_{nombre_tipo}"

        permiso, permiso_created = Permiso.objects.get_or_create(
            nombre=permiso_nombre,
            modulo=modulo_pagos,
            defaults={
                'descripcion': f"{nombre_tipo} en Pagos",
                'tipo': tipo_permiso,
                'activo': True,
                'en_uso': False
            }
        )

        if permiso_created:
            print(f"  [OK] Permiso '{permiso_nombre}' creado")

        # Asignar SOLO al rol Cajero los permisos especificados
        if tipo_permiso in permisos_cajero:
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

    # ===================================================================
    # 4. VERIFICACION: NO ASIGNAR A CONTADOR NI OTROS ROLES
    # ===================================================================
    print("\n--- VERIFICACION DE SEGURIDAD ---")

    # Verificar que el Contador NO tiene permisos en Pagos
    try:
        rol_contador = Rol.objects.get(nombre='Contador')
        permisos_pagos = Permiso.objects.filter(modulo=modulo_pagos)

        relaciones_contador = RolesPermisos.objects.filter(
            rol=rol_contador,
            permiso__in=permisos_pagos
        )

        if relaciones_contador.exists():
            print(f"[ADVERTENCIA] El rol Contador tiene {relaciones_contador.count()} permisos en Pagos")
            print("[ADVERTENCIA] Considere remover estos permisos manualmente")
        else:
            print("[OK] El rol Contador NO tiene permisos en Pagos (correcto)")

    except Rol.DoesNotExist:
        print("[INFO] Rol Contador no existe (no es necesario para esta migracion)")

    # Verificar que solo el Cajero tiene permisos en Pagos
    permisos_pagos_obj = Permiso.objects.filter(modulo=modulo_pagos)
    roles_con_acceso = RolesPermisos.objects.filter(
        permiso__in=permisos_pagos_obj
    ).exclude(rol=rol_cajero).values_list('rol__nombre', flat=True).distinct()

    if roles_con_acceso:
        print(f"[ADVERTENCIA] Otros roles tienen acceso a Pagos: {', '.join(roles_con_acceso)}")
        print("[INFO] Roles Admin con es_admin=True no necesitan permisos explicitos")
    else:
        print("[OK] Solo el rol Cajero tiene permisos explicitos en Pagos (correcto)")

    # Resumen de permisos del Cajero en Pagos
    print("\n--- RESUMEN DE PERMISOS DEL CAJERO EN PAGOS ---")
    permisos_cajero_pagos = Permiso.objects.filter(
        modulo=modulo_pagos,
        roles_permisos__rol=rol_cajero
    ).order_by('tipo')

    for permiso in permisos_cajero_pagos:
        print(f"  - {permiso.get_tipo_display():12} : {permiso.nombre}")

    print("\n" + "="*80)
    print("[OK] MIGRACION COMPLETADA EXITOSAMENTE")
    print("="*80 + "\n")


def revertir_modulo_pagos_y_permisos(apps, schema_editor):
    """
    Función de reversión: Elimina los permisos del módulo Pagos
    (solo si no están en uso)
    """
    Modulo = apps.get_model('modulo', 'Modulo')
    Permiso = apps.get_model('permiso', 'Permiso')
    Rol = apps.get_model('rol', 'Rol')
    RolesPermisos = apps.get_model('rol', 'RolesPermisos')

    print("\n" + "="*80)
    print("REVERSION: ELIMINANDO MODULO PAGOS")
    print("="*80 + "\n")

    try:
        modulo_pagos = Modulo.objects.get(nombre='Pagos')
        permisos = Permiso.objects.filter(modulo=modulo_pagos)

        # Eliminar relaciones de permisos
        relaciones_eliminadas = RolesPermisos.objects.filter(
            permiso__in=permisos
        ).count()

        RolesPermisos.objects.filter(permiso__in=permisos).delete()
        print(f"[OK] {relaciones_eliminadas} relaciones de permisos eliminadas")

        # Eliminar permisos
        permisos_count = permisos.count()
        permisos.delete()
        print(f"[OK] {permisos_count} permisos del modulo Pagos eliminados")

        # Eliminar módulo si no está en uso
        if not modulo_pagos.en_uso:
            modulo_pagos.delete()
            print(f"[OK] Modulo 'Pagos' eliminado")
        else:
            print(f"[ADVERTENCIA] Modulo 'Pagos' esta en uso, no se eliminara")

    except Modulo.DoesNotExist:
        print("[ERROR] Modulo 'Pagos' no existe")

    print("\n" + "="*80)
    print("[OK] REVERSION COMPLETADA")
    print("="*80 + "\n")


class Migration(migrations.Migration):

    dependencies = [
        ('modulo', '0008_crear_rol_contador_modulo_cotizaciones'),
        ('permiso', '0013_alter_permiso_nombre'),
        ('rol', '0006_rol_es_admin'),
    ]

    operations = [
        migrations.RunPython(
            crear_modulo_pagos_y_permisos,
            reverse_code=revertir_modulo_pagos_y_permisos
        ),
    ]
