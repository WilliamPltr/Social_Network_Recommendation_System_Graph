## Basic graph and feature-based embeddings

This folder represents an iteration of the Professional Social Network Recommendation System
that introduces **numeric feature-based embeddings**.

This snapshot:
- Exposes the core endpoints:
  - `GET /api/users/{user_id}/recommendations/friends`
  - `GET /api/users/{user_id}/recommendations/jobs`
  - `GET /api/paths/shortest`
- Uses **numeric feature vectors** for users and jobs instead of only binary skill tags.
  - User features come from a simplified representation of the SNAP features.
  - Job features are small numeric vectors that roughly encode skills and seniority.
- Job recommendations are based on **cosine similarity** over these numeric vectors.

This version is intentionally still **lighter** than the final V4:
- No Hugging Face datasets.
- No sentence-transformers.
- No HTML demo UI and no tests.


