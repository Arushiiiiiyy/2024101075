"""White-box tests for game flow, cards, jail, and winner selection."""

from unittest.mock import patch

from moneypoly.config import GO_SALARY, JAIL_FINE, STARTING_BALANCE
from moneypoly.game import Game


def test_handle_jail_turn_uses_card_when_available():
    """A jail-free card should release the player immediately when chosen."""
    game = Game(["A", "B"])
    player = game.players[0]
    player.go_to_jail()
    player.jail.get_out_of_jail_cards = 1

    with patch("moneypoly.ui.confirm", side_effect=[True]), patch.object(
        game.dice, "roll", return_value=5
    ), patch.object(game, "_move_and_resolve") as resolve:
        game._handle_jail_turn(player)

    assert player.jail.in_jail is False
    assert player.jail.get_out_of_jail_cards == 0
    resolve.assert_called_once_with(player, 5)

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
    """Paying to leave jail should actually reduce the player's balance."""
    game = Game(["A", "B"])
    player = game.players[0]
    player.go_to_jail()
    player.balance = 100

    with patch("moneypoly.ui.confirm", side_effect=[True]), patch.object(
        game.dice, "roll", return_value=4
    ), patch.object(game, "_move_and_resolve"):
        game._handle_jail_turn(player)

    assert player.balance == 100 - JAIL_FINE
    assert player.jail.in_jail is False


def test_card_move_to_collects_salary_when_wrapping_and_handles_property_tile():
    """Move-to cards should award Go salary when wrapping and resolve property destinations."""
    game = Game(["A", "B"])
    player = game.players[0]
    player.position = 36

    with patch.object(game, "_handle_property_tile") as handle_property:
        game._card_move_to(player, 39)
        handle_property.assert_called_once()
    assert player.position == 39

    player.position = 36
    original_balance = player.balance
    game._card_move_to(player, 0)
    assert player.position == 0
    assert player.balance == original_balance + GO_SALARY

def test_move_and_resolve_covers_special_tiles_and_cards():
    """Move resolution should execute tax, jail, free parking, and card branches."""
    game = Game(["A", "B"])
    player = game.players[0]

    with patch.object(game, "_check_bankruptcy") as check_bankruptcy:
        player.position = 3
        game._move_and_resolve(player, 1)
        assert player.balance == STARTING_BALANCE - 200
        check_bankruptcy.assert_called_with(player)

    with patch.object(game, "_check_bankruptcy"):
        player.position = 37
        game._move_and_resolve(player, 1)
        assert player.balance == STARTING_BALANCE - 275

    with patch.object(game, "_check_bankruptcy"):
        player.position = 29
        game._move_and_resolve(player, 1)
        assert player.jail.in_jail is True

    player.jail.in_jail = False
    with patch.object(game, "_check_bankruptcy"), patch.object(
        game, "_apply_card"
    ) as apply_card:
        player.position = 6
        game._move_and_resolve(player, 1)
        apply_card.assert_called_once()

    with patch.object(game, "_check_bankruptcy"), patch.object(
        game, "_apply_card"
    ) as apply_card:
        player.position = 16
        game._move_and_resolve(player, 1)
        apply_card.assert_called_once()

    with patch.object(game, "_check_bankruptcy"):
        player.position = 19
        game._move_and_resolve(player, 1)
        assert player.position == 20

def test_apply_card_dispatches_core_actions():
    """Card dispatch should cover collect, pay, jail, jail-free, and player-to-player collection."""
    game = Game(["A", "B", "C"])
    player = game.players[0]
    others = game.players[1:]

    player.balance = 100
    with patch.object(game.bank, "pay_out", return_value=50):
        game._apply_card(player, {"description": "collect", "action": "collect", "value": 50})
    assert player.balance == 150

    game._apply_card(player, {"description": "pay", "action": "pay", "value": 25})
    assert player.balance == 125

    game._apply_card(player, {"description": "jail free", "action": "jail_free", "value": 0})
    assert player.jail.get_out_of_jail_cards == 1

    for other in others:
        other.balance = 40
    game._apply_card(
        player,
        {"description": "birthday", "action": "birthday", "value": 10},
    )
    assert player.balance == 145
    assert [other.balance for other in others] == [30, 30]

    game._apply_card(player, {"description": "jail", "action": "jail", "value": 0})
    assert player.jail.in_jail is True

def test_apply_card_ignores_none_and_unknown_actions():
    """Card application should safely ignore missing cards and unsupported actions."""
    game = Game(["A", "B"])
    player = game.players[0]
    starting_balance = player.balance

    game._apply_card(player, None)
    game._apply_card(player, {"description": "noop", "action": "unknown", "value": 99})

    assert player.balance == starting_balance

def test_check_bankruptcy_releases_assets_and_removes_player():
    """Bankruptcy should clear ownership and remove the player from the game."""
    game = Game(["A", "B"])
    player = game.players[0]
    prop = game.board.get_property_at(1)
    prop.owner = player
    prop.is_mortgaged = True
    player.add_property(prop)
    player.balance = 0

    game._check_bankruptcy(player)

    assert player.is_eliminated is True
    assert prop.owner is None
    assert prop.is_mortgaged is False
    assert player not in game.players

def test_current_player_advance_turn_and_play_turn_branches():
    """Turn helpers should rotate players and handle jail, doubles, and normal turns."""
    game = Game(["A", "B"])

    assert game.current_player() == game.players[0]
    game.advance_turn()
    assert game.current_player() == game.players[1]

    game.state.current_index = 0
    player = game.players[0]
    player.go_to_jail()
    with patch.object(game, "_handle_jail_turn") as jail_turn, patch.object(
        game, "advance_turn"
    ) as advance_turn:
        game.play_turn()
        jail_turn.assert_called_once_with(player)
        advance_turn.assert_called_once()

    player.jail.in_jail = False
    with patch.object(game.dice, "roll", return_value=4), patch.object(
        game.dice, "describe", return_value="2 + 2 = 4 (DOUBLES)"
    ), patch.object(game.dice, "is_doubles", return_value=True), patch.object(
        game, "_move_and_resolve"
    ) as move_and_resolve, patch.object(game, "advance_turn") as advance_turn:
        game.dice.doubles_streak = 1
        game.play_turn()
        move_and_resolve.assert_called_once_with(player, 4)
        advance_turn.assert_not_called()

    with patch.object(game.dice, "roll", return_value=5), patch.object(
        game.dice, "describe", return_value="2 + 3 = 5"
    ), patch.object(game.dice, "is_doubles", return_value=False), patch.object(
        game, "_move_and_resolve"
    ) as move_and_resolve, patch.object(game, "advance_turn") as advance_turn:
        game.dice.doubles_streak = 0
        game.play_turn()
        move_and_resolve.assert_called_once_with(player, 5)
        advance_turn.assert_called_once()

def test_play_turn_sends_player_to_jail_after_three_consecutive_doubles():
    """Rolling three doubles in a row should send the player to jail immediately."""
    game = Game(["A", "B"])
    player = game.players[0]

    with patch.object(game.dice, "roll", return_value=6), patch.object(
        game.dice, "describe", return_value="3 + 3 = 6 (DOUBLES)"
    ), patch.object(game, "advance_turn") as advance_turn, patch.object(
        game, "_move_and_resolve"
    ) as move_and_resolve:
        game.dice.doubles_streak = 3
        game.play_turn()

    assert player.jail.in_jail is True
    move_and_resolve.assert_not_called()
    advance_turn.assert_called_once()