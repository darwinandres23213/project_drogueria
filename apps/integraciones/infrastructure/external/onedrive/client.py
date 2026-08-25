"""Cliente OneDrive vía Microsoft Graph."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any, BinaryIO, Iterable, Optional
from urllib.parse import quote

import requests
from django.conf import settings

from apps.integraciones.domain.exceptions import (
    ApiExternaIntegracionError,
    AutenticacionIntegracionError,
    ConexionIntegracionError,
)
from apps.integraciones.domain.repositories import StorageObject, StorageProvider
from apps.integraciones.infrastructure.external.onedrive.authentication import (
    OneDriveAuthenticator,
)


def encode_share_url(share_url: str) -> str:
    """Codifica URL compartida al formato Graph shares (u!...)."""
    encoded = base64.urlsafe_b64encode(share_url.encode('utf-8')).decode('ascii')
    return 'u!' + encoded.rstrip('=')


class OneDriveClient(StorageProvider):
    """Adaptador de OneDrive que implementa StorageProvider."""

    GRAPH = 'https://graph.microsoft.com/v1.0'

    def __init__(
        self,
        authenticator: OneDriveAuthenticator | None = None,
        *,
        drive_id: str | None = None,
        share_url: str | None = None,
    ):
        onedrive = getattr(settings, 'ONEDRIVE', {})
        self._authenticator = authenticator or OneDriveAuthenticator()
        self._token: str | None = None
        self.drive_id = drive_id if drive_id is not None else (onedrive.get('DRIVE_ID') or '')
        self.share_url = share_url if share_url is not None else (onedrive.get('SHARE_URL') or '')
        self._share_item_id: str | None = None
        self._share_drive_id: str | None = None

    def authenticate(self) -> None:
        try:
            self._token = self._authenticator.get_access_token()
            if self.share_url and not self.drive_id:
                self._resolve_share_root()
        except AutenticacionIntegracionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConexionIntegracionError(
                'No se pudo autenticar contra OneDrive',
                payload={'detail': str(exc)},
            ) from exc

    def list_files(self, folder_path: str) -> Iterable[StorageObject]:
        self._ensure_auth()
        url = self._children_url(folder_path)
        items: list[StorageObject] = []
        while url:
            data = self._get_json(url)
            for raw in data.get('value', []):
                items.append(self._to_object(raw, parent=folder_path))
            url = data.get('@odata.nextLink')
        return items

    def download_file(self, remote_path: str) -> BinaryIO:
        self._ensure_auth()
        url = f'{self._item_url(remote_path)}:/content'
        response = self._request('GET', url, stream=True)
        return BytesIO(response.content)

    def upload_file(
        self,
        remote_path: str,
        content: BinaryIO,
        content_type: Optional[str] = None,
    ) -> StorageObject:
        self._ensure_auth()
        url = f'{self._item_url(remote_path)}:/content'
        headers = {}
        if content_type:
            headers['Content-Type'] = content_type
        response = self._request('PUT', url, data=content.read(), headers=headers)
        return self._to_object(response.json(), parent='')

    def file_exists(self, remote_path: str) -> bool:
        self._ensure_auth()
        try:
            self.get_item_meta(remote_path)
            return True
        except ApiExternaIntegracionError:
            return False

    def get_item_meta(self, remote_path: str) -> StorageObject | None:
        self._ensure_auth()
        data = self._get_json(self._item_url(remote_path))
        return self._to_object(data, parent='')

    def _resolve_share_root(self) -> None:
        share_id = encode_share_url(self.share_url)
        data = self._get_json(f'{self.GRAPH}/shares/{share_id}/driveItem')
        parent = data.get('parentReference') or {}
        self._share_drive_id = parent.get('driveId') or data.get('id')
        self._share_item_id = data.get('id')
        if parent.get('driveId'):
            self.drive_id = parent['driveId']

    def _children_url(self, folder_path: str) -> str:
        cleaned = (folder_path or '').strip('/')
        if self._share_item_id and not cleaned:
            if self.drive_id:
                return f'{self.GRAPH}/drives/{self.drive_id}/items/{self._share_item_id}/children'
            return f'{self.GRAPH}/shares/{encode_share_url(self.share_url)}/driveItem/children'
        return f'{self._item_url(cleaned)}:/children'

    def _item_url(self, remote_path: str) -> str:
        cleaned = (remote_path or '').strip('/').replace('\\', '/')
        drive = self.drive_id or self._share_drive_id
        if not drive:
            raise ApiExternaIntegracionError(
                'Falta ONEDRIVE_DRIVE_ID o ONEDRIVE_SHARE_URL para resolver rutas',
            )
        if not cleaned:
            if self._share_item_id:
                return f'{self.GRAPH}/drives/{drive}/items/{self._share_item_id}'
            return f'{self.GRAPH}/drives/{drive}/root'
        encoded = quote(cleaned)
        return f'{self.GRAPH}/drives/{drive}/root:/{encoded}'

    def _ensure_auth(self) -> None:
        if not self._token:
            self.authenticate()

    def _headers(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self._token}'}

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        try:
            response = requests.request(
                method,
                url,
                headers={**self._headers(), **kwargs.pop('headers', {})},
                timeout=120,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ConexionIntegracionError(
                'Error de red con Microsoft Graph',
                payload={'detail': str(exc), 'url': url},
            ) from exc
        if response.status_code >= 400:
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = response.text[:500]
            raise ApiExternaIntegracionError(
                f'Graph {response.status_code} en {method} {url}',
                payload={'status': response.status_code, 'body': body},
            )
        return response

    def _get_json(self, url: str) -> dict[str, Any]:
        return self._request('GET', url).json()

    @staticmethod
    def _to_object(raw: dict[str, Any], *, parent: str) -> StorageObject:
        name = raw.get('name') or ''
        parent_clean = (parent or '').strip('/')
        path = f'{parent_clean}/{name}'.strip('/') if name else parent_clean
        return StorageObject(
            path=path,
            name=name,
            size=raw.get('size'),
            content_type=(raw.get('file') or {}).get('mimeType'),
            etag=raw.get('eTag') or raw.get('cTag'),
            is_folder='folder' in raw,
            web_url=raw.get('webUrl'),
        )
