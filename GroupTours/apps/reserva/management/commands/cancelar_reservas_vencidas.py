from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.reserva.models import Reserva


class Command(BaseCommand):
    help = (
        "Cancela automáticamente las reservas que no están pagadas al 100% "
        "cuando faltan menos de 15 días para la salida."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué reservas se cancelarían sin aplicar cambios.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=15)

        queryset = Reserva.objects.filter(
            estado__in=['pendiente', 'confirmada'],
            salida__isnull=False,
            salida__fecha_salida__isnull=False,
            activo=True
        ).select_related('salida', 'paquete', 'habitacion')

        canceladas = 0

        for reserva in queryset:
            dias_restantes = reserva.dias_hasta_salida

            if dias_restantes is None:
                continue

            if dias_restantes >= 15:
                continue

            if reserva.esta_totalmente_pagada():
                continue

            mensaje = (
                f"Reserva {reserva.codigo} (ID {reserva.id}) "
                f"faltan {dias_restantes} días - cancelación automática."
            )

            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY-RUN] {mensaje}"))
                canceladas += 1
                continue

            reserva.marcar_cancelada(
                motivo_cancelacion_id='5',  # '5' = Cancelación automática por falta de pago
                motivo_observaciones="Cancelación automática por falta de pago",
                liberar_cupo=True
            )
            canceladas += 1
            self.stdout.write(self.style.SUCCESS(mensaje))

        if canceladas == 0:
            self.stdout.write(self.style.WARNING("No se encontraron reservas para cancelar."))
        else:
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY-RUN] Total a cancelar: {canceladas}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Reservas canceladas automáticamente: {canceladas}"))

