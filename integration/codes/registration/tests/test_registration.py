# registration/tests/test_registration.py

import pytest
import sys
import os

# Make sure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import (
    register_member,
    get_member,
    list_members,
    is_registered,
    deactivate_member,
    reactivate_member,
)


@pytest.fixture(autouse=True)
def clean_db():
    """Reset the shared database before every test."""
    reset_database()
    yield
    reset_database()


# ------------------------------------------------------------------
# register_member
# ------------------------------------------------------------------

class TestRegisterMember:

    def test_register_valid_driver(self):
        result = register_member("Dom Toretto", "driver")
        assert result["success"] is True
        assert result["member_id"] == "M001"
        assert "driver" in result["message"]

    def test_register_valid_mechanic(self):
        result = register_member("Letty Ortiz", "mechanic")
        assert result["success"] is True
        assert result["member_id"] is not None

    def test_register_all_valid_roles(self):
        roles = ["driver", "mechanic", "strategist", "scout", "trainer"]
        for i, role in enumerate(roles):
            r = register_member(f"Member {i}", role)
            assert r["success"] is True, f"Failed for role: {role}"

    def test_register_empty_name(self):
        result = register_member("", "driver")
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_register_whitespace_name(self):
        result = register_member("   ", "driver")
        assert result["success"] is False

    def test_register_invalid_role(self):
        result = register_member("Ghost Rider", "racer")
        assert result["success"] is False
        assert "invalid role" in result["message"].lower()

    def test_register_duplicate_name(self):
        register_member("Dom Toretto", "driver")
        result = register_member("Dom Toretto", "mechanic")
        assert result["success"] is False
        assert "already registered" in result["message"].lower()

    def test_register_duplicate_name_case_insensitive(self):
        register_member("dom toretto", "driver")
        result = register_member("DOM TORETTO", "mechanic")
        assert result["success"] is False

    def test_register_role_case_insensitive(self):
        result = register_member("Fast Brian", "DRIVER")
        assert result["success"] is True

    def test_registered_member_has_skill_level_1(self):
        register_member("Tej Parker", "mechanic")
        member = get_member("M001")
        assert member["member"]["skill_level"] == 1

    def test_registered_member_status_is_active(self):
        register_member("Roman Pearce", "strategist")
        member = get_member("M001")
        assert member["member"]["status"] == "active"

    def test_multiple_registrations_get_unique_ids(self):
        r1 = register_member("Alpha", "driver")
        r2 = register_member("Beta", "mechanic")
        assert r1["member_id"] != r2["member_id"]


# ------------------------------------------------------------------
# get_member
# ------------------------------------------------------------------

class TestGetMember:

    def test_get_existing_member(self):
        register_member("Han Seoul-Oh", "driver")
        result = get_member("M001")
        assert result["success"] is True
        assert result["member"]["name"] == "Han Seoul-Oh"

    def test_get_nonexistent_member(self):
        result = get_member("M999")
        assert result["success"] is False
        assert result["member"] is None

    def test_get_member_id_case_insensitive(self):
        register_member("Gisele", "strategist")
        result = get_member("m001")
        assert result["success"] is True


# ------------------------------------------------------------------
# list_members
# ------------------------------------------------------------------

class TestListMembers:

    def test_list_empty(self):
        result = list_members()
        assert result["success"] is True
        assert result["members"] == []

    def test_list_all(self):
        register_member("Alpha", "driver")
        register_member("Beta", "mechanic")
        result = list_members()
        assert len(result["members"]) == 2

    def test_list_filter_by_role(self):
        register_member("Alpha", "driver")
        register_member("Beta", "mechanic")
        register_member("Gamma", "driver")
        result = list_members(role_filter="driver")
        assert len(result["members"]) == 2
        for m in result["members"]:
            assert m["role"] == "driver"

    def test_list_filter_invalid_role(self):
        result = list_members(role_filter="ghost")
        assert result["success"] is False

    def test_list_filter_by_status(self):
        register_member("Alpha", "driver")
        register_member("Beta", "mechanic")
        deactivate_member("M001")
        result = list_members(status_filter="inactive")
        assert len(result["members"]) == 1
        assert result["members"][0]["name"] == "Alpha"


# ------------------------------------------------------------------
# is_registered
# ------------------------------------------------------------------

class TestIsRegistered:

    def test_is_registered_true(self):
        register_member("Luke Hobbs", "driver")
        assert is_registered("M001") is True

    def test_is_registered_false(self):
        assert is_registered("M999") is False


# ------------------------------------------------------------------
# deactivate / reactivate
# ------------------------------------------------------------------

class TestDeactivateReactivate:

    def test_deactivate_member(self):
        register_member("Deckard Shaw", "strategist")
        result = deactivate_member("M001")
        assert result["success"] is True
        assert get_member("M001")["member"]["status"] == "inactive"

    def test_deactivate_nonexistent(self):
        result = deactivate_member("M999")
        assert result["success"] is False

    def test_deactivate_already_inactive(self):
        register_member("Ramsey", "strategist")
        deactivate_member("M001")
        result = deactivate_member("M001")
        assert result["success"] is False
        assert "already inactive" in result["message"].lower()

    def test_reactivate_member(self):
        register_member("Owen Shaw", "driver")
        deactivate_member("M001")
        result = reactivate_member("M001")
        assert result["success"] is True
        assert get_member("M001")["member"]["status"] == "active"

    def test_reactivate_already_active(self):
        register_member("Elena Neves", "scout")
        result = reactivate_member("M001")
        assert result["success"] is False
        assert "already active" in result["message"].lower()

    def test_reactivate_nonexistent(self):
        result = reactivate_member("M999")
        assert result["success"] is False