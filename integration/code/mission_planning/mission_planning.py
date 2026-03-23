# mission_planning/mission_planning.py
# Assigns missions, verifies required crew roles are available,
# and manages mission lifecycle.
# Depends on: Registration, Crew Management modules.

from shared.database import (
    missions,
    crew_members,
    _next_id,
    VALID_MISSION_TYPES,
)
from registration.registration import is_registered
from crew_management.crew_management import has_available_role, VALID_ROLES


# ------------------------------------------------------------------
# VALID MISSION STATUSES
# ------------------------------------------------------------------

VALID_MISSION_STATUSES = {"planned", "active", "completed", "failed"}


# ------------------------------------------------------------------
# CREATE MISSION
# ------------------------------------------------------------------

def create_mission(name: str, mission_type: str, required_roles: list) -> dict:
    """
    Create a new mission with status 'planned'.

    Parameters
    ----------
    name           : str        Name of the mission. Must be non-empty.
    mission_type   : str        One of: delivery | rescue | sabotage | recon
    required_roles : list[str]  Roles required to execute the mission.
                                Each must be a valid role.

    Returns
    -------
    dict  {"success": True,  "mission_id": str, "message": str}
       or {"success": False, "mission_id": None, "message": str}
    """
    name = name.strip()
    if not name:
        return _fail("Mission name cannot be empty.")

    mission_type = mission_type.strip().lower()
    if mission_type not in VALID_MISSION_TYPES:
        return _fail(
            f"Invalid mission type '{mission_type}'. "
            f"Valid types: {', '.join(sorted(VALID_MISSION_TYPES))}."
        )

    # Validate required_roles
    if not required_roles:
        return _fail("At least one required role must be specified.")

    required_roles = [r.strip().lower() for r in required_roles]
    for role in required_roles:
        if role not in VALID_ROLES:
            return _fail(
                f"Invalid role '{role}' in required_roles. "
                f"Valid roles: {', '.join(sorted(VALID_ROLES))}."
            )

    # Duplicate name check
    for mission in missions.values():
        if mission["name"].lower() == name.lower():
            return _fail(f"A mission named '{name}' already exists.")

    mission_id = _next_id("MI", "mission")
    missions[mission_id] = {
        "name"           : name,
        "type"           : mission_type,
        "required_roles" : required_roles,
        "assigned_crew"  : [],
        "status"         : "planned",
    }

    return {
        "success"    : True,
        "mission_id" : mission_id,
        "message"    : (
            f"Mission '{name}' created (ID: {mission_id}, "
            f"type: {mission_type}, "
            f"required roles: {required_roles})."
        ),
    }


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

def get_mission(mission_id: str) -> dict:
    """
    Fetch a single mission by ID.

    Returns
    -------
    dict  {"success": True,  "mission": dict}
       or {"success": False, "mission": None, "message": str}
    """
    mission_id = mission_id.strip().upper()
    if mission_id not in missions:
        return {**_fail(f"No mission found with ID '{mission_id}'."), "mission": None}
    return {"success": True, "mission": missions[mission_id]}


def list_missions(status_filter: str = None, type_filter: str = None) -> dict:
    """
    List all missions with optional filters.

    Returns
    -------
    dict  {"success": True, "missions": list[dict]}
       or {"success": False, "missions": [], "message": str}
    """
    if status_filter:
        status_filter = status_filter.strip().lower()
        if status_filter not in VALID_MISSION_STATUSES:
            return {
                **_fail(f"Invalid status filter '{status_filter}'."),
                "missions": [],
            }

    if type_filter:
        type_filter = type_filter.strip().lower()
        if type_filter not in VALID_MISSION_TYPES:
            return {
                **_fail(f"Invalid type filter '{type_filter}'."),
                "missions": [],
            }

    missions_out = []
    for mid, data in missions.items():
        if status_filter and data["status"] != status_filter:
            continue
        if type_filter and data["type"] != type_filter:
            continue
        missions_out.append({"id": mid, **data})

    return {"success": True, "missions": missions_out}


# ------------------------------------------------------------------
# ASSIGN CREW TO MISSION
# ------------------------------------------------------------------

def assign_crew_member(mission_id: str, member_id: str) -> dict:
    """
    Assign a crew member to a planned mission.

    Rules
    -----
    - Mission must exist and be 'planned'.
    - Member must be registered and active.
    - Member cannot be assigned to the same mission twice.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    mission_id = mission_id.strip().upper()
    member_id  = member_id.strip().upper()

    # Validate mission
    check = _validate_mission_planned(mission_id)
    if not check["success"]:
        return check

    # Validate member registered
    if not is_registered(member_id):
        return _fail(f"Member '{member_id}' is not registered.")

    member = crew_members[member_id]

    # Validate active
    if member["status"] != "active":
        return _fail(f"Member '{member_id}' is inactive and cannot be assigned to a mission.")

    # Duplicate check
    if member_id in missions[mission_id]["assigned_crew"]:
        return _fail(
            f"Member '{member_id}' is already assigned to mission '{mission_id}'."
        )

    missions[mission_id]["assigned_crew"].append(member_id)
    return {
        "success": True,
        "message": (
            f"'{member['name']}' (ID: {member_id}) assigned to mission '{mission_id}'."
        ),
    }


def remove_crew_member(mission_id: str, member_id: str) -> dict:
    """
    Remove a crew member from a planned mission.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    mission_id = mission_id.strip().upper()
    member_id  = member_id.strip().upper()

    check = _validate_mission_planned(mission_id)
    if not check["success"]:
        return check

    if member_id not in missions[mission_id]["assigned_crew"]:
        return _fail(
            f"Member '{member_id}' is not assigned to mission '{mission_id}'."
        )

    missions[mission_id]["assigned_crew"].remove(member_id)
    return {
        "success": True,
        "message": f"Member '{member_id}' removed from mission '{mission_id}'.",
    }


# ------------------------------------------------------------------
# MISSION LIFECYCLE
# ------------------------------------------------------------------

def start_mission(mission_id: str) -> dict:
    """
    Start a planned mission — moves status from 'planned' to 'active'.

    Rules
    -----
    - Mission must be 'planned'.
    - All required roles must be covered by assigned crew members.
    - Missions cannot start if any required role has no active member assigned.

    Returns
    -------
    dict  {"success": True/False, "message": str, "missing_roles": list}
    """
    mission_id = mission_id.strip().upper()

    check = _validate_mission_planned(mission_id)
    if not check["success"]:
        return {**check, "missing_roles": []}

    mission = missions[mission_id]

    # Check that assigned crew covers all required roles
    assigned_roles = {
        crew_members[mid]["role"]
        for mid in mission["assigned_crew"]
        if mid in crew_members
    }

    missing_roles = [
        role for role in mission["required_roles"]
        if role not in assigned_roles
    ]

    if missing_roles:
        return {
            "success"      : False,
            "message"      : (
                f"Mission '{mission_id}' cannot start. "
                f"Missing required roles: {missing_roles}."
            ),
            "missing_roles": missing_roles,
        }

    missions[mission_id]["status"] = "active"
    return {
        "success"      : True,
        "message"      : f"Mission '{mission_id}' is now active.",
        "missing_roles": [],
    }


def complete_mission(mission_id: str) -> dict:
    """
    Mark an active mission as 'completed'.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    mission_id = mission_id.strip().upper()

    if mission_id not in missions:
        return _fail(f"No mission found with ID '{mission_id}'.")

    if missions[mission_id]["status"] != "active":
        return _fail(
            f"Mission '{mission_id}' is '{missions[mission_id]['status']}'. "
            f"Only active missions can be completed."
        )

    missions[mission_id]["status"] = "completed"
    return {"success": True, "message": f"Mission '{mission_id}' marked as completed."}


def fail_mission(mission_id: str) -> dict:
    """
    Mark an active mission as 'failed'.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    mission_id = mission_id.strip().upper()

    if mission_id not in missions:
        return _fail(f"No mission found with ID '{mission_id}'.")

    if missions[mission_id]["status"] != "active":
        return _fail(
            f"Mission '{mission_id}' is '{missions[mission_id]['status']}'. "
            f"Only active missions can be marked as failed."
        )

    missions[mission_id]["status"] = "failed"
    return {"success": True, "message": f"Mission '{mission_id}' marked as failed."}


# ------------------------------------------------------------------
# ROLE AVAILABILITY CHECK (used externally by Garage module)
# ------------------------------------------------------------------

def check_roles_available(required_roles: list) -> dict:
    """
    Check whether all required roles have at least one active
    crew member available in the system (not mission-specific).

    Used by Garage module before starting a repair mission.

    Returns
    -------
    dict  {
        "success"       : bool,
        "missing_roles" : list[str],
        "message"       : str,
    }
    """
    required_roles = [r.strip().lower() for r in required_roles]
    missing = [role for role in required_roles if not has_available_role(role)]

    if missing:
        return {
            "success"       : False,
            "missing_roles" : missing,
            "message"       : f"Missing active crew for roles: {missing}.",
        }

    return {
        "success"       : True,
        "missing_roles" : [],
        "message"       : "All required roles are available.",
    }


# ------------------------------------------------------------------
# INTERNAL VALIDATORS
# ------------------------------------------------------------------

def _validate_mission_planned(mission_id: str) -> dict:
    """Check that a mission exists and is in 'planned' status."""
    if mission_id not in missions:
        return _fail(f"No mission found with ID '{mission_id}'.")
    if missions[mission_id]["status"] != "planned":
        return _fail(
            f"Mission '{mission_id}' is '{missions[mission_id]['status']}'. "
            f"This action requires a 'planned' mission."
        )
    return {"success": True}


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _fail(message: str) -> dict:
    return {"success": False, "mission_id": None, "message": message}