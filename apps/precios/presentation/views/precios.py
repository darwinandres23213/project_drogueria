from rest_framework import viewsets

from apps.precios.models import ListaPrecio, PrecioProducto
from apps.precios.presentation.filters import ListaPrecioFilter, PrecioProductoFilter
from apps.precios.presentation.serializers import (
    ListaPrecioSerializer,
    PrecioProductoSerializer,
)


class ListaPrecioViewSet(viewsets.ModelViewSet):
    queryset = ListaPrecio.objects.all()
    serializer_class = ListaPrecioSerializer
    filterset_class = ListaPrecioFilter
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'es_default']
    ordering = ['nombre']


class PrecioProductoViewSet(viewsets.ModelViewSet):
    queryset = PrecioProducto.objects.select_related(
        'producto', 'producto__marca', 'producto__proveedor', 'lista_precio'
    ).all()
    serializer_class = PrecioProductoSerializer
    filterset_class = PrecioProductoFilter
    search_fields = ['producto__nombre', 'producto__sku']
    ordering_fields = ['precio_base', 'fecha_inicio', 'created_at', 'updated_at']
    ordering = ['-fecha_inicio']
