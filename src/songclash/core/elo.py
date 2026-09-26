"""Elo rating math (the system used for chess rankings)."""

K_FACTOR = 32


def expected_score(rating: float, opponent: float) -> float:
    """Probability, from 0 to 1, that ``rating`` beats ``opponent``."""
    return 1 / (1 + 10 ** ((opponent - rating) / 400))


def rating_change(winner: float, loser: float, k: float = K_FACTOR) -> float:
    """Points the winner gains (and the loser loses). Upsets earn more."""
    return k * (1 - expected_score(winner, loser))
