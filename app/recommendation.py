"""
Core recommendation logic: mutual friends, people you may know, and job matching.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from neo4j import AsyncSession


async def get_friend_recommendations(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[Tuple[int, str | None, int]]:
    """
    Recommend friends based on number of mutual connections.

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


async def get_friend_counts(
    session: AsyncSession,
    user_id: int,
) -> Tuple[int, int]:
    """
    Return (number_of_direct_friends, number_of_friend_of_friend_candidates)
    for a given user.
    """
    # Nombre d'amis directs.
    direct_query = """
    MATCH (u:User {id: $user_id})-[:KNOWS]->(f:User)
    RETURN count(DISTINCT f) AS cnt
    """
    res1 = await session.run(direct_query, user_id=user_id)
    rec1 = await res1.single()
    direct_friends = rec1["cnt"] if rec1 is not None else 0

    # Nombre de candidats "amis d'amis" (amis de mes amis qui ne sont pas déjà mes amis).
    fof_query = """
    MATCH (u:User {id: $user_id})-[:KNOWS]->(:User)-[:KNOWS]->(rec:User)
    WHERE rec.id <> $user_id AND NOT (u)-[:KNOWS]->(rec)
    RETURN count(DISTINCT rec) AS cnt
    """
    res2 = await session.run(fof_query, user_id=user_id)
    rec2 = await res2.single()
    friends_of_friends = rec2["cnt"] if rec2 is not None else 0

    return int(direct_friends), int(friends_of_friends)


def pearson_correlation(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Compute Pearson correlation coefficient between two 1D numpy arrays.
    """
    if vec_a.size != vec_b.size or vec_a.size == 0:
        raise ValueError("Vectors must be non-empty and of the same size")

    if np.all(vec_a == vec_a[0]) or np.all(vec_b == vec_b[0]):
        # Zero variance -> correlation undefined; return 0 as neutral.
        return 0.0

    return float(np.corrcoef(vec_a, vec_b)[0, 1])


async def get_people_you_may_know(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[Tuple[int, str | None, float]]:
    """
    Recommend "people you may know" based on Pearson correlation between
    SNAP feature vectors.

    Assumes each :User node has a numeric feature vector stored as `features`
    (list of floats or ints with fixed length).
    """
    # Fetch target user features.
    user_query = """
    MATCH (u:User {id: $user_id})
    RETURN u.name AS name, u.features AS features
    """
    result = await session.run(user_query, user_id=user_id)
    record = await result.single()
    if record is None or record["features"] is None:
        return []

    target_name = record.get("name")
    target_vec = np.array(record["features"], dtype=float)

    # Fetch candidate users and their features.
    candidates_query = """
    MATCH (other:User)
    WHERE other.id <> $user_id
      AND other.features IS NOT NULL
    RETURN other.id AS id, other.name AS name, other.features AS features
    """
    result = await session.run(candidates_query, user_id=user_id)
    correlations: List[Tuple[int, str | None, float]] = []
    async for rec in result:
        candidate_vec = np.array(rec["features"], dtype=float)
        if candidate_vec.size != target_vec.size:
            continue

        score = pearson_correlation(target_vec, candidate_vec)
        if not np.isnan(score):
            correlations.append((rec["id"], rec.get("name"), score))

    # Trier par corrélation décroissante: de 1 vers -1, puis prendre les 10 premiers.
    correlations.sort(key=lambda x: x[2], reverse=True)
    return correlations[:limit]


async def get_job_recommendations(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[Tuple[str, str, str | None, str | None, float | None, float]]:
    """
    Recommend jobs based on precomputed embeddings.

    Assumes:
      - Each :User has a `embedding` property: list[float]
      - Each :Job has a `embedding` property: list[float]
    Uses cosine similarity between embeddings.
    """
    # Fetch user embedding.
    user_query = """
    MATCH (u:User {id: $user_id})
    RETURN u.embedding AS embedding
    """
    result = await session.run(user_query, user_id=user_id)
    record = await result.single()
    if record is None or record["embedding"] is None:
        return []

    user_vec = np.array(record["embedding"], dtype=float)
    if user_vec.size == 0:
        return []

    # Fetch job embeddings.
    jobs_query = """
    MATCH (j:Job)
    WHERE j.embedding IS NOT NULL
    RETURN j.job_id AS job_id,
           j.title AS title,
           j.company AS company,
           j.location AS location,
           j.job_posting_url AS job_posting_url,
           j.normalized_salary AS normalized_salary,
           j.embedding AS embedding
    """
    result = await session.run(jobs_query)

    scores: List[Tuple[str, str, str | None, str | None, float | None, float]] = []
    async for rec in result:
        job_vec = np.array(rec["embedding"], dtype=float)
        if job_vec.size != user_vec.size or job_vec.size == 0:
            continue

        # Cosine similarity.
        denom = np.linalg.norm(user_vec) * np.linalg.norm(job_vec)
        if denom == 0:
            continue
        score = float(np.dot(user_vec, job_vec) / denom)

        # On ne garde que les scores positifs (corrélation / similarité utile).
        if score <= 0:
            continue

        scores.append(
            (
                rec["job_id"],             # 0
                rec["title"],              # 1
                rec.get("company"),        # 2
                rec.get("location"),       # 3
                rec.get("normalized_salary"),  # 4
                score,                     # 5
            ),
        )

    # Trier par score de similarité décroissant (dernier élément du tuple).
    scores.sort(key=lambda x: x[-1], reverse=True)
    return scores[:limit]


