"""Resolver matches pendientes de imagen (aceptar / rechazar)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from apps.catalogo.models import Producto
from apps.integraciones.application.services.sync_helpers import (
    link_product_image,
    mark_match_linked,
    sync_paths_from_settings,
)
from apps.integraciones.domain.exceptions import ValidacionDatosIntegracionError
from apps.integraciones.domain.repositories import StorageProvider
from apps.integraciones.infrastructure.external.local_fs import LocalFilesystemProvider
from apps.integraciones.infrastructure.external.onedrive.share_client import (
    OneDriveShareLinkClient,
)
from apps.integraciones.infrastructure.models import ImagenMatchPendiente


class ResolverMatchImagen:
    def execute(
        self,
        *,
        match_id: UUID | str,
        accion: str,
        producto_id: UUID | str | None = None,
        storage: StorageProvider | None = None,
    ) -> dict[str, Any]:
        try:
            match = ImagenMatchPendiente.objects.get(pk=match_id)
        except ImagenMatchPendiente.DoesNotExist as exc:
            raise ValidacionDatosIntegracionError('Match no encontrado') from exc

        accion = (accion or '').strip().lower()
        if accion == 'rechazar':
            match.estado = ImagenMatchPendiente.Estado.RECHAZADO
            match.producto = None
            match.save(update_fields=['estado', 'producto', 'updated_at'])
            return {'id': str(match.id), 'estado': match.estado}

        if accion != 'aceptar':
            raise ValidacionDatosIntegracionError(
                'accion debe ser aceptar o rechazar'
            )

        target_id = producto_id or (match.producto_id if match.producto_id else None)
        if not target_id and match.candidatos:
            target_id = match.candidatos[0].get('producto_id')
        if not target_id:
            raise ValidacionDatosIntegracionError(
                'Debes indicar producto_id para aceptar'
            )

        try:
            producto = Producto.objects.get(pk=target_id)
        except Producto.DoesNotExist as exc:
            raise ValidacionDatosIntegracionError('Producto no encontrado') from exc

        url = match.url_origen or ''
        if not url:
            provider = storage or self._default_provider()
            provider.authenticate()
            if hasattr(provider, 'public_url_for'):
                url = provider.public_url_for(match.ruta_remota)
            else:
                meta = provider.get_item_meta(match.ruta_remota)
                url = (meta.web_url if meta else '') or ''

        if not url:
            raise ValidacionDatosIntegracionError(
                'No hay URL remota para vincular la imagen'
            )

        imagen = link_product_image(
            producto=producto,
            url_imagen=url,
            origen_remoto=match.ruta_remota,
        )
        mark_match_linked(
            match,
            producto=producto,
            imagen=imagen,
            estado=ImagenMatchPendiente.Estado.ACEPTADO,
        )
        return {
            'id': str(match.id),
            'estado': match.estado,
            'producto_id': str(producto.id),
            'producto_imagen_id': str(imagen.id),
            'url_imagen': imagen.url_imagen,
        }

    def _default_provider(self) -> StorageProvider:
        paths = sync_paths_from_settings()
        local = paths.get('imagenes_local') or ''
        if local and Path(local).exists():
            return LocalFilesystemProvider(local)
        share = paths.get('imagenes_share') or ''
        if share:
            return OneDriveShareLinkClient(share)
        raise ValidacionDatosIntegracionError(
            'No hay ONEDRIVE_IMAGENES_LOCAL_PATH configurada'
        )
