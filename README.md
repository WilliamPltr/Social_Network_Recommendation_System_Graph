## Professional Social Network Recommendation System (Neo4j + FastAPI)

This project implements a **LinkedIn-style professional network** on top of **Neo4j** with a **FastAPI** backend, using:

- **SNAP GitHub Developers dataset** for the social graph.
- **LinkedIn Job Listings** (`datastax/linkedin_job_listings` on Hugging Face) for jobs.
- **Graph-based recommendations**:
  - **Friend recommendations** via mutual connections.
  - **“People you may know”** via **Pearson correlation** on SNAP feature vectors.
  - **Job recommendations** via **embeddings** stored on `User` and `Job` nodes.

### Main Components

- **`docker-compose.yml`**: Orchestrates:
  - `neo4j`: graph database.
  - `api`: FastAPI service exposing the endpoints.
  - `tests`: container running `pytest`.
- **`app/`**:
  - `main.py`: FastAPI app and endpoints:
    - `GET /api/users/{user_id}/recommendations/friends`
    - `GET /api/users/{user_id}/suggestions/people`
    - `GET /api/users/{user_id}/recommendations/jobs`
    - `GET /api/paths/shortest?from_user=&to_user=`
  - `db.py`: Neo4j async driver/session management.
  - `config.py`: environment-based configuration.
  - `recommendation.py`: mutual friends, Pearson-based “people you may know”, and job matching via cosine similarity over embeddings.
- **`scripts/`**:
  - `load_snap.py`: ETL for SNAP GitHub graph → `User` nodes + `KNOWS` relationships + `features` vector.
  - `load_jobs.py`: ETL for LinkedIn jobs → `Job` nodes with text **embeddings** using `sentence-transformers`.
  - `create_user_embeddings.py`: projects SNAP `features` into dense `User.embedding` vectors compatible with `Job.embedding`.
- **`tests/`**:
  - `test_pearson.py`: tests for the Pearson correlation function used in the “people you may know” algorithm.

### Running the Stack

1. **Build and start services**:

```bash
make up
```

or for the 🥷


```bash
docker compose up --build
```

2. **Load data into Neo4j** (in another terminal, inside the project directory):

```bash
make begin
```

or for the 🥷🏿

```bash
docker compose exec api python -m scripts.load_snap
docker compose exec api python -m scripts.load_jobs
docker compose exec api python -m scripts.create_user_embeddings
```

3. **Explore the API**:

- Swagger UI: `http://localhost:8000/docs`

### Makefile commands

For convenience, common tasks are exposed via the `Makefile`:

- `make up` – build and start all Docker services.
- `make down` – stop and remove all Docker services.
- `make logs` – follow Docker logs.
- `make api` – run the FastAPI app locally with Uvicorn.
- `make tests` – run the pytest test suite.
- `make lint` – run pylint on `app/`, `scripts/`, and `tests/`.
- `make etl-snap` – load the SNAP GitHub dataset into Neo4j.
- `make etl-jobs` – load LinkedIn job listings into Neo4j.
- `make etl-user-emb` – compute user embeddings based on features.

You can also run `make help` to see a short description of each command.

### Graph Modeling (High-level)

- **Nodes**:
  - `User(id, name, features, embedding)`
  - `Job(job_id, title, company, embedding)`
- **Relationships**:
  - `(:User)-[:KNOWS]->(:User)` for follower/friend relationships.

**Pearson-based “People you may know”**

- SNAP feature vectors are loaded into `User.features` as fixed-length numeric lists.
- For a given user, we compute **Pearson correlation coefficient** between their feature vector and all others.
- We keep only positive correlations and return the **top-N users** as `"people you may know"`.

**Job Recommendations via Embeddings**

- `scripts/load_jobs.py` computes an embedding of job title/company/location using
  `sentence-transformers/all-MiniLM-L6-v2` and stores it in `Job.embedding`.
- `scripts/create_user_embeddings.py` uses `app.embedding.project_features_to_embedding`
  to map SNAP `features` into a dense `User.embedding` with the **same dimensionality**
  as `Job.embedding`, making direct cosine similarity comparisons possible.
- The API then uses **cosine similarity** between `User.embedding` and `Job.embedding` to rank jobs.

### Modeling and architecture diagrams (textual)

**Graph schema (conceptual)**

- Node labels:
  - `User(id, name, features, embedding)`
  - `Job(job_id, title, company, location, embedding, normalized_salary)`
- Relationships:
  - `(:User)-[:KNOWS]->(:User)` – follower / friend relationships.

This can be extended to additional labels such as `Company` or `Skill` if needed.

**System architecture (conceptual)**

- Services:
  - `api` (FastAPI) – exposes the HTTP API and calls Neo4j.
  - `neo4j` – graph database storing users, jobs, and relationships.
  - `tests` – container that runs the pytest suite against the same code.
- Data flow:
  - ETL scripts (`scripts/load_snap.py`, `scripts/load_jobs.py`, `scripts/create_user_embeddings.py`)
    connect to Neo4j and populate / enrich the graph.
  - The FastAPI endpoints read from Neo4j and compute recommendations on the fly.

### Testing

Run tests locally:

```bash
pytest -q
```

Or in Docker:

```bash
docker compose run --rm tests
```