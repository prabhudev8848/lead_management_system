# Copyright (c) 2025, Prabhudev Desai and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Lead(Document):
	
    def before_save(doc):
        old_doc = frappe.get_doc("Lead", doc.name) if frappe.db.exists("Lead", doc.name) else None

        # Prevent moving back to Cold Calling
        if old_doc and old_doc.status != "Cold Calling" and doc.status == "Cold Calling":
            frappe.throw("Leads cannot be moved back to Cold Calling.")

        # Ensure only Admin or L1 - Team Leader can change Lead status
        if old_doc and old_doc.status != doc.status:
            if not check_current_user_role(["Admin", "L1 - Team Leader"]):
                frappe.throw("Only Admin or L1 - Team Leader can change Lead status.")

        # Ensure L2 - Team Member cannot set substatus to "Completed"
        if doc.substatus == "Completed" and check_current_user_role(["L2 - Team Member"]):
            frappe.throw("L2 - Team Member cannot change substatus to 'Completed'.")

        # Ensure L2 - Team Member follows correct substatus flow
        if check_current_user_role(["L2 - Team Member"]) and old_doc:
            valid_substatus_transitions = {
                "Pending": "Under Work",
                "Under Work": "Under Review"
            }
            if old_doc.substatus in valid_substatus_transitions and doc.substatus != valid_substatus_transitions[old_doc.substatus]:
                frappe.throw(f"L2 - Team Member can only move substatus from '{old_doc.substatus}' to '{valid_substatus_transitions[old_doc.substatus]}'.")

        # If the lead is NEW, assign it to the correct team using round-robin
        if not old_doc:
            assign_team_round_robin(doc)

        # Handle Lead Assignment on Status Change
        if old_doc and old_doc.status != doc.status:
            doc.substatus = "Pending"  # Reset substatus when status changes
            doc.assigned_user = None   # Reset assigned user
            assign_team_round_robin(doc)

def assign_team_round_robin(doc):
    """Assigns a new lead to one of the multiple teams (CC Team, LR Team, Customer Team) in a round-robin manner"""
    team_type = get_team_type_for_status(doc.status)

    if not team_type:
        return  # No reassignment needed

    # Get all available teams for this team type
    available_teams = frappe.get_all("Team", filters={"team_type": team_type}, fields=["name"])
    if not available_teams:
        frappe.throw(f"No teams found for {team_type} assignment.")

    # Get last assigned team from Lead Assignment Tracker
    tracker = frappe.get_value("Lead Assignment Tracker", {"team_type": team_type}, "last_assigned_team")

    # If tracker doesn't exist, create it
    if not tracker:
        tracker_doc = frappe.new_doc("Lead Assignment Tracker")
        tracker_doc.team_type = team_type
        tracker_doc.save()
        tracker = tracker_doc.name

    # Find the next team in the list (Round Robin)
    next_index = 0
    if tracker and tracker in [t["name"] for t in available_teams]:
        last_index = [t["name"] for t in available_teams].index(tracker)
        next_index = (last_index + 1) % len(available_teams)

    assigned_team = available_teams[next_index]["name"]
    doc.assigned_team = assigned_team

    # Assign the lead to L1 first, then distribute to L2s
    assign_user_to_lead(doc, assigned_team, team_type)

    # Update Lead Assignment Tracker
    frappe.db.set_value("Lead Assignment Tracker", {"team_type": team_type}, {
        "last_assigned_team": assigned_team
    })

def assign_user_to_lead(doc, assigned_team, team_type):
    """Assigns the lead to a Team Leader first, then distributes to L2s"""
    team = frappe.get_doc("Team", assigned_team)

    # Get Team Leader (L1)
    team_leader = team.team_leader

    # Assign to L1 first
    doc.assigned_user = team_leader

    # Fetch all users from the Team's child table (All are L2s)
    l2_users = [member.user for member in team.get("team_members")]

    if l2_users:
        last_assigned_user = frappe.get_value("Lead Assignment Tracker", {"team_type": team_type}, "last_assigned_user")
        user_index = 0  # Default to first member
        
        if last_assigned_user and last_assigned_user in l2_users:
            last_index = l2_users.index(last_assigned_user)
            user_index = (last_index + 1) % len(l2_users)

        assigned_user = l2_users[user_index]
        doc.assigned_user = assigned_user
    else:
        # Default to Team Leader if no L2 members exist
        doc.assigned_user = team_leader if team_leader else None

    # Update last assigned user in tracker
    frappe.db.set_value("Lead Assignment Tracker", {"team_type": team_type}, {
        "last_assigned_user": doc.assigned_user
    })

def get_team_type_for_status(status):
    """Maps lead status to the correct team type"""
    status_team_map = {
        "Cold Calling": "CC Team",
        "Lead": "LR Team",
        "Register": "LR Team",
        "Customer": "Customer Team"
    }
    return status_team_map.get(status)

def check_current_user_role(required_roles):
    """Check if the current user has one of the required roles"""
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    return any(role in user_roles for role in required_roles)

