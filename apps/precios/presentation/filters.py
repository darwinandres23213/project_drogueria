import django_filters

from apps.precios.models import ListaPrecio, PrecioProducto


class ListaPrecioFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    activo = django_filters.BooleanFilter()
    es_default = django_filters.BooleanFilter()

    class Meta:
        model = ListaPrecio
        fields = ['nombre', 'activo', 'es_default']


class PrecioProductoFilter(django_filters.FilterSet):
    producto = django_filters.UUIDFilter(field_name='producto_id')
    producto_sku = django_filters.CharFilter(
        field_name='producto__sku', lookup_expr='icontains'
    )
    producto_nombre = django_filters.CharFilter(
        field_name='producto__nombre', lookup_expr='icontains'
    )
    marca = django_filters.UUIDFilter(field_name='producto__marca_id')
    proveedor = django_filters.UUIDFilter(field_name='producto__proveedor_id')
    lista_precio = django_filters.UUIDFilter(field_name='lista_precio_id')
    moneda = django_filters.CharFilter(lookup_expr='iexact')
    activo = django_filters.BooleanFilter()
    precio_min = django_filters.NumberFilter(field_name='precio_base', lookup_expr='gte')
    precio_max = django_filters.NumberFilter(field_name='precio_base', lookup_expr='lte')

    class Meta:
        model = PrecioProducto
        fields = [
            'producto',
            'producto_sku',
            'producto_nombre',
            'marca',
            'proveedor',
            'lista_precio',
            'moneda',
            'activo',
            'precio_min',
            'precio_max',
        ]
