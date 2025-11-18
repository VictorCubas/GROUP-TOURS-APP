#!/usr/bin/env python
"""
Script para preparar los datos antes de la migración de Caja a relación 1:1 con PuntoExpedicion
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.arqueo_caja.models import Caja
from apps.facturacion.models import PuntoExpedicion, Establecimiento
from django.db.models import Count

def main():
    print("="*60)
    print("PREPARACION DE DATOS: Migracion Caja -> PE (1:1)")
    print("="*60)
    print()

    # 1. Verificar cajas sin PE
    cajas_sin_pe = Caja.objects.filter(punto_expedicion__isnull=True, activo=True)
    print(f"[INFO] Cajas sin Punto de Expedicion: {cajas_sin_pe.count()}")

    # 2. Verificar PEs compartidos
    pes_compartidos = Caja.objects.filter(
        punto_expedicion__isnull=False,
        activo=True
    ).values('punto_expedicion').annotate(
        num_cajas=Count('id')
    ).filter(num_cajas__gt=1)

    pes_compartidos_list = list(pes_compartidos)
    print(f"[INFO] Puntos de Expedicion compartidos: {len(pes_compartidos_list)}")
    print()

    if not cajas_sin_pe.exists() and not pes_compartidos_list:
        print("[OK] Perfecto! No hay problemas. Puedes ejecutar las migraciones directamente.")
        print()
        print("Ejecuta:")
        print("  python manage.py makemigrations arqueo_caja")
        print("  python manage.py migrate arqueo_caja")
        return

    # 3. Resolver cajas sin PE
    if cajas_sin_pe.exists():
        print("[PROCESO] Creando Puntos de Expedicion para cajas que no tienen...")
        establecimiento = Establecimiento.objects.filter(activo=True).first()

        if not establecimiento:
            print("[ERROR] No hay establecimientos activos. Crea uno primero.")
            return

        for caja in cajas_sin_pe:
            # Verificar que el código no esté usado
            codigo = caja.numero_caja
            pe_existente = PuntoExpedicion.objects.filter(
                establecimiento=establecimiento,
                codigo=codigo
            ).first()

            if pe_existente:
                # Si existe, usar un código diferente
                ultimo_pe = PuntoExpedicion.objects.filter(
                    establecimiento=establecimiento
                ).order_by('-codigo').first()

                if ultimo_pe:
                    try:
                        nuevo_numero = int(ultimo_pe.codigo) + 1
                    except:
                        nuevo_numero = int(codigo) + 100
                else:
                    nuevo_numero = 1

                codigo = f"{nuevo_numero:03d}"

            # Crear PE
            pe = PuntoExpedicion.objects.create(
                nombre=f"PE {caja.nombre}",
                establecimiento=establecimiento,
                codigo=codigo,
                descripcion=f"Auto-generado para {caja.nombre}"
            )
            caja.punto_expedicion = pe
            caja.save()
            print(f"  [OK] Caja {caja.numero_caja} ({caja.nombre}) -> PE {pe.codigo}")

        print()

    # 4. Resolver PEs compartidos
    if pes_compartidos_list:
        print("[PROCESO] Creando Puntos de Expedicion para cajas con PE compartido...")

        for pe_data in pes_compartidos_list:
            pe_id = pe_data['punto_expedicion']
            cajas_compartidas = Caja.objects.filter(
                punto_expedicion_id=pe_id,
                activo=True
            )

            # Mantener la primera caja con el PE original
            primera_caja = cajas_compartidas.first()
            pe_original = primera_caja.punto_expedicion
            print(f"  [INFO] Caja {primera_caja.numero_caja} mantiene PE {pe_original.codigo}")

            # Crear nuevos PEs para las demás
            for caja in cajas_compartidas.exclude(pk=primera_caja.pk):
                # Buscar código disponible
                codigo = caja.numero_caja
                pe_existente = PuntoExpedicion.objects.filter(
                    establecimiento=pe_original.establecimiento,
                    codigo=codigo
                ).first()

                if pe_existente and pe_existente != pe_original:
                    # Si existe, usar un código diferente
                    ultimo_pe = PuntoExpedicion.objects.filter(
                        establecimiento=pe_original.establecimiento
                    ).order_by('-codigo').first()

                    try:
                        nuevo_numero = int(ultimo_pe.codigo) + 1
                    except:
                        nuevo_numero = int(codigo) + 100

                    codigo = f"{nuevo_numero:03d}"

                # Crear nuevo PE
                nuevo_pe = PuntoExpedicion.objects.create(
                    nombre=f"PE {caja.nombre}",
                    establecimiento=pe_original.establecimiento,
                    codigo=codigo,
                    descripcion=f"Auto-generado para {caja.nombre}"
                )
                caja.punto_expedicion = nuevo_pe
                caja.save()
                print(f"  [OK] Caja {caja.numero_caja} ({caja.nombre}) -> Nuevo PE {nuevo_pe.codigo}")

        print()

    print("="*60)
    print("[OK] DATOS PREPARADOS")
    print("="*60)
    print()
    print("Ahora puedes ejecutar las migraciones:")
    print("  python manage.py makemigrations arqueo_caja")
    print("  python manage.py migrate arqueo_caja")
    print()

if __name__ == '__main__':
    main()
