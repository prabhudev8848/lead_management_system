# Copyright (c) 2025, Prabhudev Desai and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Team(Document):
     
	def before_save(self):
		if frappe.db.exists(self.doctype, self.name):
			handle_permission_updates(self)
		else:
			create_new_permissions(self)

def create_new_permissions(self):
    """Assign permissions to the team leader and members when a new team is created."""
    if self.team_leader:
        assign_permission(self.team_leader, "Team", self.team_name)
        assign_permission(self.team_leader, "User", self.team_leader)

    for member in self.team_members:
        if self.team_leader:
            assign_permission(self.team_leader, "User", member.user)

        assign_permission(member.user, "Team", self.team_name)
        assign_permission(member.user, "User", member.user)

def handle_permission_updates(self):
    """Handle all permission updates based on changes in team details."""
    previous_doc = frappe.get_doc(self.doctype, self.name)

    previous_team_name = previous_doc.team_name
    current_team_name = self.team_name

    previous_team_type = previous_doc.team_type
    current_team_type = self.team_type

    prev_leader = previous_doc.team_leader
    curr_leader = self.team_leader

    prev_members = {member.user for member in previous_doc.team_members}
    curr_members = {member.user for member in self.team_members}

    removed_members = prev_members - curr_members
    added_members = curr_members - prev_members

    # Remove old permissions if the team name changed
    if previous_team_type != current_team_type:
        revoke_permission(prev_leader, "Team", previous_team_name)
        for member in prev_members:
            revoke_permission(member, "Team", previous_team_name)

    # Remove permissions if leader changed
    if prev_leader != curr_leader:
        revoke_permission(prev_leader, "User", prev_leader)
        for member in prev_members:
            revoke_permission(prev_leader, "User", member)

    # Remove permissions for removed members
    for removed_member in removed_members:
        revoke_permission(removed_member, "User", removed_member)
        revoke_permission(removed_member, "Team", previous_team_name)

    # Assign new permissions
    if previous_team_type != current_team_type or prev_leader != curr_leader:
        create_new_permissions(self)  # If the team or leader changed, reset permissions

    # Add permissions for new members
    for added_member in added_members:
        assign_permission(added_member, "User", added_member)
        assign_permission(added_member, "Team", current_team_name)

def check_existing_permissions(user, allow, for_value):
    """Check if a user already has the specified permission."""
    return frappe.db.exists("User Permission", {"user": user, "allow": allow, "for_value": for_value})

def assign_permission(user, allow, for_value):
    """Assign a new user permission if it does not already exist."""
    if not check_existing_permissions(user, allow, for_value):
        permission_doc = frappe.new_doc("User Permission")
        permission_doc.user = user
        permission_doc.allow = allow
        permission_doc.for_value = for_value
        permission_doc.save()

def revoke_permission(user, allow, for_value):
    """Remove an existing user permission."""
    frappe.db.delete("User Permission", {"user": user, "allow": allow, "for_value": for_value})
