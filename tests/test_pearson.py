"""
Unit tests for the Pearson correlation implementation used in
the 'people you may know' feature.
"""

import numpy as np

from app.recommendation import pearson_correlation


def test_pearson_basic_positive():
    vec_a = np.array([1, 2, 3, 4], dtype=float)
    vec_b = np.array([2, 4, 6, 8], dtype=float)
    score = pearson_correlation(vec_a, vec_b)
    assert np.isclose(score, 1.0)


def test_pearson_basic_negative():
    vec_a = np.array([1, 2, 3, 4], dtype=float)
    vec_b = np.array([4, 3, 2, 1], dtype=float)
    score = pearson_correlation(vec_a, vec_b)
    assert np.isclose(score, -1.0)


def test_pearson_zero_variance_returns_zero():
    vec_a = np.array([1, 1, 1, 1], dtype=float)
    vec_b = np.array([1, 2, 3, 4], dtype=float)
    score = pearson_correlation(vec_a, vec_b)
    assert score == 0.0


def test_pearson_size_mismatch_raises():
    vec_a = np.array([1, 2], dtype=float)
    vec_b = np.array([1, 2, 3], dtype=float)
    try:
        _ = pearson_correlation(vec_a, vec_b)
        assert False, "Expected ValueError"
    except ValueError:
        assert True


