# sponsorship/tests/test_sponsorship.py

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.database import reset_database
from registration.registration import register_member, deactivate_member
from inventory.inventory import add_car, get_cash_balance
from race_management.race_management import (
    create_race, enter_driver, assign_car, start_race,
)
from results.results import record_result
from sponsorship.sponsorship import (
    add_sponsor,
    get_sponsor,
    list_sponsors,
    claim_win_bonus,
    deactivate_sponsor,
    reactivate_sponsor,
    get_sponsorship_summary,
    _reset_claims,
    TIER_SEED_MONEY,
    TIER_BONUS_PER_WIN,
)


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    _reset_claims()
    yield
    reset_database()
    _reset_claims()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_driver(name="Dom"):
    return register_member(name, "driver")

def _make_car(name="Skyline"):
    return add_car(name, "good")

def _setup_completed_race(
    driver_name="Dom",
    car_name="Skyline",
    race_name="Street Kings",
    prize=500.0,
):
    """Register a driver, add a car, run a race to completion."""
    r    = _make_driver(driver_name)
    c    = _make_car(car_name)
    race = create_race(race_name)
    enter_driver(race["race_id"], r["member_id"])
    assign_car(race["race_id"], c["car_id"])
    start_race(race["race_id"])
    record_result(race["race_id"], [r["member_id"]], prize)
    return race["race_id"], r["member_id"]


# ==================================================================
# add_sponsor
# ==================================================================

class TestAddSponsor:

    def test_add_valid_sponsor_bronze(self):
        result = add_sponsor("SpeedCorp", "bronze")
        assert result["success"] is True
        assert result["sponsor_id"] == "SP001"

    def test_add_sponsor_all_tiers(self):
        for i, tier in enumerate(["bronze", "silver", "gold"]):
            result = add_sponsor(f"Corp {i}", tier)
            assert result["success"] is True, f"Failed for tier: {tier}"

    def test_seed_money_added_to_cash_on_creation(self):
        add_sponsor("SpeedCorp", "gold")
        assert get_cash_balance()["cash_balance"] == TIER_SEED_MONEY["gold"]

    def test_default_seed_money_bronze(self):
        add_sponsor("SpeedCorp", "bronze")
        assert get_cash_balance()["cash_balance"] == 500.0

    def test_default_seed_money_silver(self):
        add_sponsor("SpeedCorp", "silver")
        assert get_cash_balance()["cash_balance"] == 1500.0

    def test_default_seed_money_gold(self):
        add_sponsor("SpeedCorp", "gold")
        assert get_cash_balance()["cash_balance"] == 5000.0

    def test_custom_seed_money(self):
        add_sponsor("SpeedCorp", "bronze", seed_money=999.0)
        assert get_cash_balance()["cash_balance"] == 999.0

    def test_custom_bonus_per_win(self):
        add_sponsor("SpeedCorp", "bronze", bonus_per_win=250.0)
        s = get_sponsor("SP001")["sponsor"]
        assert s["bonus_per_win"] == 250.0

    def test_add_sponsor_with_driver(self):
        r = _make_driver()
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id=r["member_id"])
        assert result["success"] is True
        s = get_sponsor("SP001")["sponsor"]
        assert s["sponsored_driver_id"] == r["member_id"]

    def test_add_sponsor_nonexistent_driver(self):
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id="M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_add_sponsor_non_driver_role(self):
        register_member("Letty", "mechanic")
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id="M001")
        assert result["success"] is False
        assert "not a driver" in result["message"].lower()

    def test_add_sponsor_inactive_driver(self):
        r = _make_driver()
        deactivate_member(r["member_id"])
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id=r["member_id"])
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_add_sponsor_empty_name(self):
        result = add_sponsor("", "bronze")
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_add_sponsor_whitespace_name(self):
        result = add_sponsor("   ", "bronze")
        assert result["success"] is False

    def test_add_sponsor_invalid_tier(self):
        result = add_sponsor("SpeedCorp", "platinum")
        assert result["success"] is False
        assert "invalid tier" in result["message"].lower()

    def test_add_sponsor_duplicate_name(self):
        add_sponsor("SpeedCorp", "bronze")
        result = add_sponsor("SpeedCorp", "silver")
        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    def test_add_sponsor_duplicate_name_case_insensitive(self):
        add_sponsor("speedcorp", "bronze")
        result = add_sponsor("SPEEDCORP", "silver")
        assert result["success"] is False

    def test_add_sponsor_negative_seed_money(self):
        result = add_sponsor("SpeedCorp", "bronze", seed_money=-100.0)
        assert result["success"] is False

    def test_add_sponsor_negative_bonus(self):
        result = add_sponsor("SpeedCorp", "bronze", bonus_per_win=-50.0)
        assert result["success"] is False

    def test_add_sponsor_zero_seed_money_allowed(self):
        result = add_sponsor("SpeedCorp", "bronze", seed_money=0.0)
        assert result["success"] is True

    def test_sponsor_initial_status_is_active(self):
        add_sponsor("SpeedCorp", "bronze")
        s = get_sponsor("SP001")["sponsor"]
        assert s["status"] == "active"

    def test_sponsor_total_paid_equals_seed_on_creation(self):
        add_sponsor("SpeedCorp", "silver")
        s = get_sponsor("SP001")["sponsor"]
        assert s["total_paid"] == s["seed_money"]

    def test_multiple_sponsors_unique_ids(self):
        r1 = add_sponsor("Corp A", "bronze")
        r2 = add_sponsor("Corp B", "gold")
        assert r1["sponsor_id"] != r2["sponsor_id"]


# ==================================================================
# get_sponsor
# ==================================================================

class TestGetSponsor:

    def test_get_existing_sponsor(self):
        add_sponsor("SpeedCorp", "bronze")
        result = get_sponsor("SP001")
        assert result["success"] is True
        assert result["sponsor"]["name"] == "SpeedCorp"

    def test_get_nonexistent_sponsor(self):
        result = get_sponsor("SP999")
        assert result["success"] is False
        assert result["sponsor"] is None

    def test_get_sponsor_id_case_insensitive(self):
        add_sponsor("SpeedCorp", "bronze")
        result = get_sponsor("sp001")
        assert result["success"] is True

    def test_get_sponsor_fields_present(self):
        add_sponsor("SpeedCorp", "bronze")
        s = get_sponsor("SP001")["sponsor"]
        for field in ["name", "tier", "seed_money", "bonus_per_win",
                      "sponsored_driver_id", "status", "total_paid"]:
            assert field in s


# ==================================================================
# list_sponsors
# ==================================================================

class TestListSponsors:

    def test_list_empty(self):
        result = list_sponsors()
        assert result["success"] is True
        assert result["sponsors"] == []

    def test_list_all(self):
        add_sponsor("Corp A", "bronze")
        add_sponsor("Corp B", "gold")
        result = list_sponsors()
        assert len(result["sponsors"]) == 2

    def test_list_filter_by_tier(self):
        add_sponsor("Corp A", "bronze")
        add_sponsor("Corp B", "gold")
        result = list_sponsors(tier_filter="gold")
        assert len(result["sponsors"]) == 1
        assert result["sponsors"][0]["tier"] == "gold"

    def test_list_filter_invalid_tier(self):
        result = list_sponsors(tier_filter="diamond")
        assert result["success"] is False

    def test_list_filter_by_status_inactive(self):
        add_sponsor("Corp A", "bronze")
        add_sponsor("Corp B", "silver")
        deactivate_sponsor("SP001")
        result = list_sponsors(status_filter="inactive")
        assert len(result["sponsors"]) == 1
        assert result["sponsors"][0]["id"] == "SP001"

    def test_list_filter_invalid_status(self):
        result = list_sponsors(status_filter="pending")
        assert result["success"] is False


# ==================================================================
# claim_win_bonus
# ==================================================================

class TestClaimWinBonus:

    def test_claim_bonus_no_specific_driver(self):
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is True
        assert result["bonus_paid"] == TIER_BONUS_PER_WIN["bronze"]

    def test_bonus_added_to_cash_balance(self):
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "gold")
        balance_before = get_cash_balance()["cash_balance"]
        claim_win_bonus("SP001", race_id)
        assert get_cash_balance()["cash_balance"] == balance_before + TIER_BONUS_PER_WIN["gold"]

    def test_claim_with_correct_sponsored_driver(self):
        race_id, driver_id = _setup_completed_race()
        add_sponsor("SpeedCorp", "silver", sponsored_driver_id=driver_id)
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is True
        assert result["bonus_paid"] == TIER_BONUS_PER_WIN["silver"]

    def test_claim_with_wrong_sponsored_driver(self):
        race_id, _ = _setup_completed_race("Dom", "Car A", "Race A")
        r2 = register_member("Brian", "driver")
        add_sponsor("SpeedCorp", "silver", sponsored_driver_id=r2["member_id"])
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is False
        assert "did not win" in result["message"].lower()
        assert result["bonus_paid"] == 0.0

    def test_claim_duplicate_bonus_fails(self):
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")
        claim_win_bonus("SP001", race_id)
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is False
        assert "already claimed" in result["message"].lower()

    def test_claim_inactive_sponsor_fails(self):
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")
        deactivate_sponsor("SP001")
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_claim_nonexistent_sponsor(self):
        race_id, _ = _setup_completed_race()
        result = claim_win_bonus("SP999", race_id)
        assert result["success"] is False

    def test_claim_nonexistent_race(self):
        add_sponsor("SpeedCorp", "bronze")
        result = claim_win_bonus("SP001", "R999")
        assert result["success"] is False

    def test_claim_ongoing_race_fails(self):
        r = _make_driver()
        c = _make_car()
        create_race("Race A")
        enter_driver("R001", r["member_id"])
        assign_car("R001", c["car_id"])
        start_race("R001")
        add_sponsor("SpeedCorp", "bronze")
        result = claim_win_bonus("SP001", "R001")
        assert result["success"] is False
        assert "not completed" in result["message"].lower()

    def test_total_paid_increases_after_bonus(self):
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")
        before = get_sponsor("SP001")["sponsor"]["total_paid"]
        claim_win_bonus("SP001", race_id)
        after = get_sponsor("SP001")["sponsor"]["total_paid"]
        assert after == before + TIER_BONUS_PER_WIN["bronze"]

    def test_two_sponsors_claim_same_race(self):
        race_id, _ = _setup_completed_race()
        add_sponsor("Corp A", "bronze")
        add_sponsor("Corp B", "silver")
        r1 = claim_win_bonus("SP001", race_id)
        r2 = claim_win_bonus("SP002", race_id)
        assert r1["success"] is True
        assert r2["success"] is True


# ==================================================================
# deactivate / reactivate
# ==================================================================

class TestDeactivateReactivate:

    def test_deactivate_sponsor(self):
        add_sponsor("SpeedCorp", "bronze")
        result = deactivate_sponsor("SP001")
        assert result["success"] is True
        assert get_sponsor("SP001")["sponsor"]["status"] == "inactive"

    def test_deactivate_already_inactive(self):
        add_sponsor("SpeedCorp", "bronze")
        deactivate_sponsor("SP001")
        result = deactivate_sponsor("SP001")
        assert result["success"] is False
        assert "already inactive" in result["message"].lower()

    def test_reactivate_sponsor(self):
        add_sponsor("SpeedCorp", "bronze")
        deactivate_sponsor("SP001")
        result = reactivate_sponsor("SP001")
        assert result["success"] is True
        assert get_sponsor("SP001")["sponsor"]["status"] == "active"

    def test_reactivate_already_active(self):
        add_sponsor("SpeedCorp", "bronze")
        result = reactivate_sponsor("SP001")
        assert result["success"] is False
        assert "already active" in result["message"].lower()

    def test_deactivate_nonexistent(self):
        result = deactivate_sponsor("SP999")
        assert result["success"] is False

    def test_reactivate_nonexistent(self):
        result = reactivate_sponsor("SP999")
        assert result["success"] is False


# ==================================================================
# get_sponsorship_summary
# ==================================================================

class TestSponsorshipSummary:

    def test_empty_summary(self):
        result = get_sponsorship_summary()
        assert result["success"] is True
        assert result["sponsors"] == []
        assert result["total_contributed"] == 0.0

    def test_total_contributed_seed_only(self):
        add_sponsor("Corp A", "bronze")    # 500
        add_sponsor("Corp B", "silver")   # 1500
        result = get_sponsorship_summary()
        assert result["total_contributed"] == 2000.0

    def test_total_includes_win_bonuses(self):
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")   # 500 seed
        claim_win_bonus("SP001", race_id)    # +100 bonus
        result = get_sponsorship_summary()
        assert result["total_contributed"] == 600.0

    def test_summary_contains_all_sponsors(self):
        add_sponsor("Corp A", "bronze")
        add_sponsor("Corp B", "gold")
        result = get_sponsorship_summary()
        assert len(result["sponsors"]) == 2