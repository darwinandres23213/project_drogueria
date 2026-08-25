from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.catalogo.presentation.views.catalogo import (
    CategoriaViewSet,
    MarcaViewSet,
    PresentacionViewSet,
    ProductoViewSet,
    ProveedorViewSet,
    UnidadMedidaViewSet,
)
from apps.catalogo.presentation.views.status import module_status

router = DefaultRouter()
router.register('categorias', CategoriaViewSet, basename='categoria')
router.register('marcas', MarcaViewSet, basename='marca')
router.register('proveedores', ProveedorViewSet, basename='proveedor')
router.register('unidades-medida', UnidadMedidaViewSet, basename='unidad-medida')
router.register('presentaciones', PresentacionViewSet, basename='presentacion')
router.register('productos', ProductoViewSet, basename='producto')

urlpatterns = [
    path('status/', module_status, name='catalogo-status'),
    path('', include(router.urls)),
]
