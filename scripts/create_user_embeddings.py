"""
Offline script to create user embeddings from SNAP feature vectors.

This script establishes a concrete relation between:
- SNAP node ``features`` stored on :User nodes; and
- Job title embeddings stored on :Job nodes.

For each :User with a ``features`` property, we compute a dense embedding
using ``project_features_to_embedding`` so that:

    User.embedding  <-->  Job.embedding

live in the same dimensional space and can be compared directly via cosine
similarity in the job recommendation endpoint.
"""

from __future__ import annotations

from neo4j import GraphDatabase

from app.config import get_settings
from app.embedding import project_features_to_embedding


def run(batch_size: int = 1000) -> None:
    """Compute and persist embeddings for all users based on their features."""
    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    with driver.session() as session:
        # Iterate in batches over all users that have features.
        skip = 0
        while True:
            result = session.run(
                """
                MATCH (u:User)
                WHERE u.features IS NOT NULL
                RETURN u.id AS user_id, u.features AS features
                SKIP $skip LIMIT $limit
                """,
                skip=skip,
                limit=batch_size,
            )
            records = list(result)
            if not records:
                break

            for record in records:
                user_id = record["user_id"]
                features = record["features"]
                embedding = project_features_to_embedding(features)

                session.run(
                    """
                    MATCH (u:User {id: $user_id})
                    SET u.embedding = $embedding
                    """,
                    user_id=user_id,
                    embedding=embedding,
                )

            skip += batch_size

    driver.close()


if __name__ == "__main__":
    run()


