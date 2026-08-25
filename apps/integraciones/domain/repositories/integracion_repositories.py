from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID


class SincronizacionRepository(ABC):
    """Puerto para registrar ejecuciones de sincronización."""

    @abstractmethod
    def crear(self, *, sistema_id: UUID, tipo: str, estado: str = 'PENDIENTE') -> Any:
        raise NotImplementedError

    @abstractmethod
    def actualizar(self, sincronizacion_id: UUID, **campos: Any) -> Any:
        raise NotImplementedError


class ErrorIntegracionRepository(ABC):
    """Puerto para registrar errores de integración (HU-SIG-008)."""

    @abstractmethod
    def registrar(
        self,
        *,
        sincronizacion_id: UUID,
        tipo_error: str,
        mensaje: str,
        payload: Optional[dict] = None,
    ) -> Any:
        raise NotImplementedError
