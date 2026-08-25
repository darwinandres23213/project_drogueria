"""HU-SIG-003 — Sincronizar inventario (esqueleto)."""

from __future__ import annotations

from apps.integraciones.domain.repositories import (
    ErrorIntegracionRepository,
    SincronizacionRepository,
    StorageProvider,
)
from apps.inventario.domain.repositories import InventarioRepository


class SincronizarInventario:
    def __init__(
        self,
        storage: StorageProvider,
        inventario: InventarioRepository,
        sincronizaciones: SincronizacionRepository,
        errores: ErrorIntegracionRepository,
    ):
        self._storage = storage
        self._inventario = inventario
        self._sincronizaciones = sincronizaciones
        self._errores = errores

    def execute(self, *, sistema_id, sucursal_id=None) -> dict:
        raise NotImplementedError('SincronizarInventario pendiente (HU-SIG-003)')
