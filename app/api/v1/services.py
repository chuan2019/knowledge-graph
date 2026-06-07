"""Services health-check endpoint."""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter

from app.models.services import ServiceStatus

router = APIRouter()

_SERVICES: list[ServiceStatus] = [
    ServiceStatus(
        id="grafana",
        name="Grafana",
        category="Observability",
        description="Dashboards & visualizations",
        port=3000,
        client_url="http://localhost:3000",
        has_ui=True,
    ),
    ServiceStatus(
        id="prometheus",
        name="Prometheus",
        category="Observability",
        description="Metrics collection & alerting",
        port=9090,
        client_url="http://localhost:9090",
        has_ui=True,
    ),
    ServiceStatus(
        id="jaeger",
        name="Jaeger",
        category="Observability",
        description="Distributed tracing",
        port=16686,
        client_url="http://localhost:16686",
        has_ui=True,
    ),
    ServiceStatus(
        id="loki",
        name="Loki",
        category="Observability",
        description="Log aggregation",
        port=3100,
        client_url="http://localhost:3100",
        has_ui=False,
    ),
    ServiceStatus(
        id="neo4j",
        name="Neo4j",
        category="Storage",
        description="Graph database browser",
        port=7474,
        client_url="http://localhost:7474",
        has_ui=True,
    ),
    ServiceStatus(
        id="weaviate",
        name="Weaviate",
        category="Storage",
        description="Vector database",
        port=8080,
        client_url="http://localhost:8080",
        has_ui=False,
    ),
    ServiceStatus(
        id="ollama",
        name="Ollama",
        category="Model",
        description="LLM runtime & model serving",
        port=11434,
        client_url="http://localhost:11434",
        has_ui=False,
    ),
]

_HEALTH_URLS: dict[str, str] = {
    "grafana": "http://grafana:3000/api/health",
    "prometheus": "http://prometheus:9090/-/healthy",
    "jaeger": "http://jaeger:14269/",
    "loki": "http://loki:3100/ready",
    "neo4j": "http://neo4j:7474/",
    "weaviate": "http://weaviate:8080/v1/.well-known/ready",
    "ollama": "http://ollama:11434/",
}


async def _probe(client: httpx.AsyncClient, svc_id: str) -> bool:
    try:
        r = await client.get(_HEALTH_URLS[svc_id], timeout=2.0)
        return r.status_code < 500
    except Exception:
        return False


@router.get("/services", response_model=list[ServiceStatus])
async def get_services() -> list[ServiceStatus]:
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_probe(client, s.id) for s in _SERVICES])
    return [s.model_copy(update={"healthy": h}) for s, h in zip(_SERVICES, results)]
