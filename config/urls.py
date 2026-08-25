from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve


def health(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('api/catalogo/', include('apps.catalogo.presentation.urls')),
    path('api/inventario/', include('apps.inventario.presentation.urls')),
    path('api/precios/', include('apps.precios.presentation.urls')),
    path('api/ventas/', include('apps.ventas.presentation.urls')),
    path('api/integraciones/', include('apps.integraciones.presentation.urls')),
]

_imagenes_root = (getattr(settings, 'ONEDRIVE', {}) or {}).get('IMAGENES_LOCAL_PATH') or ''
_imagenes_prefix = (getattr(settings, 'IMAGENES_PUBLIC_URL', '/media/imagenes-productos/') or '').strip('/')
if _imagenes_root:
    urlpatterns += [
        re_path(
            rf'^{_imagenes_prefix}/(?P<path>.*)$',
            serve,
            {'document_root': _imagenes_root},
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
