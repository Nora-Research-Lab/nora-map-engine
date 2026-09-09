from __future__ import annotations

from fastapi import APIRouter

from app.schemas.map import MapWorkspace, MapWorkspaceCreate
from app.services import registry
from app.utils.errors import MapNotFoundError

router = APIRouter(prefix="/maps", tags=["maps"])


@router.get("", response_model=list[MapWorkspace])
def list_maps():
    return registry.workspaces.list()


@router.post("", response_model=MapWorkspace)
def create_map(payload: MapWorkspaceCreate):
    workspace = MapWorkspace(id=registry.new_id("map"), **payload.model_dump())
    registry.workspaces.add(workspace.id, workspace)
    registry.persist_workspace(workspace)
    return workspace


@router.get("/{map_id}", response_model=MapWorkspace)
def get_map(map_id: str):
    workspace = registry.workspaces.get(map_id)
    if not workspace:
        raise MapNotFoundError(map_id)
    return workspace


@router.put("/{map_id}", response_model=MapWorkspace)
def update_map(map_id: str, payload: MapWorkspaceCreate):
    existing = registry.workspaces.get(map_id)
    if not existing:
        raise MapNotFoundError(map_id)
    from datetime import datetime, timezone

    updated = existing.model_copy(update={**payload.model_dump(), "updated_at": datetime.now(timezone.utc)})
    registry.workspaces.update(map_id, updated)
    registry.persist_workspace(updated)
    return updated


@router.delete("/{map_id}")
def delete_map(map_id: str):
    if not registry.workspaces.get(map_id):
        raise MapNotFoundError(map_id)
    registry.workspaces.delete(map_id)
    return {"deleted": map_id}
