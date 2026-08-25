"""Helpers compartidos de sincronización OneDrive/local."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.text import slugify

from apps.catalogo.models import Producto, ProductoImagen
from apps.integraciones.infrastructure.models import (
    ImagenMatchPendiente,
    RecursoExternoEstado,
    Sincronizacion,
    SistemaIntegracion,
)


SISTEMA_NOMBRE = 'OneDrive Madherdei'
CLAVE_CATALOGO = 'catalogo_excel'
CLAVE_IMAGENES = 'imagenes_productos'


def get_or_create_sistema() -> SistemaIntegracion:
    sistema, _ = SistemaIntegracion.objects.get_or_create(
        nombre=SISTEMA_NOMBRE,
        defaults={
            'tipo': SistemaIntegracion.TipoSistema.OTRO,
            'activo': True,
        },
    )
    return sistema


def start_sincronizacion(tipo: str) -> Sincronizacion:
    return Sincronizacion.objects.create(
        sistema=get_or_create_sistema(),
        tipo=tipo,
        estado=Sincronizacion.Estado.EN_PROCESO,
        fecha_inicio=timezone.now(),
    )


def finish_sincronizacion(
    sync: Sincronizacion,
    *,
    estado: str,
    procesados: int = 0,
    exitosos: int = 0,
    errores: int = 0,
) -> Sincronizacion:
    sync.estado = estado
    sync.fecha_fin = timezone.now()
    sync.registros_procesados = procesados
    sync.registros_exitosos = exitosos
    sync.registros_error = errores
    sync.save(
        update_fields=[
            'estado',
            'fecha_fin',
            'registros_procesados',
            'registros_exitosos',
            'registros_error',
        ]
    )
    return sync


def get_recurso(clave: str) -> RecursoExternoEstado:
    recurso, _ = RecursoExternoEstado.objects.get_or_create(clave=clave)
    return recurso


def update_recurso(
    clave: str,
    *,
    etag: str = '',
    metadata: dict[str, Any] | None = None,
) -> RecursoExternoEstado:
    recurso = get_recurso(clave)
    recurso.etag = etag or recurso.etag
    recurso.last_sync_at = timezone.now()
    if metadata is not None:
        recurso.metadata = metadata
    recurso.save()
    return recurso


def store_product_image(
    *,
    producto: Producto,
    filename: str,
    content: bytes,
    origen_remoto: str,
) -> ProductoImagen:
    safe = slugify(Path(filename).stem)[:80] or 'imagen'
    ext = Path(filename).suffix.lower() or '.jpg'
    relative = f'productos/{producto.id}/{safe}{ext}'
    saved_path = default_storage.save(relative, ContentFile(content))
    url = default_storage.url(saved_path)
    return link_product_image(
        producto=producto,
        url_imagen=url,
        origen_remoto=origen_remoto,
    )


def link_product_image(
    *,
    producto: Producto,
    url_imagen: str,
    origen_remoto: str = '',
) -> ProductoImagen:
    """Vincula la imagen del producto. Si ya hay una, actualiza la URL (p. ej. OneDrive → disco)."""
    if not url_imagen:
        raise ValueError('url_imagen vacía')
    existing = producto.imagenes.filter(url_imagen=url_imagen).first()
    if existing:
        return existing
    if origen_remoto:
        stem = Path(origen_remoto).stem.casefold()
        for img in producto.imagenes.all():
            url = (img.url_imagen or '')
            if stem and stem in Path(url).stem.casefold():
                img.url_imagen = url_imagen
                img.save(update_fields=['url_imagen'])
                return img
    principal = producto.imagenes.filter(es_principal=True).first()
    if principal and (
        principal.url_imagen.startswith('http')
        or principal.url_imagen.startswith('file:')
    ):
        principal.url_imagen = url_imagen
        principal.save(update_fields=['url_imagen'])
        return principal
    es_principal = not producto.imagenes.filter(deleted_at__isnull=True).exists()
    orden = producto.imagenes.filter(deleted_at__isnull=True).count()
    return ProductoImagen.objects.create(
        producto=producto,
        url_imagen=url_imagen,
        es_principal=es_principal,
        orden=orden,
    )


def candidates_payload(candidates) -> list[dict[str, Any]]:
    return [
        {
            'producto_id': item.producto_id,
            'nombre': item.nombre,
            'sku': item.sku,
            'score': item.score,
        }
        for item in candidates
    ]


def mark_match_linked(
    match: ImagenMatchPendiente,
    *,
    producto: Producto,
    imagen: ProductoImagen,
    estado: str,
) -> ImagenMatchPendiente:
    match.producto = producto
    match.producto_imagen = imagen
    match.estado = estado
    match.save(
        update_fields=['producto', 'producto_imagen', 'estado', 'updated_at']
    )
    return match


def media_absolute_url(request, url: str) -> str:
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if request is None:
        return url
    return request.build_absolute_uri(url)


def sync_paths_from_settings() -> dict[str, str]:
    cfg = getattr(settings, 'ONEDRIVE', {})
    return {
        'catalogo_local': cfg.get('CATALOGO_LOCAL_PATH') or '',
        'imagenes_local': cfg.get('IMAGENES_LOCAL_PATH') or '',
        'catalogo_share': cfg.get('CATALOGO_SHARE_URL') or '',
        'imagenes_share': cfg.get('IMAGENES_SHARE_URL') or '',
        'catalogo_remote': cfg.get('CATALOGO_REMOTE_PATH') or '',
        'provider': cfg.get('PROVIDER') or 'local',
    }
