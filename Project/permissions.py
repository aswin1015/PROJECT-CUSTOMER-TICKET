"""
Permission system to control what each role can do
"""
import logging

from users import (
    get_user_by_email,
    ROLE_CUSTOMER,
    ROLE_HELPER,
    ROLE_ADMIN,
)
from database import (
    get_ticket,
    get_all_tickets,
    update_ticket,
)

logger = logging.getLogger(__name__)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    # Verify helper exists and is active
    helper = get_user_by_email(helper_email)
    if not helper or helper.role != ROLE_HELPER or not helper.is_active:
        raise ValueError("Invalid or inactive helper")

    update_ticket(
        ticket_id,
        assigned_to=helper_email,
        changed_by=admin_email,
    )

    logger.info(f"Admin {admin_email} assigned ticket #{ticket_id} to {helper_email}")
    return ticket


def can_create_ticket(user_email: str) -> bool:
    """Anyone can create tickets"""
    user = get_user_by_email(user_email)
    return user is not None and user.is_active


def can_view_ticket(user_email: str, ticket_id: int) -> bool:
    """
    - Customer: Can view their own tickets
    - Helper: Can view assigned tickets
    - Admin: Can view all tickets
    """
    user = get_user_by_email(user_email)
    if not user or not user.is_active:
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
    return user and user.role == ROLE_ADMIN and user.is_active


def can_update_ticket(user_email: str, ticket_id: int) -> bool:
    """
    - Customer: No (cannot update)
    - Helper: Can update assigned tickets
    - Admin: Can update all tickets
    """
    user = get_user_by_email(user_email)
    if not user or not user.is_active:
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
    
    # Customers cannot update tickets
    return False


def can_delete_ticket(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: No
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role == ROLE_ADMIN and user.is_active


def can_assign_ticket(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: No
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role == ROLE_ADMIN and user.is_active


def can_add_comment(user_email: str, ticket_id: int) -> bool:
    user = get_user_by_email(user_email)
    if not user or not user.is_active:
        return False

    ticket = get_ticket(ticket_id)
    if not ticket:
        return False

    if user.role == ROLE_ADMIN:
        return True

    if user.role == ROLE_HELPER:
        return ticket.assigned_to == user_email

    if user.role == ROLE_CUSTOMER:
        return ticket.created_by == user_email

    return False


def can_add_internal_comment(user_email: str, ticket_id: int) -> bool:
    user = get_user_by_email(user_email)
    if not user or not user.is_active:
        return False

    ticket = get_ticket(ticket_id)
    if not ticket:
        return False

    if user.role == ROLE_ADMIN:
        return True

    if user.role == ROLE_HELPER:
        return ticket.assigned_to == user_email

    return False


def can_view_internal_comments(user_email: str) -> bool:
    """
    - Customer: No (cannot see internal notes)
    - Helper: Yes
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role in [ROLE_HELPER, ROLE_ADMIN] and user.is_active


def can_view_workload(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: Can view own workload
    - Admin: Can view all workload
    """
    user = get_user_by_email(user_email)
    return user and user.role in [ROLE_HELPER, ROLE_ADMIN] and user.is_active


def can_manage_users(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: No
    - Admin: Yes
    """
    user = get_user_by_email(user_email)
    return user and user.role == ROLE_ADMIN and user.is_active


def can_view_analytics(user_email: str) -> bool:
    """
    - Customer: No
    - Helper: Limited (own stats only)
    - Admin: Yes (full analytics)
    """
    user = get_user_by_email(user_email)
    return user and user.role in [ROLE_HELPER, ROLE_ADMIN] and user.is_active


def get_user_tickets_filter(user_email: str) -> dict:
    """
    Get filter for tickets based on user role
    Returns dict to pass to get_all_tickets()
    """
    user = get_user_by_email(user_email)
    if not user or not user.is_active:
        return {"created_by": "___NONEXISTENT___"}  # Return no tickets
    
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
        "add_internal_comment": lambda: can_add_internal_comment(user_email),
        "view_internal_comments": lambda: can_view_internal_comments(user_email),
        "view_workload": lambda: can_view_workload(user_email),
        "manage_users": lambda: can_manage_users(user_email),
        "view_analytics": lambda: can_view_analytics(user_email),
    }
    
    check = permission_checks.get(action)
    if not check:
        raise ValueError(f"Unknown permission action: {action}")
    
    if not check():
        user = get_user_by_email(user_email)
        role = user.role if user else "unknown"
        logger.warning(f"Permission denied: {role} user {user_email} attempted to {action}")
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


def assert_is_helper_or_admin(user_email: str):
    """Raise exception if user is not helper or admin"""
    user = get_user_by_email(user_email)
    if not user or user.role not in [ROLE_HELPER, ROLE_ADMIN] or not user.is_active:
        raise PermissionDenied("User must be a helper or admin")


def get_accessible_tickets(user_email: str, **additional_filters):
    """
    Get all tickets accessible to user with optional additional filters
    """
    base_filters = get_user_tickets_filter(user_email)
    base_filters.update(additional_filters)
    return get_all_tickets(**base_filters)
