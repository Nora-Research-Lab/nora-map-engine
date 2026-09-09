"""Consistent local-cache naming for a dataset's raw bytes.

Every registered dataset (upload, URL, catalog, or derived) keeps a copy of
its source bytes here for the lifetime of the instance, so processing tools
and preview/export endpoints can re-read it without re-fetching. This is the
one place that knows the on-disk naming convention.
"""
from __future__ import annotations

from app.config import get_settings
from app.storage.local import LocalStorage


def _storage() -> LocalStorage:
    return LocalStorage(get_settings().local_storage_dir)


def _derived_storage() -> LocalStorage:
    return LocalStorage(get_settings().derived_storage_dir)


def save(dataset_id: str, suffix: str, data: bytes, derived: bool = False) -> str:
    storage = _derived_storage() if derived else _storage()
    return storage.write(f"{dataset_id}{suffix}", data)


def load(dataset_id: str, suffix: str, derived: bool = False) -> bytes:
    storage = _derived_storage() if derived else _storage()
    return storage.read(f"{dataset_id}{suffix}")


def exists(dataset_id: str, suffix: str, derived: bool = False) -> bool:
    storage = _derived_storage() if derived else _storage()
    return storage.exists(f"{dataset_id}{suffix}")
