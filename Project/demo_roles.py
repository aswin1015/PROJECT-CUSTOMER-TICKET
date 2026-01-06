"""
Demo script showing the complete flow with different user roles
(Windows-safe, no emojis)
"""

from database import (
    init_database,
    create_ticket,
    update_ticket,
    get_ticket,
    get_all_tickets,
    add_comment,
    get_ticket_comments,
)
from users import init_users_table, setup_demo_users
from permissions import *
from allocation import get_available_staff, get_allocation_report
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def demo_customer_flow():
    """Demonstrate customer flow"""
    print_section("CUSTOMER FLOW")

    print("\n1. Customer creates a ticket")
    customer_email = "customer1@example.com"

    try:
        ticket = create_ticket(
            title="Cannot login to my account",
            description="I forgot my password and the reset link is not working",
            priority="High",
            created_by=customer_email,
        )

        print(f"[OK] Ticket #{ticket.id} created by {customer_email}")
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

    print("\n2. Customer views their tickets")
    try:
        filters = get_user_tickets_filter(customer_email)
        customer_tickets = get_all_tickets(**filters)
        print(f"[OK] Customer sees {len(customer_tickets)} ticket(s)")
        for t in customer_tickets:
            print(f"  - {t}")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n3. Customer tries to update ticket status (should fail)")
    try:
        assert_can_update_ticket(customer_email, ticket.id)
        print("[ERROR] Customer should not be able to update ticket!")
    except PermissionDenied as e:
        print(f"[OK - DENIED] {e}")

    return ticket.id


def demo_admin_flow(ticket_id):
    """Demonstrate admin flow"""
    print_section("ADMIN FLOW")

    admin_email = "admin@system.com"

    print("\n1. Admin views all tickets")
    try:
        tickets = admin_view_all_tickets(admin_email)
        print(f"[OK] Admin sees {len(tickets)} tickets")
    except PermissionDenied as e:
        print(f"[ERROR] {e}")
        return

    print("\n2. Admin assigns ticket to helper")
    try:
        admin_assign_ticket(
            admin_email=admin_email,
            ticket_id=ticket_id,
            helper_email="john@support.com"
        )
        print(f"[OK] Ticket #{ticket_id} assigned to john@support.com")
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    print("\n3. Admin checks helper workload")
    try:
        staff_list = get_available_staff()
        print("[OK] Available helpers:")
        for staff in staff_list:
            status = "FULL" if staff['current_tickets'] >= staff['max_tickets'] else "OK"
            print(
                f"  [{status}] {staff['name']} ({staff['email']}): "
                f"{staff['current_tickets']}/{staff['max_tickets']} tickets"
            )
    except Exception as e:
        print(f"[ERROR] {e}")


def demo_helper_flow(ticket_id):
    """Demonstrate helper flow"""
    print_section("HELPER FLOW")

    helper_email = "john@support.com"

    print("\n1. Helper views assigned tickets")
    try:
        filters = get_user_tickets_filter(helper_email)
        helper_tickets = get_all_tickets(**filters)
        print(f"[OK] Helper sees {len(helper_tickets)} assigned ticket(s)")
        for t in helper_tickets:
            print(f"  - {t}")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n2. Helper updates ticket status")
    try:
        assert_can_update_ticket(helper_email, ticket_id)
        update_ticket(
            ticket_id,
            status="In Progress",
            changed_by=helper_email,
        )
        print("[OK] Ticket status updated to 'In Progress'")
    except PermissionDenied as e:
        print(f"[ERROR] {e}")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n3. Helper adds internal note")
    try:
        require_permission(helper_email, "add_comment", ticket_id=ticket_id)
        
        if can_add_internal_comment(helper_email):
            add_comment(
                ticket_id,
                helper_email,
                "Checked user account. Password reset link was expired.",
                is_internal=True,
            )
            print("[OK] Internal note added")
        else:
            print("[ERROR] Helper should be able to add internal notes")
    except PermissionDenied as e:
        print(f"[ERROR] {e}")

    print("\n4. Helper adds public comment")
    try:
        add_comment(
            ticket_id,
            helper_email,
            "I've sent you a new password reset link. Please check your email.",
            is_internal=False,
        )
        print("[OK] Public comment added")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n5. Helper resolves ticket")
    try:
        update_ticket(
            ticket_id,
            status="Resolved",
            changed_by=helper_email,
        )
        print("[OK] Ticket marked as Resolved")
    except Exception as e:
        print(f"[ERROR] {e}")


def demo_customer_sees_updates(ticket_id):
    """Customer sees helper's updates"""
    print_section("CUSTOMER SEES UPDATES")

    customer_email = "customer1@example.com"

    print("\n1. Customer views ticket status")
    try:
        assert_can_view_ticket(customer_email, ticket_id)
        ticket = get_ticket(ticket_id)
        print(f"[OK] Ticket #{ticket.id} - Status: {ticket.status}")
        print(f"     Assigned to: {ticket.assigned_to}")
    except PermissionDenied as e:
        print(f"[ERROR] {e}")

    print("\n2. Customer views comments (public only)")
    try:
        include_internal = can_view_internal_comments(customer_email)
        comments = get_ticket_comments(ticket_id, include_internal=include_internal)
        print(f"[OK] Customer sees {len(comments)} comment(s)")
        for c in comments:
            internal_flag = " [INTERNAL]" if c.is_internal else ""
            print(f"  [{c.author}]{internal_flag}: {c.comment}")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n3. Customer adds reply")
    try:
        require_permission(customer_email, "add_comment", ticket_id=ticket_id)
        add_comment(
            ticket_id,
            customer_email,
            "Thank you! The new link worked.",
            is_internal=False,
        )
        print("[OK] Customer reply added")
    except Exception as e:
        print(f"[ERROR] {e}")


def demo_permission_checks():
    """Demonstrate permission checks"""
    print_section("PERMISSION CHECKS")

    customer = "customer1@example.com"
    helper = "john@support.com"
    admin = "admin@system.com"

    checks = [
        ("View all tickets", can_view_all_tickets),
        ("Assign tickets", can_assign_ticket),
        ("Delete tickets", can_delete_ticket),
        ("View internal comments", can_view_internal_comments),
        ("Manage users", can_manage_users),
        ("View analytics", can_view_analytics),
    ]

    print(f"\n{'Action':<30} {'Customer':<10} {'Helper':<10} {'Admin':<10}")
    print("-" * 70)

    for action, check in checks:
        customer_can = "YES" if check(customer) else "NO"
        helper_can = "YES" if check(helper) else "NO"
        admin_can = "YES" if check(admin) else "NO"
        
        print(
            f"{action:<30} {customer_can:<10} {helper_can:<10} {admin_can:<10}"
        )


def run_complete_demo():
    """Run the complete role-based demo"""
    print("\n" + "=" * 70)
    print("CUSTOMER SUPPORT TICKETING SYSTEM - ROLE DEMO")
    print("=" * 70)

    print("\nInitializing system...")
    try:
        init_database()
        init_users_table()
        setup_demo_users()
        print("[OK] System initialized")
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        return

    ticket_id = demo_customer_flow()
    if ticket_id:
        demo_admin_flow(ticket_id)
        demo_helper_flow(ticket_id)
        demo_customer_sees_updates(ticket_id)
    
    demo_permission_checks()

    print_section("FINAL WORKLOAD REPORT")
    try:
        get_allocation_report()
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETED")
    print("=" * 70)
    print("\nSummary:")
    print("- Customers can create and view their own tickets")
    print("- Helpers can view and update assigned tickets")
    print("- Admins can manage all tickets and users")
    print("- Permission system enforces role-based access control")


if __name__ == "__main__":
    run_complete_demo()
