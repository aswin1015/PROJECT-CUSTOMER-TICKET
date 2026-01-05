"""
Permission system to control what each role can do
"""

from users import get_user_by_email, ROLE_CUSTOMER, ROLE_HELPER, ROLE_ADMIN
from database import get_ticket, get_all_tickets, update_ticket


class PermissionDenied(Exception):
    """Raised when user doesn't have permission"""
    pass



def admin_view_all_tickets(admin_email: str):
    """
    Admin-only function to view all tickets
    """
    require_permission(admin_email, "view_all_tickets")
    return get_all_tickets()


def admin_assign_ticket(admin_email: str, ticket_id: int, helper_email: str):
    """
    Admin-only function to assign a ticket to a helper
    """
    require_permission(admin_email, "assign_ticket")

    ticket = get_ticket(ticket_id)
    if not ticket:
        raise ValueError("Ticket not found")

    update_ticket(
        ticket_id,
        assigned_to=helper_email,
        changed_by=admin_email,
    )

    return ticket


def can_create_ticket(user_email: str) -> bool:
    """Anyone can create tickets"""
    return True


def can_view_ticket(user_email: str, ticket_id: int) -> bool:
    """
    - Customer: Can view their own tickets
    - Helper: Can view assigned tickets
    - Admin: Can view all tickets
    """
    user = get_user_by_email(user_email)
    if not user:
        return False
    
    ticket = get_ticket(ticket_id)
    if not ticket:
        return False
    
    # Admin can view all
    if user.role == ROLE_ADMIN:
        return True
    
    # Helper can view assigned tickets
    if user.role == ROLE_HELPER:
        return ticket.assigned_to == user_email
    
    # Customer can view their own tickets
    if user.role == ROLE_CUSTOMER:
        return ticket.created_by == user_email
    
    return False


def can_view_all_tickets(user_email: str) -> bool:
    """
    - Customer: No (only their own)
    - Helper: No (only assigned)
    - Admin: Yes (all tickets)
    """
    user = get_user_by_email(user_email)
    return user and user.role == ROLE_ADMIN


def can_update_ticket(user_email: str, ticket_id: int) -> bool:
    """
    - Customer: No (cannot update)
    - Helper: Can update assigned tickets
    - Admin: Can update all tickets
    """
    user = get_user_by_email(user_email)
    if not user:
        return False
    
    ticket = get_ticket(ticket_id)
    if not ticket:
        return False
    
    # Admin can update all
    if user.role == ROLE_ADMIN:
        return True
    
    # Helper can update assigned tickets
    if user.role == ROLE_HELPER:
        return ticket.assigned_to == user_email
    
    return False


def can_delete_ticket(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: No
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role == ROLE_ADMIN


def can_assign_ticket(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: No
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role == ROLE_ADMIN


def can_add_comment(user_email: str, ticket_id: int) -> bool:
    """
    - Customer: Can comment on their own tickets
    - Helper: Can comment on assigned tickets
    - Admin: Can comment on all tickets
    """
    user = get_user_by_email(user_email)
    if not user:
        return False
    
    ticket = get_ticket(ticket_id)
    if not ticket:
        return False
    
    # Admin can comment on all
    if user.role == ROLE_ADMIN:
        return True
    
    # Helper can comment on assigned tickets
    if user.role == ROLE_HELPER:
        return ticket.assigned_to == user_email
    
    # Customer can comment on their own tickets
    if user.role == ROLE_CUSTOMER:
        return ticket.created_by == user_email
    
    return False


def can_view_internal_comments(user_email: str) -> bool:
    """
    - Customer: No (cannot see internal notes)
    - Helper: Yes
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role in [ROLE_HELPER, ROLE_ADMIN]


def can_view_workload(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: Can view own workload
    - Admin: Can view all workload
    """
    user = get_user_by_email(user_email)
    return user and user.role in [ROLE_HELPER, ROLE_ADMIN]


def can_manage_users(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: No
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role == ROLE_ADMIN


def get_user_tickets_filter(user_email: str) -> dict:
    """
    Get filter for tickets based on user role
    Returns dict to pass to get_all_tickets()
    """
    user = get_user_by_email(user_email)
    if not user:
        return {}
    
    # Admin sees all tickets
    if user.role == ROLE_ADMIN:
        return {}
    
    # Helper sees assigned tickets
    if user.role == ROLE_HELPER:
        return {"assigned_to": user_email}
    
    # Customer sees their own tickets
    if user.role == ROLE_CUSTOMER:
        return {"created_by": user_email}
    
    return {}


def require_permission(user_email: str, action: str, **kwargs):
    """
    Check permission and raise exception if denied
    Usage: require_permission("user@example.com", "view_ticket", ticket_id=1)
    """
    permission_checks = {
        "create_ticket": lambda: can_create_ticket(user_email),
        "view_ticket": lambda: can_view_ticket(user_email, kwargs.get("ticket_id")),
        "view_all_tickets": lambda: can_view_all_tickets(user_email),
        "update_ticket": lambda: can_update_ticket(user_email, kwargs.get("ticket_id")),
        "delete_ticket": lambda: can_delete_ticket(user_email),
        "assign_ticket": lambda: can_assign_ticket(user_email),
        "add_comment": lambda: can_add_comment(user_email, kwargs.get("ticket_id")),
        "view_internal_comments": lambda: can_view_internal_comments(user_email),
        "view_workload": lambda: can_view_workload(user_email),
        "manage_users": lambda: can_manage_users(user_email),
    }
    
    check = permission_checks.get(action)
    if not check or not check():
        user = get_user_by_email(user_email)
        role = user.role if user else "unknown"
        raise PermissionDenied(f"User ({role}) does not have permission to {action}")


# Helper functions for common permission checks

def assert_can_view_ticket(user_email: str, ticket_id: int):
    """Raise exception if user cannot view ticket"""
    require_permission(user_email, "view_ticket", ticket_id=ticket_id)


def assert_can_update_ticket(user_email: str, ticket_id: int):
    """Raise exception if user cannot update ticket"""
    require_permission(user_email, "update_ticket", ticket_id=ticket_id)


def assert_is_admin(user_email: str):
    """Raise exception if user is not admin"""
    require_permission(user_email, "assign_ticket")
