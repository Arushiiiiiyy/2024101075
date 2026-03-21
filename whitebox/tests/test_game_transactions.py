"""White-box tests for transaction-heavy game logic."""

from unittest.mock import patch

from moneypoly.game import Game


def test_buy_property_allows_exact_balance_and_rejects_insufficient_funds():
    """Buying should succeed with exact funds and fail only when balance is lower."""
    game = Game(["A", "B"])
    buyer = game.players[0]
    prop = game.board.get_property_at(1)

    buyer.balance = prop.price
    assert game.buy_property(buyer, prop) is True
    assert prop.owner == buyer

    other_prop = game.board.get_property_at(3)
    buyer.balance = other_prop.price - 1
    assert game.buy_property(buyer, other_prop) is False