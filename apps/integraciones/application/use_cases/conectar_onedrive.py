"""HU-SIG-001 — Conexión con API de OneDrive (esqueleto)."""

from __future__ import annotations

from apps.integraciones.domain.repositories import StorageProvider


class ConectarOneDrive:
    def __init__(self, storage: StorageProvider):
        self._storage = storage

    def execute(self) -> dict:
        self._storage.authenticate()
        return {'status': 'authenticated'}
