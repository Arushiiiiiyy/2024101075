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


def test_mortgage_and_unmortgage_cover_owner_and_affordability_branches():
    """Mortgage helpers should enforce ownership and keep state when redemption fails."""
    game = Game(["A", "B"])
    owner, other = game.players
    prop = game.board.get_property_at(1)
    prop.owner = owner
    owner.add_property(prop)

    assert game.mortgage_property(other, prop) is False
    assert game.mortgage_property(owner, prop) is True
    assert prop.is_mortgaged is True
    assert game.mortgage_property(owner, prop) is False

    owner.balance = 0
    assert game.unmortgage_property(owner, prop) is False
    assert prop.is_mortgaged is True

    owner.balance = int(prop.mortgage_value * 1.1)
    assert game.unmortgage_property(owner, prop) is True
    assert prop.is_mortgaged is False
    assert game.unmortgage_property(owner, prop) is False

def test_trade_requires_ownership_and_affordability_and_pays_seller():
    """Trades should fail on invalid states and credit the seller on success."""
    game = Game(["Seller", "Buyer"])
    seller, buyer = game.players
    prop = game.board.get_property_at(1)

    assert game.trade(seller, buyer, prop, 50) is False

    prop.owner = seller
    seller.add_property(prop)
    buyer.balance = 40
    assert game.trade(seller, buyer, prop, 50) is False

    seller.balance = 100
    buyer.balance = 200
    assert game.trade(seller, buyer, prop, 50) is True
    assert seller.balance == 150
    assert buyer.balance == 150
    assert prop.owner == buyer