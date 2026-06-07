"""Load title documents into Weaviate for vector-based semantic search.

Creates (or recreates) the ContentTitle collection with text2vec-ollama
vectorization, then imports titles together with their generated synopses.

Usage:
    python kg4rag/vector-data-loader.py

Environment variables:
    WEAVIATE_HOST          (default: localhost)
    WEAVIATE_HTTP_PORT     (default: 8080)
    WEAVIATE_GRPC_PORT     (default: 50051)
    OLLAMA_BASE_URL        (default: http://localhost:11434)
    OLLAMA_EMBED_MODEL     (default: nomic-embed-text)
    KG_DATA_DIR            (default: <script dir>/kg_demo_data)
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import weaviate
import weaviate.classes as wvc

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
WEAVIATE_HTTP_PORT = int(os.getenv("WEAVIATE_HTTP_PORT", "8080"))
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
DATA_DIR = Path(os.getenv("KG_DATA_DIR", Path(__file__).with_name("kg_demo_data")))

COLLECTION_NAME = "ContentTitle"
BATCH_SIZE = 100


def load_data() -> None:
    titles_df = pd.read_csv(DATA_DIR / "titles.csv")
    desc_df = pd.read_csv(DATA_DIR / "title_descriptions.csv")
    merged = titles_df.merge(desc_df, on="title_id", how="left")
    merged["synopsis"] = merged["synopsis"].fillna("")

    client = weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_HTTP_PORT,
        grpc_port=WEAVIATE_GRPC_PORT,
    )
    try:
        if client.collections.exists(COLLECTION_NAME):
            client.collections.delete(COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'")

        client.collections.create(
            name=COLLECTION_NAME,
            description="Media content titles with semantic synopses for vector similarity search",
            vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_ollama(
                api_endpoint=OLLAMA_BASE_URL,
                model=OLLAMA_EMBED_MODEL,
            ),
            generative_config=wvc.config.Configure.Generative.ollama(
                api_endpoint=OLLAMA_BASE_URL,
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            ),
            properties=[
                wvc.config.Property(
                    name="title_id",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=True,
                    vectorize_property_name=False,
                ),
                wvc.config.Property(
                    name="title_name",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=False,
                    vectorize_property_name=False,
                ),
                wvc.config.Property(
                    name="title_type",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=False,
                    vectorize_property_name=False,
                ),
                wvc.config.Property(
                    name="genre",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=False,
                    vectorize_property_name=False,
                ),
                wvc.config.Property(
                    name="studio",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=True,
                    vectorize_property_name=False,
                ),
                wvc.config.Property(
                    name="release_year",
                    data_type=wvc.config.DataType.INT,
                ),
                wvc.config.Property(
                    name="duration_minutes",
                    data_type=wvc.config.DataType.INT,
                ),
                wvc.config.Property(
                    name="season_count",
                    data_type=wvc.config.DataType.INT,
                ),
                wvc.config.Property(
                    name="synopsis",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=False,
                    vectorize_property_name=False,
                ),
            ],
        )
        print(f"Created collection '{COLLECTION_NAME}'")

        collection = client.collections.get(COLLECTION_NAME)

        def _safe_int(val, default: int = 0) -> int:
            try:
                v = int(val)
                return v if not pd.isna(val) else default
            except (ValueError, TypeError):
                return default

        total = 0
        with collection.batch.fixed_size(batch_size=BATCH_SIZE) as batch:
            for _, row in merged.iterrows():
                batch.add_object(
                    properties={
                        "title_id": str(row["title_id"]),
                        "title_name": str(row["title_name"]),
                        "title_type": str(row["title_type"]),
                        "genre": str(row["genre"]),
                        "studio": str(row["studio"]),
                        "release_year": _safe_int(row.get("release_year"), 2000),
                        "duration_minutes": _safe_int(row.get("duration_minutes"), 0),
                        "season_count": _safe_int(row.get("season_count"), 0),
                        "synopsis": str(row["synopsis"]),
                    }
                )
                total += 1

        print(f"Imported {total} titles into '{COLLECTION_NAME}'")
        count = collection.aggregate.over_all(total_count=True).total_count
        print(f"Verified count in Weaviate: {count}")
    finally:
        client.close()


if __name__ == "__main__":
    load_data()
