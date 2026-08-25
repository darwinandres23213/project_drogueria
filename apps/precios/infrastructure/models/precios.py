from django.db import models

from shared.infrastructure.models import TimeStampedModel, UUIDModel


class ListaPrecio(UUIDModel):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    es_default = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'listas_precios'
        verbose_name = 'lista de precios'
        verbose_name_plural = 'listas de precios'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class PrecioProducto(UUIDModel, TimeStampedModel):
    producto = models.ForeignKey(
        'catalogo.Producto',
        on_delete=models.CASCADE,
        related_name='precios',
        db_column='producto_id',
    )
    lista_precio = models.ForeignKey(
        ListaPrecio,
        on_delete=models.CASCADE,
        related_name='precios',
        db_column='lista_precio_id',
    )
    precio_base = models.DecimalField(max_digits=16, decimal_places=2)
    moneda = models.CharField(max_length=3, default='COP')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'precios_producto'
        verbose_name = 'precio de producto'
        verbose_name_plural = 'precios de producto'
        indexes = [
            models.Index(fields=['producto', 'lista_precio'], name='idx_precio_prod_lista'),
        ]

    def __str__(self):
        return f'{self.producto_id} / {self.lista_precio_id}: {self.precio_base}'
