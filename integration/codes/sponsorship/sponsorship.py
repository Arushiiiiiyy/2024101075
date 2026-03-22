# sponsorship/sponsorship.py
# Manages sponsors who fund the crew.
# Sponsors provide seed money upfront and bonuses per race win.
# Depends on: Registration, Inventory, Results modules.

from shared.database import (
    sponsors,
    crew_members,
    _next_id,
    VALID_SPONSOR_TIERS,
)
from registration.registration import is_registered
from inventory.inventory import add_cash


# ------------------------------------------------------------------
# TIER DEFAULTS
# ------------------------------------------------------------------
TIER_SEED_MONEY = {
    "bronze" : 500.0,
    "silver" : 1500.0,
    "gold"   : 5000.0,
}

TIER_BONUS_PER_WIN = {
    "bronze" : 100.0,
    "silver" : 300.0,
    "gold"   : 1000.0,
}

# In-memory claim tracker — prevents double-claiming bonus for same race
_claimed_bonuses = set()


def _reset_claims():
    """Clear claim tracker. Called in test fixtures."""
    _claimed_bonuses.clear()


# ------------------------------------------------------------------
# ADD SPONSOR
# ------------------------------------------------------------------

def add_sponsor(name, tier, sponsored_driver_id=None, seed_money=None, bonus_per_win=None):
    name = name.strip()
    if not name:
        return _fail("Sponsor name cannot be empty.")

    tier = tier.strip().lower()
    if tier not in VALID_SPONSOR_TIERS:
        return _fail(f"Invalid tier '{tier}'. Valid tiers: {', '.join(sorted(VALID_SPONSOR_TIERS))}.")

    for s in sponsors.values():
        if s["name"].lower() == name.lower():
            return _fail(f"A sponsor named '{name}' already exists.")

    if sponsored_driver_id:
        sponsored_driver_id = sponsored_driver_id.strip().upper()
        if not is_registered(sponsored_driver_id):
            return _fail(f"Driver '{sponsored_driver_id}' is not registered.")
        member = crew_members[sponsored_driver_id]
        if member["role"] != "driver":
            return _fail(f"Member '{sponsored_driver_id}' is not a driver. Sponsors can only back drivers.")
        if member["status"] != "active":
            return _fail(f"Driver '{sponsored_driver_id}' is inactive. Cannot sponsor an inactive driver.")

    if seed_money is None:
        seed_money = TIER_SEED_MONEY[tier]
    if bonus_per_win is None:
        bonus_per_win = TIER_BONUS_PER_WIN[tier]

    if not isinstance(seed_money, (int, float)) or seed_money < 0:
        return _fail(f"Seed money must be a non-negative number. Got '{seed_money}'.")
    if not isinstance(bonus_per_win, (int, float)) or bonus_per_win < 0:
        return _fail(f"Bonus per win must be a non-negative number. Got '{bonus_per_win}'.")

    sponsor_id = _next_id("SP", "sponsor")
    sponsors[sponsor_id] = {
        "name"                : name,
        "tier"                : tier,
        "seed_money"          : seed_money,
        "bonus_per_win"       : bonus_per_win,
        "sponsored_driver_id" : sponsored_driver_id,
        "status"              : "active",
        "total_paid"          : seed_money,
    }

    add_cash(seed_money)

    return {
        "success"    : True,
        "sponsor_id" : sponsor_id,
        "message"    : (
            f"Sponsor '{name}' added (ID: {sponsor_id}, tier: {tier}). "
            f"Seed money ${seed_money:.2f} added to cash balance."
        ),
    }


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

def get_sponsor(sponsor_id):
    sponsor_id = sponsor_id.strip().upper()
    if sponsor_id not in sponsors:
        return {**_fail(f"No sponsor found with ID '{sponsor_id}'."), "sponsor": None}
    return {"success": True, "sponsor": sponsors[sponsor_id]}


def list_sponsors(tier_filter=None, status_filter=None):
    if tier_filter:
        tier_filter = tier_filter.strip().lower()
        if tier_filter not in VALID_SPONSOR_TIERS:
            return {**_fail(f"Invalid tier filter '{tier_filter}'."), "sponsors": []}

    if status_filter:
        status_filter = status_filter.strip().lower()
        if status_filter not in {"active", "inactive"}:
            return {**_fail(f"Invalid status filter '{status_filter}'."), "sponsors": []}

    out = []
    for sid, data in sponsors.items():
        if tier_filter and data["tier"] != tier_filter:
            continue
        if status_filter and data["status"] != status_filter:
            continue
        out.append({"id": sid, **data})

    return {"success": True, "sponsors": out}


# ------------------------------------------------------------------
# WIN BONUS
# ------------------------------------------------------------------

def claim_win_bonus(sponsor_id, race_id):
    from shared.database import results, races

    sponsor_id = sponsor_id.strip().upper()
    race_id    = race_id.strip().upper()

    if sponsor_id not in sponsors:
        return {**_fail(f"No sponsor found with ID '{sponsor_id}'."), "bonus_paid": 0.0}

    sponsor = sponsors[sponsor_id]
    if sponsor["status"] != "active":
        return {**_fail(f"Sponsor '{sponsor_id}' is inactive."), "bonus_paid": 0.0}

    if race_id not in races:
        return {**_fail(f"No race found with ID '{race_id}'."), "bonus_paid": 0.0}

    if races[race_id]["status"] != "completed":
        return {**_fail(f"Race '{race_id}' is not completed yet."), "bonus_paid": 0.0}

    if race_id not in results:
        return {**_fail(f"No result recorded for race '{race_id}'."), "bonus_paid": 0.0}

    claim_key = f"{sponsor_id}_{race_id}"
    if claim_key in _claimed_bonuses:
        return {**_fail(f"Win bonus for race '{race_id}' already claimed by sponsor '{sponsor_id}'."), "bonus_paid": 0.0}

    winner_id = results[race_id]["winner_id"]

    if sponsor["sponsored_driver_id"]:
        if winner_id != sponsor["sponsored_driver_id"]:
            return {
                **_fail(
                    f"Sponsored driver '{sponsor['sponsored_driver_id']}' "
                    f"did not win race '{race_id}'. No bonus paid."
                ),
                "bonus_paid": 0.0,
            }

    bonus = sponsor["bonus_per_win"]
    add_cash(bonus)
    sponsors[sponsor_id]["total_paid"] += bonus
    _claimed_bonuses.add(claim_key)

    winner_name = crew_members[winner_id]["name"]
    return {
        "success"    : True,
        "message"    : (
            f"Win bonus of ${bonus:.2f} claimed for race '{race_id}'. "
            f"Winner: '{winner_name}'. Total paid by '{sponsor['name']}': "
            f"${sponsors[sponsor_id]['total_paid']:.2f}."
        ),
        "bonus_paid" : bonus,
    }


# ------------------------------------------------------------------
# DEACTIVATE / REACTIVATE
# ------------------------------------------------------------------

def deactivate_sponsor(sponsor_id):
    sponsor_id = sponsor_id.strip().upper()
    if sponsor_id not in sponsors:
        return _fail(f"No sponsor found with ID '{sponsor_id}'.")
    if sponsors[sponsor_id]["status"] == "inactive":
        return _fail(f"Sponsor '{sponsor_id}' is already inactive.")
    sponsors[sponsor_id]["status"] = "inactive"
    return {"success": True, "message": f"Sponsor '{sponsors[sponsor_id]['name']}' deactivated."}


def reactivate_sponsor(sponsor_id):
    sponsor_id = sponsor_id.strip().upper()
    if sponsor_id not in sponsors:
        return _fail(f"No sponsor found with ID '{sponsor_id}'.")
    if sponsors[sponsor_id]["status"] == "active":
        return _fail(f"Sponsor '{sponsor_id}' is already active.")
    sponsors[sponsor_id]["status"] = "active"
    return {"success": True, "message": f"Sponsor '{sponsors[sponsor_id]['name']}' reactivated."}


# ------------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------------

def get_sponsorship_summary():
    total = sum(s["total_paid"] for s in sponsors.values())
    return {
        "success"           : True,
        "sponsors"          : [{"id": sid, **data} for sid, data in sponsors.items()],
        "total_contributed" : total,
    }


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _fail(message):
    return {"success": False, "sponsor_id": None, "message": message}