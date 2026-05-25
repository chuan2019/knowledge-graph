"""Metrics endpoints."""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Request

from app.core.middleware import MetricsRegistry
from app.models.metrics import MetricsResponse

router = APIRouter()
legacy_router = APIRouter(include_in_schema=False)


def _get_metrics_response(request: Request) -> MetricsResponse:
    registry: MetricsRegistry = request.app.state.metrics_registry
    snapshot = cast(dict[str, Any], registry.snapshot())
    return MetricsResponse(**snapshot)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(request: Request) -> MetricsResponse:
    return _get_metrics_response(request)


@legacy_router.get("/metrics")
async def get_legacy_metrics(request: Request) -> MetricsResponse:
    return _get_metrics_response(request)
