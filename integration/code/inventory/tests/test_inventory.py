# inventory/tests/test_inventory.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from inventory.inventory import (
    add_car,
    get_car,
    list_cars,
    get_available_cars,
    update_car_condition,
    set_car_assigned,
    remove_car,
    add_spare_parts,
    use_spare_parts,
    add_tools,
    use_tools,
    get_parts_and_tools,
    add_cash,
    deduct_cash,
    get_cash_balance,
    get_inventory_summary,
)


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield
    reset_database()


# ------------------------------------------------------------------
# add_car
# ------------------------------------------------------------------

class TestAddCar:

    def test_add_valid_car(self):
        result = add_car("Nissan Skyline")
        assert result["success"] is True
        assert result["car_id"] == "C001"

    def test_add_car_with_condition(self):
        result = add_car("Toyota Supra", "damaged")
        assert result["success"] is True
        assert get_car("C001")["car"]["condition"] == "damaged"

    def test_add_car_default_condition_is_good(self):
        add_car("Mazda RX-7")
        assert get_car("C001")["car"]["condition"] == "good"

    def test_add_car_default_assigned_is_false(self):
        add_car("Mazda RX-7")
        assert get_car("C001")["car"]["assigned"] is False

    def test_add_car_empty_name(self):
        result = add_car("")
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_add_car_whitespace_name(self):
        result = add_car("   ")
        assert result["success"] is False

    def test_add_car_invalid_condition(self):
        result = add_car("BMW M3", "broken")
        assert result["success"] is False
        assert "invalid condition" in result["message"].lower()

    def test_add_car_duplicate_name(self):
        add_car("Dodge Charger")
        result = add_car("Dodge Charger")
        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    def test_add_car_duplicate_name_case_insensitive(self):
        add_car("dodge charger")
        result = add_car("DODGE CHARGER")
        assert result["success"] is False

    def test_add_multiple_cars_unique_ids(self):
        r1 = add_car("Car A")
        r2 = add_car("Car B")
        assert r1["car_id"] != r2["car_id"]

    def test_add_all_valid_conditions(self):
        for i, cond in enumerate(["good", "damaged", "under_repair"]):
            result = add_car(f"Car {i}", cond)
            assert result["success"] is True


# ------------------------------------------------------------------
# get_car
# ------------------------------------------------------------------

class TestGetCar:

    def test_get_existing_car(self):
        add_car("Subaru Impreza")
        result = get_car("C001")
        assert result["success"] is True
        assert result["car"]["name"] == "Subaru Impreza"

    def test_get_nonexistent_car(self):
        result = get_car("C999")
        assert result["success"] is False
        assert result["car"] is None

    def test_get_car_id_case_insensitive(self):
        add_car("Honda Civic")
        result = get_car("c001")
        assert result["success"] is True


# ------------------------------------------------------------------
# list_cars
# ------------------------------------------------------------------

class TestListCars:

    def test_list_empty(self):
        result = list_cars()
        assert result["success"] is True
        assert result["cars"] == []

    def test_list_all(self):
        add_car("Car A")
        add_car("Car B")
        result = list_cars()
        assert len(result["cars"]) == 2

    def test_list_filter_by_condition(self):
        add_car("Car A", "good")
        add_car("Car B", "damaged")
        add_car("Car C", "good")
        result = list_cars(condition_filter="good")
        assert len(result["cars"]) == 2

    def test_list_filter_invalid_condition(self):
        result = list_cars(condition_filter="broken")
        assert result["success"] is False

    def test_list_filter_by_assigned(self):
        add_car("Car A")
        add_car("Car B")
        set_car_assigned("C001", True)
        result = list_cars(assigned_filter=True)
        assert len(result["cars"]) == 1
        assert result["cars"][0]["id"] == "C001"

    def test_list_filter_not_assigned(self):
        add_car("Car A")
        add_car("Car B")
        set_car_assigned("C001", True)
        result = list_cars(assigned_filter=False)
        assert len(result["cars"]) == 1
        assert result["cars"][0]["id"] == "C002"


# ------------------------------------------------------------------
# get_available_cars
# ------------------------------------------------------------------

class TestGetAvailableCars:

    def test_available_good_unassigned(self):
        add_car("Car A", "good")
        add_car("Car B", "damaged")
        result = get_available_cars()
        assert "C001" in result
        assert "C002" not in result

    def test_assigned_car_not_available(self):
        add_car("Car A", "good")
        set_car_assigned("C001", True)
        assert get_available_cars() == []

    def test_empty_when_no_cars(self):
        assert get_available_cars() == []


# ------------------------------------------------------------------
# update_car_condition
# ------------------------------------------------------------------

class TestUpdateCarCondition:

    def test_update_to_damaged(self):
        add_car("Car A")
        result = update_car_condition("C001", "damaged")
        assert result["success"] is True
        assert get_car("C001")["car"]["condition"] == "damaged"

    def test_update_to_under_repair(self):
        add_car("Car A", "damaged")
        result = update_car_condition("C001", "under_repair")
        assert result["success"] is True

    def test_update_invalid_condition(self):
        add_car("Car A")
        result = update_car_condition("C001", "totaled")
        assert result["success"] is False

    def test_update_nonexistent_car(self):
        result = update_car_condition("C999", "good")
        assert result["success"] is False


# ------------------------------------------------------------------
# set_car_assigned
# ------------------------------------------------------------------

class TestSetCarAssigned:

    def test_assign_car(self):
        add_car("Car A")
        result = set_car_assigned("C001", True)
        assert result["success"] is True
        assert get_car("C001")["car"]["assigned"] is True

    def test_unassign_car(self):
        add_car("Car A")
        set_car_assigned("C001", True)
        result = set_car_assigned("C001", False)
        assert result["success"] is True
        assert get_car("C001")["car"]["assigned"] is False

    def test_assign_nonexistent_car(self):
        result = set_car_assigned("C999", True)
        assert result["success"] is False


# ------------------------------------------------------------------
# remove_car
# ------------------------------------------------------------------

class TestRemoveCar:

    def test_remove_existing_car(self):
        add_car("Car A")
        result = remove_car("C001")
        assert result["success"] is True
        assert get_car("C001")["success"] is False

    def test_remove_nonexistent_car(self):
        result = remove_car("C999")
        assert result["success"] is False

    def test_remove_assigned_car_fails(self):
        add_car("Car A")
        set_car_assigned("C001", True)
        result = remove_car("C001")
        assert result["success"] is False
        assert "assigned" in result["message"].lower()


# ------------------------------------------------------------------
# spare parts
# ------------------------------------------------------------------

class TestSpareParts:

    def test_add_spare_parts(self):
        result = add_spare_parts(10)
        assert result["success"] is True
        assert result["spare_parts"] == 10

    def test_add_spare_parts_accumulates(self):
        add_spare_parts(5)
        result = add_spare_parts(3)
        assert result["spare_parts"] == 8

    def test_add_spare_parts_zero(self):
        result = add_spare_parts(0)
        assert result["success"] is False

    def test_add_spare_parts_negative(self):
        result = add_spare_parts(-5)
        assert result["success"] is False

    def test_use_spare_parts(self):
        add_spare_parts(10)
        result = use_spare_parts(4)
        assert result["success"] is True
        assert result["spare_parts"] == 6

    def test_use_spare_parts_exact(self):
        add_spare_parts(5)
        result = use_spare_parts(5)
        assert result["success"] is True
        assert result["spare_parts"] == 0

    def test_use_spare_parts_insufficient(self):
        add_spare_parts(3)
        result = use_spare_parts(5)
        assert result["success"] is False
        assert "not enough" in result["message"].lower()

    def test_use_spare_parts_zero(self):
        result = use_spare_parts(0)
        assert result["success"] is False


# ------------------------------------------------------------------
# tools
# ------------------------------------------------------------------

class TestTools:

    def test_add_tools(self):
        result = add_tools(5)
        assert result["success"] is True
        assert result["tools"] == 5

    def test_add_tools_zero(self):
        result = add_tools(0)
        assert result["success"] is False

    def test_use_tools(self):
        add_tools(10)
        result = use_tools(3)
        assert result["success"] is True
        assert result["tools"] == 7

    def test_use_tools_insufficient(self):
        add_tools(2)
        result = use_tools(5)
        assert result["success"] is False
        assert "not enough" in result["message"].lower()

    def test_get_parts_and_tools(self):
        add_spare_parts(7)
        add_tools(3)
        result = get_parts_and_tools()
        assert result["spare_parts"] == 7
        assert result["tools"] == 3


# ------------------------------------------------------------------
# cash balance
# ------------------------------------------------------------------

class TestCashBalance:

    def test_add_cash(self):
        result = add_cash(500.0)
        assert result["success"] is True
        assert result["cash_balance"] == 500.0

    def test_add_cash_accumulates(self):
        add_cash(200.0)
        result = add_cash(300.0)
        assert result["cash_balance"] == 500.0

    def test_add_cash_zero(self):
        result = add_cash(0)
        assert result["success"] is False

    def test_add_cash_negative(self):
        result = add_cash(-100.0)
        assert result["success"] is False

    def test_deduct_cash(self):
        add_cash(1000.0)
        result = deduct_cash(400.0)
        assert result["success"] is True
        assert result["cash_balance"] == 600.0

    def test_deduct_cash_exact(self):
        add_cash(500.0)
        result = deduct_cash(500.0)
        assert result["success"] is True
        assert result["cash_balance"] == 0.0

    def test_deduct_cash_insufficient(self):
        add_cash(100.0)
        result = deduct_cash(200.0)
        assert result["success"] is False
        assert "insufficient" in result["message"].lower()

    def test_deduct_cash_zero(self):
        result = deduct_cash(0)
        assert result["success"] is False

    def test_get_cash_balance(self):
        add_cash(750.0)
        result = get_cash_balance()
        assert result["success"] is True
        assert result["cash_balance"] == 750.0

    def test_initial_balance_is_zero(self):
        result = get_cash_balance()
        assert result["cash_balance"] == 0.0


# ------------------------------------------------------------------
# inventory summary
# ------------------------------------------------------------------

class TestInventorySummary:

    def test_summary_empty(self):
        result = get_inventory_summary()
        assert result["success"] is True
        assert result["cars"] == []
        assert result["spare_parts"] == 0
        assert result["tools"] == 0
        assert result["cash_balance"] == 0.0

    def test_summary_with_data(self):
        add_car("Car A")
        add_spare_parts(5)
        add_tools(3)
        add_cash(1000.0)
        result = get_inventory_summary()
        assert len(result["cars"]) == 1
        assert result["spare_parts"] == 5
        assert result["tools"] == 3
        assert result["cash_balance"] == 1000.0