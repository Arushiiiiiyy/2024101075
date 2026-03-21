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


def test_pay_rent_transfers_money_to_owner_and_skips_mortgaged_property():
    """Rent should move money between players, except when the property is mortgaged."""
    game = Game(["Tenant", "Owner"])
    tenant, owner = game.players
    prop = game.board.get_property_at(1)
    other_brown = game.board.get_property_at(3)
    prop.owner = owner
    other_brown.owner = tenant
    owner.add_property(prop)

    tenant.balance = 100
    owner.balance = 200
    game.pay_rent(tenant, prop)
    assert tenant.balance == 98
    assert owner.balance == 202

    prop.is_mortgaged = True
    tenant.balance = 100
    owner.balance = 200
    game.pay_rent(tenant, prop)
    assert tenant.balance == 100
    assert owner.balance == 200