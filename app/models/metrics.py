from __future__ import annotations

from pydantic import BaseModel


class PathMetricsResponse(BaseModel):
    method: str
    path: str
    requests: int
    avg_duration_ms: float
    max_duration_ms: float
    status_counts: dict[str, int]


class MetricsResponse(BaseModel):
    total_requests: int
    in_flight_requests: int
    total_exceptions: int
    paths: list[PathMetricsResponse]
