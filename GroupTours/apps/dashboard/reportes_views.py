"""
Views para reportes detallados con filtros y paginación.
Retorna datos en formato JSON listo para frontend.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
from decimal import Decimal
import csv

from apps.arqueo_caja.models import MovimientoCaja
from apps.reserva.models import Reserva
from apps.paquete.models import Paquete
from .reportes_serializers import (
    MovimientoCajaReporteSerializer,
    PaqueteReporteSerializer,
    ReservaReporteSerializer
)
from .reportes_utils import (
    generar_pdf_movimientos_cajas,
    generar_excel_movimientos_cajas,
    generar_pdf_paquetes,
    generar_excel_paquetes,
    generar_pdf_reservas,
    generar_excel_reservas
)


# ============================================================================
# UTILIDADES
# ============================================================================

def paginar_resultados(queryset, page, page_size):
    """
    Pagina un queryset y retorna estructura estándar.
    
    Returns:
        dict: {
            'totalItems': int,
            'pageSize': int,
            'totalPages': int,
            'currentPage': int,
            'results': list
        }
    """
    # Validar page_size
    try:
        page_size = int(page_size)
        if page_size not in [10, 20, 50, 100]:
            page_size = 20  # default
    except (ValueError, TypeError):
        page_size = 20
    
    # Validar page
    try:
        page = int(page)
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    
    # Contar total
    total_items = queryset.count()
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    
    # Ajustar página si está fuera de rango
    if page > total_pages:
        page = total_pages
    
    # Calcular índices
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    # Obtener resultados
    results = queryset[start_index:end_index]
    
    return {
        'totalItems': total_items,
        'pageSize': page_size,
        'totalPages': total_pages,
        'currentPage': page,
        'results': results
    }


def parsear_fecha(fecha_str, default=None):
    """
    Parsea una fecha en formato YYYY-MM-DD.
    
    Args:
        fecha_str: String con fecha
        default: Valor por defecto si falla
    
    Returns:
        date o None
    """
    if not fecha_str:
        return default
    
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return default


def filtrar_paquetes_por_cupos(queryset, tiene_cupos_str):
    """
    Filtra un queryset de Paquetes según disponibilidad de cupos.
    
    Args:
        queryset: QuerySet de Paquete
        tiene_cupos_str: 'true' o 'false' (string)
    
    Returns:
        QuerySet filtrado con IDs de paquetes
    """
    from apps.paquete.models import SalidaPaquete
    from apps.reserva.models import Reserva
    
    if tiene_cupos_str.lower() == 'true':
        # Paquetes CON cupos disponibles
        paquetes_con_cupos = []
        for paquete in queryset.filter(propio=True):
            salida = paquete.salidas.filter(activo=True).order_by('fecha_salida').first()
            if salida and salida.cupo:
                reservas = Reserva.objects.filter(
                    salida=salida,
                    activo=True
                ).exclude(estado='cancelada')
                ocupados = sum(r.cantidad_pasajeros or 0 for r in reservas)
                disponibles = salida.cupo - ocupados
                
                if disponibles > 0:
                    paquetes_con_cupos.append(paquete.id)
        
        return queryset.filter(id__in=paquetes_con_cupos)
    
    elif tiene_cupos_str.lower() == 'false':
        # Paquetes SIN cupos disponibles (cupos <= 0 o de distribuidora)
        paquetes_sin_cupos = []
        for paquete in queryset:
            if not paquete.propio:
                # Distribuidoras no manejan cupos, se consideran "sin cupos" para filtrado
                paquetes_sin_cupos.append(paquete.id)
            else:
                salida = paquete.salidas.filter(activo=True).order_by('fecha_salida').first()
                if salida and salida.cupo:
                    reservas = Reserva.objects.filter(
                        salida=salida,
                        activo=True
                    ).exclude(estado='cancelada')
                    ocupados = sum(r.cantidad_pasajeros or 0 for r in reservas)
                    disponibles = salida.cupo - ocupados
                    
                    if disponibles <= 0:
                        paquetes_sin_cupos.append(paquete.id)
                else:
                    # Si no tiene salida o cupo definido, incluir
                    paquetes_sin_cupos.append(paquete.id)
        
        return queryset.filter(id__in=paquetes_sin_cupos)
    
    return queryset


def calcular_precio_promedio_usd(salidas_o_paquetes, es_queryset_paquetes=False):
    """
    Calcula el precio promedio en USD.
    
    Args:
        salidas_o_paquetes: QuerySet de SalidaPaquete o QuerySet de Paquete
        es_queryset_paquetes: Si es True, considera solo la próxima salida de cada paquete
    
    Returns:
        float: Precio promedio en USD o None si no hay datos
    """
    from apps.moneda.models import Moneda, CotizacionMoneda
    from apps.paquete.models import SalidaPaquete
    
    try:
        total_usd = Decimal('0')
        count = 0
        
        # Si recibimos paquetes, obtener solo la próxima salida de cada uno
        if es_queryset_paquetes:
            for paquete in salidas_o_paquetes:
                proxima_salida = paquete.salidas.filter(activo=True).order_by('fecha_salida').first()
                if not proxima_salida:
                    continue
                
                precio = proxima_salida.precio_final or proxima_salida.precio_actual or Decimal('0')
                if precio <= 0:
                    continue
                
                # Convertir a USD según la moneda del paquete
                if paquete.moneda and paquete.moneda.codigo == 'USD':
                    total_usd += precio
                    count += 1
                elif paquete.moneda and paquete.moneda.codigo == 'PYG':
                    moneda_usd = Moneda.objects.get(codigo='USD')
                    cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                    if cotizacion and cotizacion.valor_en_guaranies > 0:
                        precio_usd = precio / cotizacion.valor_en_guaranies
                        total_usd += precio_usd
                        count += 1
                else:
                    if paquete.moneda:
                        try:
                            precio_gs = CotizacionMoneda.convertir_a_guaranies(precio, paquete.moneda)
                            moneda_usd = Moneda.objects.get(codigo='USD')
                            cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                            if cotizacion and cotizacion.valor_en_guaranies > 0:
                                precio_usd = precio_gs / cotizacion.valor_en_guaranies
                                total_usd += precio_usd
                                count += 1
                        except:
                            pass
        else:
            # Si recibimos salidas directamente (comportamiento anterior)
            salidas = salidas_o_paquetes
            if not salidas.exists():
                return None
            
            for salida in salidas:
                paquete = salida.paquete
                precio = salida.precio_actual or Decimal('0')
                
                if precio <= 0:
                    continue
                
                # Si el paquete está en USD, usar directamente
                if paquete.moneda and paquete.moneda.codigo == 'USD':
                    total_usd += precio
                    count += 1
                # Si está en PYG, convertir a USD
                elif paquete.moneda and paquete.moneda.codigo == 'PYG':
                    moneda_usd = Moneda.objects.get(codigo='USD')
                    cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                    if cotizacion and cotizacion.valor_en_guaranies > 0:
                        precio_usd = precio / cotizacion.valor_en_guaranies
                        total_usd += precio_usd
                        count += 1
                else:
                    # Para otras monedas, primero convertir a Gs, luego a USD
                    if paquete.moneda:
                        try:
                            precio_gs = CotizacionMoneda.convertir_a_guaranies(precio, paquete.moneda)
                            moneda_usd = Moneda.objects.get(codigo='USD')
                            cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                            if cotizacion and cotizacion.valor_en_guaranies > 0:
                                precio_usd = precio_gs / cotizacion.valor_en_guaranies
                                total_usd += precio_usd
                                count += 1
                        except:
                            pass
        
        if count > 0:
            return float(round(total_usd / count, 2))
        return None
        
    except Exception as e:
        print(f"Error calculando precio_promedio_usd: {e}")
        return None


def calcular_precio_promedio_pyg(salidas_o_paquetes, es_queryset_paquetes=False):
    """
    Calcula el precio promedio en PYG (guaraníes).
    
    Args:
        salidas_o_paquetes: QuerySet de SalidaPaquete o QuerySet de Paquete
        es_queryset_paquetes: Si es True, considera solo la próxima salida de cada paquete
    
    Returns:
        float: Precio promedio en PYG o None si no hay datos
    """
    from apps.moneda.models import CotizacionMoneda
    from apps.paquete.models import SalidaPaquete
    
    try:
        total_pyg = Decimal('0')
        count = 0
        
        # Si recibimos paquetes, obtener solo la próxima salida de cada uno
        if es_queryset_paquetes:
            for paquete in salidas_o_paquetes:
                proxima_salida = paquete.salidas.filter(activo=True).order_by('fecha_salida').first()
                if not proxima_salida:
                    continue
                
                precio = proxima_salida.precio_final or proxima_salida.precio_actual or Decimal('0')
                if precio <= 0:
                    continue
                
                # Convertir a PYG según la moneda del paquete
                if paquete.moneda and paquete.moneda.codigo == 'PYG':
                    total_pyg += precio
                    count += 1
                elif paquete.moneda:
                    try:
                        precio_gs = CotizacionMoneda.convertir_a_guaranies(precio, paquete.moneda)
                        total_pyg += precio_gs
                        count += 1
                    except:
                        pass
        else:
            # Si recibimos salidas directamente (comportamiento anterior)
            salidas = salidas_o_paquetes
            if not salidas.exists():
                return None
            
            for salida in salidas:
                paquete = salida.paquete
                precio = salida.precio_actual or Decimal('0')
                
                if precio <= 0:
                    continue
                
                # Si el paquete está en PYG, usar directamente
                if paquete.moneda and paquete.moneda.codigo == 'PYG':
                    total_pyg += precio
                    count += 1
                # Si está en otra moneda, convertir a PYG
                elif paquete.moneda:
                    try:
                        precio_gs = CotizacionMoneda.convertir_a_guaranies(precio, paquete.moneda)
                        total_pyg += precio_gs
                        count += 1
                    except:
                        pass
        
        if count > 0:
            return float(round(total_pyg / count, 2))
        return None
        
    except Exception as e:
        print(f"Error calculando precio_promedio_pyg: {e}")
        return None


# ============================================================================
# 1. REPORTE DE MOVIMIENTOS DE CAJAS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_movimientos_cajas(request):
    """
    GET /api/dashboard/reportes/movimientos-cajas/
    
    Retorna listado detallado de movimientos de cajas con filtros.
    
    Parámetros:
    - fecha_desde (REQUERIDO): YYYY-MM-DD
    - fecha_hasta (REQUERIDO): YYYY-MM-DD
    - caja_id: ID de caja
    - tipo_movimiento: ingreso, egreso, todas
    - metodo_pago: efectivo, transferencia, etc.
    - concepto: código del concepto
    - busqueda: texto libre en descripción/referencia
    - page: número de página (default: 1)
    - page_size: registros por página (default: 20, opciones: 10,20,50,100)
    """
    try:
        # ===== VALIDAR FECHAS REQUERIDAS =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if not fecha_desde_str or not fecha_hasta_str:
            return Response(
                {
                    "success": False,
                    "message": "Los parámetros fecha_desde y fecha_hasta son obligatorios",
                    "errors": ["Debe especificar fecha_desde y fecha_hasta en formato YYYY-MM-DD"]
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fecha_desde = parsear_fecha(fecha_desde_str)
        fecha_hasta = parsear_fecha(fecha_hasta_str)
        
        if not fecha_desde or not fecha_hasta:
            return Response(
                {
                    "success": False,
                    "message": "Formato de fecha inválido",
                    "errors": ["Use formato YYYY-MM-DD para las fechas"]
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if fecha_desde > fecha_hasta:
            return Response(
                {
                    "success": False,
                    "message": "fecha_desde debe ser menor o igual a fecha_hasta",
                    "errors": ["Rango de fechas inválido"]
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ===== CONSTRUIR QUERY BASE =====
        queryset = MovimientoCaja.objects.filter(
            fecha_hora_movimiento__date__gte=fecha_desde,
            fecha_hora_movimiento__date__lte=fecha_hasta,
            activo=True
        ).select_related(
            'apertura_caja',
            'apertura_caja__caja',
            'usuario_registro',
            'usuario_registro__persona',
            'comprobante'
        ).order_by('-fecha_hora_movimiento')
        
        # ===== APLICAR FILTROS =====
        caja_id = request.query_params.get('caja_id')
        if caja_id:
            queryset = queryset.filter(apertura_caja__caja_id=caja_id)
        
        tipo_movimiento = request.query_params.get('tipo_movimiento')
        if tipo_movimiento and tipo_movimiento != 'todas':
            queryset = queryset.filter(tipo_movimiento=tipo_movimiento)
        
        metodo_pago = request.query_params.get('metodo_pago')
        if metodo_pago:
            queryset = queryset.filter(metodo_pago=metodo_pago)
        
        concepto = request.query_params.get('concepto')
        if concepto:
            queryset = queryset.filter(concepto=concepto)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(descripcion__icontains=busqueda) |
                Q(referencia__icontains=busqueda) |
                Q(numero_movimiento__icontains=busqueda)
            )
        
        # ===== CALCULAR RESUMEN =====
        resumen_data = queryset.aggregate(
            total_ingresos=Sum('monto', filter=Q(tipo_movimiento='ingreso')),
            total_egresos=Sum('monto', filter=Q(tipo_movimiento='egreso')),
            ingresos_count=Count('id', filter=Q(tipo_movimiento='ingreso')),
            egresos_count=Count('id', filter=Q(tipo_movimiento='egreso'))
        )
        
        total_ingresos_gs = resumen_data['total_ingresos'] or Decimal('0')
        total_egresos_gs = resumen_data['total_egresos'] or Decimal('0')
        balance_gs = total_ingresos_gs - total_egresos_gs
        
        # Convertir a USD usando cotización vigente más reciente
        total_ingresos_usd = None
        total_egresos_usd = None
        balance_usd = None
        
        try:
            from apps.moneda.models import Moneda, CotizacionMoneda
            
            moneda_usd = Moneda.objects.get(codigo='USD')
            # Usar la cotización del último día del rango
            cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd, fecha_hasta)
            
            if cotizacion and cotizacion.valor_en_guaranies > 0:
                tasa = Decimal(str(cotizacion.valor_en_guaranies))
                total_ingresos_usd = float(round(total_ingresos_gs / tasa, 2))
                total_egresos_usd = float(round(total_egresos_gs / tasa, 2))
                balance_usd = float(round(balance_gs / tasa, 2))
        except (Moneda.DoesNotExist, Exception):
            pass  # Si no hay cotización, los valores USD quedan en None
        
        resumen = {
            "total_registros": queryset.count(),
            "total_ingresos_gs": float(total_ingresos_gs),
            "total_egresos_gs": float(total_egresos_gs),
            "balance_gs": float(balance_gs),
            "total_ingresos_usd": total_ingresos_usd,
            "total_egresos_usd": total_egresos_usd,
            "balance_usd": balance_usd,
            "ingresos_count": resumen_data['ingresos_count'],
            "egresos_count": resumen_data['egresos_count']
        }
        
        # ===== PAGINAR =====
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        paginacion = paginar_resultados(queryset, page, page_size)
        
        # ===== SERIALIZAR =====
        serializer = MovimientoCajaReporteSerializer(paginacion['results'], many=True)
        paginacion['results'] = serializer.data
        
        # ===== RESPUESTA =====
        return Response({
            "success": True,
            "filtros_aplicados": {
                "fecha_desde": fecha_desde_str,
                "fecha_hasta": fecha_hasta_str,
                "caja_id": caja_id,
                "tipo_movimiento": tipo_movimiento or "todas"
            },
            "resumen": resumen,
            "data": paginacion
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al generar reporte de movimientos",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# 2. REPORTE DE PAQUETES
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_paquetes(request):
    """
    GET /api/dashboard/reportes/paquetes/
    
    Retorna listado detallado de paquetes con filtros.
    
    Parámetros:
    - fecha_desde: YYYY-MM-DD (fecha creación)
    - fecha_hasta: YYYY-MM-DD (fecha creación)
    - fecha_salida_desde: YYYY-MM-DD
    - fecha_salida_hasta: YYYY-MM-DD
    - destino_id: ID de destino
    - tipo_paquete_id: ID de tipo de paquete
    - estado: activo, inactivo, todos (default: activo)
    - personalizado: true/false
    - propio: true/false
    - distribuidora_id: ID de distribuidora
    - busqueda: texto en nombre
    - ordenar_por: fecha, precio, nombre
    - page: número de página
    - page_size: registros por página
    """
    try:
        # ===== CONSTRUIR QUERY BASE =====
        queryset = Paquete.objects.all().select_related(
            'tipo_paquete',
            'destino',
            'destino__ciudad',
            'destino__ciudad__pais',
            'distribuidora',
            'moneda'
        ).prefetch_related(
            'salidas',
            'reservas',
            'paquete_servicios__servicio'
        )
        
        # ===== FILTRO POR ESTADO =====
        estado = request.query_params.get('estado', 'activo')
        if estado == 'activo':
            queryset = queryset.filter(activo=True)
        elif estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        # 'todos' = no filtrar
        
        # ===== FILTRO POR FECHAS DE CREACIÓN =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if fecha_desde_str:
            fecha_desde = parsear_fecha(fecha_desde_str)
            if fecha_desde:
                queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
        
        if fecha_hasta_str:
            fecha_hasta = parsear_fecha(fecha_hasta_str)
            if fecha_hasta:
                queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)
        
        # ===== FILTRO POR FECHAS DE SALIDA =====
        fecha_salida_desde_str = request.query_params.get('fecha_salida_desde')
        fecha_salida_hasta_str = request.query_params.get('fecha_salida_hasta')
        
        if fecha_salida_desde_str or fecha_salida_hasta_str:
            from apps.paquete.models import SalidaPaquete
            salidas_ids = SalidaPaquete.objects.filter(activo=True)
            
            if fecha_salida_desde_str:
                fecha = parsear_fecha(fecha_salida_desde_str)
                if fecha:
                    salidas_ids = salidas_ids.filter(fecha_salida__gte=fecha)
            
            if fecha_salida_hasta_str:
                fecha = parsear_fecha(fecha_salida_hasta_str)
                if fecha:
                    salidas_ids = salidas_ids.filter(fecha_salida__lte=fecha)
            
            paquetes_ids = salidas_ids.values_list('paquete_id', flat=True).distinct()
            queryset = queryset.filter(id__in=paquetes_ids)
        
        # ===== OTROS FILTROS =====
        destino_id = request.query_params.get('destino_id')
        if destino_id:
            queryset = queryset.filter(destino_id=destino_id)
        
        zona_geografica_id = request.query_params.get('zona_geografica_id')
        if zona_geografica_id:
            queryset = queryset.filter(destino__ciudad__pais__zona_geografica_id=zona_geografica_id)
        
        pais_id = request.query_params.get('pais_id')
        if pais_id:
            queryset = queryset.filter(destino__ciudad__pais_id=pais_id)
        
        tipo_paquete_id = request.query_params.get('tipo_paquete_id')
        if tipo_paquete_id:
            queryset = queryset.filter(tipo_paquete_id=tipo_paquete_id)
        
        personalizado = request.query_params.get('personalizado')
        if personalizado is not None:
            queryset = queryset.filter(personalizado=(personalizado.lower() == 'true'))
        
        propio = request.query_params.get('propio')
        if propio is not None:
            queryset = queryset.filter(propio=(propio.lower() == 'true'))
        
        distribuidora_id = request.query_params.get('distribuidora_id')
        if distribuidora_id:
            queryset = queryset.filter(distribuidora_id=distribuidora_id)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            # Intentar extraer el ID del código si viene en formato PAQ-2024-XXXX o PAQ-XXXX
            paquete_id = None
            busqueda_upper = busqueda.upper().strip()
            
            if busqueda_upper.startswith('PAQ'):
                # Formato: PAQ-2024-0142, PAQ-2024-142, PAQ-142
                parts = busqueda_upper.replace('PAQ-', '').replace('PAQ', '').strip('-').split('-')
                # Tomar el último número (puede ser solo uno si es PAQ-142)
                try:
                    paquete_id = int(parts[-1])
                except (ValueError, IndexError):
                    pass
            elif busqueda.isdigit():
                # Si es solo un número, usarlo como ID directamente
                paquete_id = int(busqueda)
            
            # Filtrar por ID o por nombre
            if paquete_id:
                queryset = queryset.filter(
                    Q(id=paquete_id) | Q(nombre__icontains=busqueda)
                )
            else:
                queryset = queryset.filter(nombre__icontains=busqueda)
        
        # ===== FILTRO: SALIDAS EN PRÓXIMOS X DÍAS =====
        fecha_salida_proxima = request.query_params.get('fecha_salida_proxima')
        if fecha_salida_proxima:
            try:
                dias = int(fecha_salida_proxima)
                from apps.paquete.models import SalidaPaquete
                from django.utils import timezone
                fecha_limite = timezone.now().date() + timedelta(days=dias)
                salidas_proximas = SalidaPaquete.objects.filter(
                    activo=True,
                    fecha_salida__gte=timezone.now().date(),
                    fecha_salida__lte=fecha_limite
                )
                paquetes_ids = salidas_proximas.values_list('paquete_id', flat=True).distinct()
                queryset = queryset.filter(id__in=paquetes_ids)
            except (ValueError, TypeError):
                pass
        
        # ===== FILTRO: SOLO CON CUPOS DISPONIBLES =====
        tiene_cupos_disponibles = request.query_params.get('tiene_cupos_disponibles')
        if tiene_cupos_disponibles is not None:
            queryset = filtrar_paquetes_por_cupos(queryset, tiene_cupos_disponibles)
        
        # ===== ORDENAMIENTO =====
        ordenar_por = request.query_params.get('ordenar_por', 'fecha')
        if ordenar_por == 'nombre':
            queryset = queryset.order_by('nombre')
        elif ordenar_por == 'fecha':
            queryset = queryset.order_by('-fecha_creacion')
        else:
            queryset = queryset.order_by('-fecha_creacion')
        
        # ===== CALCULAR RESUMEN =====
        total_registros = queryset.count()
        paquetes_activos = queryset.filter(activo=True).count()
        paquetes_inactivos = queryset.filter(activo=False).count()
        paquetes_personalizados = queryset.filter(personalizado=True).count()
        
        # Calcular precios (de salidas)
        from apps.paquete.models import SalidaPaquete
        salidas = SalidaPaquete.objects.filter(
            paquete__in=queryset,
            activo=True
        )
        
        if salidas.exists():
            precio_stats = salidas.aggregate(
                promedio=Avg('precio_actual')
            )
            salida_minima = salidas.order_by('precio_actual').first()
            salida_maxima = salidas.order_by('-precio_actual').first()
            
            precio_promedio = str(precio_stats['promedio'] or Decimal('0'))
            precio_minimo = str(salida_minima.precio_actual if salida_minima else Decimal('0'))
            precio_maximo = str(salida_maxima.precio_actual if salida_maxima else Decimal('0'))
            
            # Calcular promedios en ambas monedas (usando solo la próxima salida de cada paquete)
            precio_promedio_pyg = calcular_precio_promedio_pyg(queryset, es_queryset_paquetes=True)
            precio_promedio_usd = calcular_precio_promedio_usd(queryset, es_queryset_paquetes=True)
        else:
            precio_promedio = "0.00"
            precio_minimo = "0.00"
            precio_maximo = "0.00"
            precio_promedio_pyg = None
            precio_promedio_usd = None
        
        resumen = {
            "total_registros": total_registros,
            "paquetes_activos": paquetes_activos,
            "paquetes_inactivos": paquetes_inactivos,
            "paquetes_personalizados": paquetes_personalizados,
            "precio_promedio": precio_promedio,
            "precio_promedio_pyg": precio_promedio_pyg,
            "precio_promedio_usd": precio_promedio_usd,
            "precio_minimo": precio_minimo,
            "precio_maximo": precio_maximo
        }
        
        # ===== PAGINAR =====
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        paginacion = paginar_resultados(queryset, page, page_size)
        
        # ===== SERIALIZAR =====
        serializer = PaqueteReporteSerializer(paginacion['results'], many=True)
        paginacion['results'] = serializer.data
        
        # ===== RESPUESTA =====
        return Response({
            "success": True,
            "filtros_aplicados": {
                "fecha_desde": fecha_desde_str,
                "fecha_hasta": fecha_hasta_str,
                "estado": estado,
                "destino_id": destino_id
            },
            "resumen": resumen,
            "data": paginacion
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al generar reporte de paquetes",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# 3. REPORTE DE RESERVAS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_reservas(request):
    """
    GET /api/dashboard/reportes/reservas/
    
    Retorna listado detallado de reservas con filtros.
    
    Parámetros:
    - fecha_desde: YYYY-MM-DD (fecha reserva)
    - fecha_hasta: YYYY-MM-DD (fecha reserva)
    - fecha_salida_desde: YYYY-MM-DD
    - fecha_salida_hasta: YYYY-MM-DD
    - estado: pendiente, confirmada, finalizada, cancelada, todas
    - estado_pago: sin_pagar, pago_parcial, pago_completo, todas
    - paquete_id: ID de paquete
    - destino_id: ID de destino
    - titular_documento: número de documento
    - busqueda: texto en código/titular
    - modalidad_facturacion: global, individual
    - ordenar_por: fecha, monto, estado
    - page: número de página
    - page_size: registros por página
    """
    try:
        # ===== CONSTRUIR QUERY BASE =====
        queryset = Reserva.objects.filter(
            activo=True
        ).select_related(
            'titular',
            'paquete',
            'paquete__destino',
            'paquete__destino__ciudad',
            'paquete__destino__ciudad__pais',
            'paquete__moneda',
            'salida',
            'habitacion',
            'habitacion__hotel',
            'habitacion__tipo_habitacion'
        ).prefetch_related('pasajeros')
        
        # ===== FILTRO POR FECHAS DE RESERVA =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if fecha_desde_str:
            fecha_desde = parsear_fecha(fecha_desde_str)
            if fecha_desde:
                queryset = queryset.filter(fecha_reserva__date__gte=fecha_desde)
        
        if fecha_hasta_str:
            fecha_hasta = parsear_fecha(fecha_hasta_str)
            if fecha_hasta:
                queryset = queryset.filter(fecha_reserva__date__lte=fecha_hasta)
        
        # ===== FILTRO POR FECHAS DE SALIDA =====
        fecha_salida_desde_str = request.query_params.get('fecha_salida_desde')
        fecha_salida_hasta_str = request.query_params.get('fecha_salida_hasta')
        
        if fecha_salida_desde_str:
            fecha = parsear_fecha(fecha_salida_desde_str)
            if fecha:
                queryset = queryset.filter(salida__fecha_salida__gte=fecha)
        
        if fecha_salida_hasta_str:
            fecha = parsear_fecha(fecha_salida_hasta_str)
            if fecha:
                queryset = queryset.filter(salida__fecha_salida__lte=fecha)
        
        # ===== FILTRO POR ESTADO =====
        estado = request.query_params.get('estado')
        if estado and estado != 'todas':
            queryset = queryset.filter(estado=estado)
        
        # ===== FILTRO POR ESTADO DE PAGO =====
        # Este filtro se aplicará después de serializar porque es calculado
        estado_pago_filtro = request.query_params.get('estado_pago')
        
        # ===== OTROS FILTROS =====
        paquete_id = request.query_params.get('paquete_id')
        if paquete_id:
            queryset = queryset.filter(paquete_id=paquete_id)
        
        destino_id = request.query_params.get('destino_id')
        if destino_id:
            queryset = queryset.filter(paquete__destino_id=destino_id)
        
        titular_documento = request.query_params.get('titular_documento')
        if titular_documento:
            queryset = queryset.filter(titular__documento__icontains=titular_documento)
        
        modalidad_facturacion = request.query_params.get('modalidad_facturacion')
        if modalidad_facturacion:
            queryset = queryset.filter(modalidad_facturacion=modalidad_facturacion)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(codigo__icontains=busqueda) |
                Q(titular__nombres__icontains=busqueda) |
                Q(titular__apellidos__icontains=busqueda)
            )
        
        # ===== ORDENAMIENTO =====
        ordenar_por = request.query_params.get('ordenar_por', 'fecha')
        if ordenar_por == 'fecha':
            queryset = queryset.order_by('-fecha_reserva')
        elif ordenar_por == 'monto':
            queryset = queryset.order_by('-precio_unitario')
        elif ordenar_por == 'estado':
            queryset = queryset.order_by('estado')
        else:
            queryset = queryset.order_by('-fecha_reserva')
        
        # ===== CALCULAR RESUMEN (antes de paginar) =====
        reservas_por_estado = {
            'pendiente': queryset.filter(estado='pendiente').count(),
            'confirmada': queryset.filter(estado='confirmada').count(),
            'finalizada': queryset.filter(estado='finalizada').count(),
            'cancelada': queryset.filter(estado='cancelada').count()
        }
        
        # Calcular totales (excluyendo canceladas)
        reservas_activas = queryset.exclude(estado='cancelada')
        
        total_pasajeros = sum(r.cantidad_pasajeros or 0 for r in reservas_activas)
        
        # Calcular montos
        monto_total_gs = Decimal('0')
        monto_pagado_total_gs = Decimal('0')
        monto_total_usd = Decimal('0')
        monto_pagado_total_usd = Decimal('0')
        
        # Flag para saber si tenemos datos en USD
        tiene_cotizacion_usd = False
        
        try:
            from apps.moneda.models import Moneda, CotizacionMoneda
            moneda_usd = Moneda.objects.get(codigo='USD')
            cotizacion_usd = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
            tiene_cotizacion_usd = cotizacion_usd is not None
        except Exception:
            pass
        
        for reserva in reservas_activas:
            if reserva.precio_unitario and reserva.cantidad_pasajeros:
                monto_reserva = reserva.precio_unitario * reserva.cantidad_pasajeros
                monto_pagado_reserva = reserva.monto_pagado or Decimal('0')
                
                # Sumar en moneda original o convertir
                if reserva.paquete and reserva.paquete.moneda:
                    if reserva.paquete.moneda.codigo == 'PYG':
                        # Ya está en Gs
                        monto_total_gs += monto_reserva
                        monto_pagado_total_gs += monto_pagado_reserva
                        
                        # Convertir a USD
                        if tiene_cotizacion_usd and cotizacion_usd.valor_en_guaranies > 0:
                            monto_total_usd += monto_reserva / cotizacion_usd.valor_en_guaranies
                            monto_pagado_total_usd += monto_pagado_reserva / cotizacion_usd.valor_en_guaranies
                    
                    elif reserva.paquete.moneda.codigo == 'USD':
                        # Ya está en USD
                        monto_total_usd += monto_reserva
                        monto_pagado_total_usd += monto_pagado_reserva
                        
                        # Convertir a Gs
                        if tiene_cotizacion_usd:
                            monto_total_gs += monto_reserva * cotizacion_usd.valor_en_guaranies
                            monto_pagado_total_gs += monto_pagado_reserva * cotizacion_usd.valor_en_guaranies
                    
                    else:
                        # Otra moneda: convertir a Gs y luego a USD
                        try:
                            from apps.moneda.models import CotizacionMoneda
                            monto_gs = CotizacionMoneda.convertir_a_guaranies(monto_reserva, reserva.paquete.moneda)
                            pagado_gs = CotizacionMoneda.convertir_a_guaranies(monto_pagado_reserva, reserva.paquete.moneda)
                            
                            monto_total_gs += monto_gs
                            monto_pagado_total_gs += pagado_gs
                            
                            if tiene_cotizacion_usd and cotizacion_usd.valor_en_guaranies > 0:
                                monto_total_usd += monto_gs / cotizacion_usd.valor_en_guaranies
                                monto_pagado_total_usd += pagado_gs / cotizacion_usd.valor_en_guaranies
                        except Exception:
                            pass
                else:
                    # Sin moneda definida, asumir Gs
                    monto_total_gs += monto_reserva
                    monto_pagado_total_gs += monto_pagado_reserva
        
        saldo_pendiente_gs = monto_total_gs - monto_pagado_total_gs
        saldo_pendiente_usd = monto_total_usd - monto_pagado_total_usd if tiene_cotizacion_usd else None
        
        resumen = {
            "total_registros": queryset.count(),
            "reservas_pendientes": reservas_por_estado['pendiente'],
            "reservas_confirmadas": reservas_por_estado['confirmada'],
            "reservas_finalizadas": reservas_por_estado['finalizada'],
            "reservas_canceladas": reservas_por_estado['cancelada'],
            "monto_total_gs": float(monto_total_gs),
            "monto_pagado_gs": float(monto_pagado_total_gs),
            "saldo_pendiente_gs": float(saldo_pendiente_gs),
            "monto_total_usd": float(round(monto_total_usd, 2)) if tiene_cotizacion_usd else None,
            "monto_pagado_usd": float(round(monto_pagado_total_usd, 2)) if tiene_cotizacion_usd else None,
            "saldo_pendiente_usd": float(round(saldo_pendiente_usd, 2)) if saldo_pendiente_usd is not None else None,
            "total_pasajeros": total_pasajeros
        }
        
        # ===== PAGINAR =====
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        paginacion = paginar_resultados(queryset, page, page_size)
        
        # ===== SERIALIZAR =====
        serializer = ReservaReporteSerializer(paginacion['results'], many=True)
        paginacion['results'] = serializer.data
        
        # ===== FILTRAR POR ESTADO DE PAGO (post-serialización) =====
        if estado_pago_filtro and estado_pago_filtro != 'todas':
            paginacion['results'] = [
                r for r in paginacion['results']
                if r['estado_pago'] == estado_pago_filtro
            ]
            # Recalcular totalItems
            paginacion['totalItems'] = len(paginacion['results'])
        
        # ===== RESPUESTA =====
        return Response({
            "success": True,
            "filtros_aplicados": {
                "fecha_desde": fecha_desde_str,
                "fecha_hasta": fecha_hasta_str,
                "estado": estado or "todas",
                "estado_pago": estado_pago_filtro or "todas"
            },
            "resumen": resumen,
            "data": paginacion
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al generar reporte de reservas",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# EXPORTACIÓN PDF - MOVIMIENTOS CAJAS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_movimientos_pdf(request):
    """
    GET /api/dashboard/reportes/movimientos-cajas/exportar-pdf/
    
    Exporta reporte de movimientos de cajas a PDF.
    Acepta los mismos filtros que el endpoint JSON.
    """
    try:
        # ===== VALIDAR FECHAS (OBLIGATORIAS) =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if not fecha_desde_str or not fecha_hasta_str:
            return Response(
                {
                    "success": False,
                    "message": "Los parámetros fecha_desde y fecha_hasta son obligatorios",
                    "errors": ["Formato esperado: YYYY-MM-DD"]
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fecha_desde = parsear_fecha(fecha_desde_str)
        fecha_hasta = parsear_fecha(fecha_hasta_str)
        
        if not fecha_desde or not fecha_hasta:
            return Response(
                {
                    "success": False,
                    "message": "Formato de fecha inválido",
                    "errors": ["Use formato YYYY-MM-DD"]
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if fecha_desde > fecha_hasta:
            return Response(
                {
                    "success": False,
                    "message": "La fecha_desde no puede ser mayor que fecha_hasta"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ===== CONSTRUIR QUERY =====
        queryset = MovimientoCaja.objects.filter(
            activo=True,
            fecha_hora_movimiento__date__gte=fecha_desde,
            fecha_hora_movimiento__date__lte=fecha_hasta
        ).select_related(
            'apertura_caja',
            'apertura_caja__caja',
            'usuario_registro',
            'usuario_registro__persona',
            'comprobante'
        ).order_by('-fecha_hora_movimiento')
        
        # ===== APLICAR FILTROS =====
        caja_id = request.query_params.get('caja_id')
        if caja_id:
            queryset = queryset.filter(apertura_caja__caja_id=caja_id)
        
        tipo_movimiento = request.query_params.get('tipo_movimiento')
        if tipo_movimiento and tipo_movimiento != 'todas':
            queryset = queryset.filter(tipo_movimiento=tipo_movimiento)
        
        metodo_pago = request.query_params.get('metodo_pago')
        if metodo_pago:
            queryset = queryset.filter(metodo_pago=metodo_pago)
        
        concepto = request.query_params.get('concepto')
        if concepto:
            queryset = queryset.filter(concepto=concepto)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(descripcion__icontains=busqueda) |
                Q(referencia__icontains=busqueda) |
                Q(numero_movimiento__icontains=busqueda)
            )
        
        # ===== CALCULAR RESUMEN =====
        resumen_data = queryset.aggregate(
            total_ingresos=Sum('monto', filter=Q(tipo_movimiento='ingreso')),
            total_egresos=Sum('monto', filter=Q(tipo_movimiento='egreso')),
            ingresos_count=Count('id', filter=Q(tipo_movimiento='ingreso')),
            egresos_count=Count('id', filter=Q(tipo_movimiento='egreso'))
        )
        
        total_ingresos = resumen_data['total_ingresos'] or Decimal('0')
        total_egresos = resumen_data['total_egresos'] or Decimal('0')
        balance = total_ingresos - total_egresos
        
        resumen = {
            "total_registros": queryset.count(),
            "total_ingresos": str(total_ingresos),
            "total_egresos": str(total_egresos),
            "balance": str(balance),
            "ingresos_count": resumen_data['ingresos_count'],
            "egresos_count": resumen_data['egresos_count']
        }
        
        # ===== SERIALIZAR TODOS LOS DATOS (sin paginar para PDF) =====
        serializer = MovimientoCajaReporteSerializer(queryset[:1000], many=True)  # Limitar a 1000 registros para PDF
        data = serializer.data
        
        # ===== FILTROS APLICADOS =====
        filtros = {
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "caja_id": caja_id,
            "tipo_movimiento": tipo_movimiento or "todas"
        }
        
        # ===== GENERAR PDF =====
        pdf_buffer = generar_pdf_movimientos_cajas(data, filtros, resumen)
        
        # ===== NOMBRE DEL ARCHIVO =====
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"movimientos_cajas_{fecha_actual}.pdf"
        
        # ===== RESPUESTA =====
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al exportar PDF",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_movimientos_excel(request):
    """
    GET /api/dashboard/reportes/movimientos-cajas/exportar-excel/
    
    Exporta reporte de movimientos de cajas a Excel.
    """
    try:
        # ===== VALIDAR FECHAS (OBLIGATORIAS) =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if not fecha_desde_str or not fecha_hasta_str:
            return Response(
                {
                    "success": False,
                    "message": "Los parámetros fecha_desde y fecha_hasta son obligatorios"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fecha_desde = parsear_fecha(fecha_desde_str)
        fecha_hasta = parsear_fecha(fecha_hasta_str)
        
        if not fecha_desde or not fecha_hasta:
            return Response(
                {
                    "success": False,
                    "message": "Formato de fecha inválido"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ===== CONSTRUIR QUERY (igual que PDF) =====
        queryset = MovimientoCaja.objects.filter(
            activo=True,
            fecha_hora_movimiento__date__gte=fecha_desde,
            fecha_hora_movimiento__date__lte=fecha_hasta
        ).select_related(
            'apertura_caja',
            'apertura_caja__caja',
            'usuario_registro',
            'usuario_registro__persona',
            'comprobante'
        ).order_by('-fecha_hora_movimiento')
        
        # ===== APLICAR FILTROS =====
        caja_id = request.query_params.get('caja_id')
        if caja_id:
            queryset = queryset.filter(apertura_caja__caja_id=caja_id)
        
        tipo_movimiento = request.query_params.get('tipo_movimiento')
        if tipo_movimiento and tipo_movimiento != 'todas':
            queryset = queryset.filter(tipo_movimiento=tipo_movimiento)
        
        metodo_pago = request.query_params.get('metodo_pago')
        if metodo_pago:
            queryset = queryset.filter(metodo_pago=metodo_pago)
        
        concepto = request.query_params.get('concepto')
        if concepto:
            queryset = queryset.filter(concepto=concepto)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(descripcion__icontains=busqueda) |
                Q(referencia__icontains=busqueda) |
                Q(numero_movimiento__icontains=busqueda)
            )
        
        # ===== CALCULAR RESUMEN =====
        resumen_data = queryset.aggregate(
            total_ingresos=Sum('monto', filter=Q(tipo_movimiento='ingreso')),
            total_egresos=Sum('monto', filter=Q(tipo_movimiento='egreso')),
            ingresos_count=Count('id', filter=Q(tipo_movimiento='ingreso')),
            egresos_count=Count('id', filter=Q(tipo_movimiento='egreso'))
        )
        
        total_ingresos = resumen_data['total_ingresos'] or Decimal('0')
        total_egresos = resumen_data['total_egresos'] or Decimal('0')
        balance = total_ingresos - total_egresos
        
        resumen = {
            "total_registros": queryset.count(),
            "total_ingresos": str(total_ingresos),
            "total_egresos": str(total_egresos),
            "balance": str(balance),
            "ingresos_count": resumen_data['ingresos_count'],
            "egresos_count": resumen_data['egresos_count']
        }
        
        # ===== VERIFICAR SI HAY DATOS =====
        total_count = queryset.count()
        print(f"[DEBUG] Total de movimientos encontrados: {total_count}")
        print(f"[DEBUG] Rango de fechas: {fecha_desde_str} a {fecha_hasta_str}")
        
        # ===== SERIALIZAR =====
        serializer = MovimientoCajaReporteSerializer(queryset, many=True)
        data = serializer.data
        
        print(f"[DEBUG] Registros serializados: {len(data)}")
        
        # ===== FILTROS APLICADOS =====
        filtros = {
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "caja_id": caja_id,
            "tipo_movimiento": tipo_movimiento or "todas",
            "total_encontrados": total_count  # Agregar para debug
        }
        
        # ===== GENERAR EXCEL =====
        excel_buffer = generar_excel_movimientos_cajas(data, filtros, resumen)
        
        # ===== NOMBRE DEL ARCHIVO =====
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"movimientos_cajas_{fecha_actual}.xlsx"
        
        # ===== RESPUESTA =====
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al exportar Excel",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# EXPORTACIÓN PDF - PAQUETES
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_paquetes_pdf(request):
    """
    GET /api/dashboard/reportes/paquetes/exportar-pdf/
    
    Exporta reporte de paquetes a PDF.
    """
    try:
        # ===== CONSTRUIR QUERY BASE =====
        queryset = Paquete.objects.all().select_related(
            'tipo_paquete',
            'destino',
            'destino__ciudad',
            'destino__ciudad__pais',
            'distribuidora',
            'moneda'
        ).prefetch_related(
            'salidas',
            'reservas',
            'paquete_servicios__servicio'
        )
        
        # ===== FILTRO POR ESTADO =====
        estado = request.query_params.get('estado', 'activo')
        if estado == 'activo':
            queryset = queryset.filter(activo=True)
        elif estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        
        # ===== FILTRO POR FECHAS DE CREACIÓN =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if fecha_desde_str:
            fecha_desde = parsear_fecha(fecha_desde_str)
            if fecha_desde:
                queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
        
        if fecha_hasta_str:
            fecha_hasta = parsear_fecha(fecha_hasta_str)
            if fecha_hasta:
                queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)
        
        # ===== FILTRO POR FECHAS DE SALIDA =====
        fecha_salida_desde_str = request.query_params.get('fecha_salida_desde')
        fecha_salida_hasta_str = request.query_params.get('fecha_salida_hasta')
        
        if fecha_salida_desde_str or fecha_salida_hasta_str:
            from apps.paquete.models import SalidaPaquete
            salidas_ids = SalidaPaquete.objects.filter(activo=True)
            
            if fecha_salida_desde_str:
                fecha = parsear_fecha(fecha_salida_desde_str)
                if fecha:
                    salidas_ids = salidas_ids.filter(fecha_salida__gte=fecha)
            
            if fecha_salida_hasta_str:
                fecha = parsear_fecha(fecha_salida_hasta_str)
                if fecha:
                    salidas_ids = salidas_ids.filter(fecha_salida__lte=fecha)
            
            paquetes_ids = salidas_ids.values_list('paquete_id', flat=True).distinct()
            queryset = queryset.filter(id__in=paquetes_ids)
        
        # ===== OTROS FILTROS =====
        destino_id = request.query_params.get('destino_id')
        if destino_id:
            queryset = queryset.filter(destino_id=destino_id)
        
        zona_geografica_id = request.query_params.get('zona_geografica_id')
        if zona_geografica_id:
            queryset = queryset.filter(destino__ciudad__pais__zona_geografica_id=zona_geografica_id)
        
        pais_id = request.query_params.get('pais_id')
        if pais_id:
            queryset = queryset.filter(destino__ciudad__pais_id=pais_id)
        
        tipo_paquete_id = request.query_params.get('tipo_paquete_id')
        if tipo_paquete_id:
            queryset = queryset.filter(tipo_paquete_id=tipo_paquete_id)
        
        personalizado = request.query_params.get('personalizado')
        if personalizado is not None:
            queryset = queryset.filter(personalizado=(personalizado.lower() == 'true'))
        
        propio = request.query_params.get('propio')
        if propio is not None:
            queryset = queryset.filter(propio=(propio.lower() == 'true'))
        
        distribuidora_id = request.query_params.get('distribuidora_id')
        if distribuidora_id:
            queryset = queryset.filter(distribuidora_id=distribuidora_id)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            # Intentar extraer el ID del código si viene en formato PAQ-2024-XXXX o PAQ-XXXX
            paquete_id = None
            busqueda_upper = busqueda.upper().strip()
            
            if busqueda_upper.startswith('PAQ'):
                # Formato: PAQ-2024-0142, PAQ-2024-142, PAQ-142
                parts = busqueda_upper.replace('PAQ-', '').replace('PAQ', '').strip('-').split('-')
                # Tomar el último número (puede ser solo uno si es PAQ-142)
                try:
                    paquete_id = int(parts[-1])
                except (ValueError, IndexError):
                    pass
            elif busqueda.isdigit():
                # Si es solo un número, usarlo como ID directamente
                paquete_id = int(busqueda)
            
            # Filtrar por ID o por nombre
            if paquete_id:
                queryset = queryset.filter(
                    Q(id=paquete_id) | Q(nombre__icontains=busqueda)
                )
            else:
                queryset = queryset.filter(nombre__icontains=busqueda)
        
        # ===== FILTRO: FECHA SALIDA PRÓXIMA =====
        fecha_salida_proxima = request.query_params.get('fecha_salida_proxima')
        if fecha_salida_proxima:
            try:
                dias = int(fecha_salida_proxima)
                from apps.paquete.models import SalidaPaquete
                fecha_limite = timezone.now().date() + timedelta(days=dias)
                salidas_proximas = SalidaPaquete.objects.filter(
                    activo=True,
                    fecha_salida__lte=fecha_limite,
                    fecha_salida__gte=timezone.now().date()
                )
                paquetes_ids = salidas_proximas.values_list('paquete_id', flat=True).distinct()
                queryset = queryset.filter(id__in=paquetes_ids)
            except (ValueError, TypeError):
                pass
        
        # ===== FILTRO: SOLO CON CUPOS DISPONIBLES =====
        tiene_cupos_disponibles = request.query_params.get('tiene_cupos_disponibles')
        if tiene_cupos_disponibles is not None:
            queryset = filtrar_paquetes_por_cupos(queryset, tiene_cupos_disponibles)
        
        # ===== CALCULAR RESUMEN =====
        total = queryset.count()
        activos = queryset.filter(activo=True).count()
        inactivos = queryset.filter(activo=False).count()
        personalizados = queryset.filter(personalizado=True).count()
        
        # Calcular precios (de salidas, no del paquete directamente)
        from apps.paquete.models import SalidaPaquete
        salidas = SalidaPaquete.objects.filter(
            paquete__in=queryset,
            activo=True
        )
        
        if salidas.exists():
            precio_stats = salidas.aggregate(
                promedio=Avg('precio_actual')
            )
            salida_minima = salidas.order_by('precio_actual').first()
            salida_maxima = salidas.order_by('-precio_actual').first()
            
            precio_promedio = precio_stats['promedio'] or Decimal('0')
            precio_minimo = salida_minima.precio_actual if salida_minima else Decimal('0')
            precio_maximo = salida_maxima.precio_actual if salida_maxima else Decimal('0')
            
            # Calcular promedios en ambas monedas (usando solo la próxima salida de cada paquete)
            precio_promedio_pyg = calcular_precio_promedio_pyg(queryset, es_queryset_paquetes=True)
            precio_promedio_usd = calcular_precio_promedio_usd(queryset, es_queryset_paquetes=True)
        else:
            precio_promedio = Decimal('0')
            precio_minimo = Decimal('0')
            precio_maximo = Decimal('0')
            precio_promedio_pyg = None
            precio_promedio_usd = None
        
        resumen = {
            "total_registros": total,
            "paquetes_activos": activos,
            "paquetes_inactivos": inactivos,
            "paquetes_personalizados": personalizados,
            "precio_promedio": str(precio_promedio),
            "precio_promedio_pyg": precio_promedio_pyg,
            "precio_promedio_usd": precio_promedio_usd,
            "precio_minimo": str(precio_minimo),
            "precio_maximo": str(precio_maximo)
        }
        
        # ===== SERIALIZAR =====
        serializer = PaqueteReporteSerializer(queryset[:1000], many=True)
        data = serializer.data
        
        # ===== FILTROS =====
        filtros = {
            "estado": estado,
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str
        }
        
        # ===== GENERAR PDF =====
        pdf_buffer = generar_pdf_paquetes(data, filtros, resumen)
        
        # ===== RESPUESTA =====
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"paquetes_{fecha_actual}.pdf"
        
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al exportar PDF de paquetes",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_paquetes_excel(request):
    """
    GET /api/dashboard/reportes/paquetes/exportar-excel/
    
    Exporta reporte de paquetes a Excel.
    """
    try:
        # ===== CONSTRUIR QUERY BASE =====
        queryset = Paquete.objects.all().select_related(
            'tipo_paquete',
            'destino',
            'destino__ciudad',
            'destino__ciudad__pais',
            'distribuidora',
            'moneda'
        ).prefetch_related(
            'salidas',
            'reservas',
            'paquete_servicios__servicio'
        )
        
        # ===== FILTRO POR ESTADO =====
        estado = request.query_params.get('estado', 'activo')
        if estado == 'activo':
            queryset = queryset.filter(activo=True)
        elif estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        
        # ===== FILTRO POR FECHAS DE CREACIÓN =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if fecha_desde_str:
            fecha_desde = parsear_fecha(fecha_desde_str)
            if fecha_desde:
                queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
        
        if fecha_hasta_str:
            fecha_hasta = parsear_fecha(fecha_hasta_str)
            if fecha_hasta:
                queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)
        
        # ===== FILTRO POR FECHAS DE SALIDA =====
        fecha_salida_desde_str = request.query_params.get('fecha_salida_desde')
        fecha_salida_hasta_str = request.query_params.get('fecha_salida_hasta')
        
        if fecha_salida_desde_str or fecha_salida_hasta_str:
            from apps.paquete.models import SalidaPaquete
            salidas_ids = SalidaPaquete.objects.filter(activo=True)
            
            if fecha_salida_desde_str:
                fecha = parsear_fecha(fecha_salida_desde_str)
                if fecha:
                    salidas_ids = salidas_ids.filter(fecha_salida__gte=fecha)
            
            if fecha_salida_hasta_str:
                fecha = parsear_fecha(fecha_salida_hasta_str)
                if fecha:
                    salidas_ids = salidas_ids.filter(fecha_salida__lte=fecha)
            
            paquetes_ids = salidas_ids.values_list('paquete_id', flat=True).distinct()
            queryset = queryset.filter(id__in=paquetes_ids)
        
        # ===== OTROS FILTROS =====
        destino_id = request.query_params.get('destino_id')
        if destino_id:
            queryset = queryset.filter(destino_id=destino_id)
        
        zona_geografica_id = request.query_params.get('zona_geografica_id')
        if zona_geografica_id:
            queryset = queryset.filter(destino__ciudad__pais__zona_geografica_id=zona_geografica_id)
        
        pais_id = request.query_params.get('pais_id')
        if pais_id:
            queryset = queryset.filter(destino__ciudad__pais_id=pais_id)
        
        tipo_paquete_id = request.query_params.get('tipo_paquete_id')
        if tipo_paquete_id:
            queryset = queryset.filter(tipo_paquete_id=tipo_paquete_id)
        
        personalizado = request.query_params.get('personalizado')
        if personalizado is not None:
            queryset = queryset.filter(personalizado=(personalizado.lower() == 'true'))
        
        propio = request.query_params.get('propio')
        if propio is not None:
            queryset = queryset.filter(propio=(propio.lower() == 'true'))
        
        distribuidora_id = request.query_params.get('distribuidora_id')
        if distribuidora_id:
            queryset = queryset.filter(distribuidora_id=distribuidora_id)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            # Intentar extraer el ID del código si viene en formato PAQ-2024-XXXX o PAQ-XXXX
            paquete_id = None
            busqueda_upper = busqueda.upper().strip()
            
            if busqueda_upper.startswith('PAQ'):
                # Formato: PAQ-2024-0142, PAQ-2024-142, PAQ-142
                parts = busqueda_upper.replace('PAQ-', '').replace('PAQ', '').strip('-').split('-')
                # Tomar el último número (puede ser solo uno si es PAQ-142)
                try:
                    paquete_id = int(parts[-1])
                except (ValueError, IndexError):
                    pass
            elif busqueda.isdigit():
                # Si es solo un número, usarlo como ID directamente
                paquete_id = int(busqueda)
            
            # Filtrar por ID o por nombre
            if paquete_id:
                queryset = queryset.filter(
                    Q(id=paquete_id) | Q(nombre__icontains=busqueda)
                )
            else:
                queryset = queryset.filter(nombre__icontains=busqueda)
        
        # ===== FILTRO: FECHA SALIDA PRÓXIMA =====
        fecha_salida_proxima = request.query_params.get('fecha_salida_proxima')
        if fecha_salida_proxima:
            try:
                dias = int(fecha_salida_proxima)
                from apps.paquete.models import SalidaPaquete
                fecha_limite = timezone.now().date() + timedelta(days=dias)
                salidas_proximas = SalidaPaquete.objects.filter(
                    activo=True,
                    fecha_salida__lte=fecha_limite,
                    fecha_salida__gte=timezone.now().date()
                )
                paquetes_ids = salidas_proximas.values_list('paquete_id', flat=True).distinct()
                queryset = queryset.filter(id__in=paquetes_ids)
            except (ValueError, TypeError):
                pass
        
        # ===== FILTRO: SOLO CON CUPOS DISPONIBLES =====
        tiene_cupos_disponibles = request.query_params.get('tiene_cupos_disponibles')
        if tiene_cupos_disponibles is not None:
            queryset = filtrar_paquetes_por_cupos(queryset, tiene_cupos_disponibles)
        
        # ===== CALCULAR RESUMEN =====
        total = queryset.count()
        activos = queryset.filter(activo=True).count()
        inactivos = queryset.filter(activo=False).count()
        personalizados = queryset.filter(personalizado=True).count()
        
        # Calcular precios (de salidas, no del paquete directamente)
        from apps.paquete.models import SalidaPaquete
        salidas = SalidaPaquete.objects.filter(
            paquete__in=queryset,
            activo=True
        )
        
        if salidas.exists():
            precio_stats = salidas.aggregate(
                promedio=Avg('precio_actual')
            )
            salida_minima = salidas.order_by('precio_actual').first()
            salida_maxima = salidas.order_by('-precio_actual').first()
            
            precio_promedio = precio_stats['promedio'] or Decimal('0')
            precio_minimo = salida_minima.precio_actual if salida_minima else Decimal('0')
            precio_maximo = salida_maxima.precio_actual if salida_maxima else Decimal('0')
            
            # Calcular promedios en ambas monedas (usando solo la próxima salida de cada paquete)
            precio_promedio_pyg = calcular_precio_promedio_pyg(queryset, es_queryset_paquetes=True)
            precio_promedio_usd = calcular_precio_promedio_usd(queryset, es_queryset_paquetes=True)
        else:
            precio_promedio = Decimal('0')
            precio_minimo = Decimal('0')
            precio_maximo = Decimal('0')
            precio_promedio_pyg = None
            precio_promedio_usd = None
        
        resumen = {
            "total_registros": total,
            "paquetes_activos": activos,
            "paquetes_inactivos": inactivos,
            "paquetes_personalizados": personalizados,
            "precio_promedio": str(precio_promedio),
            "precio_promedio_pyg": precio_promedio_pyg,
            "precio_promedio_usd": precio_promedio_usd,
            "precio_minimo": str(precio_minimo),
            "precio_maximo": str(precio_maximo)
        }
        
        serializer = PaqueteReporteSerializer(queryset, many=True)
        data = serializer.data
        
        filtros = {
            "estado": estado,
            "fecha_desde": request.query_params.get('fecha_desde'),
            "fecha_hasta": request.query_params.get('fecha_hasta')
        }
        
        excel_buffer = generar_excel_paquetes(data, filtros, resumen)
        
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"paquetes_{fecha_actual}.xlsx"
        
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al exportar Excel de paquetes",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# EXPORTACIÓN PDF - RESERVAS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_reservas_pdf(request):
    """
    GET /api/dashboard/reportes/reservas/exportar-pdf/
    
    Exporta reporte de reservas a PDF.
    """
    try:
        # ===== CONSTRUIR QUERY BASE =====
        queryset = Reserva.objects.filter(
            activo=True
        ).select_related(
            'titular',
            'paquete',
            'paquete__destino',
            'paquete__destino__ciudad',
            'paquete__destino__ciudad__pais',
            'paquete__moneda',
            'salida',
            'habitacion',
            'habitacion__hotel',
            'habitacion__tipo_habitacion'
        ).prefetch_related('pasajeros')
        
        # ===== FILTROS =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if fecha_desde_str:
            fecha_desde = parsear_fecha(fecha_desde_str)
            if fecha_desde:
                queryset = queryset.filter(fecha_reserva__date__gte=fecha_desde)
        
        if fecha_hasta_str:
            fecha_hasta = parsear_fecha(fecha_hasta_str)
            if fecha_hasta:
                queryset = queryset.filter(fecha_reserva__date__lte=fecha_hasta)
        
        estado = request.query_params.get('estado')
        if estado and estado != 'todas':
            queryset = queryset.filter(estado=estado)
        
        # ===== CALCULAR RESUMEN =====
        reservas_por_estado = {
            'pendiente': queryset.filter(estado='pendiente').count(),
            'confirmada': queryset.filter(estado='confirmada').count(),
            'finalizada': queryset.filter(estado='finalizada').count(),
            'cancelada': queryset.filter(estado='cancelada').count()
        }
        
        reservas_activas = queryset.exclude(estado='cancelada')
        total_pasajeros = sum(r.cantidad_pasajeros or 0 for r in reservas_activas)
        
        monto_total = Decimal('0')
        monto_pagado_total = Decimal('0')
        
        for reserva in reservas_activas:
            if reserva.precio_unitario and reserva.cantidad_pasajeros:
                monto_reserva = reserva.precio_unitario * reserva.cantidad_pasajeros
                monto_total += monto_reserva
                monto_pagado_total += (reserva.monto_pagado or Decimal('0'))
        
        saldo_pendiente = monto_total - monto_pagado_total
        
        resumen = {
            "total_registros": queryset.count(),
            "reservas_pendientes": reservas_por_estado['pendiente'],
            "reservas_confirmadas": reservas_por_estado['confirmada'],
            "reservas_finalizadas": reservas_por_estado['finalizada'],
            "reservas_canceladas": reservas_por_estado['cancelada'],
            "monto_total": str(monto_total),
            "monto_pagado": str(monto_pagado_total),
            "saldo_pendiente": str(saldo_pendiente),
            "total_pasajeros": total_pasajeros
        }
        
        # ===== SERIALIZAR =====
        serializer = ReservaReporteSerializer(queryset[:1000], many=True)
        data = serializer.data
        
        filtros = {
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "estado": estado or "todas"
        }
        
        # ===== GENERAR PDF =====
        pdf_buffer = generar_pdf_reservas(data, filtros, resumen)
        
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reservas_{fecha_actual}.pdf"
        
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al exportar PDF de reservas",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_reservas_excel(request):
    """
    GET /api/dashboard/reportes/reservas/exportar-excel/
    
    Exporta reporte de reservas a Excel.
    """
    try:
        # Reutilizar lógica del PDF
        queryset = Reserva.objects.filter(
            activo=True
        ).select_related(
            'titular',
            'paquete',
            'paquete__destino',
            'paquete__destino__ciudad',
            'paquete__destino__ciudad__pais',
            'paquete__moneda',
            'salida',
            'habitacion',
            'habitacion__hotel',
            'habitacion__tipo_habitacion'
        ).prefetch_related('pasajeros')
        
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if fecha_desde_str:
            fecha_desde = parsear_fecha(fecha_desde_str)
            if fecha_desde:
                queryset = queryset.filter(fecha_reserva__date__gte=fecha_desde)
        
        if fecha_hasta_str:
            fecha_hasta = parsear_fecha(fecha_hasta_str)
            if fecha_hasta:
                queryset = queryset.filter(fecha_reserva__date__lte=fecha_hasta)
        
        estado = request.query_params.get('estado')
        if estado and estado != 'todas':
            queryset = queryset.filter(estado=estado)
        
        # Calcular resumen
        reservas_por_estado = {
            'pendiente': queryset.filter(estado='pendiente').count(),
            'confirmada': queryset.filter(estado='confirmada').count(),
            'finalizada': queryset.filter(estado='finalizada').count(),
            'cancelada': queryset.filter(estado='cancelada').count()
        }
        
        reservas_activas = queryset.exclude(estado='cancelada')
        total_pasajeros = sum(r.cantidad_pasajeros or 0 for r in reservas_activas)
        
        monto_total = Decimal('0')
        monto_pagado_total = Decimal('0')
        
        for reserva in reservas_activas:
            if reserva.precio_unitario and reserva.cantidad_pasajeros:
                monto_reserva = reserva.precio_unitario * reserva.cantidad_pasajeros
                monto_total += monto_reserva
                monto_pagado_total += (reserva.monto_pagado or Decimal('0'))
        
        saldo_pendiente = monto_total - monto_pagado_total
        
        resumen = {
            "total_registros": queryset.count(),
            "reservas_pendientes": reservas_por_estado['pendiente'],
            "reservas_confirmadas": reservas_por_estado['confirmada'],
            "reservas_finalizadas": reservas_por_estado['finalizada'],
            "reservas_canceladas": reservas_por_estado['cancelada'],
            "monto_total": str(monto_total),
            "monto_pagado": str(monto_pagado_total),
            "saldo_pendiente": str(saldo_pendiente),
            "total_pasajeros": total_pasajeros
        }
        
        serializer = ReservaReporteSerializer(queryset, many=True)
        data = serializer.data
        
        filtros = {
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "estado": estado or "todas"
        }
        
        excel_buffer = generar_excel_reservas(data, filtros, resumen)
        
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reservas_{fecha_actual}.xlsx"
        
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al exportar Excel de reservas",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# EXPORTACIÓN CSV - MOVIMIENTOS CAJAS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exportar_movimientos_csv(request):
    """
    GET /api/dashboard/reportes/movimientos-cajas/exportar-csv/
    
    Exporta reporte de movimientos de cajas a CSV.
    Formato simple y liviano, compatible con Excel y Google Sheets.
    """
    try:
        # ===== VALIDAR FECHAS (OBLIGATORIAS) =====
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        
        if not fecha_desde_str or not fecha_hasta_str:
            return Response(
                {
                    "success": False,
                    "message": "Los parámetros fecha_desde y fecha_hasta son obligatorios"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fecha_desde = parsear_fecha(fecha_desde_str)
        fecha_hasta = parsear_fecha(fecha_hasta_str)
        
        if not fecha_desde or not fecha_hasta:
            return Response(
                {
                    "success": False,
                    "message": "Formato de fecha inválido"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ===== CONSTRUIR QUERY =====
        queryset = MovimientoCaja.objects.filter(
            activo=True,
            fecha_hora_movimiento__date__gte=fecha_desde,
            fecha_hora_movimiento__date__lte=fecha_hasta
        ).select_related(
            'apertura_caja',
            'apertura_caja__caja',
            'usuario_registro',
            'usuario_registro__persona',
            'comprobante'
        ).order_by('-fecha_hora_movimiento')
        
        # ===== APLICAR FILTROS =====
        caja_id = request.query_params.get('caja_id')
        if caja_id:
            queryset = queryset.filter(apertura_caja__caja_id=caja_id)
        
        tipo_movimiento = request.query_params.get('tipo_movimiento')
        if tipo_movimiento and tipo_movimiento != 'todas':
            queryset = queryset.filter(tipo_movimiento=tipo_movimiento)
        
        metodo_pago = request.query_params.get('metodo_pago')
        if metodo_pago:
            queryset = queryset.filter(metodo_pago=metodo_pago)
        
        concepto = request.query_params.get('concepto')
        if concepto:
            queryset = queryset.filter(concepto=concepto)
        
        busqueda = request.query_params.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(descripcion__icontains=busqueda) |
                Q(referencia__icontains=busqueda) |
                Q(numero_movimiento__icontains=busqueda)
            )
        
        # ===== VERIFICAR SI HAY DATOS =====
        total_count = queryset.count()
        print(f"[CSV DEBUG] Total de movimientos encontrados: {total_count}")
        
        # ===== CREAR CSV =====
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="movimientos_cajas_{fecha_actual}.csv"'
        
        # BOM para UTF-8 (para que Excel lo abra correctamente)
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # ===== HEADERS =====
        writer.writerow([
            'Número Movimiento',
            'Fecha/Hora',
            'Caja',
            'Número Caja',
            'Tipo Movimiento',
            'Concepto',
            'Descripción',
            'Monto',
            'Método Pago',
            'Referencia',
            'Usuario Registro',
            'Comprobante'
        ])
        
        # ===== DATOS =====
        for mov in queryset:
            # Obtener nombre de la caja
            caja_nombre = 'N/A'
            caja_numero = 'N/A'
            if mov.apertura_caja and mov.apertura_caja.caja:
                caja_nombre = mov.apertura_caja.caja.nombre
                caja_numero = mov.apertura_caja.caja.numero
            
            # Obtener nombre del usuario
            usuario_nombre = 'N/A'
            if mov.usuario_registro:
                if hasattr(mov.usuario_registro, 'persona') and mov.usuario_registro.persona:
                    usuario_nombre = f"{mov.usuario_registro.persona.nombres} {mov.usuario_registro.persona.apellidos}"
                else:
                    usuario_nombre = mov.usuario_registro.username
            
            # Obtener concepto display
            concepto_display = mov.get_concepto_display() if hasattr(mov, 'get_concepto_display') else mov.concepto
            
            # Obtener tipo display
            tipo_display = mov.get_tipo_movimiento_display() if hasattr(mov, 'get_tipo_movimiento_display') else mov.tipo_movimiento
            
            # Obtener método display
            metodo_display = mov.get_metodo_pago_display() if hasattr(mov, 'get_metodo_pago_display') else mov.metodo_pago
            
            # Comprobante
            comprobante_num = mov.comprobante.numero if mov.comprobante else 'N/A'
            
            writer.writerow([
                mov.numero_movimiento or 'N/A',
                mov.fecha_hora_movimiento.strftime('%d/%m/%Y %H:%M') if mov.fecha_hora_movimiento else 'N/A',
                caja_nombre,
                caja_numero,
                tipo_display,
                concepto_display,
                mov.descripcion or '',
                f"{mov.monto:,.2f}" if mov.monto else '0.00',
                metodo_display,
                mov.referencia or '',
                usuario_nombre,
                comprobante_num
            ])
        
        print(f"[CSV DEBUG] CSV generado exitosamente con {total_count} registros")
        return response
        
    except Exception as e:
        print(f"[CSV ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {
                "success": False,
                "message": "Error al exportar CSV",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

