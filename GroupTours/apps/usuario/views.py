# apps/usuario/views.py
from rest_framework import viewsets
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from .models import Usuario
from .serializers import UsuarioListadoSerializer, UsuarioCreateSerializer
from .filters import UsuarioFilter
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class UsuarioPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response({
            'totalItems': self.page.paginator.count,
            'pageSize': self.get_page_size(self.request),
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = (
        Usuario.objects
        .filter(is_superuser=False)  # Excluir superusuarios del listado
        .select_related('empleado', 'empleado__persona')
        .prefetch_related('roles', 'roles__permisos')
        .order_by('-fecha_creacion')
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = UsuarioFilter
    pagination_class = UsuarioPagination
    permission_classes = []

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return UsuarioListadoSerializer
        return UsuarioCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Obtener email directamente
        email_destino = getattr(instance.empleado.persona, 'email', None) if instance.empleado else None
        password_generada = getattr(instance, 'generated_password', None)

        if email_destino and password_generada:
            asunto = "Tu cuenta ha sido creada"
            mensaje = (
                f"Bienvenido,\n\n"
                f"Tu cuenta en el sistema ha sido creada exitosamente.\n"
                f"Usuario: {instance.username}\n"
                f"Contraseña temporal: {password_generada}\n\n"
                f"Por favor, inicia sesión y cambia tu contraseña."
            )

            try:
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [email_destino],
                    fail_silently=False
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")

        return Response(serializer.to_representation(instance))

    @action(detail=False, methods=['get'], url_path='resumen', pagination_class=None)
    def resumen(self, request):
        # Usar queryset base que excluye superusuarios
        base_queryset = Usuario.objects.filter(is_superuser=False)

        total = base_queryset.count()
        activos = base_queryset.filter(activo=True).count()
        inactivos = base_queryset.filter(activo=False).count()

        ultimos_30_dias = timezone.now() - timedelta(days=30)
        nuevos = base_queryset.filter(fecha_creacion__gte=ultimos_30_dias).count()

        data = [
            {'texto': 'Total', 'valor': str(total)},
            {'texto': 'Activos', 'valor': str(activos)},
            {'texto': 'Inactivos', 'valor': str(inactivos)},
            {'texto': 'Nuevos últimos 30 días', 'valor': str(nuevos)},
        ]
        return Response(data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def resetear(self, request):
        usuario = request.user
        nueva_password = request.data.get('new_password')
        if not nueva_password:
            return Response({'error': 'Nueva contraseña requerida'}, status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(nueva_password)
        usuario.debe_cambiar_contrasenia = False  # <--- Resetear flag
        usuario.save()

        return Response({'message': 'Contraseña actualizada correctamente'})

    @action(detail=False, methods=['get'], url_path='responsables', pagination_class=None)
    def responsables(self, request):
        """
        Endpoint para obtener empleados con roles específicos (cajero/admin)
        que pueden ser asignados como responsables de aperturas de caja.

        Query params:
        - roles: lista de roles separados por coma (ej: ?roles=cajero,admin)
        - activo: filtrar solo usuarios activos (default: true)
        - busqueda: término de búsqueda para filtrar por nombre, email, puesto o teléfono

        Retorna lista de empleados con formato:
        [
            {
                "empleado_id": 5,
                "nombre_completo": "Juan Pérez",
                "puesto": "Cajero",
                "email": "juan@example.com",
                "roles": ["cajero"]
            }
        ]
        """
        # Obtener parámetros
        roles_param = request.query_params.get('roles', 'cajero,admin')
        solo_activos = request.query_params.get('activo', 'true').lower() == 'true'
        busqueda = request.query_params.get('busqueda', '').strip()

        # Convertir roles a lista
        roles_buscados = [r.strip() for r in roles_param.split(',')]

        # Filtrar usuarios
        queryset = self.get_queryset()

        if solo_activos:
            queryset = queryset.filter(activo=True)

        # Filtrar por roles (case-insensitive)
        from django.db.models import Q
        q_filters = Q()
        for rol in roles_buscados:
            q_filters |= Q(roles__nombre__iexact=rol)
        queryset = queryset.filter(q_filters).distinct()

        # Solo usuarios con empleado asignado
        queryset = queryset.filter(empleado__isnull=False)

        # Filtrar por búsqueda si se proporciona
        if busqueda:
            busqueda_filters = Q()
            busqueda_filters |= Q(empleado__persona__personafisica__nombre__icontains=busqueda)
            busqueda_filters |= Q(empleado__persona__personafisica__apellido__icontains=busqueda)
            busqueda_filters |= Q(empleado__persona__personajuridica__razon_social__icontains=busqueda)
            busqueda_filters |= Q(empleado__persona__email__icontains=busqueda)
            busqueda_filters |= Q(empleado__persona__telefono__icontains=busqueda)
            busqueda_filters |= Q(empleado__puesto__nombre__icontains=busqueda)
            busqueda_filters |= Q(username__icontains=busqueda)
            queryset = queryset.filter(busqueda_filters).distinct()

        # Construir respuesta
        resultado = []
        for usuario in queryset:
            if usuario.empleado and usuario.empleado.persona:
                persona = usuario.empleado.persona

                # Obtener nombre completo
                if hasattr(persona, 'personafisica'):
                    nombre_completo = f"{persona.personafisica.nombre} {persona.personafisica.apellido}".strip()
                elif hasattr(persona, 'personajuridica'):
                    nombre_completo = persona.personajuridica.razon_social
                else:
                    nombre_completo = usuario.username

                resultado.append({
                    'empleado_id': usuario.empleado.id,
                    'usuario_id': usuario.id,
                    'nombre_completo': nombre_completo,
                    'puesto': usuario.empleado.puesto.nombre if usuario.empleado.puesto else None,
                    'email': persona.email if hasattr(persona, 'email') else None,
                    'telefono': persona.telefono if hasattr(persona, 'telefono') else None,
                    'roles': [rol.nombre for rol in usuario.roles.all()]
                })

        return Response(resultado)
