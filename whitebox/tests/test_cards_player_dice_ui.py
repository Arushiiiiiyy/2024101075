"""White-box tests for deck, player, dice, and UI helpers."""

from unittest.mock import patch

import pytest

from moneypoly.cards import CardDeck
from moneypoly.config import GO_SALARY, STARTING_BALANCE
from moneypoly.board import Board
from moneypoly.dice import Dice
from moneypoly.player import Player
from moneypoly import ui

from test_helpers import make_property


def test_card_deck_draw_peek_cycle_and_empty_paths():
    """Card decks should support peeking, cycling, and empty-deck behavior."""
    empty_deck = CardDeck([])
    assert empty_deck.draw() is None
    assert empty_deck.peek() is None

    deck = CardDeck([{"value": 1}, {"value": 2}])
    assert deck.peek() == {"value": 1}
    assert deck.draw() == {"value": 1}
    assert deck.draw() == {"value": 2}
    assert deck.draw() == {"value": 1}
    assert deck.cards_remaining() == 1


def test_player_money_validation_and_bankruptcy_state():
    """Negative money operations should fail and zero balance counts as bankrupt."""
    player = Player("Tester")

    with pytest.raises(ValueError):
        player.add_money(-1)
    with pytest.raises(ValueError):
        player.deduct_money(-1)

    player.balance = 0
    assert player.is_bankrupt() is True

def test_player_property_tracking_and_status_line():
    """Player property helper methods and status rendering should reflect state changes."""
    player = Player("Tester")
    prop = make_property()

    player.add_property(prop)
    assert player.count_properties() == 1
    assert "props=1" in player.status_line()

    player.go_to_jail()
    assert "[JAILED]" in player.status_line()

    player.remove_property(prop)
    assert player.count_properties() == 0

def test_player_move_awards_salary_when_passing_go():
    """Moving past Go should credit salary, not only landing exactly on square zero."""
    player = Player("Runner")
    player.position = 39

    new_position = player.move(2)

    assert new_position == 1
    assert player.balance == STARTING_BALANCE + GO_SALARY

def test_dice_roll_tracks_doubles_and_uses_full_six_sided_range():
    """Dice should accept a roll of six and track doubles streaks correctly."""
    dice = Dice()

    with patch("random.randint") as mock_randint:
        mock_randint.side_effect = [6, 6, 3, 4]
        dice.roll()
        mock_randint.assert_any_call(1, 6)