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
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    ds = load_dataset("datastax/linkedin_job_listings", split="train")
    if limit is not None:
        ds = ds.select(range(min(limit, len(ds))))

    model = SentenceTransformer(MODEL_NAME)

    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE")

        titles: List[str] = []
        meta: List[dict] = []
        for row in ds:
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

        embeddings = model.encode(titles, convert_to_numpy=True).tolist()

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

    driver.close()


if __name__ == "__main__":
    run()


