"""
Script de prueba para verificar la conversión automática de servicios USD → Moneda del paquete.

Uso:
    python manage.py shell < apps/paquete/test_conversion_servicios.py

o ejecutar en el shell de Django:
    python manage.py shell
    >>> exec(open('apps/paquete/test_conversion_servicios.py').read())
"""

from decimal import Decimal
from apps.paquete.models import Paquete
from apps.servicio.models import Servicio
from apps.moneda.models import Moneda
from django.db.models import Prefetch

print("\n" + "="*70)
print("🧪 TEST: Conversión Automática de Servicios USD → Moneda del Paquete")
print("="*70 + "\n")

# 1. Buscar un paquete con servicios
try:
    # Intentar obtener el último paquete creado con servicios
    paquete = Paquete.objects.prefetch_related(
        'paquete_servicios__servicio',
        'salidas'
    ).filter(
        activo=True,
        paquete_servicios__isnull=False
    ).distinct().first()
    
    if not paquete:
        print("❌ No se encontraron paquetes con servicios.")
        print("   Cree un paquete con servicios para probar la conversión.\n")
        exit()
    
    print(f"📦 Paquete: {paquete.nombre} (ID: {paquete.id})")
    print(f"💰 Moneda del paquete: {paquete.moneda.codigo} ({paquete.moneda.nombre})")
    print(f"🔢 Campo propio: {paquete.propio}")
    print()
    
    # 2. Obtener moneda USD
    try:
        moneda_usd = Moneda.objects.get(codigo='USD')
        print(f"✅ Moneda USD encontrada: {moneda_usd.nombre}")
    except Moneda.DoesNotExist:
        print("❌ Moneda USD no encontrada en la base de datos.")
        print("   Debe crear la moneda USD para que funcione la conversión.\n")
        exit()
    
    print()
    
    # 3. Listar servicios del paquete
    print("-" * 70)
    print("📋 SERVICIOS DEL PAQUETE:")
    print("-" * 70)
    
    servicios = paquete.paquete_servicios.all()
    if not servicios.exists():
        print("❌ Este paquete no tiene servicios asociados.\n")
        exit()
    
    total_servicios_usd = Decimal("0")
    for ps in servicios:
        precio = ps.precio if ps.precio and ps.precio > 0 else ps.servicio.precio
        total_servicios_usd += precio if precio else Decimal("0")
        
        print(f"   • {ps.servicio.nombre}")
        print(f"     - Precio override: {ps.precio if ps.precio else 'N/A'}")
        print(f"     - Precio base: {ps.servicio.precio if ps.servicio.precio else 'N/A'}")
        print(f"     - Precio final: {precio} USD (asumido)")
        print()
    
    print(f"💵 Total servicios en USD: {total_servicios_usd}")
    print()
    
    # 4. Conversión a moneda del paquete
    print("-" * 70)
    print("💱 CONVERSIÓN A MONEDA DEL PAQUETE:")
    print("-" * 70)
    
    if paquete.moneda.codigo == 'USD':
        print(f"✅ El paquete ya está en USD, no se requiere conversión.")
        print(f"   Total servicios: {total_servicios_usd} USD")
    else:
        from apps.paquete.utils import convertir_entre_monedas
        
        # Obtener fecha de referencia de la primera salida
        salida = paquete.salidas.filter(activo=True).first()
        
        if not salida or not salida.fecha_salida:
            print(f"⚠️  No hay salidas con fecha definida.")
            print(f"   No se puede obtener la cotización para la conversión.\n")
            exit()
        
        print(f"📅 Fecha de referencia: {salida.fecha_salida}")
        
        try:
            total_convertido = convertir_entre_monedas(
                total_servicios_usd,
                moneda_usd,
                paquete.moneda,
                salida.fecha_salida
            )
            
            # Obtener la cotización usada
            from apps.moneda.models import CotizacionMoneda
            cotizacion = CotizacionMoneda.objects.filter(
                moneda=moneda_usd,
                fecha__lte=salida.fecha_salida
            ).order_by('-fecha').first()
            
            print(f"📊 Cotización usada:")
            print(f"   - Fecha: {cotizacion.fecha if cotizacion else 'N/A'}")
            print(f"   - Valor: 1 USD = {cotizacion.valor if cotizacion else 'N/A'} {paquete.moneda.codigo}")
            print()
            print(f"🧮 Cálculo:")
            print(f"   {total_servicios_usd} USD × {cotizacion.valor if cotizacion else 0} = {total_convertido} {paquete.moneda.codigo}")
            print()
            print(f"✅ Total servicios convertido: {total_convertido:,.2f} {paquete.moneda.codigo}")
            
        except Exception as e:
            print(f"❌ Error en la conversión: {e}")
            print()
    
    print()
    
    # 5. Cálculo completo del precio_venta_desde
    print("-" * 70)
    print("📊 CÁLCULO COMPLETO DE PRECIO_VENTA_DESDE:")
    print("-" * 70)
    
    salidas = paquete.salidas.filter(activo=True)
    if not salidas.exists():
        print("❌ Este paquete no tiene salidas activas.\n")
        exit()
    
    salida = salidas.first()
    print(f"🚀 Salida seleccionada: {salida.fecha_salida}")
    print(f"   - Precio venta sugerido min: {salida.precio_venta_sugerido_min:,.2f} {paquete.moneda.codigo}")
    print()
    
    if paquete.moneda.codigo == 'USD':
        precio_venta_desde = salida.precio_venta_sugerido_min + total_servicios_usd
        print(f"🧮 Cálculo (paquete en USD):")
        print(f"   precio_venta_desde = {salida.precio_venta_sugerido_min} + {total_servicios_usd}")
        print(f"   precio_venta_desde = {precio_venta_desde} USD")
    else:
        try:
            total_convertido = convertir_entre_monedas(
                total_servicios_usd,
                moneda_usd,
                paquete.moneda,
                salida.fecha_salida
            )
            
            # Verificar si debe sumar servicios (solo para distribuidoras)
            if not paquete.propio:
                precio_venta_desde = salida.precio_venta_sugerido_min + total_convertido
                print(f"🧮 Cálculo (distribuidora, suma servicios):")
                print(f"   precio_venta_desde = {salida.precio_venta_sugerido_min:,.2f} + {total_convertido:,.2f}")
                print(f"   precio_venta_desde = {precio_venta_desde:,.2f} {paquete.moneda.codigo}")
            else:
                precio_venta_desde = salida.precio_venta_sugerido_min
                print(f"🧮 Cálculo (paquete propio, servicios ya incluidos):")
                print(f"   precio_venta_desde = {salida.precio_venta_sugerido_min:,.2f} {paquete.moneda.codigo}")
                print(f"   (servicios convertidos: {total_convertido:,.2f} ya incluidos)")
            
        except Exception as e:
            print(f"❌ Error calculando precio_venta_desde: {e}")
            precio_venta_desde = salida.precio_venta_sugerido_min
    
    print()
    print("-" * 70)
    print(f"✅ RESULTADO FINAL: {precio_venta_desde:,.2f} {paquete.moneda.codigo}")
    print("-" * 70)
    print()
    
    # 6. Comparar con el valor en la base de datos
    from apps.paquete.serializers import PaqueteListadoSerializer
    from rest_framework.request import Request
    from django.test import RequestFactory
    
    factory = RequestFactory()
    request = factory.get('/')
    
    serializer = PaqueteListadoSerializer(paquete, context={'request': request})
    precio_desde_serializer = serializer.data.get('precio_venta_desde', 0)
    
    print("-" * 70)
    print("🔍 VERIFICACIÓN CON SERIALIZER:")
    print("-" * 70)
    print(f"   Calculado manualmente: {precio_venta_desde:,.2f} {paquete.moneda.codigo}")
    print(f"   Desde serializer: {precio_desde_serializer:,.2f} {paquete.moneda.codigo}")
    
    diferencia = abs(float(precio_venta_desde) - float(precio_desde_serializer))
    if diferencia < 0.01:
        print(f"   ✅ COINCIDEN (diferencia: {diferencia})")
    else:
        print(f"   ⚠️  DIFIEREN (diferencia: {diferencia:,.2f})")
    
    print()

except Exception as e:
    print(f"\n❌ Error ejecutando el test: {e}")
    import traceback
    traceback.print_exc()
    print()

print("="*70)
print("✅ Test completado")
print("="*70 + "\n")


