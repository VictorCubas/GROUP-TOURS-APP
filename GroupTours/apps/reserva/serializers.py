from rest_framework import serializers
from .models import Reserva, Pasajero
from apps.persona.models import PersonaFisica
from apps.paquete.serializers import PaqueteSerializer


class PersonaFisicaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaFisica
        fields = ["id", "nombre", "apellido", "documento", "email", "telefono"]


class PasajeroSerializer(serializers.ModelSerializer):
    persona = PersonaFisicaSimpleSerializer(read_only=True)

    class Meta:
        model = Pasajero
        fields = [
            "id",
            "persona",
            "es_titular",
            "ticket_numero",
            "voucher_codigo",
            "fecha_registro",
        ]


class ReservaSerializer(serializers.ModelSerializer):
    titular = PersonaFisicaSimpleSerializer(read_only=True)
    pasajeros = PasajeroSerializer(many=True, read_only=True)
    paquete = PaqueteSerializer(read_only=True)

    titular_id = serializers.PrimaryKeyRelatedField(
        queryset=PersonaFisica.objects.all(),
        write_only=True,
        source="titular"
    )
    paquete_id = serializers.PrimaryKeyRelatedField(
        queryset=Reserva.objects.model.paquete.field.related_model.objects.all(),
        write_only=True,
        source="paquete"
    )

    class Meta:
        model = Reserva
        fields = [
            "id",
            "codigo",
            "observacion",
            "titular",
            "titular_id",
            "paquete",
            "paquete_id",
            "fecha_reserva",
            "cantidad_pasajeros",
            "monto_pagado",
            "estado",
            "pasajeros",
            "activo",
            "fecha_modificacion",
        ]
        read_only_fields = ["codigo", "fecha_reserva", "estado", "pasajeros"]
