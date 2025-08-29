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
        total = Usuario.objects.count()
        activos = Usuario.objects.filter(activo=True).count()
        inactivos = Usuario.objects.filter(activo=False).count()
        
        ultimos_30_dias = timezone.now() - timedelta(days=30)
        nuevos = Usuario.objects.filter(fecha_creacion__gte=ultimos_30_dias).count()
        
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
