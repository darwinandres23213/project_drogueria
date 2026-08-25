"""Proveedor local de archivos (dev / prueba sin Graph)."""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterable, Optional
from urllib.parse import quote

from apps.integraciones.domain.repositories import StorageObject, StorageProvider


class LocalFilesystemProvider(StorageProvider):
    """Lista/descarga archivos desde una carpeta del disco."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def authenticate(self) -> None:
        if not self.root.exists():
            raise FileNotFoundError(f'No existe la carpeta local: {self.root}')

    def list_files(self, folder_path: str) -> Iterable[StorageObject]:
        self.authenticate()
        folder = self._resolve(folder_path)
        if not folder.exists() or not folder.is_dir():
            return []
        items: list[StorageObject] = []
        for child in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
            items.append(self._to_object(child))
        return items

    def download_file(self, remote_path: str) -> BinaryIO:
        path = self._resolve(remote_path)
        if not path.is_file():
            raise FileNotFoundError(remote_path)
        return BytesIO(path.read_bytes())

    def upload_file(
        self,
        remote_path: str,
        content: BinaryIO,
        content_type: Optional[str] = None,
    ) -> StorageObject:
        path = self._resolve(remote_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as handle:
            shutil.copyfileobj(content, handle)
        return self._to_object(path)

    def file_exists(self, remote_path: str) -> bool:
        return self._resolve(remote_path).exists()

    def get_item_meta(self, remote_path: str) -> StorageObject | None:
        path = self._resolve(remote_path)
        if not path.exists():
            return None
        return self._to_object(path)

    def public_url_for(self, remote_path: str) -> str:
        """URL HTTP servida por Django (mucho más rápida que OneDrive)."""
        from django.conf import settings

        prefix = getattr(settings, 'IMAGENES_PUBLIC_URL', '/media/imagenes-productos/')
        rel = (remote_path or '').replace('\\', '/').lstrip('/')
        return f"{prefix.rstrip('/')}/{quote(rel, safe='/')}"

    def _resolve(self, remote_path: str) -> Path:
        cleaned = (remote_path or '.').replace('\\', '/').lstrip('/')
        if cleaned in {'', '.', '/'}:
            return self.root
        candidate = (self.root / cleaned).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError(f'Ruta fuera del root local: {remote_path}')
        return candidate

    def _to_object(self, path: Path) -> StorageObject:
        relative = path.relative_to(self.root).as_posix() if path != self.root else ''
        etag = ''
        size = None
        if path.is_file():
            stat = path.stat()
            etag = f'{stat.st_mtime_ns}-{stat.st_size}'
            size = stat.st_size
        elif path.is_dir():
            parts = []
            for child in sorted(path.iterdir(), key=lambda p: p.name):
                try:
                    st = child.stat()
                    parts.append(f'{child.name}:{st.st_mtime_ns}:{st.st_size}')
                except OSError:
                    parts.append(child.name)
            etag = hashlib.md5('|'.join(parts).encode()).hexdigest()
        content_type = None
        if path.is_file():
            content_type = mimetypes.guess_type(path.name)[0]
        web_url = self.public_url_for(relative) if path.is_file() else None
        return StorageObject(
            path=relative,
            name=path.name if path != self.root else self.root.name,
            size=size,
            content_type=content_type,
            etag=etag,
            is_folder=path.is_dir(),
            web_url=web_url,
        )
