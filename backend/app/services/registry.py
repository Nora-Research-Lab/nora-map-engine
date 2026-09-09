"""
In-memory registries for datasets / layers / map workspaces.

These are process-local dictionaries -- simple, dependency-free, and enough
to make every workflow in the product actually work end-to-end today. They
are deliberately isolated behind a small repository-style interface so a
Postgres/Supabase-backed implementation can be dropped in later (see
docs/ADDING_PERSISTENCE.md) without touching any API route.

Trade-off to know about: on Render's free tier the instance can spin down
after idling and loses this state on restart, same as anything else on the
ephemeral filesystem. Workspaces are additionally mirrored to local JSON
files (app/storage/local.py) so short restarts don't lose them, but a true
multi-user deployment should wire up real persistence.
"""
from __future__ import annotations

import json
import threading
import uuid
from typing import Generic, TypeVar

from app.config import get_settings
from app.schemas.dataset import DatasetMetadata
from app.schemas.layer import Layer
from app.schemas.map import MapWorkspace
from app.storage.local import LocalStorage

T = TypeVar("T")


class _Repository(Generic[T]):
    def __init__(self):
        self._items: dict[str, T] = {}
        self._lock = threading.Lock()

    def add(self, item_id: str, item: T) -> T:
        with self._lock:
            self._items[item_id] = item
        return item

    def get(self, item_id: str) -> T | None:
        return self._items.get(item_id)

    def list(self) -> list[T]:
        return list(self._items.values())

    def update(self, item_id: str, item: T) -> T:
        with self._lock:
            self._items[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        with self._lock:
            self._items.pop(item_id, None)


datasets = _Repository[DatasetMetadata]()
layers = _Repository[Layer]()
workspaces = _Repository[MapWorkspace]()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def persist_workspace(workspace: MapWorkspace) -> None:
    settings = get_settings()
    storage = LocalStorage(settings.workspace_storage_dir)
    storage.write(f"{workspace.id}.json", workspace.model_dump_json(indent=2).encode())


def load_persisted_workspaces() -> None:
    settings = get_settings()
    from pathlib import Path

    root = Path(settings.workspace_storage_dir)
    if not root.exists():
        return
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            workspaces.add(data["id"], MapWorkspace(**data))
        except Exception:
            continue
