"""
User feature projection to the semantic job embedding space.

Jobs are embedded with a sentence-transformers model.
User nodes keep a `features` vector (e.g. derived from SNAP).
This module provides a simple projection from user features to the same
dimension as the job embeddings so that cosine similarity can be used.
"""

from __future__ import annotations

from typing import Iterable, List

import numpy as np


JOB_EMBED_DIM = 384


def project_features_to_embedding(
    features: Iterable[float],
    dim: int = JOB_EMBED_DIM,
) -> List[float]:
    """
    Convert a user feature vector into a dense embedding with the same
    dimensionality as the job embeddings.

    Implementation is intentionally simple:
    - cast to float
    - L2-normalize when possible
    - truncate or pad with zeros to `dim`
    """
    vec = np.asarray(list(features), dtype=float)

    if vec.size == 0:
        return [0.0] * dim

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    if vec.size >= dim:
        return vec[:dim].tolist()

    padded = np.zeros(dim, dtype=float)
    padded[: vec.size] = vec
    return padded.tolist()



