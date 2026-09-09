"""
Storage abstraction.

Render's free tier gives the app an EPHEMERAL disk: files survive only for
the life of the running instance and are wiped on every redeploy or
spin-down/spin-up cycle. Nothing about the rest of the codebase assumes
otherwise -- every path that needs to persist something goes through this
interface, so swapping `local` for `s3` or `supabase` later is a one-file
change (implement the same interface, update `storage_backend` in .env).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def write(self, key: str, data: bytes) -> str:
        """Persist bytes under `key`, return a reference usable by `read`."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...
