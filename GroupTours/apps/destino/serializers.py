from rest_framework import serializers
from .models import Destino
from apps.hotel.serializers import HotelSerializer

class DestinoSerializer(serializers.ModelSerializer):
    hoteles = HotelSerializer(many=True, read_only=True)
    hoteles_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Destino.hoteles.field.related_model.objects.all(),
        source='hoteles'
    )

    class Meta:
        model = Destino
        fields = [
            'id',
            'nombre',
            'descripcion',
            'pais',
            'hoteles',
            'hoteles_ids',
            'activo',
            'en_uso',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']
