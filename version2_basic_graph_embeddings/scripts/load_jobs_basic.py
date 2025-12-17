"""
Basic job loader for the numeric-feature-based snapshot.

It inserts a small number of :Job nodes with numeric `features` vectors
that are used for recommendation.
"""

from __future__ import annotations

from typing import List

from neo4j import GraphDatabase

from app.config import get_settings


BASIC_JOBS: List[dict] = [
    {
        "job_id": "job-1",
        "title": "Backend Engineer",
        "company": "Acme Corp",
        "location": "Remote",
        # Example features: [backend, frontend, data, ml, seniority]
        "features": [1.0, 0.2, 0.1, 0.0, 0.6],
    },
    {
        "job_id": "job-2",
        "title": "Data Scientist",
        "company": "DataLab",
        "location": "London",
        "features": [0.2, 0.1, 1.0, 0.8, 0.7],
    },
    {
        "job_id": "job-3",
        "title": "Fullstack Developer",
        "company": "WebWorks",
        "location": "Berlin",
        "features": [0.8, 0.8, 0.3, 0.0, 0.5],
    },
]


def run() -> None:
    """Insert a small set of jobs into Neo4j with numeric feature vectors."""
    settings = get_settings()
    print(f"[JOBS] Connecting to Neo4j at: {settings.neo4j_uri}")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    with driver.session() as session:
        print("[JOBS] Creating Job constraint...")
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE",
        )
        print("[JOBS] ✓ Constraint created")

        print("[JOBS] Writing basic jobs...")
        for job in BASIC_JOBS:
            session.run(
                """
                MERGE (j:Job {job_id: $job_id})
                SET j.title = $title,
                    j.company = $company,
                    j.location = $location,
                    j.features = $features
                """,
                **job,
            )
        print(f"[JOBS] ✓ Inserted {len(BASIC_JOBS)} jobs")

    driver.close()
    print("[JOBS] ✓ Completed")


if __name__ == "__main__":
    run()



