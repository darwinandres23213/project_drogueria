import re

import django_filters
from django.db.models import Q
from django.db.models.functions import Length

from apps.catalogo.models import Categoria, Marca, Presentacion, Producto, Proveedor, UnidadMedida


class CategoriaFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    slug = django_filters.CharFilter(lookup_expr='iexact')
    activo = django_filters.BooleanFilter()
    parent = django_filters.UUIDFilter(field_name='parent_id')
    nivel = django_filters.NumberFilter()
    con_productos = django_filters.CharFilter(method='filter_con_productos')

    class Meta:
        model = Categoria
        fields = ['nombre', 'slug', 'activo', 'parent', 'nivel', 'con_productos']

    def filter_con_productos(self, queryset, name, value):
        flag = str(value).strip().lower() in {'1', 'true', 'si', 'yes'}
        if not flag:
            return queryset
        return queryset.filter(productos__activo=True).distinct()


class MarcaFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    activo = django_filters.BooleanFilter()

    class Meta:
        model = Marca
        fields = ['nombre', 'activo']


class ProveedorFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    nit = django_filters.CharFilter(lookup_expr='icontains')
    activo = django_filters.BooleanFilter()

    class Meta:
        model = Proveedor
        fields = ['nombre', 'nit', 'activo']


class UnidadMedidaFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    abreviatura = django_filters.CharFilter(lookup_expr='iexact')
    activo = django_filters.BooleanFilter()

    class Meta:
        model = UnidadMedida
        fields = ['nombre', 'abreviatura', 'activo']


class PresentacionFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    unidad_medida = django_filters.UUIDFilter(field_name='unidad_medida_id')
    activo = django_filters.BooleanFilter()

    class Meta:
        model = Presentacion
        fields = ['nombre', 'unidad_medida', 'activo']


class ProductoFilter(django_filters.FilterSet):
    """Filtros combinables: marca + precio + nombre/código/proveedor/etc."""

    search = django_filters.CharFilter(method='filter_search')
    q = django_filters.CharFilter(method='filter_search')
    keywords = django_filters.CharFilter(method='filter_keywords')
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    sku = django_filters.CharFilter(lookup_expr='icontains')
    codigo = django_filters.CharFilter(field_name='sku', lookup_expr='icontains')
    codigo_barras = django_filters.CharFilter(lookup_expr='icontains')
    marca = django_filters.UUIDFilter(field_name='marca_id')
    marca_nombre = django_filters.CharFilter(
        field_name='marca__nombre', lookup_expr='icontains'
    )
    proveedor = django_filters.UUIDFilter(field_name='proveedor_id')
    proveedor_nombre = django_filters.CharFilter(
        field_name='proveedor__nombre', lookup_expr='icontains'
    )
    categoria = django_filters.UUIDFilter(field_name='categoria_id')
    categoria_nombre = django_filters.CharFilter(
        field_name='categoria__nombre', lookup_expr='icontains'
    )
    tipo_producto = django_filters.CharFilter(lookup_expr='iexact')
    inventariable = django_filters.BooleanFilter()
    activo = django_filters.BooleanFilter()
    con_imagen = django_filters.CharFilter(method='filter_con_imagen')
    nombre_min_len = django_filters.NumberFilter(method='filter_nombre_min_len')
    precio_min = django_filters.NumberFilter(method='filter_precio_min')
    precio_max = django_filters.NumberFilter(method='filter_precio_max')

    class Meta:
        model = Producto
        fields = [
            'search',
            'q',
            'keywords',
            'nombre',
            'sku',
            'codigo',
            'codigo_barras',
            'marca',
            'marca_nombre',
            'proveedor',
            'proveedor_nombre',
            'categoria',
            'categoria_nombre',
            'tipo_producto',
            'inventariable',
            'activo',
            'con_imagen',
            'nombre_min_len',
            'precio_min',
            'precio_max',
        ]

    def filter_search(self, queryset, name, value):
        term = (value or '').strip()
        if len(term) < 2:
            return queryset.none() if term else queryset
        return queryset.filter(
            Q(nombre__icontains=term)
            | Q(sku__icontains=term)
            | Q(codigo_barras__icontains=term)
            | Q(descripcion_corta__icontains=term)
            | Q(referencia_fabricante__icontains=term)
            | Q(categoria__nombre__icontains=term)
            | Q(marca__nombre__icontains=term)
        )

    def filter_keywords(self, queryset, name, value):
        """OR de términos (subcategorías del menú: higiene íntima, oral, etc.)."""
        terms = [
            term.strip()
            for term in re.split(r'[,|]', value or '')
            if len(term.strip()) >= 2
        ][:20]
        if not terms:
            return queryset
        query = Q()
        for term in terms:
            query |= Q(nombre__icontains=term)
        return queryset.filter(query).distinct()

    def filter_con_imagen(self, queryset, name, value):
        flag = str(value).strip().lower()
        if flag in {'1', 'true', 'si', 'yes'}:
            return queryset.filter(imagenes__isnull=False).distinct()
        if flag in {'0', 'false', 'no'}:
            return queryset.filter(imagenes__isnull=True).distinct()
        return queryset

    def filter_nombre_min_len(self, queryset, name, value):
        if value is None:
            return queryset
        # Evita códigos/basura tipo "0,3 LT" o "* 1mm" en listados de vitrina
        return queryset.annotate(_nombre_len=Length('nombre')).filter(
            _nombre_len__gte=int(value)
        )

    def filter_precio_min(self, queryset, name, value):
        return queryset.filter(
            precios__activo=True,
            precios__precio_base__gte=value,
        ).distinct()

    def filter_precio_max(self, queryset, name, value):
        return queryset.filter(
            precios__activo=True,
            precios__precio_base__lte=value,
        ).distinct()
