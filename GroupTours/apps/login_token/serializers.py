from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from collections import defaultdict
from django.utils import timezone
from apps.moneda.models import CotizacionMoneda, Moneda

class LoginTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)

            # 1️⃣ Obtener el nombre según el tipo de persona
            nombre_persona = None
            if self.user.empleado and self.user.empleado.persona:
                persona = self.user.empleado.persona
                if hasattr(persona, "personafisica"):
                    nombre_persona = f"{persona.personafisica.nombre} {persona.personafisica.apellido or ''}".strip()
                elif hasattr(persona, "personajuridica"):
                    nombre_persona = persona.personajuridica.razon_social

            # Si no hay nombre, usar username
            if not nombre_persona:
                nombre_persona = self.user.username

            # 2️⃣ Datos básicos del usuario
            user_info = {
                "id": self.user.id,
                "username": self.user.username,
                "nombre_persona": nombre_persona,
                "roles": list(self.user.roles.values_list("nombre", flat=True)),
                "es_admin": False,
                "permisos": []
            }

            # 3️⃣ Revisar si el usuario tiene algún rol admin
            roles_data = self.user.roles.all()
            tiene_admin = any(rol.es_admin for rol in roles_data)
            user_info["es_admin"] = tiene_admin

            # 4️⃣ Si no es admin, obtener permisos detallados
            if not tiene_admin:
                permisos_por_modulo = defaultdict(lambda: {
                    "crear": False,
                    "leer": False,
                    "modificar": False,
                    "eliminar": False,
                    "exportar": False
                })

                for rol in self.user.roles.prefetch_related("permisos__modulo").all():
                    for permiso in rol.permisos.all():
                        if permiso.tipo == "C":
                            permisos_por_modulo[permiso.modulo.nombre]["crear"] = True
                        elif permiso.tipo == "R":
                            permisos_por_modulo[permiso.modulo.nombre]["leer"] = True
                        elif permiso.tipo == "U":
                            permisos_por_modulo[permiso.modulo.nombre]["modificar"] = True
                        elif permiso.tipo == "D":
                            permisos_por_modulo[permiso.modulo.nombre]["eliminar"] = True
                        elif permiso.tipo == "E":
                            permisos_por_modulo[permiso.modulo.nombre]["exportar"] = True

                for modulo, permisos in permisos_por_modulo.items():
                    user_info["permisos"].append({
                        "modulo": modulo,
                        "permisos": permisos
                    })

            # 5️⃣ Verificar si hay cotización diaria cargada
            cotizacion_diaria_cargada = self._verificar_cotizacion_diaria()

            # 6️⃣ Agregar datos al token
            data["user"] = user_info
            data["debe_cambiar_contrasenia"] = self.user.debe_cambiar_contrasenia
            data["cotizacion_diaria_cargada"] = cotizacion_diaria_cargada

            return data

        except AuthenticationFailed:
            raise AuthenticationFailed({'message': 'Credenciales incorrectas'})

    def _verificar_cotizacion_diaria(self):
        """
        Verifica si existe al menos una cotización registrada para la fecha actual.
        Retorna True si existe cotización del día, False en caso contrario.
        """
        import pytz
        # Obtener la fecha actual en la zona horaria de Paraguay (America/Asuncion)
        tz_asuncion = pytz.timezone('America/Asuncion')
        fecha_hoy = timezone.now().astimezone(tz_asuncion).date()

        # Verificar si existe al menos una cotización para hoy
        existe_cotizacion = CotizacionMoneda.objects.filter(
            fecha_vigencia=fecha_hoy
        ).exists()

        return existe_cotizacion
