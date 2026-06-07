from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    log_level: str = "INFO"
    tracing_enabled: bool = False
    tracing_service_name: str = "knowledge-graph-api"
    otlp_traces_exporter_endpoint: str = "http://localhost:4318/v1/traces"
    qa_max_concurrency: int = 64
    qa_queue_timeout_ms: int = 250
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "testpass"
    neo4j_database: str = "neo4j"
    neo4j_max_connection_pool_size: int = 100
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 60.0
    ollama_max_connections: int = 200
    ollama_max_keepalive_connections: int = 50
    planner_temperature: float = 0.0
    answer_temperature: float = 0.2
    max_query_retries: int = 2
    result_row_limit: int = 25
    cypher_timeout_ms: int = 15000
    weaviate_host: str = "localhost"
    weaviate_http_port: int = 8080
    weaviate_grpc_port: int = 50051

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            tracing_enabled=_env_bool("TRACING_ENABLED", cls.tracing_enabled),
            tracing_service_name=os.getenv(
                "TRACING_SERVICE_NAME",
                cls.tracing_service_name,
            ),
            otlp_traces_exporter_endpoint=os.getenv(
                "OTEL_TRACES_EXPORTER_ENDPOINT",
                cls.otlp_traces_exporter_endpoint,
            ),
            qa_max_concurrency=int(
                os.getenv("QA_MAX_CONCURRENCY", str(cls.qa_max_concurrency))
            ),
            qa_queue_timeout_ms=int(
                os.getenv("QA_QUEUE_TIMEOUT_MS", str(cls.qa_queue_timeout_ms))
            ),
            neo4j_uri=os.getenv("NEO4J_URI", cls.neo4j_uri),
            neo4j_user=os.getenv("NEO4J_USER", cls.neo4j_user),
            neo4j_password=os.getenv("NEO4J_PASSWORD", cls.neo4j_password),
            neo4j_database=os.getenv("NEO4J_DATABASE", cls.neo4j_database),
            neo4j_max_connection_pool_size=int(
                os.getenv(
                    "NEO4J_MAX_CONNECTION_POOL_SIZE",
                    str(cls.neo4j_max_connection_pool_size),
                )
            ),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", cls.ollama_base_url),
            ollama_model=os.getenv("OLLAMA_MODEL", cls.ollama_model),
            ollama_timeout_seconds=float(
                os.getenv(
                    "OLLAMA_TIMEOUT_SECONDS",
                    str(cls.ollama_timeout_seconds),
                )
            ),
            ollama_max_connections=int(
                os.getenv(
                    "OLLAMA_MAX_CONNECTIONS",
                    str(cls.ollama_max_connections),
                )
            ),
            ollama_max_keepalive_connections=int(
                os.getenv(
                    "OLLAMA_MAX_KEEPALIVE_CONNECTIONS",
                    str(cls.ollama_max_keepalive_connections),
                )
            ),
            planner_temperature=float(
                os.getenv("PLANNER_TEMPERATURE", str(cls.planner_temperature))
            ),
            answer_temperature=float(
                os.getenv("ANSWER_TEMPERATURE", str(cls.answer_temperature))
            ),
            max_query_retries=int(
                os.getenv("MAX_QUERY_RETRIES", str(cls.max_query_retries))
            ),
            result_row_limit=int(
                os.getenv("RESULT_ROW_LIMIT", str(cls.result_row_limit))
            ),
            cypher_timeout_ms=int(
                os.getenv("CYPHER_TIMEOUT_MS", str(cls.cypher_timeout_ms))
            ),
            weaviate_host=os.getenv("WEAVIATE_HOST", cls.weaviate_host),
            weaviate_http_port=int(
                os.getenv("WEAVIATE_HTTP_PORT", str(cls.weaviate_http_port))
            ),
            weaviate_grpc_port=int(
                os.getenv("WEAVIATE_GRPC_PORT", str(cls.weaviate_grpc_port))
            ),
        )
