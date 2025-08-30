from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from collections import defaultdict

class LoginTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)

            # 1️⃣ Datos básicos del usuario
            user_info = {
                "id": self.user.id,
                "username": self.user.username,
                "roles": list(self.user.roles.values_list("nombre", flat=True)),
                "permisos": []
            }

            # 🔹 Agregar bandera es_admin
            roles_data = self.user.roles.all()
            tiene_admin = any(rol.es_admin for rol in roles_data)
            user_info["es_admin"] = tiene_admin

            # 2️⃣ Estructura para agrupar permisos por módulo
            permisos_por_modulo = defaultdict(lambda: {
                "crear": False,
                "leer": False,
                "modificar": False,
                "eliminar": False,
                "exportar": False
            })

            # 3️⃣ Si es admin, puede tener todos los permisos sin consultar la DB uno por uno
            if tiene_admin:
                from apps.permiso.models import Permiso
                for permiso in Permiso.objects.select_related("modulo").all():
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
            else:
                # 4️⃣ Obtener todos los permisos asociados a los roles del usuario
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

            # 5️⃣ Convertir el diccionario en lista para el JSON
            for modulo, permisos in permisos_por_modulo.items():
                user_info["permisos"].append({
                    "modulo": modulo,
                    "permisos": permisos
                })

            # 6️⃣ Agregar info del usuario y flag de cambio de contraseña
            data["user"] = user_info
            data["debe_cambiar_contrasenia"] = self.user.debe_cambiar_contrasenia

            return data

        except AuthenticationFailed:
            raise AuthenticationFailed({'message': 'Credenciales incorrectas'})
