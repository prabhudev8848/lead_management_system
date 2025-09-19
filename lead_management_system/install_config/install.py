import frappe

def after_install():
    roles = ["Admin", "L1 - Team Leader", "L2 - Team Member"]

    for role in roles:
        role_doc = frappe.new_doc("Role")
        role_doc.role_name = role
        role_doc.save()

        role_profile = frappe.new_doc("Role Profile")
        role_profile.role_profile = role

        has_role = role_profile.append("roles", {
            "role": role
        })

        role_profile.save()
        