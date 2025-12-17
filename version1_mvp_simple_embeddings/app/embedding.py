"""
Tiny helper to convert skill tags into simple binary vectors for this MVP.

The idea:
- We keep a **very small vocabulary** of skills.
- Each user and job has a list of skill tags.
- We represent them as binary vectors over that vocabulary.
"""

from __future__ import annotations

from typing import Iterable, List

import numpy as np


DEFAULT_SKILL_VOCAB = [
    "python",
    "java",
    "javascript",
    "data-science",
    "backend",
    "frontend",
    "ml",
    "devops",
]


def skills_to_vector(skills: Iterable[str], vocab: list[str] | None = None) -> List[float]:
    """
    Map a list of skill tags to a binary vector over the given vocabulary.
    """
    if vocab is None:
        vocab = DEFAULT_SKILL_VOCAB

    skill_set = {s.lower() for s in skills}
    vec = np.zeros(len(vocab), dtype=float)
    for idx, token in enumerate(vocab):
        if token in skill_set:
            vec[idx] = 1.0
    return vec.tolist()



