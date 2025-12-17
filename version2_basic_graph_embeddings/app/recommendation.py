"""
Core recommendation logic for this numeric-feature-based snapshot:
- Friend recommendations via mutual connections.
- Job recommendations using simple numeric feature vectors.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from neo4j import AsyncSession

from .embedding import to_numeric_vector


async def get_friend_recommendations(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[Tuple[int, str | None, int]]:
    """
    Recommend friends based on the number of mutual connections.

    Returns a list of (user_id, name, mutual_count).
    """
    query = """
    MATCH (u:User {id: $user_id})-[:KNOWS]->(:User)-[:KNOWS]->(rec:User)
    WHERE rec.id <> $user_id AND NOT (u)-[:KNOWS]->(rec)
    RETURN rec.id AS id, rec.name AS name, count(*) AS mutuals
    ORDER BY mutuals DESC
    LIMIT $limit
    """
    result = await session.run(query, user_id=user_id, limit=limit)
    records = await result.data()
    return [(record["id"], record.get("name"), record["mutuals"]) for record in records]


async def get_job_recommendations(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[Tuple[str, str, str | None, str | None, float]]:
    """
    Recommend jobs based on small numeric feature vectors.

    Assumes:
      - Each :User has a `features` property: list[float]
      - Each :Job has a `features` property: list[float]
    We map both to fixed-length numeric vectors and use cosine similarity.
    """
    user_query = """
    MATCH (u:User {id: $user_id})
    RETURN u.features AS features
    """
    result = await session.run(user_query, user_id=user_id)
    record = await result.single()
    if record is None or record["features"] is None:
        return []

    user_vec = np.array(to_numeric_vector(record["features"]), dtype=float)
    if user_vec.size == 0:
        return []

    jobs_query = """
    MATCH (j:Job)
    WHERE j.features IS NOT NULL
    RETURN j.job_id AS job_id,
           j.title AS title,
           j.company AS company,
           j.location AS location,
           j.features AS features
    """
    result = await session.run(jobs_query)

    scores: List[Tuple[str, str, str | None, str | None, float]] = []
    async for rec in result:
        job_vec = np.array(to_numeric_vector(rec["features"]), dtype=float)
        if job_vec.size != user_vec.size or job_vec.size == 0:
            continue

        denom = np.linalg.norm(user_vec) * np.linalg.norm(job_vec)
        if denom == 0:
            continue
        score = float(np.dot(user_vec, job_vec) / denom)

        if score <= 0:
            continue

        scores.append(
            (
                rec["job_id"],
                rec["title"],
                rec.get("company"),
                rec.get("location"),
                score,
            ),
        )

    scores.sort(key=lambda x: x[-1], reverse=True)
    return scores[:limit]



