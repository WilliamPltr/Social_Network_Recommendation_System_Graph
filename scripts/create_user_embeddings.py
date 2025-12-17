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
    print(f"[EMBEDDINGS ETL] Connecting to Neo4j at: {settings.neo4j_uri}")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    # Test connection
    with driver.session() as test_session:
        test_session.run("RETURN 1").single()
    print("[EMBEDDINGS ETL] ✓ Connection successful")

    with driver.session() as session:
        # Count users with features
        count_query = (
            "MATCH (u:User) WHERE u.features IS NOT NULL "
            "RETURN count(u) AS cnt"
        )
        count_result = session.run(count_query).single()
        total_users = count_result["cnt"] if count_result else 0
        print(f"[EMBEDDINGS ETL] Found {total_users} users with features")

        # Iterate in batches over all users that have features.
        skip = 0
        processed = 0
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

            print(f"[EMBEDDINGS ETL] Processing batch: {skip} to {skip + len(records)}...")
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
                processed += 1

            skip += batch_size
            if processed % 1000 == 0:
                print(f"[EMBEDDINGS ETL] Processed {processed}/{total_users} users...")

    # Verify
    with driver.session() as verify_session:
        verify_query = (
            "MATCH (u:User) WHERE u.embedding IS NOT NULL "
            "RETURN count(u) AS cnt"
        )
        embedding_count_result = verify_session.run(verify_query).single()
        print(
            f"[EMBEDDINGS ETL] Verification: "
            f"{embedding_count_result['cnt']} users with embeddings"
        )

    driver.close()
    print(
        f"[EMBEDDINGS ETL] ✓ ETL completed successfully: "
        f"{processed} users processed"
    )


if __name__ == "__main__":
    run()

