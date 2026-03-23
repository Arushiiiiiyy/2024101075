# mission_planning/tests/test_mission_planning.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import register_member, deactivate_member
from mission_planning.mission_planning import (
    create_mission,
    get_mission,
    list_missions,
    assign_crew_member,
    remove_crew_member,
    start_mission,
    complete_mission,
    fail_mission,
    check_roles_available,
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

def _mission(name="Op Nightfall", mtype="delivery", roles=None):
    if roles is None:
        roles = ["driver"]
    return create_mission(name, mtype, roles)


# ------------------------------------------------------------------
# create_mission
# ------------------------------------------------------------------

class TestCreateMission:

    def test_create_valid_mission(self):
        result = _mission()
        assert result["success"] is True
        assert result["mission_id"] == "MI001"

    def test_create_mission_default_status_planned(self):
        _mission()
        assert get_mission("MI001")["mission"]["status"] == "planned"

    def test_create_mission_empty_assigned_crew(self):
        _mission()
        assert get_mission("MI001")["mission"]["assigned_crew"] == []

    def test_create_mission_empty_name(self):
        result = create_mission("", "delivery", ["driver"])
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_create_mission_whitespace_name(self):
        result = create_mission("   ", "delivery", ["driver"])
        assert result["success"] is False

    def test_create_mission_invalid_type(self):
        result = create_mission("Op X", "heist", ["driver"])
        assert result["success"] is False
        assert "invalid mission type" in result["message"].lower()

    def test_create_mission_all_valid_types(self):
        for i, t in enumerate(["delivery", "rescue", "sabotage", "recon"]):
            result = create_mission(f"Op {i}", t, ["driver"])
            assert result["success"] is True

    def test_create_mission_empty_roles(self):
        result = create_mission("Op X", "delivery", [])
        assert result["success"] is False
        assert "at least one" in result["message"].lower()

    def test_create_mission_invalid_role(self):
        result = create_mission("Op X", "delivery", ["hacker"])
        assert result["success"] is False
        assert "invalid role" in result["message"].lower()

    def test_create_mission_duplicate_name(self):
        _mission("Op Nightfall")
        result = _mission("Op Nightfall")
        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    def test_create_mission_duplicate_name_case_insensitive(self):
        _mission("op nightfall")
        result = _mission("OP NIGHTFALL")
        assert result["success"] is False

    def test_create_mission_multiple_roles(self):
        result = create_mission("Op X", "rescue", ["driver", "mechanic"])
        assert result["success"] is True
        mission = get_mission("MI001")["mission"]
        assert "driver" in mission["required_roles"]
        assert "mechanic" in mission["required_roles"]

    def test_create_mission_unique_ids(self):
        r1 = _mission("Op A")
        r2 = create_mission("Op B", "recon", ["scout"])
        assert r1["mission_id"] != r2["mission_id"]


# ------------------------------------------------------------------
# get_mission
# ------------------------------------------------------------------

class TestGetMission:

    def test_get_existing_mission(self):
        _mission()
        result = get_mission("MI001")
        assert result["success"] is True
        assert result["mission"]["name"] == "Op Nightfall"

    def test_get_nonexistent_mission(self):
        result = get_mission("MI999")
        assert result["success"] is False
        assert result["mission"] is None

    def test_get_mission_case_insensitive(self):
        _mission()
        result = get_mission("mi001")
        assert result["success"] is True


# ------------------------------------------------------------------
# list_missions
# ------------------------------------------------------------------

class TestListMissions:

    def test_list_empty(self):
        result = list_missions()
        assert result["success"] is True
        assert result["missions"] == []

    def test_list_all(self):
        _mission("Op A")
        create_mission("Op B", "recon", ["scout"])
        result = list_missions()
        assert len(result["missions"]) == 2

    def test_list_filter_by_status(self):
        _mission("Op A")
        _mission("Op B")
        _reg("Dom", "driver")
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        result = list_missions(status_filter="active")
        assert len(result["missions"]) == 1

    def test_list_filter_invalid_status(self):
        result = list_missions(status_filter="pending")
        assert result["success"] is False

    def test_list_filter_by_type(self):
        _mission("Op A", "delivery")
        create_mission("Op B", "recon", ["scout"])
        result = list_missions(type_filter="recon")
        assert len(result["missions"]) == 1

    def test_list_filter_invalid_type(self):
        result = list_missions(type_filter="heist")
        assert result["success"] is False


# ------------------------------------------------------------------
# assign_crew_member
# ------------------------------------------------------------------

class TestAssignCrewMember:

    def test_assign_valid_member(self):
        _reg("Dom", "driver")
        _mission()
        result = assign_crew_member("MI001", "M001")
        assert result["success"] is True

    def test_assign_updates_mission(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        assert "M001" in get_mission("MI001")["mission"]["assigned_crew"]

    def test_assign_unregistered_member(self):
        _mission()
        result = assign_crew_member("MI001", "M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_assign_inactive_member(self):
        _reg("Dom", "driver")
        deactivate_member("M001")
        _mission()
        result = assign_crew_member("MI001", "M001")
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_assign_duplicate_member(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        result = assign_crew_member("MI001", "M001")
        assert result["success"] is False
        assert "already assigned" in result["message"].lower()

    def test_assign_to_nonexistent_mission(self):
        _reg("Dom", "driver")
        result = assign_crew_member("MI999", "M001")
        assert result["success"] is False

    def test_assign_to_active_mission_fails(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        _reg("Brian", "mechanic")
        result = assign_crew_member("MI001", "M002")
        assert result["success"] is False
        assert "planned" in result["message"].lower()

    def test_assign_multiple_members(self):
        _reg("Dom", "driver")
        _reg("Letty", "mechanic")
        _mission("Op X", "rescue", ["driver", "mechanic"])
        assign_crew_member("MI001", "M001")
        assign_crew_member("MI001", "M002")
        assert len(get_mission("MI001")["mission"]["assigned_crew"]) == 2


# ------------------------------------------------------------------
# remove_crew_member
# ------------------------------------------------------------------

class TestRemoveCrewMember:

    def test_remove_assigned_member(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        result = remove_crew_member("MI001", "M001")
        assert result["success"] is True
        assert "M001" not in get_mission("MI001")["mission"]["assigned_crew"]

    def test_remove_unassigned_member(self):
        _reg("Dom", "driver")
        _mission()
        result = remove_crew_member("MI001", "M001")
        assert result["success"] is False
        assert "not assigned" in result["message"].lower()

    def test_remove_from_nonexistent_mission(self):
        _reg("Dom", "driver")
        result = remove_crew_member("MI999", "M001")
        assert result["success"] is False

    def test_remove_from_active_mission_fails(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        result = remove_crew_member("MI001", "M001")
        assert result["success"] is False


# ------------------------------------------------------------------
# start_mission
# ------------------------------------------------------------------

class TestStartMission:

    def test_start_valid_mission(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        result = start_mission("MI001")
        assert result["success"] is True
        assert get_mission("MI001")["mission"]["status"] == "active"

    def test_start_mission_missing_role(self):
        _mission("Op X", "rescue", ["driver", "mechanic"])
        _reg("Dom", "driver")
        assign_crew_member("MI001", "M001")
        # mechanic not assigned
        result = start_mission("MI001")
        assert result["success"] is False
        assert "mechanic" in result["missing_roles"]

    def test_start_mission_no_crew(self):
        _mission()
        result = start_mission("MI001")
        assert result["success"] is False
        assert "driver" in result["missing_roles"]

    def test_start_mission_all_roles_covered(self):
        _reg("Dom", "driver")
        _reg("Letty", "mechanic")
        _mission("Op X", "rescue", ["driver", "mechanic"])
        assign_crew_member("MI001", "M001")
        assign_crew_member("MI001", "M002")
        result = start_mission("MI001")
        assert result["success"] is True
        assert result["missing_roles"] == []

    def test_start_nonexistent_mission(self):
        result = start_mission("MI999")
        assert result["success"] is False

    def test_start_already_active_mission_fails(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        result = start_mission("MI001")
        assert result["success"] is False
        assert "planned" in result["message"].lower()


# ------------------------------------------------------------------
# complete_mission
# ------------------------------------------------------------------

class TestCompleteMission:

    def test_complete_active_mission(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        result = complete_mission("MI001")
        assert result["success"] is True
        assert get_mission("MI001")["mission"]["status"] == "completed"

    def test_complete_planned_mission_fails(self):
        _mission()
        result = complete_mission("MI001")
        assert result["success"] is False
        assert "active" in result["message"].lower()

    def test_complete_nonexistent_mission(self):
        result = complete_mission("MI999")
        assert result["success"] is False

    def test_complete_already_completed_fails(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        complete_mission("MI001")
        result = complete_mission("MI001")
        assert result["success"] is False


# ------------------------------------------------------------------
# fail_mission
# ------------------------------------------------------------------

class TestFailMission:

    def test_fail_active_mission(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        result = fail_mission("MI001")
        assert result["success"] is True
        assert get_mission("MI001")["mission"]["status"] == "failed"

    def test_fail_planned_mission_fails(self):
        _mission()
        result = fail_mission("MI001")
        assert result["success"] is False
        assert "active" in result["message"].lower()

    def test_fail_nonexistent_mission(self):
        result = fail_mission("MI999")
        assert result["success"] is False

    def test_fail_already_completed_fails(self):
        _reg("Dom", "driver")
        _mission()
        assign_crew_member("MI001", "M001")
        start_mission("MI001")
        complete_mission("MI001")
        result = fail_mission("MI001")
        assert result["success"] is False


# ------------------------------------------------------------------
# check_roles_available
# ------------------------------------------------------------------

class TestCheckRolesAvailable:

    def test_all_roles_available(self):
        _reg("Dom", "driver")
        _reg("Letty", "mechanic")
        result = check_roles_available(["driver", "mechanic"])
        assert result["success"] is True
        assert result["missing_roles"] == []

    def test_missing_role(self):
        _reg("Dom", "driver")
        result = check_roles_available(["driver", "mechanic"])
        assert result["success"] is False
        assert "mechanic" in result["missing_roles"]

    def test_all_roles_missing(self):
        result = check_roles_available(["driver", "mechanic"])
        assert result["success"] is False
        assert len(result["missing_roles"]) == 2

    def test_inactive_member_not_counted(self):
        _reg("Dom", "driver")
        deactivate_member("M001")
        result = check_roles_available(["driver"])
        assert result["success"] is False
        assert "driver" in result["missing_roles"]

    def test_empty_required_roles(self):
        result = check_roles_available([])
        assert result["success"] is True
        assert result["missing_roles"] == []