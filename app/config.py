from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "testpass"
    neo4j_database: str = "neo4j"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    planner_temperature: float = 0.0
    answer_temperature: float = 0.2
    max_query_retries: int = 2
    result_row_limit: int = 25
    cypher_timeout_ms: int = 15000

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            neo4j_uri=os.getenv("NEO4J_URI", cls.neo4j_uri),
            neo4j_user=os.getenv("NEO4J_USER", cls.neo4j_user),
            neo4j_password=os.getenv("NEO4J_PASSWORD", cls.neo4j_password),
            neo4j_database=os.getenv("NEO4J_DATABASE", cls.neo4j_database),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", cls.ollama_base_url),
            ollama_model=os.getenv("OLLAMA_MODEL", cls.ollama_model),
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
        )
