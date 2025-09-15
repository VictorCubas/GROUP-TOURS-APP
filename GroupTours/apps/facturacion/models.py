# apps/facturacion/models.py
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

# ---------- Tipos de impuesto ----------
class TipoImpuesto(models.Model):
    nombre = models.CharField(max_length=50)  # Ej: "IVA", "IRP", "ISC"
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)  # Nuevo campo

    def __str__(self):
        return self.nombre


class SubtipoImpuesto(models.Model):
    tipo_impuesto = models.ForeignKey(TipoImpuesto, on_delete=models.CASCADE, related_name="subtipos")
    nombre = models.CharField(max_length=50)  # Ej: "IVA 10%", "IVA 5%", "IVA 0%"
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(default=True)  # Nuevo campo

    def __str__(self):
        return f"{self.tipo_impuesto.nombre} - {self.nombre}"


# ---------- Empresa (única) ----------
class Empresa(models.Model):
    # Solo una empresa en todo el sistema
    ruc = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=250, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    actividades = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True) 

    def save(self, *args, **kwargs):
        if not self.pk and Empresa.objects.exists():
            raise ValueError("Solo puede existir una empresa en el sistema")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


# ---------- Establecimiento ----------
class Establecimiento(models.Model):
    nombre = models.CharField(max_length=100, default='SIN NOMBRE')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="establecimientos")
    codigo = models.CharField(max_length=3)  # Ej: "001"
    direccion = models.CharField(max_length=250, blank=True, null=True)
    activo = models.BooleanField(default=True) 

    class Meta:
        unique_together = ("empresa", "codigo")

    def __str__(self):
        return f"{self.empresa.nombre} - Estab {self.codigo}"


# ---------- Punto de Expedición ----------
class PuntoExpedicion(models.Model):
    nombre = models.CharField(max_length=100, default='SIN NOMBRE')
    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.CASCADE, related_name="puntos_expedicion")
    codigo = models.CharField(max_length=3)  # Ej: "001"
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    activo = models.BooleanField(default=True) 

    class Meta:
        unique_together = ("establecimiento", "codigo")

    def __str__(self):
        return f"{self.establecimiento.codigo}-{self.codigo}"


# ---------- Timbrado ----------
class Timbrado(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="timbrados")
    numero = models.CharField(max_length=20)
    inicio_vigencia = models.DateField()
    fin_vigencia = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.numero} ({self.empresa.nombre})"


# ---------- Factura Electrónica (Configuración) ----------
class FacturaElectronica(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="facturas")
    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.PROTECT)
    punto_expedicion = models.ForeignKey(PuntoExpedicion, on_delete=models.PROTECT, null=True, blank=True)  
    timbrado = models.ForeignKey(Timbrado, on_delete=models.PROTECT)
    es_configuracion = models.BooleanField(default=False)
    activo = models.BooleanField(default=True) 

    tipo_impuesto = models.ForeignKey(TipoImpuesto, on_delete=models.PROTECT)
    subtipo_impuesto = models.ForeignKey(SubtipoImpuesto, on_delete=models.SET_NULL, null=True, blank=True)

    # Opcionales para configuraciones
    numero_factura = models.CharField(max_length=15, editable=False, null=True, blank=True)
    fecha_emision = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("establecimiento", "punto_expedicion", "numero_factura")

    def __str__(self):
        if self.es_configuracion:
            return f"CONFIG - {self.empresa.nombre}"
        return f"{self.numero_factura} - {self.empresa.nombre}"

    def save(self, *args, **kwargs):
        # Validar si es configuración
        if self.es_configuracion:
            # Si es configuración, no se requiere punto de expedición
            self.punto_expedicion = None
            self.numero_factura = None
            self.fecha_emision = None
        else:
            # Si es factura real, se requiere punto de expedición
            if not self.punto_expedicion:
                raise ValueError("El punto de expedición es obligatorio para facturas reales")
            if not self.numero_factura:
                self.numero_factura = self.generar_numero_factura()

        super().save(*args, **kwargs)

    def generar_numero_factura(self):
        """
        Formato: XXX-XXX-XXXXXXX
        Donde:
        - XXX = código del establecimiento
        - XXX = código del punto de expedición
        - XXXXXXX = correlativo incremental
        """
        ultimo = FacturaElectronica.objects.filter(
            establecimiento=self.establecimiento,
            punto_expedicion=self.punto_expedicion,
            es_configuracion=False
        ).aggregate(max_num=Max('numero_factura'))['max_num']

        if ultimo:
            try:
                correlativo = int(ultimo.split('-')[2]) + 1
            except:
                correlativo = 1
        else:
            correlativo = 1

        correlativo_str = str(correlativo).zfill(7)
        return f"{self.establecimiento.codigo}-{self.punto_expedicion.codigo}-{correlativo_str}"