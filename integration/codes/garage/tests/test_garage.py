# garage/tests/test_garage.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import register_member, deactivate_member
from inventory.inventory import (
    add_car, add_spare_parts, add_tools,
    get_car, set_car_assigned,
)
from garage.garage import (
    get_car_condition,
    list_damaged_cars,
    list_cars_under_repair,
    send_for_repair,
    complete_repair,
    repair_car,
    get_garage_summary,
)


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield
    reset_database()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _add_good_car(name="Skyline"):
    return add_car(name, "good")

def _add_damaged_car(name="Supra"):
    return add_car(name, "damaged")

def _add_mechanic(name="Letty"):
    return register_member(name, "mechanic")

def _stock_resources(parts=10, tools=10):
    add_spare_parts(parts)
    add_tools(tools)


# ------------------------------------------------------------------
# get_car_condition
# ------------------------------------------------------------------

class TestGetCarCondition:

    def test_good_car_condition(self):
        _add_good_car()
        result = get_car_condition("C001")
        assert result["success"] is True
        assert result["condition"] == "good"

    def test_damaged_car_condition(self):
        _add_damaged_car()
        result = get_car_condition("C001")
        assert result["condition"] == "damaged"

    def test_nonexistent_car(self):
        result = get_car_condition("C999")
        assert result["success"] is False
        assert result["condition"] is None


# ------------------------------------------------------------------
# list_damaged_cars
# ------------------------------------------------------------------

class TestListDamagedCars:

    def test_no_damaged_cars(self):
        _add_good_car()
        result = list_damaged_cars()
        assert result["success"] is True
        assert result["cars"] == []

    def test_one_damaged_car(self):
        _add_damaged_car()
        result = list_damaged_cars()
        assert len(result["cars"]) == 1

    def test_multiple_damaged_cars(self):
        _add_damaged_car("Car A")
        _add_damaged_car("Car B")
        _add_good_car("Car C")
        result = list_damaged_cars()
        assert len(result["cars"]) == 2

    def test_empty_inventory(self):
        result = list_damaged_cars()
        assert result["cars"] == []


# ------------------------------------------------------------------
# list_cars_under_repair
# ------------------------------------------------------------------

class TestListCarsUnderRepair:

    def test_no_cars_under_repair(self):
        _add_good_car()
        result = list_cars_under_repair()
        assert result["cars"] == []

    def test_one_car_under_repair(self):
        _add_damaged_car()
        _add_mechanic()
        send_for_repair("C001")
        result = list_cars_under_repair()
        assert len(result["cars"]) == 1

    def test_only_under_repair_shown(self):
        _add_damaged_car("Car A")
        _add_damaged_car("Car B")
        _add_mechanic()
        send_for_repair("C001")
        result = list_cars_under_repair()
        assert len(result["cars"]) == 1
        assert result["cars"][0]["id"] == "C001"


# ------------------------------------------------------------------
# send_for_repair
# ------------------------------------------------------------------

class TestSendForRepair:

    def test_send_damaged_car_with_mechanic(self):
        _add_damaged_car()
        _add_mechanic()
        result = send_for_repair("C001")
        assert result["success"] is True
        assert get_car("C001")["car"]["condition"] == "under_repair"

    def test_send_good_car_fails(self):
        _add_good_car()
        _add_mechanic()
        result = send_for_repair("C001")
        assert result["success"] is False
        assert "damaged" in result["message"].lower()

    def test_send_under_repair_car_fails(self):
        _add_damaged_car()
        _add_mechanic()
        send_for_repair("C001")
        result = send_for_repair("C001")
        assert result["success"] is False

    def test_send_car_no_mechanic_fails(self):
        _add_damaged_car()
        result = send_for_repair("C001")
        assert result["success"] is False
        assert "mechanic" in result["message"].lower()

    def test_send_car_inactive_mechanic_fails(self):
        _add_damaged_car()
        r = _add_mechanic()
        deactivate_member(r["member_id"])
        result = send_for_repair("C001")
        assert result["success"] is False
        assert "mechanic" in result["message"].lower()

    def test_send_assigned_car_fails(self):
        _add_damaged_car()
        _add_mechanic()
        set_car_assigned("C001", True)
        result = send_for_repair("C001")
        assert result["success"] is False
        assert "assigned" in result["message"].lower()

    def test_send_nonexistent_car_fails(self):
        result = send_for_repair("C999")
        assert result["success"] is False


# ------------------------------------------------------------------
# complete_repair
# ------------------------------------------------------------------

class TestCompleteRepair:

    def test_complete_repair_success(self):
        _add_damaged_car()
        _add_mechanic()
        _stock_resources()
        send_for_repair("C001")
        result = complete_repair("C001")
        assert result["success"] is True
        assert get_car("C001")["car"]["condition"] == "good"

    def test_complete_repair_consumes_parts(self):
        from inventory.inventory import get_parts_and_tools
        _add_damaged_car()
        _add_mechanic()
        add_spare_parts(5)
        add_tools(5)
        send_for_repair("C001")
        complete_repair("C001")
        pt = get_parts_and_tools()
        assert pt["spare_parts"] == 3   # 5 - 2
        assert pt["tools"] == 4         # 5 - 1

    def test_complete_repair_insufficient_parts(self):
        _add_damaged_car()
        _add_mechanic()
        add_spare_parts(1)   # need 2
        add_tools(5)
        send_for_repair("C001")
        result = complete_repair("C001")
        assert result["success"] is False
        assert "spare parts" in result["message"].lower()

    def test_complete_repair_insufficient_tools(self):
        from inventory.inventory import get_parts_and_tools
        _add_damaged_car()
        _add_mechanic()
        add_spare_parts(5)
        add_tools(0)         # need 1
        send_for_repair("C001")
        result = complete_repair("C001")
        assert result["success"] is False
        assert "tools" in result["message"].lower()
        # Parts should be rolled back
        assert get_parts_and_tools()["spare_parts"] == 5

    def test_complete_repair_good_car_fails(self):
        _add_good_car()
        _stock_resources()
        result = complete_repair("C001")
        assert result["success"] is False
        assert "under repair" in result["message"].lower()

    def test_complete_repair_damaged_car_fails(self):
        _add_damaged_car()
        _stock_resources()
        result = complete_repair("C001")
        assert result["success"] is False

    def test_complete_repair_nonexistent_car(self):
        result = complete_repair("C999")
        assert result["success"] is False


# ------------------------------------------------------------------
# repair_car (full pipeline)
# ------------------------------------------------------------------

class TestRepairCar:

    def test_repair_car_full_pipeline(self):
        _add_damaged_car()
        _add_mechanic()
        _stock_resources()
        result = repair_car("C001")
        assert result["success"] is True
        assert get_car("C001")["car"]["condition"] == "good"

    def test_repair_good_car_fails(self):
        _add_good_car()
        _add_mechanic()
        _stock_resources()
        result = repair_car("C001")
        assert result["success"] is False

    def test_repair_car_no_mechanic_fails(self):
        _add_damaged_car()
        _stock_resources()
        result = repair_car("C001")
        assert result["success"] is False
        assert "mechanic" in result["message"].lower()

    def test_repair_car_no_parts_leaves_under_repair(self):
        _add_damaged_car()
        _add_mechanic()
        add_spare_parts(1)   # insufficient
        add_tools(5)
        result = repair_car("C001")
        assert result["success"] is False
        # Car should be under_repair (sent but not completed)
        assert get_car("C001")["car"]["condition"] == "under_repair"

    def test_repair_nonexistent_car(self):
        result = repair_car("C999")
        assert result["success"] is False


# ------------------------------------------------------------------
# get_garage_summary
# ------------------------------------------------------------------

class TestGetGarageSummary:

    def test_empty_garage(self):
        result = get_garage_summary()
        assert result["success"] is True
        assert result["good"] == []
        assert result["damaged"] == []
        assert result["under_repair"] == []

    def test_summary_groups_correctly(self):
        _add_good_car("Car A")
        _add_damaged_car("Car B")
        _add_damaged_car("Car C")
        _add_mechanic()
        send_for_repair("C002")
        result = get_garage_summary()
        assert len(result["good"]) == 1
        assert len(result["damaged"]) == 1
        assert len(result["under_repair"]) == 1

    def test_summary_all_good(self):
        _add_good_car("A")
        _add_good_car("B")
        result = get_garage_summary()
        assert len(result["good"]) == 2
        assert result["damaged"] == []
        assert result["under_repair"] == []

    def test_summary_after_repair(self):
        _add_damaged_car()
        _add_mechanic()
        _stock_resources()
        repair_car("C001")
        result = get_garage_summary()
        assert len(result["good"]) == 1
        assert result["damaged"] == []
        assert result["under_repair"] == []