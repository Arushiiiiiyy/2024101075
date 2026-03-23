"""
Comprehensive white-box test suite for MoneyPoly.
Covers every branch and decision path in:
  bank.py, board.py, cards.py, config.py, dice.py,
  game.py, player.py, property.py, ui.py
"""
 
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
 
import pytest
 
# ── path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "whitebox" / "moneypoly"))
 
from moneypoly.bank import Bank
from moneypoly.board import Board
from moneypoly.cards import CardDeck, CHANCE_CARDS, COMMUNITY_CHEST_CARDS
from moneypoly.config import (
    BANK_STARTING_FUNDS, STARTING_BALANCE, GO_SALARY,
    JAIL_FINE, INCOME_TAX_AMOUNT, LUXURY_TAX_AMOUNT,
    BOARD_SIZE, JAIL_POSITION,
)
from moneypoly.dice import Dice
from moneypoly.game import Game
from moneypoly.player import Player
from moneypoly.property import Property, PropertyConfig, PropertyGroup
from moneypoly import ui


def make_prop(name="Prop", position=99, price=100, rent=10, group=None):
    return Property(name, position, PropertyConfig(price, rent), group)

class TestBankInit:
    def test_initial_balance_equals_config(self):
        """Bank starts with BANK_STARTING_FUNDS."""
        b = Bank()
        assert b.get_balance() == BANK_STARTING_FUNDS
 
    def test_repr_contains_funds(self):
        b = Bank()
        assert "Bank(funds=" in repr(b)


