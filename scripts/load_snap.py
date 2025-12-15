"""
ETL script to load SNAP GitHub social network data into Neo4j.

It expects the following files at the project root:
- musae_git_edges.csv
- musae_git_features.json
- musae_git_target.csv

This script:
- Creates :User nodes with `id`, `name`, and `features` (numeric vector)
- Creates :KNOWS relationships from the edges file
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd
from neo4j import GraphDatabase

from app.config import get_settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_edges() -> pd.DataFrame:
    """Load follower edges."""
    path = PROJECT_ROOT / "musae_git_edges.csv"
    df = pd.read_csv(path)
    # Standard SNAP format: columns id_1, id_2 with integer IDs.
    df = df.rename(columns={"id_1": "src", "id_2": "dst"})
    return df[["src", "dst"]]


def load_targets() -> pd.DataFrame:
    """Load node targets (id -> name/label)."""
    path = PROJECT_ROOT / "musae_git_target.csv"
    return pd.read_csv(path)


def load_features() -> Dict[str, List[int]]:
    """Load SNAP node features from JSON."""
    path = PROJECT_ROOT / "musae_git_features.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run():
    """Main ETL entrypoint."""
    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    edges = load_edges()
    targets = load_targets()
    features = load_features()

    # Normalize feature vectors into fixed-length lists.
    # musae_git_features.json maps node_id -> {feature_index: value, ...}
    # In the simplified case described, features are integer codes; we treat them as a dense list.
    max_len = max(len(v) for v in features.values())

    def to_dense(vec: List[int]) -> List[int]:
        dense = list(vec)
        if len(dense) < max_len:
            dense.extend([0] * (max_len - len(dense)))
        return dense

    dense_features = {int(k): to_dense(v) for k, v in features.items()}

    with driver.session() as session:
        # Create unique constraint.
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")

        # Create users.
        for _, row in targets.iterrows():
            node_id = int(row["id"])
            name = row.get("name") or row.get("target") or str(node_id)
            feats = dense_features.get(node_id, [0] * max_len)
            session.run(
                """
                MERGE (u:User {id: $id})
                SET u.name = $name,
                    u.features = $features
                """,
                id=node_id,
                name=name,
                features=feats,
            )

        # Create KNOWS edges (followers).
        for _, row in edges.iterrows():
            src = int(row["src"])
            dst = int(row["dst"])
            session.run(
                """
                MATCH (a:User {id: $src}), (b:User {id: $dst})
                MERGE (a)-[:KNOWS]->(b)
                """,
                src=src,
                dst=dst,
            )

    driver.close()


if __name__ == "__main__":
    run()


