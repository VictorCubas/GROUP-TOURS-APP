from django.core.management.base import BaseCommand
from apps.permiso.models import Permiso
from datetime import datetime


class Command(BaseCommand):
    help = 'Verificar permisos creados en una fecha y hora específica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha en formato DD/MM/YYYY',
            default='23/11/2025'
        )
        parser.add_argument(
            '--hora',
            type=str,
            help='Hora en formato HH:MM',
            default='12:07'
        )

    def handle(self, *args, **options):
        fecha_str = options['fecha']
        hora_str = options['hora']
        
        # Parsear la fecha y hora
        try:
            fecha_parts = fecha_str.split('/')
            hora_parts = hora_str.split(':')
            
            dia = int(fecha_parts[0])
            mes = int(fecha_parts[1])
            anio = int(fecha_parts[2])
            hora = int(hora_parts[0])
            minuto = int(hora_parts[1])
            
        except (ValueError, IndexError) as e:
            self.stdout.write(self.style.ERROR(f'Error al parsear fecha/hora: {e}'))
            return
        
        # Consultar permisos
        permisos = Permiso.objects.filter(
            fechaCreacion__year=anio,
            fechaCreacion__month=mes,
            fechaCreacion__day=dia,
            fechaCreacion__hour=hora,
            fechaCreacion__minute=minuto
        ).select_related('modulo').order_by('id')
        
        total = permisos.count()
        
        self.stdout.write("\n" + "="*100)
        self.stdout.write(self.style.SUCCESS(f"PERMISOS CREADOS EL {fecha_str} A LAS {hora_str}"))
        self.stdout.write("="*100 + "\n")
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No se encontraron permisos con esa fecha y hora exacta.'))
            
            # Buscar permisos cercanos
            self.stdout.write("\n" + "-"*100)
            self.stdout.write("Buscando permisos en el mismo día...")
            self.stdout.write("-"*100 + "\n")
            
            permisos_dia = Permiso.objects.filter(
                fechaCreacion__year=anio,
                fechaCreacion__month=mes,
                fechaCreacion__day=dia
            ).select_related('modulo').order_by('fechaCreacion', 'id')
            
            if permisos_dia.exists():
                self.stdout.write(f"\nSe encontraron {permisos_dia.count()} permisos en la fecha {fecha_str}:\n")
                for p in permisos_dia:
                    fecha_creacion = p.fechaCreacion.strftime("%d/%m/%Y %H:%M:%S")
                    self.stdout.write(
                        f"  {p.id:3d}. {p.nombre:45s} | Módulo: {p.modulo.nombre:20s} | "
                        f"Tipo: {p.get_tipo_display():12s} | Activo: {str(p.activo):5s} | "
                        f"Fecha: {fecha_creacion}"
                    )
            else:
                self.stdout.write(self.style.WARNING(f'No se encontraron permisos en la fecha {fecha_str}.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Total encontrados: {total}\n'))
            
            # Agrupar por módulo
            modulos_dict = {}
            for p in permisos:
                modulo_nombre = p.modulo.nombre
                if modulo_nombre not in modulos_dict:
                    modulos_dict[modulo_nombre] = []
                modulos_dict[modulo_nombre].append(p)
            
            # Mostrar agrupados por módulo
            for modulo_nombre, permisos_list in sorted(modulos_dict.items()):
                self.stdout.write(f"\n--- MÓDULO: {modulo_nombre} ---")
                for p in permisos_list:
                    fecha_creacion = p.fechaCreacion.strftime("%d/%m/%Y %H:%M:%S")
                    self.stdout.write(
                        f"  {p.id:3d}. {p.nombre:45s} | "
                        f"Tipo: {p.get_tipo_display():12s} | Activo: {str(p.activo):5s} | "
                        f"Fecha: {fecha_creacion}"
                    )
            
            # Resumen
            self.stdout.write("\n" + "="*100)
            self.stdout.write("RESUMEN")
            self.stdout.write("="*100)
            self.stdout.write(f"\nTotal de permisos: {total}")
            self.stdout.write(f"Módulos afectados: {len(modulos_dict)}")
            self.stdout.write(f"Módulos: {', '.join(sorted(modulos_dict.keys()))}\n")
            
            # Contar por tipo
            tipos_count = {}
            for p in permisos:
                tipo_display = p.get_tipo_display()
                tipos_count[tipo_display] = tipos_count.get(tipo_display, 0) + 1
            
            self.stdout.write("\nPermisos por tipo:")
            for tipo, count in sorted(tipos_count.items()):
                self.stdout.write(f"  - {tipo:15s}: {count}")
        
        self.stdout.write("\n" + "="*100 + "\n")

