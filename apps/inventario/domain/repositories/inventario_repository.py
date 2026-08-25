from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional
from uuid import UUID


class InventarioRepository(ABC):
    """Puerto de persistencia de inventario por sucursal."""

    @abstractmethod
    def get_by_producto_sucursal(self, producto_id: UUID, sucursal_id: UUID) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def list_by_sucursal(self, sucursal_id: UUID) -> Iterable[Any]:
        raise NotImplementedError
