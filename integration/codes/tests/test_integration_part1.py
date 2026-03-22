# tests/test_integration_part1.py
# Integration Part 1 — Registration + Crew Management
#
# Run from integration/ folder with:
# PYTHONPATH=codes:. python -m pytest codes/tests/test_integration_part1.py -v

import pytest


from registration.registration import (
    register_member,
    deactivate_member,
    reactivate_member,
    is_registered,
)
from crew_management.crew_management import (
    assign_role,
    get_role,
    set_skill_level,
    increase_skill,
    get_skill_level,
    has_available_role,
    get_available_drivers,
    get_available_mechanics,
    get_crew_summary,
    list_members_by_role,
)


# A crew member must be registered before a role can be assigned.


class TestRegisterThenAssignRole:

    def test_register_then_assign_role(self):
        """
        WHY: Core business rule — role assignment only works
        after registration. Tests the handoff between modules.
        """
        r = register_member("Dom Toretto", "driver")
        result = assign_role(r["member_id"], "mechanic")
        assert result["success"] is True
        assert get_role(r["member_id"])["role"] == "mechanic"

    def test_assign_role_without_registration_fails(self):
        """
        WHY: Crew Management must reject operations on members
        that Registration hasn't processed yet.
        """
        result = assign_role("M999", "driver")
        assert result["success"] is False
        assert "register" in result["message"].lower()

    def test_role_at_registration_is_stored_correctly(self):
        """
        WHY: Role set during registration should be readable
        by Crew Management immediately — no sync issues.
        """
        register_member("Letty", "mechanic")
        result = get_role("M001")
        assert result["success"] is True
        assert result["role"] == "mechanic"

    def test_reassign_role_multiple_times(self):
        """
        WHY: Verifies Crew Management correctly overwrites the
        role that Registration initially set.
        """
        r = register_member("Brian", "driver")
        assign_role(r["member_id"], "strategist")
        assign_role(r["member_id"], "scout")
        assert get_role(r["member_id"])["role"] == "scout"


# Deactivated members cannot have roles assigned.


class TestDeactivationBlocksCrewOps:

    def test_deactivated_member_cannot_get_role(self):
        """
        WHY: Inactive members should be frozen — Crew Management
        must respect the status set by Registration.
        """
        r = register_member("Roman", "driver")
        deactivate_member(r["member_id"])
        result = assign_role(r["member_id"], "mechanic")
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_reactivated_member_can_get_role(self):
        """
        WHY: After reactivation via Registration, Crew Management
        should accept the member again.
        """
        r = register_member("Roman", "driver")
        deactivate_member(r["member_id"])
        reactivate_member(r["member_id"])
        result = assign_role(r["member_id"], "mechanic")
        assert result["success"] is True

    def test_deactivated_member_excluded_from_available_drivers(self):
        """
        WHY: get_available_drivers() is used by Race Management.
        Deactivated drivers must not appear in that list.
        """
        r = register_member("Dom", "driver")
        assert r["member_id"] in get_available_drivers()
        deactivate_member(r["member_id"])
        assert r["member_id"] not in get_available_drivers()

    def test_deactivated_mechanic_excluded_from_available_mechanics(self):
        """
        WHY: get_available_mechanics() is used by Mission Planning.
        Inactive mechanics must be excluded.
        """
        r = register_member("Letty", "mechanic")
        assert r["member_id"] in get_available_mechanics()
        deactivate_member(r["member_id"])
        assert r["member_id"] not in get_available_mechanics()



# Skill levels are set at registration (default 1) and updated

class TestSkillLevelIntegration:

    def test_registered_member_starts_at_skill_1(self):
        """
        WHY: Every member starts equal. Crew Management reads the
        skill that Registration initialised.
        """
        r = register_member("Tej", "mechanic")
        result = get_skill_level(r["member_id"])
        assert result["success"] is True
        assert result["skill_level"] == 1

    def test_crew_management_updates_skill_after_registration(self):
        """
        WHY: Skill changes made via Crew Management must persist
        and be readable back — tests shared state.
        """
        r = register_member("Han", "driver")
        set_skill_level(r["member_id"], 7)
        assert get_skill_level(r["member_id"])["skill_level"] == 7

    def test_increase_skill_accumulates_correctly(self):
        """
        WHY: Multiple increases must compound correctly across
        the shared database.
        """
        r = register_member("Gisele", "scout")
        increase_skill(r["member_id"], 3)
        increase_skill(r["member_id"], 2)
        assert get_skill_level(r["member_id"])["skill_level"] == 6

    def test_skill_update_unregistered_member_fails(self):
        """
        WHY: Crew Management must not silently update a member
        that doesn't exist in Registration's records.
        """
        result = set_skill_level("M999", 5)
        assert result["success"] is False




class TestHasAvailableRoleIntegration:

    def test_no_members_no_roles_available(self):
        """
        WHY: Empty system should correctly report no roles
        available — used by Mission Planning gate checks.
        """
        assert has_available_role("driver") is False
        assert has_available_role("mechanic") is False

    def test_role_available_after_registration(self):
        """
        WHY: As soon as a driver is registered, Mission Planning
        and Race Management should see them as available.
        """
        register_member("Dom", "driver")
        assert has_available_role("driver") is True

    def test_role_unavailable_after_deactivation(self):
        """
        WHY: Deactivating last driver must immediately make
        driver role unavailable — cross-module state sync.
        """
        r = register_member("Dom", "driver")
        deactivate_member(r["member_id"])
        assert has_available_role("driver") is False

    def test_role_available_again_after_reactivation(self):
        """
        WHY: Reactivation must restore role availability — full
        lifecycle test across both modules.
        """
        r = register_member("Dom", "driver")
        deactivate_member(r["member_id"])
        reactivate_member(r["member_id"])
        assert has_available_role("driver") is True

    def test_role_change_updates_availability(self):
        """
        WHY: If Crew Management reassigns a role, availability
        must update. e.g. only driver → role change → no drivers.
        """
        r = register_member("Dom", "driver")
        assert has_available_role("driver") is True
        assign_role(r["member_id"], "mechanic")
        assert has_available_role("driver") is False
        assert has_available_role("mechanic") is True



# SCENARIO 5
# get_crew_summary() shows accurate cross-module data.
# Modules: Registration + Crew Management


class TestCrewSummaryIntegration:

    def test_summary_reflects_registration_and_skill_updates(self):
        """
        WHY: Crew summary is the single view of the system state.
        Must reflect changes from both modules correctly.
        """
        r1 = register_member("Dom", "driver")
        r2 = register_member("Letty", "mechanic")
        set_skill_level(r1["member_id"], 8)
        set_skill_level(r2["member_id"], 5)

        summary = get_crew_summary()["summary"]
        assert len(summary) == 2

        dom = next(m for m in summary if m["name"] == "Dom")
        assert dom["skill_level"] == 8
        assert dom["role"] == "driver"

    def test_summary_excludes_nothing_all_members_shown(self):
      
        r1 = register_member("Dom", "driver")
        register_member("Brian", "mechanic")
        deactivate_member(r1["member_id"])
        summary = get_crew_summary()["summary"]
        assert len(summary) == 2

    def test_list_members_by_role_excludes_inactive(self):
        
        r = register_member("Dom", "driver")
        register_member("Brian", "driver")
        deactivate_member(r["member_id"])
        result = list_members_by_role("driver")
        assert len(result["members"]) == 1
        assert result["members"][0]["name"] == "Brian"