"""
Tests para la integración de ComprobantePago con MovimientoCaja

Ejecutar tests:
    python manage.py test apps.comprobante.tests_movimientos_caja
"""

from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion
from apps.arqueo_caja.models import Caja, AperturaCaja, MovimientoCaja
from apps.reserva.models import Reserva, Pasajero
from apps.paquete.models import Paquete, SalidaPaquete
from apps.empleado.models import Empleado
from apps.persona.models import PersonaFisica
from apps.facturacion.models import PuntoExpedicion, Establecimiento, Empresa
from apps.moneda.models import Moneda
from apps.destino.models import Destino
from apps.tipo_paquete.models import TipoPaquete


class ComprobantePagoMovimientoCajaTestCase(TestCase):
    """Tests de integración entre ComprobantePago y MovimientoCaja"""

    def setUp(self):
        """Configurar datos de prueba"""

        # Crear empresa y punto de expedición
        self.empresa = Empresa.objects.create(
            ruc='80000000-1',
            nombre='Test Tours SA'
        )

        self.establecimiento = Establecimiento.objects.create(
            empresa=self.empresa,
            codigo='001',
            nombre='Central'
        )

        self.punto_expedicion = PuntoExpedicion.objects.create(
            establecimiento=self.establecimiento,
            codigo='001',
            nombre='Caja 1'
        )

        # Crear caja
        self.caja = Caja.objects.create(
            nombre='Caja Principal',
            punto_expedicion=self.punto_expedicion,
            descripcion='Caja de prueba'
        )

        # Crear empleado
        self.persona_empleado = PersonaFisica.objects.create(
            nombre='Juan',
            apellido='Pérez',
            documento='1234567',
            email='juan@test.com'
        )

        self.empleado = Empleado.objects.create(
            persona=self.persona_empleado,
            codigo_empleado='EMP001'
        )

        # Crear otro empleado
        self.persona_empleado2 = PersonaFisica.objects.create(
            nombre='María',
            apellido='González',
            documento='7654321',
            email='maria@test.com'
        )

        self.empleado2 = Empleado.objects.create(
            persona=self.persona_empleado2,
            codigo_empleado='EMP002'
        )

        # Crear moneda
        self.moneda = Moneda.objects.create(
            nombre='Guaraníes',
            codigo='PYG',
            simbolo='Gs.'
        )

        # Crear tipo de paquete
        self.tipo_paquete = TipoPaquete.objects.create(
            nombre='Terrestre'
        )

        # Crear destino
        self.destino = Destino.objects.create(
            nombre='Encarnación'
        )

        # Crear paquete
        self.paquete = Paquete.objects.create(
            nombre='Paquete Test',
            descripcion='Paquete de prueba',
            tipo_paquete=self.tipo_paquete,
            destino=self.destino,
            moneda=self.moneda,
            modalidad='flexible',
            propio=True
        )

        # Crear salida
        self.salida = SalidaPaquete.objects.create(
            paquete=self.paquete,
            fecha_salida=timezone.now().date(),
            precio_actual=Decimal('1000000'),
            senia=Decimal('300000')
        )

        # Crear titular
        self.titular = PersonaFisica.objects.create(
            nombre='Cliente',
            apellido='Test',
            documento='9999999',
            email='cliente@test.com'
        )

        # Crear reserva
        self.reserva = Reserva.objects.create(
            titular=self.titular,
            paquete=self.paquete,
            salida=self.salida,
            cantidad_pasajeros=2,
            precio_unitario=Decimal('1000000')
        )

        # Crear pasajero
        self.pasajero = Pasajero.objects.create(
            reserva=self.reserva,
            persona=self.titular,
            es_titular=True,
            precio_asignado=Decimal('1000000')
        )

    def test_comprobante_con_caja_abierta_genera_movimiento(self):
        """
        Test: Un comprobante con caja abierta genera MovimientoCaja automáticamente
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        # Verificar saldo inicial
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('500000'))

        # Crear comprobante de pago
        comprobante = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        # Verificar que se creó el movimiento
        movimientos = MovimientoCaja.objects.filter(comprobante=comprobante)
        self.assertEqual(movimientos.count(), 1)

        movimiento = movimientos.first()
        self.assertEqual(movimiento.apertura_caja, apertura)
        self.assertEqual(movimiento.tipo_movimiento, 'ingreso')
        self.assertEqual(movimiento.concepto, 'venta_efectivo')
        self.assertEqual(movimiento.monto, Decimal('300000'))
        self.assertEqual(movimiento.metodo_pago, 'efectivo')
        self.assertEqual(movimiento.usuario_registro, self.empleado)

        # Verificar que se actualizó el saldo
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('800000'))

    def test_comprobante_sin_caja_abierta_no_genera_movimiento(self):
        """
        Test: Un comprobante sin caja abierta NO genera MovimientoCaja
        """
        # NO abrir caja

        # Crear comprobante de pago
        comprobante = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        # Verificar que NO se creó movimiento
        movimientos = MovimientoCaja.objects.filter(comprobante=comprobante)
        self.assertEqual(movimientos.count(), 0)

        # El comprobante se creó correctamente
        self.assertTrue(comprobante.pk is not None)
        self.assertEqual(comprobante.activo, True)

    def test_comprobante_con_caja_de_otro_empleado_no_genera_movimiento(self):
        """
        Test: Un comprobante con caja abierta por otro empleado NO genera MovimientoCaja
        """
        # Abrir caja con empleado2
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado2,  # Otro empleado
            monto_inicial=Decimal('500000')
        )

        # Crear comprobante con empleado1
        comprobante = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado  # Empleado diferente
        )

        # Verificar que NO se creó movimiento
        movimientos = MovimientoCaja.objects.filter(comprobante=comprobante)
        self.assertEqual(movimientos.count(), 0)

    def test_comprobante_con_tarjeta_mapea_concepto_correcto(self):
        """
        Test: Comprobantes con tarjeta mapean al concepto 'venta_tarjeta'
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        # Tarjeta de débito
        comprobante_debito = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='pago_parcial',
            monto=Decimal('200000'),
            metodo_pago='tarjeta_debito',
            empleado=self.empleado
        )

        movimiento_debito = MovimientoCaja.objects.get(comprobante=comprobante_debito)
        self.assertEqual(movimiento_debito.concepto, 'venta_tarjeta')

        # Tarjeta de crédito
        comprobante_credito = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='pago_parcial',
            monto=Decimal('200000'),
            metodo_pago='tarjeta_credito',
            empleado=self.empleado
        )

        movimiento_credito = MovimientoCaja.objects.get(comprobante=comprobante_credito)
        self.assertEqual(movimiento_credito.concepto, 'venta_tarjeta')

    def test_comprobante_transferencia_mapea_concepto_correcto(self):
        """
        Test: Comprobantes con transferencia mapean al concepto 'transferencia_recibida'
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        comprobante = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='pago_total',
            monto=Decimal('1000000'),
            metodo_pago='transferencia',
            empleado=self.empleado
        )

        movimiento = MovimientoCaja.objects.get(comprobante=comprobante)
        self.assertEqual(movimiento.concepto, 'transferencia_recibida')

    def test_devolucion_genera_egreso(self):
        """
        Test: Una devolución genera un MovimientoCaja de tipo 'egreso'
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        # Crear devolución
        comprobante_devolucion = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='devolucion',
            monto=Decimal('100000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        # Verificar movimiento
        movimiento = MovimientoCaja.objects.get(comprobante=comprobante_devolucion)
        self.assertEqual(movimiento.tipo_movimiento, 'egreso')
        self.assertEqual(movimiento.concepto, 'devolucion')

        # Verificar que el saldo disminuyó
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('400000'))

    def test_anular_comprobante_anula_movimiento(self):
        """
        Test: Al anular un comprobante, se anula también el movimiento
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        # Crear comprobante
        comprobante = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        # Verificar saldo después del ingreso
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('800000'))

        # Obtener movimiento
        movimiento = MovimientoCaja.objects.get(comprobante=comprobante)
        self.assertTrue(movimiento.activo)

        # Anular comprobante
        comprobante.anular(motivo="Pago duplicado")

        # Verificar que el comprobante se anuló
        comprobante.refresh_from_db()
        self.assertFalse(comprobante.activo)

        # Verificar que el movimiento se anuló
        movimiento.refresh_from_db()
        self.assertFalse(movimiento.activo)
        self.assertIn("ANULADO", movimiento.descripcion)
        self.assertIn("Pago duplicado", movimiento.descripcion)

        # Verificar que el saldo se recalculó correctamente
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('500000'))

    def test_multiples_pagos_actualizan_saldo_correctamente(self):
        """
        Test: Múltiples pagos actualizan el saldo correctamente
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('1000000')
        )

        # Pago 1: Efectivo
        ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('1300000'))

        # Pago 2: Tarjeta
        ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='pago_parcial',
            monto=Decimal('500000'),
            metodo_pago='tarjeta_debito',
            empleado=self.empleado
        )

        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('1800000'))

        # Devolución
        ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='devolucion',
            monto=Decimal('100000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('1700000'))

    def test_anular_uno_de_varios_pagos_recalcula_correctamente(self):
        """
        Test: Anular uno de varios pagos recalcula el saldo correctamente
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        # Crear varios pagos
        pago1 = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('200000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        pago2 = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='pago_parcial',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        pago3 = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='pago_parcial',
            monto=Decimal('150000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        # Saldo esperado: 500000 + 200000 + 300000 + 150000 = 1150000
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('1150000'))

        # Anular el segundo pago
        pago2.anular(motivo="Error de registro")

        # Saldo esperado: 500000 + 200000 + 150000 = 850000
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('850000'))

        # Verificar que hay 3 movimientos pero solo 2 activos
        todos_movimientos = MovimientoCaja.objects.filter(apertura_caja=apertura)
        self.assertEqual(todos_movimientos.count(), 3)

        movimientos_activos = todos_movimientos.filter(activo=True)
        self.assertEqual(movimientos_activos.count(), 2)

    def test_referencia_contiene_numero_comprobante(self):
        """
        Test: El campo referencia del movimiento contiene el número del comprobante
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        # Crear comprobante
        comprobante = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado
        )

        # Verificar referencia
        movimiento = MovimientoCaja.objects.get(comprobante=comprobante)
        self.assertEqual(movimiento.referencia, comprobante.numero_comprobante)

    def test_descripcion_incluye_informacion_reserva(self):
        """
        Test: La descripción del movimiento incluye información de la reserva
        """
        # Abrir caja
        apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('500000')
        )

        # Crear comprobante
        comprobante = ComprobantePago.objects.create(
            reserva=self.reserva,
            tipo='sena',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            empleado=self.empleado,
            observaciones='Pago inicial del cliente'
        )

        # Verificar descripción
        movimiento = MovimientoCaja.objects.get(comprobante=comprobante)
        self.assertIn(self.reserva.codigo, movimiento.descripcion)
        self.assertIn(comprobante.numero_comprobante, movimiento.descripcion)
        self.assertIn('Pago inicial del cliente', movimiento.descripcion)


class RecalculoSaldoCajaTestCase(TestCase):
    """Tests específicos para el recálculo de saldo de caja"""

    def setUp(self):
        """Configurar datos básicos"""
        # (Reutilizar setup similar al anterior)
        self.empresa = Empresa.objects.create(ruc='80000000-1', nombre='Test')
        self.establecimiento = Establecimiento.objects.create(
            empresa=self.empresa, codigo='001', nombre='Central'
        )
        self.punto_expedicion = PuntoExpedicion.objects.create(
            establecimiento=self.establecimiento, codigo='001', nombre='Caja 1'
        )
        self.caja = Caja.objects.create(
            nombre='Caja Test',
            punto_expedicion=self.punto_expedicion
        )
        self.persona = PersonaFisica.objects.create(
            nombre='Test', apellido='User', documento='123'
        )
        self.empleado = Empleado.objects.create(
            persona=self.persona, codigo_empleado='EMP001'
        )

        self.apertura = AperturaCaja.objects.create(
            caja=self.caja,
            responsable=self.empleado,
            monto_inicial=Decimal('1000000')
        )

    def test_recalculo_con_movimientos_mixtos(self):
        """
        Test: El recálculo funciona correctamente con ingresos y egresos mezclados
        """
        # Crear movimientos manuales (sin comprobante)
        MovimientoCaja.objects.create(
            apertura_caja=self.apertura,
            tipo_movimiento='ingreso',
            concepto='deposito',
            monto=Decimal('500000'),
            metodo_pago='efectivo',
            usuario_registro=self.empleado
        )

        MovimientoCaja.objects.create(
            apertura_caja=self.apertura,
            tipo_movimiento='egreso',
            concepto='retiro_efectivo',
            monto=Decimal('200000'),
            metodo_pago='efectivo',
            usuario_registro=self.empleado
        )

        MovimientoCaja.objects.create(
            apertura_caja=self.apertura,
            tipo_movimiento='ingreso',
            concepto='otro_ingreso',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            usuario_registro=self.empleado
        )

        # Saldo esperado: 1000000 + 500000 - 200000 + 300000 = 1600000
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('1600000'))

    def test_recalculo_ignora_movimientos_inactivos(self):
        """
        Test: El recálculo ignora movimientos marcados como inactivos
        """
        # Crear movimientos activos
        mov1 = MovimientoCaja.objects.create(
            apertura_caja=self.apertura,
            tipo_movimiento='ingreso',
            concepto='deposito',
            monto=Decimal('500000'),
            metodo_pago='efectivo',
            usuario_registro=self.empleado,
            activo=True
        )

        # Crear movimiento inactivo
        mov2 = MovimientoCaja.objects.create(
            apertura_caja=self.apertura,
            tipo_movimiento='ingreso',
            concepto='deposito',
            monto=Decimal('300000'),
            metodo_pago='efectivo',
            usuario_registro=self.empleado,
            activo=False  # Inactivo
        )

        # Saldo esperado: 1000000 + 500000 = 1500000 (ignora el inactivo)
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal('1500000'))
