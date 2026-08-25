"""Composition root mínimo para integraciones (inyección de dependencias)."""

from apps.integraciones.domain.repositories import StorageProvider
from apps.integraciones.infrastructure.external.onedrive import OneDriveClient


def get_storage_provider() -> StorageProvider:
    """Retorna el proveedor de almacenamiento configurado.

    Hoy: OneDrive. Mañana: otro adaptador sin cambiar casos de uso.
    """
    return OneDriveClient()
