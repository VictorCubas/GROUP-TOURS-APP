from rest_framework import serializers

from apps.modulo.models import Modulo

from .models import Permiso

class ModuloSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = ['id', 'nombre']

class PermisoSerializer(serializers.ModelSerializer):
    tipo = serializers.CharField()  # Campo normal para lectura y escritura
    modulo = ModuloSimpleSerializer(read_only=True) #para la recuperacion en el listado
    modulo_id = serializers.PrimaryKeyRelatedField( #para guardar o editar
        queryset=Modulo.objects.all(),
        source='modulo',
        write_only=True
    )

    class Meta:
        model = Permiso
        fields = [
            'id', 'nombre', 'descripcion', 'tipo', 'modulo',
            'modulo_id', 'activo', 'en_uso', 'fechaCreacion'
        ]

    def to_representation(self, obj):
        """Cuando serializamos, mostrar descripción legible"""
        rep = super().to_representation(obj)
        rep['tipo'] = obj.get_tipo_display()
        return rep

    def to_internal_value(self, data):
        """
        Cuando deserializamos (input), convertir el valor a código.
        Acepta tanto código ('D') como nombre legible ('Eliminacion').
        """
        tipo_reverse_map = {v: k for k, v in Permiso.TIPO_CHOICES}

        if 'tipo' in data: 
            tipo_valor = data.get('tipo')
            if tipo_valor in tipo_reverse_map:
                data['tipo'] = tipo_reverse_map[tipo_valor]
            elif tipo_valor not in dict(Permiso.TIPO_CHOICES):
                raise serializers.ValidationError({
                    'tipo': f'Valor inválido "{tipo_valor}". Debe ser uno de códigos {list(dict(Permiso.TIPO_CHOICES).keys())} o nombres {list(tipo_reverse_map.keys())}'
                })

        return super().to_internal_value(data)