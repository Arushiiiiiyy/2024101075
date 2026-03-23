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

def test_handle_property_tile_branches(monkeypatch):
    """Property tile handling should cover buy, auction, pass, owned, and rent branches."""
    game = Game(["A", "B"])
    player, other = game.players
    prop = game.board.get_property_at(1)

    monkeypatch.setattr("builtins.input", lambda _prompt: "b")
    with patch.object(game, "buy_property") as buy_property:
        game._handle_property_tile(player, prop)
        buy_property.assert_called_once_with(player, prop)

    monkeypatch.setattr("builtins.input", lambda _prompt: "a")
    with patch.object(game, "auction_property") as auction_property:
        game._handle_property_tile(player, prop)
        auction_property.assert_called_once_with(prop)

    monkeypatch.setattr("builtins.input", lambda _prompt: "s")
    game._handle_property_tile(player, prop)

    prop.owner = player
    player.add_property(prop)
    game._handle_property_tile(player, prop)

    prop.owner = other
    with patch.object(game, "pay_rent") as pay_rent:
        game._handle_property_tile(player, prop)
        pay_rent.assert_called_once_with(player, prop)

def test_auction_property_covers_no_bid_and_winning_bid_paths(monkeypatch):
    """Auctions should leave property unowned when everyone passes and sell to top bidder otherwise."""
    game = Game(["A", "B"])
    prop = game.board.get_property_at(1)

    bids = iter([0, 0])
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: next(bids))
    game.auction_property(prop)
    assert prop.owner is None

    prop.owner = None
    bids = iter([20, 40])
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: next(bids))
    game.auction_property(prop)
    assert prop.owner == game.players[1]

def test_trade_rejects_negative_cash_amount():
    """A trade with a negative cash amount should be rejected safely."""
    game = Game(["Seller", "Buyer"])
    seller, buyer = game.players
    prop = game.board.get_property_at(1)
    prop.owner = seller
    seller.add_property(prop)

    original_seller_balance = seller.balance
    original_buyer_balance = buyer.balance

    assert game.trade(seller, buyer, prop, -50) is False
    assert seller.balance == original_seller_balance
    assert buyer.balance == original_buyer_balance
    assert prop.owner == seller


def test_buy_property_rejects_already_owned_property():
    """Buying an already-owned property should fail without overwriting ownership."""
    game = Game(["A", "B"])
    buyer, original_owner = game.players
    prop = game.board.get_property_at(1)
    prop.owner = original_owner
    original_owner.add_property(prop)

    buyer.balance = 1000
    assert game.buy_property(buyer, prop) is False
    assert prop.owner == original_owner


def test_trade_completes_property_group_immediate_rent_double():
    """Edge Case: Trading a property instantly alters the rent calculations for the whole group."""
    game = Game(["Tycoon", "Pauper"])
    tycoon, pauper = game.players
    group = game.board.groups["brown"]
    p1, p2 = group.properties[0], group.properties[1] # Mediterranean & Baltic
    p1.owner = tycoon; tycoon.add_property(p1)
    p2.owner = pauper; pauper.add_property(p2)
    
    assert p1.get_rent() == p1.base_rent # Normal rent
    
    # Execute trade
    game.trade(pauper, tycoon, p2, 0)
    
    # Rent should immediately reflect the FULL_GROUP_MULTIPLIER
    assert p1.get_rent() == p1.base_rent * 2
    assert p2.get_rent() == p2.base_rent * 2


def test_pay_rent_to_bankrupt_owner_is_handled_safely():
    """Edge Case: Rent payment triggered for an owner who just hit $0 but hasn't been purged yet."""
    game = Game(["Tenant", "Zombie"])
    tenant, zombie = game.players
    prop = game.board.get_property_at(1)
    
    prop.owner = zombie
    zombie.add_property(prop)
    zombie.balance = 0 # Zombie is technically bankrupt
    
    tenant_start = tenant.balance
    game.pay_rent(tenant, prop)
    
    # Tenant still pays. Zombie still collects. 
    # (Zombie might survive bankruptcy if this happens before their turn!)
    assert tenant.balance < tenant_start
    assert zombie.balance > 0