# crew_management/tests/test_crew_management.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import register_member, deactivate_member
from crew_management.crew_management import (
    assign_role,
    get_role,
    list_members_by_role,
    get_available_drivers,
    get_available_mechanics,
    has_available_role,
    set_skill_level,
    increase_skill,
    get_skill_level,
    get_crew_summary,
)


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield
    reset_database()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _reg(name, role):
    return register_member(name, role)


# ------------------------------------------------------------------
# assign_role
# ------------------------------------------------------------------

class TestAssignRole:

    def test_assign_valid_role(self):
        r = _reg("Dom", "driver")
        mid = r["member_id"]
        result = assign_role(mid, "mechanic")
        assert result["success"] is True
        assert get_role(mid)["role"] == "mechanic"

    def test_assign_same_role(self):
        r = _reg("Dom", "driver")
        mid = r["member_id"]
        result = assign_role(mid, "driver")
        assert result["success"] is True

    def test_assign_role_invalid(self):
        r = _reg("Dom", "driver")
        result = assign_role(r["member_id"], "hacker")
        assert result["success"] is False
        assert "invalid role" in result["message"].lower()

    def test_assign_role_unregistered(self):
        result = assign_role("M999", "driver")
        assert result["success"] is False
        assert "register them first" in result["message"].lower()

    def test_assign_role_inactive_member(self):
        r = _reg("Letty", "driver")
        mid = r["member_id"]
        deactivate_member(mid)
        result = assign_role(mid, "mechanic")
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_assign_role_case_insensitive(self):
        r = _reg("Brian", "driver")
        result = assign_role(r["member_id"], "MECHANIC")
        assert result["success"] is True

    def test_assign_role_updates_correctly(self):
        r = _reg("Tej", "strategist")
        mid = r["member_id"]
        assign_role(mid, "driver")
        assert get_role(mid)["role"] == "driver"


# ------------------------------------------------------------------
# get_role
# ------------------------------------------------------------------

class TestGetRole:

    def test_get_role_existing(self):
        r = _reg("Roman", "strategist")
        result = get_role(r["member_id"])
        assert result["success"] is True
        assert result["role"] == "strategist"

    def test_get_role_nonexistent(self):
        result = get_role("M999")
        assert result["success"] is False
        assert result["role"] is None


# ------------------------------------------------------------------
# list_members_by_role
# ------------------------------------------------------------------

class TestListMembersByRole:

    def test_list_drivers(self):
        _reg("Alpha", "driver")
        _reg("Beta", "driver")
        _reg("Gamma", "mechanic")
        result = list_members_by_role("driver")
        assert result["success"] is True
        assert len(result["members"]) == 2

    def test_list_empty_role(self):
        result = list_members_by_role("scout")
        assert result["success"] is True
        assert result["members"] == []

    def test_list_invalid_role(self):
        result = list_members_by_role("ghost")
        assert result["success"] is False

    def test_inactive_excluded(self):
        r = _reg("Hobbs", "driver")
        deactivate_member(r["member_id"])
        result = list_members_by_role("driver")
        assert len(result["members"]) == 0


# ------------------------------------------------------------------
# get_available_drivers / get_available_mechanics
# ------------------------------------------------------------------

class TestAvailableHelpers:

    def test_get_available_drivers(self):
        _reg("D1", "driver")
        _reg("D2", "driver")
        _reg("M1", "mechanic")
        drivers = get_available_drivers()
        assert len(drivers) == 2

    def test_get_available_mechanics(self):
        _reg("M1", "mechanic")
        _reg("D1", "driver")
        mechanics = get_available_mechanics()
        assert len(mechanics) == 1

    def test_inactive_not_in_available(self):
        r = _reg("D1", "driver")
        deactivate_member(r["member_id"])
        assert get_available_drivers() == []

    def test_empty_when_no_members(self):
        assert get_available_drivers() == []
        assert get_available_mechanics() == []


# ------------------------------------------------------------------
# has_available_role
# ------------------------------------------------------------------

class TestHasAvailableRole:

    def test_has_driver_true(self):
        _reg("Driver One", "driver")
        assert has_available_role("driver") is True

    def test_has_driver_false(self):
        assert has_available_role("driver") is False

    def test_has_role_inactive_excluded(self):
        r = _reg("Mech One", "mechanic")
        deactivate_member(r["member_id"])
        assert has_available_role("mechanic") is False


# ------------------------------------------------------------------
# set_skill_level
# ------------------------------------------------------------------

class TestSetSkillLevel:

    def test_set_valid_skill(self):
        r = _reg("Ramsey", "strategist")
        mid = r["member_id"]
        result = set_skill_level(mid, 7)
        assert result["success"] is True
        assert get_skill_level(mid)["skill_level"] == 7

    def test_set_skill_min(self):
        r = _reg("Ramsey", "strategist")
        result = set_skill_level(r["member_id"], 1)
        assert result["success"] is True

    def test_set_skill_max(self):
        r = _reg("Ramsey", "strategist")
        result = set_skill_level(r["member_id"], 10)
        assert result["success"] is True

    def test_set_skill_below_min(self):
        r = _reg("Ramsey", "strategist")
        result = set_skill_level(r["member_id"], 0)
        assert result["success"] is False

    def test_set_skill_above_max(self):
        r = _reg("Ramsey", "strategist")
        result = set_skill_level(r["member_id"], 11)
        assert result["success"] is False

    def test_set_skill_non_integer(self):
        r = _reg("Ramsey", "strategist")
        result = set_skill_level(r["member_id"], 5.5)
        assert result["success"] is False

    def test_set_skill_unregistered(self):
        result = set_skill_level("M999", 5)
        assert result["success"] is False


# ------------------------------------------------------------------
# increase_skill
# ------------------------------------------------------------------

class TestIncreaseSkill:

    def test_increase_by_one(self):
        r = _reg("Han", "driver")
        mid = r["member_id"]
        result = increase_skill(mid, 1)
        assert result["success"] is True
        assert result["new_skill"] == 2

    def test_increase_by_multiple(self):
        r = _reg("Han", "driver")
        mid = r["member_id"]
        increase_skill(mid, 4)
        assert get_skill_level(mid)["skill_level"] == 5

    def test_increase_caps_at_max(self):
        r = _reg("Han", "driver")
        mid = r["member_id"]
        set_skill_level(mid, 9)
        result = increase_skill(mid, 5)
        assert result["new_skill"] == 10

    def test_increase_already_at_max(self):
        r = _reg("Han", "driver")
        mid = r["member_id"]
        set_skill_level(mid, 10)
        result = increase_skill(mid, 1)
        assert result["new_skill"] == 10

    def test_increase_zero_amount(self):
        r = _reg("Han", "driver")
        result = increase_skill(r["member_id"], 0)
        assert result["success"] is False

    def test_increase_negative_amount(self):
        r = _reg("Han", "driver")
        result = increase_skill(r["member_id"], -1)
        assert result["success"] is False

    def test_increase_unregistered(self):
        result = increase_skill("M999", 1)
        assert result["success"] is False


# ------------------------------------------------------------------
# get_skill_level
# ------------------------------------------------------------------

class TestGetSkillLevel:

    def test_default_skill_is_1(self):
        r = _reg("Gisele", "scout")
        result = get_skill_level(r["member_id"])
        assert result["success"] is True
        assert result["skill_level"] == 1

    def test_get_skill_after_set(self):
        r = _reg("Gisele", "scout")
        set_skill_level(r["member_id"], 8)
        result = get_skill_level(r["member_id"])
        assert result["skill_level"] == 8

    def test_get_skill_unregistered(self):
        result = get_skill_level("M999")
        assert result["success"] is False
        assert result["skill_level"] is None


# ------------------------------------------------------------------
# get_crew_summary
# ------------------------------------------------------------------

class TestGetCrewSummary:

    def test_empty_summary(self):
        result = get_crew_summary()
        assert result["success"] is True
        assert result["summary"] == []

    def test_summary_contains_all_members(self):
        _reg("Alpha", "driver")
        _reg("Beta", "mechanic")
        result = get_crew_summary()
        assert len(result["summary"]) == 2

    def test_summary_fields(self):
        _reg("Alpha", "driver")
        summary = get_crew_summary()["summary"][0]
        for field in ["id", "name", "role", "skill_level", "status"]:
            assert field in summary