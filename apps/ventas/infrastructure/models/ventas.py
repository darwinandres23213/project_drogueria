from django.db import models

from shared.infrastructure.models import SoftDeleteModel, TimeStampedModel, UUIDModel


class Cliente(UUIDModel, TimeStampedModel):
    tipo_documento = models.CharField(max_length=20)
    numero_documento = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150, blank=True, default='')
    correo = models.EmailField(max_length=150, unique=True, null=True, blank=True, db_index=True)
    telefono = models.CharField(max_length=50, blank=True, default='')
    fecha_nacimiento = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'clientes'
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'
        ordering = ['nombre', 'apellido']

    def __str__(self):
        return f'{self.nombre} {self.apellido}'.strip()


class DireccionCliente(UUIDModel, SoftDeleteModel):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='direcciones',
        db_column='cliente_id',
    )
    nombre_direccion = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100, blank=True, default='')
    departamento = models.CharField(max_length=100, blank=True, default='')
    barrio = models.CharField(max_length=100, blank=True, default='')
    latitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    es_principal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'direcciones_cliente'
        verbose_name = 'dirección de cliente'
        verbose_name_plural = 'direcciones de cliente'

    def __str__(self):
        return f'{self.nombre_direccion} - {self.cliente_id}'


class Cupon(UUIDModel):
    class TipoDescuento(models.TextChoices):
        PORCENTAJE = 'PORCENTAJE', 'Porcentaje'
        VALOR_FIJO = 'VALOR_FIJO', 'Valor fijo'

    codigo = models.CharField(max_length=50, unique=True)
    tipo_descuento = models.CharField(max_length=20, choices=TipoDescuento.choices)
    valor = models.DecimalField(max_digits=16, decimal_places=2)
    min_compra = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    usos_maximos = models.PositiveIntegerField(null=True, blank=True)
    usos_actuales = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'cupones'
        verbose_name = 'cupón'
        verbose_name_plural = 'cupones'

    def __str__(self):
        return self.codigo


class Pedido(UUIDModel, TimeStampedModel):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADO = 'PAGADO', 'Pagado'
        ENVIADO = 'ENVIADO', 'Enviado'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    numero_pedido = models.CharField(max_length=30, unique=True)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='pedidos',
        db_column='cliente_id',
    )
    sucursal = models.ForeignKey(
        'inventario.Sucursal',
        on_delete=models.PROTECT,
        related_name='pedidos',
        db_column='sucursal_id',
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    valor_domicilio = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    fecha_pedido = models.DateTimeField()
    notas = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'pedidos'
        verbose_name = 'pedido'
        verbose_name_plural = 'pedidos'
        ordering = ['-fecha_pedido']
        indexes = [
            models.Index(fields=['cliente', 'fecha_pedido'], name='idx_pedido_cliente_fecha'),
        ]

    def __str__(self):
        return self.numero_pedido


class DetallePedido(UUIDModel):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='detalles',
        db_column='pedido_id',
    )
    producto = models.ForeignKey(
        'catalogo.Producto',
        on_delete=models.PROTECT,
        related_name='detalles_pedido',
        db_column='producto_id',
    )
    cantidad = models.DecimalField(max_digits=16, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=16, decimal_places=2)
    descuento = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        db_table = 'detalle_pedido'
        verbose_name = 'detalle de pedido'
        verbose_name_plural = 'detalles de pedido'

    def __str__(self):
        return f'{self.pedido_id} / {self.producto_id}'
