# results/results.py
# Records race outcomes, updates driver rankings, handles prize money.
# Depends on: Race Management, Inventory modules.

from shared.database import (
    races,
    results,
    crew_members,
    cars,
    _next_id,
)
from race_management.race_management import complete_race
from inventory.inventory import add_cash, update_car_condition, set_car_assigned


# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------

MIN_PRIZE = 0.0


# ------------------------------------------------------------------
# RECORD RESULT
# ------------------------------------------------------------------

def record_result(
    race_id     : str,
    rankings    : list,
    prize_money : float,
    damages     : list = None,
) -> dict:
    """
    Record the result of an ongoing race.

    Parameters
    ----------
    race_id     : str         ID of the race (must be 'ongoing').
    rankings    : list[str]   Ordered list of driver member_ids (1st to last).
                              All must be entered drivers in this race.
    prize_money : float       Total prize money awarded. Must be >= 0.
    damages     : list[str]   Optional list of car_ids damaged during the race.
                              These cars will be set to 'damaged' in Inventory.

    Business rules
    --------------
    - Race must be 'ongoing'.
    - rankings must be non-empty.
    - Every member_id in rankings must be a driver entered in this race.
    - No duplicate driver in rankings.
    - prize_money must be a non-negative number.
    - damaged car_ids must belong to cars assigned to this race.
    - After recording:
        * Race status → 'completed' (via Race Management).
        * Prize money → added to Inventory cash balance.
        * Damaged cars → condition set to 'damaged' in Inventory.
        * All race cars → unassigned in Inventory.

    Returns
    -------
    dict  {"success": True,  "result_id": str, "message": str}
       or {"success": False, "result_id": None, "message": str}
    """
    if damages is None:
        damages = []

    race_id = race_id.strip().upper()

    # --- Validate race exists and is ongoing ---
    if race_id not in races:
        return _fail(f"No race found with ID '{race_id}'.")

    race = races[race_id]
    if race["status"] != "ongoing":
        return _fail(
            f"Race '{race_id}' is '{race['status']}'. "
            f"Results can only be recorded for ongoing races."
        )

    # --- Validate rankings non-empty ---
    if not rankings:
        return _fail("Rankings cannot be empty. Provide at least one driver.")

    # --- Validate no duplicates in rankings ---
    if len(rankings) != len(set(rankings)):
        return _fail("Rankings contain duplicate driver IDs.")

    # --- Validate all ranked drivers are entered in this race ---
    entered_drivers = set(race["driver_ids"])
    for mid in rankings:
        mid = mid.strip().upper()
        if mid not in entered_drivers:
            return _fail(
                f"Driver '{mid}' is not entered in race '{race_id}'. "
                f"Only entered drivers can be ranked."
            )

    # Normalize rankings to uppercase
    rankings = [mid.strip().upper() for mid in rankings]

    # --- Validate prize money ---
    if not isinstance(prize_money, (int, float)) or prize_money < MIN_PRIZE:
        return _fail(
            f"Prize money must be a non-negative number. Got '{prize_money}'."
        )

    # --- Validate damaged car_ids ---
    assigned_cars = set(race["car_ids"])
    damages = [cid.strip().upper() for cid in damages]
    for cid in damages:
        if cid not in assigned_cars:
            return _fail(
                f"Car '{cid}' is not assigned to race '{race_id}'. "
                f"Cannot mark it as damaged."
            )

    # ------------------------------------------------------------------
    # All validations passed — commit the result
    # ------------------------------------------------------------------

    # 1. Store result
    result_id = _next_id("RS", "result")
    results[race_id] = {
        "result_id"   : result_id,
        "winner_id"   : rankings[0],
        "rankings"    : rankings,
        "prize_money" : prize_money,
        "damages"     : damages,
    }

    # Link result back to race record
    races[race_id]["result"] = results[race_id]

    # 2. Complete the race (Race Management)
    complete_race(race_id)

    # 3. Add prize money to Inventory cash balance
    if prize_money > 0:
        add_cash(prize_money)

    # 4. Update damaged cars in Inventory
    for cid in damages:
        update_car_condition(cid, "damaged")

    # 5. Unassign all race cars from Inventory
    for cid in race["car_ids"]:
        set_car_assigned(cid, False)

    winner_name = crew_members[rankings[0]]["name"]
    return {
        "success"   : True,
        "result_id" : result_id,
        "message"   : (
            f"Result recorded for race '{race_id}'. "
            f"Winner: '{winner_name}'. "
            f"Prize: ${prize_money:.2f}. "
            f"Damages: {damages if damages else 'none'}."
        ),
    }


# ------------------------------------------------------------------
# READ RESULTS
# ------------------------------------------------------------------

def get_result(race_id: str) -> dict:
    """
    Fetch the recorded result for a race.

    Returns
    -------
    dict  {"success": True,  "result": dict}
       or {"success": False, "result": None, "message": str}
    """
    race_id = race_id.strip().upper()

    if race_id not in races:
        return {**_fail(f"No race found with ID '{race_id}'."), "result": None}

    if race_id not in results:
        return {
            **_fail(f"No result recorded yet for race '{race_id}'."),
            "result": None,
        }

    return {"success": True, "result": results[race_id]}


def list_results() -> dict:
    """
    Return all recorded race results.

    Returns
    -------
    dict  {"success": True, "results": list[dict]}
    """
    results_out = [
        {"race_id": race_id, **data}
        for race_id, data in results.items()
    ]
    return {"success": True, "results": results_out}


# ------------------------------------------------------------------
# RANKINGS & LEADERBOARD
# ------------------------------------------------------------------

def get_winner(race_id: str) -> dict:
    """
    Return the winner of a completed race.

    Returns
    -------
    dict  {"success": True,  "winner_id": str, "winner_name": str}
       or {"success": False, "winner_id": None, "message": str}
    """
    race_id = race_id.strip().upper()

    result = get_result(race_id)
    if not result["success"]:
        return {**result, "winner_id": None, "winner_name": None}

    winner_id   = result["result"]["winner_id"]
    winner_name = crew_members[winner_id]["name"]

    return {
        "success"     : True,
        "winner_id"   : winner_id,
        "winner_name" : winner_name,
    }


def get_leaderboard() -> dict:
    """
    Compute a win-count leaderboard across all completed races.
    Sorted by number of wins descending.

    Returns
    -------
    dict  {"success": True, "leaderboard": list[dict]}
    Each entry: {"member_id": str, "name": str, "wins": int}
    """
    win_counts = {}

    for data in results.values():
        winner_id = data["winner_id"]
        win_counts[winner_id] = win_counts.get(winner_id, 0) + 1

    leaderboard = [
        {
            "member_id" : mid,
            "name"      : crew_members[mid]["name"],
            "wins"      : wins,
        }
        for mid, wins in win_counts.items()
    ]

    leaderboard.sort(key=lambda x: x["wins"], reverse=True)

    return {"success": True, "leaderboard": leaderboard}


def get_driver_results(member_id: str) -> dict:
    """
    Return all race results where a specific driver participated.

    Returns
    -------
    dict  {"success": True,  "races": list[dict]}
       or {"success": False, "races": [], "message": str}
    """
    member_id = member_id.strip().upper()

    if member_id not in crew_members:
        return {
            **_fail(f"No crew member found with ID '{member_id}'."),
            "races": [],
        }

    driver_races = []
    for race_id, data in results.items():
        if member_id in data["rankings"]:
            position = data["rankings"].index(member_id) + 1
            driver_races.append({
                "race_id"    : race_id,
                "position"   : position,
                "prize_money": data["prize_money"],
                "winner_id"  : data["winner_id"],
            })

    return {"success": True, "races": driver_races}


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _fail(message: str) -> dict:
    return {"success": False, "result_id": None, "message": message}