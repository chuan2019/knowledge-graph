# Knowledge Graph Demo Workspace

This repository contains a local workspace for experimenting with knowledge-graph workflows, Neo4j, and graph-oriented retrieval for RAG-style use cases.

The current focus is the `kg4rag` demo, which generates a synthetic media-operations dataset, loads it into Neo4j, and provides a practical graph structure for multi-hop retrieval experiments.

## What Is Included

- `docker-compose.yml`
	Runs Neo4j locally, plus optional Ollama and Weaviate services.
- `kg4rag/kg-data-gen.py`
	Generates synthetic CSV data for titles, versions, rights, localization, delivery specs, and delivery requests.
- `kg4rag/kg-data-loader.py`
	Loads the generated CSV files into Neo4j using the Python driver.
- `kg4rag/kg_demo_data/`
	Output folder for generated CSV files and supporting demo artifacts.
- `notebooks/`
	Notebooks for graph-related exploration.

## Services

The Docker setup provides these services:

- `Neo4j`
	- Bolt: `bolt://localhost:7687`
	- Browser: `http://localhost:7474`
	- Default credentials: `neo4j` / `testpass`
- `Ollama`
	- API: `http://localhost:11434`
- `Weaviate`
	- HTTP API: `http://localhost:8080`

If you only need the graph database for the `kg4rag` workflow, Neo4j is the main required service.

## Python Environment

This project uses `uv` and defines dependencies in [pyproject.toml](pyproject.toml).

Create or sync the environment with:

```bash
cd /home/chuan/Documents/My_Study/AI/knowledge-graph
uv sync
```

If you prefer `pip`, the dependency list is mirrored in [requirements.txt](requirements.txt).

## Start the Local Services

To start Neo4j only:

```bash
cd /home/chuan/Documents/My_Study/AI/knowledge-graph
docker compose up -d neo4j
```

To start all services:

```bash
cd /home/chuan/Documents/My_Study/AI/knowledge-graph
docker compose up -d
```

## Generate the KG Demo Data

The main generator builds a synthetic media supply-chain dataset with entities such as:

- `Title`
- `Version`
- `Client`
- `Region`
- `Language`
- `DeliveryPoint`
- `Rights`
- `LocalizationJob`
- `DeliverySpec`
- `DeliveryRequest`

Run the generator with:

```bash
cd /home/chuan/Documents/My_Study/AI/knowledge-graph
uv run python kg4rag/kg-data-gen.py
```

By default, the generated files are written to:

```text
kg4rag/kg_demo_data/
```

The generator creates CSV files such as:

- `titles.csv`
- `versions.csv`
- `clients.csv`
- `regions.csv`
- `languages.csv`
- `rights.csv`
- `localization.csv`
- `delivery_points.csv`
- `delivery_specs.csv`
- `delivery_requests.csv`

## Load the Data into Neo4j

After generating the CSV files, load them into Neo4j with:

```bash
cd /home/chuan/Documents/My_Study/AI/knowledge-graph
uv run python kg4rag/kg-data-loader.py
```

The loader:

- reads CSV files directly from `kg4rag/kg_demo_data`
- creates Neo4j constraints for the main node identifiers
- loads nodes in batches
- creates the main graph relationships after node import

By default, the loader connects with:

- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=testpass`

You can override them with environment variables:

```bash
NEO4J_URI=bolt://localhost:7687 \
NEO4J_USER=neo4j \
NEO4J_PASSWORD=testpass \
KG_DATA_DIR=/home/chuan/Documents/My_Study/AI/knowledge-graph/kg4rag/kg_demo_data \
uv run python kg4rag/kg-data-loader.py
```

Important:

- the loader currently starts with `MATCH (n) DETACH DELETE n`
- this clears the entire Neo4j database before reloading the demo data

## Example Workflow

```bash
cd /home/chuan/Documents/My_Study/AI/knowledge-graph
docker compose up -d neo4j
uv sync
uv run python kg4rag/kg-data-gen.py
uv run python kg4rag/kg-data-loader.py
```

Then open Neo4j Browser at:

```text
http://localhost:7474
```

## Notes

- The `kg4rag` dataset is synthetic and intended for demos, graph experiments, and article examples.
- The current graph model keeps operational records such as rights, localization jobs, delivery specs, and delivery requests as explicit nodes.
- Some technical format fields are still stored inline in the generated CSV data rather than being fully normalized.

## Related Files

- [pyproject.toml](pyproject.toml)
- [requirements.txt](requirements.txt)
- [docker-compose.yml](docker-compose.yml)
- [kg4rag/kg-data-gen.py](kg4rag/kg-data-gen.py)
- [kg4rag/kg-data-loader.py](kg4rag/kg-data-loader.py)
- [kg4rag/kg_demo_data/data_model.md](kg4rag/kg_demo_data/data_model.md)
