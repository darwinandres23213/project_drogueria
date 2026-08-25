from rest_framework import serializers

from apps.catalogo.models import (
    Categoria,
    Marca,
    Presentacion,
    Producto,
    ProductoImagen,
    Proveedor,
    UnidadMedida,
)


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = [
            'id',
            'parent',
            'nombre',
            'slug',
            'nivel',
            'activo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'activo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            'id',
            'nit',
            'nombre',
            'telefono',
            'correo',
            'activo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = ['id', 'nombre', 'abreviatura', 'activo']
        read_only_fields = ['id']


class PresentacionSerializer(serializers.ModelSerializer):
    unidad_medida_nombre = serializers.CharField(
        source='unidad_medida.nombre', read_only=True
    )

    class Meta:
        model = Presentacion
        fields = [
            'id',
            'unidad_medida',
            'unidad_medida_nombre',
            'nombre',
            'cantidad',
            'activo',
        ]
        read_only_fields = ['id', 'unidad_medida_nombre']


class ProductoImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoImagen
        fields = [
            'id',
            'url_imagen',
            'es_principal',
            'orden',
            'created_at',
        ]
        read_only_fields = fields


class ProductoListSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    proveedor_nombre = serializers.CharField(
        source='proveedor.nombre', read_only=True, allow_null=True
    )
    precio_actual = serializers.DecimalField(
        max_digits=16, decimal_places=2, read_only=True, allow_null=True
    )
    imagen_principal = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id',
            'sku',
            'codigo_barras',
            'nombre',
            'descripcion_corta',
            'categoria',
            'categoria_nombre',
            'marca',
            'marca_nombre',
            'proveedor',
            'proveedor_nombre',
            'tipo_producto',
            'inventariable',
            'activo',
            'precio_actual',
            'imagen_principal',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_imagen_principal(self, obj):
        imagen = next(
            (
                img
                for img in obj.imagenes.all()
                if getattr(img, 'es_principal', False)
            ),
            None,
        )
        if imagen is None:
            imagen = next(iter(obj.imagenes.all()), None)
        if imagen is None:
            return None
        return ProductoImagenSerializer(imagen).data


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    proveedor_nombre = serializers.CharField(
        source='proveedor.nombre', read_only=True, allow_null=True
    )
    presentacion_nombre = serializers.CharField(
        source='presentacion.nombre', read_only=True, allow_null=True
    )
    presentacion_cantidad = serializers.DecimalField(
        source='presentacion.cantidad',
        max_digits=16,
        decimal_places=3,
        read_only=True,
        allow_null=True,
    )
    presentacion_unidad = serializers.CharField(
        source='presentacion.unidad_medida.nombre',
        read_only=True,
        allow_null=True,
    )
    registro_sanitario_numero = serializers.CharField(
        source='registro_sanitario.numero_registro',
        read_only=True,
        allow_null=True,
    )
    registro_sanitario_tipo = serializers.CharField(
        source='registro_sanitario.tipo_registro',
        read_only=True,
        allow_null=True,
    )
    precio_actual = serializers.DecimalField(
        max_digits=16, decimal_places=2, read_only=True, allow_null=True
    )
    imagenes = ProductoImagenSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id',
            'sku',
            'codigo_barras',
            'nombre',
            'descripcion_corta',
            'descripcion_larga',
            'categoria',
            'categoria_nombre',
            'marca',
            'marca_nombre',
            'proveedor',
            'proveedor_nombre',
            'presentacion',
            'presentacion_nombre',
            'presentacion_cantidad',
            'presentacion_unidad',
            'registro_sanitario',
            'registro_sanitario_numero',
            'registro_sanitario_tipo',
            'referencia_fabricante',
            'modelo',
            'tipo_producto',
            'inventariable',
            'requiere_formula',
            'controlado',
            'activo',
            'precio_actual',
            'imagenes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'categoria_nombre',
            'marca_nombre',
            'proveedor_nombre',
            'presentacion_nombre',
            'presentacion_cantidad',
            'presentacion_unidad',
            'registro_sanitario_numero',
            'registro_sanitario_tipo',
            'precio_actual',
            'imagenes',
            'created_at',
            'updated_at',
        ]

    def validate_sku(self, value):
        qs = Producto.all_objects.filter(sku=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un producto con este SKU.')
        return value

    def validate_codigo_barras(self, value):
        if not value:
            return value
        qs = Producto.all_objects.filter(codigo_barras=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Ya existe un producto con este código de barras.'
            )
        return value
