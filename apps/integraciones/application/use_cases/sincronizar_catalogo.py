"""Sincroniza catálogo Excel (OneDrive share o ruta local) → DB."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from django.core.management import call_command

from apps.integraciones.application.services.sync_helpers import (
    CLAVE_CATALOGO,
    finish_sincronizacion,
    get_recurso,
    start_sincronizacion,
    sync_paths_from_settings,
    update_recurso,
)
from apps.integraciones.domain.exceptions import (
    SincronizacionIntegracionError,
    ValidacionDatosIntegracionError,
)
from apps.integraciones.infrastructure.external.local_fs import LocalFilesystemProvider
from apps.integraciones.infrastructure.external.onedrive import OneDriveClient
from apps.integraciones.infrastructure.external.onedrive.share_client import (
    OneDriveShareLinkClient,
)
from apps.integraciones.infrastructure.models import Sincronizacion

logger = logging.getLogger(__name__)


class SincronizarCatalogo:
    """
    Detecta cambios del Excel y reimporta productos/precios.

    Fuentes (en orden):
    1. archivo_bytes / archivo_path explícitos (upload API)
    2. ONEDRIVE_CATALOGO_SHARE_URL (link compartido OneDrive — preferido)
    3. ONEDRIVE_CATALOGO_LOCAL_PATH (fallback local)
    4. Graph app (PROVIDER=onedrive + credenciales)
    """

    def execute(
        self,
        *,
        force: bool = False,
        archivo_path: str | None = None,
        archivo_bytes: bytes | None = None,
        filename: str = 'catalogo.xlsx',
    ) -> dict[str, Any]:
        sync = start_sincronizacion(Sincronizacion.Tipo.PRODUCTOS)
        tmp_path: Path | None = None
        source = ''
        try:
            paths = sync_paths_from_settings()
            source_path, etag, source = self._resolve_source(
                archivo_path=archivo_path,
                archivo_bytes=archivo_bytes,
                filename=filename,
                paths=paths,
            )
            if source in {'upload', 'onedrive_share', 'onedrive'}:
                tmp_path = source_path

            recurso = get_recurso(CLAVE_CATALOGO)
            if not force and etag and recurso.etag and recurso.etag == etag:
                finish_sincronizacion(
                    sync,
                    estado=Sincronizacion.Estado.EXITOSA,
                    procesados=0,
                    exitosos=0,
                )
                return {
                    'sincronizacion_id': str(sync.id),
                    'skipped': True,
                    'reason': 'sin_cambios',
                    'etag': etag,
                    'source': source,
                }

            call_command('import_siigo_catalogo', str(source_path))
            update_recurso(
                CLAVE_CATALOGO,
                etag=etag or '',
                metadata={'source': source, 'path': str(source_path)},
            )
            finish_sincronizacion(
                sync,
                estado=Sincronizacion.Estado.EXITOSA,
                procesados=1,
                exitosos=1,
            )
            return {
                'sincronizacion_id': str(sync.id),
                'skipped': False,
                'etag': etag,
                'source': source,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception('Error sincronizando catálogo')
            finish_sincronizacion(
                sync,
                estado=Sincronizacion.Estado.ERROR,
                errores=1,
            )
            raise SincronizacionIntegracionError(
                str(exc),
                payload={'sincronizacion_id': str(sync.id)},
            ) from exc
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def _resolve_source(
        self,
        *,
        archivo_path: str | None,
        archivo_bytes: bytes | None,
        filename: str,
        paths: dict[str, str],
    ) -> tuple[Path, str, str]:
        if archivo_bytes is not None:
            suffix = Path(filename).suffix or '.xlsx'
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            handle.write(archivo_bytes)
            handle.close()
            path = Path(handle.name)
            etag = str(hash(archivo_bytes))
            return path, etag, 'upload'

        if archivo_path:
            path = Path(archivo_path)
            if not path.exists():
                raise ValidacionDatosIntegracionError(f'No existe: {path}')
            provider = LocalFilesystemProvider(path.parent)
            meta = provider.get_item_meta(path.name)
            return path, (meta.etag if meta else ''), 'path'

        # Preferir link compartido OneDrive del Excel
        share = paths.get('catalogo_share') or ''
        if share:
            return self._download_from_share_link(share)

        local = paths.get('catalogo_local') or ''
        if local:
            path = Path(local)
            if not path.exists():
                raise ValidacionDatosIntegracionError(
                    f'ONEDRIVE_CATALOGO_LOCAL_PATH no existe: {path}'
                )
            provider = LocalFilesystemProvider(path.parent)
            meta = provider.get_item_meta(path.name)
            return path, (meta.etag if meta else ''), 'local'

        provider_name = (paths.get('provider') or 'local').lower()
        if provider_name == 'onedrive':
            return self._download_from_onedrive(paths)

        raise ValidacionDatosIntegracionError(
            'Define ONEDRIVE_CATALOGO_SHARE_URL, ONEDRIVE_CATALOGO_LOCAL_PATH, '
            'sube un archivo, o PROVIDER=onedrive con credenciales Graph.'
        )

    def _download_from_share_link(self, share_url: str) -> tuple[Path, str, str]:
        client = OneDriveShareLinkClient(share_url)
        client.authenticate()
        meta = client.get_item_meta('')
        if meta is None:
            raise ValidacionDatosIntegracionError(
                'No se pudo leer metadatos del Excel en OneDrive'
            )
        if meta.is_folder:
            raise ValidacionDatosIntegracionError(
                'ONEDRIVE_CATALOGO_SHARE_URL apunta a una carpeta; '
                'debe ser el link del archivo .xlsx'
            )

        stream = client.download_file('')
        content = stream.read()
        if not content or content[:2] != b'PK':
            raise ValidacionDatosIntegracionError(
                'La descarga de OneDrive no parece un Excel (.xlsx)'
            )

        remote_name = meta.name or 'catalogo.xlsx'
        suffix = Path(remote_name).suffix or '.xlsx'
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        handle.write(content)
        handle.close()
        logger.info(
            'Excel OneDrive descargado: %s (%s bytes, etag=%s)',
            remote_name,
            len(content),
            meta.etag,
        )
        return Path(handle.name), meta.etag or '', 'onedrive_share'

    def _download_from_onedrive(self, paths: dict[str, str]) -> tuple[Path, str, str]:
        share = paths.get('catalogo_share') or ''
        remote = paths.get('catalogo_remote') or ''
        client = OneDriveClient(share_url=share or None)
        client.authenticate()
        if not remote and share:
            meta = client.get_item_meta('')
            remote_name = meta.name if meta else 'catalogo.xlsx'
            stream = client.download_file('')
            etag = meta.etag if meta else ''
        else:
            if not remote:
                raise ValidacionDatosIntegracionError(
                    'Falta ONEDRIVE_CATALOGO_REMOTE_PATH o CATALOGO_SHARE_URL'
                )
            meta = client.get_item_meta(remote)
            remote_name = Path(remote).name
            stream = client.download_file(remote)
            etag = meta.etag if meta else ''

        suffix = Path(remote_name).suffix or '.xlsx'
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        handle.write(stream.read())
        handle.close()
        return Path(handle.name), etag or '', 'onedrive'
