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
            result = list_members()
            members = result["members"]
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
            result = get_crew_summary()
            summary = result["summary"]
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
            result = list_cars()
            cars = result["cars"]
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
                print("\n  No cars available (good + unassigned).")
            else:
                print(f"\n  Available car IDs: {', '.join(available)}")

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
                amt = int(get_input("How many spare parts to add"))
                result = add_spare_parts(amt)
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "8":
            try:
                amt = int(get_input("How many spare parts to use"))
                result = use_spare_parts(amt)
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "9":
            try:
                amt = int(get_input("How many tools to add"))
                result = add_tools(amt)
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "10":
            try:
                amt = int(get_input("How many tools to use"))
                result = use_tools(amt)
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "11":
            pt = get_parts_and_tools()
            print(f"\n  Spare Parts : {pt['spare_parts']}")
            print(f"  Tools       : {pt['tools']}")

        elif choice == "12":
            try:
                amt = float(get_input("Amount to add ($)"))
                result = add_cash(amt)
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "13":
            try:
                amt = float(get_input("Amount to deduct ($)"))
                result = deduct_cash(amt)
                print(f"\n  {'✓' if result['success'] else '✗'} {result['message']}")
            except ValueError:
                print("\n  ✗ Must be a number.")

        elif choice == "14":
            bal = get_cash_balance()
            print(f"\n  Cash Balance: ${bal['cash_balance']:.2f}")

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
            "0": "Exit",
        })
        choice = get_input("Choose module")

        if choice == "1":
            menu_registration()
        elif choice == "2":
            menu_crew_management()
        elif choice == "3":
            menu_inventory()
        elif choice == "0":
            print("\n  Goodbye. Stay off the radar.\n")
            sys.exit(0)
        else:
            print("\n  Invalid option. Try again.")


if __name__ == "__main__":
    main()