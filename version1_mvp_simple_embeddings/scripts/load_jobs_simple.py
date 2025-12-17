"""
Very small job loader for the minimal MVP snapshot.

It creates a handful of :Job nodes with simple `skills` lists that are
used by the recommendation logic.
"""

from __future__ import annotations

from neo4j import GraphDatabase

from app.config import get_settings


SIMPLE_JOBS = [
    {
        "job_id": "job-1",
        "title": "Backend Python Engineer",
        "company": "Acme Corp",
        "location": "Remote",
        "skills": ["python", "backend"],
    },
    {
        "job_id": "job-2",
        "title": "Fullstack JavaScript Developer",
        "company": "WebWorks",
        "location": "Berlin",
        "skills": ["javascript", "frontend", "backend"],
    },
    {
        "job_id": "job-3",
        "title": "Data Scientist",
        "company": "DataLab",
        "location": "London",
        "skills": ["python", "data-science", "ml"],
    },
]


def run() -> None:
    """Insert a small set of jobs into Neo4j with simple skill tags."""
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

        print("[JOBS] Writing simple jobs...")
        for job in SIMPLE_JOBS:
            session.run(
                """
                MERGE (j:Job {job_id: $job_id})
                SET j.title = $title,
                    j.company = $company,
                    j.location = $location,
                    j.skills = $skills
                """,
                **job,
            )
        print(f"[JOBS] ✓ Inserted {len(SIMPLE_JOBS)} jobs")

    driver.close()
    print("[JOBS] ✓ Completed")


if __name__ == "__main__":
    run()



