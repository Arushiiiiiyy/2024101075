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

def test_interactive_menu_exits_on_zero():
    """Branch: choice == 0 breaks the while True loop."""
    game = Game(["P1", "P2"])
    player = game.players[0]
    
    with patch("moneypoly.ui.safe_int_input", return_value=0):
        # If the loop doesn't break, this will hang indefinitely
        game.interactive_menu(player)

def test_interactive_menu_routing(monkeypatch):
    """Branch: covers routing to standings, board ownership, and loans."""
    game = Game(["P1", "P2"])
    player = game.players[0]
    
    # Simulate choosing 1, 2, 6, loan amount 500, then 0 to exit
    inputs = iter([1, 2, 6, 500, 0])
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: next(inputs))
    
    with patch("moneypoly.ui.print_standings") as mock_standings, \
         patch("moneypoly.ui.print_board_ownership") as mock_board, \
         patch.object(game.bank, "give_loan") as mock_loan:
         
        game.interactive_menu(player)
        
        mock_standings.assert_called_once()
        mock_board.assert_called_once()
        mock_loan.assert_called_once_with(player, 500)

def test_menu_mortgage_no_properties_branch(capsys):
    """Branch: early return if player has no mortgageable properties."""
    game = Game(["P1"])
    player = game.players[0]
    # Player has no properties
    game._menu_mortgage(player)
    assert "No properties available to mortgage." in capsys.readouterr().out

def test_menu_unmortgage_success_branch(monkeypatch):
    """Branch: successful selection and unmortgaging of a property."""
    game = Game(["P1"])
    player = game.players[0]
    prop = game.board.get_property_at(1)
    
    # Setup: Player owns a mortgaged property
    prop.owner = player
    prop.is_mortgaged = True
    player.add_property(prop)
    player.balance = 5000 # Ensure they can afford it
    
    # Select option 1 (Fix: using a lambda instead of return_value)
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: 1)
    
    with patch.object(game, "unmortgage_property") as mock_unmortgage:
        game._menu_unmortgage(player)
        mock_unmortgage.assert_called_once_with(player, prop)

def test_check_bankruptcy_index_wrap_around():
    """Branch: self.state.current_index >= len(self.players) inside bankruptcy check."""
    game = Game(["A", "B", "C"])
    game.state.current_index = 2 
    player_c = game.players[2]
    player_c.balance = 0
    
    game._check_bankruptcy(player_c)
    
    assert game.state.current_index == 0

def test_auction_property_bid_too_low(monkeypatch):
    """Branch: bid < min_required -> continue loop."""
    game = Game(["A", "B"])
    prop = game.board.get_property_at(1)
    
    # A bids 10, B tries to bid 15 (min raise is 10, so 20 required)
    bids = iter([10, 15, 0, 0]) 
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: next(bids))
    game.auction_property(prop)
    
    assert prop.owner == game.players[0] # A wins because B's bid was rejected

def test_auction_property_cannot_afford(monkeypatch):
    """Branch: bid > player.balance -> continue loop."""
    game = Game(["A", "B"])
    prop = game.board.get_property_at(1)
    game.players[0].balance = 50
    
    
    bids = iter([100, 0])
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: next(bids))
    game.auction_property(prop)
    
    assert prop.owner is None # A's bid rejected, property remains unowned

def test_pay_rent_unowned_property():
    """Branch: prop.owner is None -> early return."""
    game = Game(["A"])
    player = game.players[0]
    prop = game.board.get_property_at(1) # Unowned by default
    
    original_balance = player.balance
    game.pay_rent(player, prop)
    assert player.balance == original_balance 

def test_unmortgage_property_wrong_owner():
    """Branch: prop.owner != player inside unmortgage -> return False."""
    game = Game(["A", "B"])
    owner, other = game.players
    prop = game.board.get_property_at(1)
    prop.owner = owner
    prop.is_mortgaged = True
    
    assert game.unmortgage_property(other, prop) is False


def test_menus_ignore_out_of_bounds_selections(monkeypatch):
    """Branch: index is not within the 0 to len() bounds for mortgage menus."""
    game = Game(["Alice"])
    p1 = game.players[0]
    dummy_prop = game.board.get_property_at(1)
    dummy_prop.owner = p1
    p1.add_property(dummy_prop)
    
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: 500)
    
    # If the out-of-bounds guard fails, these will throw IndexError crashes
    game._menu_mortgage(p1)
    game._menu_unmortgage(p1)
    game._menu_trade(p1)
    
    assert dummy_prop.is_mortgaged is False

def test_interactive_menu_rejects_negative_loan(monkeypatch):
    """Branch: amount <= 0 inside interactive_menu option 6."""
    game = Game(["Bob"])
    p1 = game.players[0]
    initial_cash = p1.balance

    user_inputs = iter([6, -500, 0])
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: next(user_inputs))
    
    game.interactive_menu(p1)
    
    # Balance must remain exactly the same
    assert p1.balance == initial_cash

def test_game_loop_terminates_on_max_turns_limit(monkeypatch, capsys):
    """Branch: while loop terminates because turn_number >= MAX_TURNS."""
    from moneypoly.config import MAX_TURNS
    game = Game(["P1", "P2"])
    game.state.turn_number = MAX_TURNS
    monkeypatch.setattr("moneypoly.ui.print_banner", lambda *args: None)
    
    game.run()
    
    output = capsys.readouterr().out
    assert "wins with a net worth" in output

def test_bankruptcy_avoids_crash_if_player_already_removed():
    """Branch: if player in self.players evaluates to False during bankruptcy."""
    game = Game(["Ghost"])
    ghost_player = game.players[0]
    ghost_player.balance = 0
    game.players.clear()
    game._check_bankruptcy(ghost_player)
    assert ghost_player.is_eliminated is True

def test_card_collect_from_all_strict_boundaries():
    """Branch Boundary: other.balance == value, and other.balance == value - 1."""
    game = Game(["Collector", "Exactly_50", "Exactly_49"])
    collector, p_50, p_49 = game.players

    collector.balance = 0
    p_50.balance = 50  # Exactly enough
    p_49.balance = 49  
    game._apply_card(collector, {"description": "bday", "action": "birthday", "value": 50})
    assert p_50.balance == 0   # Paid exactly all they had
    assert p_49.balance == 49  # Guard protected them; they paid nothing
    assert collector.balance == 50 


def test_auction_accepts_all_in_exact_balance_bid(monkeypatch):
    """Branch Boundary: bid == player.balance (accepted)."""
    game = Game(["P1", "P2"])
    p1, p2 = game.players
    prop = game.board.get_property_at(1)
    
    # P1 bids everything they have. P2 passes.
    all_in_amount = p1.balance
    bids = iter([all_in_amount, 0])
    monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda *_args, **_kwargs: next(bids))
    
    game.auction_property(prop)
    
    assert prop.owner == p1
    assert p1.balance == 0

def test_trade_rejects_self_trade():
    """Trade should fail if buyer and seller are the same player."""
    game = Game(["Solo"])
    player = game.players[0]
    prop = game.board.get_property_at(1)
    prop.owner = player
    player.add_property(prop)
    
    success = game.trade(player, player, prop, 100)
    
    assert success is False

def test_find_winner_tied_net_worth():
    """Edge Case: find_winner() when multiple players have identical net worths."""
    game = Game(["Twin1", "Twin2"])
    t1, t2 = game.players
    t1.balance = 5000
    t2.balance = 5000
    
    winner = game.find_winner()
    # max() returns the first encountered item in a tie. 
    assert winner == t1 

def test_advance_turn_with_only_one_player():
    """Edge Case: advance_turn modulo math when the player list shrinks to 1."""
    game = Game(["Survivor", "Loser"])
    survivor, loser = game.players
    game.players.remove(loser) # Simulate elimination
    
    game.state.current_index = 0
    game.advance_turn()
    
    # (0 + 1) % 1 == 0. It should seamlessly give the turn back to the survivor.
    assert game.state.current_index == 0

def test_collect_from_all_skips_exactly_broke_players():
    """Boundary Case: Card collection against players with exactly $0."""
    game = Game(["Collector", "Broke1", "Broke2"])
    collector, b1, b2 = game.players
    b1.balance = 0
    b2.balance = 0
    collector.balance = 0
    
    game._card_collect_from_others(collector, 50)
    
    # Collector gets nothing because the logic guards against balance < value
    assert collector.balance == 0
    assert b1.balance == 0
             