from rest_framework import serializers

from apps.precios.models import ListaPrecio, PrecioProducto


class ListaPrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListaPrecio
        fields = ['id', 'nombre', 'descripcion', 'es_default', 'activo']
        read_only_fields = ['id']


class PrecioProductoSerializer(serializers.ModelSerializer):
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    lista_precio_nombre = serializers.CharField(
        source='lista_precio.nombre', read_only=True
    )

    class Meta:
        model = PrecioProducto
        fields = [
            'id',
            'producto',
            'producto_sku',
            'producto_nombre',
            'lista_precio',
            'lista_precio_nombre',
            'precio_base',
            'moneda',
            'fecha_inicio',
            'fecha_fin',
            'activo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'producto_sku',
            'producto_nombre',
            'lista_precio_nombre',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs):
        fecha_inicio = attrs.get('fecha_inicio') or getattr(self.instance, 'fecha_inicio', None)
        fecha_fin = attrs.get('fecha_fin') if 'fecha_fin' in attrs else getattr(
            self.instance, 'fecha_fin', None
        )
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {'fecha_fin': 'La fecha fin no puede ser anterior a la fecha inicio.'}
            )
        precio = attrs.get('precio_base')
        if precio is not None and precio < 0:
            raise serializers.ValidationError(
                {'precio_base': 'El precio no puede ser negativo.'}
            )
        return attrs
