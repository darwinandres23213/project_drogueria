from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.integraciones.presentation.views.status import module_status
from apps.integraciones.presentation.views.sync import (
    ImagenMatchViewSet,
    SincronizacionViewSet,
    match_preview,
    sync_catalogo,
    sync_imagenes,
)

router = DefaultRouter()
router.register('sincronizaciones', SincronizacionViewSet, basename='sincronizaciones')
router.register('matches-imagen', ImagenMatchViewSet, basename='matches-imagen')

urlpatterns = [
    path('status/', module_status, name='integraciones-status'),
    path('sync/catalogo/', sync_catalogo, name='sync-catalogo'),
    path('sync/imagenes/', sync_imagenes, name='sync-imagenes'),
    path('matches-imagen/preview/', match_preview, name='match-preview'),
    path('', include(router.urls)),
]
