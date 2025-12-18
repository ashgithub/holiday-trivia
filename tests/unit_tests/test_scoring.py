import sys
sys.path.insert(0, '/Users/ashish/work/code/python/all-hands-game')

import pytest
from backend.main import compute_numeric_score, compute_semantic_score, cluster_word_cloud_answers, extract_number_from_text

def test_compute_numeric_score():
    # Exact match always gets full points
    assert compute_numeric_score("150", "150") == 30

    # Non-exact matches get temporary closeness scores (will be adjusted by proportional scoring)
    # These scores are based on closeness but won't be the final scores
    score_155 = compute_numeric_score("150", "155")  # diff=5
    score_152 = compute_numeric_score("150", "152")  # diff=2
    score_100 = compute_numeric_score("150", "100")  # diff=50

    # Closer answers should get higher temporary scores than farther ones
    assert score_152 > score_155  # diff=2 should be closer than diff=5
    assert score_155 > score_100  # diff=5 should be closer than diff=50

    # Very close should get reasonable scores
    assert score_152 > 20  # diff=2 should be quite high
    assert score_155 > 5   # diff=5 should be moderate

    # Very far should get low scores
    assert score_100 < 5   # diff=50 should be very low

    # Non-numeric should get 0
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

def test_extract_number_from_text():
    # Test direct numbers
    assert extract_number_from_text("150") == 150.0
    assert extract_number_from_text("75.5") == 75.5

    # Test written numbers
    assert extract_number_from_text("eight") == 8.0
    assert extract_number_from_text("seven") == 7.0
    assert extract_number_from_text("twenty") == 20.0

    # Test phrases with numbers
    assert extract_number_from_text("eight days") == 8.0
    assert extract_number_from_text("seven days") == 7.0
    assert extract_number_from_text("one thousand five hundred") == 1500.0

    # Test invalid inputs
    assert extract_number_from_text("hello world") is None
    assert extract_number_from_text("") is None
    assert extract_number_from_text("   ") is None

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
