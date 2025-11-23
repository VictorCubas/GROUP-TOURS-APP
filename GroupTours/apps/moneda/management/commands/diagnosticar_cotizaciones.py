from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.moneda.models import CotizacionMoneda, Moneda
import pytz


class Command(BaseCommand):
    help = 'Diagnostica las cotizaciones de USD para verificar por que no se encuentra cotizacion vigente'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("DIAGNOSTICO DE COTIZACIONES")
        self.stdout.write("=" * 80)

        # 1. Obtener fecha actual en Paraguay
        tz_asuncion = pytz.timezone('America/Asuncion')
        fecha_hoy_py = timezone.now().astimezone(tz_asuncion).date()
        self.stdout.write(f"\n[INFO] Fecha actual en Paraguay: {fecha_hoy_py}")

        # 2. Obtener fecha sin timezone
        fecha_hoy_simple = timezone.now().date()
        self.stdout.write(f"[INFO] Fecha simple (sin TZ): {fecha_hoy_simple}")

        # 3. Verificar moneda USD
        try:
            moneda_usd = Moneda.objects.get(codigo='USD')
            self.stdout.write(self.style.SUCCESS(f"\n[OK] Moneda USD encontrada: {moneda_usd.nombre}"))
        except Moneda.DoesNotExist:
            self.stdout.write(self.style.ERROR("\n[ERROR] Moneda USD no existe"))
            return

        # 4. Buscar cotizaciones de HOY (como lo hace el login)
        cot_hoy = CotizacionMoneda.objects.filter(
            moneda=moneda_usd,
            fecha_vigencia=fecha_hoy_py
        )
        self.stdout.write(f"\n[INFO] Cotizaciones con fecha_vigencia = {fecha_hoy_py}:")
        self.stdout.write(f"Total: {cot_hoy.count()}")
        for c in cot_hoy:
            self.stdout.write(f"  ID: {c.id}, Valor: {c.valor_en_guaranies}, Fecha: {c.fecha_vigencia}")

        # 5. Buscar cotizaciones <= HOY (como lo hace el endpoint vigente)
        cot_vigente = CotizacionMoneda.objects.filter(
            moneda=moneda_usd,
            fecha_vigencia__lte=fecha_hoy_py
        ).order_by('-fecha_vigencia')
        self.stdout.write(f"\n[INFO] Cotizaciones con fecha_vigencia <= {fecha_hoy_py}:")
        self.stdout.write(f"Total: {cot_vigente.count()}")
        for c in cot_vigente[:3]:  # Mostrar las 3 más recientes
            self.stdout.write(f"  ID: {c.id}, Valor: {c.valor_en_guaranies}, Fecha: {c.fecha_vigencia}")

        # 6. Verificar el método del modelo
        self.stdout.write(f"\n[INFO] Usando el metodo obtener_cotizacion_vigente:")
        cotizacion_metodo = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd, fecha_hoy_py)
        if cotizacion_metodo:
            self.stdout.write(self.style.SUCCESS(
                f"  [OK] Cotizacion encontrada: ID {cotizacion_metodo.id}, "
                f"Fecha {cotizacion_metodo.fecha_vigencia}, Valor {cotizacion_metodo.valor_en_guaranies}"
            ))
        else:
            self.stdout.write(self.style.ERROR("  [ERROR] No se encontro cotizacion vigente"))

        # 7. Listar TODAS las cotizaciones de USD
        self.stdout.write(f"\n[INFO] TODAS las cotizaciones de USD:")
        todas = CotizacionMoneda.objects.filter(moneda=moneda_usd).order_by('-fecha_vigencia')
        self.stdout.write(f"Total: {todas.count()}")
        for c in todas[:5]:
            self.stdout.write(f"  Fecha: {c.fecha_vigencia}, Valor: {c.valor_en_guaranies}, ID: {c.id}")

        # 8. Verificar si hay diferencia entre las fechas
        if fecha_hoy_py != fecha_hoy_simple:
            self.stdout.write(self.style.WARNING(
                f"\n[ATENCION] Hay diferencia entre fecha con TZ ({fecha_hoy_py}) "
                f"y sin TZ ({fecha_hoy_simple})"
            ))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("\nDiagnostico completado"))

