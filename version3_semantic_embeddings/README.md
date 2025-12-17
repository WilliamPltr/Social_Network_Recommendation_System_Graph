## Semantic job embeddings snapshot

This folder represents an iteration of the Professional Social Network Recommendation System
that introduces **semantic job embeddings**.

This snapshot:
- Keeps the core endpoints:
  - `GET /api/users/{user_id}/recommendations/friends`
  - `GET /api/users/{user_id}/recommendations/jobs`
  - `GET /api/paths/shortest`
- Introduces **semantic job embeddings** using a sentence-transformers model
  (e.g. `sentence-transformers/all-MiniLM-L6-v2`).
- Adds a simple projection from user feature vectors into the same embedding
  space as the job embeddings, so that cosine similarity can be used.

Compared to the final V4 at the repository root, this version is still a bit
simpler:
- Smaller code surface (no HTML UI, no debug endpoints, no tests).
- Job and user embeddings are computed with a lighter, more direct pipeline.


