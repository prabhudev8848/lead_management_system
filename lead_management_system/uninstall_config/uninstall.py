import frappe

def delete_created_records(doctype, records):
    for record in records:
        try:
            record_doc = frappe.get_doc(doctype, record)
            record_doc.delete()
        except Exception as e:
            pass

def before_uninstall():
    roles = ["Admin", "L1 - Team Leader", "L2 - Team Member"]

    delete_created_records("Role Profile", roles)
    delete_created_records("Role", roles)
