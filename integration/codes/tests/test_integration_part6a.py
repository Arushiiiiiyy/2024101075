# tests/test_integration_part6a.py
# Integration Part 6a — + Sponsorship
#
# Tests cross-module sponsorship scenarios.
# conftest.py handles database reset automatically.

import pytest

from registration.registration import register_member, deactivate_member
from inventory.inventory import add_car, get_cash_balance
from race_management.race_management import (
    create_race, enter_driver, assign_car, start_race,
)
from results.results import record_result
from sponsorship.sponsorship import (
    add_sponsor, get_sponsor, list_sponsors,
    claim_win_bonus, deactivate_sponsor,
    reactivate_sponsor, get_sponsorship_summary,
    _reset_claims,
    TIER_SEED_MONEY, TIER_BONUS_PER_WIN,
)




def _driver(name="Dom"):
    return register_member(name, "driver")

def _car(name="Skyline"):
    return add_car(name, "good")

def _setup_completed_race(
    driver_name="Dom",
    car_name="Skyline",
    race_name="Street Kings",
    prize=500.0,
):
    """Full pipeline: register → car → race → result."""
    d    = _driver(driver_name)
    c    = _car(car_name)
    race = create_race(race_name)
    enter_driver(race["race_id"], d["member_id"])
    assign_car(race["race_id"], c["car_id"])
    start_race(race["race_id"])
    record_result(race["race_id"], [d["member_id"]], prize)
    return race["race_id"], d["member_id"]



# Sponsor seed money is immediately added to Inventory cash.
# Modules: Sponsorship → Inventory


class TestSeedMoneyUpdatesInventory:

    def test_bronze_seed_added_to_cash(self):
        """
        WHY: When a sponsor is added, seed money must flow
        directly into Inventory cash balance.
        """
        add_sponsor("SpeedCorp", "bronze")
        assert get_cash_balance()["cash_balance"] == TIER_SEED_MONEY["bronze"]

    def test_gold_seed_added_to_cash(self):
        """
        WHY: Verify seed money scales correctly with tier —
        gold tier must add more than bronze.
        """
        add_sponsor("SpeedCorp", "gold")
        assert get_cash_balance()["cash_balance"] == TIER_SEED_MONEY["gold"]

    def test_multiple_sponsors_seed_accumulates(self):
        """
        WHY: Multiple sponsors funding the crew must all add
        their seed money to the same cash balance.
        """
        add_sponsor("Corp A", "bronze")
        add_sponsor("Corp B", "silver")
        expected = TIER_SEED_MONEY["bronze"] + TIER_SEED_MONEY["silver"]
        assert get_cash_balance()["cash_balance"] == expected

    def test_custom_seed_money_added_correctly(self):
        """
        WHY: Custom seed money overrides tier default —
        must still flow into Inventory cash correctly.
        """
        add_sponsor("SpeedCorp", "bronze", seed_money=1234.0)
        assert get_cash_balance()["cash_balance"] == 1234.0



# Win bonus paid only after race is completed with correct winner.
# Modules: Sponsorship + Results + Inventory


class TestWinBonusAfterRace:

    def test_win_bonus_added_to_cash_after_race(self):
        """
        WHY: After a race is completed, claiming win bonus must
        add money to Inventory cash — full cross-module flow.
        """
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")
        balance_before = get_cash_balance()["cash_balance"]
        claim_win_bonus("SP001", race_id)
        expected = balance_before + TIER_BONUS_PER_WIN["bronze"]
        assert get_cash_balance()["cash_balance"] == expected

    def test_win_bonus_only_for_correct_sponsored_driver(self):
        """
        WHY: If sponsor backs a specific driver, bonus must only
        pay out when THAT driver wins — not any driver.
        """
        race_id, winner_id = _setup_completed_race("Dom", "Car A", "Race A")
        other = register_member("Brian", "driver")
        add_sponsor("SpeedCorp", "gold", sponsored_driver_id=other["member_id"])
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is False
        assert result["bonus_paid"] == 0.0

    def test_win_bonus_for_unsponsored_driver_pays_any_winner(self):
        """
        WHY: A sponsor with no specific driver must pay bonus
        regardless of which driver wins.
        """
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "silver")
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is True
        assert result["bonus_paid"] == TIER_BONUS_PER_WIN["silver"]

    def test_win_bonus_cannot_be_claimed_before_race_completes(self):
        """
        WHY: Bonus must not be claimable while race is ongoing —
        result must exist first.
        """
        d = _driver()
        c = _car()
        race = create_race("Race A")
        enter_driver(race["race_id"], d["member_id"])
        assign_car(race["race_id"], c["car_id"])
        start_race(race["race_id"])
        add_sponsor("SpeedCorp", "bronze")
        result = claim_win_bonus("SP001", race["race_id"])
        assert result["success"] is False
        assert "not completed" in result["message"].lower()

    def test_win_bonus_cannot_be_claimed_twice(self):
        """
        WHY: Double-claiming must be blocked — prevents sponsor
        being charged twice for the same race win.
        """
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")
        claim_win_bonus("SP001", race_id)
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is False
        assert "already claimed" in result["message"].lower()

    def test_two_sponsors_can_claim_same_race(self):
        """
        WHY: Multiple sponsors can each claim their own bonus
        for the same race — they are independent.
        """
        race_id, _ = _setup_completed_race()
        add_sponsor("Corp A", "bronze")
        add_sponsor("Corp B", "silver")
        r1 = claim_win_bonus("SP001", race_id)
        r2 = claim_win_bonus("SP002", race_id)
        assert r1["success"] is True
        assert r2["success"] is True



# Sponsor must back a registered active driver.
# Modules: Registration → Sponsorship


class TestSponsorDriverValidation:

    def test_sponsor_backs_registered_driver(self):
        """
        Sponsorship must verify the driver exists in
        Registration before accepting the sponsor deal.
        """
        d = _driver()
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id=d["member_id"])
        assert result["success"] is True

    def test_sponsor_cannot_back_unregistered_driver(self):
        """
        WHY: An unregistered driver ID must be rejected —
        Sponsorship depends on Registration data.
        """
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id="M999")
        assert result["success"] is False
        assert "not registered" in result["message"].lower()

    def test_sponsor_cannot_back_mechanic(self):
        """
        WHY: Only drivers can be sponsored — a mechanic ID
        must be rejected even if registered.
        """
        m = register_member("Letty", "mechanic")
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id=m["member_id"])
        assert result["success"] is False
        assert "not a driver" in result["message"].lower()

    def test_sponsor_cannot_back_inactive_driver(self):
        """
        WHY: Inactive drivers are not racing — sponsoring them
        makes no sense and must be rejected.
        """
        d = _driver()
        deactivate_member(d["member_id"])
        result = add_sponsor("SpeedCorp", "gold", sponsored_driver_id=d["member_id"])
        assert result["success"] is False
        assert "inactive" in result["message"].lower()



# Deactivated sponsor cannot claim bonuses.
# Modules: Sponsorship internal lifecycle


class TestSponsorLifecycle:

    def test_deactivated_sponsor_cannot_claim(self):
        """
        WHY: A sponsor that has been deactivated must not be
        able to claim any more win bonuses.
        """
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")
        deactivate_sponsor("SP001")
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_reactivated_sponsor_can_claim(self):
        """
        WHY: After reactivation, sponsor must be able to claim
        bonuses again — full lifecycle test.
        """
        race_id, _ = _setup_completed_race("Dom", "Car A", "Race A")
        add_sponsor("SpeedCorp", "bronze")
        deactivate_sponsor("SP001")
        reactivate_sponsor("SP001")
        result = claim_win_bonus("SP001", race_id)
        assert result["success"] is True


# ------------------------------------------------------------------
# SCENARIO 5
# Sponsorship summary reflects total money contributed.
# Modules: Sponsorship + Inventory
# ------------------------------------------------------------------

class TestSponsorshipSummaryIntegration:

    def test_summary_total_includes_seed_and_bonus(self):
        """
        WHY: Total contributed must count both seed money paid
        upfront AND all win bonuses claimed after races.
        """
        race_id, _ = _setup_completed_race()
        add_sponsor("SpeedCorp", "bronze")   # 500 seed
        claim_win_bonus("SP001", race_id)    # +100 bonus
        summary = get_sponsorship_summary()
        assert summary["total_contributed"] == 600.0

    def test_cash_balance_matches_all_sponsor_payments(self):
        """
        WHY: Everything sponsors pay must end up in Inventory
        cash — verifies end-to-end money flow.
        """
        race_id, _ = _setup_completed_race(prize=0.0)
        add_sponsor("Corp A", "bronze")   # 500
        add_sponsor("Corp B", "silver")  # 1500
        claim_win_bonus("SP001", race_id)  # +100
        claim_win_bonus("SP002", race_id)  # +300
        # total = 500 + 1500 + 100 + 300 = 2400
        assert get_cash_balance()["cash_balance"] == 2400.0