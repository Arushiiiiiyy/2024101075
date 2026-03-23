# registration/registration.py
# Handles registering new crew members into the StreetRace Manager system.

from shared.database import (
    crew_members,
    _next_id,
    VALID_ROLES,
    VALID_MEMBER_STATUSES,
)




def register_member(name: str, role: str) -> dict:
    """
    Register a new crew member.

    Parameters
    ----------
    name : str   Full name of the crew member. Must be non-empty.
    role : str   One of: driver | mechanic | strategist | scout | trainer

    Returns
    -------
    dict  {"success": True,  "member_id": str, "message": str}
       or {"success": False, "member_id": None, "message": str}
    """
    # --- Validate name ---
    name = name.strip()
    if not name:
        return _fail("Name cannot be empty.")

    # --- Validate role ---
    role = role.strip().lower()
    if role not in VALID_ROLES:
        return _fail(
            f"Invalid role '{role}'. Valid roles are: {', '.join(sorted(VALID_ROLES))}."
        )

    # --- Check for duplicate name ---
    for member in crew_members.values():
        if member["name"].lower() == name.lower():
            return _fail(f"A crew member named '{name}' is already registered.")

    # --- Create and store member ---
    member_id = _next_id("M", "member")
    crew_members[member_id] = {
        "name"        : name,
        "role"        : role,
        "skill_level" : 1,       # Everyone starts at skill level 1
        "status"      : "active",
    }

    return {
        "success"   : True,
        "member_id" : member_id,
        "message"   : f"'{name}' registered successfully as {role} (ID: {member_id}).",
    }


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

def get_member(member_id: str) -> dict:
    """
    Fetch a single crew member by ID.

    Returns
    -------
    dict  {"success": True,  "member": dict}
       or {"success": False, "member": None, "message": str}
    """
    member_id = member_id.strip().upper()
    if member_id not in crew_members:
        return {**_fail(f"No crew member found with ID '{member_id}'."), "member": None}
    return {"success": True, "member": crew_members[member_id]}


def list_members(role_filter: str = None, status_filter: str = None) -> dict:
    """
    List all crew members, with optional filters.

    Parameters
    ----------
    role_filter   : str | None  — only return members with this role
    status_filter : str | None  — only return members with this status

    Returns
    -------
    dict  {"success": True, "members": list[dict]}
       or {"success": False, "members": [], "message": str}
    """
    if role_filter:
        role_filter = role_filter.strip().lower()
        if role_filter not in VALID_ROLES:
            return {**_fail(f"Invalid role filter '{role_filter}'."), "members": []}

    if status_filter:
        status_filter = status_filter.strip().lower()
        if status_filter not in VALID_MEMBER_STATUSES:
            return {**_fail(f"Invalid status filter '{status_filter}'."), "members": []}

    members_out = []
    for mid, data in crew_members.items():
        if role_filter and data["role"] != role_filter:
            continue
        if status_filter and data["status"] != status_filter:
            continue
        members_out.append({"id": mid, **data})

    return {"success": True, "members": members_out}


def is_registered(member_id: str) -> bool:
    """Return True if a member with this ID exists in the system."""
    return member_id.strip().upper() in crew_members


# ------------------------------------------------------------------
# UPDATE / DEACTIVATE
# ------------------------------------------------------------------

def deactivate_member(member_id: str) -> dict:
    """
    Set a crew member's status to 'inactive'.
    Inactive members cannot be assigned to races or missions.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    member_id = member_id.strip().upper()
    if member_id not in crew_members:
        return _fail(f"No crew member found with ID '{member_id}'.")

    if crew_members[member_id]["status"] == "inactive":
        return _fail(f"Member '{member_id}' is already inactive.")

    crew_members[member_id]["status"] = "inactive"
    name = crew_members[member_id]["name"]
    return {"success": True, "message": f"'{name}' (ID: {member_id}) has been deactivated."}


def reactivate_member(member_id: str) -> dict:
    """
    Set a crew member's status back to 'active'.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    member_id = member_id.strip().upper()
    if member_id not in crew_members:
        return _fail(f"No crew member found with ID '{member_id}'.")

    if crew_members[member_id]["status"] == "active":
        return _fail(f"Member '{member_id}' is already active.")

    crew_members[member_id]["status"] = "active"
    name = crew_members[member_id]["name"]
    return {"success": True, "message": f"'{name}' (ID: {member_id}) has been reactivated."}


def _fail(message: str) -> dict:
    return {"success": False, "member_id": None, "message": message}