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

def test_bank_collect_summary_and_repr(capsys):
    """Bank bookkeeping helpers should report totals and reserve values correctly."""
    bank = Bank()
    bank.collect(200)
    bank.summary()
    output = capsys.readouterr().out

    assert "Total collected" in output
    assert bank.loan_count() == 0
    assert bank.total_loans_issued() == 0
    assert "Bank(funds=" in repr(bank)

def test_bank_collect_ignores_negative_amounts():
    """Negative amounts passed to collect should not reduce bank funds."""
    bank = Bank()
    starting_funds = bank.get_balance()

    bank.collect(-100)

    assert bank.get_balance() == starting_funds

def test_give_loan_respects_available_funds():
    """Bank should not issue loans exceeding available reserves."""
    bank = Bank()
    player = Player("Borrower")
    with pytest.raises(ValueError):
        bank.give_loan(player, bank.get_balance() + 1)