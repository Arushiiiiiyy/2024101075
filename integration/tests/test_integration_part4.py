# tests/test_integration_part4.py
# Integration Part 4 — + Results
#
# Tests cross-module result recording scenarios.
# conftest.py handles database reset automatically.

import pytest

from registration.registration import register_member
from inventory.inventory import add_car, get_car, get_cash_balance
from race_management.race_management import (
    create_race, enter_driver, assign_car,
    start_race, get_race,
)
from results.results import (
    record_result,
    get_result,
    list_results,
    get_winner,
    get_leaderboard,
    get_driver_results,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _driver(name="Dom"):
    return register_member(name, "driver")

def _car(name="Skyline"):
    return add_car(name, "good")

def _setup_ongoing(
    driver_names=None,
    car_names=None,
    race_name="Street Kings",
):
    if driver_names is None:
        driver_names = ["Dom"]
    if car_names is None:
        car_names = ["Skyline"]

    drivers = [register_member(n, "driver") for n in driver_names]
    cars    = [add_car(n, "good") for n in car_names]
    race    = create_race(race_name)
    rid     = race["race_id"]

    for d in drivers:
        enter_driver(rid, d["member_id"])
    for c in cars:
        assign_car(rid, c["car_id"])

    start_race(rid)
    return rid, drivers, cars


# ------------------------------------------------------------------
# SCENARIO 1
# Complete a race and verify prize money updates Inventory cash.
# Modules: Results → Inventory
# ------------------------------------------------------------------

class TestPrizeMoneyUpdatesInventory:

    def test_prize_money_added_to_cash_balance(self):
        """
        WHY: Core assignment requirement — race results must
        update the cash balance in Inventory.
        """
        rid, drivers, _ = _setup_ongoing()
        record_result(rid, [d["member_id"] for d in drivers], 1000.0)
        assert get_cash_balance()["cash_balance"] == 1000.0

    def test_zero_prize_does_not_change_balance(self):
        """
        WHY: A race with no prize must not add to cash —
        verifies add_cash(0) is handled cleanly.
        """
        rid, drivers, _ = _setup_ongoing()
        record_result(rid, [d["member_id"] for d in drivers], 0.0)
        assert get_cash_balance()["cash_balance"] == 0.0

    def test_multiple_races_prize_accumulates(self):
        """
        WHY: Prize money from multiple races must stack up
        correctly in Inventory cash balance.
        """
        rid1, d1, _ = _setup_ongoing(["Dom"], ["Car A"], "Race A")
        record_result(rid1, [d1[0]["member_id"]], 500.0)

        rid2, d2, _ = _setup_ongoing(["Brian"], ["Car B"], "Race B")
        record_result(rid2, [d2[0]["member_id"]], 700.0)

        assert get_cash_balance()["cash_balance"] == 1200.0


# ------------------------------------------------------------------
# SCENARIO 2
# Race status moves to completed after result is recorded.
# Modules: Results → Race Management
# ------------------------------------------------------------------

class TestRaceCompletedAfterResult:

    def test_race_status_completed_after_record(self):
        """
        WHY: Recording a result must trigger Race Management to
        mark the race as completed — cross-module state change.
        """
        rid, drivers, _ = _setup_ongoing()
        record_result(rid, [d["member_id"] for d in drivers], 500.0)
        assert get_race(rid)["race"]["status"] == "completed"

    def test_cannot_record_result_for_scheduled_race(self):
        """
        WHY: Results can only be recorded for ongoing races —
        prevents recording before race even starts.
        """
        d = _driver()
        c = _car()
        race = create_race("Race A")
        enter_driver(race["race_id"], d["member_id"])
        assign_car(race["race_id"], c["car_id"])
        # do NOT start the race
        result = record_result(
            race["race_id"], [d["member_id"]], 500.0
        )
        assert result["success"] is False
        assert "ongoing" in result["message"].lower()

    def test_cannot_record_result_twice(self):
        """
        WHY: A completed race must not accept another result —
        prevents overwriting the official outcome.
        """
        rid, drivers, _ = _setup_ongoing()
        record_result(rid, [d["member_id"] for d in drivers], 500.0)
        result = record_result(
            rid, [d["member_id"] for d in drivers], 500.0
        )
        assert result["success"] is False


# ------------------------------------------------------------------
# SCENARIO 3
# Damaged cars in a race are updated in Inventory.
# Modules: Results → Inventory
# ------------------------------------------------------------------

class TestDamagedCarsUpdatedInInventory:

    def test_damaged_car_condition_updated(self):
        """
        WHY: Assignment requirement — if a car is damaged during
        a race, Results must update its condition in Inventory.
        """
        rid, drivers, cars = _setup_ongoing()
        cid = cars[0]["car_id"]
        record_result(
            rid,
            [d["member_id"] for d in drivers],
            500.0,
            damages=[cid],
        )
        assert get_car(cid)["car"]["condition"] == "damaged"

    def test_undamaged_car_stays_good(self):
        """
        WHY: Only explicitly damaged cars should change condition.
        Other cars in the race must stay 'good'.
        """
        rid, drivers, cars = _setup_ongoing(
            ["Dom", "Brian"], ["Car A", "Car B"]
        )
        record_result(
            rid,
            [d["member_id"] for d in drivers],
            500.0,
            damages=[cars[0]["car_id"]],
        )
        assert get_car(cars[1]["car_id"])["car"]["condition"] == "good"

    def test_all_race_cars_unassigned_after_result(self):
        """
        WHY: After a race, all cars must be freed in Inventory
        so they can be used in future races.
        """
        rid, drivers, cars = _setup_ongoing(
            ["Dom", "Brian"], ["Car A", "Car B"]
        )
        record_result(
            rid,
            [d["member_id"] for d in drivers],
            500.0,
        )
        for c in cars:
            assert get_car(c["car_id"])["car"]["assigned"] is False

    def test_damage_car_not_in_race_fails(self):
        """
        WHY: Cannot mark a car as damaged if it wasn't even
        in the race — prevents invalid inventory updates.
        """
        rid, drivers, _ = _setup_ongoing()
        extra = _car("Extra Car")
        result = record_result(
            rid,
            [d["member_id"] for d in drivers],
            500.0,
            damages=[extra["car_id"]],
        )
        assert result["success"] is False
        assert "not assigned" in result["message"].lower()


# ------------------------------------------------------------------
# SCENARIO 4
# Rankings and leaderboard work correctly across modules.
# Modules: Registration + Race Management + Results
# ------------------------------------------------------------------

class TestRankingsAndLeaderboard:

    def test_winner_is_first_in_rankings(self):
        """
        WHY: The first driver in rankings must be the winner —
        verifies Results correctly identifies the winner.
        """
        rid, drivers, _ = _setup_ongoing(
            ["Dom", "Brian", "Tej"],
            ["Car A", "Car B", "Car C"],
        )
        mid_order = [d["member_id"] for d in drivers]
        record_result(rid, mid_order, 1000.0)
        winner = get_winner(rid)
        assert winner["success"] is True
        assert winner["winner_id"] == mid_order[0]
        assert winner["winner_name"] == "Dom"

    def test_leaderboard_updates_after_race(self):
        """
        WHY: Leaderboard must reflect wins from completed races —
        tests Results feeding back into the ranking system.
        """
        rid, drivers, _ = _setup_ongoing()
        record_result(rid, [d["member_id"] for d in drivers], 500.0)
        board = get_leaderboard()["leaderboard"]
        assert len(board) == 1
        assert board[0]["wins"] == 1

    def test_driver_results_shows_position(self):
        """
        WHY: A driver must be able to look up their position
        in a race — tests cross-module data retrieval.
        """
        rid, drivers, _ = _setup_ongoing(
            ["Dom", "Brian"],
            ["Car A", "Car B"],
        )
        mid_order = [d["member_id"] for d in drivers]
        record_result(rid, mid_order, 1000.0)

        # Dom is 1st
        r1 = get_driver_results(mid_order[0])
        assert r1["races"][0]["position"] == 1

        # Brian is 2nd
        r2 = get_driver_results(mid_order[1])
        assert r2["races"][0]["position"] == 2

    def test_driver_not_in_race_results_empty(self):
        """
        WHY: A driver who hasn't raced must have no results —
        verifies clean isolation between drivers.
        """
        rid, drivers, _ = _setup_ongoing()
        record_result(rid, [d["member_id"] for d in drivers], 500.0)
        outsider = register_member("Ghost", "driver")
        r = get_driver_results(outsider["member_id"])
        assert r["races"] == []

    def test_list_results_grows_with_each_race(self):
        """
        WHY: list_results() must return all completed race
        results — verifies Results stores each one correctly.
        """
        rid1, d1, _ = _setup_ongoing(["Dom"], ["Car A"], "Race A")
        record_result(rid1, [d1[0]["member_id"]], 500.0)

        rid2, d2, _ = _setup_ongoing(["Brian"], ["Car B"], "Race B")
        record_result(rid2, [d2[0]["member_id"]], 700.0)

        assert len(list_results()["results"]) == 2