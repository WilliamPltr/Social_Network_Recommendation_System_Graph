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
    print(f"[SNAP ETL] Connecting to Neo4j at: {settings.neo4j_uri}")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    # Test connection
    with driver.session() as test_session:
        test_session.run("RETURN 1").single()
    print("[SNAP ETL] ✓ Connection successful")

    print("[SNAP ETL] Loading CSV/JSON files...")
    edges = load_edges()
    targets = load_targets()
    features = load_features()
    print(
        f"[SNAP ETL] Loaded: {len(edges)} edges, "
        f"{len(targets)} targets, {len(features)} feature vectors"
    )

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
        print("[SNAP ETL] Creating User constraint...")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        print("[SNAP ETL] ✓ Constraint created")

        # Create users.
        print(f"[SNAP ETL] Creating {len(targets)} User nodes...")
        user_count = 0
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
            user_count += 1
            if user_count % 1000 == 0:
                print(f"[SNAP ETL] Created {user_count} users...")

        print(f"[SNAP ETL] ✓ Created {user_count} User nodes")

        # Create KNOWS edges (followers).
        print(f"[SNAP ETL] Creating {len(edges)} KNOWS relationships...")
        edge_count = 0
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
            edge_count += 1
            if edge_count % 10000 == 0:
                print(f"[SNAP ETL] Created {edge_count} relationships...")

        print(f"[SNAP ETL] ✓ Created {edge_count} KNOWS relationships")

    # Verify
    with driver.session() as verify_session:
        user_query = "MATCH (u:User) RETURN count(u) AS cnt"
        user_count_result = verify_session.run(user_query).single()
        knows_query = "MATCH ()-[r:KNOWS]->() RETURN count(r) AS cnt"
        knows_count_result = verify_session.run(knows_query).single()
        print(
            f"[SNAP ETL] Verification: {user_count_result['cnt']} users, "
            f"{knows_count_result['cnt']} KNOWS relationships"
        )

    driver.close()
    print("[SNAP ETL] ✓ ETL completed successfully")


if __name__ == "__main__":
    run()

