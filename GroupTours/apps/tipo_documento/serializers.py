from rest_framework import serializers
from .models import TipoDocumento

class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ['id', 'nombre', 'descripcion', 'activo', 'en_uso']
