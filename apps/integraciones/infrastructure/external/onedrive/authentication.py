"""Autenticación Microsoft Graph (client credentials)."""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

from apps.integraciones.domain.exceptions import AutenticacionIntegracionError

logger = logging.getLogger(__name__)


class OneDriveAuthenticator:
    """Obtiene tokens de acceso para OneDrive/Graph."""

    TOKEN_URL = 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'

    def __init__(
        self,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        onedrive = getattr(settings, 'ONEDRIVE', {})
        self.tenant_id = tenant_id or onedrive.get('TENANT_ID', '') or ''
        self.client_id = client_id or onedrive.get('CLIENT_ID', '') or ''
        self.client_secret = client_secret or onedrive.get('CLIENT_SECRET', '') or ''
        self._cached_token: str | None = None

    def configured(self) -> bool:
        return bool(self.tenant_id and self.client_id and self.client_secret)

    def get_access_token(self) -> str:
        if self._cached_token:
            return self._cached_token
        if not self.configured():
            raise AutenticacionIntegracionError(
                'Faltan credenciales de OneDrive en configuración '
                '(ONEDRIVE_TENANT_ID / CLIENT_ID / CLIENT_SECRET)',
            )
        url = self.TOKEN_URL.format(tenant=self.tenant_id)
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials',
        }
        try:
            response = requests.post(url, data=data, timeout=30)
        except requests.RequestException as exc:
            raise AutenticacionIntegracionError(
                'No se pudo contactar login.microsoftonline.com',
                payload={'detail': str(exc)},
            ) from exc

        payload: dict[str, Any] = {}
        try:
            payload = response.json()
        except ValueError:
            payload = {'raw': response.text[:500]}

        if response.status_code >= 400 or 'access_token' not in payload:
            raise AutenticacionIntegracionError(
                'Graph rechazó las credenciales de OneDrive',
                payload={'status': response.status_code, 'body': payload},
            )
        self._cached_token = str(payload['access_token'])
        return self._cached_token
