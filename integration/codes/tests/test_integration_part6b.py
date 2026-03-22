# tests/test_integration_part6b.py
# Integration Part 6b — + Training
#
# Tests cross-module training scenarios.
# conftest.py handles database reset automatically.

import pytest

from registration.registration import register_member, deactivate_member
from crew_management.crew_management import get_skill_level, set_skill_level
from inventory.inventory import add_car
from race_management.race_management import (
    create_race, enter_driver, assign_car, start_race,
)
from results.results import record_result
from training.training import (
    conduct_session,
    get_session,
    get_member_sessions,
    get_skill_summary,
    get_top_drivers,
    get_total_sessions_count,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _driver(name="Dom"):
    return register_member(name, "driver")

def _mechanic(name="Letty"):
    return register_member(name, "mechanic")

def _setup_completed_race(driver_name="Dom", car_name="Skyline"):
    d    = _driver(driver_name)
    c    = add_car(car_name, "good")
    race = create_race("Street Kings")
    enter_driver(race["race_id"], d["member_id"])
    assign_car(race["race_id"], c["car_id"])
    start_race(race["race_id"])
    record_result(race["race_id"], [d["member_id"]], 500.0)
    return d["member_id"]


# Member must be registered before training.
# Modules: Registration → Training


class TestRegistrationGatesTraining:

    def test_registered_member_can_train(self):
        """
        WHY: Training must check Registration before allowing
        a session — core dependency between modules.
        """
        d = _driver()
        result = conduct_session(d["member_id"])
        assert result["success"] is True

    def test_unregistered_member_cannot_train(self):
        """
        WHY: Training must reject sessions for members that
        don't exist in Registration.
        """
        result = conduct_session("M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_inactive_member_cannot_train(self):
        """
        WHY: Deactivated members must be excluded from training
        just as they are excluded from races and missions.
        """
        d = _driver()
        deactivate_member(d["member_id"])
        result = conduct_session(d["member_id"])
        assert result["success"] is False
        assert "inactive" in result["message"].lower()



# Training increases skill level via Crew Management.
# Modules: Training → Crew Management


class TestTrainingUpdatesSkillLevel:

    def test_session_increases_skill_in_crew_management(self):
        """
        WHY: Skill gain from training must be reflected in
        Crew Management's skill_level — tests shared state.
        """
        d = _driver()
        conduct_session(d["member_id"], skill_gain=2)
        assert get_skill_level(d["member_id"])["skill_level"] == 3

    def test_multiple_sessions_accumulate_skill(self):
        """
        WHY: Skill must compound across multiple sessions —
        verifies Training and Crew Management stay in sync.
        """
        d = _driver()
        conduct_session(d["member_id"], skill_gain=2)
        conduct_session(d["member_id"], skill_gain=3)
        assert get_skill_level(d["member_id"])["skill_level"] == 6

    def test_skill_capped_at_10_across_modules(self):
        """
        WHY: Skill cap must be enforced consistently whether
        set via Crew Management or Training.
        """
        d = _driver()
        set_skill_level(d["member_id"], 9)
        result = conduct_session(d["member_id"], skill_gain=3)
        assert result["new_skill"] == 10
        assert get_skill_level(d["member_id"])["skill_level"] == 10

    def test_session_at_max_skill_logs_but_no_change(self):
        """
        WHY: Training at max skill must still log the session
        but not alter skill level in Crew Management.
        """
        d = _driver()
        set_skill_level(d["member_id"], 10)
        result = conduct_session(d["member_id"])
        assert result["success"] is True
        assert result["new_skill"] == 10
        assert get_skill_level(d["member_id"])["skill_level"] == 10



# get_top_drivers() reflects training and crew management state.
# Modules: Training + Crew Management + Registration


class TestTopDriversReflectsTraining:

    def test_top_drivers_sorted_by_skill_after_training(self):
        """
        WHY: After training, get_top_drivers() must return
        drivers in correct skill order — used in race selection.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")
        d3 = register_member("Tej", "driver")

        conduct_session(d1["member_id"], skill_gain=3)  # skill 4
        conduct_session(d2["member_id"], skill_gain=1)  # skill 2
        # d3 stays at 1

        result = get_top_drivers(3)
        assert result["success"] is True
        skills = [d["skill_level"] for d in result["drivers"]]
        assert skills == sorted(skills, reverse=True)
        assert skills[0] == 4

    def test_inactive_driver_excluded_from_top_drivers(self):
        """
        WHY: Deactivated drivers must not appear in top drivers
        even if they have high skill from training.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")

        set_skill_level(d1["member_id"], 9)
        set_skill_level(d2["member_id"], 3)

        deactivate_member(d1["member_id"])

        result = get_top_drivers(3)
        ids = [d["id"] for d in result["drivers"]]
        assert d1["member_id"] not in ids
        assert d2["member_id"] in ids

    def test_non_drivers_excluded_from_top_drivers(self):
        """
        WHY: Mechanics and other roles trained must not appear
        in get_top_drivers() — only drivers qualify.
        """
        d = _driver("Dom")
        m = _mechanic("Letty")

        set_skill_level(m["member_id"], 10)
        conduct_session(d["member_id"], skill_gain=1)

        result = get_top_drivers(5)
        ids = [dr["id"] for dr in result["drivers"]]
        assert m["member_id"] not in ids
        assert d["member_id"] in ids



# Training session history is tracked correctly.
# Modules: Registration + Training


class TestSessionHistoryTracking:

    def test_session_count_increases_per_member(self):
        """
        WHY: Each training session must be logged and
        retrievable — tests persistent tracking.
        """
        d = _driver()
        conduct_session(d["member_id"])
        conduct_session(d["member_id"])
        conduct_session(d["member_id"])
        assert get_total_sessions_count(d["member_id"])["count"] == 3

    def test_session_history_isolated_per_member(self):
        """
        WHY: One member's training must not affect another's
        session count — verifies clean isolation.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")

        conduct_session(d1["member_id"])
        conduct_session(d1["member_id"])
        conduct_session(d2["member_id"])

        assert get_total_sessions_count(d1["member_id"])["count"] == 2
        assert get_total_sessions_count(d2["member_id"])["count"] == 1

    def test_session_notes_stored_correctly(self):
        """
        WHY: Session notes must be retrievable — useful for
        tracking what was practiced in each session.
        """
        d = _driver()
        result = conduct_session(d["member_id"], notes="Cornering drills")
        session = get_session(result["session_id"])
        assert session["session"]["notes"] == "Cornering drills"

    def test_member_sessions_list_accurate(self):
        """
        WHY: get_member_sessions() must return all sessions
        for a specific member only — not other members.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")
        conduct_session(d1["member_id"])
        conduct_session(d1["member_id"])
        conduct_session(d2["member_id"])
        sessions = get_member_sessions(d1["member_id"])["sessions"]
        assert len(sessions) == 2
        assert all(s["member_id"] == d1["member_id"] for s in sessions)



# get_skill_summary() reflects combined state of both modules.
# Modules: Training + Crew Management + Registration


class TestSkillSummaryIntegration:

    def test_skill_summary_sorted_by_skill(self):
        """
        WHY: Skill summary is used to see who the most
        skilled crew members are — must be in correct order.
        """
        d1 = _driver("Dom")
        d2 = register_member("Brian", "driver")
        m  = _mechanic("Letty")

        conduct_session(d1["member_id"], skill_gain=3)
        conduct_session(d2["member_id"], skill_gain=1)

        summary = get_skill_summary()["members"]
        skills = [m["skill_level"] for m in summary]
        assert skills == sorted(skills, reverse=True)

    def test_skill_summary_includes_all_roles(self):
        """
        WHY: Summary must show all crew regardless of role —
        not just drivers.
        """
        _driver("Dom")
        _mechanic("Letty")
        register_member("Tej", "strategist")
        summary = get_skill_summary()["members"]
        assert len(summary) == 3

    def test_skill_summary_reflects_latest_training(self):
        """
        WHY: Summary must always show the most up-to-date skill
        level after each training session.
        """
        d = _driver()
        conduct_session(d["member_id"], skill_gain=3)
        conduct_session(d["member_id"], skill_gain=2)
        summary = get_skill_summary()["members"]
        dom = next(m for m in summary if m["id"] == d["member_id"])
        assert dom["skill_level"] == 6