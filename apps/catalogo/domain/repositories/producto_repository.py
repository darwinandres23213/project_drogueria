from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional
from uuid import UUID


class ProductoRepository(ABC):
    """Puerto de persistencia de productos (para sync y casos de uso futuros)."""

    @abstractmethod
    def get_by_id(self, producto_id: UUID) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_by_sku(self, sku: str) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def list_activos(self) -> Iterable[Any]:
        raise NotImplementedError
