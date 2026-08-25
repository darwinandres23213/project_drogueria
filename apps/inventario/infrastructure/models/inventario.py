from django.conf import settings
from django.db import models
from django.db.models import F

from shared.infrastructure.models import TimeStampedModel, UUIDModel


class Sucursal(UUIDModel, TimeStampedModel):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255, blank=True, default='')
    ciudad = models.CharField(max_length=100, blank=True, default='')
    departamento = models.CharField(max_length=100, blank=True, default='')
    telefono = models.CharField(max_length=50, blank=True, default='')
    latitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'sucursales'
        verbose_name = 'sucursal'
        verbose_name_plural = 'sucursales'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class Inventario(UUIDModel):
    producto = models.ForeignKey(
        'catalogo.Producto',
        on_delete=models.CASCADE,
        related_name='inventarios',
        db_column='producto_id',
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        related_name='inventarios',
        db_column='sucursal_id',
    )
    stock_fisico = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    stock_reservado = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    stock_disponible = models.GeneratedField(
        expression=F('stock_fisico') - F('stock_reservado'),
        output_field=models.DecimalField(max_digits=16, decimal_places=3),
        db_persist=True,
    )
    ultima_sincronizacion = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventario'
        verbose_name = 'inventario'
        verbose_name_plural = 'inventarios'
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'sucursal'],
                name='uq_inventario_producto_sucursal',
            )
        ]

    def __str__(self):
        return f'{self.producto_id} @ {self.sucursal_id}'


class MovimientoInventario(UUIDModel):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida'
        VENTA = 'VENTA', 'Venta'
        AJUSTE = 'AJUSTE', 'Ajuste'
        TRASLADO = 'TRASLADO', 'Traslado'
        DEVOLUCION = 'DEVOLUCION', 'Devolución'

    producto = models.ForeignKey(
        'catalogo.Producto',
        on_delete=models.PROTECT,
        related_name='movimientos_inventario',
        db_column='producto_id',
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='movimientos_inventario',
        db_column='sucursal_id',
    )
    tipo_movimiento = models.CharField(max_length=30, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField(max_digits=16, decimal_places=3)
    stock_anterior = models.DecimalField(max_digits=16, decimal_places=3)
    stock_nuevo = models.DecimalField(max_digits=16, decimal_places=3)
    observacion = models.TextField(null=True, blank=True)
    fecha_movimiento = models.DateTimeField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        db_column='usuario_id',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimientos_inventario'
        verbose_name = 'movimiento de inventario'
        verbose_name_plural = 'movimientos de inventario'
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f'{self.tipo_movimiento} {self.cantidad} ({self.producto_id})'
