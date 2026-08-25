"""Operaciones de alto nivel sobre archivos OneDrive."""

from __future__ import annotations

from typing import BinaryIO

from apps.integraciones.domain.repositories import StorageObject, StorageProvider


class OneDriveFileManager:
    """Fachada de archivos que depende del puerto StorageProvider."""

    def __init__(self, storage: StorageProvider):
        self._storage = storage

    def ensure_authenticated(self) -> None:
        self._storage.authenticate()

    def list_folder(self, folder_path: str) -> list[StorageObject]:
        return list(self._storage.list_files(folder_path))

    def download(self, remote_path: str) -> BinaryIO:
        return self._storage.download_file(remote_path)

    def upload(self, remote_path: str, content: BinaryIO, content_type: str | None = None) -> StorageObject:
        return self._storage.upload_file(remote_path, content, content_type)
