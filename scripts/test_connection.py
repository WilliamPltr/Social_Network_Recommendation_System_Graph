"""
Simple script to test Neo4j connection and verify data exists.
Run this to diagnose connection issues.
"""

import sys
import traceback

from neo4j import GraphDatabase

from app.config import get_settings


def test_connection():
    """Test Neo4j connection and show basic stats."""
    settings = get_settings()
    print(f"Testing connection to: {settings.neo4j_uri}")
    print(f"User: {settings.neo4j_user}")
    print(f"Password: {'*' * len(settings.neo4j_password)}")
    print()

    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

        with driver.session() as session:
            # Test basic connection
            result = session.run("RETURN 1 AS test")
            record = result.single()
            print("✓ Connection successful!")

            # Count users
            result = session.run("MATCH (u:User) RETURN count(u) AS cnt")
            record = result.single()
            user_count = record["cnt"] if record else 0
            print(f"✓ Users in database: {user_count}")

            # Count jobs
            result = session.run("MATCH (j:Job) RETURN count(j) AS cnt")
            record = result.single()
            job_count = record["cnt"] if record else 0
            print(f"✓ Jobs in database: {job_count}")

            # Count KNOWS relationships
            result = session.run("MATCH ()-[r:KNOWS]->() RETURN count(r) AS cnt")
            record = result.single()
            knows_count = record["cnt"] if record else 0
            print(f"✓ KNOWS relationships: {knows_count}")

            # Count users with features
            features_query = (
                "MATCH (u:User) WHERE u.features IS NOT NULL "
                "RETURN count(u) AS cnt"
            )
            result = session.run(features_query)
            record = result.single()
            features_count = record["cnt"] if record else 0
            print(f"✓ Users with features: {features_count}")

            # Count users with embeddings
            embedding_query = (
                "MATCH (u:User) WHERE u.embedding IS NOT NULL "
                "RETURN count(u) AS cnt"
            )
            result = session.run(embedding_query)
            record = result.single()
            embedding_count = record["cnt"] if record else 0
            print(f"✓ Users with embeddings: {embedding_count}")

            # Count jobs with embeddings
            job_embedding_query = (
                "MATCH (j:Job) WHERE j.embedding IS NOT NULL "
                "RETURN count(j) AS cnt"
            )
            result = session.run(job_embedding_query)
            record = result.single()
            job_embedding_count = record["cnt"] if record else 0
            print(f"✓ Jobs with embeddings: {job_embedding_count}")

            # Sample users
            result = session.run("MATCH (u:User) RETURN u.id AS id, u.name AS name LIMIT 5")
            records = result.data()
            if records:
                print("\nSample users:")
                for r in records:
                    print(f"  - id: {r['id']}, name: {r.get('name', 'N/A')}")

        driver.close()
        print("\n✓ All checks passed!")

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    test_success = test_connection()  # pylint: disable=invalid-name
    sys.exit(0 if test_success else 1)

