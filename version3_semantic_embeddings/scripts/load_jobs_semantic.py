"""
Semantic job loader for this semantic-embedding snapshot.

It loads LinkedIn-like jobs from a Hugging Face dataset and embeds them
with a sentence-transformers model.
"""

from __future__ import annotations

from typing import List

from datasets import load_dataset
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

from app.config import get_settings


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_job_text(title: str, company: str | None, location: str | None) -> str:
    """Concatenate fields into a single text to embed."""
    parts: List[str] = [title]
    if company:
        parts.append(company)
    if location:
        parts.append(location)
    return " - ".join(parts)


def run(limit: int | None = 2000) -> None:
    """Main job ingestion logic for this snapshot."""
    settings = get_settings()
    print(f"[JOBS] Connecting to Neo4j at: {settings.neo4j_uri}")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    print("[JOBS] Loading job listings from Hugging Face...")
    ds = load_dataset("datastax/linkedin_job_listings", split="train")
    print(f"[JOBS] Dataset loaded: {len(ds)} jobs")
    if limit is not None:
        ds = ds.select(range(min(limit, len(ds))))

    print(f"[JOBS] Loading sentence transformer model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("[JOBS] ✓ Model loaded")

    titles: List[str] = []
    meta: List[dict] = []
    for idx, row in enumerate(ds):
        job_id = str(row.get("job_id") or row.get("id") or row.get("url"))
        title = row.get("job_title") or row.get("title") or "Unknown title"
        company = row.get("company_name") or row.get("company") or None
        location = row.get("job_location") or row.get("location") or None

        text = build_job_text(title, company, location)
        titles.append(text)
        meta.append(
            {
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
            },
        )
        if (idx + 1) % 1000 == 0:
            print(f"[JOBS] Processed {idx + 1} jobs...")

    print(f"[JOBS] Computing embeddings for {len(titles)} jobs...")
    embeddings = model.encode(titles, convert_to_numpy=True).tolist()
    print(f"[JOBS] ✓ Computed {len(embeddings)} embeddings")

    with driver.session() as session:
        print("[JOBS] Creating Job constraint...")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE")
        print("[JOBS] ✓ Constraint created")

        print("[JOBS] Writing jobs to Neo4j...")
        job_count = 0
        for emb, info in zip(embeddings, meta, strict=False):
            session.run(
                """
                MERGE (j:Job {job_id: $job_id})
                SET j.title = $title,
                    j.company = $company,
                    j.location = $location,
                    j.embedding = $embedding
                """,
                job_id=info["job_id"],
                title=info["title"],
                company=info["company"],
                location=info["location"],
                embedding=emb,
            )
            job_count += 1
            if job_count % 1000 == 0:
                print(f"[JOBS] Written {job_count} jobs...")

        print(f"[JOBS] ✓ Written {job_count} Job nodes")

    driver.close()
    print("[JOBS] ✓ ETL completed successfully")


if __name__ == "__main__":
    run()



