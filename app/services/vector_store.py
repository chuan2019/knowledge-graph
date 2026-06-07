"""Weaviate vector store — async wrapper for semantic similarity search."""

from __future__ import annotations

import logging
from typing import Any

import weaviate
import weaviate.classes as wvc
from opentelemetry import trace

from app.core.config import Settings

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

COLLECTION_NAME = "ContentTitle"


class VectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: weaviate.WeaviateAsyncClient | None = None

    async def connect(self) -> None:
        self._client = weaviate.use_async_with_local(
            host=self._settings.weaviate_host,
            port=self._settings.weaviate_http_port,
            grpc_port=self._settings.weaviate_grpc_port,
        )
        await self._client.connect()
        logger.info(
            "Connected to Weaviate at %s:%s (gRPC:%s)",
            self._settings.weaviate_host,
            self._settings.weaviate_http_port,
            self._settings.weaviate_grpc_port,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            logger.info("Closed Weaviate connection")

    async def verify_connectivity(self) -> None:
        if self._client is None:
            raise RuntimeError("VectorStore not connected — call connect() first")
        is_ready = await self._client.is_ready()
        if not is_ready:
            raise RuntimeError("Weaviate is not ready")
        exists = await self._client.collections.exists(COLLECTION_NAME)
        if not exists:
            raise RuntimeError(
                f"Weaviate collection '{COLLECTION_NAME}' does not exist. "
                "Run kg4rag/vector-data-loader.py to create and populate it."
            )
        logger.debug("Weaviate connectivity and collection verified")

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        with tracer.start_as_current_span("vector_store.semantic_search") as span:
            span.set_attribute("vs.query_length", len(query))
            span.set_attribute("vs.limit", limit)

            if self._client is None:
                raise RuntimeError("VectorStore not connected")

            collection = self._client.collections.get(COLLECTION_NAME)
            response = await collection.query.near_text(
                query=query,
                limit=limit,
                return_metadata=wvc.query.MetadataQuery(certainty=True, distance=True),
            )

            hits: list[dict[str, Any]] = []
            for obj in response.objects:
                row = dict(obj.properties)
                if obj.metadata:
                    if obj.metadata.certainty is not None:
                        row["_certainty"] = round(float(obj.metadata.certainty), 4)
                    if obj.metadata.distance is not None:
                        row["_distance"] = round(float(obj.metadata.distance), 4)
                hits.append(row)

            span.set_attribute("vs.hit_count", len(hits))
            logger.debug(
                "Semantic search returned %s hits for query_length=%s",
                len(hits),
                len(query),
            )
            return hits
