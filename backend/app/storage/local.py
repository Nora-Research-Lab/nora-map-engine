from __future__ import annotations

from pathlib import Path

from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Ephemeral local-disk storage. Fine for demo data, uploads-in-session,
    and derived rasters that only need to live as long as the instance does.
    """

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent path traversal outside the storage root (see security notes).
        safe_key = key.replace("..", "").lstrip("/")
        path = (self.root / safe_key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError("Invalid storage key.")
        return path

    def write(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()
