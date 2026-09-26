import pytest

from songclash.core.elo import K_FACTOR, expected_score, rating_change


def test_equal_ratings_are_a_coin_flip():
    assert expected_score(1200, 1200) == pytest.approx(0.5)
    assert rating_change(1200, 1200) == pytest.approx(K_FACTOR / 2)


def test_upsets_earn_more_points():
    assert rating_change(1100, 1300) > rating_change(1300, 1100)


def test_expected_scores_sum_to_one():
    assert expected_score(1250, 1180) + expected_score(1180, 1250) == pytest.approx(1)
