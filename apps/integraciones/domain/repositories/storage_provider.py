"""Abstracciones de almacenamiento externo (sin dependencias de infraestructura)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO, Iterable, Optional


@dataclass(frozen=True)
class StorageObject:
    """Metadatos mínimos de un archivo en un proveedor de almacenamiento."""

    path: str
    name: str
    size: Optional[int] = None
    content_type: Optional[str] = None
    etag: Optional[str] = None
    is_folder: bool = False
    web_url: Optional[str] = None


class StorageProvider(ABC):
    """
    Puerto de salida para almacenamiento remoto.

    Permite reemplazar OneDrive por Google Drive, S3, FTP, etc.
    sin alterar casos de uso de sincronización.
    """

    @abstractmethod
    def authenticate(self) -> None:
        """Establece/renueva la sesión con el proveedor."""

    @abstractmethod
    def list_files(self, folder_path: str) -> Iterable[StorageObject]:
        """Lista archivos en una carpeta remota."""

    @abstractmethod
    def download_file(self, remote_path: str) -> BinaryIO:
        """Descarga un archivo y retorna un stream binario."""

    @abstractmethod
    def upload_file(
        self,
        remote_path: str,
        content: BinaryIO,
        content_type: str | None = None,
    ) -> StorageObject:
        """Sube un archivo al proveedor."""

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Indica si existe un archivo remoto."""

    def get_item_meta(self, remote_path: str) -> StorageObject | None:
        """Metadatos de un ítem (opcional; default None)."""
        return None
