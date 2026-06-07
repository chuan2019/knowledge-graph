from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VectorAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    model: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class VectorAskResponse(BaseModel):
    question: str
    answer: str
    hits: list[dict[str, Any]]
    hit_count: int
    agent_trace: list[str]
