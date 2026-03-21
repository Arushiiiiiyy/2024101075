"""White-box tests for bank behavior."""

import pytest

from moneypoly.bank import Bank
from moneypoly.config import STARTING_BALANCE
from moneypoly.player import Player


def test_bank_payout_and_loan_paths_update_funds():
    """Successful loans should pay the player and reduce bank reserves."""
    bank = Bank()
    player = Player("Borrower")
    starting_funds = bank.get_balance()

    assert bank.pay_out(0) == 0
    with pytest.raises(ValueError):
        bank.pay_out(starting_funds + 1)

    bank.give_loan(player, 100)

    assert player.balance == STARTING_BALANCE + 100
    assert bank.get_balance() == starting_funds - 100
