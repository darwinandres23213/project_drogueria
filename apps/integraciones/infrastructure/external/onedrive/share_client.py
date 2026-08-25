"""Cliente OneDrive por link compartido (sin Graph app / sin descargar a disco)."""

from __future__ import annotations

import base64
import re
from io import BytesIO
from typing import Any, BinaryIO, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests

from apps.integraciones.domain.exceptions import (
    ApiExternaIntegracionError,
    ConexionIntegracionError,
    ValidacionDatosIntegracionError,
)
from apps.integraciones.domain.repositories import StorageObject, StorageProvider


def normalize_share_url(share_url: str) -> str:
    """Prefiere el short link 1drv.ms embebido en redeem= si existe."""
    raw = (share_url or '').strip()
    if not raw:
        raise ValidacionDatosIntegracionError('Falta URL compartida de OneDrive')
    qs = parse_qs(urlparse(raw).query)
    redeem = qs.get('redeem', [None])[0]
    if redeem:
        pad = '=' * (-len(redeem) % 4)
        try:
            decoded = base64.b64decode(redeem + pad).decode('utf-8')
            if decoded.startswith('http'):
                return decoded
        except Exception:  # noqa: BLE001
            pass
    return raw


class OneDriveShareLinkClient(StorageProvider):
    """
    Lista archivos de una carpeta compartida abriendo el link (FedAuth)
    y usando la API consumer `_api/v2.0`. No requiere TENANT/CLIENT.
    """

    def __init__(self, share_url: str):
        self.share_url = normalize_share_url(share_url)
        self._session = requests.Session()
        self._session.headers.update(
            {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json',
            }
        )
        self.cid: str | None = None
        self.root_item_id: str | None = None
        self._path_to_id: dict[str, str] = {'': ''}
        self._id_to_meta: dict[str, dict[str, Any]] = {}

    def authenticate(self) -> None:
        try:
            landing = self._session.get(
                self.share_url,
                allow_redirects=True,
                timeout=45,
                headers={'Accept': 'text/html,application/xhtml+xml'},
            )
        except requests.RequestException as exc:
            raise ConexionIntegracionError(
                'No se pudo abrir el link de OneDrive',
                payload={'detail': str(exc)},
            ) from exc

        self.cid, self.root_item_id = self._resolve_ids_from_landing(landing)

        if not self.cid or not self.root_item_id:
            raise ApiExternaIntegracionError(
                'No se pudo resolver cid/id del link compartido. '
                'Verifica que el link tenga acceso (cualquiera con el vínculo).',
                payload={'final_url': landing.url, 'status': landing.status_code},
            )

        self._path_to_id[''] = self.root_item_id
        meta = self._get_json(self._item_url(self.root_item_id))
        self._id_to_meta[self.root_item_id] = meta

    @staticmethod
    def _is_drive_cid(value: str | None) -> bool:
        """Drive cid consumer es hex sin guiones; CID de sesión es UUID."""
        if not value:
            return False
        cleaned = value.strip()
        if '-' in cleaned:
            return False
        return bool(re.fullmatch(r'[0-9a-fA-F]{8,}', cleaned))

    def _resolve_ids_from_landing(
        self,
        landing: requests.Response,
    ) -> tuple[str | None, str | None]:
        """
        Extrae drive cid + item id desde redirect HTML.

        Carpetas (:f:) suelen usar ?cid=&id= o resid=CID!itemId.
        Excel (:x:) suele ir a Doc.aspx?sourcedoc={GUID} con /personal/{cid}/.
        """
        parsed = urlparse(landing.url)
        qs = parse_qs(parsed.query)
        body = landing.text or ''

        cid: str | None = None
        item_id: str | None = None

        # 1) Ruta personal/{cid} (Excel Doc.aspx / download.aspx)
        m_personal = re.search(r'/personal/([0-9a-fA-F]+)/', parsed.path)
        if m_personal and self._is_drive_cid(m_personal.group(1)):
            cid = m_personal.group(1)

        # 2) sourcedoc={guid} → item UniqueId
        sourcedoc = qs.get('sourcedoc', [None])[0]
        if sourcedoc:
            item_id = unquote(sourcedoc).strip('{}')

        # 3) Classic query params (carpetas / vistas antiguas)
        q_cid = qs.get('cid', [None])[0] or qs.get('CID', [None])[0]
        if self._is_drive_cid(q_cid):
            cid = cid or q_cid
        q_id = unquote(qs.get('id', [''])[0] or '') or None
        if q_id:
            item_id = item_id or q_id

        # 4) resid=CID!itemId
        resid = qs.get('resid', [None])[0]
        if resid and '!' in resid:
            cid_from_resid, _rest = resid.split('!', 1)
            if self._is_drive_cid(cid_from_resid):
                cid = cid or cid_from_resid
            item_id = item_id or resid

        # 5) Fallback HTML: download.aspx?UniqueId=...
        if not cid or not item_id:
            m_dl = re.search(
                r'/personal/([0-9a-fA-F]+)/_layouts/15/download\.aspx\?UniqueId='
                r'([0-9a-fA-F\-]{36})',
                body,
                re.I,
            )
            if m_dl:
                cid = cid or m_dl.group(1)
                item_id = item_id or m_dl.group(2)

        # 6) Fallback HTML: resid=...
        if not cid or not item_id:
            m_resid = re.search(r'resid=([0-9a-fA-F]+![^&"\'\s]+)', body, re.I)
            if m_resid:
                resid_body = unquote(m_resid.group(1))
                if '!' in resid_body:
                    cid_b, _ = resid_body.split('!', 1)
                    cid = cid or cid_b
                    item_id = item_id or resid_body

        return cid, item_id

    def list_files(self, folder_path: str) -> Iterable[StorageObject]:
        self._ensure_auth()
        item_id = self._resolve_path(folder_path)
        url = f'{self._item_url(item_id)}/children'
        items: list[StorageObject] = []
        while url:
            data = self._get_json(url)
            for raw in data.get('value', []):
                obj = self._to_object(raw, parent=folder_path)
                self._path_to_id[obj.path] = raw['id']
                self._id_to_meta[raw['id']] = raw
                items.append(obj)
            url = data.get('@odata.nextLink')
        return items

    def download_file(self, remote_path: str) -> BinaryIO:
        """Solo para casos puntuales; el sync de imágenes NO lo usa."""
        self._ensure_auth()
        meta = self._meta_for_path(remote_path)
        url = (
            meta.get('@content.downloadUrlNoAuth')
            or meta.get('@content.downloadUrl')
            or ''
        )
        if not url:
            raise ApiExternaIntegracionError(
                'El archivo no expone URL de descarga',
                payload={'path': remote_path},
            )
        try:
            response = self._session.get(url, timeout=300)
        except requests.RequestException as exc:
            raise ConexionIntegracionError(str(exc)) from exc
        if response.status_code >= 400:
            raise ApiExternaIntegracionError(
                f'Error descargando {remote_path}',
                payload={'status': response.status_code},
            )
        return BytesIO(response.content)

    def upload_file(
        self,
        remote_path: str,
        content: BinaryIO,
        content_type: Optional[str] = None,
    ) -> StorageObject:
        raise ApiExternaIntegracionError('Upload no soportado en share link (solo lectura)')

    def file_exists(self, remote_path: str) -> bool:
        self._ensure_auth()
        try:
            self._resolve_path(remote_path)
            return True
        except ApiExternaIntegracionError:
            return False

    def get_item_meta(self, remote_path: str) -> StorageObject | None:
        self._ensure_auth()
        if remote_path in {'', '.', '/'}:
            raw = self._id_to_meta.get(self.root_item_id or '') or self._get_json(
                self._item_url(self.root_item_id or '')
            )
            return self._to_object(raw, parent='')
        raw = self._meta_for_path(remote_path)
        parent = '/'.join(remote_path.strip('/').split('/')[:-1])
        return self._to_object(raw, parent=parent)

    def public_url_for(self, remote_path: str) -> str:
        """URL usable en front sin copiar el archivo al servidor."""
        meta = self._meta_for_path(remote_path)
        return (
            meta.get('@content.downloadUrlNoAuth')
            or meta.get('@content.downloadUrl')
            or meta.get('webUrl')
            or ''
        )

    def _resolve_path(self, folder_path: str) -> str:
        cleaned = (folder_path or '').strip('/').replace('\\', '/')
        if cleaned in self._path_to_id:
            return self._path_to_id[cleaned]
        # Resuelve segmento a segmento
        current_id = self.root_item_id or ''
        built = []
        for part in cleaned.split('/'):
            if not part:
                continue
            built.append(part)
            key = '/'.join(built)
            if key in self._path_to_id:
                current_id = self._path_to_id[key]
                continue
            children = self.list_files('/'.join(built[:-1]))
            match = next((c for c in children if c.name == part), None)
            if match is None:
                raise ApiExternaIntegracionError(
                    f'No existe la ruta remota: {key}',
                )
            current_id = self._path_to_id[key]
        return current_id

    def _meta_for_path(self, remote_path: str) -> dict[str, Any]:
        item_id = self._resolve_path(remote_path)
        if item_id in self._id_to_meta and (
            '@content.downloadUrlNoAuth' in self._id_to_meta[item_id]
            or 'folder' in self._id_to_meta[item_id]
            or 'file' in self._id_to_meta[item_id]
        ):
            return self._id_to_meta[item_id]
        raw = self._get_json(self._item_url(item_id))
        self._id_to_meta[item_id] = raw
        return raw

    def _item_url(self, item_id: str) -> str:
        return f'https://onedrive.live.com/_api/v2.0/drives/{self.cid}/items/{item_id}'

    def _ensure_auth(self) -> None:
        if not self.cid or not self.root_item_id:
            self.authenticate()

    def _get_json(self, url: str) -> dict[str, Any]:
        try:
            response = self._session.get(url, timeout=60)
        except requests.RequestException as exc:
            raise ConexionIntegracionError(
                'Error de red con OneDrive share API',
                payload={'detail': str(exc), 'url': url},
            ) from exc
        if response.status_code >= 400:
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = response.text[:400]
            raise ApiExternaIntegracionError(
                f'OneDrive share API {response.status_code}',
                payload={'status': response.status_code, 'body': body, 'url': url},
            )
        return response.json()

    @staticmethod
    def _to_object(raw: dict[str, Any], *, parent: str) -> StorageObject:
        name = raw.get('name') or ''
        parent_clean = (parent or '').strip('/')
        path = f'{parent_clean}/{name}'.strip('/') if name else parent_clean
        public = (
            raw.get('@content.downloadUrlNoAuth')
            or raw.get('@content.downloadUrl')
            or raw.get('webUrl')
        )
        return StorageObject(
            path=path,
            name=name,
            size=raw.get('size'),
            content_type=(raw.get('file') or {}).get('mimeType'),
            etag=raw.get('eTag') or raw.get('cTag'),
            is_folder='folder' in raw,
            web_url=public,
        )
