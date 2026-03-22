# shared/database.py
# Central in-memory database shared across all modules.
# All modules import from here to read and write state.

# ------------------------------------------------------------------
# CREW MEMBERS
# Key   : member_id (str)  e.g. "M001"
# Value : {
#     "name"        : str,
#     "role"        : str,   (driver | mechanic | strategist | scout | trainer)
#     "skill_level" : int,   (1-10)
#     "status"      : str,   (active | inactive)
# }
# ------------------------------------------------------------------
crew_members = {}

# ------------------------------------------------------------------
# CARS / INVENTORY
# Key   : car_id (str)  e.g. "C001"
# Value : {
#     "name"      : str,
#     "condition" : str,   (good | damaged | under_repair)
#     "assigned"  : bool,  True if currently in a race
# }
# ------------------------------------------------------------------
cars = {}

# Spare parts and tools counts
spare_parts = 0
tools = 0

# Cash balance (float)
cash_balance = 0.0

# ------------------------------------------------------------------
# RACES
# Key   : race_id (str)  e.g. "R001"
# Value : {
#     "name"       : str,
#     "status"     : str,   (scheduled | ongoing | completed)
#     "driver_ids" : list[str],
#     "car_ids"    : list[str],
#     "result"     : dict | None,   filled in by Results module
# }
# ------------------------------------------------------------------
races = {}

# ------------------------------------------------------------------
# RESULTS
# Key   : race_id (str)
# Value : {
#     "winner_id"   : str,
#     "rankings"    : list[str],   ordered member_ids
#     "prize_money" : float,
#     "damages"     : list[str],   car_ids that got damaged
# }
# ------------------------------------------------------------------
results = {}

# ------------------------------------------------------------------
# MISSIONS
# Key   : mission_id (str)  e.g. "MI001"
# Value : {
#     "name"           : str,
#     "type"           : str,   (delivery | rescue | sabotage | recon)
#     "required_roles" : list[str],
#     "assigned_crew"  : list[str],  member_ids
#     "status"         : str,   (planned | active | completed | failed)
# }
# ------------------------------------------------------------------
missions = {}
sponsors = {}
# ------------------------------------------------------------------
# TRAINING SESSIONS  (Training module)
# Key   : session_id (str)  e.g. "T001"
# Value : {
#     "member_id"    : str,
#     "skill_gained" : int,
#     "notes"        : str,
# }
# ------------------------------------------------------------------
training_sessions = {}

# ------------------------------------------------------------------
# COUNTERS  — used to auto-generate IDs
# ------------------------------------------------------------------
_counters = {
    "member"   : 0,
    "car"      : 0,
    "race"     : 0,
    "mission"  : 0,
    "training" : 0,
    "result"   : 0,
    "sponsor"  : 0,
}

def _next_id(prefix: str, counter_key: str) -> str:
    """Generate the next sequential ID for a given entity type."""
    _counters[counter_key] += 1
    return f"{prefix}{_counters[counter_key]:03d}"


# ------------------------------------------------------------------
# VALID VALUES  — shared constants used across modules
# ------------------------------------------------------------------
VALID_ROLES = {"driver", "mechanic", "strategist", "scout", "trainer"}
VALID_CONDITIONS = {"good", "damaged", "under_repair"}
VALID_MISSION_TYPES = {"delivery", "rescue", "sabotage", "recon"}
VALID_RACE_STATUSES = {"scheduled", "ongoing", "completed"}
VALID_MEMBER_STATUSES = {"active", "inactive"}
VALID_SPONSOR_TIERS = {"bronze", "silver", "gold"}

def reset_database():
    """
    Clears all data. Used in tests to get a clean state.
    """
    crew_members.clear()
    cars.clear()
    races.clear()
    results.clear()
    missions.clear()
    training_sessions.clear()
    sponsors.clear() 
    global spare_parts, tools, cash_balance
    spare_parts = 0
    tools = 0
    cash_balance = 0.0

    for key in _counters:
        _counters[key] = 0