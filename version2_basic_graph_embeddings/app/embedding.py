"""
Simple numeric feature projection.

Users and jobs are both represented by small numeric feature vectors
(`user_features` and `job_features`). This module only ensures that the
vectors have the same length and applies a light normalization so they
can be compared with cosine similarity.
"""

from __future__ import annotations

from typing import Iterable, List

import numpy as np


def to_numeric_vector(features: Iterable[float], dim: int = 8) -> List[float]:
    """
    Convert an iterable of numeric features into a fixed-length vector:
    - cast to float
    - truncate or pad with zeros to `dim`
    - L2-normalize when possible
    """
    vec = np.asarray(list(features), dtype=float)

    if vec.size == 0:
        return [0.0] * dim

    if vec.size >= dim:
        vec = vec[:dim]
    else:
        padded = np.zeros(dim, dtype=float)
        padded[: vec.size] = vec
        vec = padded

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()



