"""White-box tests for game flow, cards, jail, and winner selection."""

from unittest.mock import patch

from moneypoly.config import GO_SALARY, JAIL_FINE, STARTING_BALANCE
from moneypoly.game import Game


def test_handle_jail_turn_forces_release_after_three_turns():
    """A player who stays in jail long enough should be released after the mandatory fine."""
    game = Game(["A", "B"])
    player = game.players[0]
    player.go_to_jail()
    player.balance = 100
    player.jail.jail_turns = 2

    with patch("moneypoly.ui.confirm", side_effect=[False, False]), patch.object(
        game.dice, "roll", return_value=6
    ), patch.object(game, "_move_and_resolve"):
        game._handle_jail_turn(player)

    assert player.balance == 100 - JAIL_FINE
    assert player.jail.in_jail is False
    assert player.jail.jail_turns == 0


def test_find_winner_returns_highest_net_worth_player():
    """The winner should be the richest remaining player, not the poorest one."""
    game = Game(["A", "B", "C"])
    game.players[0].balance = 100
    game.players[1].balance = 600
    game.players[2].balance = 300

    assert game.find_winner() == game.players[1]

def test_handle_jail_turn_deducts_fine_when_player_pays_voluntarily():
    """Paying the jail fine voluntarily should deduct money from the player."""
    game = Game(["A", "B"])
    player = game.players[0]
    player.go_to_jail()
    player.balance = 100

    with patch("moneypoly.ui.confirm", side_effect=[True]), \
         patch.object(game.dice, "roll", return_value=6), \
         patch.object(game, "_move_and_resolve"):
        game._handle_jail_turn(player)

    assert player.balance == 100 - JAIL_FINE
    assert player.jail.in_jail is False

