# race_management/tests/test_race_management.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import register_member, deactivate_member
from inventory.inventory import add_car, update_car_condition, set_car_assigned
from race_management.race_management import (
    create_race,
    get_race,
    list_races,
    enter_driver,
    assign_car,
    start_race,
    complete_race,
    get_race_drivers,
    get_race_cars,
    list_available_drivers,
    list_available_cars,
)


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield
    reset_database()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_driver(name="Dom Toretto"):
    return register_member(name, "driver")

def _make_mechanic(name="Letty Ortiz"):
    return register_member(name, "mechanic")

def _make_car(name="Nissan Skyline"):
    return add_car(name, "good")

def _make_race(name="Street Kings"):
    return create_race(name)


# ------------------------------------------------------------------
# create_race
# ------------------------------------------------------------------

class TestCreateRace:

    def test_create_valid_race(self):
        result = create_race("Street Kings")
        assert result["success"] is True
        assert result["race_id"] == "R001"

    def test_create_race_default_status_scheduled(self):
        create_race("Street Kings")
        race = get_race("R001")["race"]
        assert race["status"] == "scheduled"

    def test_create_race_empty_drivers_and_cars(self):
        create_race("Street Kings")
        race = get_race("R001")["race"]
        assert race["driver_ids"] == []
        assert race["car_ids"] == []

    def test_create_race_empty_name(self):
        result = create_race("")
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_create_race_whitespace_name(self):
        result = create_race("   ")
        assert result["success"] is False

    def test_create_race_duplicate_name(self):
        create_race("Street Kings")
        result = create_race("Street Kings")
        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    def test_create_race_duplicate_name_case_insensitive(self):
        create_race("street kings")
        result = create_race("STREET KINGS")
        assert result["success"] is False

    def test_create_multiple_races_unique_ids(self):
        r1 = create_race("Race Alpha")
        r2 = create_race("Race Beta")
        assert r1["race_id"] != r2["race_id"]


# ------------------------------------------------------------------
# get_race
# ------------------------------------------------------------------

class TestGetRace:

    def test_get_existing_race(self):
        create_race("Midnight Run")
        result = get_race("R001")
        assert result["success"] is True
        assert result["race"]["name"] == "Midnight Run"

    def test_get_nonexistent_race(self):
        result = get_race("R999")
        assert result["success"] is False
        assert result["race"] is None

    def test_get_race_id_case_insensitive(self):
        create_race("Midnight Run")
        result = get_race("r001")
        assert result["success"] is True


# ------------------------------------------------------------------
# list_races
# ------------------------------------------------------------------

class TestListRaces:

    def test_list_empty(self):
        result = list_races()
        assert result["success"] is True
        assert result["races"] == []

    def test_list_all(self):
        create_race("Race A")
        create_race("Race B")
        result = list_races()
        assert len(result["races"]) == 2

    def test_list_filter_scheduled(self):
        create_race("Race A")
        create_race("Race B")
        result = list_races(status_filter="scheduled")
        assert len(result["races"]) == 2

    def test_list_filter_invalid_status(self):
        result = list_races(status_filter="unknown")
        assert result["success"] is False

    def test_list_filter_completed(self):
        _make_driver()
        _make_car()
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        start_race("R001")
        complete_race("R001")
        result = list_races(status_filter="completed")
        assert len(result["races"]) == 1


# ------------------------------------------------------------------
# enter_driver
# ------------------------------------------------------------------

class TestEnterDriver:

    def test_enter_valid_driver(self):
        _make_driver("Dom")
        create_race("Race A")
        result = enter_driver("R001", "M001")
        assert result["success"] is True

    def test_enter_driver_updates_race(self):
        _make_driver("Dom")
        create_race("Race A")
        enter_driver("R001", "M001")
        assert "M001" in get_race("R001")["race"]["driver_ids"]

    def test_enter_nonexistent_member(self):
        create_race("Race A")
        result = enter_driver("R001", "M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_enter_inactive_driver(self):
        _make_driver("Dom")
        deactivate_member("M001")
        create_race("Race A")
        result = enter_driver("R001", "M001")
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_enter_non_driver_role(self):
        _make_mechanic("Letty")
        create_race("Race A")
        result = enter_driver("R001", "M001")
        assert result["success"] is False
        assert "only drivers" in result["message"].lower()

    def test_enter_driver_duplicate(self):
        _make_driver("Dom")
        create_race("Race A")
        enter_driver("R001", "M001")
        result = enter_driver("R001", "M001")
        assert result["success"] is False
        assert "already entered" in result["message"].lower()

    def test_enter_driver_nonexistent_race(self):
        _make_driver("Dom")
        result = enter_driver("R999", "M001")
        assert result["success"] is False

    def test_enter_driver_ongoing_race_fails(self):
        _make_driver("Dom")
        _make_car()
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        start_race("R001")
        register_member("Brian", "driver")
        result = enter_driver("R001", "M002")
        assert result["success"] is False
        assert "scheduled" in result["message"].lower()

    def test_enter_multiple_drivers(self):
        register_member("Dom", "driver")
        register_member("Brian", "driver")
        create_race("Race A")
        enter_driver("R001", "M001")
        enter_driver("R001", "M002")
        assert len(get_race("R001")["race"]["driver_ids"]) == 2


# ------------------------------------------------------------------
# assign_car
# ------------------------------------------------------------------

class TestAssignCar:

    def test_assign_valid_car(self):
        _make_car("Skyline")
        create_race("Race A")
        result = assign_car("R001", "C001")
        assert result["success"] is True

    def test_assign_car_updates_race(self):
        _make_car()
        create_race("Race A")
        assign_car("R001", "C001")
        assert "C001" in get_race("R001")["race"]["car_ids"]

    def test_assign_car_marks_assigned_in_inventory(self):
        from inventory.inventory import get_car
        _make_car()
        create_race("Race A")
        assign_car("R001", "C001")
        assert get_car("C001")["car"]["assigned"] is True

    def test_assign_damaged_car_fails(self):
        add_car("Damaged Car", "damaged")
        create_race("Race A")
        result = assign_car("R001", "C001")
        assert result["success"] is False
        assert "good" in result["message"].lower()

    def test_assign_under_repair_car_fails(self):
        add_car("Repair Car", "under_repair")
        create_race("Race A")
        result = assign_car("R001", "C001")
        assert result["success"] is False

    def test_assign_already_assigned_car_fails(self):
        _make_car()
        create_race("Race A")
        create_race("Race B")
        assign_car("R001", "C001")
        result = assign_car("R002", "C001")
        assert result["success"] is False
        assert "already assigned" in result["message"].lower()

    def test_assign_nonexistent_car(self):
        create_race("Race A")
        result = assign_car("R001", "C999")
        assert result["success"] is False

    def test_assign_car_duplicate_in_same_race(self):
        _make_car()
        create_race("Race A")
        assign_car("R001", "C001")
        result = assign_car("R001", "C001")
        assert result["success"] is False

    def test_assign_car_to_ongoing_race_fails(self):
        _make_driver()
        _make_car()
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        start_race("R001")
        add_car("Second Car")
        result = assign_car("R001", "C002")
        assert result["success"] is False


# ------------------------------------------------------------------
# start_race
# ------------------------------------------------------------------

class TestStartRace:

    def test_start_valid_race(self):
        _make_driver()
        _make_car()
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        result = start_race("R001")
        assert result["success"] is True
        assert get_race("R001")["race"]["status"] == "ongoing"

    def test_start_race_no_drivers(self):
        _make_car()
        create_race("Race A")
        assign_car("R001", "C001")
        result = start_race("R001")
        assert result["success"] is False
        assert "no drivers" in result["message"].lower()

    def test_start_race_no_cars(self):
        _make_driver()
        create_race("Race A")
        enter_driver("R001", "M001")
        result = start_race("R001")
        assert result["success"] is False
        assert "no cars" in result["message"].lower()

    def test_start_already_ongoing_race_fails(self):
        _make_driver()
        _make_car()
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        start_race("R001")
        result = start_race("R001")
        assert result["success"] is False

    def test_start_nonexistent_race(self):
        result = start_race("R999")
        assert result["success"] is False


# ------------------------------------------------------------------
# complete_race
# ------------------------------------------------------------------

class TestCompleteRace:

    def test_complete_ongoing_race(self):
        _make_driver()
        _make_car()
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        start_race("R001")
        result = complete_race("R001")
        assert result["success"] is True
        assert get_race("R001")["race"]["status"] == "completed"

    def test_complete_scheduled_race_fails(self):
        create_race("Race A")
        result = complete_race("R001")
        assert result["success"] is False
        assert "ongoing" in result["message"].lower()

    def test_complete_nonexistent_race(self):
        result = complete_race("R999")
        assert result["success"] is False

    def test_complete_already_completed_fails(self):
        _make_driver()
        _make_car()
        create_race("Race A")
        enter_driver("R001", "M001")
        assign_car("R001", "C001")
        start_race("R001")
        complete_race("R001")
        result = complete_race("R001")
        assert result["success"] is False


# ------------------------------------------------------------------
# get_race_drivers / get_race_cars
# ------------------------------------------------------------------

class TestGetRaceDriversAndCars:

    def test_get_race_drivers(self):
        _make_driver()
        create_race("Race A")
        enter_driver("R001", "M001")
        result = get_race_drivers("R001")
        assert result["success"] is True
        assert "M001" in result["driver_ids"]

    def test_get_race_drivers_nonexistent_race(self):
        result = get_race_drivers("R999")
        assert result["success"] is False
        assert result["driver_ids"] == []

    def test_get_race_cars(self):
        _make_car()
        create_race("Race A")
        assign_car("R001", "C001")
        result = get_race_cars("R001")
        assert result["success"] is True
        assert "C001" in result["car_ids"]

    def test_get_race_cars_nonexistent_race(self):
        result = get_race_cars("R999")
        assert result["success"] is False
        assert result["car_ids"] == []


# ------------------------------------------------------------------
# list_available_drivers / list_available_cars
# ------------------------------------------------------------------

class TestListAvailableHelpers:

    def test_list_available_drivers(self):
        _make_driver("Dom")
        _make_mechanic("Letty")
        result = list_available_drivers()
        assert result["success"] is True
        assert len(result["driver_ids"]) == 1

    def test_list_available_cars(self):
        add_car("Good Car", "good")
        add_car("Bad Car", "damaged")
        result = list_available_cars()
        assert result["success"] is True
        assert len(result["car_ids"]) == 1

    def test_available_drivers_empty(self):
        result = list_available_drivers()
        assert result["driver_ids"] == []

    def test_available_cars_empty(self):
        result = list_available_cars()
        assert result["car_ids"] == []