# main.py
# StreetRace Manager — Command Line Interface
# Run from integration/ folder with: python main.py

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "codes"))
sys.path.insert(0, os.path.dirname(__file__))

# ----------------------------------------------------------------
# Integrated modules:
# Part 1 — Registration + Crew Management
# Part 2 — + Inventory
# Part 3 — + Race Management
# Part 4 — + Results
# Part 5 — + Mission Planning
# ----------------------------------------------------------------

from registration.registration import (
    register_member, deactivate_member,
    reactivate_member, list_members, get_member,
)
from crew_management.crew_management import (
    assign_role, get_role, set_skill_level,
    get_skill_level, get_crew_summary,
    list_members_by_role, has_available_role,
)
from inventory.inventory import (
    add_car, get_car, list_cars, get_available_cars,
    update_car_condition, remove_car,
    add_spare_parts, use_spare_parts,
    add_tools, use_tools, get_parts_and_tools,
    add_cash, deduct_cash, get_cash_balance,
    get_inventory_summary,
)
from race_management.race_management import (
    create_race, get_race, list_races,
    enter_driver, assign_car, start_race,
    complete_race, get_race_drivers, get_race_cars,
    list_available_drivers, list_available_cars,
)
from results.results import (
    record_result, get_result, list_results,
    get_winner, get_leaderboard, get_driver_results,
)
from mission_planning.mission_planning import (
    create_mission, get_mission, list_missions,
    assign_crew_member, remove_crew_member,
    start_mission, complete_mission, fail_mission,
    check_roles_available,
)


# ----------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------

def print_separator():
    print("\n" + "=" * 50 + "\n")

def print_menu(title, options):
    print_separator()
    print(f"  {title}")
    print_separator()
    for key, label in options.items():
        print(f"  [{key}] {label}")
    print()

def get_input(prompt):
    return input(f"  >> {prompt}: ").strip()


# ----------------------------------------------------------------
# REGISTRATION MENU
# ----------------------------------------------------------------

def menu_registration():
    while True:
        print_menu("REGISTRATION", {
            "1": "Register new crew member",
            "2": "View crew member by ID",
            "3": "List all crew members",
            "4": "Deactivate crew member",
            "5": "Reactivate crew member",
            "0": "Back",
        })
        choice = get_input("Choose option")

        if choice == "1":
            name = get_input("Enter name")
            print("  Roles: driver | mechanic | strategist | scout | trainer")
            role = get_input("Enter role")
            result = register_member(name, role)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "2":
            mid = get_input("Enter member ID (e.g. M001)")
            result = get_member(mid)
            if result["success"]:
                m = result["member"]
                print(f"\n  ID     : {mid}")
                print(f"  Name   : {m['name']}")
                print(f"  Role   : {m['role']}")
                print(f"  Skill  : {m['skill_level']}")
                print(f"  Status : {m['status']}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "3":
            members = list_members()["members"]
            if not members:
                print("\n  No crew members registered yet.")
            else:
                print(f"\n  {'ID':<8} {'Name':<20} {'Role':<12} {'Skill':<7} {'Status'}")
                print("  " + "-" * 55)
                for m in members:
                    print(f"  {m['id']:<8} {m['name']:<20} {m['role']:<12} {m['skill_level']:<7} {m['status']}")

        elif choice == "4":
            mid = get_input("Enter member ID to deactivate")
            result = deactivate_member(mid)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "5":
            mid = get_input("Enter member ID to reactivate")
            result = reactivate_member(mid)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "0":
            break
        else:
            print("\n  Invalid option. Try again.")


# ----------------------------------------------------------------
# CREW MANAGEMENT MENU
# ----------------------------------------------------------------

def menu_crew_management():
    while True:
        print_menu("CREW MANAGEMENT", {
            "1": "Assign role to member",
            "2": "Get role of member",
            "3": "Set skill level",
            "4": "Get skill level",
            "5": "List members by role",
            "6": "View full crew summary",
            "7": "Check if role is available",
            "0": "Back",
        })
        choice = get_input("Choose option")

        if choice == "1":
            mid = get_input("Enter member ID")
            print("  Roles: driver | mechanic | strategist | scout | trainer")
            role = get_input("Enter new role")
            result = assign_role(mid, role)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "2":
            mid = get_input("Enter member ID")
            result = get_role(mid)
            if result["success"]:
                print(f"\n  Role: {result['role']}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "3":
            mid = get_input("Enter member ID")
            level = get_input("Enter skill level (1-10)")
            try:
                result = set_skill_level(mid, int(level))
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Skill level must be a number.")

        elif choice == "4":
            mid = get_input("Enter member ID")
            result = get_skill_level(mid)
            if result["success"]:
                print(f"\n  Skill level: {result['skill_level']}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "5":
            print("  Roles: driver | mechanic | strategist | scout | trainer")
            role = get_input("Enter role to filter by")
            result = list_members_by_role(role)
            if not result["success"]:
                print(f"\n  ✗ {result['message']}")
            elif not result["members"]:
                print(f"\n  No active members with role '{role}'.")
            else:
                print(f"\n  {'ID':<8} {'Name':<20} {'Skill'}")
                print("  " + "-" * 35)
                for m in result["members"]:
                    print(f"  {m['id']:<8} {m['name']:<20} {m['skill_level']}")

        elif choice == "6":
            summary = get_crew_summary()["summary"]
            if not summary:
                print("\n  No crew members found.")
            else:
                print(f"\n  {'ID':<8} {'Name':<20} {'Role':<12} {'Skill':<7} {'Status'}")
                print("  " + "-" * 55)
                for m in summary:
                    print(f"  {m['id']:<8} {m['name']:<20} {m['role']:<12} {m['skill_level']:<7} {m['status']}")

        elif choice == "7":
            print("  Roles: driver | mechanic | strategist | scout | trainer")
            role = get_input("Enter role to check")
            available = has_available_role(role)
            print(f"\n  Role '{role}': {'✓ Available' if available else '✗ Not available'}")

        elif choice == "0":
            break
        else:
            print("\n  Invalid option. Try again.")


# ----------------------------------------------------------------
# INVENTORY MENU
# ----------------------------------------------------------------

def menu_inventory():
    while True:
        print_menu("INVENTORY", {
            "1" : "Add car",
            "2" : "View car by ID",
            "3" : "List all cars",
            "4" : "List available cars",
            "5" : "Update car condition",
            "6" : "Remove car",
            "7" : "Add spare parts",
            "8" : "Use spare parts",
            "9" : "Add tools",
            "10": "Use tools",
            "11": "View parts & tools",
            "12": "Add cash",
            "13": "Deduct cash",
            "14": "View cash balance",
            "15": "Full inventory summary",
            "0" : "Back",
        })
        choice = get_input("Choose option")

        if choice == "1":
            name = get_input("Car name")
            print("  Conditions: good | damaged | under_repair")
            cond = get_input("Condition (default: good)") or "good"
            result = add_car(name, cond)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "2":
            cid = get_input("Enter car ID (e.g. C001)")
            result = get_car(cid)
            if result["success"]:
                c = result["car"]
                print(f"\n  ID        : {cid}")
                print(f"  Name      : {c['name']}")
                print(f"  Condition : {c['condition']}")
                print(f"  Assigned  : {c['assigned']}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "3":
            cars = list_cars()["cars"]
            if not cars:
                print("\n  No cars in inventory.")
            else:
                print(f"\n  {'ID':<8} {'Name':<20} {'Condition':<14} {'Assigned'}")
                print("  " + "-" * 50)
                for c in cars:
                    print(f"  {c['id']:<8} {c['name']:<20} {c['condition']:<14} {c['assigned']}")

        elif choice == "4":
            available = get_available_cars()
            if not available:
                print("\n  No cars available.")
            else:
                print(f"\n  Available: {', '.join(available)}")

        elif choice == "5":
            cid = get_input("Enter car ID")
            print("  Conditions: good | damaged | under_repair")
            cond = get_input("New condition")
            result = update_car_condition(cid, cond)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "6":
            cid = get_input("Enter car ID to remove")
            result = remove_car(cid)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "7":
            try:
                result = add_spare_parts(int(get_input("Spare parts to add")))
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "8":
            try:
                result = use_spare_parts(int(get_input("Spare parts to use")))
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "9":
            try:
                result = add_tools(int(get_input("Tools to add")))
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "10":
            try:
                result = use_tools(int(get_input("Tools to use")))
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "11":
            pt = get_parts_and_tools()
            print(f"\n  Spare Parts : {pt['spare_parts']}")
            print(f"  Tools       : {pt['tools']}")

        elif choice == "12":
            try:
                result = add_cash(float(get_input("Amount to add ($)")))
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "13":
            try:
                result = deduct_cash(float(get_input("Amount to deduct ($)")))
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "14":
            print(f"\n  Cash Balance: ${get_cash_balance()['cash_balance']:.2f}")

        elif choice == "15":
            s = get_inventory_summary()
            print(f"\n  Cash Balance : ${s['cash_balance']:.2f}")
            print(f"  Spare Parts  : {s['spare_parts']}")
            print(f"  Tools        : {s['tools']}")
            print(f"\n  Cars ({len(s['cars'])}):")
            if not s["cars"]:
                print("    None")
            else:
                print(f"  {'ID':<8} {'Name':<20} {'Condition':<14} {'Assigned'}")
                print("  " + "-" * 50)
                for c in s["cars"]:
                    print(f"  {c['id']:<8} {c['name']:<20} {c['condition']:<14} {c['assigned']}")

        elif choice == "0":
            break
        else:
            print("\n  Invalid option. Try again.")


# ----------------------------------------------------------------
# RACE MANAGEMENT MENU
# ----------------------------------------------------------------

def menu_race_management():
    while True:
        print_menu("RACE MANAGEMENT", {
            "1" : "Create race",
            "2" : "View race by ID",
            "3" : "List all races",
            "4" : "Enter driver into race",
            "5" : "Assign car to race",
            "6" : "Start race",
            "7" : "Complete race",
            "8" : "View race drivers",
            "9" : "View race cars",
            "10": "List available drivers",
            "11": "List available cars",
            "0" : "Back",
        })
        choice = get_input("Choose option")

        if choice == "1":
            result = create_race(get_input("Race name"))
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "2":
            result = get_race(get_input("Race ID (e.g. R001)"))
            if result["success"]:
                r = result["race"]
                print(f"\n  Name    : {r['name']}")
                print(f"  Status  : {r['status']}")
                print(f"  Drivers : {r['driver_ids'] or 'none'}")
                print(f"  Cars    : {r['car_ids'] or 'none'}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "3":
            races = list_races()["races"]
            if not races:
                print("\n  No races yet.")
            else:
                print(f"\n  {'ID':<8} {'Name':<20} {'Status':<12} {'Drivers':<10} {'Cars'}")
                print("  " + "-" * 58)
                for r in races:
                    print(f"  {r['id']:<8} {r['name']:<20} {r['status']:<12} "
                          f"{len(r['driver_ids']):<10} {len(r['car_ids'])}")

        elif choice == "4":
            result = enter_driver(get_input("Race ID"), get_input("Driver member ID"))
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "5":
            result = assign_car(get_input("Race ID"), get_input("Car ID"))
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "6":
            result = start_race(get_input("Race ID to start"))
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "7":
            result = complete_race(get_input("Race ID to complete"))
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "8":
            result = get_race_drivers(get_input("Race ID"))
            if result["success"]:
                print(f"\n  Drivers: {result['driver_ids'] or 'none'}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "9":
            result = get_race_cars(get_input("Race ID"))
            if result["success"]:
                print(f"\n  Cars: {result['car_ids'] or 'none'}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "10":
            ids = list_available_drivers()["driver_ids"]
            print(f"\n  Available drivers: {', '.join(ids) if ids else 'none'}")

        elif choice == "11":
            ids = list_available_cars()["car_ids"]
            print(f"\n  Available cars: {', '.join(ids) if ids else 'none'}")

        elif choice == "0":
            break
        else:
            print("\n  Invalid option. Try again.")


# ----------------------------------------------------------------
# RESULTS MENU
# ----------------------------------------------------------------

def menu_results():
    while True:
        print_menu("RESULTS", {
            "1": "Record race result",
            "2": "View result by race ID",
            "3": "List all results",
            "4": "Get race winner",
            "5": "View leaderboard",
            "6": "View driver race history",
            "0": "Back",
        })
        choice = get_input("Choose option")

        if choice == "1":
            rid = get_input("Race ID")
            raw = get_input("Driver rankings (comma-separated IDs, 1st to last)")
            rankings = [r.strip().upper() for r in raw.split(",") if r.strip()]
            try:
                prize = float(get_input("Prize money ($)"))
            except ValueError:
                print("\n  ✗ Prize must be a number.")
                continue
            dmg_raw = get_input("Damaged car IDs (comma-separated, or leave blank)")
            damages = [c.strip().upper() for c in dmg_raw.split(",") if c.strip()]
            result = record_result(rid, rankings, prize, damages)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "2":
            result = get_result(get_input("Race ID"))
            if result["success"]:
                r = result["result"]
                print(f"\n  Winner   : {r['winner_id']}")
                print(f"  Rankings : {r['rankings']}")
                print(f"  Prize    : ${r['prize_money']:.2f}")
                print(f"  Damages  : {r['damages'] or 'none'}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "3":
            results = list_results()["results"]
            if not results:
                print("\n  No results yet.")
            else:
                print(f"\n  {'Race ID':<10} {'Winner':<10} {'Prize':<12} {'Damages'}")
                print("  " + "-" * 45)
                for r in results:
                    print(f"  {r['race_id']:<10} {r['winner_id']:<10} "
                          f"${r['prize_money']:<11.2f} {r['damages'] or 'none'}")

        elif choice == "4":
            result = get_winner(get_input("Race ID"))
            if result["success"]:
                print(f"\n  Winner: {result['winner_name']} ({result['winner_id']})")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "5":
            board = get_leaderboard()["leaderboard"]
            if not board:
                print("\n  No races completed yet.")
            else:
                print(f"\n  {'#':<4} {'ID':<8} {'Name':<20} {'Wins'}")
                print("  " + "-" * 38)
                for i, e in enumerate(board, 1):
                    print(f"  {i:<4} {e['member_id']:<8} {e['name']:<20} {e['wins']}")

        elif choice == "6":
            result = get_driver_results(get_input("Driver member ID"))
            if not result["success"]:
                print(f"\n  ✗ {result['message']}")
            elif not result["races"]:
                print("\n  No race history.")
            else:
                print(f"\n  {'Race ID':<10} {'Position':<10} {'Prize'}")
                print("  " + "-" * 32)
                for r in result["races"]:
                    print(f"  {r['race_id']:<10} {r['position']:<10} ${r['prize_money']:.2f}")

        elif choice == "0":
            break
        else:
            print("\n  Invalid option. Try again.")


# ----------------------------------------------------------------
# MISSION PLANNING MENU
# ----------------------------------------------------------------

def menu_mission_planning():
    while True:
        print_menu("MISSION PLANNING", {
            "1" : "Create mission",
            "2" : "View mission by ID",
            "3" : "List all missions",
            "4" : "Assign crew member to mission",
            "5" : "Remove crew member from mission",
            "6" : "Start mission",
            "7" : "Complete mission",
            "8" : "Fail mission",
            "9" : "Check roles available",
            "0" : "Back",
        })
        choice = get_input("Choose option")

        if choice == "1":
            name = get_input("Mission name")
            print("  Types: delivery | rescue | sabotage | recon")
            mtype = get_input("Mission type")
            raw = get_input("Required roles (comma-separated)")
            roles = [r.strip().lower() for r in raw.split(",") if r.strip()]
            result = create_mission(name, mtype, roles)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "2":
            result = get_mission(get_input("Mission ID (e.g. MI001)"))
            if result["success"]:
                m = result["mission"]
                print(f"\n  Name           : {m['name']}")
                print(f"  Type           : {m['type']}")
                print(f"  Status         : {m['status']}")
                print(f"  Required roles : {m['required_roles']}")
                print(f"  Assigned crew  : {m['assigned_crew'] or 'none'}")
            else:
                print(f"\n  ✗ {result['message']}")

        elif choice == "3":
            missions = list_missions()["missions"]
            if not missions:
                print("\n  No missions yet.")
            else:
                print(f"\n  {'ID':<8} {'Name':<20} {'Type':<12} {'Status':<12} {'Crew'}")
                print("  " + "-" * 60)
                for m in missions:
                    print(f"  {m['id']:<8} {m['name']:<20} {m['type']:<12} "
                          f"{m['status']:<12} {len(m['assigned_crew'])}")

        elif choice == "4":
            mid_m = get_input("Mission ID")
            mid_c = get_input("Crew member ID")
            result = assign_crew_member(mid_m, mid_c)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "5":
            mid_m = get_input("Mission ID")
            mid_c = get_input("Crew member ID to remove")
            result = remove_crew_member(mid_m, mid_c)
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "6":
            result = start_mission(get_input("Mission ID to start"))
            if result["success"]:
                print(f"\n  ✓ {result['message']}")
            else:
                print(f"\n  ✗ {result['message']}")
                if result.get("missing_roles"):
                    print(f"  Missing roles: {result['missing_roles']}")

        elif choice == "7":
            result = complete_mission(get_input("Mission ID to complete"))
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "8":
            result = fail_mission(get_input("Mission ID to fail"))
            print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")

        elif choice == "9":
            raw = get_input("Roles to check (comma-separated)")
            roles = [r.strip().lower() for r in raw.split(",") if r.strip()]
            result = check_roles_available(roles)
            if result["success"]:
                print(f"\n  ✓ All required roles are available.")
            else:
                print(f"\n  ✗ Missing roles: {result['missing_roles']}")

        elif choice == "0":
            break
        else:
            print("\n  Invalid option. Try again.")


# ----------------------------------------------------------------
# MAIN MENU
# ----------------------------------------------------------------

def main():
    print("\n" + "=" * 50)
    print("   STREETRACE MANAGER — Underground Racing System")
    print("=" * 50)

    while True:
        print_menu("MAIN MENU", {
            "1": "Registration",
            "2": "Crew Management",
            "3": "Inventory",
            "4": "Race Management",
            "5": "Results",
            "6": "Mission Planning",
            "0": "Exit",
        })
        choice = get_input("Choose module")

        if choice == "1":
            menu_registration()
        elif choice == "2":
            menu_crew_management()
        elif choice == "3":
            menu_inventory()
        elif choice == "4":
            menu_race_management()
        elif choice == "5":
            menu_results()
        elif choice == "6":
            menu_mission_planning()
        elif choice == "0":
            print("\n  Goodbye. Stay off the radar.\n")
            sys.exit(0)
        else:
            print("\n  Invalid option. Try again.")


if __name__ == "__main__":
    main()