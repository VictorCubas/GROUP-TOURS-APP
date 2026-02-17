# Generated manually - Data migration
from django.db import migrations
from django.utils.timezone import now
from datetime import date


def crear_usuarios_operativos(apps, schema_editor):
    """
    Crea los usuarios operativos del sistema:
    - gissellescurra (Cajero)
    - nicolaslopez (Contador)
    
    IMPORTANTE: Asegúrate de que existan los siguientes datos maestros:
    - TipoDocumento: CI (Cédula de Identidad)
    - Nacionalidad: Paraguaya
    - Puesto: Cajero y Contador
    - TipoRemuneracion: Salario Fijo
    - Roles: Cajero y Contador (creados en migración anterior)
    """
    # Obtener modelos
    PersonaFisica = apps.get_model('persona', 'PersonaFisica')
    Empleado = apps.get_model('empleado', 'Empleado')
    Usuario = apps.get_model('usuario', 'Usuario')
    Rol = apps.get_model('rol', 'Rol')
    TipoDocumento = apps.get_model('tipo_documento', 'TipoDocumento')
    Nacionalidad = apps.get_model('nacionalidad', 'Nacionalidad')
    Puesto = apps.get_model('puesto', 'Puesto')
    TipoRemuneracion = apps.get_model('tipo_remuneracion', 'TipoRemuneracion')
    
    print("\n" + "="*80)
    print("CREACION DE USUARIOS OPERATIVOS: CAJERO Y CONTADOR")
    print("="*80 + "\n")
    
    # ===================================================================
    # 1. VERIFICAR DATOS MAESTROS NECESARIOS
    # ===================================================================
    print("--- VERIFICACION DE DATOS MAESTROS ---")
    
    try:
        tipo_doc_ci = TipoDocumento.objects.get(nombre='CI')
        print(f"[OK] Tipo Documento 'CI' encontrado (ID: {tipo_doc_ci.id})")
    except TipoDocumento.DoesNotExist:
        print("[ERROR] No existe el Tipo Documento 'CI'")
        print("  Crea primero el tipo de documento CI antes de ejecutar esta migracion")
        return
    
    try:
        nacionalidad_py = Nacionalidad.objects.get(nombre='Paraguaya')
        print(f"[OK] Nacionalidad 'Paraguaya' encontrada (ID: {nacionalidad_py.id})")
    except Nacionalidad.DoesNotExist:
        print("[ERROR] No existe la Nacionalidad 'Paraguaya'")
        print("  Crea primero la nacionalidad antes de ejecutar esta migracion")
        return
    
    try:
        puesto_cajero = Puesto.objects.get(nombre='Cajero')
        print(f"[OK] Puesto 'Cajero' encontrado (ID: {puesto_cajero.id})")
    except Puesto.DoesNotExist:
        print("[AVISO] No existe el Puesto 'Cajero', creandolo...")
        puesto_cajero = Puesto.objects.create(
            nombre='Cajero',
            descripcion='Responsable de la gestion de caja y operaciones de efectivo',
            activo=True
        )
        print(f"[OK] Puesto 'Cajero' creado (ID: {puesto_cajero.id})")
    
    try:
        puesto_contador = Puesto.objects.get(nombre='Contador')
        print(f"[OK] Puesto 'Contador' encontrado (ID: {puesto_contador.id})")
    except Puesto.DoesNotExist:
        print("[AVISO] No existe el Puesto 'Contador', creandolo...")
        puesto_contador = Puesto.objects.create(
            nombre='Contador',
            descripcion='Responsable de gestion financiera y contable',
            activo=True
        )
        print(f"[OK] Puesto 'Contador' creado (ID: {puesto_contador.id})")
    
    try:
        tipo_rem_fijo = TipoRemuneracion.objects.get(nombre='Salario Fijo')
        print(f"[OK] Tipo Remuneracion 'Salario Fijo' encontrado (ID: {tipo_rem_fijo.id})")
    except TipoRemuneracion.DoesNotExist:
        print("[AVISO] No existe 'Salario Fijo', creandolo...")
        tipo_rem_fijo = TipoRemuneracion.objects.create(
            nombre='Salario Fijo',
            descripcion='Remuneracion fija mensual',
            activo=True
        )
        print(f"[OK] Tipo Remuneracion 'Salario Fijo' creado (ID: {tipo_rem_fijo.id})")
    
    # Verificar roles
    try:
        rol_cajero = Rol.objects.get(nombre='Cajero')
        print(f"[OK] Rol 'Cajero' encontrado (ID: {rol_cajero.id})")
    except Rol.DoesNotExist:
        print("[ERROR] No existe el Rol 'Cajero'")
        print("  Ejecuta primero las migraciones de modulo para crear los roles")
        return
    
    try:
        rol_contador = Rol.objects.get(nombre='Contador')
        print(f"[OK] Rol 'Contador' encontrado (ID: {rol_contador.id})")
    except Rol.DoesNotExist:
        print("[ERROR] No existe el Rol 'Contador'")
        print("  Ejecuta primero las migraciones de modulo para crear los roles")
        return
    
    # ===================================================================
    # 2. CREAR USUARIO GISSELLE SCURRA (CAJERO)
    # ===================================================================
    print("\n--- CREANDO USUARIO: GISSELLE SCURRA (CAJERO) ---")
    
    # Verificar si ya existe
    if Usuario.objects.filter(username='gissellescurra').exists():
        print("[AVISO] El usuario 'gissellescurra' ya existe, saltando creacion...")
    else:
        # Crear PersonaFisica
        persona_gisselle, created = PersonaFisica.objects.get_or_create(
            documento='5678901',
            defaults={
                'tipo_documento': tipo_doc_ci,
                'nombre': 'Gisselle',
                'apellido': 'Scurra',
                'email': 'gisselle.scurra@grouptours.com',
                'telefono': '0981234567',
                'direccion': 'Asuncion, Paraguay',
                'fecha_nacimiento': date(1995, 3, 15),
                'sexo': 'F',
                'nacionalidad': nacionalidad_py,
                'activo': True
            }
        )
        
        if created:
            print(f"[OK] Persona creada: {persona_gisselle.nombre} {persona_gisselle.apellido}")
        else:
            print(f"[OK] Persona ya existia: {persona_gisselle.nombre} {persona_gisselle.apellido}")
        
        # Crear Empleado
        empleado_gisselle, created = Empleado.objects.get_or_create(
            persona=persona_gisselle,
            defaults={
                'puesto': puesto_cajero,
                'tipo_remuneracion': tipo_rem_fijo,
                'salario': 3500000,  # 3.500.000 Gs
                'porcentaje_comision': 0.00,
                'activo': True,
                'fecha_ingreso': date.today()
            }
        )
        
        if created:
            print(f"[OK] Empleado creado: {empleado_gisselle.persona.nombre} - {empleado_gisselle.puesto.nombre}")
        else:
            print(f"[OK] Empleado ya existia: {empleado_gisselle.persona.nombre} - {empleado_gisselle.puesto.nombre}")
        
        # Crear Usuario
        usuario_gisselle = Usuario.objects.create(
            username='gissellescurra',
            first_name='Gisselle',
            last_name='Scurra',
            email='gisselle.scurra@grouptours.com',
            empleado=empleado_gisselle,
            activo=True,
            debe_cambiar_contrasenia=True,
            is_staff=False,
            is_superuser=False,
            is_active=True
        )
        
        # IMPORTANTE: Usar set_password para hashear correctamente
        usuario_gisselle.set_password('Cajero2025!')
        usuario_gisselle.save()
        
        # Asignar rol
        usuario_gisselle.roles.add(rol_cajero)
        
        print(f"[OK] Usuario creado: '{usuario_gisselle.username}' (ID: {usuario_gisselle.id})")
        print(f"  - Email: {usuario_gisselle.email}")
        print(f"  - Contrasena temporal: Cajero2025!")
        print(f"  - Rol asignado: {rol_cajero.nombre}")
        print(f"  - Debe cambiar contrasena: Si")
    
    # ===================================================================
    # 3. CREAR USUARIO NICOLAS LOPEZ (CONTADOR)
    # ===================================================================
    print("\n--- CREANDO USUARIO: NICOLAS LOPEZ (CONTADOR) ---")
    
    # Verificar si ya existe
    if Usuario.objects.filter(username='nicolaslopez').exists():
        print("[AVISO] El usuario 'nicolaslopez' ya existe, saltando creacion...")
    else:
        # Crear PersonaFisica
        persona_nicolas, created = PersonaFisica.objects.get_or_create(
            documento='6789012',
            defaults={
                'tipo_documento': tipo_doc_ci,
                'nombre': 'Nicolas',
                'apellido': 'Lopez',
                'email': 'nicolas.lopez@grouptours.com',
                'telefono': '0981234568',
                'direccion': 'Asuncion, Paraguay',
                'fecha_nacimiento': date(1988, 7, 22),
                'sexo': 'M',
                'nacionalidad': nacionalidad_py,
                'activo': True
            }
        )
        
        if created:
            print(f"[OK] Persona creada: {persona_nicolas.nombre} {persona_nicolas.apellido}")
        else:
            print(f"[OK] Persona ya existia: {persona_nicolas.nombre} {persona_nicolas.apellido}")
        
        # Crear Empleado
        empleado_nicolas, created = Empleado.objects.get_or_create(
            persona=persona_nicolas,
            defaults={
                'puesto': puesto_contador,
                'tipo_remuneracion': tipo_rem_fijo,
                'salario': 4500000,  # 4.500.000 Gs
                'porcentaje_comision': 0.00,
                'activo': True,
                'fecha_ingreso': date.today()
            }
        )
        
        if created:
            print(f"[OK] Empleado creado: {empleado_nicolas.persona.nombre} - {empleado_nicolas.puesto.nombre}")
        else:
            print(f"[OK] Empleado ya existia: {empleado_nicolas.persona.nombre} - {empleado_nicolas.puesto.nombre}")
        
        # Crear Usuario
        usuario_nicolas = Usuario.objects.create(
            username='nicolaslopez',
            first_name='Nicolas',
            last_name='Lopez',
            email='nicolas.lopez@grouptours.com',
            empleado=empleado_nicolas,
            activo=True,
            debe_cambiar_contrasenia=True,
            is_staff=False,
            is_superuser=False,
            is_active=True
        )
        
        # IMPORTANTE: Usar set_password para hashear correctamente
        usuario_nicolas.set_password('Contador2025!')
        usuario_nicolas.save()
        
        # Asignar rol
        usuario_nicolas.roles.add(rol_contador)
        
        print(f"[OK] Usuario creado: '{usuario_nicolas.username}' (ID: {usuario_nicolas.id})")
        print(f"  - Email: {usuario_nicolas.email}")
        print(f"  - Contrasena temporal: Contador2025!")
        print(f"  - Rol asignado: {rol_contador.nombre}")
        print(f"  - Debe cambiar contrasena: Si")
    
    # ===================================================================
    # 4. RESUMEN FINAL
    # ===================================================================
    print("\n--- RESUMEN DE USUARIOS CREADOS ---")
    
    usuarios_creados = Usuario.objects.filter(
        username__in=['gissellescurra', 'nicolaslopez']
    ).select_related('empleado__persona', 'empleado__puesto')
    
    for usuario in usuarios_creados:
        roles_nombres = ', '.join([r.nombre for r in usuario.roles.all()])
        print(f"\nUsuario: {usuario.username}")
        print(f"  - Nombre completo: {usuario.first_name} {usuario.last_name}")
        print(f"  - Email: {usuario.email}")
        print(f"  - Empleado: {usuario.empleado.persona.nombre} {usuario.empleado.persona.apellido}")
        print(f"  - Puesto: {usuario.empleado.puesto.nombre}")
        print(f"  - Roles: {roles_nombres}")
        print(f"  - Activo: {'Si' if usuario.activo else 'No'}")
    
    print("\n" + "="*80)
    print("[OK] MIGRACION COMPLETADA EXITOSAMENTE")
    print("="*80 + "\n")
    
    print("[IMPORTANTE] Las contrasenas temporales son:")
    print("  - gissellescurra: Cajero2025!")
    print("  - nicolaslopez: Contador2025!")
    print("  Ambos usuarios deberan cambiar su contrasena en el primer inicio de sesion.")
    print()


def revertir_usuarios_operativos(apps, schema_editor):
    """
    Revierte la creacion de usuarios operativos
    """
    Usuario = apps.get_model('usuario', 'Usuario')
    Empleado = apps.get_model('empleado', 'Empleado')
    PersonaFisica = apps.get_model('persona', 'PersonaFisica')
    
    print("\n" + "="*80)
    print("REVERSION: ELIMINANDO USUARIOS OPERATIVOS")
    print("="*80 + "\n")
    
    usuarios_a_eliminar = ['gissellescurra', 'nicolaslopez']
    documentos_a_eliminar = ['5678901', '6789012']
    
    for username in usuarios_a_eliminar:
        try:
            usuario = Usuario.objects.get(username=username)
            empleado = usuario.empleado
            persona = empleado.persona if empleado else None
            
            # Eliminar en orden inverso
            usuario.delete()
            print(f"[OK] Usuario '{username}' eliminado")
            
            if empleado:
                empleado.delete()
                print(f"[OK] Empleado asociado eliminado")
            
            if persona:
                persona.delete()
                print(f"[OK] Persona asociada eliminada")
                
        except Usuario.DoesNotExist:
            print(f"[AVISO] Usuario '{username}' no existe")
    
    print("\n" + "="*80)
    print("[OK] REVERSION COMPLETADA")
    print("="*80 + "\n")


class Migration(migrations.Migration):
    
    dependencies = [
        ('usuario', '0006_alter_usuario_debe_cambiar_contrasenia'),  # Fixed: Changed from 0009 to 0006
        ('rol', '0006_rol_es_admin'),
        ('modulo', '0009_crear_modulo_pagos_permisos_cajero'),  # Asegura que los roles existan
        ('persona', '0005_alter_personafisica_options_and_more'),  # Fixed: Changed to latest persona migration
        ('empleado', '0004_alter_empleado_salario'),
        ('puesto', '0001_initial'),
        ('tipo_remuneracion', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(
            crear_usuarios_operativos,
            reverse_code=revertir_usuarios_operativos
        ),
    ]

