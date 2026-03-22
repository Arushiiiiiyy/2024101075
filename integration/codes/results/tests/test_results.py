# results/tests/test_results.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import register_member
from inventory.inventory import add_car, get_car, get_cash_balance
from race_management.race_management import (
    create_race, enter_driver, assign_car, start_race,
)
from results.results import (
    record_result,
    get_result,
    list_results,
    get_winner,
    get_leaderboard,
    get_driver_results,
)


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield
    reset_database()


# ------------------------------------------------------------------
# Helpers — build a ready-to-record race in one call
# ------------------------------------------------------------------

def _setup_ongoing_race(
    race_name="Street Kings",
    driver_names=None,
    car_names=None,
):
    """
    Register drivers, add cars, create race, enter all drivers,
    assign all cars, start race. Returns (race_id, driver_ids, car_ids).
    """
    if driver_names is None:
        driver_names = ["Dom Toretto"]
    if car_names is None:
        car_names = ["Nissan Skyline"]

    driver_ids = []
    for name in driver_names:
        r = register_member(name, "driver")
        driver_ids.append(r["member_id"])

    car_ids = []
    for name in car_names:
        r = add_car(name, "good")
        car_ids.append(r["car_id"])

    race = create_race(race_name)
    race_id = race["race_id"]

    for did in driver_ids:
        enter_driver(race_id, did)
    for cid in car_ids:
        assign_car(race_id, cid)

    start_race(race_id)
    return race_id, driver_ids, car_ids


# ------------------------------------------------------------------
# record_result
# ------------------------------------------------------------------

class TestRecordResult:

    def test_record_valid_result(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        result = record_result(race_id, driver_ids, 1000.0)
        assert result["success"] is True
        assert result["result_id"] is not None

    def test_record_result_race_becomes_completed(self):
        from race_management.race_management import get_race
        race_id, driver_ids, _ = _setup_ongoing_race()
        record_result(race_id, driver_ids, 500.0)
        assert get_race(race_id)["race"]["status"] == "completed"

    def test_record_result_prize_added_to_inventory(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        record_result(race_id, driver_ids, 800.0)
        assert get_cash_balance()["cash_balance"] == 800.0

    def test_record_result_zero_prize(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        result = record_result(race_id, driver_ids, 0.0)
        assert result["success"] is True
        assert get_cash_balance()["cash_balance"] == 0.0

    def test_record_result_with_damages(self):
        race_id, driver_ids, car_ids = _setup_ongoing_race()
        record_result(race_id, driver_ids, 500.0, damages=car_ids)
        assert get_car(car_ids[0])["car"]["condition"] == "damaged"

    def test_record_result_cars_unassigned_after(self):
        race_id, driver_ids, car_ids = _setup_ongoing_race()
        record_result(race_id, driver_ids, 500.0)
        assert get_car(car_ids[0])["car"]["assigned"] is False

    def test_record_result_damaged_cars_also_unassigned(self):
        race_id, driver_ids, car_ids = _setup_ongoing_race()
        record_result(race_id, driver_ids, 500.0, damages=car_ids)
        assert get_car(car_ids[0])["car"]["assigned"] is False

    def test_record_result_multiple_drivers_rankings(self):
        race_id, driver_ids, _ = _setup_ongoing_race(
            driver_names=["Dom", "Brian", "Tej"],
            car_names=["Car A", "Car B", "Car C"],
        )
        result = record_result(race_id, driver_ids, 1500.0)
        assert result["success"] is True
        stored = get_result(race_id)["result"]
        assert stored["rankings"] == driver_ids
        assert stored["winner_id"] == driver_ids[0]

    def test_record_result_nonexistent_race(self):
        result = record_result("R999", ["M001"], 500.0)
        assert result["success"] is False
        assert "no race" in result["message"].lower()

    def test_record_result_scheduled_race_fails(self):
        register_member("Dom", "driver")
        add_car("Car A", "good")
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        # Don't start → still scheduled
        result = record_result("R001", ["M001"], 500.0)
        assert result["success"] is False
        assert "ongoing" in result["message"].lower()

    def test_record_result_empty_rankings(self):
        race_id, _, _ = _setup_ongoing_race()
        result = record_result(race_id, [], 500.0)
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_record_result_duplicate_in_rankings(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        result = record_result(race_id, [driver_ids[0], driver_ids[0]], 500.0)
        assert result["success"] is False
        assert "duplicate" in result["message"].lower()

    def test_record_result_driver_not_in_race(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        register_member("Ghost Driver", "driver")
        result = record_result(race_id, ["M002"], 500.0)
        assert result["success"] is False
        assert "not entered" in result["message"].lower()

    def test_record_result_negative_prize(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        result = record_result(race_id, driver_ids, -100.0)
        assert result["success"] is False
        assert "non-negative" in result["message"].lower()

    def test_record_result_invalid_prize_type(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        result = record_result(race_id, driver_ids, "lots")
        assert result["success"] is False

    def test_record_result_damage_car_not_in_race(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        add_car("Extra Car", "good")
        result = record_result(race_id, driver_ids, 500.0, damages=["C002"])
        assert result["success"] is False
        assert "not assigned" in result["message"].lower()

    def test_record_result_already_completed_fails(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        record_result(race_id, driver_ids, 500.0)
        result = record_result(race_id, driver_ids, 500.0)
        assert result["success"] is False


# ------------------------------------------------------------------
# get_result
# ------------------------------------------------------------------

class TestGetResult:

    def test_get_existing_result(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        record_result(race_id, driver_ids, 1000.0)
        result = get_result(race_id)
        assert result["success"] is True
        assert result["result"]["prize_money"] == 1000.0

    def test_get_result_nonexistent_race(self):
        result = get_result("R999")
        assert result["success"] is False
        assert result["result"] is None

    def test_get_result_no_result_yet(self):
        create_race("Race A")
        result = get_result("R001")
        assert result["success"] is False
        assert result["result"] is None


# ------------------------------------------------------------------
# list_results
# ------------------------------------------------------------------

class TestListResults:

    def test_list_empty(self):
        result = list_results()
        assert result["success"] is True
        assert result["results"] == []

    def test_list_one_result(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        record_result(race_id, driver_ids, 500.0)
        result = list_results()
        assert len(result["results"]) == 1

    def test_list_multiple_results(self):
        race_id_1, d1, _ = _setup_ongoing_race("Race A", ["Dom"], ["Car A"])
        race_id_2, d2, _ = _setup_ongoing_race("Race B", ["Brian"], ["Car B"])
        record_result(race_id_1, d1, 500.0)
        record_result(race_id_2, d2, 700.0)
        result = list_results()
        assert len(result["results"]) == 2


# ------------------------------------------------------------------
# get_winner
# ------------------------------------------------------------------

class TestGetWinner:

    def test_get_winner_correct(self):
        race_id, driver_ids, _ = _setup_ongoing_race(
            driver_names=["Dom", "Brian"],
            car_names=["Car A", "Car B"],
        )
        record_result(race_id, driver_ids, 1000.0)
        result = get_winner(race_id)
        assert result["success"] is True
        assert result["winner_id"] == driver_ids[0]
        assert result["winner_name"] == "Dom"

    def test_get_winner_no_result(self):
        create_race("Race A")
        result = get_winner("R001")
        assert result["success"] is False
        assert result["winner_id"] is None

    def test_get_winner_nonexistent_race(self):
        result = get_winner("R999")
        assert result["success"] is False


# ------------------------------------------------------------------
# get_leaderboard
# ------------------------------------------------------------------

class TestGetLeaderboard:

    def test_leaderboard_empty(self):
        result = get_leaderboard()
        assert result["success"] is True
        assert result["leaderboard"] == []

    def test_leaderboard_single_winner(self):
        race_id, driver_ids, _ = _setup_ongoing_race()
        record_result(race_id, driver_ids, 500.0)
        result = get_leaderboard()
        assert len(result["leaderboard"]) == 1
        assert result["leaderboard"][0]["wins"] == 1

    def test_leaderboard_sorted_by_wins(self):
        # Dom wins twice, Brian wins once
        r1, d1, _ = _setup_ongoing_race("Race A", ["Dom"], ["Car A"])
        record_result(r1, d1, 500.0)

        r2, d2, _ = _setup_ongoing_race("Race B", ["Dom2", "Brian"], ["Car B", "Car C"])
        record_result(r2, d2, 500.0)   # Dom2 wins

        r3, d3, _ = _setup_ongoing_race("Race C", ["Dom3", "Brian2"], ["Car D", "Car E"])
        record_result(r3, d3, 500.0)   # Dom3 wins

        board = get_leaderboard()["leaderboard"]
        # Top entry should have the most wins
        assert board[0]["wins"] >= board[-1]["wins"]

    def test_leaderboard_multiple_wins_same_driver(self):
        r1, d1, _ = _setup_ongoing_race("Race A", ["Dom"], ["Car A"])
        record_result(r1, d1, 500.0)
        r2, d2, _ = _setup_ongoing_race("Race B", ["Dom2"], ["Car B"])
        record_result(r2, d2, 500.0)
        board = get_leaderboard()["leaderboard"]
        assert len(board) == 2


# ------------------------------------------------------------------
# get_driver_results
# ------------------------------------------------------------------

class TestGetDriverResults:

    def test_driver_results_one_race(self):
        race_id, driver_ids, _ = _setup_ongoing_race(
            driver_names=["Dom", "Brian"],
            car_names=["Car A", "Car B"],
        )
        record_result(race_id, driver_ids, 1000.0)
        result = get_driver_results(driver_ids[0])
        assert result["success"] is True
        assert len(result["races"]) == 1
        assert result["races"][0]["position"] == 1

    def test_driver_results_position_correct(self):
        race_id, driver_ids, _ = _setup_ongoing_race(
            driver_names=["Dom", "Brian", "Tej"],
            car_names=["Car A", "Car B", "Car C"],
        )
        record_result(race_id, driver_ids, 1000.0)
        # Brian is 2nd
        result = get_driver_results(driver_ids[1])
        assert result["races"][0]["position"] == 2

    def test_driver_results_nonexistent_member(self):
        result = get_driver_results("M999")
        assert result["success"] is False

    def test_driver_results_no_races(self):
        register_member("Ghost", "driver")
        result = get_driver_results("M001")
        assert result["success"] is True
        assert result["races"] == []