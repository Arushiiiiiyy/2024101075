#this integrates (req+crew manage) + inventory
# tests/test_integration_part2.py
# Integration Part 2 — Registration + Crew Management + Inventory
#
# Tests that Inventory works correctly with the existing modules.
# conftest.py handles database reset automatically.

import pytest

from registration.registration import register_member, deactivate_member
from crew_management.crew_management import assign_role
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
    add_cash,
    deduct_cash,
    get_cash_balance,
    get_inventory_summary,
)


# Cars in inventory must be in 'good' condition to be race-eligible.


class TestCarLifecycle:

    def test_add_car_and_check_condition(self):
        """
        WHY: Verifies a freshly added car is in 'good' condition
        and ready to be assigned to a race.
        """
        result = add_car("Nissan Skyline")
        assert result["success"] is True
        car = get_car(result["car_id"])["car"]
        assert car["condition"] == "good"
        assert car["assigned"] is False

    def test_damaged_car_not_in_available(self):
        """
        WHY: Race Management only picks available cars.
        A damaged car must not appear as available.
        """
        add_car("Supra", "damaged")
        assert get_available_cars() == []

    def test_good_car_in_available(self):
        """
        WHY: A good unassigned car must show up for Race Management.
        """
        r = add_car("Skyline", "good")
        assert r["car_id"] in get_available_cars()

    def test_assigned_car_not_available(self):
        """
        WHY: Once Race Management assigns a car, it must disappear
        from the available pool so it can't be double-assigned.
        """
        r = add_car("Skyline", "good")
        set_car_assigned(r["car_id"], True)
        assert r["car_id"] not in get_available_cars()

    def test_car_condition_update(self):
        """
        WHY: After a race, Results module marks cars as damaged.
        Inventory must correctly store the new condition.
        """
        r = add_car("Charger", "good")
        update_car_condition(r["car_id"], "damaged")
        assert get_car(r["car_id"])["car"]["condition"] == "damaged"

    def test_cannot_remove_assigned_car(self):
        """
        WHY: A car in an active race cannot be removed from inventory.
        """
        r = add_car("Skyline")
        set_car_assigned(r["car_id"], True)
        result = remove_car(r["car_id"])
        assert result["success"] is False
        assert "assigned" in result["message"].lower()

    def test_can_remove_unassigned_car(self):
        """
        WHY: An unassigned car can be removed cleanly.
        """
        r = add_car("Skyline")
        result = remove_car(r["car_id"])
        assert result["success"] is True
        assert get_car(r["car_id"])["success"] is False



class TestPartsAndTools:

    def test_add_and_use_spare_parts(self):
        """
        WHY: Repair operations consume spare parts. Inventory must
        track this correctly and prevent over-consumption.
        """
        add_spare_parts(10)
        use_spare_parts(3)
        from inventory.inventory import get_parts_and_tools
        assert get_parts_and_tools()["spare_parts"] == 7

    def test_cannot_use_more_parts_than_available(self):
        """
        WHY: Repair must fail gracefully if not enough parts —
        prevents negative inventory.
        """
        add_spare_parts(2)
        result = use_spare_parts(5)
        assert result["success"] is False
        assert "not enough" in result["message"].lower()

    def test_add_and_use_tools(self):
        """
        WHY: Tools are consumed alongside parts during repair.
        """
        add_tools(5)
        use_tools(2)
        from inventory.inventory import get_parts_and_tools
        assert get_parts_and_tools()["tools"] == 3

    def test_cannot_use_more_tools_than_available(self):
        """
        WHY: Same as parts — tools must not go below zero.
        """
        add_tools(1)
        result = use_tools(5)
        assert result["success"] is False


# ------------------------------------------------------------------
# SCENARIO 3
# Cash balance is updated by Results (prize money) and
# Sponsorship (seed money / bonuses).
# Modules: Inventory (cash)
# ------------------------------------------------------------------

class TestCashBalance:

    def test_initial_balance_is_zero(self):
        """
        WHY: Fresh system should start with no money — verifies
        clean state after reset.
        """
        assert get_cash_balance()["cash_balance"] == 0.0

    def test_add_cash_increases_balance(self):
        """
        WHY: Prize money from Results is added via add_cash().
        Must reflect correctly in balance.
        """
        add_cash(1000.0)
        assert get_cash_balance()["cash_balance"] == 1000.0

    def test_deduct_cash_decreases_balance(self):
        """
        WHY: Expenses (repairs, missions) deduct cash.
        Must update correctly.
        """
        add_cash(1000.0)
        deduct_cash(400.0)
        assert get_cash_balance()["cash_balance"] == 600.0

    def test_cannot_deduct_more_than_balance(self):
        """
        WHY: Cannot spend money you don't have — prevents
        negative cash balance.
        """
        add_cash(100.0)
        result = deduct_cash(500.0)
        assert result["success"] is False
        assert "insufficient" in result["message"].lower()

    def test_multiple_additions_accumulate(self):
        """
        WHY: Prize money from multiple races should stack up
        correctly in the balance.
        """
        add_cash(500.0)
        add_cash(300.0)
        add_cash(200.0)
        assert get_cash_balance()["cash_balance"] == 1000.0

# Inventory summary reflects all state correctly.



class TestInventorySummaryIntegration:

    def test_summary_reflects_all_additions(self):
        """
        WHY: get_inventory_summary() is the single snapshot of
        all inventory state — must be accurate across all ops.
        """
        add_car("Skyline")
        add_car("Supra", "damaged")
        add_spare_parts(10)
        add_tools(5)
        add_cash(2000.0)

        summary = get_inventory_summary()
        assert summary["success"] is True
        assert len(summary["cars"]) == 2
        assert summary["spare_parts"] == 10
        assert summary["tools"] == 5
        assert summary["cash_balance"] == 2000.0

    def test_summary_after_operations(self):
        """
        WHY: Summary must reflect live changes, not stale data.
        """
        r = add_car("Skyline")
        add_spare_parts(10)
        add_cash(1000.0)
        use_spare_parts(3)
        deduct_cash(200.0)
        update_car_condition(r["car_id"], "damaged")

        summary = get_inventory_summary()
        assert summary["spare_parts"] == 7
        assert summary["cash_balance"] == 800.0
        car = next(c for c in summary["cars"] if c["id"] == r["car_id"])
        assert car["condition"] == "damaged"

# Inventory is independent of crew — registering/deactivating


class TestInventoryIndependentOfCrew:

    def test_cars_unaffected_by_member_registration(self):
        """
        WHY: Ensures no accidental coupling — adding crew members
        must not modify inventory state.
        """
        add_car("Skyline")
        add_cash(500.0)
        register_member("Dom", "driver")
        register_member("Letty", "mechanic")

        assert len(list_cars()["cars"]) == 1
        assert get_cash_balance()["cash_balance"] == 500.0

    def test_cars_unaffected_by_member_deactivation(self):
        """
        WHY: Deactivating a crew member must not touch cars
        or cash — modules must stay decoupled.
        """
        add_car("Skyline")
        r = register_member("Dom", "driver")
        deactivate_member(r["member_id"])

        assert len(list_cars()["cars"]) == 1
        assert get_available_cars() != []