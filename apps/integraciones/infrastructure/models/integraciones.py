from django.db import models

from shared.infrastructure.models import UUIDModel


class SistemaIntegracion(UUIDModel):
    class TipoSistema(models.TextChoices):
        POS = 'POS', 'POS'
        ERP = 'ERP', 'ERP'
        CONTABLE = 'CONTABLE', 'Contable'
        MARKETPLACE = 'MARKETPLACE', 'Marketplace'
        OTRO = 'OTRO', 'Otro'

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=30, choices=TipoSistema.choices)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'sistemas_integracion'
        verbose_name = 'sistema de integración'
        verbose_name_plural = 'sistemas de integración'

    def __str__(self):
        return f'{self.nombre} ({self.tipo})'


class IntegracionProducto(UUIDModel):
    producto = models.ForeignKey(
        'catalogo.Producto',
        on_delete=models.CASCADE,
        related_name='integraciones',
        db_column='producto_id',
    )
    sistema = models.ForeignKey(
        SistemaIntegracion,
        on_delete=models.CASCADE,
        related_name='productos_integrados',
        db_column='sistema_id',
    )
    id_externo = models.CharField(max_length=100)
    codigo_externo = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'integracion_productos'
        verbose_name = 'integración de producto'
        verbose_name_plural = 'integraciones de productos'
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'sistema'],
                name='uq_integracion_producto_sistema',
            )
        ]

    def __str__(self):
        return f'{self.producto_id} ↔ {self.sistema_id}'


class Sincronizacion(UUIDModel):
    class Tipo(models.TextChoices):
        PRODUCTOS = 'PRODUCTOS', 'Productos'
        INVENTARIO = 'INVENTARIO', 'Inventario'
        PRECIOS = 'PRECIOS', 'Precios'
        VENTAS = 'VENTAS', 'Ventas'
        COMPLETA = 'COMPLETA', 'Completa'
        IMAGENES = 'IMAGENES', 'Imágenes'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_PROCESO = 'EN_PROCESO', 'En proceso'
        EXITOSA = 'EXITOSA', 'Exitosa'
        ERROR = 'ERROR', 'Error'
        PARCIAL = 'PARCIAL', 'Parcial'

    sistema = models.ForeignKey(
        SistemaIntegracion,
        on_delete=models.CASCADE,
        related_name='sincronizaciones',
        db_column='sistema_id',
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    registros_procesados = models.PositiveIntegerField(default=0)
    registros_exitosos = models.PositiveIntegerField(default=0)
    registros_error = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'sincronizaciones'
        verbose_name = 'sincronización'
        verbose_name_plural = 'sincronizaciones'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f'{self.sistema_id} {self.tipo} ({self.estado})'


class ErrorIntegracion(UUIDModel):
    sincronizacion = models.ForeignKey(
        Sincronizacion,
        on_delete=models.CASCADE,
        related_name='errores',
        db_column='sincronizacion_id',
    )
    tipo_error = models.CharField(max_length=50)
    mensaje = models.TextField()
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'errores_integracion'
        verbose_name = 'error de integración'
        verbose_name_plural = 'errores de integración'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.tipo_error}: {self.mensaje[:50]}'


class VentaExterna(UUIDModel):
    class EstadoEnvio(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ENVIADO = 'ENVIADO', 'Enviado'
        ERROR = 'ERROR', 'Error'

    pedido = models.ForeignKey(
        'ventas.Pedido',
        on_delete=models.CASCADE,
        related_name='ventas_externas',
        db_column='pedido_id',
    )
    sistema = models.ForeignKey(
        SistemaIntegracion,
        on_delete=models.CASCADE,
        related_name='ventas_externas',
        db_column='sistema_id',
    )
    estado_envio = models.CharField(
        max_length=20, choices=EstadoEnvio.choices, default=EstadoEnvio.PENDIENTE
    )
    documento_externo = models.CharField(max_length=100, null=True, blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    intentos = models.PositiveIntegerField(default=0)
    ultimo_error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'ventas_externas'
        verbose_name = 'venta externa'
        verbose_name_plural = 'ventas externas'
        constraints = [
            models.UniqueConstraint(
                fields=['pedido', 'sistema'],
                name='uq_venta_externa_pedido_sistema',
            )
        ]

    def __str__(self):
        return f'{self.pedido_id} → {self.sistema_id} ({self.estado_envio})'


class RecursoExternoEstado(UUIDModel):
    """Estado de un recurso externo (Excel / carpeta imágenes) para detectar cambios."""

    clave = models.CharField(max_length=100, unique=True)
    etag = models.CharField(max_length=255, blank=True, default='')
    last_modified = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recursos_externos_estado'
        verbose_name = 'estado de recurso externo'
        verbose_name_plural = 'estados de recursos externos'

    def __str__(self):
        return self.clave


class ImagenMatchPendiente(UUIDModel):
    """Cola de match imagen ↔ producto (auto o revisión humana)."""

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ACEPTADO = 'ACEPTADO', 'Aceptado'
        RECHAZADO = 'RECHAZADO', 'Rechazado'
        AUTO = 'AUTO', 'Asignado automático'

    ruta_remota = models.CharField(max_length=500, unique=True)
    nombre_archivo = models.CharField(max_length=255)
    carpeta_marca = models.CharField(max_length=255, blank=True, default='')
    url_origen = models.TextField(blank=True, default='')
    nombre_normalizado = models.CharField(max_length=255, blank=True, default='')
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    candidatos = models.JSONField(default=list, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    producto = models.ForeignKey(
        'catalogo.Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches_imagen',
        db_column='producto_id',
    )
    producto_imagen = models.ForeignKey(
        'catalogo.ProductoImagen',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches_origen',
        db_column='producto_imagen_id',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imagen_matches_pendientes'
        verbose_name = 'match de imagen pendiente'
        verbose_name_plural = 'matches de imagen pendientes'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.nombre_archivo} ({self.estado})'
