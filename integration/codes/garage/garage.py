# garage/garage.py
# Tracks car conditions and manages repair jobs.
# Before a repair can begin, mechanic availability is verified.
# Depends on: Inventory, Crew Management, Mission Planning modules.

from shared.database import cars
from inventory.inventory import (
    update_car_condition,
    use_spare_parts,
    use_tools,
    get_car,
)
from crew_management.crew_management import get_available_mechanics
from mission_planning.mission_planning import check_roles_available


# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------

# Parts and tools consumed per repair job
PARTS_PER_REPAIR = 2
TOOLS_PER_REPAIR = 1


# ------------------------------------------------------------------
# CAR CONDITION OVERVIEW
# ------------------------------------------------------------------

def get_car_condition(car_id: str) -> dict:
    """
    Return the current condition of a car.

    Returns
    -------
    dict  {"success": True,  "car_id": str, "condition": str}
       or {"success": False, "car_id": None, "condition": None, "message": str}
    """
    car_id = car_id.strip().upper()
    result = get_car(car_id)
    if not result["success"]:
        return {
            **_fail(result["message"]),
            "car_id"    : None,
            "condition" : None,
        }
    return {
        "success"   : True,
        "car_id"    : car_id,
        "condition" : result["car"]["condition"],
    }


def list_damaged_cars() -> dict:
    """
    Return all cars currently in 'damaged' condition.

    Returns
    -------
    dict  {"success": True, "cars": list[dict]}
    """
    damaged = [
        {"id": cid, **data}
        for cid, data in cars.items()
        if data["condition"] == "damaged"
    ]
    return {"success": True, "cars": damaged}


def list_cars_under_repair() -> dict:
    """
    Return all cars currently in 'under_repair' condition.

    Returns
    -------
    dict  {"success": True, "cars": list[dict]}
    """
    under_repair = [
        {"id": cid, **data}
        for cid, data in cars.items()
        if data["condition"] == "under_repair"
    ]
    return {"success": True, "cars": under_repair}


# ------------------------------------------------------------------
# SEND CAR FOR REPAIR
# ------------------------------------------------------------------

def send_for_repair(car_id: str) -> dict:
    """
    Move a damaged car into 'under_repair' status.

    Rules
    -----
    - Car must exist and be in 'damaged' condition.
    - At least one active mechanic must be available (checked via
      Mission Planning's check_roles_available).
    - Car must not be currently assigned to a race.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    car_id = car_id.strip().upper()

    # Validate car exists
    car_result = get_car(car_id)
    if not car_result["success"]:
        return _fail(car_result["message"])

    car = car_result["car"]

    # Validate car is damaged
    if car["condition"] != "damaged":
        return _fail(
            f"Car '{car_id}' is in '{car['condition']}' condition. "
            f"Only damaged cars can be sent for repair."
        )

    # Validate car is not assigned to a race
    if car["assigned"]:
        return _fail(
            f"Car '{car_id}' is currently assigned to a race. "
            f"Cannot send it for repair while racing."
        )

    # Check mechanic availability via Mission Planning
    role_check = check_roles_available(["mechanic"])
    if not role_check["success"]:
        return _fail(
            f"Cannot send car '{car_id}' for repair. "
            f"No active mechanics available in the crew."
        )

    # Move to under_repair
    update_car_condition(car_id, "under_repair")
    mechanics = get_available_mechanics()

    return {
        "success" : True,
        "message" : (
            f"Car '{car_id}' sent for repair. "
            f"Assigned mechanic(s): {mechanics}."
        ),
    }


# ------------------------------------------------------------------
# COMPLETE REPAIR
# ------------------------------------------------------------------

def complete_repair(car_id: str) -> dict:
    """
    Complete a repair — moves car from 'under_repair' back to 'good'.

    Rules
    -----
    - Car must exist and be in 'under_repair' condition.
    - Consumes PARTS_PER_REPAIR spare parts and TOOLS_PER_REPAIR tools
      from Inventory. Repair fails if resources are insufficient.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    car_id = car_id.strip().upper()

    # Validate car exists
    car_result = get_car(car_id)
    if not car_result["success"]:
        return _fail(car_result["message"])

    car = car_result["car"]

    # Validate under_repair
    if car["condition"] != "under_repair":
        return _fail(
            f"Car '{car_id}' is in '{car['condition']}' condition. "
            f"Only cars under repair can be completed."
        )

    # Check spare parts availability
    parts_result = use_spare_parts(PARTS_PER_REPAIR)
    if not parts_result["success"]:
        return _fail(
            f"Repair failed for car '{car_id}'. "
            f"Insufficient spare parts: {parts_result['message']}"
        )

    # Check tools availability
    tools_result = use_tools(TOOLS_PER_REPAIR)
    if not tools_result["success"]:
        # Rollback parts usage by re-adding them
        from inventory.inventory import add_spare_parts
        add_spare_parts(PARTS_PER_REPAIR)
        return _fail(
            f"Repair failed for car '{car_id}'. "
            f"Insufficient tools: {tools_result['message']}"
        )

    # Mark car as good
    update_car_condition(car_id, "good")

    return {
        "success" : True,
        "message" : (
            f"Car '{car_id}' repair completed. "
            f"Consumed {PARTS_PER_REPAIR} spare parts and "
            f"{TOOLS_PER_REPAIR} tool(s). Car is now in 'good' condition."
        ),
    }


# ------------------------------------------------------------------
# FULL REPAIR PIPELINE (convenience)
# ------------------------------------------------------------------

def repair_car(car_id: str) -> dict:
    """
    Full pipeline: damaged → under_repair → good in one call.

    Combines send_for_repair + complete_repair.
    Useful for tests and CLI where you want to repair in one step.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    # Step 1 — send for repair
    send_result = send_for_repair(car_id)
    if not send_result["success"]:
        return send_result

    # Step 2 — complete repair
    complete_result = complete_repair(car_id)
    if not complete_result["success"]:
        # Rollback: car is now under_repair but repair couldn't complete
        # Leave it under_repair so caller knows it's in progress
        return {
            "success" : False,
            "message" : (
                f"Car '{car_id}' was sent for repair but could not be completed. "
                f"Reason: {complete_result['message']}"
            ),
        }

    return {
        "success" : True,
        "message" : f"Car '{car_id}' fully repaired and back in 'good' condition.",
    }


# ------------------------------------------------------------------
# GARAGE SUMMARY
# ------------------------------------------------------------------

def get_garage_summary() -> dict:
    """
    Return a summary of all cars grouped by condition.

    Returns
    -------
    dict  {
        "success"    : True,
        "good"       : list[dict],
        "damaged"    : list[dict],
        "under_repair": list[dict],
    }
    """
    good         = []
    damaged      = []
    under_repair = []

    for cid, data in cars.items():
        entry = {"id": cid, **data}
        if data["condition"] == "good":
            good.append(entry)
        elif data["condition"] == "damaged":
            damaged.append(entry)
        elif data["condition"] == "under_repair":
            under_repair.append(entry)

    return {
        "success"      : True,
        "good"         : good,
        "damaged"      : damaged,
        "under_repair" : under_repair,
    }


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _fail(message: str) -> dict:
    return {"success": False, "message": message}