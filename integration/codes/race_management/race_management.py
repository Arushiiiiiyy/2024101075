# race_management/race_management.py
# Creates races, selects drivers and cars, and manages race lifecycle.
# Depends on: Registration, Crew Management, Inventory modules.

from shared.database import (
    races,
    crew_members,
    _next_id,
    VALID_RACE_STATUSES,
)
from registration.registration import is_registered
from crew_management.crew_management import get_available_drivers
from inventory.inventory import get_available_cars, set_car_assigned


# ------------------------------------------------------------------
# CREATE RACE
# ------------------------------------------------------------------

def create_race(name: str) -> dict:
    """
    Create a new race entry with status 'scheduled'.

    Parameters
    ----------
    name : str   Name of the race. Must be non-empty.

    Returns
    -------
    dict  {"success": True,  "race_id": str, "message": str}
       or {"success": False, "race_id": None, "message": str}
    """
    name = name.strip()
    if not name:
        return _fail("Race name cannot be empty.")

    # Duplicate name check
    for race in races.values():
        if race["name"].lower() == name.lower():
            return _fail(f"A race named '{name}' already exists.")

    race_id = _next_id("R", "race")
    races[race_id] = {
        "name"       : name,
        "status"     : "scheduled",
        "driver_ids" : [],
        "car_ids"    : [],
        "result"     : None,
    }

    return {
        "success" : True,
        "race_id" : race_id,
        "message" : f"Race '{name}' created (ID: {race_id}, status: scheduled).",
    }


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

def get_race(race_id: str) -> dict:
    """
    Fetch a single race by ID.

    Returns
    -------
    dict  {"success": True,  "race": dict}
       or {"success": False, "race": None, "message": str}
    """
    race_id = race_id.strip().upper()
    if race_id not in races:
        return {**_fail(f"No race found with ID '{race_id}'."), "race": None}
    return {"success": True, "race": races[race_id]}


def list_races(status_filter: str = None) -> dict:
    """
    List all races with an optional status filter.

    Returns
    -------
    dict  {"success": True, "races": list[dict]}
       or {"success": False, "races": [], "message": str}
    """
    if status_filter:
        status_filter = status_filter.strip().lower()
        if status_filter not in VALID_RACE_STATUSES:
            return {
                **_fail(
                    f"Invalid status filter '{status_filter}'. "
                    f"Valid: {', '.join(sorted(VALID_RACE_STATUSES))}."
                ),
                "races": [],
            }

    races_out = []
    for rid, data in races.items():
        if status_filter and data["status"] != status_filter:
            continue
        races_out.append({"id": rid, **data})

    return {"success": True, "races": races_out}


# ------------------------------------------------------------------
# ENTER DRIVER INTO RACE
# ------------------------------------------------------------------

def enter_driver(race_id: str, member_id: str) -> dict:
    """
    Add a driver to a scheduled race.

    Rules
    -----
    - Race must exist and be in 'scheduled' status.
    - Member must be registered and active.
    - Member must have the 'driver' role.
    - Driver cannot be entered into the same race twice.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    race_id   = race_id.strip().upper()
    member_id = member_id.strip().upper()

    # Validate race
    result = _validate_race_scheduled(race_id)
    if not result["success"]:
        return result

    # Validate member registered
    if not is_registered(member_id):
        return _fail(f"Member '{member_id}' is not registered.")

    member = crew_members[member_id]

    # Validate active
    if member["status"] != "active":
        return _fail(f"Member '{member_id}' is inactive and cannot enter a race.")

    # Validate driver role
    if member["role"] != "driver":
        return _fail(
            f"Member '{member_id}' has role '{member['role']}'. "
            f"Only drivers can enter a race."
        )

    # Duplicate entry check
    if member_id in races[race_id]["driver_ids"]:
        return _fail(f"Driver '{member_id}' is already entered in race '{race_id}'.")

    races[race_id]["driver_ids"].append(member_id)
    return {
        "success" : True,
        "message" : (
            f"Driver '{member['name']}' (ID: {member_id}) "
            f"entered into race '{race_id}'."
        ),
    }


# ------------------------------------------------------------------
# ASSIGN CAR TO RACE
# ------------------------------------------------------------------

def assign_car(race_id: str, car_id: str) -> dict:
    """
    Assign a car to a scheduled race.

    Rules
    -----
    - Race must exist and be 'scheduled'.
    - Car must exist, be in 'good' condition, and not already assigned.
    - Car cannot be assigned to the same race twice.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    from shared.database import cars  # local import to avoid circular

    race_id = race_id.strip().upper()
    car_id  = car_id.strip().upper()

    # Validate race
    result = _validate_race_scheduled(race_id)
    if not result["success"]:
        return result

    # Validate car exists
    if car_id not in cars:
        return _fail(f"Car '{car_id}' does not exist in inventory.")

    car = cars[car_id]

    # Validate condition
    if car["condition"] != "good":
        return _fail(
            f"Car '{car_id}' is in '{car['condition']}' condition. "
            f"Only cars in 'good' condition can race."
        )

    # Validate not already assigned elsewhere
    if car["assigned"]:
        return _fail(f"Car '{car_id}' is already assigned to another race.")

    # Duplicate in this race check
    if car_id in races[race_id]["car_ids"]:
        return _fail(f"Car '{car_id}' is already assigned to race '{race_id}'.")

    # Mark car as assigned in inventory
    set_car_assigned(car_id, True)
    races[race_id]["car_ids"].append(car_id)

    return {
        "success" : True,
        "message" : f"Car '{car_id}' ({car['name']}) assigned to race '{race_id}'.",
    }


# ------------------------------------------------------------------
# RACE LIFECYCLE
# ------------------------------------------------------------------

def start_race(race_id: str) -> dict:
    """
    Move a race from 'scheduled' to 'ongoing'.

    Rules
    -----
    - Race must be scheduled.
    - Must have at least one driver.
    - Must have at least one car.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    race_id = race_id.strip().upper()

    result = _validate_race_scheduled(race_id)
    if not result["success"]:
        return result

    race = races[race_id]

    if not race["driver_ids"]:
        return _fail(f"Race '{race_id}' has no drivers. Add at least one driver before starting.")

    if not race["car_ids"]:
        return _fail(f"Race '{race_id}' has no cars. Assign at least one car before starting.")

    races[race_id]["status"] = "ongoing"
    return {
        "success" : True,
        "message" : f"Race '{race_id}' has started and is now ongoing.",
    }


def complete_race(race_id: str) -> dict:
    """
    Move a race from 'ongoing' to 'completed'.
    Called by the Results module after recording the outcome.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    race_id = race_id.strip().upper()

    if race_id not in races:
        return _fail(f"No race found with ID '{race_id}'.")

    if races[race_id]["status"] != "ongoing":
        return _fail(
            f"Race '{race_id}' is '{races[race_id]['status']}'. "
            f"Only ongoing races can be completed."
        )

    races[race_id]["status"] = "completed"
    return {
        "success" : True,
        "message" : f"Race '{race_id}' marked as completed.",
    }


# ------------------------------------------------------------------
# CONVENIENCE HELPERS  (used by other modules)
# ------------------------------------------------------------------

def get_race_drivers(race_id: str) -> dict:
    """
    Return the list of driver IDs entered in a race.

    Returns
    -------
    dict  {"success": True, "driver_ids": list[str]}
       or {"success": False, "driver_ids": [], "message": str}
    """
    race_id = race_id.strip().upper()
    if race_id not in races:
        return {**_fail(f"No race found with ID '{race_id}'."), "driver_ids": []}
    return {"success": True, "driver_ids": races[race_id]["driver_ids"]}


def get_race_cars(race_id: str) -> dict:
    """
    Return the list of car IDs assigned to a race.

    Returns
    -------
    dict  {"success": True, "car_ids": list[str]}
       or {"success": False, "car_ids": [], "message": str}
    """
    race_id = race_id.strip().upper()
    if race_id not in races:
        return {**_fail(f"No race found with ID '{race_id}'."), "car_ids": []}
    return {"success": True, "car_ids": races[race_id]["car_ids"]}


def list_available_drivers() -> dict:
    """
    Return all active drivers available to be entered in a race.
    Wraps crew_management helper for convenience.

    Returns
    -------
    dict  {"success": True, "driver_ids": list[str]}
    """
    return {"success": True, "driver_ids": get_available_drivers()}


def list_available_cars() -> dict:
    """
    Return all good + unassigned cars available for a race.
    Wraps inventory helper for convenience.

    Returns
    -------
    dict  {"success": True, "car_ids": list[str]}
    """
    return {"success": True, "car_ids": get_available_cars()}


# ------------------------------------------------------------------
# INTERNAL VALIDATORS
# ------------------------------------------------------------------

def _validate_race_scheduled(race_id: str) -> dict:
    """Check that a race exists and is in 'scheduled' status."""
    if race_id not in races:
        return _fail(f"No race found with ID '{race_id}'.")
    if races[race_id]["status"] != "scheduled":
        return _fail(
            f"Race '{race_id}' is '{races[race_id]['status']}'. "
            f"This action requires a 'scheduled' race."
        )
    return {"success": True}


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _fail(message: str) -> dict:
    return {"success": False, "message": message}