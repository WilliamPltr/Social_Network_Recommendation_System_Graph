"""
ETL script to load LinkedIn job listings and push them to Neo4j with embeddings.

Data source:
    from datasets import load_dataset
    ds = load_dataset("datastax/linkedin_job_listings")

For each job, we:
- Build a text from title + company + location
- Compute a dense embedding using sentence-transformers
- Create :Job nodes with `job_id`, `title`, `company`, and `embedding`

These embeddings are later used in the API for job recommendations.
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


def run(limit: int | None = 5000) -> None:
    """Main job ingestion logic."""
    settings = get_settings()
    print(f"[JOBS ETL] Connecting to Neo4j at: {settings.neo4j_uri}")
    
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        # Test connection
        with driver.session() as test_session:
            test_session.run("RETURN 1").single()
        print("[JOBS ETL] ✓ Connection successful")
    except Exception as e:
        print(f"[JOBS ETL] ✗ Connection failed: {e}")
        raise

    print("[JOBS ETL] Loading LinkedIn job listings from Hugging Face...")
    ds = load_dataset("datastax/linkedin_job_listings", split="train")
    print(f"[JOBS ETL] Dataset loaded: {len(ds)} jobs")
    if limit is not None:
        ds = ds.select(range(min(limit, len(ds))))

    print(f"[JOBS ETL] Loading sentence transformer model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("[JOBS ETL] ✓ Model loaded")

    with driver.session() as session:
        print("[JOBS ETL] Creating Job constraint...")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE")
        print("[JOBS ETL] ✓ Constraint created")

        print("[JOBS ETL] Processing jobs and computing embeddings...")
        titles: List[str] = []
        meta: List[dict] = []
        for idx, row in enumerate(ds):
            job_id = str(row.get("job_id") or row.get("id") or row.get("url"))
            title = row.get("job_title") or row.get("title") or "Unknown title"
            company = row.get("company_name") or row.get("company") or None
            location = row.get("job_location") or row.get("location") or None
            # URL de l'offre d'emploi
            url = row.get("job_posting_url") or row.get("url") or row.get("job_url")
            # Salaire normalisé (champ numérique si disponible)
            normalized_salary = row.get("normalized_salary")

            text = build_job_text(title, company, location)
            titles.append(text)
            meta.append(
                {
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": url,
                    "normalized_salary": normalized_salary,
                },
            )
            if (idx + 1) % 1000 == 0:
                print(f"[JOBS ETL] Processed {idx + 1} jobs...")

        print(f"[JOBS ETL] Computing embeddings for {len(titles)} jobs...")
        embeddings = model.encode(titles, convert_to_numpy=True).tolist()
        print(f"[JOBS ETL] ✓ Computed {len(embeddings)} embeddings")

        print("[JOBS ETL] Writing jobs to Neo4j...")
        job_count = 0
        for emb, info in zip(embeddings, meta, strict=False):
            session.run(
                """
                MERGE (j:Job {job_id: $job_id})
                SET j.title = $title,
                    j.company = $company,
                    j.location = $location,
                    j.job_posting_url = $url,
                    j.normalized_salary = $normalized_salary,
                    j.embedding = $embedding
                """,
                job_id=info["job_id"],
                title=info["title"],
                company=info["company"],
                location=info["location"],
                url=info["url"],
                normalized_salary=info["normalized_salary"],
                embedding=emb,
            )
            job_count += 1
            if job_count % 1000 == 0:
                print(f"[JOBS ETL] Written {job_count} jobs...")

        print(f"[JOBS ETL] ✓ Written {job_count} Job nodes")

    # Verify
    with driver.session() as verify_session:
        job_count_result = verify_session.run("MATCH (j:Job) RETURN count(j) AS cnt").single()
        job_embedding_result = verify_session.run("MATCH (j:Job) WHERE j.embedding IS NOT NULL RETURN count(j) AS cnt").single()
        print(f"[JOBS ETL] Verification: {job_count_result['cnt']} jobs, {job_embedding_result['cnt']} with embeddings")

    driver.close()
    print("[JOBS ETL] ✓ ETL completed successfully")


if __name__ == "__main__":
    run()


