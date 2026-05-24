#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib
import os
import sys
from typing import Any

try:
    GraphDatabase = importlib.import_module("neo4j").GraphDatabase
except ImportError as exc:  # pragma: no cover - import guard for local setup
    raise SystemExit(
        "The neo4j package is required. Install it with: uv add neo4j"
    ) from exc


DEFAULT_DATASET_ID = "kg-rag-movie-demo"

DEMO_MOVIES: list[dict[str, Any]] = [
    {
        "title": "Inception",
        "year": 2010,
        "director": "Christopher Nolan",
        "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
        "genres": ["Sci-Fi", "Thriller"],
        "themes": ["Dreams", "Memory", "Time", "Identity"],
        "summary": (
            "A skilled extractor enters layered dreams to implant an idea while wrestling "
            "with guilt, memory, and the unstable nature of reality."
        ),
    },
    {
        "title": "Interstellar",
        "year": 2014,
        "director": "Christopher Nolan",
        "actors": ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"],
        "genres": ["Sci-Fi", "Drama"],
        "themes": ["Space", "Time", "Love", "Survival"],
        "summary": (
            "A team of explorers travels through a wormhole to find a new home for humanity, "
            "where time dilation and sacrifice shape every decision."
        ),
    },
    {
        "title": "Memento",
        "year": 2000,
        "director": "Christopher Nolan",
        "actors": ["Guy Pearce", "Carrie-Anne Moss", "Joe Pantoliano"],
        "genres": ["Thriller", "Mystery"],
        "themes": ["Memory", "Identity", "Revenge"],
        "summary": (
            "A man with short-term memory loss uses notes and tattoos to pursue revenge, "
            "turning memory itself into the central mystery."
        ),
    },
    {
        "title": "Tenet",
        "year": 2020,
        "director": "Christopher Nolan",
        "actors": ["John David Washington", "Robert Pattinson", "Elizabeth Debicki"],
        "genres": ["Sci-Fi", "Action", "Thriller"],
        "themes": ["Time", "Espionage", "Entropy"],
        "summary": (
            "An operative manipulates inverted time to prevent global catastrophe in a story "
            "driven by temporal mechanics and high-stakes espionage."
        ),
    },
    {
        "title": "The Matrix",
        "year": 1999,
        "director": "The Wachowskis",
        "actors": ["Keanu Reeves", "Carrie-Anne Moss", "Laurence Fishburne"],
        "genres": ["Sci-Fi", "Action"],
        "themes": ["Reality", "Simulation", "Cyberpunk", "AI"],
        "summary": (
            "A hacker discovers that reality is a simulation and joins a rebellion against the "
            "machines controlling humanity."
        ),
    },
    {
        "title": "The Matrix Reloaded",
        "year": 2003,
        "director": "The Wachowskis",
        "actors": ["Keanu Reeves", "Carrie-Anne Moss", "Laurence Fishburne"],
        "genres": ["Sci-Fi", "Action"],
        "themes": ["Simulation", "Cyberpunk", "Choice", "AI"],
        "summary": (
            "Neo and his allies push deeper into the machine conflict while prophecy, choice, "
            "and simulation remain central to the story."
        ),
    },
    {
        "title": "Johnny Mnemonic",
        "year": 1995,
        "director": "Robert Longo",
        "actors": ["Keanu Reeves", "Dina Meyer", "Takeshi Kitano"],
        "genres": ["Sci-Fi", "Action"],
        "themes": ["Cyberpunk", "Data", "Memory", "Corporations"],
        "summary": (
            "A data courier with a storage implant carries sensitive information through a dystopian "
            "future shaped by cybernetic tech and corporate power."
        ),
    },
    {
        "title": "John Wick",
        "year": 2014,
        "director": "Chad Stahelski",
        "actors": ["Keanu Reeves", "Michael Nyqvist", "Willem Dafoe"],
        "genres": ["Action", "Thriller"],
        "themes": ["Revenge", "Underworld", "Loyalty"],
        "summary": (
            "A retired assassin returns to a hidden criminal underworld after a brutal personal loss "
            "pulls him back into violence."
        ),
    },
    {
        "title": "Blade Runner 2049",
        "year": 2017,
        "director": "Denis Villeneuve",
        "actors": ["Ryan Gosling", "Harrison Ford", "Ana de Armas"],
        "genres": ["Sci-Fi", "Drama"],
        "themes": ["AI", "Identity", "Memory", "Cyberpunk"],
        "summary": (
            "A blade runner uncovers a buried secret in a future defined by replicants, surveillance, "
            "and questions of identity and memory."
        ),
    },
    {
        "title": "Dark City",
        "year": 1998,
        "director": "Alex Proyas",
        "actors": ["Rufus Sewell", "Jennifer Connelly", "Kiefer Sutherland"],
        "genres": ["Sci-Fi", "Mystery"],
        "themes": ["Memory", "Reality", "Identity"],
        "summary": (
            "A man awakens with no memory in a city where reality itself is manipulated by unseen "
            "forces."
        ),
    },
]

SIMILAR_MOVIES: list[dict[str, Any]] = [
    {
        "left_title": "Inception",
        "right_title": "Interstellar",
        "score": 0.92,
        "reasons": ["director", "genre", "theme"],
        "note": "Christopher Nolan sci-fi films with strong time-centric storytelling.",
    },
    {
        "left_title": "Inception",
        "right_title": "Tenet",
        "score": 0.89,
        "reasons": ["director", "theme"],
        "note": "Both films lean on time manipulation and layered, puzzle-box plots.",
    },
    {
        "left_title": "Inception",
        "right_title": "Memento",
        "score": 0.83,
        "reasons": ["director", "theme"],
        "note": "Both Nolan films use memory as a core narrative device.",
    },
    {
        "left_title": "The Matrix",
        "right_title": "The Matrix Reloaded",
        "score": 0.98,
        "reasons": ["director", "genre", "theme"],
        "note": "Direct franchise continuation with the same creative core and themes.",
    },
    {
        "left_title": "The Matrix",
        "right_title": "Johnny Mnemonic",
        "score": 0.85,
        "reasons": ["actor", "genre", "theme"],
        "note": "Keanu Reeves cyberpunk stories centered on digital control and stored data.",
    },
    {
        "left_title": "The Matrix",
        "right_title": "Blade Runner 2049",
        "score": 0.82,
        "reasons": ["genre", "theme"],
        "note": "Both explore cyberpunk futures, identity, and human-machine boundaries.",
    },
    {
        "left_title": "The Matrix",
        "right_title": "Dark City",
        "score": 0.8,
        "reasons": ["genre", "theme"],
        "note": "Both question whether perceived reality is authentic or manufactured.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load the sample movie graph used in the KG-RAG demo documents."
    )
    parser.add_argument(
        "--uri",
        default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j Bolt URI.",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("NEO4J_USER", "neo4j"),
        help="Neo4j username.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD", "testpass"),
        help="Neo4j password.",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("NEO4J_DATABASE", "neo4j"),
        help="Neo4j database name.",
    )
    parser.add_argument(
        "--dataset-id",
        default=os.getenv("KG_RAG_DATASET_ID", DEFAULT_DATASET_ID),
        help="Dataset marker attached to all demo nodes.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing nodes from the same dataset id before loading.",
    )
    return parser.parse_args()


def reset_dataset(tx, dataset_id: str) -> None:
    tx.run(
        """
        MATCH (n:Demo {dataset: $dataset_id})
        DETACH DELETE n
        """,
        dataset_id=dataset_id,
    )


def load_movies(tx, dataset_id: str, movies: list[dict[str, Any]]) -> None:
    tx.run(
        """
        UNWIND $movies AS movie
        MERGE (m:Movie:Demo {dataset: $dataset_id, title: movie.title})
        SET m.year = movie.year,
            m.summary = movie.summary

        MERGE (d:Person:Demo {dataset: $dataset_id, name: movie.director})
        MERGE (d)-[:DIRECTED {dataset: $dataset_id}]->(m)

        FOREACH (actor IN movie.actors |
          MERGE (a:Person:Demo {dataset: $dataset_id, name: actor})
          MERGE (a)-[:ACTED_IN {dataset: $dataset_id}]->(m)
        )

        FOREACH (genre IN movie.genres |
          MERGE (g:Genre:Demo {dataset: $dataset_id, name: genre})
          MERGE (m)-[:HAS_GENRE {dataset: $dataset_id}]->(g)
        )

        FOREACH (theme IN movie.themes |
          MERGE (t:Theme:Demo {dataset: $dataset_id, name: theme})
          MERGE (m)-[:HAS_THEME {dataset: $dataset_id}]->(t)
        )
        """,
        dataset_id=dataset_id,
        movies=movies,
    )


def load_similar_movies(tx, dataset_id: str, movie_pairs: list[dict[str, Any]]) -> None:
    tx.run(
        """
        UNWIND $movie_pairs AS pair
        MATCH (left:Movie:Demo {dataset: $dataset_id, title: pair.left_title})
        MATCH (right:Movie:Demo {dataset: $dataset_id, title: pair.right_title})
        MERGE (left)-[forward:SIMILAR_TO {dataset: $dataset_id}]->(right)
        SET forward.score = pair.score,
            forward.reasons = pair.reasons,
            forward.note = pair.note
        MERGE (right)-[reverse:SIMILAR_TO {dataset: $dataset_id}]->(left)
        SET reverse.score = pair.score,
            reverse.reasons = pair.reasons,
            reverse.note = pair.note
        """,
        dataset_id=dataset_id,
        movie_pairs=movie_pairs,
    )


def fetch_counts(session, dataset_id: str) -> dict[str, int]:
    record = session.run(
        """
        CALL {
          MATCH (:Movie:Demo {dataset: $dataset_id})
          RETURN count(*) AS movies
        }
        CALL {
          MATCH (:Person:Demo {dataset: $dataset_id})
          RETURN count(*) AS people
        }
        CALL {
          MATCH (:Genre:Demo {dataset: $dataset_id})
          RETURN count(*) AS genres
        }
        CALL {
          MATCH (:Theme:Demo {dataset: $dataset_id})
          RETURN count(*) AS themes
        }
        CALL {
          MATCH (:Demo {dataset: $dataset_id})-[r {dataset: $dataset_id}]->(:Demo {dataset: $dataset_id})
          RETURN count(r) AS relationships
        }
        RETURN movies, people, genres, themes, relationships
        """,
        dataset_id=dataset_id,
    ).single()
    if record is None:
        return {"movies": 0, "people": 0, "genres": 0, "themes": 0, "relationships": 0}
    return {key: int(record[key]) for key in record.keys()}


def print_demo_queries(dataset_id: str) -> None:
    print("\nSuggested Cypher queries for the demo:\n")
    print("1. Christopher Nolan + Sci-Fi + memory/time")
    print(
        """
MATCH (d:Person:Demo {dataset: $dataset_id, name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie:Demo)-[:HAS_GENRE]->(:Genre:Demo {dataset: $dataset_id, name: 'Sci-Fi'})
MATCH (m)-[:HAS_THEME]->(t:Theme:Demo {dataset: $dataset_id})
WHERE t.name IN ['Memory', 'Time']
RETURN m.title AS movie, m.year AS year, collect(DISTINCT t.name) AS matched_themes, m.summary AS summary
ORDER BY year DESC;
        """.strip()
    )
    print("\n2. Keanu Reeves movies connected to cyberpunk themes")
    print(
        """
MATCH (:Person:Demo {dataset: $dataset_id, name: 'Keanu Reeves'})-[:ACTED_IN]->(m:Movie:Demo)-[:HAS_THEME]->(:Theme:Demo {dataset: $dataset_id, name: 'Cyberpunk'})
RETURN m.title AS movie, m.year AS year, m.summary AS summary
ORDER BY year;
        """.strip()
    )
    print("\n3. Movies related to The Matrix through genre, theme, director, or curated similarity")
    print(
        """
MATCH (seed:Movie:Demo {dataset: $dataset_id, title: 'The Matrix'})
OPTIONAL MATCH (seed)<-[:DIRECTED]-(director:Person:Demo)-[:DIRECTED]->(director_match:Movie:Demo)
OPTIONAL MATCH (seed)-[:HAS_GENRE]->(genre:Genre:Demo)<-[:HAS_GENRE]-(genre_match:Movie:Demo)
OPTIONAL MATCH (seed)-[:HAS_THEME]->(theme:Theme:Demo)<-[:HAS_THEME]-(theme_match:Movie:Demo)
OPTIONAL MATCH (seed)-[sim:SIMILAR_TO]->(similar_match:Movie:Demo)
WITH seed,
     collect(DISTINCT director_match.title) +
     collect(DISTINCT genre_match.title) +
     collect(DISTINCT theme_match.title) +
     collect(DISTINCT similar_match.title) AS raw_titles
UNWIND raw_titles AS related_title
WITH seed, related_title
WHERE related_title IS NOT NULL AND related_title <> seed.title
RETURN DISTINCT related_title
ORDER BY related_title;
        """.strip()
    )
    print(f"\nUse parameters: {{'dataset_id': '{dataset_id}'}}")


def main() -> int:
    args = parse_args()
    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))

    try:
        with driver.session(database=args.database) as session:
            session.run("RETURN 1").consume()
            if args.reset:
                session.execute_write(reset_dataset, args.dataset_id)
            session.execute_write(load_movies, args.dataset_id, DEMO_MOVIES)
            session.execute_write(load_similar_movies, args.dataset_id, SIMILAR_MOVIES)
            counts = fetch_counts(session, args.dataset_id)
    except Exception as exc:  # pragma: no cover - runtime diagnostics
        print(f"Failed to load demo data: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.close()

    print(
        "Loaded KG-RAG demo dataset "
        f"'{args.dataset_id}' into {args.database} at {args.uri}."
    )
    print(
        "Counts: "
        f"{counts['movies']} movies, "
        f"{counts['people']} people, "
        f"{counts['genres']} genres, "
        f"{counts['themes']} themes, "
        f"{counts['relationships']} relationships."
    )
    print_demo_queries(args.dataset_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())