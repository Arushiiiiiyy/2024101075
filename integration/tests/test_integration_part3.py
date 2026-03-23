#Integration Part 3:Registration + Crew Management + Inventory + Race Management

import pytest

from registration.registration import register_member, deactivate_member
from crew_management.crew_management import assign_role
from inventory.inventory import add_car, get_car, add_cash
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



def _driver(name="Dom"):
    return register_member(name, "driver")

def _mechanic(name="Letty"):
    return register_member(name, "mechanic")

def _car(name="Skyline"):
    return add_car(name, "good")

def _race(name="Street Kings"):
    return create_race(name)


# Register a driver then enter them into a race.
# Modules: Registration → Race Management


class TestRegisterThenEnterRace:

    def test_registered_driver_can_enter_race(self):
        """
        WHY: Core assignment requirement — registered driver
        must be able to enter a race successfully.
        """
        d = _driver()
        r = _race()
        result = enter_driver(r["race_id"], d["member_id"])
        assert result["success"] is True
        assert d["member_id"] in get_race_drivers(r["race_id"])["driver_ids"]

    def test_unregistered_driver_cannot_enter_race(self):
        """
        WHY: Race Management must verify registration before
        allowing entry — core business rule.
        """
        r = _race()
        result = enter_driver(r["race_id"], "M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_non_driver_role_cannot_enter_race(self):
        """
        WHY: Only drivers can race — assignment requirement.
        A mechanic trying to enter must be rejected.
        """
        m = _mechanic()
        r = _race()
        result = enter_driver(r["race_id"], m["member_id"])
        assert result["success"] is False
        assert "only drivers" in result["message"].lower()

    def test_inactive_driver_cannot_enter_race(self):
        """
        WHY: Deactivated members must be blocked from races
        even if they have the driver role.
        """
        d = _driver()
        deactivate_member(d["member_id"])
        r = _race()
        result = enter_driver(r["race_id"], d["member_id"])
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_driver_after_role_change_cannot_enter(self):
        """
        WHY: If Crew Management changes a driver's role to
        mechanic, Race Management must pick that up immediately.
        """
        d = _driver()
        assign_role(d["member_id"], "mechanic")
        r = _race()
        result = enter_driver(r["race_id"], d["member_id"])
        assert result["success"] is False
        assert "only drivers" in result["message"].lower()

    def test_multiple_drivers_can_enter_same_race(self):
        """
        WHY: A race can have multiple drivers — data must
        track all of them correctly.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")
        r = _race()
        enter_driver(r["race_id"], d1["member_id"])
        enter_driver(r["race_id"], d2["member_id"])
        driver_ids = get_race_drivers(r["race_id"])["driver_ids"]
        assert d1["member_id"] in driver_ids
        assert d2["member_id"] in driver_ids


# Assign a car to a race — only good unassigned cars allowed.
# Modules: Inventory → Race Management


class TestAssignCarToRace:

    def test_good_car_can_be_assigned(self):
        """
        WHY: Only good condition cars are race-eligible.
        Verifies Inventory condition check flows into Race Management.
        """
        c = _car()
        r = _race()
        result = assign_car(r["race_id"], c["car_id"])
        assert result["success"] is True
        assert c["car_id"] in get_race_cars(r["race_id"])["car_ids"]

    def test_damaged_car_cannot_be_assigned(self):
        """
        WHY: A damaged car from a previous race must not enter
        a new race — Race Management checks Inventory condition.
        """
        c = add_car("Damaged Supra", "damaged")
        r = _race()
        result = assign_car(r["race_id"], c["car_id"])
        assert result["success"] is False
        assert "good" in result["message"].lower()

    def test_car_marked_assigned_in_inventory_after_race_assign(self):
        """
        WHY: When Race Management assigns a car, Inventory must
        be updated so the car can't be double-assigned.
        """
        c = _car()
        r = _race()
        assign_car(r["race_id"], c["car_id"])
        assert get_car(c["car_id"])["car"]["assigned"] is True

    def test_already_assigned_car_cannot_be_reused(self):
        """
        WHY: A car in one race must not enter another race
        simultaneously — prevents double assignment.
        """
        c = _car()
        r1 = _race("Race A")
        r2 = create_race("Race B")
        assign_car(r1["race_id"], c["car_id"])
        result = assign_car(r2["race_id"], c["car_id"])
        assert result["success"] is False
        assert "already assigned" in result["message"].lower()



# Full race lifecycle — scheduled → ongoing → completed.
# Modules: Registration + Inventory + Race Management


class TestRaceLifecycle:

    def test_full_race_lifecycle(self):
        """
        WHY: Tests the complete flow from creation to completion
        across Registration, Inventory and Race Management.
        """
        d = _driver()
        c = _car()
        r = _race()

        enter_driver(r["race_id"], d["member_id"])
        assign_car(r["race_id"], c["car_id"])

        assert get_race(r["race_id"])["race"]["status"] == "scheduled"

        start_race(r["race_id"])
        assert get_race(r["race_id"])["race"]["status"] == "ongoing"

        complete_race(r["race_id"])
        assert get_race(r["race_id"])["race"]["status"] == "completed"

    def test_cannot_start_race_without_driver(self):
        """
        WHY: A race with no drivers entered must not start —
        prevents empty races.
        """
        _car()
        r = _race()
        assign_car(r["race_id"], "C001")
        result = start_race(r["race_id"])
        assert result["success"] is False
        assert "no drivers" in result["message"].lower()

    def test_cannot_start_race_without_car(self):
        """
        WHY: A race with no cars assigned must not start.
        """
        d = _driver()
        r = _race()
        enter_driver(r["race_id"], d["member_id"])
        result = start_race(r["race_id"])
        assert result["success"] is False
        assert "no cars" in result["message"].lower()

    def test_cannot_enter_driver_to_ongoing_race(self):
        """
        WHY: Once a race starts, the lineup is locked.
        Late entries must be rejected.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")
        c = _car()
        r = _race()
        enter_driver(r["race_id"], d1["member_id"])
        assign_car(r["race_id"], c["car_id"])
        start_race(r["race_id"])
        result = enter_driver(r["race_id"], d2["member_id"])
        assert result["success"] is False

    def test_cannot_complete_scheduled_race(self):
        """
        WHY: A race must go through 'ongoing' before completion —
        cannot skip lifecycle stages.
        """
        r = _race()
        result = complete_race(r["race_id"])
        assert result["success"] is False
        assert "ongoing" in result["message"].lower()




# Available drivers and cars lists reflect live state.
# Modules: Registration + Inventory + Race Management


class TestAvailableListsIntegration:

    def test_available_drivers_only_shows_active_drivers(self):
        """
        WHY: list_available_drivers() is used in the CLI to
        show who can be picked for a race. Must be accurate.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")
        _mechanic("Letty")
        deactivate_member(d2["member_id"])

        result = list_available_drivers()
        assert d1["member_id"] in result["driver_ids"]
        assert d2["member_id"] not in result["driver_ids"]

    def test_available_cars_only_shows_good_unassigned(self):
        """
        WHY: list_available_cars() shows what can be picked
        for a race. Damaged and assigned cars must be excluded.
        """
        c1 = _car("Skyline")
        c2 = add_car("Supra", "damaged")
        c3 = add_car("Charger", "good")

        r = _race()
        assign_car(r["race_id"], c3["car_id"])

        result = list_available_cars()
        assert c1["car_id"] in result["car_ids"]
        assert c2["car_id"] not in result["car_ids"]
        assert c3["car_id"] not in result["car_ids"]

    def test_car_returns_to_available_after_unassign(self):
        """
        WHY: After a race completes and cars are freed,
        they should reappear in available list.
        """
        c = _car()
        d = _driver()
        r = _race()
        enter_driver(r["race_id"], d["member_id"])
        assign_car(r["race_id"], c["car_id"])
        start_race(r["race_id"])
        complete_race(r["race_id"])

        # Manually unassign (Results module does this automatically)
        from inventory.inventory import set_car_assigned
        set_car_assigned(c["car_id"], False)

        assert c["car_id"] in list_available_cars()["car_ids"]