# crew_management/crew_management.py
# Manages crew member roles and skill levels.
# Depends on Registration module — a member must be registered first.

from shared.database import (
    crew_members,
    VALID_ROLES,
)
from registration.registration import is_registered



SKILL_MIN = 1
SKILL_MAX = 10

# ROLE MANAGEMENT


def assign_role(member_id: str, new_role: str) -> dict:
    """
    Assign or change the role of a registered crew member.

    Rules
    -----
    - Member must be registered and active.
    - Role must be one of the valid roles.

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    member_id = member_id.strip().upper()

    # Must be registered
    if not is_registered(member_id):
        return _fail(f"No crew member found with ID '{member_id}'. Register them first.")

    member = crew_members[member_id]

    # Must be active
    if member["status"] != "active":
        return _fail(f"Member '{member_id}' is inactive. Reactivate before assigning a role.")

    # Validate role
    new_role = new_role.strip().lower()
    if new_role not in VALID_ROLES:
        return _fail(
            f"Invalid role '{new_role}'. Valid roles: {', '.join(sorted(VALID_ROLES))}."
        )

    old_role = member["role"]
    member["role"] = new_role

    return {
        "success": True,
        "message": f"Member '{member_id}' role updated from '{old_role}' to '{new_role}'.",
    }


def get_role(member_id: str) -> dict:
    """
    Get the current role of a crew member.

    Returns
    -------
    dict  {"success": True, "role": str}
       or {"success": False, "role": None, "message": str}
    """
    member_id = member_id.strip().upper()
    if not is_registered(member_id):
        return {**_fail(f"No crew member found with ID '{member_id}'."), "role": None}

    return {"success": True, "role": crew_members[member_id]["role"]}


def list_members_by_role(role: str) -> dict:
    """
    Return all active crew members with a given role.

    Returns
    -------
    dict  {"success": True, "members": list[dict]}
       or {"success": False, "members": [], "message": str}
    """
    role = role.strip().lower()
    if role not in VALID_ROLES:
        return {
            **_fail(f"Invalid role '{role}'."),
            "members": [],
        }

    members_out = [
        {"id": mid, **data}
        for mid, data in crew_members.items()
        if data["role"] == role and data["status"] == "active"
    ]

    return {"success": True, "members": members_out}


def get_available_drivers() -> list:
    """
    Convenience helper used by Race Management.
    Returns a list of member_ids who are active drivers.
    """
    return [
        mid
        for mid, data in crew_members.items()
        if data["role"] == "driver" and data["status"] == "active"
    ]


def get_available_mechanics() -> list:
    """
    Convenience helper used by Garage / Mission Planning.
    Returns a list of member_ids who are active mechanics.
    """
    return [
        mid
        for mid, data in crew_members.items()
        if data["role"] == "mechanic" and data["status"] == "active"
    ]


def has_available_role(role: str) -> bool:
    """
    Return True if at least one active member with the given role exists.
    Used by Mission Planning to verify role availability before starting a mission.
    """
    role = role.strip().lower()
    return any(
        data["role"] == role and data["status"] == "active"
        for data in crew_members.values()
    )



def set_skill_level(member_id: str, skill_level: int) -> dict:
    """
    Directly set the skill level of a crew member (1–10).

    Returns
    -------
    dict  {"success": True/False, "message": str}
    """
    member_id = member_id.strip().upper()

    if not is_registered(member_id):
        return _fail(f"No crew member found with ID '{member_id}'.")

    if not isinstance(skill_level, int) or not (SKILL_MIN <= skill_level <= SKILL_MAX):
        return _fail(
            f"Skill level must be an integer between {SKILL_MIN} and {SKILL_MAX}. Got '{skill_level}'."
        )

    old_level = crew_members[member_id]["skill_level"]
    crew_members[member_id]["skill_level"] = skill_level

    return {
        "success": True,
        "message": (
            f"Member '{member_id}' skill level updated from {old_level} to {skill_level}."
        ),
    }


def increase_skill(member_id: str, amount: int = 1) -> dict:
    """
    Increase a crew member's skill level by a given amount.
    Caps at SKILL_MAX (10).

    Returns
    -------
    dict  {"success": True/False, "message": str, "new_skill": int | None}
    """
    member_id = member_id.strip().upper()

    if not is_registered(member_id):
        return {**_fail(f"No crew member found with ID '{member_id}'."), "new_skill": None}

    if not isinstance(amount, int) or amount < 1:
        return {
            **_fail(f"Amount must be a positive integer. Got '{amount}'."),
            "new_skill": None,
        }

    current = crew_members[member_id]["skill_level"]
    new_level = min(current + amount, SKILL_MAX)
    crew_members[member_id]["skill_level"] = new_level

    return {
        "success"   : True,
        "message"   : f"Member '{member_id}' skill increased from {current} to {new_level}.",
        "new_skill" : new_level,
    }


def get_skill_level(member_id: str) -> dict:
    """
    Get the current skill level of a crew member.

    Returns
    -------
    dict  {"success": True, "skill_level": int}
       or {"success": False, "skill_level": None, "message": str}
    """
    member_id = member_id.strip().upper()

    if not is_registered(member_id):
        return {
            **_fail(f"No crew member found with ID '{member_id}'."),
            "skill_level": None,
        }

    return {"success": True, "skill_level": crew_members[member_id]["skill_level"]}


def get_crew_summary() -> dict:
    """
    Returns a full summary of all crew members with their id, name, role,
    skill level, and status. Useful for reports and debugging.

    Returns
    -------
    dict  {"success": True, "summary": list[dict]}
    """
    summary = [
        {
            "id"          : mid,
            "name"        : data["name"],
            "role"        : data["role"],
            "skill_level" : data["skill_level"],
            "status"      : data["status"],
        }
        for mid, data in crew_members.items()
    ]
    return {"success": True, "summary": summary}



def _fail(message: str) -> dict:
    return {"success": False, "message": message}