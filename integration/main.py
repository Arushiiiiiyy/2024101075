# main.py
# StreetRace Manager — Command Line Interface
# Grow this file as each integration part is completed.
#
# Run from integration/ folder with:
# PYTHONPATH=codes:. python main.py

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "codes"))
sys.path.insert(0, os.path.dirname(__file__))


from registration.registration import (
    register_member,
    deactivate_member,
    reactivate_member,
    list_members,
    get_member,
)
from crew_management.crew_management import (
    assign_role,
    get_role,
    set_skill_level,
    get_skill_level,
    get_crew_summary,
    list_members_by_role,
    has_available_role,
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


def menu_registration():
    while True:
        print_menu("REGISTRATION", {
            "1": "Register new crew member",
            "2": "View crew member by ID",
            "3": "List all crew members",
            "4": "Deactivate crew member",
            "5": "Reactivate crew member",
            "0": "Back to main menu",
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
            "0": "Back to main menu",
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
            status = "✓ Available" if available else "✗ Not available"
            print(f"\n  Role '{role}': {status}")

        elif choice == "0":
            break
        else:
            print("\n  Invalid option. Try again.")




def main():
    print("\n" + "=" * 50)
    print("   STREETRACE MANAGER — Underground Racing System")
    print("=" * 50)

    while True:
        print_menu("MAIN MENU", {
            "1": "Registration",
            "2": "Crew Management",
            "0": "Exit",
        })
        choice = get_input("Choose module")

        if choice == "1":
            menu_registration()
        elif choice == "2":
            menu_crew_management()
        elif choice == "0":
            print("\n  Goodbye. Stay off the radar.\n")
            sys.exit(0)
        else:
            print("\n  Invalid option. Try again.")


if __name__ == "__main__":
    main()