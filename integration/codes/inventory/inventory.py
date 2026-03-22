# inventory/inventory.py
# Tracks cars, spare parts, tools, and cash balance.
# Other modules (Results, Garage) call into here to update state.

import shared.database as db
from shared.database import (
    cars,
    VALID_CONDITIONS,
)


# CAR MANAGEMENT


def add_car(name: str, condition: str = "good") -> dict:
    """
    Add a new car to the inventory.

    Parameters
    ----------
    name      : str   Name / model of the car. Must be non-empty.
    condition : str   Initial condition — good | damaged | under_repair

    Returns
    -------
    dict  {"success": True,  "car_id": str, "message": str}
       or {"success": False, "car_id": None, "message": str}
    """
    name = name.strip()
    if not name:
        return _fail("Car name cannot be empty.")

    condition = condition.strip().lower()
    if condition not in VALID_CONDITIONS:
        return _fail(
            f"Invalid condition '{condition}'. "
            f"Valid conditions: {', '.join(sorted(VALID_CONDITIONS))}."
        )

    # Duplicate name check
    for car in cars.values():
        if car["name"].lower() == name.lower():
            return _fail(f"A car named '{name}' already exists in inventory.")

    car_id = db._next_id("C", "car")
    cars[car_id] = {
        "name"      : name,
        "condition" : condition,
        "assigned"  : False,
    }

    return {
        "success" : True,
        "car_id"  : car_id,
        "message" : f"Car '{name}' added to inventory (ID: {car_id}, condition: {condition}).",
    }


def get_car(car_id: str) -> dict:
    """
    Fetch a single car by ID.

    Returns
    -------
    dict  {"success": True,  "car": dict}
       or {"success": False, "car": None, "message": str}
    """
    car_id = car_id.strip().upper()
    if car_id not in cars:
        return {**_fail(f"No car found with ID '{car_id}'."), "car": None}
    return {"success": True, "car": cars[car_id]}


def list_cars(condition_filter: str = None, assigned_filter: bool = None) -> dict:
    """
    List all cars, with optional filters.

    Parameters
    ----------
    condition_filter : str | None   — filter by condition
    assigned_filter  : bool | None  — True = only assigned, False = only free

    Returns
    -------
    dict  {"success": True, "cars": list[dict]}
       or {"success": False, "cars": [], "message": str}
    """
    if condition_filter:
        condition_filter = condition_filter.strip().lower()
        if condition_filter not in VALID_CONDITIONS:
            return {**_fail(f"Invalid condition filter '{condition_filter}'."), "cars": []}

    cars_out = []
    for cid, data in cars.items():
        if condition_filter and data["condition"] != condition_filter:
            continue
        if assigned_filter is not None and data["assigned"] != assigned_filter:
            continue
        cars_out.append({"id": cid, **data})

    return {"success": True, "cars": cars_out}


def get_available_cars() -> list:
    """
    Convenience helper used by Race Management.
    Returns list of car_ids that are in 'good' condition and not assigned.
    """
    return [
        cid
        for cid, data in cars.items()
        if data["condition"] == "good" and not data["assigned"]
    ]


def update_car_condition(car_id: str, condition: str) -> dict:
    """
    Update the condition of a car.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    car_id = car_id.strip().upper()
    if car_id not in cars:
        return _fail(f"No car found with ID '{car_id}'.")

    condition = condition.strip().lower()
    if condition not in VALID_CONDITIONS:
        return _fail(
            f"Invalid condition '{condition}'. "
            f"Valid: {', '.join(sorted(VALID_CONDITIONS))}."
        )

    old = cars[car_id]["condition"]
    cars[car_id]["condition"] = condition
    return {
        "success" : True,
        "message" : f"Car '{car_id}' condition updated from '{old}' to '{condition}'.",
    }


def set_car_assigned(car_id: str, assigned: bool) -> dict:
    """
    Mark a car as assigned (in a race) or free.
    Called by Race Management when a race starts / ends.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    car_id = car_id.strip().upper()
    if car_id not in cars:
        return _fail(f"No car found with ID '{car_id}'.")

    cars[car_id]["assigned"] = assigned
    state = "assigned" if assigned else "unassigned"
    return {
        "success" : True,
        "message" : f"Car '{car_id}' marked as {state}.",
    }


def remove_car(car_id: str) -> dict:
    """
    Remove a car from inventory entirely.
    Cannot remove a car that is currently assigned to a race.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    car_id = car_id.strip().upper()
    if car_id not in cars:
        return _fail(f"No car found with ID '{car_id}'.")

    if cars[car_id]["assigned"]:
        return _fail(f"Car '{car_id}' is currently assigned to a race and cannot be removed.")

    name = cars[car_id]["name"]
    del cars[car_id]
    return {"success": True, "message": f"Car '{name}' (ID: {car_id}) removed from inventory."}


# SPARE PARTS & TOOLS


def add_spare_parts(amount: int) -> dict:
    """
    Add spare parts to the inventory.

    Returns
    -------
    dict  {"success": True/False, "message": str, "spare_parts": int}
    """
    if not isinstance(amount, int) or amount <= 0:
        return {
            **_fail(f"Amount must be a positive integer. Got '{amount}'."),
            "spare_parts": db.spare_parts,
        }

    db.spare_parts += amount
    return {
        "success"     : True,
        "message"     : f"Added {amount} spare parts. Total: {db.spare_parts}.",
        "spare_parts" : db.spare_parts,
    }


def use_spare_parts(amount: int) -> dict:
    """
    Use / consume spare parts from inventory.

    Returns
    -------
    dict  {"success": True/False, "message": str, "spare_parts": int}
    """
    if not isinstance(amount, int) or amount <= 0:
        return {
            **_fail(f"Amount must be a positive integer. Got '{amount}'."),
            "spare_parts": db.spare_parts,
        }

    if amount > db.spare_parts:
        return {
            **_fail(
                f"Not enough spare parts. Requested {amount}, available {db.spare_parts}."
            ),
            "spare_parts": db.spare_parts,
        }

    db.spare_parts -= amount
    return {
        "success"     : True,
        "message"     : f"Used {amount} spare parts. Remaining: {db.spare_parts}.",
        "spare_parts" : db.spare_parts,
    }


def add_tools(amount: int) -> dict:
    """
    Add tools to the inventory.

    Returns
    -------
    dict  {"success": True/False, "message": str, "tools": int}
    """
    if not isinstance(amount, int) or amount <= 0:
        return {**_fail(f"Amount must be a positive integer. Got '{amount}'."), "tools": db.tools}

    db.tools += amount
    return {
        "success" : True,
        "message" : f"Added {amount} tools. Total: {db.tools}.",
        "tools"   : db.tools,
    }


def use_tools(amount: int) -> dict:
    """
    Use / consume tools from inventory.

    Returns
    -------
    dict  {"success": True/False, "message": str, "tools": int}
    """
    if not isinstance(amount, int) or amount <= 0:
        return {**_fail(f"Amount must be a positive integer. Got '{amount}'."), "tools": db.tools}

    if amount > db.tools:
        return {
            **_fail(f"Not enough tools. Requested {amount}, available {db.tools}."),
            "tools": db.tools,
        }

    db.tools -= amount
    return {
        "success" : True,
        "message" : f"Used {amount} tools. Remaining: {db.tools}.",
        "tools"   : db.tools,
    }


def get_parts_and_tools() -> dict:
    """
    Return current counts of spare parts and tools.

    Returns
    -------
    dict  {"success": True, "spare_parts": int, "tools": int}
    """
    return {"success": True, "spare_parts": db.spare_parts, "tools": db.tools}




def add_cash(amount: float) -> dict:
    """
    Add money to the cash balance (e.g. prize winnings).

    Returns
    -------
    dict  {"success": True/False, "message": str, "cash_balance": float}
    """
    if not isinstance(amount, (int, float)) or amount <= 0:
        return {
            **_fail(f"Amount must be a positive number. Got '{amount}'."),
            "cash_balance": db.cash_balance,
        }

    db.cash_balance += amount
    return {
        "success"      : True,
        "message"      : f"Added ${amount:.2f}. New balance: ${db.cash_balance:.2f}.",
        "cash_balance" : db.cash_balance,
    }


def deduct_cash(amount: float) -> dict:
    """
    Deduct money from the cash balance (e.g. repair costs, mission costs).

    Returns
    -------
    dict  {"success": True/False, "message": str, "cash_balance": float}
    """
    if not isinstance(amount, (int, float)) or amount <= 0:
        return {
            **_fail(f"Amount must be a positive number. Got '{amount}'."),
            "cash_balance": db.cash_balance,
        }

    if amount > db.cash_balance:
        return {
            **_fail(
                f"Insufficient funds. Requested ${amount:.2f}, "
                f"available ${db.cash_balance:.2f}."
            ),
            "cash_balance": db.cash_balance,
        }

    db.cash_balance -= amount
    return {
        "success"      : True,
        "message"      : f"Deducted ${amount:.2f}. New balance: ${db.cash_balance:.2f}.",
        "cash_balance" : db.cash_balance,
    }


def get_cash_balance() -> dict:
    """
    Return the current cash balance.

    Returns
    -------
    dict  {"success": True, "cash_balance": float}
    """
    return {"success": True, "cash_balance": db.cash_balance}



def get_inventory_summary() -> dict:
    """
    Return a full snapshot of all inventory data.

    Returns
    -------
    dict  {
        "success"      : True,
        "cars"         : list[dict],
        "spare_parts"  : int,
        "tools"        : int,
        "cash_balance" : float,
    }
    """
    return {
        "success"      : True,
        "cars"         : [{"id": cid, **data} for cid, data in cars.items()],
        "spare_parts"  : db.spare_parts,
        "tools"        : db.tools,
        "cash_balance" : db.cash_balance,
    }




def _fail(message: str) -> dict:
    return {"success": False, "message": message}