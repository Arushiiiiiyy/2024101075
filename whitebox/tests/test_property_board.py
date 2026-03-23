"""White-box tests for property and board helpers."""

from moneypoly.board import Board
from moneypoly.player import Player

from moneypoly.property import PropertyGroup, Property, PropertyConfig
from test_helpers import make_property
from moneypoly.game import Game
def test_property_group_requires_full_ownership_for_bonus_rent():
    """A full group bonus should only apply when one player owns every property."""
    group = PropertyGroup("Brown", "brown")
    owner = Player("Owner")
    rival = Player("Rival")
    first = make_property("A", 1, rent=20, group=group)
    second = make_property("B", 3, rent=20, group=group)

    first.owner = owner
    second.owner = rival

    assert group.all_owned_by(owner) is False
    assert first.get_rent() == 20


def test_property_get_rent_returns_zero_when_mortgaged():
    """Mortgaged properties should not charge rent."""
    prop = make_property(rent=25)
    prop.is_mortgaged = True

    assert prop.get_rent() == 0


def test_property_mortgage_and_unmortgage_paths():
    """Mortgage helpers should return correct values and state transitions."""
    prop = make_property(price=120)

    assert prop.mortgage() == 60
    assert prop.is_mortgaged is True
    assert prop.mortgage() == 0
    assert prop.unmortgage() == 66
    assert prop.is_mortgaged is False
    assert prop.unmortgage() == 0


def test_property_availability_and_group_helpers():
    """Property helper methods should reflect owner state and group counts."""
    group = PropertyGroup("Blue", "blue")
    owner = Player("Owner")
    prop = make_property(group=group)

    assert prop.is_available() is True
    assert group.size() == 1
    assert group.get_owner_counts() == {}

    prop.owner = owner
    assert prop.is_available() is False
    assert group.get_owner_counts() == {owner: 1}


def test_board_tile_type_and_purchase_checks_cover_branches():
    """Board helpers should distinguish special, property, blank, and mortgaged states."""
    board = Board()
    prop = board.get_property_at(1)

    assert board.get_tile_type(0) == "go"
    assert board.get_tile_type(1) == "property"
    assert board.get_tile_type(12) == "blank"
    assert board.is_purchasable(0) is False
    assert board.is_purchasable(1) is True

    prop.is_mortgaged = True
    assert board.is_purchasable(1) is False

    prop.is_mortgaged = False
    prop.owner = Player("Owner")
    assert board.is_purchasable(1) is False


def test_board_special_tile_and_ownership_lists():
    """Board list helpers should track owned and unowned properties correctly."""
    board = Board()
    owner = Player("Owner")
    prop = board.get_property_at(1)
    prop.owner = owner

    assert board.is_special_tile(0) is True
    assert board.is_special_tile(1) is False
    assert board.properties_owned_by(owner) == [prop]
    assert prop not in board.unowned_properties()


def test_property_init_without_group():
    """Branch: group is None during Property initialization."""
    prop = Property("Orphan", 99, PropertyConfig(100, 10))
    assert prop.group is None
    assert prop.get_rent() == 10 # Should not crash looking for group multiplier

def test_property_group_all_owned_by_none():
    """Branch: player is None -> return False."""
    group = PropertyGroup("Test", "black")
    prop = Property("P1", 1, PropertyConfig(100, 10), group)
    assert group.all_owned_by(None) is False

def test_board_is_purchasable_none_property():
    """Branch: prop is None -> return False."""
    board = Board()
    assert board.is_purchasable(99) is False # Pos 99 does not exist

def test_unmortgage_truncation_boundary():
    """Boundary Case: Verifies int() truncation on 110% unmortgage cost."""
    # If price is $101, mortgage is $50. Unmortgage is 50 * 1.1 = 55.0 -> 55
    # If price is $103, mortgage is $51. Unmortgage is 51 * 1.1 = 56.1 -> 56
    from moneypoly.property import Property, PropertyConfig
    prop = Property("WeirdPrice", 99, PropertyConfig(103, 10))
    
    prop.mortgage()
    assert prop.mortgage_value == 51
    
    cost = prop.unmortgage()
    assert cost == 56

def test_property_is_purchasable_returns_false_if_no_property_exists():
    """Branch: is_purchasable() called on a blank tile or special tile."""
    game = Game(["A"])
    # Position 12 is a blank tile. Position 0 is Go.
    assert game.board.is_purchasable(12) is False
    assert game.board.is_purchasable(0) is False


def test_mortgaged_property_rent_in_full_group():
    """
    Branch State: Player owns full group. One is mortgaged, one is active.
    Rent on the active one must still be doubled!
    """
    game = Game(["Owner", "Tenant"])
    owner, tenant = game.players
    group = game.board.groups["dark_blue"]
    p_mortgaged, p_active = group.properties[0], group.properties[1]
    
    p_mortgaged.owner = owner; owner.add_property(p_mortgaged)
    p_active.owner = owner; owner.add_property(p_active)
    
    p_mortgaged.mortgage()
    
    # The active property must recognize the group is fully owned and charge double
    assert p_active.get_rent() == p_active.base_rent * 2
    # The mortgaged one must safely return 0
    assert p_mortgaged.get_rent() == 0
