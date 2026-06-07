from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    id: str
    name: str
    category: Literal["Observability", "Storage", "Model"]
    description: str
    port: int
    client_url: str
    has_ui: bool
    healthy: bool | None = None
