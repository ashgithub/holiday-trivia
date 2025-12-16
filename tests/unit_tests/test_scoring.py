import sys
sys.path.insert(0, '/Users/ashish/work/code/python/all-hands-game')

import pytest
from backend.main import compute_numeric_score, compute_semantic_score, cluster_word_cloud_answers

def test_compute_numeric_score():
    # Exact match
    assert compute_numeric_score("150", "150") == 30
    # Close: diff=5, tolerance=1.5, so partial score 10
    assert compute_numeric_score("150", "155") == 10
    # Closer: diff=2, not within 1.5 tolerance, so decay to 22
    assert compute_numeric_score("150", "152") == 22
    # Far: diff=50, decay to 0
    assert compute_numeric_score("150", "100") == 0
    # Non-numeric
    assert compute_numeric_score("150", "abc") == 0

def test_compute_semantic_score():
    score, sim = compute_semantic_score("pig", "pig")
    assert score >= 29  # Floating point, likely 29
    assert sim >= 0.96

    # Use a pair with high sim
    score, sim = compute_semantic_score("pig", "hog")
    assert score > 20  # Expect high partial
    assert sim > 0.7

    score, sim = compute_semantic_score("pig", "elephant")
    assert score == 0
    assert sim < 0.7

def test_cluster_word_cloud_answers():
    answers = [
        (1, "eggnog"),
        (2, "eggnog latte"),
        (3, "hot chocolate"),
        (4, "eggnog")
    ]
    cluster_map, answer_to_cluster = cluster_word_cloud_answers(answers)
    # Expect 2 clusters: eggnog group (size 3), hot chocolate (1)
    assert len(cluster_map) == 2
    # Check rep and size for largest
    sizes = [len(c["users"]) for c in cluster_map.values()]
    assert max(sizes) == 3
    # Scores would be 30 * (3/4) = 22.5 ~ 23 for group
    for cid, cluster in cluster_map.items():
        if len(cluster["users"]) == 3:
            assert "eggnog" in cluster["rep"]
