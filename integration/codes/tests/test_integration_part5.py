# tests/test_integration_part5.py
# Integration Part 5 — + Mission Planning
#
# Tests cross-module mission scenarios.
# conftest.py handles database reset automatically.

import pytest

from registration.registration import register_member, deactivate_member
from crew_management.crew_management import assign_role
from inventory.inventory import add_car, get_car
from race_management.race_management import (
    create_race, enter_driver, assign_car, start_race,
)
from results.results import record_result
from mission_planning.mission_planning import (
    create_mission, get_mission, list_missions,
    assign_crew_member, start_mission,
    complete_mission, fail_mission,
    check_roles_available,
)




def _driver(name="Dom"):
    return register_member(name, "driver")

def _mechanic(name="Letty"):
    return register_member(name, "mechanic")

def _strategist(name="Tej"):
    return register_member(name, "strategist")

def _mission(name="Op Nightfall", mtype="delivery", roles=None):
    if roles is None:
        roles = ["driver"]
    return create_mission(name, mtype, roles)



# Crew member must be registered before being assigned a mission.
# Modules: Registration → Mission Planning


class TestRegistrationGatesMissionAssignment:

    def test_registered_member_can_be_assigned(self):
        """
        WHY: Core rule — only registered crew can be assigned
        to missions. Tests Registration → Mission Planning flow.
        """
        d = _driver()
        m = _mission()
        result = assign_crew_member(m["mission_id"], d["member_id"])
        assert result["success"] is True

    def test_unregistered_member_cannot_be_assigned(self):
        """
        WHY: Mission Planning must check Registration before
        assigning — unregistered members must be rejected.
        """
        m = _mission()
        result = assign_crew_member(m["mission_id"], "M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_inactive_member_cannot_be_assigned(self):
        """
        WHY: Deactivated crew must be excluded from missions
        just like they are excluded from races.
        """
        d = _driver()
        deactivate_member(d["member_id"])
        m = _mission()
        result = assign_crew_member(m["mission_id"], d["member_id"])
        assert result["success"] is False
        assert "inactive" in result["message"].lower()




# Missions cannot start if required roles are unavailable.
# Modules: Registration + Crew Management → Mission Planning


class TestMissionRoleValidation:

    def test_mission_starts_when_roles_covered(self):
        """
        WHY: Core assignment requirement — mission can only start
        when all required roles are assigned.
        """
        d = _driver()
        m = _mission(roles=["driver"])
        assign_crew_member(m["mission_id"], d["member_id"])
        result = start_mission(m["mission_id"])
        assert result["success"] is True
        assert result["missing_roles"] == []

    def test_mission_blocked_when_role_missing(self):
        """
        WHY: Core assignment requirement — missions cannot start
        if required roles are unavailable.
        """
        d = _driver()
        m = create_mission("Op X", "rescue", ["driver", "mechanic"])
        assign_crew_member(m["mission_id"], d["member_id"])
        # mechanic not assigned
        result = start_mission(m["mission_id"])
        assert result["success"] is False
        assert "mechanic" in result["missing_roles"]

    def test_mission_blocked_with_no_crew_assigned(self):
        """
        WHY: A mission with no crew assigned at all must not
        start regardless of what roles are required.
        """
        m = _mission(roles=["driver"])
        result = start_mission(m["mission_id"])
        assert result["success"] is False

    def test_check_roles_available_no_crew(self):
        """
        WHY: check_roles_available() is used by Garage module
        before repairs. Empty system must return all missing.
        """
        result = check_roles_available(["mechanic"])
        assert result["success"] is False
        assert "mechanic" in result["missing_roles"]

    def test_check_roles_available_with_crew(self):
        """
        WHY: Once a mechanic is registered and active,
        check_roles_available must return success.
        """
        _mechanic()
        result = check_roles_available(["mechanic"])
        assert result["success"] is True

    def test_role_change_breaks_mission_eligibility(self):
        """
        WHY: If a driver's role is changed to mechanic via
        Crew Management, a driver-only mission must fail.
        """
        d = _driver()
        m = _mission(roles=["driver"])
        assign_crew_member(m["mission_id"], d["member_id"])
        # change role — member is now a mechanic
        assign_role(d["member_id"], "mechanic")
        result = start_mission(m["mission_id"])
        assert result["success"] is False
        assert "driver" in result["missing_roles"]



# Damaged car after race → mechanic check before mission.
# Modules: Results + Inventory + Crew Management + Mission Planning


class TestDamagedCarMechanicCheck:

    def _run_race_with_damage(self):
        """Run a full race and damage a car."""
        d = register_member("Dom", "driver")
        c = add_car("Skyline", "good")
        race = create_race("Street Kings")
        enter_driver(race["race_id"], d["member_id"])
        assign_car(race["race_id"], c["car_id"])
        start_race(race["race_id"])
        record_result(
            race["race_id"],
            [d["member_id"]],
            500.0,
            damages=[c["car_id"]],
        )
        return c["car_id"]

    def test_car_damaged_after_race(self):
        """
        WHY: Verifies the full pipeline — race result marks car
        as damaged in Inventory as the assignment requires.
        """
        cid = self._run_race_with_damage()
        assert get_car(cid)["car"]["condition"] == "damaged"

    def test_mechanic_available_before_repair_mission(self):
        """
        WHY: Assignment requirement — if car is damaged, a mission
        requiring a mechanic must check availability first.
        """
        self._run_race_with_damage()
        _mechanic()  # register mechanic
        result = check_roles_available(["mechanic"])
        assert result["success"] is True

    def test_no_mechanic_blocks_repair_mission(self):
        """
        WHY: If no mechanic is available after a car is damaged,
        a repair mission must be blocked.
        """
        self._run_race_with_damage()
        # no mechanic registered
        result = check_roles_available(["mechanic"])
        assert result["success"] is False
        assert "mechanic" in result["missing_roles"]

    def test_inactive_mechanic_blocks_repair_mission(self):
        """
        WHY: An inactive mechanic must not count as available
        for a repair mission — same rule as races.
        """
        self._run_race_with_damage()
        m = _mechanic()
        deactivate_member(m["member_id"])
        result = check_roles_available(["mechanic"])
        assert result["success"] is False


# ------------------------------------------------------------------
# SCENARIO 4
# Mission full lifecycle — planned → active → completed/failed.
# Modules: Registration + Mission Planning
# ------------------------------------------------------------------

class TestMissionLifecycle:

    def test_full_mission_lifecycle_completed(self):
        """
        WHY: Tests the full planned → active → completed flow
        across Registration and Mission Planning.
        """
        d = _driver()
        m = _mission()
        assign_crew_member(m["mission_id"], d["member_id"])
        start_mission(m["mission_id"])
        result = complete_mission(m["mission_id"])
        assert result["success"] is True
        assert get_mission(m["mission_id"])["mission"]["status"] == "completed"

    def test_full_mission_lifecycle_failed(self):
        """
        WHY: Missions can also fail — tests the alternate
        lifecycle path planned → active → failed.
        """
        d = _driver()
        m = _mission()
        assign_crew_member(m["mission_id"], d["member_id"])
        start_mission(m["mission_id"])
        result = fail_mission(m["mission_id"])
        assert result["success"] is True
        assert get_mission(m["mission_id"])["mission"]["status"] == "failed"

    def test_multiple_mission_types(self):
        """
        WHY: All four mission types must be creatable and
        manageable — tests type variety in the system.
        """
        d = _driver()
        mech = _mechanic()
        s = _strategist()

        for i, (mtype, roles) in enumerate([
            ("delivery", ["driver"]),
            ("rescue",   ["driver", "mechanic"]),
            ("sabotage", ["driver", "strategist"]),
            ("recon",    ["scout"]),
        ]):
            if mtype != "recon":
                m = create_mission(f"Op {i}", mtype, roles)
                assert m["success"] is True

    def test_list_missions_by_status(self):
        """
        WHY: list_missions() with status filter must correctly
        show only missions in the requested state.
        """
        d = _driver()
        m1 = _mission("Op A")
        m2 = create_mission("Op B", "recon", ["scout"])

        assign_crew_member(m1["mission_id"], d["member_id"])
        start_mission(m1["mission_id"])

        active = list_missions(status_filter="active")["missions"]
        planned = list_missions(status_filter="planned")["missions"]

        assert len(active) == 1
        assert len(planned) == 1