"""
Utilities to relate SNAP node features to job title embeddings.

The idea is to project the high-dimensional, sparse-like SNAP feature vectors
into the same dimensionality as the job embeddings produced by the
SentenceTransformer model used in ``scripts/load_jobs.py``.

This gives each :User a dense ``embedding`` vector that can be compared
directly (via cosine similarity) to ``Job.embedding``.
"""

from __future__ import annotations

from typing import Iterable, List

import numpy as np

# Dimensionality of the job embeddings produced by
# sentence-transformers/all-MiniLM-L6-v2
JOB_EMBED_DIM = 384


def project_features_to_embedding(
    features: Iterable[float],
    dim: int = JOB_EMBED_DIM,
) -> List[float]:
    """
    Convert a SNAP feature vector into a dense embedding with the same
    length as the job title embeddings.

    Implémentation volontairement simple pour être facile à expliquer :
    - on convertit la liste en tableau numpy
    - on applique une normalisation L2 (si possible)
    - si le vecteur est plus long que ``dim``, on garde seulement les
      ``dim`` premières valeurs
    - s'il est plus court, on complète avec des zéros
    """
    vec = np.asarray(list(features), dtype=float)

    if vec.size == 0:
        return [0.0] * dim

    # Normalisation L2 pour supprimer l'effet d'échelle.
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    if vec.size >= dim:
        return vec[:dim].tolist()

    padded = np.zeros(dim, dtype=float)
    padded[: vec.size] = vec
    return padded.tolist()

