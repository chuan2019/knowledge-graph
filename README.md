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

## FastAPI Question-Answering Service

The repository now includes a FastAPI web service that lets a user submit a natural-language question, translates that question into read-only Cypher, executes the query against Neo4j, and sends the retrieved records to an LLM for a natural-language answer.

The service code lives under:

- [app/main.py](app/main.py)
- [app/services/qa_service.py](app/services/qa_service.py)
- [app/services/graph_store.py](app/services/graph_store.py)
- [app/services/ollama_client.py](app/services/ollama_client.py)

The QA flow is intentionally agentic in a narrow, practical sense:

- plan a Cypher query from the user question
- execute the query against Neo4j
- repair and retry if Neo4j rejects the generated Cypher
- synthesize a grounded answer from the retrieved rows

### Prerequisites

- Neo4j running locally
- Ollama running locally
- a local Ollama model pulled, for example:

```bash
ollama pull llama3.2
```

If you use Docker Compose from this repo, start Neo4j and Ollama with:

```bash
cd /home/chuan/Projects/knowledge-graph
docker compose up -d neo4j ollama
```

To run the API in Docker as well:

```bash
cd /home/chuan/Projects/knowledge-graph
docker compose up -d api neo4j ollama
```

In Docker Compose, the API container connects to Neo4j and Ollama over the internal service network using:

- `NEO4J_URI=bolt://neo4j:7687`
- `OLLAMA_BASE_URL=http://ollama:11434`

### Start the API

```bash
cd /home/chuan/Projects/knowledge-graph
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

After the server starts, open the browser UI at:

```text
http://localhost:8000/
```

The page lets you submit a question, inspect the generated Cypher, and review the returned rows and agent trace.

### Environment Variables

The service uses these defaults:

- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=testpass`
- `NEO4J_DATABASE=neo4j`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=llama3.2`

Optional tuning:

- `MAX_QUERY_RETRIES=2`
- `RESULT_ROW_LIMIT=25`
- `CYPHER_TIMEOUT_MS=15000`

### API Endpoints

- `GET /health`
- `GET /api/v1/schema`
- `POST /api/v1/ask`

Compatibility routes are also kept for the current browser UI and existing callers:

- `GET /schema`
- `POST /api/ask`

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/ask \
	-H 'Content-Type: application/json' \
	-d '{
		"question": "Which Tier 1 clients have active rights for localized versions?",
		"include_rows": true
	}'
```

Example response shape:

```json
{
	"question": "Which Tier 1 clients have active rights for localized versions?",
	"answer": "...",
	"cypher": "MATCH ... RETURN ... LIMIT 25",
	"rows": [
		{
			"title_name": "...",
			"client_name": "..."
		}
	],
	"row_count": 12,
	"agent_trace": [
		"Received user question.",
		"Planned Cypher on attempt 1.",
		"Executed Cypher and retrieved 12 rows.",
		"Synthesized natural-language answer."
	]
}
```

## Example Workflow

```bash
cd /home/chuan/Projects/knowledge-graph
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
