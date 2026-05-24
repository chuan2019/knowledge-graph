from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    model: str | None = None
    include_rows: bool = True


class AskResponse(BaseModel):
    question: str
    answer: str
    cypher: str
    rows: list[dict[str, Any]]
    row_count: int
    agent_trace: list[str]


class HealthResponse(BaseModel):
    status: str
    neo4j: str
    ollama_base_url: str
    model: str


class SchemaResponse(BaseModel):
    graph_schema: str
