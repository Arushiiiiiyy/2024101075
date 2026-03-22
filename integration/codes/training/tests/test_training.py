# training/tests/test_training.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import register_member, deactivate_member
from crew_management.crew_management import set_skill_level
from training.training import (
    conduct_session,
    get_session,
    get_member_sessions,
    list_all_sessions,
    get_skill_summary,
    get_top_drivers,
    get_total_sessions_count,
)


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield
    reset_database()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _reg(name="Dom", role="driver"):
    return register_member(name, role)


# ------------------------------------------------------------------
# conduct_session
# ------------------------------------------------------------------

class TestConductSession:

    def test_conduct_valid_session(self):
        r = _reg()
        result = conduct_session(r["member_id"])
        assert result["success"] is True
        assert result["session_id"] is not None

    def test_skill_increases_by_default(self):
        r = _reg()
        result = conduct_session(r["member_id"])
        assert result["old_skill"] == 1
        assert result["new_skill"] == 2

    def test_skill_gain_custom(self):
        r = _reg()
        result = conduct_session(r["member_id"], skill_gain=3)
        assert result["new_skill"] == 4

    def test_skill_gain_1(self):
        r = _reg()
        result = conduct_session(r["member_id"], skill_gain=1)
        assert result["success"] is True
        assert result["new_skill"] == 2

    def test_skill_gain_max_per_session(self):
        r = _reg()
        result = conduct_session(r["member_id"], skill_gain=3)
        assert result["success"] is True

    def test_skill_gain_above_max_per_session_fails(self):
        r = _reg()
        result = conduct_session(r["member_id"], skill_gain=4)
        assert result["success"] is False
        assert "between 1 and 3" in result["message"].lower()

    def test_skill_gain_zero_fails(self):
        r = _reg()
        result = conduct_session(r["member_id"], skill_gain=0)
        assert result["success"] is False

    def test_skill_gain_negative_fails(self):
        r = _reg()
        result = conduct_session(r["member_id"], skill_gain=-1)
        assert result["success"] is False

    def test_skill_gain_non_integer_fails(self):
        r = _reg()
        result = conduct_session(r["member_id"], skill_gain=1.5)
        assert result["success"] is False

    def test_session_at_max_skill_no_gain(self):
        r = _reg()
        set_skill_level(r["member_id"], 10)
        result = conduct_session(r["member_id"])
        assert result["success"] is True
        assert result["new_skill"] == 10
        assert result["old_skill"] == 10
        assert "maximum" in result["message"].lower()

    def test_session_caps_at_skill_max(self):
        r = _reg()
        set_skill_level(r["member_id"], 9)
        result = conduct_session(r["member_id"], skill_gain=3)
        assert result["new_skill"] == 10   # capped at 10

    def test_unregistered_member_fails(self):
        result = conduct_session("M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_inactive_member_fails(self):
        r = _reg()
        deactivate_member(r["member_id"])
        result = conduct_session(r["member_id"])
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_session_with_notes(self):
        r = _reg()
        result = conduct_session(r["member_id"], notes="Focused on cornering")
        assert result["success"] is True
        session = get_session(result["session_id"])
        assert session["session"]["notes"] == "Focused on cornering"

    def test_multiple_sessions_accumulate(self):
        r = _reg()
        conduct_session(r["member_id"], skill_gain=2)
        result = conduct_session(r["member_id"], skill_gain=2)
        assert result["new_skill"] == 5   # 1 + 2 + 2

    def test_session_logged_even_at_max(self):
        r = _reg()
        set_skill_level(r["member_id"], 10)
        result = conduct_session(r["member_id"])
        assert result["session_id"] is not None
        session = get_session(result["session_id"])
        assert session["success"] is True
        assert session["session"]["skill_gained"] == 0


# ------------------------------------------------------------------
# get_session
# ------------------------------------------------------------------

class TestGetSession:

    def test_get_existing_session(self):
        r = _reg()
        result = conduct_session(r["member_id"])
        session = get_session(result["session_id"])
        assert session["success"] is True
        assert session["session"]["member_id"] == r["member_id"]

    def test_get_nonexistent_session(self):
        result = get_session("T999")
        assert result["success"] is False
        assert result["session"] is None


# ------------------------------------------------------------------
# get_member_sessions
# ------------------------------------------------------------------

class TestGetMemberSessions:

    def test_no_sessions(self):
        r = _reg()
        result = get_member_sessions(r["member_id"])
        assert result["success"] is True
        assert result["sessions"] == []

    def test_one_session(self):
        r = _reg()
        conduct_session(r["member_id"])
        result = get_member_sessions(r["member_id"])
        assert len(result["sessions"]) == 1

    def test_multiple_sessions(self):
        r = _reg()
        conduct_session(r["member_id"])
        conduct_session(r["member_id"])
        conduct_session(r["member_id"])
        result = get_member_sessions(r["member_id"])
        assert len(result["sessions"]) == 3

    def test_sessions_only_for_this_member(self):
        r1 = _reg("Dom", "driver")
        r2 = register_member("Brian", "driver")
        conduct_session(r1["member_id"])
        conduct_session(r1["member_id"])
        conduct_session(r2["member_id"])
        result = get_member_sessions(r1["member_id"])
        assert len(result["sessions"]) == 2

    def test_unregistered_member_fails(self):
        result = get_member_sessions("M999")
        assert result["success"] is False
        assert result["sessions"] == []


# ------------------------------------------------------------------
# list_all_sessions
# ------------------------------------------------------------------

class TestListAllSessions:

    def test_empty(self):
        result = list_all_sessions()
        assert result["success"] is True
        assert result["sessions"] == []

    def test_all_sessions_returned(self):
        r1 = _reg("Dom", "driver")
        r2 = register_member("Brian", "driver")
        conduct_session(r1["member_id"])
        conduct_session(r2["member_id"])
        result = list_all_sessions()
        assert len(result["sessions"]) == 2


# ------------------------------------------------------------------
# get_skill_summary
# ------------------------------------------------------------------

class TestGetSkillSummary:

    def test_empty_summary(self):
        result = get_skill_summary()
        assert result["success"] is True
        assert result["members"] == []

    def test_sorted_by_skill_descending(self):
        r1 = _reg("Dom", "driver")
        r2 = register_member("Brian", "driver")
        set_skill_level(r1["member_id"], 3)
        set_skill_level(r2["member_id"], 7)
        result = get_skill_summary()
        skills = [m["skill_level"] for m in result["members"]]
        assert skills == sorted(skills, reverse=True)

    def test_summary_includes_all_roles(self):
        _reg("Dom", "driver")
        register_member("Letty", "mechanic")
        result = get_skill_summary()
        assert len(result["members"]) == 2

    def test_summary_fields_present(self):
        _reg()
        member = get_skill_summary()["members"][0]
        for field in ["id", "name", "role", "skill_level", "status"]:
            assert field in member


# ------------------------------------------------------------------
# get_top_drivers
# ------------------------------------------------------------------

class TestGetTopDrivers:

    def test_top_3_drivers(self):
        for i, name in enumerate(["A", "B", "C", "D"]):
            r = register_member(name, "driver")
            set_skill_level(r["member_id"], i + 1)
        result = get_top_drivers(3)
        assert result["success"] is True
        assert len(result["drivers"]) == 3

    def test_top_drivers_sorted_by_skill(self):
        r1 = _reg("Dom", "driver")
        r2 = register_member("Brian", "driver")
        set_skill_level(r1["member_id"], 5)
        set_skill_level(r2["member_id"], 9)
        result = get_top_drivers(2)
        assert result["drivers"][0]["skill_level"] >= result["drivers"][1]["skill_level"]

    def test_top_drivers_excludes_non_drivers(self):
        _reg("Dom", "driver")
        register_member("Letty", "mechanic")
        result = get_top_drivers(5)
        assert all(d["id"] != "M002" for d in result["drivers"])

    def test_top_drivers_excludes_inactive(self):
        r = _reg("Dom", "driver")
        deactivate_member(r["member_id"])
        result = get_top_drivers(3)
        assert result["drivers"] == []

    def test_top_drivers_fewer_than_n(self):
        _reg("Dom", "driver")
        result = get_top_drivers(5)
        assert len(result["drivers"]) == 1

    def test_top_drivers_invalid_n_zero(self):
        result = get_top_drivers(0)
        assert result["success"] is False

    def test_top_drivers_invalid_n_negative(self):
        result = get_top_drivers(-1)
        assert result["success"] is False

    def test_top_drivers_empty(self):
        result = get_top_drivers(3)
        assert result["drivers"] == []


# ------------------------------------------------------------------
# get_total_sessions_count
# ------------------------------------------------------------------

class TestGetTotalSessionsCount:

    def test_zero_sessions(self):
        r = _reg()
        result = get_total_sessions_count(r["member_id"])
        assert result["success"] is True
        assert result["count"] == 0

    def test_counts_correctly(self):
        r = _reg()
        conduct_session(r["member_id"])
        conduct_session(r["member_id"])
        result = get_total_sessions_count(r["member_id"])
        assert result["count"] == 2

    def test_counts_only_this_member(self):
        r1 = _reg("Dom", "driver")
        r2 = register_member("Brian", "driver")
        conduct_session(r1["member_id"])
        conduct_session(r2["member_id"])
        conduct_session(r2["member_id"])
        assert get_total_sessions_count(r1["member_id"])["count"] == 1
        assert get_total_sessions_count(r2["member_id"])["count"] == 2

    def test_unregistered_member_fails(self):
        result = get_total_sessions_count("M999")
        assert result["success"] is False
        assert result["count"] == 0