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
