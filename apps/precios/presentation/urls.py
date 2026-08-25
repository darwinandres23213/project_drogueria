from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.precios.presentation.views.precios import ListaPrecioViewSet, PrecioProductoViewSet
from apps.precios.presentation.views.status import module_status

router = DefaultRouter()
router.register('listas', ListaPrecioViewSet, basename='lista-precio')
router.register('precios-producto', PrecioProductoViewSet, basename='precio-producto')

urlpatterns = [
    path('status/', module_status, name='precios-status'),
    path('', include(router.urls)),
]
