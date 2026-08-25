from pathlib import Path
from urllib.parse import unquote

import requests
from django.conf import settings
from django.db.models import Min, Prefetch, Q
from django.http import FileResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalogo.models import (
    Categoria,
    Marca,
    Presentacion,
    Producto,
    ProductoImagen,
    Proveedor,
    UnidadMedida,
)
from apps.catalogo.presentation.filters import (
    CategoriaFilter,
    MarcaFilter,
    PresentacionFilter,
    ProductoFilter,
    ProveedorFilter,
    UnidadMedidaFilter,
)
from apps.catalogo.presentation.serializers import (
    CategoriaSerializer,
    MarcaSerializer,
    PresentacionSerializer,
    ProductoListSerializer,
    ProductoSerializer,
    ProveedorSerializer,
    UnidadMedidaSerializer,
)
from shared.presentation.viewsets import SoftModelViewSet


class CategoriaViewSet(SoftModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    filterset_class = CategoriaFilter
    search_fields = ['nombre', 'slug']
    ordering_fields = ['nombre', 'nivel', 'created_at']
    ordering = ['nombre']


class MarcaViewSet(SoftModelViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    filterset_class = MarcaFilter
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'created_at']
    ordering = ['nombre']


class ProveedorViewSet(SoftModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    filterset_class = ProveedorFilter
    search_fields = ['nombre', 'nit', 'correo']
    ordering_fields = ['nombre', 'nit', 'created_at']
    ordering = ['nombre']


class UnidadMedidaViewSet(viewsets.ModelViewSet):
    queryset = UnidadMedida.objects.all()
    serializer_class = UnidadMedidaSerializer
    filterset_class = UnidadMedidaFilter
    search_fields = ['nombre', 'abreviatura']
    ordering_fields = ['nombre', 'abreviatura']
    ordering = ['nombre']


class PresentacionViewSet(viewsets.ModelViewSet):
    queryset = Presentacion.objects.select_related('unidad_medida').all()
    serializer_class = PresentacionSerializer
    filterset_class = PresentacionFilter
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'cantidad']
    ordering = ['nombre']


class ProductoViewSet(SoftModelViewSet):
    filterset_class = ProductoFilter
    ordering_fields = [
        'nombre',
        'sku',
        'created_at',
        'updated_at',
        'precio_actual',
        'tipo_producto',
    ]
    ordering = ['nombre']

    def get_queryset(self):
        queryset = (
            Producto.objects.select_related(
                'categoria',
                'marca',
                'proveedor',
                'presentacion',
                'presentacion__unidad_medida',
                'registro_sanitario',
            )
            .prefetch_related(
                Prefetch(
                    'imagenes',
                    queryset=ProductoImagen.objects.order_by(
                        '-es_principal',
                        'orden',
                        'created_at',
                    ),
                )
            )
            .annotate(
                precio_actual=Min(
                    'precios__precio_base',
                    filter=Q(precios__activo=True),
                )
            )
        )
        if self.action == 'list':
            queryset = queryset.filter(activo=True)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer

    @action(detail=True, methods=['get'], url_path='imagen')
    def imagen(self, request, pk=None):
        """
        Sirve la imagen del producto (archivo local en disco o, si falta, OneDrive).
        """
        producto = self.get_object()
        imagen = (
            producto.imagenes.filter(es_principal=True).first()
            or producto.imagenes.order_by('orden', 'created_at').first()
        )
        if imagen is None:
            return Response({'detail': 'Sin imagen'}, status=status.HTTP_404_NOT_FOUND)

        url = (imagen.url_imagen or '').strip()
        if not url or url.startswith('file:'):
            return Response({'detail': 'URL inválida'}, status=status.HTTP_404_NOT_FOUND)

        local_path = _resolve_local_image_file(url)
        if local_path is not None:
            response = FileResponse(
                local_path.open('rb'),
                content_type=_guess_content_type(local_path.name),
            )
            response['Cache-Control'] = 'public, max-age=86400'
            return response

        # Remoto: primero con sesión OneDrive (FedAuth), luego HTTP plano
        content = _fetch_onedrive_bytes_for_product(producto)
        if content:
            response = HttpResponse(content, content_type='image/jpeg')
            response['Cache-Control'] = 'public, max-age=3600'
            return response

        try:
            remote = requests.get(
                url,
                timeout=45,
                allow_redirects=True,
                headers={
                    'User-Agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/124.0.0.0 Safari/537.36'
                    ),
                    'Accept': 'image/*,*/*',
                },
            )
        except requests.RequestException:
            return Response(
                {'detail': 'No se pudo obtener la imagen remota'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if remote.status_code >= 400 or not remote.content:
            return Response(
                {'detail': 'Imagen remota no disponible'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        content_type = remote.headers.get('Content-Type', 'image/jpeg')
        if 'text/html' in content_type:
            return Response(
                {'detail': 'OneDrive devolvió HTML en lugar de imagen'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = HttpResponse(remote.content, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=3600'
        return response


def _fetch_onedrive_bytes_for_product(producto) -> bytes | None:
    """Descarga bytes de OneDrive usando el link compartido + ruta del match."""
    from django.conf import settings as dj_settings

    from apps.integraciones.infrastructure.models import ImagenMatchPendiente
    from apps.integraciones.infrastructure.external.onedrive.share_client import (
        OneDriveShareLinkClient,
    )

    share = (dj_settings.ONEDRIVE or {}).get('IMAGENES_SHARE_URL') or ''
    if not share:
        return None

    match = (
        ImagenMatchPendiente.objects.filter(
            producto_id=producto.id,
            estado__in=[
                ImagenMatchPendiente.Estado.AUTO,
                ImagenMatchPendiente.Estado.ACEPTADO,
            ],
        )
        .exclude(ruta_remota='')
        .order_by('-updated_at')
        .first()
    )

    try:
        client = OneDriveShareLinkClient(share)
        client.authenticate()
        if match is not None:
            return client.download_file(match.ruta_remota).read()

        # Fallback: reutilizar sesión FedAuth contra la URL guardada
        imagen = (
            producto.imagenes.filter(es_principal=True).first()
            or producto.imagenes.order_by('orden').first()
        )
        remote_url = (imagen.url_imagen if imagen else '') or ''
        if remote_url.startswith('http'):
            resp = client._session.get(remote_url, timeout=60, allow_redirects=True)
            if resp.status_code < 400 and resp.content and 'text/html' not in (
                resp.headers.get('Content-Type') or ''
            ):
                return resp.content
    except Exception:  # noqa: BLE001
        return None
    return None


def _resolve_local_image_file(url: str) -> Path | None:
    """Resuelve /media/imagenes-productos/... o /media/... a un archivo en disco."""
    public_prefix = (getattr(settings, 'IMAGENES_PUBLIC_URL', '/media/imagenes-productos/') or '').rstrip('/') + '/'
    if url.startswith(public_prefix):
        root = Path((getattr(settings, 'ONEDRIVE', {}) or {}).get('IMAGENES_LOCAL_PATH') or '')
        if not root:
            return None
        relative = unquote(url[len(public_prefix) :])
        try:
            path = (root / relative).resolve()
            root_resolved = root.resolve()
        except OSError:
            return None
        if root_resolved not in path.parents and path != root_resolved:
            return None
        if path.is_file():
            return path
        return None

    if url.startswith('/media/') or url.startswith('media/'):
        relative = url[len('/media/') :] if url.startswith('/media/') else url[len('media/') :]
        path = Path(settings.MEDIA_ROOT) / unquote(relative)
        if path.is_file() and path.stat().st_size >= 1024:
            return path
    return None


def _guess_content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith('.png'):
        return 'image/png'
    if lower.endswith('.webp'):
        return 'image/webp'
    if lower.endswith('.gif'):
        return 'image/gif'
    return 'image/jpeg'
