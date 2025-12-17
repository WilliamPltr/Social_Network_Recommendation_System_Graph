## Minimal MVP with very simple job embeddings

This folder represents a **minimal implementation** of the Professional Social Network Recommendation System.

### Goals

- Keep the implementation **as small and simple as possible**.
- Provide the **core API endpoints**:
  - `GET /api/users/{user_id}/recommendations/friends`
  - `GET /api/users/{user_id}/recommendations/jobs`
  - `GET /api/paths/shortest`
- Use a **very simple job embedding system**:
  - Jobs and users both have a small list of **skill tags**.
  - We embed them as **binary vectors** over a tiny fixed vocabulary of skills.
  - Job recommendations are based on **cosine similarity** of these tiny vectors.

### Components

- `app/main.py` – FastAPI app and endpoints.
- `app/config.py` – Neo4j connection settings (environment variables).
- `app/db.py` – Async Neo4j driver and session management.
- `app/models.py` – Pydantic models for API responses.
- `app/recommendation.py` – Mutual-friend and job recommendation logic.
- `app/embedding.py` – Tiny helper to map skill tags to binary vectors.
- `scripts/load_jobs_simple.py` – Loads a **small hard-coded list** of jobs with skill tags into Neo4j.

There are **no tests** and **no HTML demo UI** in this version to keep the surface area minimal.


