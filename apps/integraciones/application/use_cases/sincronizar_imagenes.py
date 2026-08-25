"""Sincroniza imágenes OneDrive/local → producto_imagenes + cola de revisión."""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from apps.catalogo.models import Marca, Producto, Proveedor
from apps.integraciones.application.services.name_matcher import (
    decide_match,
    normalize_brand_key,
)
from apps.integraciones.application.services.sync_helpers import (
    CLAVE_IMAGENES,
    candidates_payload,
    finish_sincronizacion,
    get_recurso,
    mark_match_linked,
    start_sincronizacion,
    link_product_image,
    sync_paths_from_settings,
    update_recurso,
)
from apps.integraciones.domain.exceptions import (
    SincronizacionIntegracionError,
    ValidacionDatosIntegracionError,
)
from apps.integraciones.domain.repositories import StorageObject, StorageProvider
from apps.integraciones.infrastructure.external.local_fs import LocalFilesystemProvider
from apps.integraciones.infrastructure.external.onedrive import OneDriveClient
from apps.integraciones.infrastructure.external.onedrive.share_client import (
    OneDriveShareLinkClient,
)
from apps.integraciones.infrastructure.models import (
    ImagenMatchPendiente,
    Sincronizacion,
)

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}


class SincronizarImagenes:
    def execute(
        self,
        *,
        force: bool = False,
        carpeta_local: str | None = None,
        max_folders: int | None = None,
    ) -> dict[str, Any]:
        sync = start_sincronizacion(Sincronizacion.Tipo.IMAGENES)
        stats = {
            'procesados': 0,
            'auto': 0,
            'pending': 0,
            'skip': 0,
            'errores': 0,
            'folders': 0,
            'actualizados': 0,
        }
        try:
            provider, root_meta = self._build_provider(carpeta_local)
            provider.authenticate()
            etag = root_meta.etag if root_meta else ''
            recurso = get_recurso(CLAVE_IMAGENES)
            if not force and etag and recurso.etag and recurso.etag == etag:
                finish_sincronizacion(
                    sync,
                    estado=Sincronizacion.Estado.EXITOSA,
                )
                return {
                    'sincronizacion_id': str(sync.id),
                    'skipped': True,
                    'reason': 'sin_cambios',
                    'etag': etag,
                    **stats,
                }

            brand_index = self._build_brand_index()
            folders = [
                item
                for item in provider.list_files('')
                if item.is_folder
            ]
            if max_folders is not None and max_folders > 0:
                folders = folders[:max_folders]
            stats['folders'] = len(folders)
            for folder in folders:
                self._sync_folder(
                    provider=provider,
                    folder=folder,
                    brand_index=brand_index,
                    stats=stats,
                )

            estado = (
                Sincronizacion.Estado.PARCIAL
                if stats['errores']
                else Sincronizacion.Estado.EXITOSA
            )
            update_recurso(
                CLAVE_IMAGENES,
                etag=etag or '',
                metadata={'folders': len(folders), 'source': 'share_link'},
            )
            finish_sincronizacion(
                sync,
                estado=estado,
                procesados=stats['procesados'],
                exitosos=stats['auto'] + stats['pending'],
                errores=stats['errores'],
            )
            return {
                'sincronizacion_id': str(sync.id),
                'skipped': False,
                'etag': etag,
                **stats,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception('Error sincronizando imágenes')
            finish_sincronizacion(
                sync,
                estado=Sincronizacion.Estado.ERROR,
                errores=stats['errores'] + 1,
                procesados=stats['procesados'],
            )
            raise SincronizacionIntegracionError(
                str(exc),
                payload={'sincronizacion_id': str(sync.id)},
            ) from exc

    def _build_provider(
        self, carpeta_local: str | None
    ) -> tuple[StorageProvider, StorageObject | None]:
        paths = sync_paths_from_settings()
        # Las imágenes ya están en el servidor: disco local tiene prioridad (respuesta rápida).
        local = carpeta_local or paths.get('imagenes_local') or ''
        if local and Path(local).exists():
            provider = LocalFilesystemProvider(local)
            provider.authenticate()
            return provider, provider.get_item_meta('')

        share = paths.get('imagenes_share') or ''
        if share:
            provider = OneDriveShareLinkClient(share)
            provider.authenticate()
            return provider, provider.get_item_meta('')

        if (paths.get('provider') or '').lower() == 'onedrive':
            client = OneDriveClient(share_url=share or None)
            client.authenticate()
            return client, client.get_item_meta('')

        raise ValidacionDatosIntegracionError(
            'Define ONEDRIVE_IMAGENES_LOCAL_PATH con la carpeta de imágenes en el servidor, '
            'o ONEDRIVE_IMAGENES_SHARE_URL como respaldo.'
        )

    def _item_public_url(self, provider: StorageProvider, item: StorageObject) -> str:
        if hasattr(provider, 'public_url_for'):
            url = provider.public_url_for(item.path)
            if url:
                return url
        url = (item.web_url or '').strip()
        if url.startswith('file:'):
            return ''
        return url

    def _build_brand_index(self) -> dict[str, list[tuple[str, str, str]]]:
        """
        brand_key → lista (producto_id, nombre, sku)
        Incluye productos por marca y por proveedor.
        """
        index: dict[str, list[tuple[str, str, str]]] = {}

        def add(key: str, rows: list[tuple[str, str, str]]) -> None:
            if not key:
                return
            index.setdefault(key, [])
            index[key].extend(rows)

        marcas = {m.id: m.nombre for m in Marca.objects.filter(activo=True)}
        for marca_id, nombre in marcas.items():
            rows = list(
                Producto.objects.filter(marca_id=marca_id, activo=True).values_list(
                    'id', 'nombre', 'sku'
                )
            )
            rows = [(str(i), n, s) for i, n, s in rows]
            add(normalize_brand_key(nombre), rows)

        for proveedor in Proveedor.objects.filter(activo=True):
            rows = list(
                Producto.objects.filter(
                    proveedor_id=proveedor.id, activo=True
                ).values_list('id', 'nombre', 'sku')
            )
            rows = [(str(i), n, s) for i, n, s in rows]
            add(normalize_brand_key(proveedor.nombre), rows)

        # dedupe por producto_id dentro de cada key
        for key, rows in list(index.items()):
            seen: set[str] = set()
            unique: list[tuple[str, str, str]] = []
            for row in rows:
                if row[0] in seen:
                    continue
                seen.add(row[0])
                unique.append(row)
            index[key] = unique
        return index

    def _products_for_folder(
        self,
        folder_name: str,
        brand_index: dict[str, list[tuple[str, str, str]]],
    ) -> list[tuple[str, str, str]]:
        key = normalize_brand_key(folder_name)
        if key in brand_index:
            return brand_index[key]
        # fallback: prefijos / contención
        matches: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for brand_key, rows in brand_index.items():
            if not brand_key or not key:
                continue
            if key in brand_key or brand_key in key:
                for row in rows:
                    if row[0] not in seen:
                        seen.add(row[0])
                        matches.append(row)
        if matches:
            return matches
        return []

    def _sync_folder(
        self,
        *,
        provider: StorageProvider,
        folder: StorageObject,
        brand_index: dict[str, list[tuple[str, str, str]]],
        stats: dict[str, int],
    ) -> None:
        productos = self._products_for_folder(folder.name, brand_index)
        for item in provider.list_files(folder.path):
            if item.is_folder:
                continue
            ext = Path(item.name).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            stats['procesados'] += 1
            try:
                self._process_image(
                    provider=provider,
                    item=item,
                    carpeta_marca=folder.name,
                    productos=productos,
                    stats=stats,
                )
            except Exception as exc:  # noqa: BLE001
                stats['errores'] += 1
                logger.warning('Imagen %s: %s', item.path, exc)

    def _process_image(
        self,
        *,
        provider: StorageProvider,
        item: StorageObject,
        carpeta_marca: str,
        productos: list[tuple[str, str, str]],
        stats: dict[str, int],
    ) -> None:
        url = self._item_public_url(provider, item)
        existing = ImagenMatchPendiente.objects.filter(ruta_remota=item.path).first()
        if existing and existing.estado in {
            ImagenMatchPendiente.Estado.AUTO,
            ImagenMatchPendiente.Estado.ACEPTADO,
            ImagenMatchPendiente.Estado.RECHAZADO,
        }:
            if existing.estado != ImagenMatchPendiente.Estado.RECHAZADO and url:
                self._refresh_linked_url(existing, url=url, item=item, stats=stats)
            else:
                stats['skip'] += 1
            return

        decision = decide_match(item.name, productos)
        payload = candidates_payload(decision.candidates)
        score = (
            Decimal(str(decision.best.score)) if decision.best is not None else None
        )

        if decision.action == 'skip':
            ImagenMatchPendiente.objects.update_or_create(
                ruta_remota=item.path,
                defaults={
                    'nombre_archivo': item.name,
                    'carpeta_marca': carpeta_marca,
                    'url_origen': url,
                    'nombre_normalizado': decision.nombre_normalizado,
                    'score': score,
                    'candidatos': payload,
                    'estado': ImagenMatchPendiente.Estado.PENDIENTE,
                    'producto': None,
                },
            )
            stats['pending'] += 1
            return

        if decision.action == 'pending':
            ImagenMatchPendiente.objects.update_or_create(
                ruta_remota=item.path,
                defaults={
                    'nombre_archivo': item.name,
                    'carpeta_marca': carpeta_marca,
                    'url_origen': url,
                    'nombre_normalizado': decision.nombre_normalizado,
                    'score': score,
                    'candidatos': payload,
                    'estado': ImagenMatchPendiente.Estado.PENDIENTE,
                    'producto_id': decision.best.producto_id if decision.best else None,
                },
            )
            stats['pending'] += 1
            return

        assert decision.best is not None
        producto = Producto.objects.get(pk=decision.best.producto_id)
        if not url:
            raise ValueError(f'Sin URL pública para {item.path}')
        imagen = link_product_image(
            producto=producto,
            url_imagen=url,
            origen_remoto=item.path,
        )
        match, _ = ImagenMatchPendiente.objects.update_or_create(
            ruta_remota=item.path,
            defaults={
                'nombre_archivo': item.name,
                'carpeta_marca': carpeta_marca,
                'url_origen': url,
                'nombre_normalizado': decision.nombre_normalizado,
                'score': score,
                'candidatos': payload,
                'estado': ImagenMatchPendiente.Estado.AUTO,
                'producto': producto,
                'producto_imagen': imagen,
            },
        )
        mark_match_linked(
            match,
            producto=producto,
            imagen=imagen,
            estado=ImagenMatchPendiente.Estado.AUTO,
        )
        stats['auto'] += 1

    def _refresh_linked_url(
        self,
        match: ImagenMatchPendiente,
        *,
        url: str,
        item: StorageObject,
        stats: dict[str, int],
    ) -> None:
        """Si el match ya existía (OneDrive), solo actualiza la ruta local."""
        producto = match.producto
        imagen = match.producto_imagen
        if producto is None:
            stats['skip'] += 1
            return
        if imagen is None:
            imagen = link_product_image(
                producto=producto,
                url_imagen=url,
                origen_remoto=item.path,
            )
            match.producto_imagen = imagen
        elif imagen.url_imagen != url:
            imagen.url_imagen = url
            imagen.save(update_fields=['url_imagen'])
        match.url_origen = url
        match.save(update_fields=['url_origen', 'producto_imagen', 'updated_at'])
        stats['actualizados'] += 1

