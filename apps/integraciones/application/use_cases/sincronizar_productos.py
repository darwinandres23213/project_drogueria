"""HU-SIG-002 — Sincronizar productos con OneDrive (esqueleto)."""

from __future__ import annotations

from apps.catalogo.domain.repositories import ProductoRepository
from apps.integraciones.domain.repositories import (
    ErrorIntegracionRepository,
    SincronizacionRepository,
    StorageProvider,
)


class SincronizarProductos:
    def __init__(
        self,
        storage: StorageProvider,
        productos: ProductoRepository,
        sincronizaciones: SincronizacionRepository,
        errores: ErrorIntegracionRepository,
    ):
        self._storage = storage
        self._productos = productos
        self._sincronizaciones = sincronizaciones
        self._errores = errores

    def execute(self, *, sistema_id, folder_path: str = '/') -> dict:
        # TODO: orquestar lectura remota + upsert local + registro sync/errores
        raise NotImplementedError('SincronizarProductos pendiente (HU-SIG-002)')
