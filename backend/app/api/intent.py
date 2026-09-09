from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import registry
from app.services.intent_router import IntentResult, parse_intent

router = APIRouter(prefix="/intent", tags=["intent"])


class IntentRequest(BaseModel):
    text: str


class MatchedDataset(BaseModel):
    id: str
    name: str
    tags: list[str]


class IntentResponse(BaseModel):
    actions: list[str]
    domains: list[str]
    panel: str
    tool: str | None
    hint: str
    matched_datasets: list[MatchedDataset]


@router.post("", response_model=IntentResponse)
def interpret_intent(payload: IntentRequest):
    result: IntentResult = parse_intent(payload.text)

    matched = []
    if result.domains:
        for dataset in registry.datasets.list():
            if set(dataset.tags) & set(result.domains):
                matched.append(MatchedDataset(id=dataset.id, name=dataset.name, tags=dataset.tags))

    return IntentResponse(
        actions=result.actions,
        domains=result.domains,
        panel=result.panel,
        tool=result.tool,
        hint=result.hint,
        matched_datasets=matched[:10],
    )
