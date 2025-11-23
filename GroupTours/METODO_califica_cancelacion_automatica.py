# INSTRUCCIONES: Agregar este método en GroupTours/apps/reserva/serializers.py
# Insertar DESPUÉS del método get_puede_cancelar (línea ~486)
# y ANTES del método get_info_cancelacion (línea ~488)
# EN EL SERIALIZER: ReservaSerializer (línea 293)

def get_califica_cancelacion_automatica(self, obj):
    """
    Indica si la reserva califica para cancelación automática.
    
    IMPORTANTE: Esto es diferente de puede_cancelar.
    - puede_cancelar: Permite cancelación MANUAL (disponible siempre, incluso si está pagada 100%)
    - califica_cancelacion_automatica: Indica si el SISTEMA la cancelará automáticamente
    
    Criterios para cancelación AUTOMÁTICA:
    - Días hasta salida < 15
    - NO está pagada al 100% (si pagó todo, no se auto-cancela)
    - Estado: pendiente o confirmada
    - Está activa
    - Tiene fecha de salida definida
    
    Returns:
        bool: True si califica para cancelación automática, False en caso contrario
    """
    # Validar que tenga fecha de salida
    if not obj.salida or not obj.salida.fecha_salida:
        return False
    
    # Validar que esté activa
    if not obj.activo:
        return False
    
    # Validar estado (solo pendiente o confirmada pueden auto-cancelarse)
    if obj.estado not in ['pendiente', 'confirmada']:
        return False
    
    # Obtener días hasta salida
    dias_restantes = obj.dias_hasta_salida
    if dias_restantes is None:
        return False
    
    # Verificar días (< 15 para calificar)
    if dias_restantes >= 15:
        return False
    
    # CLAVE: Verificar que NO esté pagada al 100%
    # Si ya pagó todo, no tiene sentido cancelar automáticamente
    # PERO: Siempre puede cancelarse manualmente (ver puede_cancelar)
    if obj.esta_totalmente_pagada():
        return False
    
    # Si llegó aquí, cumple todos los criterios para cancelación automática
    return True



