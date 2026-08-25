from django.db import models

from shared.infrastructure.models import SoftDeleteModel, TimeStampedModel, UUIDModel


class Categoria(UUIDModel, TimeStampedModel, SoftDeleteModel):
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hijos',
        db_column='parent_id',
    )
    nombre = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)
    nivel = models.SmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categorias'
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Marca(UUIDModel, TimeStampedModel, SoftDeleteModel):
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'marcas'
        verbose_name = 'marca'
        verbose_name_plural = 'marcas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Proveedor(UUIDModel, TimeStampedModel, SoftDeleteModel):
    nit = models.CharField(max_length=30)
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=50, blank=True, default='')
    correo = models.EmailField(max_length=100, blank=True, default='')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'proveedores'
        verbose_name = 'proveedor'
        verbose_name_plural = 'proveedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class UnidadMedida(UUIDModel):
    nombre = models.CharField(max_length=100)
    abreviatura = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'unidades_medida'
        verbose_name = 'unidad de medida'
        verbose_name_plural = 'unidades de medida'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.abreviatura})'


class Presentacion(UUIDModel):
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        related_name='presentaciones',
        db_column='unidad_medida_id',
    )
    nombre = models.CharField(max_length=100)
    cantidad = models.DecimalField(max_digits=16, decimal_places=3)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'presentaciones'
        verbose_name = 'presentación'
        verbose_name_plural = 'presentaciones'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class RegistroSanitario(UUIDModel, TimeStampedModel):
    class TipoRegistro(models.TextChoices):
        INVIMA = 'INVIMA', 'INVIMA'
        ICA = 'ICA', 'ICA'
        OTRO = 'OTRO', 'Otro'

    class Estado(models.TextChoices):
        VIGENTE = 'VIGENTE', 'Vigente'
        VENCIDO = 'VENCIDO', 'Vencido'
        SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'

    tipo_registro = models.CharField(max_length=30, choices=TipoRegistro.choices)
    entidad = models.CharField(max_length=50)
    numero_registro = models.CharField(max_length=100)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.VIGENTE)

    class Meta:
        db_table = 'registros_sanitarios'
        verbose_name = 'registro sanitario'
        verbose_name_plural = 'registros sanitarios'

    def __str__(self):
        return f'{self.tipo_registro} {self.numero_registro}'


class Producto(UUIDModel, TimeStampedModel, SoftDeleteModel):
    class TipoProducto(models.TextChoices):
        MEDICAMENTO = 'MEDICAMENTO', 'Medicamento'
        OTC = 'OTC', 'OTC'
        DISPOSITIVO = 'DISPOSITIVO', 'Dispositivo'
        COSMETICO = 'COSMETICO', 'Cosmético'
        OTRO = 'OTRO', 'Otro'

    sku = models.CharField(max_length=50, unique=True, db_index=True)
    codigo_barras = models.CharField(
        max_length=50, unique=True, null=True, blank=True, db_index=True
    )
    nombre = models.CharField(max_length=255)
    descripcion_corta = models.CharField(max_length=255, null=True, blank=True)
    descripcion_larga = models.TextField(null=True, blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos',
        db_column='categoria_id',
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        related_name='productos',
        db_column='marca_id',
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        db_column='proveedor_id',
    )
    presentacion = models.ForeignKey(
        Presentacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        db_column='presentacion_id',
    )
    registro_sanitario = models.ForeignKey(
        RegistroSanitario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        db_column='registro_sanitario_id',
    )
    referencia_fabricante = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    tipo_producto = models.CharField(max_length=30, choices=TipoProducto.choices)
    inventariable = models.BooleanField(default=True)
    requiere_formula = models.BooleanField(default=False)
    controlado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'productos'
        verbose_name = 'producto'
        verbose_name_plural = 'productos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.sku} - {self.nombre}'


class ProductoImagen(UUIDModel, SoftDeleteModel):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='imagenes',
        db_column='producto_id',
    )
    url_imagen = models.TextField()
    es_principal = models.BooleanField(default=False)
    orden = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'producto_imagenes'
        verbose_name = 'imagen de producto'
        verbose_name_plural = 'imágenes de producto'
        ordering = ['orden']

    def __str__(self):
        return f'Imagen {self.orden} de {self.producto_id}'


class Atributo(UUIDModel):
    class TipoDato(models.TextChoices):
        TEXTO = 'TEXTO', 'Texto'
        NUMERO = 'NUMERO', 'Número'
        BOOLEANO = 'BOOLEANO', 'Booleano'
        FECHA = 'FECHA', 'Fecha'

    nombre = models.CharField(max_length=150)
    tipo_dato = models.CharField(max_length=20, choices=TipoDato.choices)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'atributos'
        verbose_name = 'atributo'
        verbose_name_plural = 'atributos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ProductoAtributo(UUIDModel):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='producto_atributos',
        db_column='producto_id',
    )
    atributo = models.ForeignKey(
        Atributo,
        on_delete=models.CASCADE,
        related_name='producto_atributos',
        db_column='atributo_id',
    )
    valor = models.CharField(max_length=255)

    class Meta:
        db_table = 'producto_atributos'
        verbose_name = 'atributo de producto'
        verbose_name_plural = 'atributos de producto'
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'atributo'],
                name='uq_producto_atributo',
            )
        ]

    def __str__(self):
        return f'{self.producto_id} / {self.atributo_id}: {self.valor}'


class ProductoRelacionado(UUIDModel):
    class TipoRelacion(models.TextChoices):
        CROSS_SELL = 'CROSS_SELL', 'Cross-sell'
        UPSELL = 'UPSELL', 'Upsell'
        ACCESORIO = 'ACCESORIO', 'Accesorio'
        OTRO = 'OTRO', 'Otro'

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='relaciones',
        db_column='producto_id',
    )
    producto_relacionado = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='relacionado_desde',
        db_column='producto_relacionado_id',
    )
    tipo = models.CharField(max_length=30, choices=TipoRelacion.choices)

    class Meta:
        db_table = 'productos_relacionados'
        verbose_name = 'producto relacionado'
        verbose_name_plural = 'productos relacionados'
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'producto_relacionado', 'tipo'],
                name='uq_producto_relacionado_tipo',
            )
        ]

    def __str__(self):
        return f'{self.producto_id} → {self.producto_relacionado_id} ({self.tipo})'


class ProductoEquivalente(UUIDModel):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='equivalentes',
        db_column='producto_id',
    )
    producto_equivalente = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='equivalente_desde',
        db_column='producto_equivalente_id',
    )

    class Meta:
        db_table = 'productos_equivalentes'
        verbose_name = 'producto equivalente'
        verbose_name_plural = 'productos equivalentes'
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'producto_equivalente'],
                name='uq_producto_equivalente',
            )
        ]

    def __str__(self):
        return f'{self.producto_id} ≡ {self.producto_equivalente_id}'
