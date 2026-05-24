"""Import generated KG demo CSV files into Neo4j."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, LiteralString, cast

import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "testpass")
DATA_DIR = Path(os.getenv("KG_DATA_DIR", Path(__file__).with_name("kg_demo_data")))
BATCH_SIZE = 1000


def get_auth() -> tuple[str, str]:
    password = NEO4J_PASSWORD.strip() if NEO4J_PASSWORD else ""
    if not password:
        raise ValueError(
            "Neo4j password is missing. Set NEO4J_PASSWORD or use the docker default 'testpass'."
        )
    return NEO4J_USER, password


def chunked(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def normalize_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


def read_csv_rows(file_name: str) -> list[dict[str, Any]]:
    data_frame = pd.read_csv(DATA_DIR / file_name)
    records = data_frame.to_dict(orient="records")
    normalized_records: list[dict[str, Any]] = []
    for record in records:
        normalized_records.append(
            {str(key): normalize_value(value) for key, value in record.items()}
        )
    return normalized_records


def run_batch(session, query: str, rows: list[dict[str, Any]]) -> None:
    literal_query = cast(LiteralString, query)
    for batch in chunked(rows, BATCH_SIZE):
        session.run(literal_query, rows=batch).consume()


def create_constraints(session) -> None:
    constraints = [
        "CREATE CONSTRAINT title_id IF NOT EXISTS FOR (n:Title) REQUIRE n.title_id IS UNIQUE",
        "CREATE CONSTRAINT version_id IF NOT EXISTS FOR (n:Version) REQUIRE n.version_id IS UNIQUE",
        "CREATE CONSTRAINT client_id IF NOT EXISTS FOR (n:Client) REQUIRE n.client_id IS UNIQUE",
        "CREATE CONSTRAINT region_id IF NOT EXISTS FOR (n:Region) REQUIRE n.region_id IS UNIQUE",
        "CREATE CONSTRAINT language_code IF NOT EXISTS FOR (n:Language) REQUIRE n.language_code IS UNIQUE",
        "CREATE CONSTRAINT delivery_point_id IF NOT EXISTS FOR (n:DeliveryPoint) REQUIRE n.delivery_point_id IS UNIQUE",
        "CREATE CONSTRAINT audio_format_id IF NOT EXISTS FOR (n:AudioFormat) REQUIRE n.format_id IS UNIQUE",
        "CREATE CONSTRAINT video_format_id IF NOT EXISTS FOR (n:VideoFormat) REQUIRE n.format_id IS UNIQUE",
        "CREATE CONSTRAINT rights_id IF NOT EXISTS FOR (n:Rights) REQUIRE n.rights_id IS UNIQUE",
        "CREATE CONSTRAINT localization_job_id IF NOT EXISTS FOR (n:LocalizationJob) REQUIRE n.job_id IS UNIQUE",
        "CREATE CONSTRAINT delivery_spec_id IF NOT EXISTS FOR (n:DeliverySpec) REQUIRE n.spec_id IS UNIQUE",
        "CREATE CONSTRAINT delivery_request_id IF NOT EXISTS FOR (n:DeliveryRequest) REQUIRE n.request_id IS UNIQUE",
    ]
    for query in constraints:
        session.run(cast(LiteralString, query)).consume()


def import_data() -> None:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    csv_rows = {
        "titles": read_csv_rows("titles.csv"),
        "versions": read_csv_rows("versions.csv"),
        "clients": read_csv_rows("clients.csv"),
        "regions": read_csv_rows("regions.csv"),
        "languages": read_csv_rows("languages.csv"),
        "delivery_points": read_csv_rows("delivery_points.csv"),
        "audio_formats": read_csv_rows("audio_formats.csv"),
        "video_formats": read_csv_rows("video_formats.csv"),
        "rights": read_csv_rows("rights.csv"),
        "localization": read_csv_rows("localization.csv"),
        "delivery_specs": read_csv_rows("delivery_specs.csv"),
        "delivery_requests": read_csv_rows("delivery_requests.csv"),
    }

    driver = GraphDatabase.driver(NEO4J_URI, auth=get_auth())
    try:
        with driver.session() as session:
            session.run(cast(LiteralString, "MATCH (n) DETACH DELETE n")).consume()
            create_constraints(session)

            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:Title {title_id: row.title_id})
                SET n += row
                """,
                csv_rows["titles"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:Client {client_id: row.client_id})
                SET n += row
                """,
                csv_rows["clients"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:Region {region_id: row.region_id})
                SET n += row
                """,
                csv_rows["regions"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:Language {language_code: row.language_code})
                SET n += row
                """,
                csv_rows["languages"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:AudioFormat {format_id: row.format_id})
                SET n += row
                """,
                csv_rows["audio_formats"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:VideoFormat {format_id: row.format_id})
                SET n += row
                """,
                csv_rows["video_formats"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:Version {version_id: row.version_id})
                SET n += row
                """,
                csv_rows["versions"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:DeliveryPoint {delivery_point_id: row.delivery_point_id})
                SET n += row
                """,
                csv_rows["delivery_points"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:Rights {rights_id: row.rights_id})
                SET n += row
                """,
                csv_rows["rights"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:LocalizationJob {job_id: row.job_id})
                SET n += row
                """,
                csv_rows["localization"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:DeliverySpec {spec_id: row.spec_id})
                SET n += row
                """,
                csv_rows["delivery_specs"],
            )
            run_batch(
                session,
                """
                UNWIND $rows AS row
                MERGE (n:DeliveryRequest {request_id: row.request_id})
                SET n += row
                """,
                csv_rows["delivery_requests"],
            )

            session.run(
                cast(
                    LiteralString,
                    """
                    MATCH (t:Title)
                    MATCH (v:Version {title_id: t.title_id})
                    MERGE (t)-[:HAS_VERSION]->(v)
                    """,
                )
            ).consume()
            session.run(
                cast(
                    LiteralString,
                    """
                    MATCH (dp:DeliveryPoint)
                    MATCH (r:Region {region_id: dp.region_id})
                    MERGE (dp)-[:LOCATED_IN]->(r)
                    """,
                )
            ).consume()
            session.run(
                cast(
                    LiteralString,
                    """
                    MATCH (rg:Rights)
                    MATCH (v:Version {version_id: rg.version_id})
                    MATCH (c:Client {client_id: rg.client_id})
                    MATCH (r:Region {region_id: rg.region_id})
                    MERGE (rg)-[:FOR_VERSION]->(v)
                    MERGE (rg)-[:GRANTED_TO]->(c)
                    MERGE (rg)-[:FOR_REGION]->(r)
                    """,
                )
            ).consume()
            session.run(
                cast(
                    LiteralString,
                    """
                    MATCH (lj:LocalizationJob)
                    MATCH (v:Version {version_id: lj.version_id})
                    MATCH (l:Language {language_code: lj.language_code})
                    MERGE (lj)-[:FOR_VERSION]->(v)
                    MERGE (lj)-[:LOCALIZED_FOR]->(l)
                    """,
                )
            ).consume()
            session.run(
                cast(
                    LiteralString,
                    """
                    MATCH (ds:DeliverySpec)
                    MATCH (dp:DeliveryPoint {delivery_point_id: ds.delivery_point_id})
                    MATCH (v:Version {version_id: ds.version_id})
                    MERGE (ds)-[:FOR_DELIVERY_POINT]->(dp)
                    MERGE (ds)-[:FOR_VERSION]->(v)
                    """,
                )
            ).consume()
            session.run(
                cast(
                    LiteralString,
                    """
                    MATCH (dr:DeliveryRequest)
                    MATCH (v:Version {version_id: dr.version_id})
                    MATCH (c:Client {client_id: dr.client_id})
                    MATCH (dp:DeliveryPoint {delivery_point_id: dr.delivery_point_id})
                    MERGE (dr)-[:FOR_VERSION]->(v)
                    MERGE (dr)-[:REQUESTED_BY]->(c)
                    MERGE (dr)-[:TO_POINT]->(dp)
                    """,
                )
            ).consume()
    finally:
        driver.close()

    print(f"Import complete from {DATA_DIR}")


if __name__ == "__main__":
    import_data()