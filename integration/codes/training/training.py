# training/training.py
# Manages training sessions for crew members.
# Increases skill levels and tracks session history.
# Depends on: Registration, Crew Management modules.

from shared.database import (
    crew_members,
    training_sessions,
    _next_id,
)
from registration.registration import is_registered
from crew_management.crew_management import (
    increase_skill,
    get_skill_level,
    SKILL_MAX,
)


# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------

DEFAULT_SKILL_GAIN = 1
MAX_SKILL_GAIN_PER_SESSION = 3   # can't gain more than 3 in one session


# ------------------------------------------------------------------
# CONDUCT TRAINING SESSION
# ------------------------------------------------------------------

def conduct_session(member_id: str, skill_gain: int = DEFAULT_SKILL_GAIN, notes: str = "") -> dict:
    """
    Conduct a training session for a crew member.

    Parameters
    ----------
    member_id  : str   ID of the crew member to train.
    skill_gain : int   Skill points to award (1–3). Default is 1.
    notes      : str   Optional notes about the session.

    Rules
    -----
    - Member must be registered and active.
    - skill_gain must be between 1 and MAX_SKILL_GAIN_PER_SESSION.
    - If member is already at max skill (10), session is logged
      but no skill is gained.

    Returns
    -------
    dict  {
        "success"    : True/False,
        "session_id" : str | None,
        "old_skill"  : int | None,
        "new_skill"  : int | None,
        "message"    : str,
    }
    """
    member_id = member_id.strip().upper()

    # Validate registered
    if not is_registered(member_id):
        return _fail(f"Member '{member_id}' is not registered.")

    member = crew_members[member_id]

    # Validate active
    if member["status"] != "active":
        return _fail(
            f"Member '{member_id}' is inactive. "
            f"Only active members can attend training."
        )

    # Validate skill_gain range
    if not isinstance(skill_gain, int) or not (1 <= skill_gain <= MAX_SKILL_GAIN_PER_SESSION):
        return _fail(
            f"Skill gain must be an integer between 1 and "
            f"{MAX_SKILL_GAIN_PER_SESSION}. Got '{skill_gain}'."
        )

    old_skill = member["skill_level"]

    # If already at max, log session but don't increase
    if old_skill >= SKILL_MAX:
        session_id = _log_session(member_id, 0, notes or "Already at max skill.")
        return {
            "success"    : True,
            "session_id" : session_id,
            "old_skill"  : old_skill,
            "new_skill"  : old_skill,
            "message"    : (
                f"Session logged for '{member['name']}' but skill is already "
                f"at maximum ({SKILL_MAX}). No gain applied."
            ),
        }

    # Increase skill via Crew Management
    result = increase_skill(member_id, skill_gain)
    new_skill = result["new_skill"]
    actual_gain = new_skill - old_skill

    # Log the session
    session_id = _log_session(member_id, actual_gain, notes)

    return {
        "success"    : True,
        "session_id" : session_id,
        "old_skill"  : old_skill,
        "new_skill"  : new_skill,
        "message"    : (
            f"Training session completed for '{member['name']}'. "
            f"Skill: {old_skill} → {new_skill} (+{actual_gain})."
        ),
    }


# ------------------------------------------------------------------
# SESSION HISTORY
# ------------------------------------------------------------------

def get_session(session_id: str) -> dict:
    """
    Fetch a single training session by ID.

    Returns
    -------
    dict  {"success": True,  "session": dict}
       or {"success": False, "session": None, "message": str}
    """
    session_id = session_id.strip().upper()
    if session_id not in training_sessions:
        return {
            **_fail(f"No training session found with ID '{session_id}'."),
            "session": None,
        }
    return {"success": True, "session": training_sessions[session_id]}


def get_member_sessions(member_id: str) -> dict:
    """
    Return all training sessions for a specific crew member.

    Returns
    -------
    dict  {"success": True,  "sessions": list[dict]}
       or {"success": False, "sessions": [], "message": str}
    """
    member_id = member_id.strip().upper()

    if not is_registered(member_id):
        return {
            **_fail(f"Member '{member_id}' is not registered."),
            "sessions": [],
        }

    sessions_out = [
        {"id": sid, **data}
        for sid, data in training_sessions.items()
        if data["member_id"] == member_id
    ]

    return {"success": True, "sessions": sessions_out}


def list_all_sessions() -> dict:
    """
    Return all training sessions across all members.

    Returns
    -------
    dict  {"success": True, "sessions": list[dict]}
    """
    sessions_out = [
        {"id": sid, **data}
        for sid, data in training_sessions.items()
    ]
    return {"success": True, "sessions": sessions_out}


# ------------------------------------------------------------------
# SKILL SUMMARY
# ------------------------------------------------------------------

def get_skill_summary() -> dict:
    """
    Return all crew members sorted by skill level descending.
    Useful for Race Management to pick the best drivers.

    Returns
    -------
    dict  {"success": True, "members": list[dict]}
    Each entry: {"id", "name", "role", "skill_level", "status"}
    """
    members_out = [
        {
            "id"          : mid,
            "name"        : data["name"],
            "role"        : data["role"],
            "skill_level" : data["skill_level"],
            "status"      : data["status"],
        }
        for mid, data in crew_members.items()
    ]

    members_out.sort(key=lambda x: x["skill_level"], reverse=True)

    return {"success": True, "members": members_out}


def get_top_drivers(n: int = 3) -> dict:
    """
    Return the top N drivers by skill level.
    Used by Race Management to auto-select best available drivers.

    Parameters
    ----------
    n : int   Number of top drivers to return. Default 3.

    Returns
    -------
    dict  {"success": True,  "drivers": list[dict]}
       or {"success": False, "drivers": [], "message": str}
    """
    if not isinstance(n, int) or n < 1:
        return {
            **_fail(f"N must be a positive integer. Got '{n}'."),
            "drivers": [],
        }

    drivers = [
        {
            "id"          : mid,
            "name"        : data["name"],
            "skill_level" : data["skill_level"],
            "status"      : data["status"],
        }
        for mid, data in crew_members.items()
        if data["role"] == "driver" and data["status"] == "active"
    ]

    drivers.sort(key=lambda x: x["skill_level"], reverse=True)

    return {"success": True, "drivers": drivers[:n]}


def get_total_sessions_count(member_id: str) -> dict:
    """
    Return the total number of training sessions a member has attended.

    Returns
    -------
    dict  {"success": True,  "count": int}
       or {"success": False, "count": 0, "message": str}
    """
    member_id = member_id.strip().upper()

    if not is_registered(member_id):
        return {
            **_fail(f"Member '{member_id}' is not registered."),
            "count": 0,
        }

    count = sum(
        1 for data in training_sessions.values()
        if data["member_id"] == member_id
    )

    return {"success": True, "count": count}


# ------------------------------------------------------------------
# INTERNAL HELPERS
# ------------------------------------------------------------------

def _log_session(member_id: str, skill_gained: int, notes: str) -> str:
    """Store a training session record and return its ID."""
    session_id = _next_id("T", "training")
    training_sessions[session_id] = {
        "member_id"    : member_id,
        "skill_gained" : skill_gained,
        "notes"        : notes.strip(),
    }
    return session_id


def _fail(message: str) -> dict:
    return {"success": False, "session_id": None, "message": message}