from django.core.management.base import BaseCommand
from apps.moneda.models import CotizacionMoneda, Moneda
from django.utils import timezone
import pytz
from datetime import date


class Command(BaseCommand):
    help = 'Carga una cotizacion inicial de USD para produccion.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--compra',
            type=float,
            default=7200.0,
            help='Valor de compra del USD (default: 7200.0)'
        )
        parser.add_argument(
            '--venta',
            type=float,
            default=7400.0,
            help='Valor de venta del USD (default: 7400.0)'
        )
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha de vigencia (formato: YYYY-MM-DD). Si no se especifica, usa hoy.'
        )

    def handle(self, *args, **kwargs):
        compra = kwargs['compra']
        venta = kwargs['venta']
        fecha_str = kwargs.get('fecha')

        self.stdout.write(self.style.SUCCESS("="*80))
        self.stdout.write(self.style.SUCCESS("CARGA DE COTIZACION USD"))
        self.stdout.write(self.style.SUCCESS("="*80))

        # Obtener fecha
        if fecha_str:
            try:
                fecha_vigencia = date.fromisoformat(fecha_str)
                self.stdout.write(f"\n[INFO] Fecha especificada: {fecha_vigencia}")
            except ValueError:
                self.stdout.write(self.style.ERROR(f"[ERROR] Formato de fecha invalido: {fecha_str}"))
                self.stdout.write("[INFO] Use formato YYYY-MM-DD")
                return
        else:
            tz_asuncion = pytz.timezone('America/Asuncion')
            fecha_vigencia = timezone.now().astimezone(tz_asuncion).date()
            self.stdout.write(f"\n[INFO] Usando fecha actual en Paraguay: {fecha_vigencia}")

        # Buscar moneda USD
        try:
            moneda_usd = Moneda.objects.get(codigo='USD')
            self.stdout.write(f"[OK] Moneda USD encontrada: {moneda_usd.nombre}")
        except Moneda.DoesNotExist:
            self.stdout.write(self.style.ERROR("[ERROR] No existe la moneda USD en la base de datos"))
            self.stdout.write("[INFO] Debe crear primero la moneda USD")
            return

        # Verificar si ya existe cotización para esa fecha
        cotizacion_existente = CotizacionMoneda.objects.filter(
            moneda=moneda_usd,
            fecha_vigencia=fecha_vigencia
        ).first()

        if cotizacion_existente:
            self.stdout.write(self.style.WARNING(f"\n[AVISO] Ya existe una cotizacion para USD en {fecha_vigencia}"))
            self.stdout.write(f"  - Compra actual: {cotizacion_existente.valor_compra}")
            self.stdout.write(f"  - Venta actual: {cotizacion_existente.valor_venta}")
            
            respuesta = input("\nDesea actualizar? (s/n): ").lower()
            if respuesta != 's':
                self.stdout.write(self.style.WARNING("[CANCELADO] No se realizaron cambios"))
                return
            
            cotizacion_existente.valor_compra = compra
            cotizacion_existente.valor_venta = venta
            cotizacion_existente.save()
            self.stdout.write(self.style.SUCCESS(f"\n[OK] Cotizacion actualizada exitosamente"))
            self.stdout.write(f"  - Nueva compra: {compra}")
            self.stdout.write(f"  - Nueva venta: {venta}")
        else:
            # Crear nueva cotización
            nueva_cotizacion = CotizacionMoneda.objects.create(
                moneda=moneda_usd,
                fecha_vigencia=fecha_vigencia,
                valor_compra=compra,
                valor_venta=venta
            )
            self.stdout.write(self.style.SUCCESS(f"\n[OK] Cotizacion creada exitosamente (ID: {nueva_cotizacion.id})"))
            self.stdout.write(f"  - Moneda: {moneda_usd.nombre} ({moneda_usd.codigo})")
            self.stdout.write(f"  - Fecha vigencia: {fecha_vigencia}")
            self.stdout.write(f"  - Compra: {compra}")
            self.stdout.write(f"  - Venta: {venta}")

        # Verificación final
        self.stdout.write("\n" + "="*80)
        self.stdout.write("VERIFICACION")
        self.stdout.write("="*80)
        
        cotizacion_vigente = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd, fecha_vigencia)
        if cotizacion_vigente:
            self.stdout.write(self.style.SUCCESS("\n[OK] Cotizacion vigente encontrada:"))
            self.stdout.write(f"  - ID: {cotizacion_vigente.id}")
            self.stdout.write(f"  - Fecha vigencia: {cotizacion_vigente.fecha_vigencia}")
            self.stdout.write(f"  - Compra: {cotizacion_vigente.valor_compra}")
            self.stdout.write(f"  - Venta: {cotizacion_vigente.valor_venta}")
        else:
            self.stdout.write(self.style.ERROR("\n[ERROR] No se pudo verificar la cotizacion"))

        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("[COMPLETADO]"))
        self.stdout.write("="*80 + "\n")

